# -*- coding: utf-8 -*-
"""采购入库模块：供应商管理 + 采购单(草稿) + 扫码建档 + 整单确认统一入库"""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (AuditLog, Category, ProductImage, PurchaseItem,
                      PurchaseOrder, Sku, Spu, StockLog, Supplier, Unit,
                      User, WeightUnit)
from ..schemas import (PurchaseCreate, PurchaseUpdate, SupplierCreate)
from ..deps import get_current_user

router = APIRouter(prefix="/api", tags=["purchase"])


def add_log(db: Session, user: User, action: str, detail: str = ""):
    db.add(AuditLog(user_id=user.id, username=user.username, action=action, detail=detail))


def _ensure_unit(db: Session, model, name: str):
    """单位/重量单位名若不在字典中则自动补录"""
    if not name:
        return
    if not db.query(model).filter(model.name == name.strip()).first():
        db.add(model(name=name.strip()))


def _display_name(spu, sku):
    base = spu.name
    if sku.spec_name and sku.spec_name not in ("默认", ""):
        base += "[" + sku.spec_name + "]"
    return base


def _gen_order_no(db: Session) -> str:
    prefix = "P" + datetime.now().strftime("%Y%m%d")
    last = (db.query(PurchaseOrder)
            .filter(PurchaseOrder.order_no.like(prefix + "%"))
            .order_by(PurchaseOrder.id.desc()).first())
    seq = 1
    if last:
        try:
            seq = int(last.order_no[len(prefix):]) + 1
        except (ValueError, TypeError):
            seq = 1
    return "%s%03d" % (prefix, seq)


def _item_to_out(item: PurchaseItem, spu=None, sku=None):
    """组装明细输出：已建档商品带上展示名/条码/现有库存"""
    sku_name = item.draft_name or ""
    barcode = item.draft_barcode or ""
    cur_stock = None
    if item.status == "existing" and item.sku_id:
        if sku is None:
            sku = item.sku
        if sku:
            barcode = sku.barcode or ""
            cur_stock = sku.stock or 0
            if spu is None and sku.spu_id:
                spu = sku.spu if sku.spu else None
            if spu is not None:
                sku_name = _display_name(spu, sku)
    try:
        images = json.loads(item.draft_images or "[]")
    except Exception:
        images = []
    return {
        "id": item.id, "order_id": item.order_id,
        "spu_id": item.spu_id, "sku_id": item.sku_id,
        "status": item.status, "quantity": item.quantity or 1,
        "unit_price": item.unit_price or 0,
        "sku_name": sku_name, "barcode": barcode, "cur_stock": cur_stock,
        "draft_name": item.draft_name or "", "draft_code": item.draft_code or "",
        "draft_spec": item.draft_spec or "", "draft_barcode": item.draft_barcode or "",
        "draft_category": item.draft_category or "", "draft_unit": item.draft_unit or "件",
        "draft_weight": item.draft_weight or 0,
        "draft_weight_unit": item.draft_weight_unit or "千克",
        "draft_remark": item.draft_remark or "", "draft_images": images,
        "created_at": item.created_at,
    }


def _order_to_out(order: PurchaseOrder) -> dict:
    total_qty = sum((i.quantity or 1) for i in order.items)
    total_amount = round(sum(((i.quantity or 1) * (i.unit_price or 0)) for i in order.items), 2)
    return {
        "id": order.id, "order_no": order.order_no,
        "supplier_id": order.supplier_id,
        "supplier_name": order.supplier.name if order.supplier else "",
        "purchase_method": order.purchase_method or "",
        "order_date": order.order_date or "",
        "remark": order.remark or "",
        "status": order.status,
        "operator": order.operator.nickname or order.operator.username if order.operator else "",
        "confirmed_at": order.confirmed_at,
        "created_at": order.created_at,
        "items": [_item_to_out(i) for i in order.items],
        "total_qty": total_qty, "total_amount": total_amount,
    }


# ================= 供应商 / 采购商 =================
@router.get("/suppliers")
def list_suppliers(db: Session = Depends(get_db), _u: User = Depends(get_current_user)):
    rows = db.query(Supplier).order_by(Supplier.id).all()
    return [{"id": s.id, "name": s.name, "contact": s.contact or "",
             "phone": s.phone or "", "remark": s.remark or "", "created_at": s.created_at}
            for s in rows]


