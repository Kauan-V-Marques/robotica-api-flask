"""Serializa ObjectId e datas do MongoDB no JSON das respostas."""

from datetime import date, datetime

from bson import ObjectId
from flask.json.provider import DefaultJSONProvider


class MongoJSONProvider(DefaultJSONProvider):
    sort_keys = False

    @staticmethod
    def default(o):
        if isinstance(o, ObjectId):
            return str(o)
        if isinstance(o, datetime | date):
            return o.isoformat()
        return DefaultJSONProvider.default(o)


def to_api(document: dict | None) -> dict | None:
    """Troca o _id do Mongo por id."""
    if document is None:
        return None
    result = {"id": document["_id"], **{k: v for k, v in document.items() if k != "_id"}}
    return result
