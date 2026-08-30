# -*- coding: utf-8 -*-
"""库存分析模块：库存总览 + 分类分布 + 库存排名 + 畅销/滞销 + 低库存预警 + 出入库趋势
- 登录用户可见（get_current_user），不做角色限制
- 全部基于 Sku.stock / StockLog 现有数据计算
- 低库存阈值：SKU 无独立预警字段，统一使用全局阈值（GLOBAL_LOW_STOCK_THRESHOLD）
- 滞销判定：当前有库存且最近一次出库距今超过 STALE_DAYS 天（含从未出库，按建档时间）
- 畅销金额口径：出库件数 × 当前 SKU 售价（流水无单价快照，按现价估算）
"""
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..database import get_db
from ..deps import get_current_user
from ..models import Category, Sku, Spu, StockLog, User

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

GLOBAL_LOW_STOCK_THRESHOLD = 10   # 低库存预警阈值（SKU 无预警字段，全局统一）
STALE_DAYS = 30                   # 滞销判定天数


def _display_name(spu, sku) -> str:
    base = spu.name if spu else "未知商品"
    if sku and sku.spec_name and sku.spec_name not in ("默认", ""):
        base += "[" + sku.spec_name + "]"
    return base


def _load_spu_map(db):
    return {s.id: s for s in db.query(Spu).all()}


def _load_last_out(db):
    """sku_id -> 最近一次出库时间（datetime）"""
    last = {}
    for log in db.query(StockLog).filter(StockLog.log_type == "out").all():
        if not log.created_at:
            continue
        if log.sku_id not in last or log.created_at > last[log.sku_id]:
            last[log.sku_id] = log.created_at
    return last


# ================= 库存总览卡片 =================
@router.get("/summary")
def analysis_summary(db: Session = Depends(get_db),
                     _u: User = Depends(get_current_user)):
    skus = db.query(Sku).all()
    last_out = _load_last_out(db)
    today = datetime.utcnow().date()
    total_qty = 0
    total_value = 0.0
    low_count = 0
    stale_count = 0
    for sku in skus:
        qty = sku.stock or 0
        total_qty += qty
        total_value += qty * (sku.cost_price or 0)
        if qty < GLOBAL_LOW_STOCK_THRESHOLD:
            low_count += 1
        if qty > 0:
            last = last_out.get(sku.id)
            if last is None or (today - last.date()).days >= STALE_DAYS:
                stale_count += 1
    spu_count = len({s.spu_id for s in skus})
    return {
        "total_qty": total_qty,
        "total_value": round(total_value, 2),
        "sku_count": len(skus),
        "spu_count": spu_count,
        "low_stock_count": low_count,
        "stale_count": stale_count,
    }


# ================= 按分类统计库存 =================
@router.get("/category-stock")
def analysis_category_stock(db: Session = Depends(get_db),
                            _u: User = Depends(get_current_user)):
    skus = db.query(Sku).all()
    spu_map = _load_spu_map(db)
    cat_map = {c.id: c for c in db.query(Category).all()}
    total_qty = sum(s.stock or 0 for s in skus)
    groups = {}
    for sku in skus:
        spu = spu_map.get(sku.spu_id)
        cat = cat_map.get(spu.category_id) if spu else None
        name = cat.name if cat else "未分类"
        g = groups.setdefault(name, {"category_name": name, "sku_count": 0, "qty": 0, "value": 0.0})
        g["sku_count"] += 1
        g["qty"] += sku.stock or 0
        g["value"] += (sku.stock or 0) * (sku.cost_price or 0)
    rows = []
    for g in groups.values():
        g["value"] = round(g["value"], 2)
        g["ratio"] = round(g["qty"] / total_qty * 100, 1) if total_qty > 0 else 0
        rows.append(g)
    rows.sort(key=lambda x: (-x["qty"], x["category_name"]))
    return {"rows": rows, "total_qty": total_qty}


# ================= 库存 TOP N（价值/件数） =================
@router.get("/stock-rank")
def analysis_stock_rank(limit: int = 10, order: str = "value",
                        db: Session = Depends(get_db),
                        _u: User = Depends(get_current_user)):
    spu_map = _load_spu_map(db)
    rows = []
    for sku in db.query(Sku).all():
        rows.append({
            "sku_id": sku.id,
            "name": _display_name(spu_map.get(sku.spu_id), sku),
            "stock": sku.stock or 0,
            "value": round((sku.stock or 0) * (sku.cost_price or 0), 2),
        })
    if order == "qty":
        rows.sort(key=lambda x: (-x["stock"], x["name"]))
    else:
        rows.sort(key=lambda x: (-x["value"], x["name"]))
    return {"rows": rows[:max(1, limit)]}


