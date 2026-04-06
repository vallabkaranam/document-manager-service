import os
from functools import lru_cache

from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()


class MissingDatabaseConfigurationError(RuntimeError):
    """Raised when DATABASE_URL is required but not configured."""


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise MissingDatabaseConfigurationError(
            "DATABASE_URL environment variable is not set."
        )
    return database_url


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_database_url())


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return sessionmaker(autocommit=False, autoflush=False, bind=get_engine())


def SessionLocal() -> Session:
    return get_session_factory()()


def get_db():
    try:
        db = SessionLocal()
    except MissingDatabaseConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    try:
        yield db
    finally:
        db.close()
