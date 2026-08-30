# -*- coding: utf-8 -*-
"""销售出库模块：销售单(草稿) + 扫码选品 + 整单确认出库（单事务减库存+写流水）
预留开票 / 打回单扩展字段：invoice_no / invoice_status / receipt_no
"""
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import AuditLog, Channel, SaleItem, SaleOrder, Sku, Spu, StockLog, User
from ..schemas import SaleCreate, SaleUpdate
from ..deps import get_current_user

router = APIRouter(prefix="/api", tags=["sales"])


def add_log(db: Session, user: User, action: str, detail: str = ""):
    db.add(AuditLog(user_id=user.id, username=user.username, action=action, detail=detail))


def _display_name(spu, sku):
    base = spu.name
    if sku.spec_name and sku.spec_name not in ("默认", ""):
        base += "[" + sku.spec_name + "]"
    return base


def _gen_order_no(db: Session) -> str:
    prefix = "S" + datetime.now().strftime("%Y%m%d")
    last = (db.query(SaleOrder)
            .filter(SaleOrder.order_no.like(prefix + "%"))
            .order_by(SaleOrder.id.desc()).first())
    seq = 1
    if last:
        try:
            seq = int(last.order_no[len(prefix):]) + 1
        except (ValueError, TypeError):
            seq = 1
    return "%s%03d" % (prefix, seq)


def _item_to_out(item: SaleItem):
    """组装明细输出：带上展示名 / 条码 / 当前库存（经 sku 关联）"""
    sku_name = ""
    barcode = ""
    cur_stock = None
    spec_name = ""
    if item.sku_id and item.sku:
        sku = item.sku
        barcode = sku.barcode or ""
        spec_name = sku.spec_name or ""
        cur_stock = sku.stock or 0
        if sku.spu_id and sku.spu:
            sku_name = _display_name(sku.spu, sku)
    return {
        "id": item.id, "order_id": item.order_id,
        "sku_id": item.sku_id,
        "quantity": item.quantity or 1,
        "discount": item.discount or 0,
        "unit_price": item.unit_price or 0,
        "sku_name": sku_name, "spec_name": spec_name, "barcode": barcode,
        "cur_stock": cur_stock,
        "created_at": item.created_at,
    }


def _order_to_out(order: SaleOrder) -> dict:
    total_qty = sum((i.quantity or 0) for i in order.items)
    total_amount = round(sum(((i.quantity or 0) * (i.unit_price or 0)) for i in order.items), 2)
    return {
        "id": order.id, "order_no": order.order_no,
        "channel_id": order.channel_id,
        "channel_name": order.channel.name if order.channel else "",
        "buyer": order.buyer or "",
        "remark": order.remark or "",
        "status": order.status,
        "operator": order.operator.nickname or order.operator.username if order.operator else "",
        "confirmed_at": order.confirmed_at,
        "invoice_no": order.invoice_no or "",
        "invoice_status": order.invoice_status or "uninvoiced",
        "receipt_no": order.receipt_no or "",
        "created_at": order.created_at,
        "items": [_item_to_out(i) for i in order.items],
        "total_qty": total_qty, "total_amount": total_amount,
    }


def _get_or_create_channel(db: Session, body) -> int | None:
    """按 body.channel_id 或 body.channel_name 定位/创建渠道，返回 id"""
    if body.channel_id:
        return body.channel_id
    name = (body.channel_name or "").strip()
    if not name:
        return None
    c = db.query(Channel).filter(Channel.name == name).first()
    if not c:
        c = Channel(name=name)
        db.add(c)
        db.flush()
    return c.id


def _sync_items(db: Session, order: SaleOrder, body_items: list):
    """全量同步销售明细：保留提交中带 id 的、删掉未提交的、新增无 id 的"""
    submitted = [i.id for i in body_items if i.id]
    for old in list(order.items):
        if old.id not in submitted:
            db.delete(old)
    for bi in body_items:
        if bi.id:
            target = db.query(SaleItem).filter(
                SaleItem.id == bi.id, SaleItem.order_id == order.id).first()
            if not target:
                continue
            target.sku_id = bi.sku_id
            target.quantity = bi.quantity or 1
            target.discount = bi.discount or 0
            target.unit_price = bi.unit_price or 0
        else:
            order.items.append(SaleItem(
                sku_id=bi.sku_id,
                quantity=bi.quantity or 1,
                discount=bi.discount or 0,
                unit_price=bi.unit_price or 0,
            ))


