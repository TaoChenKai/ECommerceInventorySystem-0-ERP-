---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 8cb4b16a2ae761ae637e563ea2323cd2_3973f6a6a1f411f192a2525400287e28
    ReservedCode1: /QWlxflpDt4m4OaGlAqk7HqwG3CBrJOahZkLpLjtomec1EeQfK5y86+AKRulh+GAhvLahoInlhDV0/3sG298SS7NjWSFl+gBkmLeD+u3HxWqfU60Fcixo9R8K8t8BjDXjIN80tNk4a98UspDhJue6kfSUNTNHYG8WFQDzsul/iXjsSl1oC32kmrrC1E=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 8cb4b16a2ae761ae637e563ea2323cd2_3973f6a6a1f411f192a2525400287e28
    ReservedCode2: /QWlxflpDt4m4OaGlAqk7HqwG3CBrJOahZkLpLjtomec1EeQfK5y86+AKRulh+GAhvLahoInlhDV0/3sG298SS7NjWSFl+gBkmLeD+u3HxWqfU60Fcixo9R8K8t8BjDXjIN80tNk4a98UspDhJue6kfSUNTNHYG8WFQDzsul/iXjsSl1oC32kmrrC1E=
---

# 0号仓库库存管理系统 — PC 端完整说明文档（v1.3.3）

> **版本：v1.3.3** ｜ 更新日期：2026-08-27 ｜ 覆盖范围：v1.0 初稿 ~ v1.3.3 全版本演进 ｜ 适用：电商小店 + 少量批发的 PC 端库存管理

---

## 一、项目简介

**0号仓库库存管理系统**（原名「星穹」电商库存系统）是一套自研的 **PC 端网页版电商库存管理系统**，面向电商小店与少量批发场景。系统采用 **Vue 3 + Vite 前端** 与 **FastAPI 后端**，数据默认使用本地 SQLite、Docker 部署时可无缝切换 PostgreSQL。

核心设计目标：

- **数据自掌控**：开源免费或自研，不被收费软件卡脖子；
- **一套代码多端访问**：本机 Windows、局域网其他电脑、云服务器均可通过浏览器使用；
- **三级角色权限**：老板 / 管理员 / 员工，职责边界清晰；
- **贴近真实业务流程**：商品档案 → 出入库 → 采购 → 销售 → 财务对账 → 库存分析闭环，附标签打印、渠道追踪、审计留痕、回收站等运维能力。

> 移动端规划为**独立项目单独开发**（便于分仓库管理版本），不在本版本范围内。

---

## 二、技术架构

### 2.1 总体架构

```
浏览器（PC / 局域网 / 服务器）
        │  HTTP(S)
        ▼
┌───────────────────────┐
│   前端 Vue 3 + Vite    │  登录鉴权 / 路由 / 状态管理 / 请求
│  （Nginx 托管或 dev）   │  /api、/static 代理到后端
└───────────┬───────────┘
            │  RESTful API（JWT 鉴权）
            ▼
┌───────────────────────┐
│   后端 FastAPI         │  routers 路由层 + models ORM + security 鉴权
│  （uvicorn / Docker）  │  启动 ensure_schema 自动建表 / 迁移 / 自动清理
└───────────┬───────────┘
            │
            ▼
   ┌──────────────────┐         ┌──────────────────┐
   │ SQLite（本地开发） │  或可  │ PostgreSQL（Docker）│
   │ 默认 data/inventory.db │      │ inventory 库 :5432  │
   └──────────────────┘         └──────────────────┘
```

### 2.2 后端（Python FastAPI）

