import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, scoped_session, sessionmaker


class Base(DeclarativeBase):
    """
    Declarative base for SQLAlchemy models.
    """

    pass


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+pysqlite:///training.db")

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = scoped_session(
    sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
)
