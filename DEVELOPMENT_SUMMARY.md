---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 8cb4b16a2ae761ae637e563ea2323cd2_devsummary
    ReservedCode1: dev-summary-0hao
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 8cb4b16a2ae761ae637e563ea2323cd2_devsummary
    ReservedCode2: dev-summary-0hao
---

# 0号仓库库存管理系统 —— 开发总结（面向二次开发者）

> 版本：**PC 端 v1.3.3-Final** ｜ 更新日期：2026-08-28 ｜ 状态：正式版收尾，发布包可直接安装使用

---

## 一、项目概述

**0号仓库库存管理系统**是一个自研、免费、开源的电商小店 + 少量批发场景的 **PC 端库存管理 Web 应用**。

- **定位**：面向电商小店与少量批发场景的轻量库存管理工具，替代高收费的商业进销存软件。
- **核心价值**：数据自掌控（开源免费，不被收费软件卡脖子）；一套代码多端访问（本机 / 局域网 / 服务器浏览器访问）。
- **角色权限**：老板（boss）/ 管理员（admin）/ 员工（staff）三级权限。
- **技术形态**：前后端分离 Web 应用，本地一键启动，亦可 Docker 部署。
- **非商业化**：严禁商业化运营、抢注、仿冒或二次销售，详见 `DISCLAIMER.md`。

---

## 二、完整开发历程（版本时间线）

| 版本 | 日期 | 里程碑 |
|------|------|--------|
| **v1.0 初稿** | 2026-08-23 | 首个可用版本：商品档案 / 扫码出入库 / 采购入库 / 销售出库 / 财务对账 / 库存分析 / 标签打印 / 三级账号权限 / 渠道追踪 / 审计日志；本地 git 版本管理 + Docker 本地验证 + 回归测试通过 |
| **v1.1** | 2026-08-24 | 新增「设置中心」：UI 外观自定义（亮/暗/随机 + 6 套预设主题色 + 背景图 DIY，偏好存后端用户表换设备一致）、数据存储位置自定义（仅本机 SQLite 自动安全迁移：备份/校验/回滚，仅 boss / 管理员可用）、云端备份预留占位入口 |
| **v1.1.1** | 2026-08-24 | 新增「操作日志清理」：后端 `DELETE /api/audits`（boss / 管理员手动清理，按日期或清空）+ 启动自动清理（默认保留 90 天）；左侧目录栏固定（仅右侧内容区滚动） |
| **v1.2** | 2026-08-25 | UI 视觉升级：品牌登录页终末地工业风加载动画；新增「终末地·谷地黄 / 终末地·武陵青」两套全直角工业风主题；侧边栏动态收展；路由转场动画；粒子星云 HUD 噪点质感增强 |
| **v1.2.1** | 2026-08-25 | 主界面全面终末地工业风（面板/卡片/表格/按钮/弹窗/侧边栏统一设计令牌：全直角 + 工业细线 + 黄 `#fff500`/青 `#14d0d0` 强调 + 斜线网格 + HUD 角标）；新增主题概念背景系统（谷地黄=暖色工业废土城、武陵青=冷色科学院/科幻都市，SVG 代码自绘原创概念场景） |
| **v1.2.2** | 2026-08-26 | 主界面背景改用真实游戏场景太空星云截图（1920x1080），低透明度 + 主题色半透明遮罩；强化详情页主题辨识度（全面吃 `--accent/--primary` 令牌） |
| **v1.3** | 2026-08-26 | 货品软删除进回收站（deleted_at）、智能筛选时间线（1 月 ~ 3 年下拉）、回收站子页（批量删除/批量还原/彻底删除）、超 30 天自动清理、权限收紧为 boss/admin（员工 403） |
| **v1.3.1** | 2026-08-26 | 品牌更名「0号仓库库存管理系统」（替换原「星穹」）；侧边栏按「库存管理/运营分析/系统」分组，回收站改「商品回收站」二级子菜单；收起态品牌区常驻 |
| **v1.3.2** | 2026-08-26 | 背景换终末地官网风实机图（bg_day_05.jpg / bg_night_01.jpg）+ 径向遮罩；全量 git diff 确认背景机制零代码回归 |
| **v1.3.3** | 2026-08-27 | 主题背景本地缓存兜底 + 后端校准双保险（localStorage `appThemePref` 优先、后端 UserPreference 校准），解决后端未起时主题回退问题；大版本收尾文档 + 整合打包（288 PASS） |
| **免责声明功能** | 2026-08-27 | 新增 `DISCLAIMER.md`（9 章节）、侧边栏免责入口 + 首次强制弹窗（5 秒预读 + 翻到末页才能同意）；修复免责弹窗不弹（Bug A）与退出后无法登录（Bug B） |
| **启动自检与自动拉起** | 2026-08-28 | `start.bat` 增强：8000/5173 端口自检 + 前端/后端任一缺失自动拉起 + 就绪等待；清理残留旧库；本轮再增强环境预装检测与桌面快捷方式，正式版打包 |

