# -*- coding: utf-8 -*-
"""操作日志清理回归：手动清理权限(staff 403 / admin·boss 200)、按时间清理、全清、自动清理函数
连接已启动的真实 uvicorn（隔离临时库）走 HTTP；函数级自动清理直连同一库验证。
"""
import os
import sys
from datetime import datetime, timedelta

# ---- 直连同一隔离库：与启动 uvicorn 时的环境变量保持一致（控制脚本注入） ----
TEST_DB_DIR = os.environ.get("AUDIT_TEST_DB_DIR", "")
if TEST_DB_DIR:
    os.environ.setdefault("DATABASE_URL",
                          "sqlite:///" + os.path.join(TEST_DB_DIR, "inventory.db").replace("\\", "/"))
    os.environ.setdefault("DATA_DIR", TEST_DB_DIR)

import httpx
from app.database import SessionLocal
from app.models import AuditLog
from app.routers.audit import cleanup_old_audits

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


def insert_log(dt, action):
    s = SessionLocal()
    try:
        s.add(AuditLog(username="tester", action=action, detail="", created_at=dt))
        s.commit()
    finally:
        s.close()


def list_actions(token):
    r = client.get("/api/audits", headers=auth(token))
    assert r.status_code == 200, r.text
    return [a["action"] for a in r.json()]


# ---- 准备账号（独立库：boss 自动创建，admin/staff 需自行建立，容错已存在） ----
H = auth(login("boss", "admin123"))
for uname, pwd, nick, role in [("admin1", "admin123", "管理员", "admin"),
                               ("staff1", "staff123", "员工", "staff")]:
    r = client.post("/api/users", json={"username": uname, "password": pwd,
                                        "nickname": nick, "role": role}, headers=H)
    assert r.status_code in (200, 400), r.text
HA = auth(login("admin1", "admin123"))
HS = auth(login("staff1", "staff123"))
check("登录boss/admin/staff", True)

# ---- 权限：staff 调 DELETE 得 403 ----
r = client.delete("/api/audits", headers=HS)
check("staff清理被拒(403)", r.status_code == 403, r.text)

# ---- 全清：admin 得 200，清空后列表为空 ----
r = client.delete("/api/audits", headers=HA)
check("admin全清成功(200)", r.status_code == 200 and r.json().get("deleted", -1) >= 0, r.text)
r = client.get("/api/audits", headers=H)
check("全清后列表为空", r.status_code == 200 and r.json() == [], r.text)

# ---- 按时间清理（boss）：只删目标时间之前的记录 ----
now = datetime.utcnow()
insert_log(now - timedelta(days=100), "old_100d")
insert_log(now - timedelta(days=10), "mid_10d")
insert_log(now - timedelta(days=1), "new_1d")
before = (now - timedelta(days=30)).isoformat()
r = client.delete("/api/audits", params={"before": before}, headers=H)
check("boss按时间清理成功", r.status_code == 200 and r.json()["deleted"] == 1, r.text)
actions = list_actions(login("boss", "admin123"))
check("按时间清理只删100天前的",
      "old_100d" not in actions and "mid_10d" in actions and "new_1d" in actions,
      str(actions))

# ---- 非法 before 参数被拒 ----
r = client.delete("/api/audits", params={"before": "not-a-date"}, headers=H)
check("非法before被拒(400)", r.status_code == 400, r.text)

# ---- admin 也能按时间清理（权限双确认） ----
r = client.delete("/api/audits", params={"before": (now - timedelta(days=5)).isoformat()}, headers=HA)
check("admin按时间清理成功", r.status_code == 200 and r.json()["deleted"] >= 1, r.text)
actions = list_actions(login("boss", "admin123"))
check("admin清理后仅剩1天记录",
      "new_1d" in actions and "mid_10d" not in actions and "old_100d" not in actions,
      str(actions))

# ---- 自动清理函数：只删 90 天前 ----
r = client.delete("/api/audits", headers=H)
check("清理残留(全清)", r.status_code == 200, r.text)
insert_log(now - timedelta(days=100), "auto_old_100d")
insert_log(now - timedelta(days=1), "auto_new_1d")
s = SessionLocal()
try:
    deleted = cleanup_old_audits(s)
finally:
    s.close()
check("自动清理只删90天前(1条)", deleted == 1, f"deleted={deleted}")
remaining = []
s = SessionLocal()
try:
    remaining = [a.action for a in s.query(AuditLog).all()]
finally:
    s.close()
check("自动清理后仅剩1天记录",
      "auto_new_1d" in remaining and "auto_old_100d" not in remaining, str(remaining))

print("\n================ 结果 ================")
print("PASS:", passed, " FAIL:", len(failed))
if failed:
    print("FAILED:", failed)
    sys.exit(1)
print("ALL GREEN")