| 模块 | 说明 |
|---|---|
| `backend/app/main.py` | 应用入口、CORS、启动时 `ensure_schema()` 自动建表 / 增量迁移 / 回收站与审计日志自动清理 |
| `backend/app/models.py` | ORM 模型：User / Spu / Sku / Category / Unit / StockLog / Purchase / PurchaseItem / Sale / SaleItem / Channel / FinanceOrder / LabelTemplate / AuditLog / UserPreference / PrinterProfile 等 |
| `backend/app/routers/` | 16 个业务路由：auth、spus、stock、purchase、sales、finance、analysis、channels、label、label_templates、recycle、users、settings、audits、uploads 等 |
| `backend/app/schemas.py` | Pydantic 请求 / 响应模型 |
| `backend/app/security.py` | 密码哈希（bcrypt）与 JWT 签发 / 校验 |
| `backend/app/deps.py` | `get_current_user` / `require_role("boss","admin")` 权限依赖 |
| `backend/app/config.py` | Settings（读取 `.env`，SQLite 归一化、存储迁移、AUDIT_RETENTION_DAYS 等） |
| `backend/app/database.py` | SQLAlchemy 引擎 / Session（SQLite 与 PostgreSQL 双数据库适配） |

### 2.3 前端（Vue 3 + Vite）

| 模块 | 说明 |
|---|---|
| `frontend/src/views/` | 18 个页面：Login、Dashboard、Products、ProductForm、Recycle、StockInOut、StockLogs、PurchaseOrders、PurchaseNew、SalesOrders、SalesNew、Finance、Analysis、Channels、LabelPrint、UserManage、AuditLog、SettingsDialog |
| `frontend/src/components/` | Layout（侧边栏）、ThemeBackdrop（主题背景）、StarField（粒子星云）、ImageUploader 等 |
| `frontend/src/router/index.js` | 路由 + 角色守卫（meta.roles 控制财务/回收站/账号/日志等仅管理员可见可进） |
| `frontend/src/api/` | 各模块 API 封装（axios） |
| `frontend/src/utils/theme.js` | 主题色板定义、偏好应用、**本地缓存兜底 + 后端校准**（v1.3.3） |
| `frontend/src/stores/`、`utils/auth.js` | 认证令牌 / 用户信息（localStorage 仅存 token 与 user） |

### 2.4 数据库

- **本地开发**：SQLite，默认 `backend/data/inventory.db`；旧路径 `backend/inventory.db` 首次启动自动迁移进入 `data/` 归一。
- **Docker 部署**：PostgreSQL 16（数据库 `inventory`、用户 `inventory`，仅监听 `127.0.0.1:5432`）。
- **同一套代码双库兼容**：`ensure_schema()` 通过 `_table_columns()` 按库类型分支获取已有列（PostgreSQL 走 `information_schema.columns`，SQLite 保留 `PRAGMA table_info`），迁移逻辑两库共用。

### 2.5 部署拓扑（Docker Compose）

| 服务 | 说明 |
|---|---|
| `db` | PostgreSQL 16，named volume `pgdata` 持久化业务数据 |
| `backend` | FastAPI 后端，容器内 8000（不对外映射），连接 db |
| `frontend` | Nginx 托管前端静态产物 + 反向代理 `/api`，对外暴露 80 端口 |

---

## 三、目录结构