---

## 三、技术架构

```
┌─────────────────────────────────────────────────────┐
│                   浏览器 (PC 端)                      │
│          http://localhost:5173  (Vue3 + Vite)        │
└──────────────────────────┬──────────────────────────┘
                           │  /api /static 反向代理
                           ▼
┌─────────────────────────────────────────────────────┐
│             FastAPI 后端 (127.0.0.1:8000)            │
│   app/ (main/config/database/models/schemas/        │
│        security/deps + routers/*)                   │
│   SQLAlchemy ORM                                     │
└───────────────┬──────────────────────┬──────────────┘
                ▼                       ▼
        SQLite (本地开发)       PostgreSQL (Docker 部署)
        backend/data/inventory.db   deploy/docker-compose.yml
```

### 分层

| 层 | 技术 | 说明 |
|---|---|---|
| 前端 | Vue 3 + Vite | 响应式 Web，PC 浏览器访问，`frontend/src` |
| 后端 | Python FastAPI | REST API，`backend/app` |
| 数据库 | SQLite / PostgreSQL | SQLAlchemy 2.0 双库兼容，psycopg2 |
| 部署 | Docker Compose | db + backend + frontend(nginx) 三服务 |

### 关键设计点（二次开发者必读）

1. **双数据库兼容**：`backend/app/main.py` 的 `ensure_schema()` 通过 `_table_columns()` 按库类型分支获取已有列（PostgreSQL 走 `information_schema.columns`，SQLite 保留 `PRAGMA table_info`），本地 SQLite 与 Docker PostgreSQL 共用一套代码。
2. **配置即环境**：`backend/app/config.py` 基于 `.env`（`DATABASE_URL` / `DATA_DIR` / `SECRET_KEY` / `BOSS_USERNAME` / `BOSS_PASSWORD`）构建 Settings；存储迁移（设置中心）基于 `DATA_DIR`，保证两者一致。
3. **主题持久化走后端**：用户外观偏好存 `UserPreference` 表，前端 `App.vue` 加载 → `applyPref`；v1.3.3 起 localStorage（`appThemePref`）优先 + 后端校准双保险。
4. **软删除回收站**：商品删除为软删除（`deleted_at`），回收站子页批量操作，超 30 天自动清理。
5. **权限控制**：`require_role("boss","admin")` 依赖（`backend/app/deps.py`），员工仅只读看数据。
6. **PYTHONHOME 踩坑**：本机 venv 基于 Marvis 运行时 python311 创建，缺标准库；启动/跑测试需注入 `PYTHONHOME=E:\Program Files\Tencent\Marvis\MarvisAgent\1.0.1100.522\runtime\python311`（已内置于 start.bat，自动探测存在才注入）。

---

## 四、功能模块全景

| 模块 | 说明 | 主要文件 |
|---|---|---|
| 登录鉴权 | 三级账号、JWT/bcrypt、首次自动建 boss | `backend/app/routers/auth.py` |
| 商品档案 | SPU/SKU、分类/单位/重量单位、商品图片 | `routers/products.py` + `views/Products.vue` |
| 扫码出入库 | 扫码/条码快速出入库、库存流水、低库存提示 | `routers/stock.py` + `views/Stock*.vue` |
| 采购入库 | 供应商、采购单、扫码建单、批量入库 | `routers/purchase.py` |
| 销售出库 | 销售单草稿 CRUD、折扣、确认出库减库存、流水/回滚 | `routers/sales.py` |
| 财务对账 | 成本快照、毛利分析、渠道分组对账、日期过滤 | `routers/finance.py` |
| 库存分析 | 汇总/分类/排行/慢动销/低库存/趋势 | `routers/analysis.py` |
| 标签打印 | 60x40 画布、元素缩放/对齐/三段式自动排版、发件人、模板 | `routers/label_*.py` + `views/LabelPrint.vue` |
| 渠道追踪 | 销售渠道管理、按渠道统计销售毛利 | `routers/channels.py` |
| 审计日志 | 操作留痕 + 清理（手动/自动 90 天） | `routers/audits.py` |
| 回收站 | 软删除商品管理、批量删除/还原/彻底删除 | `routers/recycle.py` + `views/Recycle.vue` |
| 设置中心 | 外观/存储迁移/云端备份占位 | `routers/settings.py` + `views/Settings*.vue` |
| 用户管理 | 账号创建/角色/重置 | `routers/users.py` + `views/UserManage.vue` |
| 免责声明 | 首次强制弹窗 + 侧边栏入口 | `components/DisclaimerDialog.vue` |

