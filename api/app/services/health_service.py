import logging

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core import error_codes
from app.core.errors import AppError
from app.repositories import health_repository
from app.schemas.health import HealthResponse

logger = logging.getLogger(__name__)


def check_health(db: Session) -> HealthResponse:
    try:
        health_repository.ping(db)
    except SQLAlchemyError as exc:
        logger.warning("Database health check failed: %s", exc)
        raise AppError(
            error_codes.SERVICE_UNAVAILABLE, "Database is unavailable", status_code=503
        ) from exc
    return HealthResponse(status="ok", database="ok")