# ================= 销售单 CRUD =================
@router.post("/sales")
def create_sale(body: SaleCreate, db: Session = Depends(get_db),
                u: User = Depends(get_current_user)):
    channel_id = _get_or_create_channel(db, body)
    order = SaleOrder(
        order_no=_gen_order_no(db),
        channel_id=channel_id,
        buyer=(body.buyer or "").strip(),
        remark=(body.remark or "").strip(),
        status="draft",
        operator_id=u.id,
    )
    db.add(order)
    db.flush()
    _sync_items(db, order, body.items)
    db.commit()
    db.refresh(order)
    add_log(db, u, "新建销售单", order.order_no)
    db.commit()
    return _order_to_out(order)


@router.get("/sales")
def list_sales(status: str = "", keyword: str = "", page: int = 1,
               page_size: int = 20, db: Session = Depends(get_db),
               _u: User = Depends(get_current_user)):
    q = db.query(SaleOrder)
    if status in ("draft", "done", "cancelled"):
        q = q.filter(SaleOrder.status == status)
    if keyword.strip():
        kw = "%%%s%%" % keyword.strip()
        q = q.outerjoin(Channel).filter(
            or_(SaleOrder.order_no.like(kw), SaleOrder.buyer.like(kw),
                Channel.name.like(kw)))
    total = q.count()
    rows = q.order_by(SaleOrder.created_at.desc(), SaleOrder.id.desc()) \
            .offset((page - 1) * page_size).limit(page_size).all()
    items = [_order_to_out(o) for o in rows]
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get("/sales/{sid}")
def get_sale(sid: int, db: Session = Depends(get_db), _u: User = Depends(get_current_user)):
    order = db.query(SaleOrder).filter(SaleOrder.id == sid).first()
    if not order:
        raise HTTPException(404, "销售单不存在")
    return _order_to_out(order)


@router.put("/sales/{sid}")
def update_sale(sid: int, body: SaleUpdate, db: Session = Depends(get_db),
                u: User = Depends(get_current_user)):
    order = db.query(SaleOrder).filter(SaleOrder.id == sid).first()
    if not order:
        raise HTTPException(404, "销售单不存在")
    if order.status != "draft":
        raise HTTPException(400, "只有草稿状态的销售单可以修改")
    order.channel_id = _get_or_create_channel(db, body)
    order.buyer = (body.buyer or "").strip()
    order.remark = (body.remark or "").strip()
    _sync_items(db, order, body.items)
    db.commit()
    db.refresh(order)
    add_log(db, u, "修改销售单", order.order_no)
    db.commit()
    return _order_to_out(order)


@router.delete("/sales/{sid}")
def delete_sale(sid: int, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    order = db.query(SaleOrder).filter(SaleOrder.id == sid).first()
    if not order:
        raise HTTPException(404, "销售单不存在")
    if order.status != "draft":
        raise HTTPException(400, "已完成的销售单不能删除")
    no = order.order_no
    db.delete(order)
    db.commit()
    add_log(db, u, "删除销售单", no)
    db.commit()
    return {"ok": True}


# ================= 确认出库（单事务：校验库存 → 减库存 → 写流水 → 置完成） =================
@router.post("/sales/{sid}/confirm")
def confirm_sale(sid: int, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    order = db.query(SaleOrder).filter(SaleOrder.id == sid).first()
    if not order:
        raise HTTPException(404, "销售单不存在")
    if order.status != "draft":
        raise HTTPException(400, "该销售单已出库，请勿重复确认")
    if not order.items:
        raise HTTPException(400, "销售单还没有任何明细，请先扫码添加商品")
    channel_name = order.channel.name if order.channel else ""
    try:
        for item in order.items:
            qty = item.quantity or 0
            if qty <= 0:
                raise HTTPException(400, "销售数量必须大于0")
            sku = db.query(Sku).filter(Sku.id == item.sku_id).first()
            if not sku:
                raise HTTPException(404, "明细中的规格不存在，请检查后重试")
            if (sku.stock or 0) < qty:
                spu = db.query(Spu).filter(Spu.id == sku.spu_id).first()
                raise HTTPException(400, "库存不足：%s 当前库存 %d，本次需出 %d"
                                         % (_display_name(spu, sku) if spu else "该商品",
                                            sku.stock or 0, qty))
            sku.stock = (sku.stock or 0) - qty
            item.cost_price = sku.cost_price or 0   # 成本价快照：锁定确认时点成本，保证历史对账不随档案成本漂移
            remark = "销售出库 %s%s" % (order.order_no,
                                       ("·" + channel_name) if channel_name else "")
            db.add(StockLog(sku_id=sku.id, channel_id=order.channel_id,
                            log_type="out", quantity=qty,
                            operator_id=u.id, remark=remark))
        order.status = "done"
        order.confirmed_at = datetime.utcnow()
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(500, "出库失败，已回滚，请检查明细数据")
    add_log(db, u, "销售出库", "%s 共%d项" % (order.order_no, len(order.items)))
    db.commit()
    return {"ok": True, "order_no": order.order_no, "items": len(order.items)}
