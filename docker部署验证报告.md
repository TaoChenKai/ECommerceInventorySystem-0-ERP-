---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 8cb4b16a2ae761ae637e563ea2323cd2_18462bd49ecc11f1a413525400287e28
    ReservedCode1: Aw6f7J+GXcPzXcC98OK4xXkFJxxJPpCU9gTZbCJBLN1s/oIjJYPasyayPWe437RJPuPAv7ysv6b6lOv1l+KLJ8d5OYIMq5Qh64KF3uohjWyPmLnRLWec1YpNVWwdgn8wK8hF50nro2VEcWt2xKGnHGRqQqajcKmxrRpxzDpLvJsUP9xaAS8v3hp0SvA=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 8cb4b16a2ae761ae637e563ea2323cd2_18462bd49ecc11f1a413525400287e28
    ReservedCode2: Aw6f7J+GXcPzXcC98OK4xXkFJxxJPpCU9gTZbCJBLN1s/oIjJYPasyayPWe437RJPuPAv7ysv6b6lOv1l+KLJ8d5OYIMq5Qh64KF3uohjWyPmLnRLWec1YpNVWwdgn8wK8hF50nro2VEcWt2xKGnHGRqQqajcKmxrRpxzDpLvJsUP9xaAS8v3hp0SvA=
---

# 电商库存管理系统 Docker 本地部署验证报告

- 验证时间：2026-08-23
- 部署位置：E:\ECommerceInventorySystem\deploy
- 环境：Windows 11 + Docker Desktop 4.87.0（WSL2 引擎，内核 6.18.33）

## 一、最终验证结论：成功

db（postgres:16-alpine）+ backend（python:3.12-slim + uvicorn）+ frontend（node 构建后 nginx:80）三服务完整构建、启动、访问验证通过，默认账号可正常登录。

| 验证项 | 结果 |
|---|---|
| 三容器状态 | 全部 Up（inventory-db / inventory-backend / inventory-frontend） |
| 后端 /api/health | HTTP 200，返回 {"status":"ok","service":"inventory","version":"0.2.0"}（经前端 80 端口反代验证） |
| 前端页面 http://localhost | HTTP 200，正常返回登录页 |
| 数据库连接 | 正常，17 张业务表全部建表成功 |
| 默认账号登录 | boss / admin123 登录成功，返回 access_token |
| 迁移列 | spus(weight_unit/designer/production_date/material)、sale_items(cost_price) 均存在 |

## 二、访问地址与账号

- 前端页面：http://localhost（或 http://<服务器IP>）
- 后端健康检查：http://localhost/api/health（后端 8000 端口不对外映射，经 nginx 反代访问）
- 数据库：127.0.0.1:5432，库 inventory，用户 inventory（仅本机监听）
- 默认账号：boss / admin123（首次登录后请尽快修改，由 .env 的 BOSS_PASSWORD 控制）

## 三、构建启动方式

```
# 进入部署目录
cd deploy
# 首次部署：生成环境配置（含数据库密码/密钥/老板账号）
cp .env.example .env     # Windows: copy .env.example .env
# 构建并后台启动
docker compose up -d --build
# 常用命令
docker compose ps        # 查看状态
docker compose logs -f   # 查看日志
docker compose down      # 停止（保留数据）
docker compose down -v   # 停止并清空数据库数据（不可恢复）
```

## 四、本次遇到并修复的问题清单

1. **backend 无法在 PostgreSQL 下启动（PRAGMA 语法错误）**
   根因：backend/app/main.py 的 ensure_schema() 轻量迁移使用 SQLite 专属的 `PRAGMA table_info`，在 PostgreSQL 下语法不支持，导致启动失败。
   修复：新增 `_table_columns(db, table)` 辅助函数，按数据库类型分支——PostgreSQL 走 `information_schema.columns`，SQLite 保留原 `PRAGMA table_info`；ensure_schema() 内 3 处列检查全部改用该函数。ALTER TABLE 语句两库语法兼容，未改动。
   影响：本地开发（SQLite start.bat）行为不变，未破坏本地环境。

2. **Docker Hub 镜像拉取被拒（网络无法直连 registry）**
   现象：`docker pull postgres:16-alpine` 报 "dial tcp ... connectex: No connection could be made"。
   修复：在本机 Docker daemon 配置（C:\Users\Administrator\.docker\daemon.json）新增国内镜像加速 registry-mirrors：docker.1ms.run / docker.m.daocloud.io / docker.1panel.live，重启 Docker Desktop 后生效。原配置已备份。

3. **backend 与 db 启动竞态（首启瞬时报错，自动恢复）**
   现象：首次 compose up 时 backend 比 db 先就绪，create_all 连接被拒，容器短暂退出。
   处理：compose 已配置 restart: unless-stopped，backend 自动重启后正常启动，无需人工干预。后续启动（db 已存在）无此问题。

4. **启动脚本编码提示**：start-docker.sh / stop-docker.sh 为 Linux bash 脚本（中文注释在 Windows 下显示为乱码），Windows 下直接执行 docker compose 命令即可，脚本仅用于服务器。

## 五、"新电脑一键跑起来"部署要点（供 README 部署章节使用）

前置条件（一次性）：
1. 安装 Docker Desktop 并启用 WSL2（若无法直连 Docker Hub，按第四节问题2配置国内镜像加速）
2. 本机需可访问 80 与 5432 端口（5432 仅监听 127.0.0.1）

一键启动：
```
cd deploy
copy .env.example .env   # Linux: cp .env.example .env
docker compose up -d --build
```

访问：
- 网页：http://localhost，账号 boss / admin123（生产部署前务必修改 .env 中 BOSS_PASSWORD 与 SECRET_KEY）
- 健康检查：http://localhost/api/health

生产部署注意：
- 服务器上执行 `bash start-docker.sh` 一键启动（会自动生成 .env 并询问是否修改默认密码）
- .env 中的 POSTGRES_PASSWORD / SECRET_KEY / BOSS_PASSWORD 部署前必须改为强随机值
- 停服：`docker compose down`（保留数据）；彻底清理：`docker compose down -v`
- 数据持久化：数据库数据存于 named volume pgdata，容器重建不丢失

## 六、本次改动文件记录

| 文件 | 改动 |
|---|---|
| backend/app/main.py | 新增 _table_columns() 按库类型取列名，ensure_schema() 3 处 PRAGMA 改用它（PostgreSQL 兼容） |
| C:\Users\Administrator\.docker\daemon.json | 新增 registry-mirrors 国内镜像加速（原配置已备份） |
| deploy\.env | 由 .env.example 复制生成，内容未改（部署配置） |
*（内容由AI生成，仅供参考）*
