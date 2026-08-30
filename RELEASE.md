---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 8cb4b16a2ae761ae637e563ea2323cd2_37ba8bf99ed011f1a65b525400826444
    ReservedCode1: s4437n6DQpUZCBN4sJWIdZ4DLhrgqRnyBFztu4iGwOQQC7vH5UPlI5Kr3UpjhXtUi3gMCvXDll5rG8in9YQhUlFTgH46PoeF/4XcWDbp6nGmQmBdbSL1oluhYX0ffdhpjaE4i9Xq0gXThcixt8ELdK6Jw9LVvbziEw7KDBHwK+myrqPDWjPkB9cr/AI=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 8cb4b16a2ae761ae637e563ea2323cd2_37ba8bf99ed011f1a65b525400826444
    ReservedCode2: s4437n6DQpUZCBN4sJWIdZ4DLhrgqRnyBFztu4iGwOQQC7vH5UPlI5Kr3UpjhXtUi3gMCvXDll5rG8in9YQhUlFTgH46PoeF/4XcWDbp6nGmQmBdbSL1oluhYX0ffdhpjaE4i9Xq0gXThcixt8ELdK6Jw9LVvbziEw7KDBHwK+myrqPDWjPkB9cr/AI=
---

# RELEASE — 电商库存管理系统 PC 端 v1.0 发行指南

> 本文档面向开发者：如何把本地已完成验收的 `ECommerceInventorySystem` 源码发布到自己的 GitHub 仓库，以及后续版本如何维护。

---

## 1. 发布包内容说明

当前发布包为「干净源码包」，仅包含源代码与运行必需文件，**不含**本地开发依赖与业务数据：

```
ECommerceInventorySystem-PC-v1.0-YYYYMMDD.zip
├── backend/       # FastAPI 后端源码（app/ + 7 个回归测试 test_*.py + requirements.txt + Dockerfile + .env.example）
├── frontend/      # Vue 3 + Vite 前端源码（src/ + package.json + nginx.conf + Dockerfile）
├── deploy/        # Docker Compose 部署配置（docker-compose.yml + start/stop-docker.sh + .env.example）
├── docs/          # 设计文档（电商库存管理系统设计文档.html）
├── README.md      # 项目说明（功能清单 / 本地启动 / Docker 部署 / 回归测试）
├── .gitignore     # Git 忽略规则
├── start.bat      # Windows 一键启动脚本
└── stop.bat       # Windows 一键停止脚本
```

**已排除**（不随源码发布，可在任意新机器按 README 重新安装/生成）：

| 排除项 | 原因 |
|---|---|
| `backend/venv` | 本地 Python 虚拟环境 |
| `frontend/node_modules` | 前端 npm 依赖，用 `npm install` 重建 |
| `frontend/dist` | Vite 构建产物，用 `npm run build` 重建 |
| `.git/` | Git 元数据，推送后由 GitHub 生成 |
| `backend/inventory.db` | 本地业务数据库（含测试数据，生产用 PostgreSQL） |
| `*.log` / `__pycache__` / 临时 txt | 运行时缓存与调试残留 |
| `.env` | 含密钥的本地环境变量（只保留 `.env.example` 模板） |

---

## 2. 推送到自己的 GitHub

### 2.1 前置准备

1. 注册/登录 [GitHub](https://github.com)，点击右上角 `+` → **New repository**
2. 创建**空仓库**（**不要**勾选 "Add a README" / ".gitignore" / "license"，保持空仓库，避免与本地历史冲突）
3. 复制仓库地址，形如：`https://github.com/<你的用户名>/ECommerceInventorySystem.git`

### 2.2 本地命令（在项目根目录执行）

```bash
# 1. 关联远程仓库（替换成你自己的地址）
git remote add origin https://github.com/<你的用户名>/ECommerceInventorySystem.git

# 2. 检查本地状态（应无未提交改动；首次需先 git init + git add + git commit，见 2.3）
git status

# 3. 推送 master 分支到 GitHub（-u 建立跟踪关系，以后直接 git push 即可）
git push -u origin master

# 4. 验证：浏览器打开仓库页面，确认 backend/frontend/deploy/README.md 等已上传
```

### 2.3 首次使用 Git（若尚未初始化）

```bash
# 在项目根目录初始化仓库并提交（本地库已存在则跳过 init）
git init
git add .
git commit -m "chore: ECommerceInventorySystem PC v1.0 初稿"

# 身份信息仅首次需要（把名字/邮箱换成你自己的）
git config user.name "你的名字"
git config user.email "you@example.com"
```

> 提示：`.gitignore` 已排除 venv/node_modules/dist/inventory.db/*.log 等，可放心 `git add .`。

---

## 3. 后续版本打 Tag 与推送

每次发布新版本时，在功能确认、回归通过后打 tag：

```bash
# 1. 先提交本次所有改动
git add .
git commit -m "feat: v1.1 新增 xxx 功能"

# 2. 打 tag（版本号自定，如 v1.1）
git tag v1.1

# 3. 推送代码 + 推送 tag（--tags 会把所有 tag 一起推上去）
git push -u origin master
git push --tags
```

**常用维护命令：**

```bash
git tag                 # 查看所有 tag
git push origin v1.1    # 只推送指定 tag
git tag -d v1.1         # 删除本地 tag（未推送时）
git status              # 查看工作区是否有未提交改动
```

---

## 4. 发行前检查清单

发布（推送 GitHub / 发布 Release）前逐项确认：

- [ ] 后端回归全过：`backend` 下 7 个 `test_*.py` 全部 PASS（240 项），无 FAIL
- [ ] 前端构建成功：`frontend` 下 `npm run build` 无报错，dist 正常产出
- [ ] 功能清单核对：README「已实现功能清单」10 项与代码实现一一对应，无遗留 TODO
- [ ] 敏感信息排查：`.env`（含密钥/密码）未入库、未进包；只保留 `.env.example`
- [ ] 业务数据隔离：`inventory.db` 未入库、未进包；`deploy/.env` 未进包
- [ ] 清理完成：无 `__pycache__` / `*.log` / `test_*.db` / 临时 txt 残留
- [ ] Docker 部署可启动：`docker compose up -d --build` 三服务正常，`/api/health` 返回 200
- [ ] 默认账号可登录：boss/admin123（生产部署前务必改 `.env` 密码）
- [ ] 生产必改项确认：`POSTGRES_PASSWORD` / `SECRET_KEY` / `BOSS_PASSWORD` 已更换

---

## 5. Release 发布（可选）

推送 GitHub 后可创建正式 Release：

1. 仓库页面 → `Releases` → `Create a new release`
2. Tag 选择 `v1.0`（或最新 tag），标题如 `PC v1.0 初稿`
3. 附件上传本发布包 `ECommerceInventorySystem-PC-v1.0-YYYYMMDD.zip`
4. 正文简要列出本次功能清单与变更，发布

---

## 6. 本次发布信息

| 项 | 值 |
|---|---|
| 版本 | PC v1.0 初稿 |
| 后端 | FastAPI + SQLite/PostgreSQL |
| 前端 | Vue 3 + Vite |
| 回归 | 240 PASS（7 个测试文件） |
| 默认账号 | boss / admin123（生产环境需修改） |
*（内容由AI生成，仅供参考）*
