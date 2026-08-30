# -*- coding: utf-8 -*-
"""财务对账模块回归：成本快照 + 汇总/渠道分组/对账明细毛利 + 日期过滤 + staff权限 + 旧单成本回退
连接已启动的真实 uvicorn（隔离临时库），走 HTTP 请求。
"""
import os
import sqlite3
import sys

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


# ---- 准备：boss 登录 + 建 staff 账号 ----
boss = login("boss", "admin123")
HB = auth(boss)
check("登录boss", True)

r = client.post("/api/users", json={"username": "staff_fin", "password": "staff123",
                                    "nickname": "店员", "role": "staff"}, headers=HB)
check("创建staff账号", r.status_code == 200, r.text)
staff_token = login("staff_fin", "staff123")
HS = auth(staff_token)

# ---- staff 权限 403 ----
for path in ("/api/finance/summary", "/api/finance/by-channel", "/api/finance/orders"):
    r = client.get(path, headers=HS)
    check(f"staff访问{path}被拒(403)", r.status_code == 403, f"{r.status_code}")

# ---- 预建商品（成本/售价/库存） ----
r = client.post("/api/spus", json={
    "name": "财务测试货品A", "code": "FINA01", "unit": "件", "weight": 0.1,
    "weight_unit": "千克", "images": [], "skus": [
        {"spec_name": "默认", "sku_code": "FINA01", "barcode": "690000000201",
         "cost_price": 20, "sale_price": 50, "stock": 50}
    ]
}, headers=HB)
check("预建货品A", r.status_code == 200, r.text)
r = client.get("/api/stock/scan", params={"code": "690000000201"}, headers=HB)
sku_a = r.json()["sku_id"]
check("货品A成本=20", r.json()["cost_price"] == 20, r.text)

r = client.post("/api/spus", json={
    "name": "财务测试货品B", "code": "FINB01", "unit": "件", "weight": 0.2,
    "weight_unit": "千克", "images": [], "skus": [
        {"spec_name": "默认", "sku_code": "FINB01", "barcode": "690000000202",
         "cost_price": 10, "sale_price": 30, "stock": 50}
    ]
}, headers=HB)
check("预建货品B", r.status_code == 200, r.text)
r = client.get("/api/stock/scan", params={"code": "690000000202"}, headers=HB)
sku_b = r.json()["sku_id"]
check("货品B成本=10", r.json()["cost_price"] == 10, r.text)

# ---- 渠道 ----
r = client.post("/api/channels", json={"name": "天猫旗舰店", "channel_type": "platform", "remark": "回归"}, headers=HB)
check("创建渠道1", r.status_code == 200, r.text)
ch1 = r.json()["id"]
r = client.post("/api/channels", json={"name": "抖音小店", "channel_type": "platform", "remark": "回归"}, headers=HB)
check("创建渠道2", r.status_code == 200, r.text)
ch2 = r.json()["id"]

# ---- 销售单1（渠道1）：A×2 @40 + B×1 @30 = 110，成本50，毛利60 ----
r = client.post("/api/sales", json={
    "channel_id": ch1, "buyer": "财务买家甲", "remark": "对账回归单1",
    "items": [
        {"sku_id": sku_a, "quantity": 2, "discount": 0.8, "unit_price": 40.0},
        {"sku_id": sku_b, "quantity": 1, "discount": 0, "unit_price": 30.0}
    ]
}, headers=HB)
check("新建销售单1", r.status_code == 200, r.text)
so1 = r.json()["id"]
r = client.post(f"/api/sales/{so1}/confirm", headers=HB)
check("确认销售单1出库", r.status_code == 200, r.text)

# 成本快照在确认时点写入（由财务对账详情验证；sales 明细接口不暴露该字段）

# ---- 销售单2（渠道2）：A×1 @50 = 50，成本20，毛利30 ----
r = client.post("/api/sales", json={
    "channel_id": ch2, "buyer": "财务买家乙", "remark": "对账回归单2",
    "items": [{"sku_id": sku_a, "quantity": 1, "discount": 0, "unit_price": 50.0}]
}, headers=HB)
so2 = r.json()["id"]
r = client.post(f"/api/sales/{so2}/confirm", headers=HB)
check("确认销售单2出库", r.status_code == 200, r.text)

# ---- 销售单3（无渠道）：B×1 @30 = 30，成本10，毛利20 ----
r = client.post("/api/sales", json={
    "buyer": "财务买家丙", "remark": "对账回归单3",
    "items": [{"sku_id": sku_b, "quantity": 1, "discount": 0, "unit_price": 30.0}]
}, headers=HB)
so3 = r.json()["id"]
r = client.post(f"/api/sales/{so3}/confirm", headers=HB)
check("确认销售单3出库", r.status_code == 200, r.text)

# ---- 单1 对账详情（逐行毛利） ----
r = client.get(f"/api/finance/orders/{so1}", headers=HB)
check("对账详情(单1)可取", r.status_code == 200, r.text)
d1 = r.json()
line_a = [l for l in d1["lines"] if l["sku_id"] == sku_a][0]
line_b = [l for l in d1["lines"] if l["sku_id"] == sku_b][0]
check("单1行A成本快照=20", line_a["cost_price"] == 20, str(line_a["cost_price"]))
check("单1行A毛利=40", line_a["gross"] == 40, str(line_a["gross"]))
check("单1行A毛利率=0.5", line_a["gross_rate"] == 0.5, str(line_a["gross_rate"]))
check("单1行B毛利=20", line_b["gross"] == 20, str(line_b["gross"]))
check("单1销售总额=110", d1["sales_total"] == 110, str(d1["sales_total"]))
check("单1成本总额=50", d1["cost_total"] == 50, str(d1["cost_total"]))
check("单1毛利总额=60", d1["gross_total"] == 60, str(d1["gross_total"]))
check("单1毛利率=60/110", abs(d1["gross_rate"] - 0.5455) < 0.0001, str(d1["gross_rate"]))

