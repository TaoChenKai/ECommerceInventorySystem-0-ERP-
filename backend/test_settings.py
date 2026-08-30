# -*- coding: utf-8 -*-
"""设置中心模块接口回归：偏好CRUD/独立性、背景图上传删除、存储迁移(备份/校验/回滚/权限)、云端占位
连接已启动的真实 uvicorn（隔离临时库），走 HTTP 请求。
"""
import sys
import httpx

BASE = "http://127.0.0.1:8765"
client = httpx.Client(base_url=BASE, timeout=30)

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


# ---- 准备：boss / admin / staff 账号 ----
boss = login("boss", "admin123")
H = auth(boss)
check("登录boss", True)

r = client.post("/api/users", json={"username": "admin1", "password": "admin123",
                                    "nickname": "管理员", "role": "admin"}, headers=H)
check("创建admin账号", r.status_code == 200, r.text)
r = client.post("/api/users", json={"username": "staff1", "password": "staff123",
                                    "nickname": "员工", "role": "staff"}, headers=H)
check("创建staff账号", r.status_code == 200, r.text)

admin = login("admin1", "admin123")
staff = login("staff1", "staff123")
HA = auth(admin)
HS = auth(staff)
check("admin/staff登录", True)

# ---- 偏好：默认值 ----
r = client.get("/api/settings/preference", headers=H)
check("boss默认偏好", r.status_code == 200 and r.json()["theme"] == "light"
      and r.json()["theme_color"] == "default" and r.json()["bg_image"] == "", r.text)

# ---- 偏好：保存与读取 ----
r = client.put("/api/settings/preference", json={"theme": "dark", "theme_color": "night", "bg_image": ""}, headers=H)
check("保存boss偏好(暗夜)", r.status_code == 200 and r.json()["theme"] == "dark"
      and r.json()["theme_color"] == "night", r.text)
r = client.get("/api/settings/preference", headers=H)
check("读取boss偏好(已保存)", r.json()["theme"] == "dark" and r.json()["theme_color"] == "night", r.text)

# ---- 偏好：用户间独立 ----
r = client.get("/api/settings/preference", headers=HS)
check("staff偏好独立(仍默认)", r.json()["theme"] == "light" and r.json()["theme_color"] == "default", r.text)
r = client.put("/api/settings/preference", json={"theme": "random", "theme_color": "mint", "bg_image": ""}, headers=HS)
check("staff保存偏好(薄荷)", r.status_code == 200 and r.json()["theme_color"] == "mint", r.text)
r = client.get("/api/settings/preference", headers=H)
check("boss偏好不受staff影响(仍暗夜)", r.json()["theme_color"] == "night", r.text)

# ---- 背景图：上传 / 访问 / 删除 ----
png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
r = client.post("/api/settings/preference/bg-image",
                files={"file": ("bg.png", png, "image/png")}, headers=HS)
check("上传背景图", r.status_code == 200 and r.json()["filename"] == "bg_3.png", r.text)
bg_url = r.json()["url"]
r = client.get(bg_url)
check("背景图可通过/media访问", r.status_code == 200 and r.content == png, r.text)
r = client.get("/api/settings/preference", headers=HS)
check("staff偏好含背景图", r.json()["bg_image"] == "bg_3.png", r.text)

# 非法文件类型被拒
r = client.post("/api/settings/preference/bg-image",
                files={"file": ("x.txt", b"hello", "text/plain")}, headers=HS)
check("非法类型被拒(400)", r.status_code == 400, r.text)

r = client.delete("/api/settings/preference/bg-image", headers=HS)
check("删除背景图", r.status_code == 200 and r.json()["removed"] is True, r.text)
r = client.get("/api/settings/preference", headers=HS)
check("删除后bg_image为空", r.json()["bg_image"] == "", r.text)

# ---- 权限：存储/系统设置仅 boss / admin ----
r = client.get("/api/settings/storage", headers=HS)
check("staff访问存储信息被拒(403)", r.status_code == 403, r.text)
r = client.post("/api/settings/storage/migrate", json={"new_dir": "D:/whatever"}, headers=HS)
check("staff迁移被拒(403)", r.status_code == 403, r.text)
r = client.get("/api/settings/storage", headers=HA)
check("admin可访问存储信息", r.status_code == 200, r.text)
r = client.get("/api/settings/storage", headers=H)
check("boss可访问存储信息", r.status_code == 200 and r.json()["data_dir"], r.text)

# ---- 云端备份占位 ----
r = client.get("/api/settings/cloud-backup", headers=HS)
check("云端备份占位(available=False)", r.status_code == 200 and r.json()["available"] is False, r.text)

# ---- 数据迁移：相同目录 / 子目录被拒 ----
r = client.get("/api/settings/storage", headers=H)
cur = r.json()["data_dir"]
r = client.post("/api/settings/storage/migrate", json={"new_dir": cur}, headers=H)
check("迁移到相同目录被拒(400)", r.status_code == 400, r.text)
import os
sub = os.path.join(cur, "sub_dir")
r = client.post("/api/settings/storage/migrate", json={"new_dir": sub}, headers=H)
check("迁移到子目录被拒(400)", r.status_code == 400, r.text)

# ---- 数据迁移：成功迁移且数据完整 ----
# 预建货品确保有数据
r = client.post("/api/spus", json={
    "name": "迁移测试货品", "code": "MIG01", "unit": "件", "weight": 0.1,
    "weight_unit": "千克", "images": [], "skus": [
        {"spec_name": "默认", "sku_code": "MIG01", "barcode": "690000001001",
         "cost_price": 10, "sale_price": 20, "stock": 5}
    ]
}, headers=H)
check("迁移前预建货品", r.status_code == 200, r.text)
import time
target = os.path.join(os.path.dirname(cur), "_migrated_dir_" + time.strftime("%H%M%S"))
r = client.post("/api/settings/storage/migrate", json={"new_dir": target}, headers=H)
check("数据目录迁移成功", r.status_code == 200, r.text)
r = client.get("/api/settings/storage", headers=H)
check("迁移后data_dir已更新", r.status_code == 200 and r.json()["data_dir"] == target, r.text)
check("迁移后db_path指向新库", r.json()["db_path"] == os.path.join(target, "inventory.db"), r.text)
# 数据完整：货品仍在 / 用户仍可登录
r2 = client.get("/api/spus", headers=H)
data = r2.json()
items = data.get("items") if isinstance(data, dict) else data
check("迁移后货品数据完整", r2.status_code == 200 and any(i["name"] == "迁移测试货品" for i in items), r2.text)
r = client.post("/api/auth/login", data={"username": "staff1", "password": "staff123"})
check("迁移后用户可登录(数据完整)", r.status_code == 200, r.text)

print("\n================ 结果 ================")
print("PASS:", passed, " FAIL:", len(failed))
if failed:
    print("FAILED:", failed)
    sys.exit(1)
print("ALL GREEN")