# ================= 畅销 TOP N（近 N 天出库量） =================
@router.get("/selling-top")
def analysis_selling_top(limit: int = 10, days: int = 30,
                         db: Session = Depends(get_db),
                         _u: User = Depends(get_current_user)):
    today = datetime.utcnow().date()
    start = today - timedelta(days=max(1, days) - 1)
    start_dt = datetime(start.year, start.month, start.day)
    logs = db.query(StockLog).filter(
        StockLog.log_type == "out", StockLog.created_at >= start_dt).all()
    qty_map = defaultdict(int)
    for log in logs:
        if log.sku_id:
            qty_map[log.sku_id] += log.quantity or 0
    spu_map = _load_spu_map(db)
    rows = []
    for sku in db.query(Sku).all():
        qty = qty_map.get(sku.id, 0)
        if qty > 0:
            rows.append({
                "sku_id": sku.id,
                "name": _display_name(spu_map.get(sku.spu_id), sku),
                "qty": qty,
                "amount": round(qty * (sku.sale_price or 0), 2),
            })
    rows.sort(key=lambda x: (-x["qty"], x["name"]))
    return {"rows": rows[:max(1, limit)]}


# ================= 滞销榜 =================
@router.get("/slow-moving")
def analysis_slow_moving(limit: int = 10,
                         db: Session = Depends(get_db),
                         _u: User = Depends(get_current_user)):
    skus = db.query(Sku).all()
    last_out = _load_last_out(db)
    spu_map = _load_spu_map(db)
    today = datetime.utcnow().date()
    rows = []
    for sku in skus:
        if (sku.stock or 0) <= 0:
            continue
        last = last_out.get(sku.id)
        if last is None:
            base_day = sku.created_at.date() if sku.created_at else today
            days = max((today - base_day).days, 0)
            rows.append({
                "sku_id": sku.id,
                "name": _display_name(spu_map.get(sku.spu_id), sku),
                "stock": sku.stock or 0,
                "last_out": None,
                "days": days,
                "_key": (0, -days),   # 从未出库排最前，建档越早越前
            })
        else:
            days = max((today - last.date()).days, 0)
            rows.append({
                "sku_id": sku.id,
                "name": _display_name(spu_map.get(sku.spu_id), sku),
                "stock": sku.stock or 0,
                "last_out": last,
                "days": days,
                "_key": (1, -days),   # 最近出库越早越前
            })
    rows.sort(key=lambda x: x["_key"])
    for r in rows:
        r.pop("_key")
    return {"rows": rows[:max(1, limit)]}


# ================= 低库存预警 =================
@router.get("/low-stock")
def analysis_low_stock(limit: int = 50,
                       db: Session = Depends(get_db),
                       _u: User = Depends(get_current_user)):
    spu_map = _load_spu_map(db)
    rows = []
    for sku in db.query(Sku).all():
        if (sku.stock or 0) < GLOBAL_LOW_STOCK_THRESHOLD:
            rows.append({
                "sku_id": sku.id,
                "name": _display_name(spu_map.get(sku.spu_id), sku),
                "stock": sku.stock or 0,
                "cost_price": sku.cost_price or 0,
            })
    rows.sort(key=lambda x: (x["stock"], x["name"]))
    return {"rows": rows[:max(1, limit)]}


# ================= 近 N 天出入库趋势 =================
@router.get("/trend")
def analysis_trend(days: int = 30,
                   db: Session = Depends(get_db),
                   _u: User = Depends(get_current_user)):
    today = datetime.utcnow().date()
    n = max(1, days)
    buckets = {}
    for i in range(n - 1, -1, -1):
        d = today - timedelta(days=i)
        key = d.isoformat()
        buckets[key] = {"date": key, "in_qty": 0, "out_qty": 0}
    for log in db.query(StockLog).all():
        if not log.created_at:
            continue
        key = log.created_at.date().isoformat()
        if key in buckets:
            if log.log_type == "in":
                buckets[key]["in_qty"] += log.quantity or 0
            elif log.log_type == "out":
                buckets[key]["out_qty"] += log.quantity or 0
    return {"rows": list(buckets.values())}