---

## 五、目录结构

```
ECommerceInventorySystem/
├── backend/                  # FastAPI 后端
│   ├── app/                  # 核心代码（main/config/database/models/schemas/security/deps + routers/）
│   ├── data/                 # 运行数据（inventory.db + media 上传图，不入库不入包）
│   ├── media/                # 媒体上传目录
│   ├── venv/                 # 本地虚拟环境（不入包）
│   ├── .env                  # 本地环境变量（不入包，只保留 .env.example）
│   ├── .env.example          # 环境变量模板
│   ├── requirements.txt      # 后端依赖
│   ├── Dockerfile
│   └── test_*.py             # 9 个回归测试脚本
├── frontend/                 # Vue3 + Vite 前端
│   ├── src/                  # App.vue / main.js / style.css / utils/theme.js / stores / router / api / components / views
│   ├── public/backgrounds/   # 背景素材（bg_day_05.jpg / bg_night_01.jpg / endfield_space.jpg）
│   ├── package.json
│   ├── vite.config.js        # 5173 + /api /static 代理到 8000
│   ├── nginx.conf
│   └── Dockerfile
├── database/                 # 数据库结构/迁移说明（.gitkeep）
├── deploy/                   # Docker Compose 部署（docker-compose.yml + start/stop-docker.sh + .env.example）
├── docs/                     # 设计文档（设计文档.html / README-full.md / manual.html）
├── scripts/                  # 工具脚本（.gitkeep）
├── DEVELOPMENT_SUMMARY.md    # 本文档（开发总结）
├── README.md                 # 项目说明（功能/启动/部署/回归）
├── RELEASE.md                # 发行指南（GitHub 发布流程）
├── DISCLAIMER.md             # 免责声明（9 章节）
├── start.bat                 # Windows 一键启动（环境检测 + 自检自动拉起 + 快捷方式）
├── stop.bat                  # Windows 一键停止
└── .gitignore                # 忽略规则
```

---

## 六、二次开发指引

### 6.1 环境准备

| 依赖 | 版本要求 | 说明 |
|---|---|---|
| Python | 3.11+（3.10 亦可） | 需加入 PATH；`start.bat` 会自动检测 |
| Node.js | 18+ | 需加入 PATH；`start.bat` 会自动检测 |
| Docker（可选） | Docker Desktop | 仅 Docker 部署需要 |

### 6.2 一键启动（客户 / 开发者通用）

1. 解压发布包到任意目录（如 `E:\`）。
2. 双击桌面「0号仓库库存管理系统」快捷方式（首次运行自动创建），或直接双击 `start.bat`。
3. `start.bat` 会自动：
   - 检测 Python 3.11+ / Node 18+（缺失则弹中文提示并打开官方下载页）；
   - 自检 8000（后端）/ 5173（前端）端口，任一缺失自动拉起；
   - 首次运行自动安装依赖（backend venv + npm install）；
   - 等待服务就绪后自动打开浏览器 `http://localhost:5173`。
4. 停止服务：双击 `stop.bat`。

默认账号：老板 `boss / admin123`（登录后请尽快修改）。

### 6.3 手动开发模式

```bash
# 后端（8000）
cd backend
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 前端（5173）
cd frontend
npm install
npm run dev
```

> 本机 venv 若报 `Could not find platform independent libraries`，先注入 `PYTHONHOME` 指向含 Lib 的 runtime python311（见第三节第 6 点）。

### 6.4 新增模块分层落地法（约定）

新增一个功能模块，按以下分层落位（与既有模块完全一致）：

