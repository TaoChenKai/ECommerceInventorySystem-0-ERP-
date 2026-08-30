# -*- coding: utf-8 -*-
"""第三段：渠道管理 + 扫码出入库 + 库存流水 + 渠道统计"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, or_
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import Channel, StockLog, Sku, Spu, User
from ..schemas import ChannelCreate, StockOp
from ..deps import get_current_user, require_role

router = APIRouter(prefix="/api", tags=["stock"])


def add_log(db, user, action, detail):
    from ..models import AuditLog
    db.add(AuditLog(user_id=user.id, username=user.username, action=action, detail=detail))


def _sku_display_name(spu, sku):
    base = spu.name
    if sku.spec_name and sku.spec_name not in ("默认", ""):
        base += "[" + sku.spec_name + "]"
    return base


# ============ 渠道管理 ============
@router.get("/channels")
def list_channels(db: Session = Depends(get_db), _u: User = Depends(get_current_user)):
    chs = db.query(Channel).order_by(Channel.id).all()
    return [{"id": c.id, "name": c.name, "channel_type": c.channel_type,
             "remark": c.remark or "", "created_at": c.created_at} for c in chs]


@router.post("/channels")
def create_channel(body: ChannelCreate, db: Session = Depends(get_db),
                   u: User = Depends(require_role("boss", "admin"))):
    name = body.name.strip()
    if not name:
        raise HTTPException(400, "渠道名称不能为空")
    if db.query(Channel).filter(Channel.name == name).first():
        raise HTTPException(400, "渠道已存在")
    c = Channel(name=name, channel_type=body.channel_type, remark=body.remark)
    db.add(c)
    db.commit()
    db.refresh(c)
    add_log(db, u, "新增渠道", name)
    db.commit()
    return {"id": c.id, "name": c.name, "channel_type": c.channel_type,
            "remark": c.remark or "", "created_at": c.created_at}


@router.put("/channels/{cid}")
def update_channel(cid: int, body: ChannelCreate, db: Session = Depends(get_db),
                   u: User = Depends(require_role("boss", "admin"))):
    c = db.query(Channel).filter(Channel.id == cid).first()
    if not c:
        raise HTTPException(404, "渠道不存在")
    c.name = body.name.strip()
    c.channel_type = body.channel_type
    c.remark = body.remark
    db.commit()
    add_log(db, u, "编辑渠道", c.name)
    db.commit()
    return {"id": c.id, "name": c.name, "channel_type": c.channel_type,
            "remark": c.remark or "", "created_at": c.created_at}


@router.delete("/channels/{cid}")
def delete_channel(cid: int, db: Session = Depends(get_db),
                   u: User = Depends(require_role("boss", "admin"))):
    c = db.query(Channel).filter(Channel.id == cid).first()
    if not c:
        raise HTTPException(404, "渠道不存在")
    if db.query(StockLog).filter(StockLog.channel_id == cid).count() > 0:
        raise HTTPException(400, "该渠道已有出入库流水，不能删除")
    name = c.name
    db.delete(c)
    db.commit()
    add_log(db, u, "删除渠道", name)
    db.commit()
    return {"ok": True}


# ============ 扫码解析 ============
def _resolve_sku(db, code: str, sku_id: int | None):
    if sku_id:
        sku = db.query(Sku).filter(Sku.id == sku_id).first()
        if not sku:
            raise HTTPException(404, "规格不存在")
        return sku
    code = (code or "").strip()
    if not code:
        raise HTTPException(400, "请提供条码/SKU编码/商品编号")
    # 1) 精确条码
    sku = db.query(Sku).filter(Sku.barcode == code).first()
    if sku:
        return sku
    # 2) 精确SKU编码
    sku = db.query(Sku).filter(Sku.sku_code == code).first()
    if sku:
        return sku
    # 3) 商品编号（SPU code）：单规格直接定位，多规格提示
    spu = db.query(Spu).filter(Spu.code == code).first()
    if spu:
        if len(spu.skus) == 1:
            return spu.skus[0]
        raise HTTPException(400, "商品[%s]有多个规格，请扫具体规格的条码" % spu.name)
    raise HTTPException(404, "未找到匹配的商品/规格")


@router.get("/stock/scan")
def scan_sku(code: str = "", sku_id: int = 0, db: Session = Depends(get_db),
             _u: User = Depends(get_current_user)):
    """扫码预查询：只返回SKU信息，不改变库存"""
    sku = _resolve_sku(db, code, sku_id or None)
    spu = db.query(Spu).filter(Spu.id == sku.spu_id).first()
    return {"sku_id": sku.id, "spu_id": spu.id, "spu_name": spu.name,
            "spec_name": sku.spec_name or "", "sku_name": _sku_display_name(spu, sku),
            "barcode": sku.barcode or "", "sku_code": sku.sku_code or "",
            "stock": sku.stock, "cost_price": sku.cost_price or 0,
            "sale_price": sku.sale_price or 0, "unit": spu.unit or "件"}


# ============ 扫码出入库 ============
@router.post("/stock/in")
def stock_in(body: StockOp, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    sku = _resolve_sku(db, body.code, body.sku_id)
    if body.quantity <= 0:
        raise HTTPException(400, "数量必须大于0")
    spu = db.query(Spu).filter(Spu.id == sku.spu_id).first()
    sku.stock = (sku.stock or 0) + body.quantity
    db.add(StockLog(sku_id=sku.id, channel_id=body.channel_id or None, log_type="in",
                    quantity=body.quantity, operator_id=u.id, remark=body.remark))
    db.commit()
    db.refresh(sku)
    add_log(db, u, "入库", "%s +%d" % (_sku_display_name(spu, sku), body.quantity))
    db.commit()
    return {"ok": True, "sku_id": sku.id, "sku_name": _sku_display_name(spu, sku),
            "stock": sku.stock}


@router.post("/stock/out")
def stock_out(body: StockOp, db: Session = Depends(get_db), u: User = Depends(get_current_user)):
    sku = _resolve_sku(db, body.code, body.sku_id)
    if body.quantity <= 0:
        raise HTTPException(400, "数量必须大于0")
    if (sku.stock or 0) < body.quantity:
        raise HTTPException(400, "库存不足：当前库存 %d" % (sku.stock or 0))
    spu = db.query(Spu).filter(Spu.id == sku.spu_id).first()
    sku.stock = sku.stock - body.quantity
    db.add(StockLog(sku_id=sku.id, channel_id=body.channel_id or None, log_type="out",
                    quantity=body.quantity, operator_id=u.id, remark=body.remark))
    db.commit()
    db.refresh(sku)
    add_log(db, u, "出库", "%s -%d" % (_sku_display_name(spu, sku), body.quantity))
    db.commit()
    return {"ok": True, "sku_id": sku.id, "sku_name": _sku_display_name(spu, sku),
            "stock": sku.stock}


# ============ 库存流水 ============
@router.get("/stock/logs")
def list_logs(log_type: str = "", channel_id: int = 0, keyword: str = "",
              page: int = 1, page_size: int = 20, db: Session = Depends(get_db),
              _u: User = Depends(get_current_user)):
    q = (db.query(StockLog, Spu.name, Sku.spec_name, Channel.name, User.username)
         .join(Sku, Sku.id == StockLog.sku_id)
         .join(Spu, Spu.id == Sku.spu_id)
         .outerjoin(Channel, Channel.id == StockLog.channel_id)
         .outerjoin(User, User.id == StockLog.operator_id))
    if log_type in ("in", "out"):
        q = q.filter(StockLog.log_type == log_type)
    if channel_id:
        q = q.filter(StockLog.channel_id == channel_id)
    if keyword:
        kw = "%%%s%%" % keyword.strip()
        q = q.filter(or_(Spu.name.like(kw), Sku.barcode.like(kw), Sku.sku_code.like(kw)))
    total = q.count()
    rows = q.order_by(StockLog.created_at.desc(), StockLog.id.desc()) \
            .offset((page - 1) * page_size).limit(page_size).all()
    items = []
    for log, spu_name, spec, ch_name, uname in rows:
        name = spu_name + ("[" + spec + "]" if spec and spec not in ("默认", "") else "")
        items.append({"id": log.id, "sku_id": log.sku_id, "sku_name": name,
                      "channel_id": log.channel_id, "channel_name": ch_name or "",
                      "log_type": log.log_type, "quantity": log.quantity,
                      "operator": uname or "", "remark": log.remark or "",
                      "created_at": log.created_at})
    return {"total": total, "page": page, "page_size": page_size, "items": items}


# ============ 渠道统计 ============
@router.get("/stock/channel-stats")
def channel_stats(db: Session = Depends(get_db), _u: User = Depends(get_current_user)):
    rows = (db.query(Channel.id, Channel.name,
                     func.coalesce(func.sum(StockLog.quantity), 0),
                     func.coalesce(func.sum(StockLog.quantity * Sku.sale_price), 0),
                     func.coalesce(func.sum(StockLog.quantity * (Sku.sale_price - Sku.cost_price)), 0))
            .select_from(Channel)
            .outerjoin(StockLog, StockLog.channel_id == Channel.id)
            .outerjoin(Sku, Sku.id == StockLog.sku_id)
            .filter(or_(StockLog.log_type == "out", StockLog.log_type.is_(None)))
            .group_by(Channel.id).all())
    stats = [{"channel_id": r[0], "channel_name": r[1], "out_qty": int(r[2] or 0),
              "out_amount": round(r[3] or 0, 2), "gross_profit": round(r[4] or 0, 2)} for r in rows]
    unc = (db.query(func.sum(StockLog.quantity),
                    func.sum(StockLog.quantity * Sku.sale_price),
                    func.sum(StockLog.quantity * (Sku.sale_price - Sku.cost_price)))
           .join(Sku, Sku.id == StockLog.sku_id)
           .filter(StockLog.log_type == "out", StockLog.channel_id.is_(None)).first())
    if unc and unc[0]:
        stats.append({"channel_id": None, "channel_name": "未选渠道",
                      "out_qty": int(unc[0]), "out_amount": round(unc[1] or 0, 2),
                      "gross_profit": round(unc[2] or 0, 2)})
    return stats


# ============ 库存概览 ============
@router.get("/stock/summary")
def stock_summary(low_threshold: int = 5, db: Session = Depends(get_db),
                  _u: User = Depends(get_current_user)):
    # 概览只统计在用（未软删）商品，回收站货品不计入
    total_spu = db.query(func.count(Spu.id)).filter(Spu.deleted_at.is_(None)).scalar() or 0
    total_sku = (db.query(func.count(Sku.id))
                 .join(Spu, Spu.id == Sku.spu_id)
                 .filter(Spu.deleted_at.is_(None)).scalar()) or 0
    total_stock = (db.query(func.coalesce(func.sum(Sku.stock), 0))
                   .join(Spu, Spu.id == Sku.spu_id)
                   .filter(Spu.deleted_at.is_(None)).scalar()) or 0
    low_rows = (db.query(Spu.name, Sku.spec_name, Sku.stock, Sku.id)
                .join(Spu, Spu.id == Sku.spu_id)
                .filter(Spu.deleted_at.is_(None))
                .filter(func.coalesce(Sku.stock, 0) <= low_threshold)
                .order_by(Sku.stock.asc()).limit(50).all())
    low_list = []
    for spu_name, spec, stock, sku_id in low_rows:
        name = spu_name + ("[" + spec + "]" if spec and spec not in ("默认", "") else "")
        low_list.append({"sku_id": sku_id, "sku_name": name, "stock": stock})
    return {"total_spu": total_spu, "total_sku": total_sku, "total_stock": total_stock,
            "low_threshold": low_threshold, "low_stock_sku": len(low_rows),
            "low_stock_list": low_list}
