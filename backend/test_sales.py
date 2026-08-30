# -*- coding: utf-8 -*-
"""销售模块接口回归：销售单(草稿CRUD) + 折扣 + 确认出库减库存/流水/留档/回滚
连接已启动的真实 uvicorn（隔离临时库），走 HTTP 请求。
"""
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


# ---- 准备：boss 登录 ----
boss = login("boss", "admin123")
H = auth(boss)
check("登录boss", True)

# ---- 预建销售商品（仓库售价 / 库存） ----
r = client.post("/api/spus", json={
    "name": "销售测试货品A", "code": "SALEA01", "unit": "件", "weight": 0.1,
    "weight_unit": "千克", "images": [], "skus": [
        {"spec_name": "默认", "sku_code": "SALEA01", "barcode": "690000000101",
         "cost_price": 40, "sale_price": 100, "stock": 20}
    ]
}, headers=H)
check("预建货品A", r.status_code == 200, r.text)
r = client.get("/api/stock/scan", params={"code": "690000000101"}, headers=H)
check("扫码取货品A(库存20)", r.status_code == 200 and r.json()["stock"] == 20, r.text)
sku_a = r.json()["sku_id"]

r = client.post("/api/spus", json={
    "name": "销售测试货品B", "code": "SALEB01", "unit": "件", "weight": 0.2,
    "weight_unit": "千克", "images": [], "skus": [
        {"spec_name": "默认", "sku_code": "SALEB01", "barcode": "690000000102",
         "cost_price": 20, "sale_price": 50, "stock": 5}
    ]
}, headers=H)
check("预建货品B", r.status_code == 200, r.text)
r = client.get("/api/stock/scan", params={"code": "690000000102"}, headers=H)
sku_b = r.json()["sku_id"]

# 低库存货品C（库存不足测试）
r = client.post("/api/spus", json={
    "name": "销售测试货品C", "code": "SALEC01", "unit": "件", "weight": 0.1,
    "weight_unit": "千克", "images": [], "skus": [
        {"spec_name": "默认", "sku_code": "SALEC01", "barcode": "690000000103",
         "cost_price": 5, "sale_price": 10, "stock": 1}
    ]
}, headers=H)
check("预建货品C(低库存)", r.status_code == 200, r.text)
r = client.get("/api/stock/scan", params={"code": "690000000103"}, headers=H)
sku_c = r.json()["sku_id"]

# ---- 创建销售单（草稿，含折扣） ----
r = client.post("/api/sales", json={
    "buyer": "回归测试买家", "remark": "销售回归测试",
    "items": [
        {"sku_id": sku_a, "quantity": 3, "discount": 0.35, "unit_price": 35.0},
        {"sku_id": sku_b, "quantity": 2, "discount": 0, "unit_price": 50.0}
    ]
}, headers=H)
check("新建销售单(草稿)", r.status_code == 200, r.text)
so = r.json()
check("销售单号生成", so["order_no"].startswith("S2026"), so["order_no"])
check("销售单明细数=2", len(so["items"]) == 2, str(len(so["items"])))
check("合计=3*35+2*50=205", abs(so["total_amount"] - 205) < 0.01, str(so["total_amount"]))
check("草稿折扣随行保存(0.35)", abs(so["items"][0]["discount"] - 0.35) < 1e-6, str(so["items"][0]["discount"]))
so_id = so["id"]

# ---- 列表 / 详情 ----
r = client.get("/api/sales", params={"status": "draft"}, headers=H)
check("销售单列表(草稿筛选)", r.status_code == 200 and r.json()["total"] >= 1, r.text)
r = client.get(f"/api/sales/{so_id}", headers=H)
check("销售单详情", r.status_code == 200 and len(r.json()["items"]) == 2, r.text)

# ---- 修改草稿（数量/折扣/售价） ----
r = client.put(f"/api/sales/{so_id}", json={
    "buyer": "回归测试买家", "remark": "改一下",
    "items": [
        {"id": so["items"][0]["id"], "sku_id": sku_a, "quantity": 4, "discount": 0.5, "unit_price": 50.0},
        {"sku_id": sku_b, "quantity": 2, "discount": 0.6, "unit_price": 30.0}
    ]
}, headers=H)
check("修改销售草稿", r.status_code == 200 and len(r.json()["items"]) == 2, r.text)
check("修改后合计=4*50+2*30=260", abs(r.json()["total_amount"] - 260) < 0.01, str(r.json()["total_amount"]))
check("修改后折扣保存(0.5/0.6)",
      abs(r.json()["items"][0]["discount"] - 0.5) < 1e-6 and abs(r.json()["items"][1]["discount"] - 0.6) < 1e-6,
      r.text)

