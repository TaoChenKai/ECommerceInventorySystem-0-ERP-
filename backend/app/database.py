from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from .config import settings

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def reconfigure_engine(url: str):
    """迁移数据目录后重建全局 engine / SessionLocal（dispose 旧连接池）。"""
    global engine, SessionLocal
    connect = {"check_same_thread": False} if url.startswith("sqlite") else {}
    engine.dispose()
    engine = create_engine(url, connect_args=connect)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
