from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import SenderProfile, AuditLog, User
from ..schemas import SenderCreate, SenderOut
from ..deps import get_current_user

router = APIRouter(prefix="/api", tags=["senders"])


def add_log(db: Session, user: User, action: str, detail: str = ""):
    db.add(AuditLog(user_id=user.id, username=user.username, action=action, detail=detail))


@router.get("/senders")
def list_senders(db: Session = Depends(get_db), _u: User = Depends(get_current_user)):
    """常用发件人列表（按创建顺序）"""
    return [SenderOut.model_validate(s) for s in db.query(SenderProfile).order_by(SenderProfile.id).all()]


@router.post("/senders")
def create_sender(body: SenderCreate, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    """新增常用发件人"""
    if not body.sender_name.strip():
        raise HTTPException(400, "发件人姓名不能为空")
    s = SenderProfile(
        name=body.name.strip(),
        sender_name=body.sender_name.strip(),
        phone=body.phone.strip(),
        address=body.address.strip(),
        remark=body.remark.strip(),
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    add_log(db, u, "新增发件人", f"{s.name}（{s.sender_name}）")
    db.commit()
    return SenderOut.model_validate(s)


@router.put("/senders/{sid}")
def update_sender(sid: int, body: SenderCreate, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    """修改常用发件人"""
    s = db.query(SenderProfile).filter(SenderProfile.id == sid).first()
    if not s:
        raise HTTPException(404, "发件人不存在")
    if not body.sender_name.strip():
        raise HTTPException(400, "发件人姓名不能为空")
    s.name = body.name.strip()
    s.sender_name = body.sender_name.strip()
    s.phone = body.phone.strip()
    s.address = body.address.strip()
    s.remark = body.remark.strip()
    db.commit()
    db.refresh(s)
    add_log(db, u, "修改发件人", f"{s.name}（{s.sender_name}）")
    db.commit()
    return SenderOut.model_validate(s)


@router.delete("/senders/{sid}")
def delete_sender(sid: int, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    """删除常用发件人"""
    s = db.query(SenderProfile).filter(SenderProfile.id == sid).first()
    if not s:
        raise HTTPException(404, "发件人不存在")
    name = f"{s.name}（{s.sender_name}）"
    db.delete(s)
    db.commit()
    add_log(db, u, "删除发件人", name)
    db.commit()
    return {"ok": True}
