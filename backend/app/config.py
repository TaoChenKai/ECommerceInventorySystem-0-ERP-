import os
import shutil
from pathlib import Path
from pydantic_settings import BaseSettings

# backend 运行目录（app/../ = backend/）
BACKEND_DIR = Path(__file__).resolve().parent.parent

# .env 路径：默认 backend/.env，可用环境变量 SETTINGS_ENV_FILE 覆盖（回归测试隔离用）
ENV_FILE = os.environ.get("SETTINGS_ENV_FILE", str(BACKEND_DIR / ".env"))


class Settings(BaseSettings):
    # 数据库连接：未显式配置时基于 DATA_DIR 自动生成 SQLite 绝对路径
    DATABASE_URL: str = ""
    SECRET_KEY: str = "please-change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    BOSS_USERNAME: str = "boss"
    BOSS_PASSWORD: str = "admin123"
    # 操作日志自动保留天数：服务启动时自动删除早于该天数的旧日志（可配置）
    AUDIT_RETENTION_DAYS: int = 90
    # 数据目录 / 媒体目录（相对路径以 backend 目录为基准）
    DATA_DIR: str = ""
    MEDIA_DIR: str = ""

    class Config:
        env_file = ENV_FILE
        extra = "ignore"

    def model_post_init(self, __context) -> None:
        # 数据目录
        data_dir = Path(self.DATA_DIR) if self.DATA_DIR else (BACKEND_DIR / "data")
        if not data_dir.is_absolute():
            data_dir = BACKEND_DIR / data_dir
        data_dir = data_dir.resolve()
        data_dir.mkdir(parents=True, exist_ok=True)
        self.DATA_DIR = str(data_dir)

        # 媒体目录（上传的背景图等）
        media_dir = Path(self.MEDIA_DIR) if self.MEDIA_DIR else (data_dir / "media")
        if not media_dir.is_absolute():
            media_dir = data_dir / media_dir
        media_dir.mkdir(parents=True, exist_ok=True)
        self.MEDIA_DIR = str(media_dir)

        # 数据库连接统一入口：SQLite 一律归一到 DATA_DIR/inventory.db
        # （设置中心的存储迁移基于 DATA_DIR，必须保证两者一致）
        self.DATABASE_URL = normalize_sqlite_url(self.DATABASE_URL, data_dir)


def normalize_sqlite_url(database_url: str, data_dir: Path) -> str:
    """统一 SQLite 数据库连接，保证与设置中心的 DATA_DIR 语义一致。

    - database_url 为空：默认 data_dir/inventory.db；旧库 backend/inventory.db 是文件则一次性复制进来
    - database_url 为 sqlite:/// 相对路径（如 ./inventory.db，按 backend 目录解析）：
      一律规范为 data_dir/inventory.db；若指向旧位置且 data_dir/inventory.db 不存在则先复制旧库（数据不丢）
    - database_url 为 sqlite:/// 绝对路径：尊重显式配置，原样保留（回归测试/高级配置依赖此行为）
    - database_url 为 PostgreSQL 等非 sqlite：原样保留，不做归一
    """
    data_dir = Path(data_dir)
    new_db = data_dir / "inventory.db"

    if not database_url:
        old_db = BACKEND_DIR / "inventory.db"
        if not new_db.exists() and old_db.is_file():
            new_db.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(old_db, new_db)
            print(f">>> 已把旧数据库一次性迁移到 {new_db}")
        return f"sqlite:///{new_db.as_posix()}"

    if not database_url.startswith("sqlite:///"):
        return database_url

    sql_path = Path(database_url[len("sqlite:///"):])
    if not sql_path.is_absolute():
        # 相对路径：以 backend 目录为基准解析，归一到 data_dir
        sql_path = (BACKEND_DIR / sql_path).resolve()
        if sql_path != new_db and sql_path.is_file() and not new_db.exists():
            new_db.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(sql_path, new_db)
            print(f">>> 已把旧数据库 {sql_path} 迁移到 {new_db}")
        return f"sqlite:///{new_db.as_posix()}"

    # 绝对路径：尊重显式配置，保留原样
    return database_url


def persist_settings(new_dir: str, new_url: str | None = None) -> str:
    """把新的数据配置持久化到 .env，返回 .env 文件路径。

    - 必写 DATA_DIR 行（更新或追加）
    - new_url 非空时同步更新 DATABASE_URL 行（保证重启后仍指向迁移后的新库）
    - .env 不存在时以 .env.example 为模板初始化
    """
    env_file = Path(ENV_FILE)
    lines: list[str] = []
    if env_file.exists():
        lines = env_file.read_text(encoding="utf-8").splitlines()
    else:
        example = BACKEND_DIR / ".env.example"
        if example.exists():
            lines = example.read_text(encoding="utf-8").splitlines()

    def upsert(key: str, value: str) -> None:
        nonlocal lines
        replaced = False
        out: list[str] = []
        for ln in lines:
            if ln.strip().startswith(f"{key}="):
                out.append(f"{key}={value}")
                replaced = True
            else:
                out.append(ln)
        if not replaced:
            out.append(f"{key}={value}")
        lines = out

    upsert("DATA_DIR", new_dir)
    if new_url:
        upsert("DATABASE_URL", new_url)
    env_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(env_file)


settings = Settings()
