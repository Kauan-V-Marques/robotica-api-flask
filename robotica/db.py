"""Conexão com o MongoDB e criação dos índices."""

from bson import ObjectId
from bson.errors import InvalidId
from flask import Flask, current_app
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.database import Database

from robotica.errors import NotFound


def init_app(app: Flask) -> None:
    client = MongoClient(app.config["MONGO_URI"], tz_aware=True, serverSelectionTimeoutMS=5000)
    app.extensions["mongo_client"] = client
    app.extensions["mongo_db"] = client.get_default_database(default="robotica")
    ensure_indexes(app.extensions["mongo_db"])


def get_db() -> Database:
    return current_app.extensions["mongo_db"]


def ensure_indexes(database: Database) -> None:
    database.robots.create_index([("team", ASCENDING), ("name", ASCENDING)], unique=True)
    database.robots.create_index("category")
    database.matches.create_index([("event_id", ASCENDING), ("category", ASCENDING)])
    database.matches.create_index("robot_a")
    database.matches.create_index("robot_b")
    database.runs.create_index([("event_id", ASCENDING), ("category", ASCENDING), ("time_ms", ASCENDING)])
    database.events.create_index([("start_date", DESCENDING)])


def object_id(value: str, what: str = "Registro") -> ObjectId:
    """Converte o id da URL; id malformado é tratado como não encontrado."""
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        raise NotFound(f"{what} {value} não encontrado.") from None
