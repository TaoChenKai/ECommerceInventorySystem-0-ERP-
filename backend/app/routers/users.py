from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, AuditLog
from ..schemas import UserCreate, UserOut
from ..security import hash_password
from ..deps import get_current_user, require_role

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db), _op: User = Depends(require_role("boss", "admin"))):
    return db.query(User).order_by(User.id).all()


@router.post("", response_model=UserOut)
def create_user(body: UserCreate, db: Session = Depends(get_db), op: User = Depends(require_role("boss", "admin"))):
    if body.role not in ("boss", "admin", "staff"):
        raise HTTPException(status_code=400, detail="角色只能是 boss / admin / staff")
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    if body.role == "boss":
        raise HTTPException(status_code=400, detail="老板账号只有一个，不能通过此方式创建")
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        nickname=body.nickname,
        role=body.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.add(AuditLog(user_id=op.id, username=op.username, action="创建账号",
                    detail=f"用户名:{body.username} 昵称:{body.nickname} 角色:{body.role}"))
    db.commit()
    return user


@router.delete("/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), boss: User = Depends(require_role("boss"))):
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="账号不存在")
    if target.role == "boss":
        raise HTTPException(status_code=400, detail="不能删除老板账号")
    if target.id == boss.id:
        raise HTTPException(status_code=400, detail="不能删除自己的账号")
    db.delete(target)
    db.commit()
    db.add(AuditLog(user_id=boss.id, username=boss.username, action="删除账号", detail=f"用户名:{target.username}"))
    db.commit()
    return {"ok": True}
