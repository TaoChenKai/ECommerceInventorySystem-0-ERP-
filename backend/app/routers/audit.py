from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import AuditLog, User
from ..deps import require_role
from ..config import settings

router = APIRouter(prefix="/api/audits", tags=["audit"])


@router.get("")
def list_audits(db: Session = Depends(get_db), _u: User = Depends(require_role("boss", "admin"))):
    return db.query(AuditLog).order_by(AuditLog.id.desc()).limit(200).all()


@router.delete("")
def clear_audits(before: str | None = Query(default=None),
                 db: Session = Depends(get_db),
                 _u: User = Depends(require_role("boss", "admin"))):
    """手动清理操作日志：boss / admin 均可。

    - 不传 before：清空全部
    - 传 before（ISO 时间字符串，如 2026-05-01）：只删除 created_at 早于该时间的记录
    返回 {"deleted": N}
    """
    q = db.query(AuditLog)
    if before:
        try:
            cutoff = datetime.fromisoformat(before)
        except ValueError:
            raise HTTPException(status_code=400, detail="before 参数格式错误，应为 ISO 时间字符串（如 2026-05-01）")
        q = q.filter(AuditLog.created_at < cutoff)
    deleted = q.delete(synchronize_session=False)
    db.commit()
    return {"deleted": deleted}


def cleanup_old_audits(db: Session) -> int:
    """自动清理：删除 created_at 早于 AUDIT_RETENTION_DAYS 天的旧日志，返回删除条数。

    created_at 以 UTC 存储（datetime.utcnow），故阈值同样按 UTC 计算。
    """
    cutoff = datetime.utcnow() - timedelta(days=settings.AUDIT_RETENTION_DAYS)
    deleted = db.query(AuditLog).filter(AuditLog.created_at < cutoff).delete(synchronize_session=False)
    db.commit()
    return deleted
