# -*- coding: utf-8 -*-
"""标签打印布局模板（LabelTemplate）模块回归：
1) 未登录拦截 401
2) 创建 / 列表 / 默认模板 / 更新 / 删除 CRUD
3) is_default 同类型互斥规则
4) 账号隔离：boss 与 staff 各自模板互不可见、不可互改
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

# ============ 未登录拦截 ============
for path in ["/api/label-templates", "/api/label-templates/default"]:
    r = client.get(path)
    check(f"未登录GET {path} 拦截401", r.status_code == 401, f"{r.status_code}")
r = client.post("/api/label-templates", json={"name": "x", "type": "goods"})
check("未登录POST 拦截401", r.status_code == 401, f"{r.status_code}")

# ============ 创建 ============
r = client.post("/api/label-templates", json={
    "name": "商品默认-简洁", "type": "goods",
    "data": '{"elements":[{"id":"barcode","visible":true}]}',
    "is_default": True,
}, headers=HB)
check("创建goods默认模板", r.status_code == 200, r.text)
g1 = r.json()["id"]
check("创建后字段回读", r.json()["name"] == "商品默认-简洁" and r.json()["type"] == "goods"
      and r.json()["is_default"] is True and r.json()["user_id"] == r.json()["user_id"], r.text)

r = client.post("/api/label-templates", json={
    "name": "商品-大字", "type": "goods",
    "data": '{"elements":[{"id":"name","fontSizeMm":8}]}',
    "is_default": True,
}, headers=HB)
check("创建第2个goods默认模板", r.status_code == 200, r.text)
g2 = r.json()["id"]
check("新默认模板 is_default=True", r.json()["is_default"] is True, r.text)

# 互斥：第1个模板应被置为非默认
r = client.get("/api/label-templates", params={"type": "goods"}, headers=HB)
items = r.json()
m1 = next(x for x in items if x["id"] == g1)
check("同类型互斥：旧模板 is_default=False", m1["is_default"] is False, str(m1))
check("新模板 is_default=True", next(x for x in items if x["id"] == g2)["is_default"] is True, "")

# 物流模板独立于商品
r = client.post("/api/label-templates", json={
    "name": "面单-标准", "type": "logistics",
    "data": '{"elements":[{"id":"company","bold":true}]}',
    "is_default": True,
}, headers=HB)
check("创建logistics默认模板", r.status_code == 200, r.text)
l1 = r.json()["id"]

# ============ 列表 / 类型过滤 ============
r = client.get("/api/label-templates", headers=HB)
check("列表全量≥3", r.status_code == 200 and len(r.json()) >= 3, r.text)
r = client.get("/api/label-templates", params={"type": "goods"}, headers=HB)
check("type=goods 过滤(2条)", r.status_code == 200 and all(x["type"] == "goods" for x in r.json())
      and len(r.json()) == 2, r.text)
r = client.get("/api/label-templates", params={"type": "logistics"}, headers=HB)
check("type=logistics 过滤(1条)", r.status_code == 200 and all(x["type"] == "logistics" for x in r.json())
      and len(r.json()) == 1, r.text)

# ============ 默认模板获取 ============
r = client.get("/api/label-templates/default", params={"type": "goods"}, headers=HB)
check("goods默认模板=g2", r.status_code == 200 and r.json() and r.json()["id"] == g2, r.text)
r = client.get("/api/label-templates/default", params={"type": "logistics"}, headers=HB)
check("logistics默认模板=l1", r.status_code == 200 and r.json() and r.json()["id"] == l1, r.text)
# 不存在的类型：无默认返回 null
r = client.get("/api/label-templates/default", params={"type": "unknown"}, headers=HB)
check("未知类型默认返回null", r.status_code == 200 and r.json() is None, r.text)

# ============ 更新 ============
r = client.put(f"/api/label-templates/{g2}", json={
    "name": "商品-特大字",
    "data": '{"elements":[{"id":"name","fontSizeMm":12,"bold":true}]}',
}, headers=HB)
check("更新名称与data", r.status_code == 200 and r.json()["name"] == "商品-特大字"
      and '"fontSizeMm":12' in r.json()["data"], r.text)

# 更新时设 is_default=true 应互斥（此时 g2 已是默认，改用 g1）
r = client.put(f"/api/label-templates/{g1}", json={"is_default": True}, headers=HB)
check("更新is_default=true", r.status_code == 200 and r.json()["is_default"] is True, r.text)
r = client.get("/api/label-templates", params={"type": "goods"}, headers=HB)
items = r.json()
check("更新后互斥：g1默认 g2非默认",
      next(x for x in items if x["id"] == g1)["is_default"] is True
      and next(x for x in items if x["id"] == g2)["is_default"] is False, r.text)

# ============ 删除 ============
r = client.delete(f"/api/label-templates/{l1}", headers=HB)
check("删除物流模板", r.status_code == 200, r.text)
r = client.delete(f"/api/label-templates/{l1}", headers=HB)
check("删除不存在404", r.status_code == 404, f"{r.status_code}")

# ============ 账号隔离 ============
# staff 账号
r = client.post("/api/users", json={"username": "staff_tpl", "password": "staff123",
                                    "nickname": "店员", "role": "staff"}, headers=HB)
check("创建staff账号", r.status_code == 200, r.text)
staff_token = login("staff_tpl", "staff123")
HS = auth(staff_token)

# staff 列表应看不到 boss 的模板（0 条）
r = client.get("/api/label-templates", headers=HS)
check("staff列表为空(隔离)", r.status_code == 200 and r.json() == [], r.text)

# staff 创建自己的模板
r = client.post("/api/label-templates", json={
    "name": "店员商品模板", "type": "goods", "data": "{}", "is_default": True,
}, headers=HS)
check("staff创建模板", r.status_code == 200, r.text)
sg = r.json()["id"]

# staff 访问 boss 的模板：更新/删除被 404 拒绝
r = client.put(f"/api/label-templates/{g1}", json={"name": "篡改"}, headers=HS)
check("staff改boss模板404", r.status_code == 404, f"{r.status_code}")
r = client.delete(f"/api/label-templates/{g1}", headers=HS)
check("staff删boss模板404", r.status_code == 404, f"{r.status_code}")

# staff 自己的默认模板互不影响 boss
r = client.get("/api/label-templates/default", params={"type": "goods"}, headers=HS)
check("staff默认模板=自己的", r.status_code == 200 and r.json() and r.json()["id"] == sg, r.text)
r = client.get("/api/label-templates/default", params={"type": "goods"}, headers=HB)
check("boss默认模板仍=g1", r.status_code == 200 and r.json() and r.json()["id"] == g1, r.text)

# 空模板名拦截
r = client.post("/api/label-templates", json={"name": "  ", "type": "goods"}, headers=HB)
check("空模板名拦截400", r.status_code == 400, f"{r.status_code}")
# 非法类型拦截
r = client.post("/api/label-templates", json={"name": "x", "type": "bad"}, headers=HB)
check("非法类型拦截400", r.status_code == 400, f"{r.status_code}")

print("=" * 40)
print(f"TOTAL: {passed} passed, {len(failed)} failed")
if failed:
    print("FAILED:", failed)
    raise SystemExit(1)