| 步骤 | 位置 | 内容 |
|---|---|---|
| 1. 数据模型 | `backend/app/models.py` | 新增 ORM 模型（含 `deleted_at` 等公共字段约定） |
| 2. 接口定义 | `backend/app/schemas.py` | Pydantic 请求/响应模型 |
| 3. 业务路由 | `backend/app/routers/xxx.py` | FastAPI Router，注册到 `main.py` |
| 4. 权限控制 | `backend/app/deps.py` | 按角色加 `require_role(...)` |
| 5. 前端 API | `frontend/src/api/index.js` | 封装 axios 请求 |
| 6. 前端页面 | `frontend/src/views/Xxx.vue` | 页面组件，注册到 `router/index.js` |
| 7. 测试 | `backend/test_xxx.py` | 仿既有 test_*.py 编写回归脚本 |
| 8. 文档 | `README.md` / `DEVELOPMENT_SUMMARY.md` | 更新功能清单与版本记录 |

**前端样式约定**：终末地工业风设计令牌集中在 `style.css`（`--accent` / `--primary` / 全直角 / 斜线网格 / HUD 角标）；主题背景经 `ThemeBackdrop.vue` + `utils/theme.js` 应用；新增全局选择器须放非 scoped `<style>`。

### 6.5 测试体系（基线：9 脚本 280 PASS）

| 测试脚本 | 覆盖 |
|---|---|
| test_analysis.py | 库存分析回归 |
| test_catunit.py | 分类/单位回归 |
| test_finance.py | 财务对账回归 |
| test_label_print.py | 标签打印回归 |
| test_label_templates.py | 标签模板回归 |
| test_purchase.py | 采购入库回归 |
| test_sales.py | 销售出库回归 |
| test_settings.py | 设置中心回归 |
| test_audit_cleanup.py | 操作日志清理回归（权限/手动/自动） |

**跑回归的正确姿势（务必隔离临时库，勿污染真实库/.env）**：
1. 不要直接跑会改 `.env` 的用例（如 settings 迁移测试），用独立临时 `.env` 或环境变量覆盖。
2. 按测试脚本的直连库依赖分组启动隔离 uvicorn（如 127.0.0.1:8765），每组 `DATABASE_URL` 指向独立临时库。
3. 每组启动后等约 8s 再跑，跑完 terminate 释放端口。
4. 基线：9 脚本 280 PASS，零 FAIL。

---

## 七、发布与部署说明

### 7.1 发布包构成（v1.3.3-Final）

发布包为「干净源码包」，含全部源码、文档与启动脚本，**不含**依赖（venv/node_modules/dist）、本地业务数据（backend/data、backend/media）、密钥（.env）：

```
ECommerceInventorySystem-v1.3.3-Final-YYYYMMDD.zip
├── backend/       # app/ + 9 个 test_*.py + requirements.txt + Dockerfile + .env.example
├── frontend/      # src/ + public/backgrounds + package.json + nginx.conf + Dockerfile
├── database/      # 数据库说明
├── deploy/        # docker-compose.yml + start/stop-docker.sh + .env.example
├── docs/          # 设计文档 + README-full.md + manual.html
├── scripts/       # 工具脚本
├── README.md / RELEASE.md / DEVELOPMENT_SUMMARY.md / DISCLAIMER.md
├── start.bat / stop.bat / .gitignore
```

**已排除**：`node_modules/`、`dist/`、`venv/`、`__pycache__/`、`.git/`、`*.log`、`*.db`、`.env`、`backend/data/`、`backend/media/`。

### 7.2 GitHub 发布流程

详见 `RELEASE.md`：`git init` → `git add .` → `git commit` → `git remote add origin <repo>` → `git push -u origin master` → `git tag v1.3.3` → 创建 Release 并上传 zip 附件。

### 7.3 Docker 部署

```bash
cd deploy
copy .env.example .env   # Linux: cp .env.example .env
docker compose up -d --build
# 前端 http://localhost ，健康检查 http://localhost/api/health
```

**生产部署必改**：`POSTGRES_PASSWORD` / `SECRET_KEY` / `BOSS_PASSWORD`。

### 7.4 后续版本规划（不在本轮范围）

- 手机端独立项目（独立仓库、独立版本）
- 打印机型号兼容扩展
- 云服务器部署（长期稳定对外服务）
- 云端备份（设置中心已预留入口）
- 多平台同步 / 多仓库数据统一
- 报表导出、批量导入导出增强

---

*0号仓库库存管理系统 开发团队*
*（内容由AI生成，仅供参考）*