@router.post("/suppliers")
def create_supplier(body: SupplierCreate, db: Session = Depends(get_db),
                    u: User = Depends(get_current_user)):
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "供应商名称不能为空")
    if db.query(Supplier).filter(Supplier.name == name).first():
        raise HTTPException(400, f"供应商「{name}」已存在")
    s = Supplier(name=name, contact=body.contact.strip(), phone=body.phone.strip(),
                 remark=body.remark.strip())
    db.add(s)
    db.commit()
    db.refresh(s)
    add_log(db, u, "新增供应商", name)
    db.commit()
    return {"id": s.id, "name": s.name, "contact": s.contact or "",
            "phone": s.phone or "", "remark": s.remark or "", "created_at": s.created_at}


@router.put("/suppliers/{sid}")
def update_supplier(sid: int, body: SupplierCreate, db: Session = Depends(get_db),
                    u: User = Depends(get_current_user)):
    s = db.query(Supplier).filter(Supplier.id == sid).first()
    if not s:
        raise HTTPException(404, "供应商不存在")
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "供应商名称不能为空")
    dup = db.query(Supplier).filter(Supplier.name == name, Supplier.id != sid).first()
    if dup:
        raise HTTPException(400, f"供应商「{name}」已存在")
    old = s.name
    s.name = name
    s.contact = body.contact.strip()
    s.phone = body.phone.strip()
    s.remark = body.remark.strip()
    db.commit()
    add_log(db, u, "修改供应商", f"{old} -> {name}")
    db.commit()
    return {"id": s.id, "name": s.name, "contact": s.contact or "",
            "phone": s.phone or "", "remark": s.remark or "", "created_at": s.created_at}


