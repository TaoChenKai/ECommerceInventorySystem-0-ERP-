import os
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from .config import settings
from .database import Base, engine, SessionLocal
from .models import User, Unit, WeightUnit, AuditLog
from .security import hash_password
from .routers import auth, users, audit, products, stock, purchase, sales, finance, upload, analysis, senders, label_templates, settings as settings_router
from .routers import recycle

# 建表（开发期自动建，部署期建议用迁移）
Base.metadata.create_all(bind=engine)


def _table_columns(db, table):
    """Get existing column names by db type (PRAGMA for sqlite, information_schema for postgres)"""
    if engine.dialect.name == "postgresql":
        rows = db.execute(
            text("SELECT column_name FROM information_schema.columns WHERE table_name = :t"),
            {"t": table},
        ).fetchall()
        return [r[0] for r in rows]
    return [r[1] for r in db.execute(text(f"PRAGMA table_info({table})")).fetchall()]


def ensure_schema():
    """轻量迁移：为旧库补充新列（新表已由 create_all 建好）"""
    db = SessionLocal()
    try:
        cols = _table_columns(db, "spus")
        if "weight_unit" not in cols:
            db.execute(text("ALTER TABLE spus ADD COLUMN weight_unit VARCHAR(16) DEFAULT '千克'"))
            db.commit()
            print(">>> 已为 spus 表补充 weight_unit 列")
        s_cols = _table_columns(db, "sale_items")
        if "cost_price" not in s_cols:
            db.execute(text("ALTER TABLE sale_items ADD COLUMN cost_price FLOAT"))
            db.commit()
            print(">>> 已为 sale_items 表补充 cost_price 列")
        # 商品档案标签字段（旧库轻量迁移）
        spu_cols = _table_columns(db, "spus")
        if "designer" not in spu_cols:
            db.execute(text("ALTER TABLE spus ADD COLUMN designer VARCHAR(128) DEFAULT ''"))
            db.commit()
            print(">>> 已为 spus 表补充 designer 列")
        if "production_date" not in spu_cols:
            db.execute(text("ALTER TABLE spus ADD COLUMN production_date DATE"))
            db.commit()
            print(">>> 已为 spus 表补充 production_date 列")
        if "material" not in spu_cols:
            db.execute(text("ALTER TABLE spus ADD COLUMN material VARCHAR(128) DEFAULT ''"))
            db.commit()
            print(">>> 已为 spus 表补充 material 列")
        if "deleted_at" not in spu_cols:
            db.execute(text("ALTER TABLE spus ADD COLUMN deleted_at DATETIME"))
            db.commit()
            print(">>> 已为 spus 表补充 deleted_at 列（回收站软删除）")
    finally:
        db.close()


def init_units():
    """初始化单位字典（仅当表为空时），用户之后可自由增删改"""
    db = SessionLocal()
    try:
        if not db.query(Unit).first():
            for name in ["件", "个", "套", "箱", "盒", "只", "包", "张", "台", "双", "支", "条", "把"]:
                db.add(Unit(name=name))
            db.commit()
            print(">>> 已初始化计数单位字典")
        if not db.query(WeightUnit).first():
            for name in ["克", "千克", "吨", "斤", "磅"]:
                db.add(WeightUnit(name=name))
            db.commit()
            print(">>> 已初始化重量单位字典")
    finally:
        db.close()


def init_boss():
    """首次启动自动创建老板账号，避免卡在登录门外。"""
    db = SessionLocal()
    try:
        if not db.query(User).filter(User.role == "boss").first():
            boss = User(
                username=os.getenv("BOSS_USERNAME", "boss"),
                password_hash=hash_password(os.getenv("BOSS_PASSWORD", "admin123")),
                nickname="老板",
                role="boss",
            )
            db.add(boss)
            db.commit()
            print(">>> 已自动创建老板账号 boss（默认密码 admin123，登录后请尽快修改）")
    finally:
        db.close()


ensure_schema()
init_units()
init_boss()


def cleanup_old_audits_on_startup():
    """服务启动时自动清理过期操作日志（保留最近 AUDIT_RETENTION_DAYS 天），
    清理成功后写入一条系统审计记录；任何异常都不影响服务启动。
    """
    db = SessionLocal()
    try:
        deleted = audit.cleanup_old_audits(db)
        if deleted:
            db.add(AuditLog(username="system", action="系统自动清理",
                            detail=f"启动时自动清理 {settings.AUDIT_RETENTION_DAYS} 天前旧日志 {deleted} 条"))
            db.commit()
            print(f">>> 已自动清理 {deleted} 条 {settings.AUDIT_RETENTION_DAYS} 天前的旧操作日志")
    except Exception as e:
        print(f">>> 自动清理旧操作日志失败（不影响启动）: {e}")
    finally:
        db.close()


def cleanup_expired_recycle_bin_on_startup():
    """服务启动时自动物理清理回收站中超过 30 天的货品（含关联流水），
    清理成功后写入一条系统审计记录；任何异常都不影响服务启动。
    """
    db = SessionLocal()
    try:
        deleted = recycle.cleanup_expired_recycle_bin(db)
        if deleted:
            db.add(AuditLog(username="system", action="回收站自动清理",
                            detail=f"启动时自动物理清理超过 {recycle.RECYCLE_RETENTION_DAYS} 天的回收站货品 {deleted} 条"))
            db.commit()
            print(f">>> 已自动物理清理回收站中 {deleted} 条超过 {recycle.RECYCLE_RETENTION_DAYS} 天的货品")
    except Exception as e:
        print(f">>> 自动清理回收站失败（不影响启动）: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    cleanup_old_audits_on_startup()
    cleanup_expired_recycle_bin_on_startup()
    yield


app = FastAPI(title="电商库存管理系统", version="0.2.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件：上传的商品图片（/static/images/...）
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# 媒体目录：背景图等用户上传文件（/media/...），目录位置随 DATA_DIR 迁移
MEDIA_DIR = Path(settings.MEDIA_DIR)
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(audit.router)
app.include_router(products.router)
app.include_router(stock.router)
app.include_router(purchase.router)
app.include_router(sales.router)
app.include_router(finance.router)
app.include_router(analysis.router)
app.include_router(senders.router)
app.include_router(label_templates.router)
app.include_router(upload.router)
app.include_router(settings_router.router)
app.include_router(recycle.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "inventory", "version": "0.2.0"}
