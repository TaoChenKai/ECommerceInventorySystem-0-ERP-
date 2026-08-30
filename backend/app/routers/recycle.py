# -*- coding: utf-8 -*-
"""回收站 + 批量删除 + 智能筛选（v1.3）

- 智能筛选（只读，登录即可）：按时间线下拉的天数，返回「库存为空」或「长期无变动」的建议货品清单（含积压天数）
- 批量软删除（仅 boss/admin）：货品标记 deleted_at，进回收站，历史流水保留
- 回收站列表（只读，登录即可）：含删除时间 / 剩余清理天数倒计时
- 批量还原（仅 boss/admin）：清除 deleted_at，恢复为正常货品
- 彻底删除（仅 boss/admin）：物理删除货品 + 清关联数据（出入库流水 / 采购明细 / 销售明细）
- 启动自动清理（仅服务启动时）：物理清除超过 30 天仍留在回收站的数据
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from ..database import get_db
from ..models import Spu, Sku, StockLog, SaleItem, PurchaseItem, AuditLog, User
from ..schemas import RecycleBatchRequest
from ..deps import get_current_user, require_role

router = APIRouter(prefix="/api/recycle", tags=["recycle"])

# 回收站自动清理保留天数（与前端倒计时一致）
RECYCLE_RETENTION_DAYS = 30


def add_log(db: Session, user: User, action: str, detail: str = ""):
    db.add(AuditLog(user_id=user.id, username=user.username, action=action, detail=detail))


def _spu_total_stock(spu: Spu) -> int:
    return sum(s.stock or 0 for s in spu.skus)


def _last_change_at(db: Session, spu: Spu) -> datetime:
    """最后变动时间：最近一条出入库流水时间；无任何流水则退回建档时间"""
    log = (db.query(StockLog)
           .join(Sku, Sku.id == StockLog.sku_id)
           .filter(Sku.spu_id == spu.id)
           .order_by(StockLog.created_at.desc())
           .first())
    return log.created_at if log else spu.created_at


def _unique_ids(spu_ids: list[int]) -> list[int]:
    return list(dict.fromkeys(int(i) for i in spu_ids if i))


# ================= 智能筛选（只读） =================
@router.get("/analyze")
def analyze_recycle(days: int = 180, db: Session = Depends(get_db),
                    _u: User = Depends(get_current_user)):
    """按天数返回建议清理清单：库存为空 或 最后变动距今超过 days 天的货品（含积压天数）"""
    if days < 1:
        days = 1
    now = datetime.utcnow()
    items = []
    spus = (db.query(Spu).options(joinedload(Spu.skus))
            .filter(Spu.deleted_at.is_(None))
            .order_by(Spu.id.desc()).all())
    for spu in spus:
        total = _spu_total_stock(spu)
        last = _last_change_at(db, spu)
        idle_days = max((now - last).days, 0)
        reasons = []
        if total <= 0:
            reasons.append("库存为空")
        if idle_days >= days:
            reasons.append(f"长期无变动{idle_days}天")
        if not reasons:
            continue
        items.append({
            "id": spu.id,
            "name": spu.name,
            "code": spu.code or "",
            "category_name": spu.category.name if spu.category else None,
            "total_stock": total,
            "last_change_at": last,
            "idle_days": idle_days,
            "suggestion": "、".join(reasons),
        })
    return {"days": days, "count": len(items), "items": items}


# ================= 批量软删除（进回收站） =================
@router.post("/batch-delete")
def batch_delete(body: RecycleBatchRequest, db: Session = Depends(get_db),
                 u: User = Depends(require_role("boss", "admin"))):
    ids = _unique_ids(body.spu_ids)
    if not ids:
        raise HTTPException(400, "请至少选择一条货品")
    spus = (db.query(Spu)
            .filter(Spu.id.in_(ids), Spu.deleted_at.is_(None)).all())
    if not spus:
        raise HTTPException(404, "未找到可删除的货品（可能已进回收站）")
    now = datetime.utcnow()
    for spu in spus:
        spu.deleted_at = now
    db.commit()
    detail = "、".join(f"{s.name}({s.id})" for s in spus)
    add_log(db, u, "批量删除进回收站", f"{len(spus)}条：{detail}")
    db.commit()
    return {"ok": True, "count": len(spus), "ids": [s.id for s in spus]}


# ================= 回收站列表（只读） =================
@router.get("/list")
def recycle_list(db: Session = Depends(get_db), _u: User = Depends(get_current_user)):
    now = datetime.utcnow()
    spus = (db.query(Spu).options(joinedload(Spu.skus))
            .filter(Spu.deleted_at.isnot(None))
            .order_by(Spu.deleted_at.desc()).all())
    items = []
    for spu in spus:
        deleted_days = max((now - spu.deleted_at).days, 0)
        items.append({
            "id": spu.id,
            "name": spu.name,
            "code": spu.code or "",
            "category_name": spu.category.name if spu.category else None,
            "unit": spu.unit or "件",
            "sku_count": len(spu.skus),
            "total_stock": _spu_total_stock(spu),
            "deleted_at": spu.deleted_at,
            "deleted_days": deleted_days,
            "remain_days": max(RECYCLE_RETENTION_DAYS - deleted_days, 0),
        })
    return {"count": len(items), "items": items}


# ================= 批量还原 =================
@router.post("/restore")
def batch_restore(body: RecycleBatchRequest, db: Session = Depends(get_db),
                  u: User = Depends(require_role("boss", "admin"))):
    ids = _unique_ids(body.spu_ids)
    if not ids:
        raise HTTPException(400, "请至少选择一条货品")
    spus = (db.query(Spu)
            .filter(Spu.id.in_(ids), Spu.deleted_at.isnot(None)).all())
    if not spus:
        raise HTTPException(404, "未找到可还原的货品")
    for spu in spus:
        spu.deleted_at = None
    db.commit()
    detail = "、".join(f"{s.name}({s.id})" for s in spus)
    add_log(db, u, "回收站批量还原", f"{len(spus)}条：{detail}")
    db.commit()
    return {"ok": True, "count": len(spus), "ids": [s.id for s in spus]}


# ================= 彻底删除（物理删 + 清关联） =================
def _purge_spu(db: Session, spu: Spu):
    """物理删除单个货品并清关联数据（出入库流水 / 采购明细 / 销售明细 / 图片 / 规格）"""
    sku_ids = [s.id for s in spu.skus]
    if sku_ids:
        db.query(StockLog).filter(StockLog.sku_id.in_(sku_ids)).delete(synchronize_session=False)
        db.query(SaleItem).filter(SaleItem.sku_id.in_(sku_ids)).delete(synchronize_session=False)
        db.query(PurchaseItem).filter(PurchaseItem.sku_id.in_(sku_ids)).delete(synchronize_session=False)
    db.delete(spu)  # cascade 连带删除 skus / product_images


@router.post("/purge")
def batch_purge(body: RecycleBatchRequest, db: Session = Depends(get_db),
                u: User = Depends(require_role("boss", "admin"))):
    ids = _unique_ids(body.spu_ids)
    if not ids:
        raise HTTPException(400, "请至少选择一条货品")
    spus = (db.query(Spu).options(joinedload(Spu.skus))
            .filter(Spu.id.in_(ids), Spu.deleted_at.isnot(None)).all())
    if not spus:
        raise HTTPException(404, "未找到可彻底删除的货品")
    detail = "、".join(f"{s.name}({s.id})" for s in spus)
    for spu in spus:
        _purge_spu(db, spu)
    db.commit()
    add_log(db, u, "回收站彻底删除", f"{len(spus)}条：{detail}")
    db.commit()
    return {"ok": True, "count": len(spus)}


# ================= 启动自动清理 =================
def cleanup_expired_recycle_bin(db: Session) -> int:
    """物理清除超过保留天数仍留在回收站的货品，返回清理条数（供启动时调用）"""
    cutoff = datetime.utcnow() - timedelta(days=RECYCLE_RETENTION_DAYS)
    spus = (db.query(Spu).options(joinedload(Spu.skus))
            .filter(Spu.deleted_at.isnot(None), Spu.deleted_at < cutoff).all())
    for spu in spus:
        _purge_spu(db, spu)
    if spus:
        db.commit()
    return len(spus)
