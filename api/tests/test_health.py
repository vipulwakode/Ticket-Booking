from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.core.errors import AppError
from app.db.session import get_db


def test_health_ok_against_postgres(client: TestClient) -> None:
    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


def test_health_returns_503_when_database_is_down(app: FastAPI, client: TestClient) -> None:
    class BrokenSession:
        def execute(self, *_args, **_kwargs):
            raise OperationalError("SELECT 1", {}, Exception("connection refused"))

    app.dependency_overrides[get_db] = lambda: BrokenSession()

    response = client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json() == {
        "code": "SERVICE_UNAVAILABLE",
        "message": "Database is unavailable",
        "details": {},
    }


def test_unknown_route_uses_error_shape(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"code": "NOT_FOUND", "message": "Not Found", "details": {}}


def test_app_error_is_returned_as_json(app: FastAPI, client: TestClient) -> None:
    @app.get("/test/app-error")
    def boom() -> None:
        raise AppError("SEAT_UNAVAILABLE", "Seats taken", 409, {"seat_ids": [1, 2]})

    response = client.get("/test/app-error")

    assert response.status_code == 409
    assert response.json() == {
        "code": "SEAT_UNAVAILABLE",
        "message": "Seats taken",
        "details": {"seat_ids": [1, 2]},
    }


def test_validation_error_uses_error_shape(app: FastAPI, client: TestClient) -> None:
    @app.get("/test/validate")
    def validate(page: int) -> dict[str, int]:
        return {"page": page}

    response = client.get("/test/validate", params={"page": "abc"})

    assert response.status_code == 422
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert body["details"]["errors"][0]["loc"] == ["query", "page"]


def test_unhandled_error_hides_stack_trace(app: FastAPI, client: TestClient) -> None:
    @app.get("/test/crash")
    def crash() -> None:
        raise RuntimeError("secret internals")

    response = client.get("/test/crash")

    assert response.status_code == 500
    assert response.json() == {
        "code": "INTERNAL_ERROR",
        "message": "Something went wrong",
        "details": {},
    }