```
ECommerceInventorySystem/
├── backend/                    # 后端代码
│   ├── app/                    # 应用源码（main / models / routers / schemas / security / deps / config / database）
│   ├── data/                   # 运行数据目录（inventory.db + media 上传图，不入库不打进分发包）
│   ├── requirements.txt        # Python 依赖
│   ├── Dockerfile              # 后端容器镜像（python:3.12-slim）
│   ├── .env                    # 本地环境变量（含密钥，不入库不打进分发包）
│   ├── .env.example            # 环境变量示例模板（随包分发）
│   └── test_*.py               # 9 个后端回归测试
├── frontend/                   # 前端代码
│   ├── src/                    # Vue 3 源码（views / components / router / api / stores / utils）
│   ├── public/backgrounds/     # 主题背景素材（endfield_space.jpg / bg_day_05.jpg / bg_night_01.jpg，需保留）
│   ├── nginx.conf              # 容器内 Nginx 配置
│   ├── Dockerfile              # 前端镜像（node:20-alpine 构建 → nginx:alpine）
│   └── package.json            # 依赖与脚本（dev / build）
├── database/                   # 数据库结构与迁移脚本（当前为空，Docker 启动自动建表）
├── deploy/                     # 部署配置
│   ├── docker-compose.yml      # 三服务编排
│   ├── .env.example            # 部署环境变量模板
│   └── start/stop-docker.sh    # Linux/Mac 启停脚本
├── docs/                       # 文档目录
│   ├── README-full.md          # 本文档（完整说明）
│   └── manual.html             # 说明文档 HTML 版（自包含，双击浏览器打开）
├── scripts/                    # 工具脚本（当前为空）
├── README.md                   # 项目说明速览
├── RELEASE.md                  # 发行 / 推 GitHub 指南
├── start.bat                   # Windows 一键启动（后端 8000 + 前端 5173）
├── stop.bat                    # Windows 一键停止
└── .gitignore                  # 版本忽略规则
```

---

## 四、功能特性全景

### 4.1 账号与三级权限

- **老板（boss）**：全部权限，可管理账号（创建 / 删除管理员与员工），唯一老板账号不可删不可通过接口创建；
- **管理员（admin）**：可增改业务数据，包含回收站 / 财务 / 日志等管理操作，但不能管理账号；
- **员工（staff）**：仅查看数据（如库存分析），写入与后台管理受限。
- 路由级 `meta.roles` + 后端 `require_role` 双层控制：商品回收站、财务对账、账号权限、操作日志仅 `boss / admin` 可见可进。

### 4.2 商品档案

- SPU / SKU 两级商品结构，分类、单位、重量单位自由维护；
- 商品图片（ImageUploader 上传），条形码 / 规格 / 成本价 / 售价 / 库存字段完整；
- 智能筛选、批量删除（v1.3，见第十一章）。

### 4.3 扫码出入库

- 扫码 / 条码 / 编码快速出入库，实时扣加库存；
- 库存流水（StockLogs）全程留痕，低库存提示。

### 4.4 采购入库

- 供应商管理 + 采购单流程（草稿 / 确认）；
- 扫码建单 + 批量入库，采购明细写入库存流水与成本基础。

### 4.5 销售出库

- 销售单（草稿 CRUD）+ 折扣；
- 确认出库自动减库存，流水留痕，可回滚。

### 4.6 财务对账

- 成本快照（出库时固化成本，不随档案成本漂移）；
- 毛利分析（销售总额 / 成本 / 毛利 / 毛利率 / 单数 / 件数）；
- 按渠道分组对账明细、日期范围过滤、员工可见性控制。

### 4.7 库存分析

汇总、分类库存、库存排行、销售排行、慢动销分析、低库存预警、30 天趋势，全部指标可由员工查看。

### 4.8 标签打印

- 商品标签排版：60×40 默认画布、元素整体缩放、水平对齐、三段式自动排版；
- 常用发件人管理、打印机偏好（localStorage）记忆；
- 布局模板（LabelTemplate）管理，支持一维码 / 二维码 / 产品名 / 价格等元素；
- 打印采用 `display:none` 隔离后台布局 + 定位打印区，**避免多页空白纸**。

### 4.9 渠道追踪

销售渠道管理（如天猫旗舰店 / 抖音小店 / 未指定），按渠道统计销售与毛利。

### 4.10 审计日志与清理（v1.1.1 起）

- 关键操作全程写入审计日志（创建 / 删除账号、出入库、删除、迁移、清理等）；
- 手动清理 `DELETE /api/audits`（boss / admin，支持按日期或清空全部）；
- 启动自动清理：删除早于 `AUDIT_RETENTION_DAYS`（默认 90 天）的旧日志，清理动作本身也留痕。

### 4.11 设置中心（v1.1 起）

