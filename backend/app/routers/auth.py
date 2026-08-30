from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import User, AuditLog
from ..schemas import TokenResponse, UserOut
from ..security import verify_password, create_access_token
from ..deps import get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])


def log_action(db: Session, user: User | None, action: str, detail: str = "", ip: str = ""):
    db.add(AuditLog(
        user_id=user.id if user else None,
        username=user.username if user else "",
        action=action,
        detail=detail,
        ip=ip,
    ))
    db.commit()


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.password_hash):
        raise HTTPException(status_code=400, detail="用户名或密码错误")
    if not user.is_active:
        raise HTTPException(status_code=400, detail="账号已被停用，请联系老板")
    token = create_access_token({"sub": str(user.id)})
    log_action(db, user, "登录")
    return TokenResponse(access_token=token, user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)):
    return user
