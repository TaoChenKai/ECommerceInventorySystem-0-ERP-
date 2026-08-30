import os
import time
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from ..deps import get_current_user

router = APIRouter(prefix="/api", tags=["upload"])

# 允许的图片扩展名
ALLOWED = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}

# 图片存放目录：backend/static/images
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
IMAGES_DIR = STATIC_DIR / "images"


@router.post("/upload/image")
async def upload_image(file: UploadFile = File(...), _u=Depends(get_current_user)):
    """上传商品图片，返回可访问的 URL 路径（/static/images/xxx）"""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED:
        raise HTTPException(400, f"仅支持图片格式：{'、'.join(sorted(ALLOWED))}")
    IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    # 用 uuid + 时间戳保证文件名唯一，避免中文名/覆盖
    fname = f"{uuid.uuid4().hex}_{int(time.time() * 1000)}{ext}"
    dest = IMAGES_DIR / fname
    try:
        content = await file.read()
    except Exception:
        raise HTTPException(400, "读取文件失败")
    if not content:
        raise HTTPException(400, "文件为空")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(400, "图片不能超过 10MB")
    dest.write_bytes(content)
    return {"url": f"/static/images/{fname}", "filename": fname}