- **UI 外观自定义**：亮 / 暗 / 随机 + 8 套预设主题色，上传本地图片作背景，偏好存**后端 UserPreference 表**、换设备一致；
- **数据存储迁移**：仅本机 SQLite，安全迁移（备份 / 校验 / 回滚），仅 boss / 管理员可用，支持迁移到任意盘；
- **云端备份**：预留占位入口（本期未实现）。

### 4.12 终端背景主题系统（v1.2 起）

- 品牌登录页终末地工业风加载动画（约 2.5s，`prefers-reduced-motion` 自动跳过）；
- 主界面全面终末地工业风设计令牌：全直角、工业细线边框、黄 `#fff500` / 青 `#14d0d0` 强调、斜线网格纹理、HUD 角标装饰；
- 主题绑定背景：谷地黄 = 暖色工业废土城（白天 bg_day_05），武陵青 = 冷色科学院/科幻都市（夜晚 bg_night_01），低透明度 + 半透明遮罩保证文字可读；上传自定义背景优先级最高。

---

## 五、版本更新历史（v1.0 → v1.3.3）

| 版本 | 日期 | 主要改动 |
|---|---|---|
| **v1.3.3** | 2026-08-27 | **主题背景本地缓存兜底 + 后端校准**：新增 `frontend/src/utils/theme.js`（键 `appThemePref` 本地缓存 + `saveLocalPref` / `loadLocalPref` / `isDefaultPref`）；App.vue 先本地应用再异步后端校准——后端失败保留本地、后端无记录用本地值、成功则覆盖缓存；SettingsDialog.vue 保存偏好后写缓存、挂载时校准。修复刷新后主题 / 背景丢失问题（commit e6c6b6a）。工作区同步落地 v1.3.2 背景素材并将 RELEASE.md 纳入版本库 |
| **v1.3.2** | 2026-08-26→08-27 | **背景切换终末地官网风格真实图**：新增谷地黄 `bg_day_05.jpg`、武陵青 `bg_night_01.jpg` 真实场景图，主题背景由自绘概念场景升级为官网风真实美术素材（保留在 `frontend/public/backgrounds/`，是打包须保留的素材） |
| **v1.3.1** | 2026-08-26 | **品牌更名 + 菜单结构重构**：全局更名「0号仓库库存管理系统」（登录页 / 侧边栏 logo / 页面标题 / 示例数据 / 主题默认名）；侧边栏按「库存管理 / 运营分析 / 系统」分组，「商品回收站」作为库存管理下二级子菜单、首页独立置顶；收起态品牌区（logo + 名称）横条常驻，仅导航收窄为图标条 |
| **v1.3** | 2026-08-26 | **回收站 + 批量删除 + 智能筛选 + 权限收紧**：商品批量软删除进回收站（30 天保留）；回收站列表 / 批量还原 / 彻底删除（物理删 + 清关联流水）；智能筛选建议（库存为空 / 长期无变动）；users 等路由收紧（删除账号仅 boss） |
| **v1.2.2** | 2026-08-26 | **真实星云背景 + 详情页辨识度**：主界面背景改用真实游戏场景太空星云截图（1920×1080）；详情页面板 / 卡片 / 表格 / 表头 / 按钮全面吃主题令牌，谷地黄 = 黄 #fff500 + 白底黑字、武陵青 = 青 #14d0d0 + 深色底，一眼可辨 |
| **v1.2.1** | 2026-08-25 | **主界面终末地化**：面板 / 表格 / 按钮 / 弹窗 / 侧边栏统一终末地设计令牌；新增主题概念背景系统（SVG 自绘场景，谷地黄 / 武陵青各一套） |
| **v1.2** | 2026-08-25 | **UI 视觉升级**：品牌登录页终末地加载动画；新增「终末地·谷地黄 / 终末地·武陵青」两套全直角工业风主题；侧边栏动态收展；路由转场动画；粒子星云 / HUD / 噪点质感 |
| **v1.1.1** | 2026-08-24 | **操作日志清理 + 侧边栏固定**：审计日志手动 / 自动清理；左侧目录栏固定，仅内容区滚动 |
| **v1.1** | 2026-08-24 | **设置中心**：UI 外观自定义（主题 / 背景）、数据存储安全迁移、云端备份占位入口 |
| **v1.0 初稿** | 2026-08-23 | 商品档案 / 扫码出入库 / 采购入库 / 销售出库 / 财务对账 / 库存分析 / 标签打印 / 三级账号权限 / 渠道追踪 / 审计日志；Docker 本地验证 + 回归测试通过 |

