import os
from functools import lru_cache

from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

POSTGRES_CONNECT_TIMEOUT_SECONDS = 10
POSTGRES_POOL_RECYCLE_SECONDS = 300


class MissingDatabaseConfigurationError(RuntimeError):
    """Raised when DATABASE_URL is required but not configured."""


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise MissingDatabaseConfigurationError(
            "DATABASE_URL environment variable is not set."
        )

    parsed_url = make_url(database_url)
    host = parsed_url.host or ""
    query = dict(parsed_url.query)

    if (
        parsed_url.drivername.startswith("postgresql")
        and host.endswith("render.com")
        and "sslmode" not in query
    ):
        parsed_url = parsed_url.set(query={**query, "sslmode": "require"})
        return parsed_url.render_as_string(hide_password=False)

    return database_url


def get_engine_kwargs(database_url: str) -> dict:
    parsed_url = make_url(database_url)

    if not parsed_url.drivername.startswith("postgresql"):
        return {}

    query = dict(parsed_url.query)
    connect_args = {}

    if "connect_timeout" not in query:
        connect_args["connect_timeout"] = POSTGRES_CONNECT_TIMEOUT_SECONDS

    # Render Postgres can drop pooled SSL connections after idle periods.
    # These settings make the pool validate and recycle connections before reuse.
    engine_kwargs = {
        "pool_pre_ping": True,
        "pool_recycle": POSTGRES_POOL_RECYCLE_SECONDS,
        "pool_use_lifo": True,
    }

    if connect_args:
        engine_kwargs["connect_args"] = connect_args

    return engine_kwargs


@lru_cache
def get_engine() -> Engine:
    database_url = get_database_url()
    return create_engine(database_url, **get_engine_kwargs(database_url))


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
