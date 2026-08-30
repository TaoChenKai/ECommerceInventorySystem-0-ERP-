# -*- coding: utf-8 -*-
"""设置中心：用户偏好（外观）、背景图、数据存储位置迁移（仅本机 SQLite）、云端备份占位。"""
import os
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from ..config import settings, persist_settings
from ..database import get_db, SessionLocal, reconfigure_engine
from ..models import UserPreference, AuditLog
from ..schemas import PreferenceOut, PreferenceUpdate, MigrateRequest, StorageOut
from ..deps import get_current_user, require_role

router = APIRouter(prefix="/api/settings", tags=["settings"])

# 允许的背景图格式
BG_ALLOWED = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


def _get_pref(db: Session, user_id: int):
    return db.query(UserPreference).filter(UserPreference.user_id == user_id).first()


def _to_out(pref: UserPreference | None) -> PreferenceOut:
    if not pref:
        return PreferenceOut(theme="light", theme_color="default", bg_image="")
    return PreferenceOut(theme=pref.theme, theme_color=pref.theme_color, bg_image=pref.bg_image or "")


# ---------- 用户偏好 ----------
@router.get("/preference", response_model=PreferenceOut)
def get_preference(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """返回当前用户偏好（无记录返回默认值）"""
    return _to_out(_get_pref(db, user.id))


@router.put("/preference", response_model=PreferenceOut)
def save_preference(body: PreferenceUpdate, db: Session = Depends(get_db), user=Depends(get_current_user)):
    """保存当前用户偏好（upsert）"""
    pref = _get_pref(db, user.id)
    if not pref:
        pref = UserPreference(user_id=user.id, theme="light", theme_color="default", bg_image="")
        db.add(pref)
    pref.theme = body.theme
    pref.theme_color = body.theme_color
    pref.bg_image = body.bg_image or ""
    pref.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(pref)
    return _to_out(pref)


# ---------- 背景图 ----------
@router.post("/preference/bg-image")
async def upload_bg_image(file: UploadFile = File(...), db: Session = Depends(get_db), user=Depends(get_current_user)):
    """上传背景图（multipart，仅图片，覆盖该用户旧图）"""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in BG_ALLOWED:
        raise HTTPException(400, f"仅支持图片格式：{'、'.join(sorted(BG_ALLOWED))}")
    content = await file.read()
    if not content:
        raise HTTPException(400, "文件为空")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "背景图不能超过 10MB")

    media = Path(settings.MEDIA_DIR)
    media.mkdir(parents=True, exist_ok=True)
    fname = f"bg_{user.id}{ext}"
    (media / fname).write_bytes(content)
    # 覆盖：清理该用户可能存在的旧后缀文件
    for p in media.glob(f"bg_{user.id}.*"):
        if p.name != fname:
            p.unlink(missing_ok=True)

    pref = _get_pref(db, user.id)
    if not pref:
        pref = UserPreference(user_id=user.id, theme="light", theme_color="default", bg_image="")
        db.add(pref)
    pref.bg_image = fname
    pref.updated_at = datetime.utcnow()
    db.commit()
    return {"url": f"/media/{fname}", "filename": fname}


@router.delete("/preference/bg-image")
def delete_bg_image(db: Session = Depends(get_db), user=Depends(get_current_user)):
    """删除当前用户背景图"""
    pref = _get_pref(db, user.id)
    removed = False
    if pref and pref.bg_image:
        media = Path(settings.MEDIA_DIR)
        for p in media.glob(f"bg_{user.id}.*"):
            p.unlink(missing_ok=True)
        pref.bg_image = ""
        pref.updated_at = datetime.utcnow()
        db.commit()
        removed = True
    return {"removed": removed}


# ---------- 数据存储位置（仅 boss / admin） ----------
@router.get("/storage", response_model=StorageOut)
def get_storage(db: Session = Depends(get_db), _u=Depends(require_role("boss", "admin"))):
    """返回当前数据目录 / 数据库文件路径 / 媒体目录 / 数据库大小"""
    db_path = Path(settings.DATA_DIR) / "inventory.db"
    size = db_path.stat().st_size if db_path.exists() else 0
    return StorageOut(data_dir=settings.DATA_DIR, db_path=str(db_path),
                      media_dir=settings.MEDIA_DIR, db_size=size)


