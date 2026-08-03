import os
from urllib.parse import urlparse

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import get_settings

settings = get_settings()

if settings.database_url.startswith("sqlite"):
    parsed = urlparse(settings.database_url)
    db_path = parsed.path
    if db_path and db_path != ":memory:":
        if db_path.startswith("/") and not db_path.startswith("//"):
            db_path = db_path[1:]
        parent_dir = os.path.dirname(db_path)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass
