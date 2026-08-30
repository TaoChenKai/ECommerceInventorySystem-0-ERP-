# -*- coding: utf-8 -*-
"""分类/单位/重量单位自由输入回归：新建分类名建档、编辑改分类、新单位补录"""
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


r = client.post("/api/auth/login", data={"username": "boss", "password": "admin123"})
assert r.status_code == 200, r.text
H = {"Authorization": "Bearer " + r.json()["access_token"]}
check("登录boss", True)

import time
suffix = str(int(time.time()) % 1000000)
NEW_CAT = "新分类_" + suffix
NEW_UNIT = "键_新_" + suffix
NEW_WUNIT = "克拉_新_" + suffix

# 1) 新建商品：只传新分类名 + 新单位 + 新重量单位，后端应自动建档
r = client.post("/api/spus", json={
    "name": "分类建档测试", "code": "CAT01_" + suffix, "category_id": None,
    "category_name": NEW_CAT, "unit": NEW_UNIT, "weight": 0.05, "weight_unit": NEW_WUNIT,
    "images": [], "skus": [
        {"spec_name": "默认", "sku_code": "CAT01_" + suffix, "barcode": "", "cost_price": 1, "sale_price": 2, "stock": 3}
    ]
}, headers=H)
check("新建分类名+新单位建档", r.status_code == 200, r.text)
spu_id = r.json().get("id")
check("返回分类id", r.json().get("category_id") is not None, r.text)

# 2) 分类列表里能查到新分类
r = client.get("/api/categories", headers=H)
cats = r.json()
check("新分类已进入分类列表", any(c["name"] == NEW_CAT for c in cats), str(cats))
new_cat_id = next((c["id"] for c in cats if c["name"] == NEW_CAT), None)

# 3) 商品详情里分类名正确
r = client.get(f"/api/spus/{spu_id}", headers=H)
check("详情分类名=新分类", r.json().get("category_name") == NEW_CAT, r.text)
check("详情单位=新单位", r.json().get("unit") == NEW_UNIT, r.text)
check("详情重量单位=新重量单位", r.json().get("weight_unit") == NEW_WUNIT, r.text)

# 4) 编辑该商品：改成一个新的分类名，再次建档
NEW_CAT2 = "新分类2_" + suffix
r = client.put(f"/api/spus/{spu_id}", json={
    "name": "分类建档测试", "code": "CAT01_" + suffix, "category_id": None,
    "category_name": NEW_CAT2, "unit": NEW_UNIT, "weight": 0.05, "weight_unit": NEW_WUNIT,
    "images": [], "skus": [
        {"id": r.json()["skus"][0]["id"], "spec_name": "默认", "sku_code": "CAT01_" + suffix, "barcode": "", "cost_price": 1, "sale_price": 2, "stock": 3}
    ]
}, headers=H)
check("编辑改为新分类名", r.status_code == 200 and r.json().get("category_name") == NEW_CAT2, r.text)

# 5) 编辑改为"未分类"（category_name 空 + category_id 空）
r = client.put(f"/api/spus/{spu_id}", json={
    "name": "分类建档测试", "code": "CAT01_" + suffix, "category_id": None,
    "category_name": "", "unit": NEW_UNIT, "weight": 0.05, "weight_unit": NEW_WUNIT,
    "images": [], "skus": [
        {"id": r.json()["skus"][0]["id"], "spec_name": "默认", "sku_code": "CAT01_" + suffix, "barcode": "", "cost_price": 1, "sale_price": 2, "stock": 3}
    ]
}, headers=H)
check("编辑清除为未分类", r.status_code == 200 and r.json().get("category_id") is None, r.text)

# 6) 单位字典自动补录：新单位/新重量单位出现在字典列表
r = client.get("/api/units", headers=H)
check("新单位已补录字典", any(x["name"] == NEW_UNIT for x in r.json()), str(r.json()))
r = client.get("/api/weight-units", headers=H)
check("新重量单位已补录字典", any(x["name"] == NEW_WUNIT for x in r.json()), str(r.json()))

# 7) 复用已有分类 id（category_id 直传仍可用）
r = client.post("/api/spus", json={
    "name": "分类id测试", "code": "CAT02_" + suffix, "category_id": new_cat_id,
    "category_name": "", "unit": "件", "weight": 0, "weight_unit": "千克",
    "images": [], "skus": [
        {"spec_name": "默认", "sku_code": "CAT02_" + suffix, "barcode": "", "cost_price": 1, "sale_price": 2, "stock": 0}
    ]
}, headers=H)
check("category_id直传仍可用", r.status_code == 200 and r.json().get("category_id") == new_cat_id, r.text)

# 8) 重复新分类名：第二次引用同名不再重复建分类
r = client.get("/api/categories", headers=H)
cats2 = r.json()
check("重复分类名复用不重复建档", sum(1 for c in cats2 if c["name"] == NEW_CAT2) == 1, str(cats2))

print("\n================ 结果 ================")
print("PASS:", passed, " FAIL:", len(failed))
if failed:
    print("FAILED:", failed)
    sys.exit(1)
print("ALL GREEN")