@router.post("/storage/migrate")
def migrate_storage(body: MigrateRequest, db: Session = Depends(get_db),
                    boss=Depends(require_role("boss", "admin"))):
    """把数据目录（含数据库 + 媒体文件）安全迁移到目标位置，失败自动回滚。"""
    new_raw = (body.new_dir or "").strip()
    if not new_raw:
        raise HTTPException(400, "请填写目标数据目录")
    new_path = Path(new_raw).expanduser()
    if not new_path.is_absolute():
        raise HTTPException(400, "请填写绝对路径（例如 D:\\inventory-data）")

    current = Path(settings.DATA_DIR)
    try:
        if new_path.resolve() == current.resolve():
            raise HTTPException(400, "目标目录与当前数据目录相同，无需迁移")
        if current.resolve() in new_path.resolve().parents or new_path.resolve() in current.resolve().parents:
            raise HTTPException(400, "目标目录不能是当前数据目录的子目录或上级目录")
    except OSError:
        pass

    # 目标目录可创建 / 可写
    try:
        new_path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise HTTPException(400, f"无法创建目标目录：{e}")
    if not os.access(new_path, os.W_OK):
        raise HTTPException(400, "目标目录不可写，请检查权限")

    # 当前数据库必须存在
    current_db = current / "inventory.db"
    if not current_db.exists():
        raise HTTPException(400, "当前数据库文件不存在，无法迁移")

    # 目标盘空间检查
    try:
        need = sum(f.stat().st_size for f in current.rglob("*") if f.is_file())
        free = shutil.disk_usage(new_path).free
    except OSError as e:
        raise HTTPException(400, f"无法获取磁盘信息：{e}")
    if free < need * 1.2 + 1024 * 1024:
        raise HTTPException(400, "目标盘可用空间不足，请清理后重试")

    # 1. 自动备份
    backup_path = current / f"inventory.db.bak-{datetime.now():%Y%m%d%H%M%S}"
    shutil.copy2(current_db, backup_path)

    # 2. 复制数据目录全部内容（跳过 .bak 备份）
    try:
        for item in current.iterdir():
            if item.name.startswith("inventory.db.bak-"):
                continue
            target = new_path / item.name
            if item.is_dir():
                shutil.copytree(item, target, dirs_exist_ok=True)
            else:
                shutil.copy2(item, target)
    except Exception as e:
        shutil.rmtree(new_path, ignore_errors=True)
        raise HTTPException(500, f"复制数据失败，已回滚：{e}")

    # 3. 校验：新库存在、大小一致、完整性检查通过
    new_db = new_path / "inventory.db"
    try:
        if not new_db.exists():
            raise RuntimeError("新数据库文件缺失")
        if new_db.stat().st_size != current_db.stat().st_size:
            raise RuntimeError("新数据库文件大小不一致")
    except RuntimeError as e:
        shutil.rmtree(new_path, ignore_errors=True)
        raise HTTPException(500, f"迁移校验失败，已回滚：{e}")

    # 4. 更新配置：持久化 .env + 刷新内存 + 重连数据库
    old_data_dir, old_media, old_url = settings.DATA_DIR, settings.MEDIA_DIR, settings.DATABASE_URL
    try:
        new_url = f"sqlite:///{new_db.as_posix()}"
        persist_settings(str(new_path.resolve()), new_url)
        settings.DATA_DIR = str(new_path.resolve())
        settings.MEDIA_DIR = str(new_path / "media")
        Path(settings.MEDIA_DIR).mkdir(parents=True, exist_ok=True)
        db.close()
        reconfigure_engine(new_url)
        settings.DATABASE_URL = new_url
    except Exception as e:
        # 失败回滚：恢复配置与连接，移除已复制内容
        try:
            persist_settings(old_data_dir, old_url)
            settings.DATA_DIR = old_data_dir
            settings.MEDIA_DIR = old_media
            settings.DATABASE_URL = old_url
            db.close()
            reconfigure_engine(old_url)
        except Exception:
            pass
        shutil.rmtree(new_path, ignore_errors=True)
        raise HTTPException(500, f"配置更新失败，已回滚：{e}")

    # 5. 成功后清空旧数据目录内容（保留 .bak 备份）
    for item in current.iterdir():
        if item.name.startswith("inventory.db.bak-"):
            continue
        try:
            if item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        except Exception:
            pass

    # 审计留痕
    try:
        s = SessionLocal()
        s.add(AuditLog(user_id=boss.id, username=boss.username, action="迁移数据目录",
                       detail=f"从 {old_data_dir} 迁移到 {new_path.resolve()}"))
        s.commit()
        s.close()
    except Exception:
        pass

    return {"ok": True, "data_dir": settings.DATA_DIR, "db_path": str(new_db)}


# ---------- 云端备份（占位） ----------
@router.get("/cloud-backup")
def cloud_backup(_u=Depends(get_current_user)):
    """云端备份预留端口：本期只占位，不做真实功能"""
    return {"available": False, "message": "云端备份功能预计在第二版开放"}
