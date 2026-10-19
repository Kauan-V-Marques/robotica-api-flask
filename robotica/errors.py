"""Erros de domínio e respostas JSON padronizadas."""

from flask import Flask, jsonify
from pydantic import ValidationError
from pymongo.errors import DuplicateKeyError
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    status = 400

    def __init__(self, message: str, details=None):
        super().__init__(message)
        self.message = message
        self.details = details


class NotFound(ApiError):
    status = 404


class Conflict(ApiError):
    status = 409


class BusinessRule(ApiError):
    status = 422


def _body(message: str, status: int, details=None):
    body = {"error": message, "status": status}
    if details is not None:
        body["details"] = details
    return jsonify(body), status


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(ApiError)
    def api_error(error: ApiError):
        return _body(error.message, error.status, error.details)

    @app.errorhandler(ValidationError)
    def validation_error(error: ValidationError):
        details = [
            {"field": ".".join(str(p) for p in e["loc"]), "message": e["msg"]}
            for e in error.errors(include_url=False)
        ]
        return _body("Dados inválidos.", 400, details)

    @app.errorhandler(DuplicateKeyError)
    def duplicate(_error: DuplicateKeyError):
        return _body("Já existe um registro com esses dados.", 409)

    @app.errorhandler(HTTPException)
    def http_error(error: HTTPException):
        return _body(error.description or error.name, error.code or 500)