---

## 六、安装部署与运行

### 6.1 环境要求

| 项 | 要求 |
|---|---|
| Python | 3.10+（后端） |
| Node.js | 18+（前端构建 / 开发） |
| Docker | Docker Desktop（Windows 自带 WSL2）+ 可选国内镜像加速（部署用） |
| 浏览器 | 现代 Chrome / Edge 等（登录页动画含 `prefers-reduced-motion` 兼容） |

### 6.2 本地运行（Windows）

**一键启动（推荐）**：双击根目录 `start.bat`（或桌面快捷方式）——自动拉起后端（8000）与前端（5173），首次自动安装依赖，就绪后自动打开 `http://localhost:5173`。停止：双击 `stop.bat`。

**手动启动（开发模式）**：

```bash
# 1. 启动后端（8000）
cd backend
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# 2. 启动前端（5173）
cd frontend
npm install
npm run dev
# 浏览器打开 http://localhost:5173
```

> 注意：主题 / 背景偏好走后端 `UserPreference`（`GET/PUT /api/settings/preference`），**须同时开启后端**才生效；仅开前端 dev（5173）不启后端（8000）会导致主题设置无法持久化。v1.3.3 起即使后端暂时不可用，也会用本地缓存兜底显示，之后自动校准。

### 6.3 其他电脑 / 局域网访问

1. 拷贝整个项目（或从 git 拉取）；
2. 目标电脑安装 Python 3.10+ 与 Node.js 18+（加入 PATH）；
3. 双击 `start.bat`，浏览器打开 `http://localhost:5173`；
4. 同一局域网其他设备访问 `http://本机IP:5173`（前端 dev 已代理 `/api`、`/static` 到后端）。

### 6.4 Docker 部署

```bash
cd deploy
copy .env.example .env     # Linux: cp .env.example .env
docker compose up -d --build   # 三服务 db + backend + frontend
```

- 前端：`http://localhost`；健康检查：`http://localhost/api/health`。
- 停止：`docker compose down`（保留 pgdata 数据卷）；彻底移除含数据：`docker compose down -v`。
- `restart: unless-stopped` 可自动自愈 backend 早于 db 就绪时的连接重试。
- **生产部署必改**：`deploy/.env` 中 `POSTGRES_PASSWORD`（默认 inventory123）、`SECRET_KEY`、`BOSS_PASSWORD`（默认 admin123）。
- **Docker Hub 拉取失败**时：在 Docker daemon `registry-mirrors` 加入 `https://docker.1ms.run` 等国内加速镜像后重启 Docker Desktop。

### 6.5 数据库迁移（SQLite → PostgreSQL）

项目默认 SQLite（本地开发）。切换 PostgreSQL：

1. 在 `backend/.env` 设置 `DATABASE_URL=postgresql+psycopg2://inventory:<password>@127.0.0.1:5432/inventory`（Docker 部署直接改 `deploy/.env`）。
2. 启动后端，`ensure_schema()` 会自动按库类型建表 / 迁移，兼容性代码见 `main.py` 的 `_table_columns()`。
3. 业务数据迁移：可先导出 SQLite 数据再导入 PostgreSQL，或直接在新库重新初始化（本地数据不走 Docker 场景）。

### 6.6 数据存储位置迁移（设置中心内）

