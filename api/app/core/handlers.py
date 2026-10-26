import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core import error_codes
from app.core.errors import AppError

logger = logging.getLogger(__name__)

_HTTP_CODES = {
    404: error_codes.NOT_FOUND,
    405: error_codes.METHOD_NOT_ALLOWED,
}


def error_response(status_code: int, code: str, message: str, details: Any = None) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"code": code, "message": message, "details": jsonable_encoder(details or {})},
    )


async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return error_response(exc.status_code, exc.code, exc.message, exc.details)


async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    errors = [
        {"loc": list(e.get("loc", [])), "msg": e.get("msg"), "type": e.get("type")}
        for e in exc.errors()
    ]
    return error_response(
        422, error_codes.VALIDATION_ERROR, "Request validation failed", {"errors": errors}
    )


async def http_error_handler(_: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = _HTTP_CODES.get(exc.status_code, error_codes.HTTP_ERROR)
    return error_response(exc.status_code, code, str(exc.detail))


async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return error_response(500, error_codes.INTERNAL_ERROR, "Something went wrong")


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(RequestValidationError, validation_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_error_handler)
    app.add_exception_handler(Exception, unhandled_error_handler)