# ---- 确认出库 ----
r = client.post(f"/api/sales/{so_id}/confirm", headers=H)
check("确认出库", r.status_code == 200, r.text)
check("确认返回项数=2", r.json()["items"] == 2, r.text)

# 库存扣减：A 20-4=16, B 5-2=3
r = client.get("/api/stock/scan", params={"code": "690000000101"}, headers=H)
check("货品A库存扣减=16", r.status_code == 200 and r.json()["stock"] == 16, r.text)
r = client.get("/api/stock/scan", params={"code": "690000000102"}, headers=H)
check("货品B库存扣减=3", r.status_code == 200 and r.json()["stock"] == 3, r.text)

# 状态 done + confirmed_at + 预留字段
r = client.get(f"/api/sales/{so_id}", headers=H)
check("状态置为done", r.json()["status"] == "done", r.json()["status"])
check("确认时间已记录", bool(r.json()["confirmed_at"]), str(r.json()["confirmed_at"]))
check("预留字段存在(未开票)", r.json()["invoice_status"] == "uninvoiced", r.json()["invoice_status"])
check("确认后折扣仍随行保存(0.5)", abs(r.json()["items"][0]["discount"] - 0.5) < 1e-6, str(r.json()["items"][0]["discount"]))

# 流水留痕（remark 带销售单号；logs 接口 keyword 匹配商品名/条码）
r = client.get("/api/stock/logs", params={"keyword": "销售测试货品A", "log_type": "out"}, headers=H)
rows = r.json().get("items") or []
ok = (r.status_code == 200 and r.json()["total"] >= 1 and rows
      and rows[0]["log_type"] == "out" and so["order_no"] in rows[0].get("remark", ""))
check("出库流水留痕(out,备注带销售单号)", ok, r.text)

# ---- 重复确认拦截 ----
r = client.post(f"/api/sales/{so_id}/confirm", headers=H)
check("重复确认被拦截", r.status_code == 400, r.text)

# ---- 已确认不可修改 ----
r = client.put(f"/api/sales/{so_id}", json={"items": []}, headers=H)
check("已确认不可修改", r.status_code == 400, r.text)

# ---- 已确认不可删除 ----
r = client.delete(f"/api/sales/{so_id}", headers=H)
check("已确认不可删除", r.status_code == 400, r.text)

# ---- 库存不足拦截 + 回滚 ----
r = client.post("/api/sales", json={
    "buyer": "不足测试", "items": [
        {"sku_id": sku_c, "quantity": 10, "discount": 0, "unit_price": 10.0}
    ]
}, headers=H)
check("新建不足库存销售单(草稿)", r.status_code == 200, r.text)
lack_id = r.json()["id"]
r = client.post(f"/api/sales/{lack_id}/confirm", headers=H)
check("库存不足被拦截(400)", r.status_code == 400, r.text)
r = client.get("/api/stock/scan", params={"code": "690000000103"}, headers=H)
check("库存不足回滚(库存不变=1)", r.json()["stock"] == 1, r.text)
r = client.delete(f"/api/sales/{lack_id}", headers=H)
check("删除库存不足草稿", r.status_code == 200, r.text)

# ---- 无明细不可确认 ----
r = client.post("/api/sales", json={"buyer": "空单", "items": []}, headers=H)
check("创建空明细草稿", r.status_code == 200, r.text)
empty_id = r.json()["id"]
r = client.post(f"/api/sales/{empty_id}/confirm", headers=H)
check("空明细确认被拦截", r.status_code == 400, r.text)
r = client.delete(f"/api/sales/{empty_id}", headers=H)
check("删除空明细草稿", r.status_code == 200, r.text)

print("\n================ 结果 ================")
print("PASS:", passed, " FAIL:", len(failed))
if failed:
    print("FAILED:", failed)
    sys.exit(1)
print("ALL GREEN")