仅本机 SQLite 可迁移：设置中心 → 数据存储 → 选择新目录，系统自动执行 **备份 → 拷贝 → 校验 → 回滚兜底**，迁移后新库生效；拒绝迁移到当前目录子目录 / 相同目录。

---

## 七、默认账号（首次登录后请尽快修改）

| 角色 | 用户名 | 初始密码 | 权限 |
|---|---|---|---|
| 老板 | `boss` | `admin123` | 全部权限，可管理账号 |
| 管理员 | `admin1` | `admin123` | 增改数据 + 后台管理（回收站 / 财务 / 日志），**不能**管理账号 |
| 员工 | `staff1` | `123456` | 仅查看数据 |

> 老板账号唯一且不可删；管理员与员工可由老板在「账号权限」创建；`boss` 账号不能通过接口重复创建。

---

## 八、主题与外观自定义说明

入口：设置中心 → UI 外观，或侧边栏设置按钮。

- **亮度**：亮 / 暗 / 随系统（含随机）。
- **主题色**：8 套预设，其中「终末地·谷地黄」（黄 #fff500 暖调）、「终末地·武陵青」（青 #14d0d0 冷调）为全直角工业风主题，「0号仓库蓝紫」保留为备选。
- **背景图**：谷地黄默认绑 `bg_day_05.jpg`（暖色废土城，白天）、武陵青默认绑 `bg_night_01.jpg`（冷色科研都市，夜晚）；上传自定义图片优先展示；v1.2.2 之前还提供 `endfield_space.jpg` 太空星云背景（保留素材）。
- **持久化机制**：偏好写**后端 `UserPreference` 表**（换设备一致）；v1.3.3 起本地缓存 `appThemePref` 兜底——启动先本地应用再异步向后端校准，后端失败 / 无记录时用本地值，保证刷新后主题背景不丢失。
- **可读性保障**：背景图低透明度 + 主题色半透明遮罩叠加，面板 / 表格文字始终清晰。

---

## 九、回收站 / 智能筛选 / 权限说明

### 9.1 回收站（v1.3）

- **批量删除**（「商品档案」勾选 → 批量删除移入回收站；仅 boss / admin）：货品仅标记 `deleted_at` 软删除，进回收站，**历史出入库 / 采购 / 销售流水全部保留**，可随时还原。
- **回收站列表**（boss / admin 可见）：显示删除时间 / 剩余清理天数倒计时。
- **批量还原**（boss / admin）：一键恢复为正常商品。
- **彻底删除**（boss / admin）：物理删除货品 + 清关联数据（出入库流水 / 采购明细 / 销售明细 / 图片 / 规格），**不可恢复**，需二次确认。
- **自动清理**：服务启动时物理清除**超过 30 天**仍在回收站的数据。

### 9.2 智能筛选（v1.3）

「商品档案 → 批量删除」弹窗提供**智能分析**：按时间线（如 30 / 90 / 180 天）调用 `GET /api/recycle/analyze`，返回建议关注清单——**库存为空** 或 **最后变动距今超过所选天数（长期无变动）** 的货品，含积压天数与建议原因，可勾选直接批量移入回收站。

### 9.3 权限矩阵

| 功能 | boss | admin | staff |
|---|---|---|---|
| 商品增删改 / 出入库 / 采购 / 销售 / 库存分析 / 标签打印 / 渠道 | ✔ | ✔ | 查看 |
| 回收站（列表） | ✔ | ✔ | ✘（路由拦截） |
| 批量删除 / 还原 / 彻底删除 / 财务对账 / 操作日志 / 账号管理 | ✔ | ✔（除账号） | ✘ |
| 删除账号 | ✔ | ✘ | ✘ |

---

## 十、回归测试

