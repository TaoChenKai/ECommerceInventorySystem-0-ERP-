# -*- coding: utf-8 -*-
"""标签打印模块回归：
1) Spu 新增三字段（designer / production_date / material）增改查
2) 常用发件人 SenderProfile CRUD（含登录拦截）
连接已启动的真实 uvicorn（隔离临时库），走 HTTP 请求。"""
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


boss = login("boss", "admin123")
HB = auth(boss)
check("登录boss", True)

# ---- 未登录访问 senders 被拦 ----
r = client.get("/api/senders")
check("未登录GET /api/senders 拦截401", r.status_code == 401, f"{r.status_code}")
r = client.post("/api/senders", json={"name": "x", "sender_name": "x"})
check("未登录POST /api/senders 拦截401", r.status_code == 401, f"{r.status_code}")

# ============ 一、Spu 三字段增改查 ============
r = client.post("/api/spus", json={
    "name": "标签测试商品A", "code": "LBL-A01", "unit": "件", "weight": 0.35,
    "weight_unit": "千克",
    "designer": "0号仓库工作室",
    "production_date": "2026-08-01",
    "material": "纯棉",
    "images": [], "skus": [
        {"spec_name": "红色XL", "sku_code": "LBL-A01-RXL", "barcode": "690000099901",
         "cost_price": 30, "sale_price": 99, "stock": 20}
    ]
}, headers=HB)
check("创建商品(带三字段)", r.status_code == 200, r.text)
spu_id = r.json()["id"]
sku_id = r.json()["skus"][0]["id"]
check("创建后 designer 回读", r.json().get("designer") == "0号仓库工作室", r.text)
check("创建后 production_date 回读", r.json().get("production_date") == "2026-08-01", r.text)
check("创建后 material 回读", r.json().get("material") == "纯棉", r.text)

# 列表接口也带三字段
r = client.get("/api/spus", params={"keyword": "标签测试商品A"}, headers=HB)
check("列表接口含三字段", r.status_code == 200 and r.json() and r.json()[0].get("designer") == "0号仓库工作室", r.text)

# 修改三字段
r = client.put(f"/api/spus/{spu_id}", json={
    "name": "标签测试商品A", "code": "LBL-A01", "unit": "件", "weight": 0.4,
    "weight_unit": "千克",
    "designer": "设计二部",
    "production_date": "2026-08-15",
    "material": "聚酯纤维",
    "images": [], "skus": [
        {"id": sku_id,
         "spec_name": "红色XL", "sku_code": "LBL-A01-RXL", "barcode": "690000099901",
         "cost_price": 30, "sale_price": 99, "stock": 20}
    ]
}, headers=HB)
check("修改商品(三字段)", r.status_code == 200, r.text)
check("修改后 designer", r.json().get("designer") == "设计二部", r.text)
check("修改后 production_date", r.json().get("production_date") == "2026-08-15", r.text)
check("修改后 material", r.json().get("material") == "聚酯纤维", r.text)

# 三字段可空：清空日期（置 null）
r = client.put(f"/api/spus/{spu_id}", json={
    "name": "标签测试商品A", "code": "LBL-A01", "unit": "件", "weight": 0.4,
    "weight_unit": "千克", "designer": "", "production_date": None, "material": "",
    "images": [], "skus": [
        {"spec_name": "红色XL", "sku_code": "LBL-A01-RXL", "barcode": "690000099901",
         "cost_price": 30, "sale_price": 99, "stock": 20}
    ]
}, headers=HB)
check("清空三字段可空", r.status_code == 200 and r.json().get("production_date") is None, r.text)

# ============ 二、常用发件人 CRUD ============
# staff 账号也应可见（get_current_user 即可）
r = client.post("/api/users", json={"username": "staff_lbl", "password": "staff123",
                                    "nickname": "店员", "role": "staff"}, headers=HB)
check("创建staff账号", r.status_code == 200, r.text)
staff_token = login("staff_lbl", "staff123")
HS = auth(staff_token)

# 创建（boss）
r = client.post("/api/senders", json={
    "name": "店里", "sender_name": "王老板", "phone": "13800001111",
    "address": "广东省广州市天河区某某路1号", "remark": "门店默认"
}, headers=HB)
check("创建发件人1", r.status_code == 200, r.text)
sid1 = r.json()["id"]
check("发件人1字段", r.json().get("sender_name") == "王老板" and r.json().get("name") == "店里", r.text)

r = client.post("/api/senders", json={
    "name": "工厂", "sender_name": "李厂长", "phone": "13900002222",
    "address": "浙江省杭州市余杭区某某工业园", "remark": ""
}, headers=HB)
check("创建发件人2", r.status_code == 200, r.text)
sid2 = r.json()["id"]

# 列表（staff 可见）
r = client.get("/api/senders", headers=HS)
check("staff查看发件人列表", r.status_code == 200 and len(r.json()) >= 2, r.text)

# 修改
r = client.put(f"/api/senders/{sid1}", json={
    "name": "门店总店", "sender_name": "王老板", "phone": "13800001111",
    "address": "广东省广州市天河区某某路100号", "remark": "总店"
}, headers=HB)
check("修改发件人", r.status_code == 200 and r.json().get("address").endswith("100号"), r.text)

# 空发件人姓名拦截
r = client.post("/api/senders", json={"name": "x", "sender_name": ""}, headers=HB)
check("空姓名拦截400", r.status_code == 400, f"{r.status_code}")

# 删除 + 404
r = client.delete(f"/api/senders/{sid2}", headers=HB)
check("删除发件人", r.status_code == 200, r.text)
r = client.delete(f"/api/senders/{sid2}", headers=HB)
check("删除不存在404", r.status_code == 404, f"{r.status_code}")

print("=" * 40)
print(f"TOTAL: {passed} passed, {len(failed)} failed")
if failed:
    print("FAILED:", failed)
    raise SystemExit(1)
