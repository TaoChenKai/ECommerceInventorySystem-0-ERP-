# -*- coding: utf-8 -*-
"""财务对账模块：销售毛利统计 + 渠道分组 + 销售单对账明细
- 毛利口径：每行毛利 = (实际售价 - 成本价) × 数量；单毛利 = 各行之和；毛利率 = 毛利 / 销售总额
- 成本价取确认出库时的快照（SaleItem.cost_price），旧单为空时回退取当前 SKU 成本
- 日期范围按 confirmed_at（确认出库时间）过滤
- 仅 boss / 管理员可访问
"""
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import SaleItem, SaleOrder, Sku, Spu
from ..deps import require_role
from ..models import User

router = APIRouter(prefix="/api/finance", tags=["finance"])


def _display_name(spu, sku):
    base = spu.name if spu else "未知商品"
    if sku and sku.spec_name and sku.spec_name not in ("默认", ""):
        base += "[" + sku.spec_name + "]"
    return base


def _item_cost(item: SaleItem) -> float:
    """行成本单价：优先快照，旧单无快照时回退当前 SKU 成本"""
    if item.cost_price is not None:
        return item.cost_price or 0
    if item.sku:
        return item.sku.cost_price or 0
    return 0


def _parse_day(s: str) -> datetime | None:
    if not s or not str(s).strip():
        return None
    try:
        return datetime.strptime(str(s).strip(), "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "日期格式应为 YYYY-MM-DD")


def _apply_range(q, start: str, end: str):
    start_dt = _parse_day(start)
    end_dt = _parse_day(end)
    if start_dt:
        q = q.filter(SaleOrder.confirmed_at >= start_dt.replace(hour=0, minute=0, second=0, microsecond=0))
    if end_dt:
        q = q.filter(SaleOrder.confirmed_at <= end_dt.replace(hour=23, minute=59, second=59, microsecond=999999))
    return q


def _order_finance(order: SaleOrder) -> dict:
    """计算单个销售单的财务汇总"""
    item_qty = 0
    sales_total = 0.0
    cost_total = 0.0
    for it in order.items:
        qty = it.quantity or 0
        item_qty += qty
        sales_total += qty * (it.unit_price or 0)
        cost_total += qty * _item_cost(it)
    sales_total = round(sales_total, 2)
    cost_total = round(cost_total, 2)
    gross_total = round(sales_total - cost_total, 2)
    gross_rate = round(gross_total / sales_total, 4) if sales_total > 0 else 0
    return {
        "item_qty": item_qty,
        "sales_total": sales_total,
        "cost_total": cost_total,
        "gross_total": gross_total,
        "gross_rate": gross_rate,
    }


# ================= 汇总卡片 =================
@router.get("/summary")
def finance_summary(start: str = "", end: str = "", channel_id: int = 0,
                    db: Session = Depends(get_db),
                    _u: User = Depends(require_role("boss", "admin"))):
    q = db.query(SaleOrder).filter(SaleOrder.status == "done")
    q = _apply_range(q, start, end)
    if channel_id > 0:
        q = q.filter(SaleOrder.channel_id == channel_id)
    orders = q.all()
    sales_total = cost_total = gross_total = 0.0
    order_count = len(orders)
    item_qty = 0
    for o in orders:
        f = _order_finance(o)
        sales_total += f["sales_total"]
        cost_total += f["cost_total"]
        gross_total += f["gross_total"]
        item_qty += f["item_qty"]
    sales_total = round(sales_total, 2)
    cost_total = round(cost_total, 2)
    gross_total = round(gross_total, 2)
    gross_rate = round(gross_total / sales_total, 4) if sales_total > 0 else 0
    return {
        "sales_total": sales_total,
        "cost_total": cost_total,
        "gross_total": gross_total,
        "gross_rate": gross_rate,
        "order_count": order_count,
        "item_qty": item_qty,
    }


# ================= 渠道分组统计 =================
@router.get("/by-channel")
def finance_by_channel(start: str = "", end: str = "",
                       db: Session = Depends(get_db),
                       _u: User = Depends(require_role("boss", "admin"))):
    q = db.query(SaleOrder).filter(SaleOrder.status == "done")
    q = _apply_range(q, start, end)
    orders = q.all()

    groups = {}  # key: 渠道名（None → 未指定渠道）
    for o in orders:
        name = o.channel.name if o.channel else None
        g = groups.setdefault(name, {
            "channel_name": name if name else "未指定渠道",
            "order_count": 0, "item_qty": 0,
            "sales_total": 0.0, "cost_total": 0.0, "gross_total": 0.0,
        })
        g["order_count"] += 1
        f = _order_finance(o)
        g["item_qty"] += f["item_qty"]
        g["sales_total"] += f["sales_total"]
        g["cost_total"] += f["cost_total"]
        g["gross_total"] += f["gross_total"]
    rows = []
    for g in groups.values():
        g["sales_total"] = round(g["sales_total"], 2)
        g["cost_total"] = round(g["cost_total"], 2)
        g["gross_total"] = round(g["gross_total"], 2)
        g["gross_rate"] = round(g["gross_total"] / g["sales_total"], 4) if g["sales_total"] > 0 else 0
        rows.append(g)
    rows.sort(key=lambda x: (-x["sales_total"], x["channel_name"]))
    return {"rows": rows}


# ================= 销售单对账明细列表（分页） =================
@router.get("/orders")
def finance_orders(start: str = "", end: str = "", channel_id: int = 0,
                   status: str = "", keyword: str = "", page: int = 1, page_size: int = 20,
                   db: Session = Depends(get_db),
                   _u: User = Depends(require_role("boss", "admin"))):
    if status not in ("draft", "done", "cancelled"):
        status = "done"  # 对账默认只看已确认出库的单
    q = db.query(SaleOrder).filter(SaleOrder.status == status)
    q = _apply_range(q, start, end)
    if channel_id > 0:
        q = q.filter(SaleOrder.channel_id == channel_id)
    if keyword.strip():
        kw = "%%%s%%" % keyword.strip()
        q = q.filter(or_(SaleOrder.order_no.like(kw), SaleOrder.buyer.like(kw)))
    total = q.count()
    rows = q.order_by(SaleOrder.confirmed_at.desc(), SaleOrder.id.desc()) \
        .offset((page - 1) * page_size).limit(page_size).all()
    items = []
    for o in rows:
        f = _order_finance(o)
        items.append({
            "id": o.id, "order_no": o.order_no,
            "confirmed_at": o.confirmed_at,
            "channel_id": o.channel_id,
            "channel_name": o.channel.name if o.channel else "",
            "buyer": o.buyer or "",
            "status": o.status,
            "invoice_status": o.invoice_status or "uninvoiced",
            "receipt_no": o.receipt_no or "",
            **f,
        })
    return {"total": total, "page": page, "page_size": page_size, "items": items}


# ================= 单个销售单对账详情（逐行货品） =================
@router.get("/orders/{oid}")
def finance_order_detail(oid: int, db: Session = Depends(get_db),
                         _u: User = Depends(require_role("boss", "admin"))):
    order = db.query(SaleOrder).filter(SaleOrder.id == oid).first()
    if not order:
        raise HTTPException(404, "销售单不存在")
    lines = []
    for it in order.items:
        cost_price = it.cost_price if it.cost_price is not None else (_item_cost(it) or None)
        qty = it.quantity or 0
        unit_price = it.unit_price or 0
        item_sales = round(qty * unit_price, 2)
        item_cost = round(qty * (cost_price or 0), 2)
        gross = round(item_sales - item_cost, 2)
        gross_rate = round(gross / item_sales, 4) if item_sales > 0 else 0
        sku = it.sku if it.sku_id else None
        spu = sku.spu if sku and sku.spu_id else None
        lines.append({
            "sku_id": it.sku_id,
            "sku_name": _display_name(spu, sku),
            "quantity": qty,
            "discount": it.discount or 0,
            "unit_price": unit_price,
            "cost_price": cost_price,
            "item_sales": item_sales,
            "item_cost": item_cost,
            "gross": gross,
            "gross_rate": gross_rate,
        })
    f = _order_finance(order)
    return {
        "id": order.id, "order_no": order.order_no,
        "channel_id": order.channel_id,
        "channel_name": order.channel.name if order.channel else "",
        "buyer": order.buyer or "",
        "remark": order.remark or "",
        "status": order.status,
        "confirmed_at": order.confirmed_at,
        "invoice_status": order.invoice_status or "uninvoiced",
        "invoice_no": order.invoice_no or "",
        "receipt_no": order.receipt_no or "",
        "operator": order.operator.nickname or order.operator.username if order.operator else "",
        **f,
        "lines": lines,
    }