```bash
# 后端：先启动隔离临时库 uvicorn，再逐个运行 9 个测试
cd backend
venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8765
venv\Scripts\python.exe test_analysis.py        # 库存分析（58 PASS）
venv\Scripts\python.exe test_catunit.py         # 分类/单位（14 PASS）
venv\Scripts\python.exe test_finance.py         # 财务对账（49 PASS）
venv\Scripts\python.exe test_label_print.py     # 标签打印（22 PASS）
venv\Scripts\python.exe test_label_templates.py # 标签模板（31 PASS）
venv\Scripts\python.exe test_purchase.py        # 采购入库（36 PASS）
venv\Scripts\python.exe test_sales.py           # 销售出库（35 PASS）
venv\Scripts\python.exe test_settings.py        # 设置中心（30 PASS）
venv\Scripts\python.exe test_audit_cleanup.py   # 日志清理（13 PASS）

# 前端：生产构建（应无报错，dist 正常产出）
cd frontend
npm run build
```

> v1.3.3 基线实测：后端 9 个测试 **288 PASS 全绿**，前端 `npm run build` 成功。

---

## 十一、打包发布（GitHub）指引

**发布包构成**（源码 + 运行必需文件，不含本地依赖与业务数据）：

```
ECommerceInventorySystem-v1.3.3-YYYYMMDD.zip
├── backend/...     # app 源码 + 9 个回归测试 + requirements.txt + Dockerfile + .env.example
├── frontend/...    # src 源码 + package.json + nginx.conf + Dockerfile + public/backgrounds 素材
├── database/       # 数据库结构脚本（Docker 自动建表）
├── deploy/         # docker-compose.yml + start/stop 脚本 + .env.example
├── docs/           # README-full.md + manual.html（说明文档）
├── README.md / RELEASE.md / start.bat / stop.bat / .gitignore
```

**打包排除**：`node_modules`、`dist`、`__pycache__`、`venv`、`.git`、`*.log`、`*.db`（含测试库）、`.env`（含密钥）、`backend/data`（运行数据 + 用户上传 media）。**保留**：`frontend/public/backgrounds` 主题背景素材。

**发布流程**：

```bash
git add .
git commit -m "feat: v1.3.3 主题背景本地缓存兜底+后端校准"
git tag v1.3.3
git remote add origin https://github.com/<你的用户名>/ECommerceInventorySystem.git   # 首次
git push -u origin master
git push --tags
```

**发行前检查清单**：后端回归全绿｜前端 build 成功｜`inventory.db` 与 `.env` 未入库未进包｜无 `__pycache__` / `*.log` / `test_*.db` 残留｜Docker 三服务可启动且 `/api/health` 200｜默认账号可登录｜生产密码已更换。

---

## 附录 A：常见问题（FAQ）

| 问题 | 处理 |
|---|---|
| 刷新后主题 / 背景丢失 | v1.3.3 已修复：本地缓存兜底 + 后端校准；确认后端（8000）已启动 |
| 主题修改换机器不一致 | 主题偏好走后端 UserPreference，登录同一账号即可同步，非 localStorage |
| 打印标签多页空白 | 已用 `display:none` 隔离后台布局，仅打印区输出；若仍在旧版本可升级 |
| 背景图不显示 | 检查 `frontend/public/backgrounds/` 素材存在（构建后需重新 `npm run build` 打包进 dist） |
| Docker 拉镜像超时 | 配置 Docker daemon registry-mirrors 国内加速后重启 Docker Desktop |
| 忘记老板密码 | 需在数据库重置（本地 SQLite 直接改 `backend/data/inventory.db` 中 User 密码哈希，或用设置中心重置流程） |
| 数据库迁移到 PostgreSQL | 设置 `DATABASE_URL=postgresql+psycopg2://...`，`ensure_schema()` 自动建表迁移 |
| 回收站自动清理 | 硬件删除 30 天是服务启动时触发；可手动在回收站「彻底删除」立即清理 |
*（内容由 AI 生成，仅供参考）*
*（内容由AI生成，仅供参考）*