@router.delete("/suppliers/{sid}")
def delete_supplier(sid: int, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    s = db.query(Supplier).filter(Supplier.id == sid).first()
    if not s:
        raise HTTPException(404, "供应商不存在")
    if db.query(PurchaseOrder).filter(PurchaseOrder.supplier_id == sid).first():
        raise HTTPException(400, "该供应商已有采购单，不能删除")
    name = s.name
    db.delete(s)
    db.commit()
    add_log(db, u, "删除供应商", name)
    db.commit()
    return {"ok": True}


def _get_or_create_supplier(db: Session, body) -> int | None:
    """按 body.supplier_id 或 body.supplier_name 定位/创建供应商，返回 id"""
    if body.supplier_id:
        return body.supplier_id
    name = (body.supplier_name or "").strip()
    if not name:
        return None
    s = db.query(Supplier).filter(Supplier.name == name).first()
    if not s:
        s = Supplier(name=name)
        db.add(s)
        db.flush()
    return s.id


# ================= 采购单 =================
def _sync_items(db: Session, order: PurchaseOrder, body_items: list):
    """全量同步采购明细：保留提交中带 id 的、删掉未提交的、新增无 id 的"""
    submitted = [i.id for i in body_items if i.id]
    for old in list(order.items):
        if old.id not in submitted:
            db.delete(old)
    for bi in body_items:
        draft_images = bi.draft_images if isinstance(bi.draft_images, list) else []
        if bi.id:
            target = db.query(PurchaseItem).filter(
                PurchaseItem.id == bi.id, PurchaseItem.order_id == order.id).first()
            if not target:
                continue
            target.spu_id = bi.spu_id
            target.sku_id = bi.sku_id
            target.status = bi.status or "existing"
            target.quantity = bi.quantity or 1
            target.unit_price = bi.unit_price or 0
            target.draft_name = bi.draft_name or ""
            target.draft_code = bi.draft_code or ""
            target.draft_spec = bi.draft_spec or ""
            target.draft_barcode = bi.draft_barcode or ""
            target.draft_category = bi.draft_category or ""
            target.draft_unit = bi.draft_unit or "件"
            target.draft_weight = bi.draft_weight or 0
            target.draft_weight_unit = bi.draft_weight_unit or "千克"
            target.draft_remark = bi.draft_remark or ""
            target.draft_images = json.dumps(draft_images, ensure_ascii=False)
        else:
            order.items.append(PurchaseItem(
                spu_id=bi.spu_id, sku_id=bi.sku_id,
                status=bi.status or "existing",
                quantity=bi.quantity or 1, unit_price=bi.unit_price or 0,
                draft_name=bi.draft_name or "", draft_code=bi.draft_code or "",
                draft_spec=bi.draft_spec or "", draft_barcode=bi.draft_barcode or "",
                draft_category=bi.draft_category or "", draft_unit=bi.draft_unit or "件",
                draft_weight=bi.draft_weight or 0,
                draft_weight_unit=bi.draft_weight_unit or "千克",
                draft_remark=bi.draft_remark or "",
                draft_images=json.dumps(draft_images, ensure_ascii=False),
            ))


@router.post("/purchases")
def create_purchase(body: PurchaseCreate, db: Session = Depends(get_db),
                    u: User = Depends(get_current_user)):
    supplier_id = _get_or_create_supplier(db, body)
    order = PurchaseOrder(
        order_no=_gen_order_no(db),
        supplier_id=supplier_id,
        purchase_method=(body.purchase_method or "").strip(),
        order_date=(body.order_date or "").strip(),
        remark=(body.remark or "").strip(),
        status="draft",
        operator_id=u.id,
    )
    db.add(order)
    db.flush()
    _sync_items(db, order, body.items)
    db.commit()
    db.refresh(order)
    add_log(db, u, "新建采购单", order.order_no)
    db.commit()
    return _order_to_out(order)


@router.get("/purchases")
def list_purchases(status: str = "", keyword: str = "", page: int = 1,
                   page_size: int = 20, db: Session = Depends(get_db),
                   _u: User = Depends(get_current_user)):
    q = db.query(PurchaseOrder)
    if status in ("draft", "done", "cancelled"):
        q = q.filter(PurchaseOrder.status == status)
    if keyword.strip():
        kw = "%%%s%%" % keyword.strip()
        q = q.outerjoin(Supplier).filter(
            or_(PurchaseOrder.order_no.like(kw), Supplier.name.like(kw)))
    total = q.count()
    rows = q.order_by(PurchaseOrder.created_at.desc(), PurchaseOrder.id.desc()) \
            .offset((page - 1) * page_size).limit(page_size).all()
    items = []
    for o in rows:
        items.append(_order_to_out(o))
    return {"total": total, "page": page, "page_size": page_size, "items": items}


@router.get("/purchases/{pid}")
def get_purchase(pid: int, db: Session = Depends(get_db), _u: User = Depends(get_current_user)):
    order = db.query(PurchaseOrder).filter(PurchaseOrder.id == pid).first()
    if not order:
        raise HTTPException(404, "采购单不存在")
    return _order_to_out(order)


@router.put("/purchases/{pid}")
def update_purchase(pid: int, body: PurchaseUpdate, db: Session = Depends(get_db),
                    u: User = Depends(get_current_user)):
    order = db.query(PurchaseOrder).filter(PurchaseOrder.id == pid).first()
    if not order:
        raise HTTPException(404, "采购单不存在")
    if order.status != "draft":
        raise HTTPException(400, "只有草稿状态的采购单可以修改")
    order.supplier_id = _get_or_create_supplier(db, body)
    order.purchase_method = (body.purchase_method or "").strip()
    order.order_date = (body.order_date or "").strip()
    order.remark = (body.remark or "").strip()
    _sync_items(db, order, body.items)
    db.commit()
    db.refresh(order)
    add_log(db, u, "修改采购单", order.order_no)
    db.commit()
    return _order_to_out(order)


@router.delete("/purchases/{pid}")
def delete_purchase(pid: int, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    order = db.query(PurchaseOrder).filter(PurchaseOrder.id == pid).first()
    if not order:
        raise HTTPException(404, "采购单不存在")
    if order.status != "draft":
        raise HTTPException(400, "已入库的采购单不能删除")
    no = order.order_no
    db.delete(order)
    db.commit()
    add_log(db, u, "删除采购单", no)
    db.commit()
    return {"ok": True}


# ================= 确认入库（统一建档 + 加库存 + 写流水，单事务） =================
def _create_spu_from_draft(db: Session, item: PurchaseItem):
    """把待建档草稿创建为 SPU+SKU，返回 (spu, sku)"""
    code = (item.draft_code or "").strip()
    barcode = (item.draft_barcode or "").strip()
    name = (item.draft_name or "").strip()
    if not name:
        raise HTTPException(400, "有待建档商品未填写名称，请补全后再入库")
    if code and db.query(Spu).filter(Spu.code == code).first():
        raise HTTPException(400, f"商品编号 {code} 已存在，请在商品档案中核对")
    if barcode and db.query(Sku).filter(Sku.barcode == barcode).first():
        raise HTTPException(400, f"条码 {barcode} 已被其他商品使用，请检查")
    # 分类：按名查找，没有则自动新建
    category_id = None
    cat_name = (item.draft_category or "").strip()
    if cat_name:
        cat = db.query(Category).filter(Category.name == cat_name).first()
        if not cat:
            cat = Category(name=cat_name)
            db.add(cat)
            db.flush()
        category_id = cat.id
    spu = Spu(
        name=name, code=code, category_id=category_id,
        unit=(item.draft_unit or "件").strip() or "件",
        weight=item.draft_weight or 0,
        weight_unit=(item.draft_weight_unit or "千克").strip() or "千克",
        remark=(item.draft_remark or "").strip(),
    )
    sku = Sku(
        spec_name=(item.draft_spec or "").strip() or "默认",
        sku_code=code or name,          # 单规格用编号/名称兜底，便于后续扫描
        barcode=barcode,
        cost_price=item.unit_price or 0,
        sale_price=0,
        stock=0,
    )
    spu.skus.append(sku)
    db.add(spu)
    db.flush()
    # 图片（采购建档默认全部作为主图）
    try:
        imgs = json.loads(item.draft_images or "[]")
    except Exception:
        imgs = []
    for idx, url in enumerate(imgs):
        if url and str(url).strip():
            spu.images.append(ProductImage(img_type="main", url=str(url).strip(), sort=idx))
    _ensure_unit(db, Unit, spu.unit)
    _ensure_unit(db, WeightUnit, spu.weight_unit)
    return spu, sku


@router.post("/purchases/{pid}/confirm")
def confirm_purchase(pid: int, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    order = db.query(PurchaseOrder).filter(PurchaseOrder.id == pid).first()
    if not order:
        raise HTTPException(404, "采购单不存在")
    if order.status != "draft":
        raise HTTPException(400, "该采购单已入库，请勿重复确认")
    if not order.items:
        raise HTTPException(400, "采购单还没有任何明细，请先扫码添加商品")
    supplier_name = order.supplier.name if order.supplier else ""
    try:
        for item in order.items:
            if item.status == "draft" or not item.sku_id:
                # 待建档 → 创建商品档案
                _, sku = _create_spu_from_draft(db, item)
                item.spu_id = sku.spu_id
                item.sku_id = sku.id
                item.status = "existing"
            sku = db.query(Sku).filter(Sku.id == item.sku_id).first()
            if not sku:
                raise HTTPException(404, "明细中的规格不存在，请检查后重试")
            qty = item.quantity or 1
            if qty <= 0:
                raise HTTPException(400, "采购数量必须大于0")
            sku.stock = (sku.stock or 0) + qty
            if item.unit_price and item.unit_price > 0:
                sku.cost_price = item.unit_price   # 入库时以本次采购价更新成本价
            spu = db.query(Spu).filter(Spu.id == sku.spu_id).first()
            remark = "采购入库 %s%s" % (order.order_no,
                                        ("·" + supplier_name) if supplier_name else "")
            db.add(StockLog(sku_id=sku.id, channel_id=None, log_type="in",
                            quantity=qty, operator_id=u.id, remark=remark))
        order.status = "done"
        order.confirmed_at = datetime.utcnow()
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(500, "入库失败，已回滚，请检查明细数据")
    add_log(db, u, "采购入库", "%s 共%d项" % (order.order_no, len(order.items)))
    db.commit()
    return {"ok": True, "order_no": order.order_no, "items": len(order.items)}
