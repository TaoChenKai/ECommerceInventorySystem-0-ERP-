# -*- coding: utf-8 -*-
"""采购模块接口回归：供应商 + 采购单 + 扫码建档 + 批量入库
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
    print(">>> login status", r.status_code, flush=True)
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


# ---- 准备：boss 登录 ----
import time
SUP_NAME = "广州玩具厂_" + str(int(time.time()) % 1000000)
SUP_NAME2 = SUP_NAME + "_改"
boss = login("boss", "admin123")
H = auth(boss)
check("登录boss", True)

# ---- 供应商 CRUD ----
r = client.post("/api/suppliers", json={"name": SUP_NAME, "contact": "王姐", "phone": "13800000000"}, headers=H)
check("新增供应商", r.status_code == 200, r.text)
sup_id = r.json()["id"]

r = client.post("/api/suppliers", json={"name": SUP_NAME}, headers=H)
check("重复供应商被拦截", r.status_code == 400, r.text)

r = client.get("/api/suppliers", headers=H)
check("供应商列表", r.status_code == 200 and len(r.json()) >= 1)

r = client.put(f"/api/suppliers/{sup_id}", json={"name": SUP_NAME2, "contact": "王姐", "phone": "13900000000"}, headers=H)
check("修改供应商", r.status_code == 200 and r.json()["name"] == SUP_NAME2)

# ---- 建采购单（草稿）：1条已建档商品 + 1条待建档 ----
# 先建一个已建档商品
r = client.post("/api/spus", json={
    "name": "已有货品", "code": "EXIST01", "unit": "件", "weight": 0.5,
    "weight_unit": "千克", "images": [], "skus": [
        {"spec_name": "默认", "sku_code": "EXIST01", "barcode": "690000000001", "cost_price": 3.5, "sale_price": 9.9, "stock": 10}
    ]
}, headers=H)
check("预建已建档商品", r.status_code == 200, r.text)
existing_spu = r.json()["id"]

# 用扫码取回该商品的 sku_id（已建档商品采购应直接挂 sku）
r = client.get("/api/stock/scan", params={"code": "690000000001"}, headers=H)
check("预建商品扫码取sku", r.status_code == 200, r.text)
existing_sku = r.json()["sku_id"]

r = client.post("/api/purchases", json={
    "supplier_id": sup_id, "purchase_method": "现货采购", "order_date": "2026-08-21", "remark": "回归测试",
    "items": [
        {"status": "existing", "spu_id": existing_spu, "sku_id": existing_sku, "quantity": 5, "unit_price": 3.2,
         "draft_name": "", "draft_barcode": "690000000001"},
        {"status": "draft", "spu_id": None, "sku_id": None, "quantity": 12, "unit_price": 2.8,
         "draft_name": "新兔子挂件", "draft_code": "NEW01", "draft_spec": "粉色", "draft_barcode": "690000000099",
         "draft_category": "挂件", "draft_unit": "个", "draft_weight": 0.03, "draft_weight_unit": "千克",
         "draft_remark": "材质PVC", "draft_images": ["/uploads/demo1.png", "/uploads/demo2.png"]}
    ]
}, headers=H)
check("新建采购单(草稿)", r.status_code == 200, r.text)
po = r.json()
check("采购单号生成", po["order_no"].startswith("P2026"), po["order_no"])
check("采购单明细数", len(po["items"]) == 2)
check("合计金额=5*3.2+12*2.8", abs(po["total_amount"] - 49.6) < 0.01, po["total_amount"])
po_id = po["id"]

# ---- 扫码解析未命中（确认会404触发建档流程） ----
r = client.get("/api/stock/scan", params={"code": "999999999999"}, headers=H)
check("扫未命中的码返回404", r.status_code == 404, str(r.status_code))

# ---- 已建档商品扫码命中 ----
r = client.get("/api/stock/scan", params={"code": "690000000001"}, headers=H)
check("扫已建档码命中", r.status_code == 200 and r.json()["sku_name"] == "已有货品", r.text)

# ---- 采购单列表 / 详情 ----
r = client.get("/api/purchases", params={"status": "draft"}, headers=H)
check("采购单列表(草稿)", r.status_code == 200 and r.json()["total"] >= 1)
r = client.get(f"/api/purchases/{po_id}", headers=H)
check("采购单详情", r.status_code == 200 and len(r.json()["items"]) == 2)

# ---- 修改采购单：数量调整 ----
r = client.put(f"/api/purchases/{po_id}", json={
    "supplier_id": sup_id, "purchase_method": "现货采购", "order_date": "2026-08-21", "remark": "改一下",
    "items": [
        {"id": po["items"][0]["id"], "status": "existing", "spu_id": existing_spu, "sku_id": existing_sku,
         "quantity": 6, "unit_price": 3.2, "draft_name": "", "draft_barcode": "690000000001"},
        {"status": "draft", "spu_id": None, "sku_id": None, "quantity": 12, "unit_price": 2.8,
         "draft_name": "新兔子挂件", "draft_code": "NEW01", "draft_spec": "粉色", "draft_barcode": "690000000099",
         "draft_category": "挂件", "draft_unit": "个", "draft_weight": 0.03, "draft_weight_unit": "千克",
         "draft_remark": "材质PVC", "draft_images": ["/uploads/demo1.png"]}
    ]
}, headers=H)
check("修改采购单", r.status_code == 200 and len(r.json()["items"]) == 2, r.text)
check("修改后合计=6*3.2+12*2.8", abs(r.json()["total_amount"] - 52.8) < 0.01, r.json()["total_amount"])

# ---- 确认入库（统一建档+加库存+流水，单事务） ----
r = client.post(f"/api/purchases/{po_id}/confirm", headers=H)
check("确认入库", r.status_code == 200, r.text)
check("入库项数", r.json()["items"] == 2, r.text)

# 原已建档商品库存 10+6=16
r = client.get("/api/stock/scan", params={"code": "690000000001"}, headers=H)
check("已建档商品库存累加=16", r.status_code == 200 and r.json()["stock"] == 16, r.text)
check("已建档商品进价更新为采购单价", r.json()["cost_price"] == 3.2, r.text)

# 新建档商品：扫码命中 + 库存12 + 价格 + 分类/图片
r = client.get("/api/stock/scan", params={"code": "690000000099"}, headers=H)
check("新建档商品可扫码命中", r.status_code == 200, r.text)
check("新建档商品库存=12", r.json()["stock"] == 12, r.text)
check("新建档商品进价=2.8", r.json()["cost_price"] == 2.8, r.text)
check("新建档商品名称", r.json()["spu_name"] == "新兔子挂件", r.text)
new_sku_id = r.json()["sku_id"]

# 商品档案里能查到新分类与新图片
r = client.get("/api/spus", headers=H)
prods = r.json()
new_prod = [p for p in prods if p["name"] == "新兔子挂件"]
check("新货品进入商品档案", len(new_prod) == 1, str(len(new_prod)))
if new_prod:
    check("新货品分类=挂件", new_prod[0].get("category_name") == "挂件", str(new_prod[0].get("category_name")))
    imgs = new_prod[0].get("images") or []
    check("新货品图片建档", len(imgs) == 1, str(imgs))
    check("新货品单位=个", new_prod[0].get("unit") == "个", str(new_prod[0].get("unit")))

# 入库流水：新货品应有一条 in 记录
r = client.get("/api/stock/logs", params={"keyword": "新兔子"}, headers=H)
check("新货品入库流水", r.status_code == 200 and r.json()["total"] >= 1 and r.json()["items"][0]["log_type"] == "in", r.text)

# 重复确认被拦截
r = client.post(f"/api/purchases/{po_id}/confirm", headers=H)
check("重复确认被拦截", r.status_code == 400, r.text)

# 已入库单不可修改
r = client.put(f"/api/purchases/{po_id}", json={"supplier_id": sup_id, "items": []}, headers=H)
check("已入库单不可修改", r.status_code == 400, r.text)

# ---- 待建档项未填名称 → 入库被拒（回滚） ----
r = client.post("/api/purchases", json={
    "supplier_id": sup_id, "items": [
        {"status": "draft", "quantity": 3, "unit_price": 1, "draft_name": "",
         "draft_barcode": "690000000088"}
    ]
}, headers=H)
bad_po = r.json()["id"]
r = client.post(f"/api/purchases/{bad_po}/confirm", headers=H)
check("未填名称建档被拒", r.status_code == 400, r.text)

# 拒单后可删除该草稿
r = client.delete(f"/api/purchases/{bad_po}", headers=H)
check("删除草稿采购单", r.status_code == 200)

# ---- 供应商被采购单引用不可删 ----
r = client.delete(f"/api/suppliers/{sup_id}", headers=H)
check("被引用供应商不可删", r.status_code == 400, r.text)

# 清理临时测试供应商数据前先删掉测试采购单（仅用于测试环境）
print("\n================ 结果 ================")
print("PASS:", passed, " FAIL:", len(failed))
if failed:
    print("FAILED:", failed)
    sys.exit(1)
print("ALL GREEN")
