from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import LabelTemplate, User
from ..schemas import LabelTemplateCreate, LabelTemplateUpdate, LabelTemplateOut
from ..deps import get_current_user

router = APIRouter(prefix="/api/label-templates", tags=["label-templates"])

VALID_TYPES = ("goods", "logistics")


def _owned(db: Session, uid: int, tid: int) -> LabelTemplate | None:
    """查当前用户自己的模板（账号隔离）"""
    return db.query(LabelTemplate).filter(
        LabelTemplate.id == tid, LabelTemplate.user_id == uid
    ).first()


def _clear_default(db: Session, uid: int, ltype: str, except_id: int | None = None):
    """同类型其它模板 is_default 全部置 false"""
    q = db.query(LabelTemplate).filter(
        LabelTemplate.user_id == uid, LabelTemplate.type == ltype, LabelTemplate.is_default.is_(True)
    )
    if except_id is not None:
        q = q.filter(LabelTemplate.id != except_id)
    for t in q.all():
        t.is_default = False


@router.get("")
def list_templates(
    type: str | None = None,
    db: Session = Depends(get_db),
    _u: User = Depends(get_current_user),
):
    """当前用户某类型（或不限）模板列表"""
    q = db.query(LabelTemplate).filter(LabelTemplate.user_id == _u.id)
    if type:
        q = q.filter(LabelTemplate.type == type)
    items = [LabelTemplateOut.model_validate(t) for t in q.order_by(LabelTemplate.id).all()]
    return items


@router.get("/default")
def get_default(
    type: str = "goods",
    db: Session = Depends(get_db),
    _u: User = Depends(get_current_user),
):
    """当前用户该类型默认模板，无则返回 null"""
    t = db.query(LabelTemplate).filter(
        LabelTemplate.user_id == _u.id,
        LabelTemplate.type == type,
        LabelTemplate.is_default.is_(True),
    ).first()
    return LabelTemplateOut.model_validate(t) if t else None


@router.post("")
def create_template(
    body: LabelTemplateCreate,
    db: Session = Depends(get_db),
    u: User = Depends(get_current_user),
):
    """新建模板；is_default=true 时同类型其它模板 is_default 全部置 false"""
    if not body.name.strip():
        raise HTTPException(400, "模板名不能为空")
    if body.type not in VALID_TYPES:
        raise HTTPException(400, "模板类型必须为 goods 或 logistics")
    if body.is_default:
        _clear_default(db, u.id, body.type)
    t = LabelTemplate(
        user_id=u.id,
        name=body.name.strip(),
        type=body.type,
        data=body.data or "{}",
        is_default=body.is_default,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return LabelTemplateOut.model_validate(t)


@router.put("/{tid}")
def update_template(
    tid: int,
    body: LabelTemplateUpdate,
    db: Session = Depends(get_db),
    u: User = Depends(get_current_user),
):
    """更新本人模板；is_default=true 规则同上"""
    t = _owned(db, u.id, tid)
    if not t:
        raise HTTPException(404, "模板不存在或无权操作")
    if body.name is not None:
        if not body.name.strip():
            raise HTTPException(400, "模板名不能为空")
        t.name = body.name.strip()
    if body.data is not None:
        t.data = body.data
    if body.is_default:
        _clear_default(db, u.id, t.type, except_id=t.id)
        t.is_default = True
    db.commit()
    db.refresh(t)
    return LabelTemplateOut.model_validate(t)


@router.delete("/{tid}")
def delete_template(
    tid: int,
    db: Session = Depends(get_db),
    u: User = Depends(get_current_user),
):
    """删除本人模板"""
    t = _owned(db, u.id, tid)
    if not t:
        raise HTTPException(404, "模板不存在或无权操作")
    db.delete(t)
    db.commit()
    return {"ok": True}