# ---- summary 全范围 ----
r = client.get("/api/finance/summary", params={"start": "2000-01-01", "end": "2099-12-31"}, headers=HB)
s = r.json()
check("summary销售总额=190", s["sales_total"] == 190, str(s["sales_total"]))
check("summary成本总额=80", s["cost_total"] == 80, str(s["cost_total"]))
check("summary毛利总额=110", s["gross_total"] == 110, str(s["gross_total"]))
check("summary毛利率=110/190", abs(s["gross_rate"] - 0.5789) < 0.0001, str(s["gross_rate"]))
check("summary单数=3", s["order_count"] == 3, str(s["order_count"]))
check("summary出库件数=5", s["item_qty"] == 5, str(s["item_qty"]))

# ---- summary 按渠道过滤 ----
r = client.get("/api/finance/summary", params={"start": "2000-01-01", "end": "2099-12-31", "channel_id": ch1}, headers=HB)
s1 = r.json()
check("summary(渠道1)销售=110", s1["sales_total"] == 110, str(s1["sales_total"]))
check("summary(渠道1)毛利=60", s1["gross_total"] == 60, str(s1["gross_total"]))
check("summary(渠道1)单数=1", s1["order_count"] == 1, str(s1["order_count"]))

# ---- by-channel 分组 ----
r = client.get("/api/finance/by-channel", params={"start": "2000-01-01", "end": "2099-12-31"}, headers=HB)
rows = r.json()["rows"]
g_tmall = next((g for g in rows if g["channel_name"] == "天猫旗舰店"), None)
g_douyin = next((g for g in rows if g["channel_name"] == "抖音小店"), None)
g_none = next((g for g in rows if g["channel_name"] == "未指定渠道"), None)
check("by-channel共3组", len(rows) == 3, str([g["channel_name"] for g in rows]))
check("by-channel天猫 110/50/60", g_tmall and g_tmall["sales_total"] == 110 and g_tmall["cost_total"] == 50 and g_tmall["gross_total"] == 60, str(g_tmall))
check("by-channel抖音 50/20/30", g_douyin and g_douyin["sales_total"] == 50 and g_douyin["gross_total"] == 30, str(g_douyin))
check("by-channel未指定 30/10/20", g_none and g_none["sales_total"] == 30 and g_none["gross_total"] == 20, str(g_none))

# ---- orders 对账明细列表 ----
r = client.get("/api/finance/orders", params={"start": "2000-01-01", "end": "2099-12-31"}, headers=HB)
check("orders总数=3", r.json()["total"] == 3, r.text)
item = next((x for x in r.json()["items"] if x["id"] == so1), None)
check("orders含单1且毛利=60", item and item["gross_total"] == 60, str(item))
check("orders含单号/渠道/客户", item and item["order_no"].startswith("S2026") and item["channel_name"] == "天猫旗舰店" and item["buyer"] == "财务买家甲", str(item))
check("orders含预留字段(未开票)", item and item["invoice_status"] == "uninvoiced", str(item))

# ---- 日期范围过滤生效 ----
r = client.get("/api/finance/summary", params={"start": "2000-01-01", "end": "2000-01-02"}, headers=HB)
check("范围外summary单数=0", r.json()["order_count"] == 0, str(r.json()["order_count"]))
r = client.get("/api/finance/orders", params={"start": "2000-01-01", "end": "2000-01-02"}, headers=HB)
check("范围外orders=0", r.json()["total"] == 0, r.text)

# ---- 成本快照不随档案成本漂移（快照优先） ----
# 把货品B当前成本改为25；单3(货品B)已确认且有快照10，对账仍应取快照10
dbpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_finance.db")
conn = sqlite3.connect(dbpath, timeout=15)
conn.execute("UPDATE skus SET cost_price = 25 WHERE id = ?", (sku_b,))
conn.commit()
conn.close()

r = client.get(f"/api/finance/orders/{so3}", headers=HB)
line3 = r.json()["lines"][0]
check("快照不随档案成本漂移(cost_price仍=10)", line3["cost_price"] == 10, str(line3["cost_price"]))
check("快照不漂移则毛利仍=20", line3["gross"] == 20, str(line3["gross"]))

# ---- 旧单无快照时回退当前SKU成本 ----
# 清空单3的行成本快照（模拟旧单），此时货品B当前成本=25 → 回退取25
r = client.get(f"/api/sales/{so3}", headers=HB)
sale_item3 = r.json()["items"][0]["id"]
conn = sqlite3.connect(dbpath, timeout=15)
conn.execute("UPDATE sale_items SET cost_price = NULL WHERE id = ?", (sale_item3,))
conn.commit()
conn.close()

r = client.get(f"/api/finance/orders/{so3}", headers=HB)
d3 = r.json()
line3 = d3["lines"][0]
check("旧单无快照回退当前成本=25", line3["cost_price"] == 25, str(line3["cost_price"]))
check("回退后行毛利=(30-25)*1=5", line3["gross"] == 5, str(line3["gross"]))
check("回退后单毛利=5", d3["gross_total"] == 5, str(d3["gross_total"]))

print("\n================ 结果 ================")
print("PASS:", passed, " FAIL:", len(failed))
if failed:
    print("FAILED:", failed)
    sys.exit(1)
print("ALL GREEN")
