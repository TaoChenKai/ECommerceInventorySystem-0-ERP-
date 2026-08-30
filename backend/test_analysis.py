# -*- coding: utf-8 -*-
"""库存分析模块回归：summary / category-stock / stock-rank / selling-top / slow-moving /
low-stock / trend + 无数据空结构 + staff 登录可见
连接已启动的真实 uvicorn（隔离临时库），走 HTTP 请求。
"""
import os
import sqlite3
import sys
from datetime import datetime, timedelta

import httpx

BASE = "http://127.0.0.1:8765"
client = httpx.Client(base_url=BASE, timeout=20)

passed = 0
failed = []


def check(name, cond, extra=""):
    global passed
    if cond:
        passed += 1
        print("PASS", name)
    else:
        failed.append(name)
        print("FAIL", name, extra)


def login(username, password):
    r = client.post("/api/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def iso_days_ago(n):
    return (datetime.utcnow() - timedelta(days=n)).strftime("%Y-%m-%d %H:%M:%S")


def today_str():
    return datetime.utcnow().date().isoformat()


# ---- 准备：boss 登录 + 建 staff 账号 ----
boss = login("boss", "admin123")
HB = auth(boss)
check("登录boss", True)

r = client.post("/api/users", json={"username": "staff_anl", "password": "staff123",
                                    "nickname": "店员", "role": "staff"}, headers=HB)
check("创建staff账号", r.status_code == 200, r.text)
staff_token = login("staff_anl", "staff123")
HS = auth(staff_token)

# ---- 无数据时空结构（建商品前，除自动 boss 外无任何 SKU） ----
r = client.get("/api/analysis/summary", headers=HB)
s0 = r.json()
check("空库summary可取且全0", r.status_code == 200 and s0["total_qty"] == 0
      and s0["total_value"] == 0 and s0["sku_count"] == 0
      and s0["spu_count"] == 0 and s0["low_stock_count"] == 0 and s0["stale_count"] == 0, r.text)
for path in ("/api/analysis/category-stock", "/api/analysis/stock-rank",
             "/api/analysis/selling-top", "/api/analysis/slow-moving", "/api/analysis/low-stock"):
    r = client.get(path, headers=HB)
    check(f"空库{path}返回空rows", r.status_code == 200 and r.json()["rows"] == [], r.text)
r = client.get("/api/analysis/trend", params={"days": 30}, headers=HB)
t0 = r.json()["rows"]
check("空库trend返回30天全0", len(t0) == 30 and all(x["in_qty"] == 0 and x["out_qty"] == 0 for x in t0), str(len(t0)))

# ---- staff 登录即可见（非仅 boss/admin） ----
r = client.get("/api/analysis/summary", headers=HS)
check("staff可访问analysis(200)", r.status_code == 200, f"{r.status_code}")

# ---- 预建分类与商品 ----
r = client.post("/api/categories", json={"name": "分析分类X"}, headers=HB)
check("建分类X", r.status_code == 200, r.text)
cat_x = r.json()["id"]
r = client.post("/api/categories", json={"name": "分析分类Y"}, headers=HB)
check("建分类Y", r.status_code == 200, r.text)
cat_y = r.json()["id"]

r = client.post("/api/spus", json={
    "name": "分析货品A", "code": "ANLA01", "unit": "件", "weight": 0.1,
    "weight_unit": "千克", "category_id": cat_x, "images": [], "skus": [
        {"spec_name": "默认", "sku_code": "ANLA01", "barcode": "690000000301",
         "cost_price": 10, "sale_price": 50, "stock": 40}
    ]
}, headers=HB)
check("建货品A(catX,stock40)", r.status_code == 200, r.text)
r = client.get("/api/stock/scan", params={"code": "690000000301"}, headers=HB)
sku_a = r.json()["sku_id"]

r = client.post("/api/spus", json={
    "name": "分析货品B", "code": "ANLB01", "unit": "件", "weight": 0.1,
    "weight_unit": "千克", "category_id": cat_x, "images": [], "skus": [
        {"spec_name": "默认", "sku_code": "ANLB01", "barcode": "690000000302",
         "cost_price": 20, "sale_price": 40, "stock": 3}
    ]
}, headers=HB)
check("建货品B(catX,stock3)", r.status_code == 200, r.text)
r = client.get("/api/stock/scan", params={"code": "690000000302"}, headers=HB)
sku_b = r.json()["sku_id"]

r = client.post("/api/spus", json={
    "name": "分析货品C", "code": "ANLC01", "unit": "件", "weight": 0.1,
    "weight_unit": "千克", "category_id": cat_y, "images": [], "skus": [
        {"spec_name": "默认", "sku_code": "ANLC01", "barcode": "690000000303",
         "cost_price": 30, "sale_price": 60, "stock": 5}
    ]
}, headers=HB)
check("建货品C(catY,stock5)", r.status_code == 200, r.text)
r = client.get("/api/stock/scan", params={"code": "690000000303"}, headers=HB)
sku_c = r.json()["sku_id"]

r = client.post("/api/spus", json={
    "name": "分析货品D", "code": "ANLD01", "unit": "件", "weight": 0.1,
    "weight_unit": "千克", "images": [], "skus": [
        {"spec_name": "默认", "sku_code": "ANLD01", "barcode": "690000000304",
         "cost_price": 15, "sale_price": 25, "stock": 7}
    ]
}, headers=HB)
check("建货品D(无分类,stock7)", r.status_code == 200, r.text)
r = client.get("/api/stock/scan", params={"code": "690000000304"}, headers=HB)
sku_d = r.json()["sku_id"]

# ---- 直连库：调整 SKU 建档时间，制造可预期的"从未出库滞销天数" ----
dbpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_analysis.db")
conn = sqlite3.connect(dbpath, timeout=15)
conn.execute("UPDATE skus SET created_at=? WHERE id=?", (iso_days_ago(20), sku_a))
conn.execute("UPDATE skus SET created_at=? WHERE id=?", (iso_days_ago(10), sku_b))
conn.execute("UPDATE skus SET created_at=? WHERE id=?", (iso_days_ago(30), sku_c))
conn.execute("UPDATE skus SET created_at=? WHERE id=?", (iso_days_ago(40), sku_d))
conn.commit()
conn.close()

# ---- summary（初始，无出库） ----
r = client.get("/api/analysis/summary", headers=HB)
s = r.json()
check("summary总件数=55", s["total_qty"] == 55, str(s["total_qty"]))
check("summary总价值=715", s["total_value"] == 715, str(s["total_value"]))
check("summary SKU数=4", s["sku_count"] == 4, str(s["sku_count"]))
check("summary SPU数=4", s["spu_count"] == 4, str(s["spu_count"]))
check("summary低库存数=3(B/C/D)", s["low_stock_count"] == 3, str(s["low_stock_count"]))
check("summary滞销数=4(全部未出库)", s["stale_count"] == 4, str(s["stale_count"]))

# ---- category-stock（X: 43/460, Y: 5/150, 未分类: 7/105） ----
r = client.get("/api/analysis/category-stock", headers=HB)
cat = r.json()
check("category分组数=3", len(cat["rows"]) == 3, str([x["category_name"] for x in cat["rows"]]))
check("category总件数=55", cat["total_qty"] == 55, str(cat["total_qty"]))
gx = next((x for x in cat["rows"] if x["category_name"] == "分析分类X"), None)
gy = next((x for x in cat["rows"] if x["category_name"] == "分析分类Y"), None)
gn = next((x for x in cat["rows"] if x["category_name"] == "未分类"), None)
check("分类X 2个SKU/43件/460元", gx and gx["sku_count"] == 2 and gx["qty"] == 43 and gx["value"] == 460, str(gx))
check("分类Y 1个SKU/5件/150元", gy and gy["sku_count"] == 1 and gy["qty"] == 5 and gy["value"] == 150, str(gy))
check("未分类 1个SKU/7件/105元", gn and gn["sku_count"] == 1 and gn["qty"] == 7 and gn["value"] == 105, str(gn))
check("分类X占比=43/55=78.2", gx and abs(gx["ratio"] - 78.2) < 0.1, str(gx["ratio"]))
check("未分类占比=7/55=12.7", gn and abs(gn["ratio"] - 12.7) < 0.1, str(gn["ratio"]))

# ---- stock-rank：value 与 qty 排序 ----
r = client.get("/api/analysis/stock-rank", params={"limit": 10, "order": "value"}, headers=HB)
rv = r.json()["rows"]
check("stock-rank(value)顺序 A,C,D,B", [x["name"] for x in rv] == ["分析货品A", "分析货品C", "分析货品D", "分析货品B"],
      str([x["name"] for x in rv]))
check("stock-rank(value)首条 40件/400元", rv[0]["stock"] == 40 and rv[0]["value"] == 400, str(rv[0]))
r = client.get("/api/analysis/stock-rank", params={"limit": 2, "order": "qty"}, headers=HB)
rq = r.json()["rows"]
check("stock-rank(qty,limit2) A,D", [x["name"] for x in rq] == ["分析货品A", "分析货品D"], str([x["name"] for x in rq]))

# ---- low-stock：阈值过滤 stock<10，库存升序 ----
r = client.get("/api/analysis/low-stock", headers=HB)
low = r.json()["rows"]
check("low-stock命中3个(B/C/D)", len(low) == 3, str(len(low)))
check("low-stock顺序 B(3),C(5),D(7)", [x["name"] for x in low] == ["分析货品B", "分析货品C", "分析货品D"]
      and [x["stock"] for x in low] == [3, 5, 7], str([(x["name"], x["stock"]) for x in low]))
check("low-stock含成本价", low[0]["cost_price"] == 20, str(low[0]["cost_price"]))

# ---- slow-moving（初始，从未出库按建档时间 D40,C30,A20,B10） ----
r = client.get("/api/analysis/slow-moving", headers=HB)
sm = r.json()["rows"]
check("slow-moving(未出库)顺序 D,C,A,B", [x["name"] for x in sm] == ["分析货品D", "分析货品C", "分析货品A", "分析货品B"],
      str([x["name"] for x in sm]))
check("slow-moving(未出库)天数 40,30,20,10", [x["days"] for x in sm] == [40, 30, 20, 10], str([x["days"] for x in sm]))
check("slow-moving含last_out=null", sm[0]["last_out"] is None, str(sm[0]["last_out"]))

# ---- 制造出库流水（销售单确认）+ 入库流水 ----
r = client.post("/api/sales", json={"buyer": "分析买家甲", "remark": "分析回归单1",
                                    "items": [
                                        {"sku_id": sku_a, "quantity": 5, "discount": 0, "unit_price": 50.0},
                                        {"sku_id": sku_b, "quantity": 2, "discount": 0, "unit_price": 40.0}
                                    ]}, headers=HB)
so1 = r.json()["id"]
r = client.post(f"/api/sales/{so1}/confirm", headers=HB)
check("确认销售单1(A5+B2)", r.status_code == 200, r.text)
r = client.post("/api/sales", json={"buyer": "分析买家乙", "remark": "分析回归单2",
                                    "items": [{"sku_id": sku_c, "quantity": 1, "discount": 0, "unit_price": 60.0}]}, headers=HB)
so2 = r.json()["id"]
r = client.post(f"/api/sales/{so2}/confirm", headers=HB)
check("确认销售单2(C1)", r.status_code == 200, r.text)

r = client.post("/api/stock/in", json={"sku_id": sku_a, "quantity": 10, "remark": "分析入库流水"}, headers=HB)
check("手工入库A 10件(流水)", r.status_code == 200, r.text)

# ---- trend：近30天按天聚合，今天 in=10(手工入库) out=8(A5+B2+C1) ----
r = client.get("/api/analysis/trend", params={"days": 30}, headers=HB)
tr = r.json()["rows"]
check("trend返回30天", len(tr) == 30, str(len(tr)))
last = tr[-1]
check("trend最后一天是今天", last["date"] == today_str(), last["date"])
check("trend今天入库=10", last["in_qty"] == 10, str(last["in_qty"]))
check("trend今天出库=8", last["out_qty"] == 8, str(last["out_qty"]))

# ---- selling-top：近30天按出库量 A5,B2,C1 ----
r = client.get("/api/analysis/selling-top", params={"limit": 10, "days": 30}, headers=HB)
st = r.json()["rows"]
check("selling-top命中3个", len(st) == 3, str(len(st)))
check("selling-top顺序 A(5),B(2),C(1)", [x["name"] for x in st] == ["分析货品A", "分析货品B", "分析货品C"],
      str([x["name"] for x in st]))
check("selling-top出库金额 A=250,B=80,C=60", st[0]["amount"] == 250 and st[1]["amount"] == 80 and st[2]["amount"] == 60,
      str([x["amount"] for x in st]))

# ---- summary 复查（出库后：A40-5=35 且手工入库+10=45, B3-2=1, C5-1=4, D7 → 57件）
# 价值 45*10+1*20+4*30+7*15=695 ----
r = client.get("/api/stock/scan", params={"code": "690000000301"}, headers=HB)
check("A出库后+手工入库库存=45", r.json()["stock"] == 45, str(r.json()["stock"]))
r = client.get("/api/analysis/summary", headers=HB)
s2 = r.json()
check("summary出库后总件数=57", s2["total_qty"] == 57, str(s2["total_qty"]))
check("summary出库后总价值=695", s2["total_value"] == 695, str(s2["total_value"]))
check("summary出库后低库存=3(B/C/D)", s2["low_stock_count"] == 3, str(s2["low_stock_count"]))
check("summary出库后滞销=1(仅D未出库)", s2["stale_count"] == 1, str(s2["stale_count"]))

# ---- 直连库：把 B/C 的出库流水时间改到 40/60 天前，制造历史滞销 ----
conn = sqlite3.connect(dbpath, timeout=15)
conn.execute("UPDATE stock_logs SET created_at=? WHERE sku_id=? AND log_type='out'", (iso_days_ago(40), sku_b))
conn.execute("UPDATE stock_logs SET created_at=? WHERE sku_id=? AND log_type='out'", (iso_days_ago(60), sku_c))
conn.commit()
conn.close()

# ---- slow-moving（有出库：从未出库D最前 → C60 → B40 → A0） ----
r = client.get("/api/analysis/slow-moving", headers=HB)
sm2 = r.json()["rows"]
check("slow-moving(有出库)顺序 D,C,B,A", [x["name"] for x in sm2] == ["分析货品D", "分析货品C", "分析货品B", "分析货品A"],
      str([x["name"] for x in sm2]))
check("slow-moving天数 C=60,B=40,A=0", sm2[1]["days"] == 60 and sm2[2]["days"] == 40 and sm2[3]["days"] == 0,
      str([x["days"] for x in sm2]))
check("slow-moving C/B 有 last_out 且 D 无", sm2[1]["last_out"] is not None and sm2[0]["last_out"] is None, str(sm2[0]["last_out"]))

# ---- summary 滞销数复查（B/C 历史出库 + D 未出库 → 3） ----
r = client.get("/api/analysis/summary", headers=HB)
check("summary滞销数=3(B/C/D)", r.json()["stale_count"] == 3, str(r.json()["stale_count"]))

print("\n================ 结果 ================")
print("PASS:", passed, " FAIL:", len(failed))
if failed:
    print("FAILED:", failed)
    sys.exit(1)
print("ALL GREEN")
