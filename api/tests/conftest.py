from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.main import create_app
from app.models import Base


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    """Real PostgreSQL test database; never SQLite (row locks must be real)."""
    engine = create_engine(get_settings().test_database_url, pool_pre_ping=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    """Session bound to a connection whose outer transaction is rolled back after each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def app(db: Session) -> FastAPI:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    return app


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
