"""Competições, partidas (sumô) e tomadas de tempo (seguidor de linha)."""

from datetime import UTC, date, datetime, time

from flask import Blueprint, request

from robotica.db import get_db, object_id
from robotica.errors import BusinessRule, NotFound
from robotica.json_provider import to_api
from robotica.models import CATEGORIES, EventIn, MatchIn, RunIn
from robotica.routes.robots import find_robot

bp = Blueprint("events", __name__, url_prefix="/api/events")


def _as_datetime(value: date) -> datetime:
    # O BSON não tem tipo "date"; a data é guardada como meia-noite UTC
    return datetime.combine(value, time.min, tzinfo=UTC)


def _event_to_api(event: dict) -> dict:
    result = to_api(event)
    result["start_date"] = event["start_date"].date().isoformat()
    result["end_date"] = event["end_date"].date().isoformat()
    return result


def find_event(event_id: str) -> dict:
    event = get_db().events.find_one({"_id": object_id(event_id, "Evento")})
    if event is None:
        raise NotFound(f"Evento {event_id} não encontrado.")
    return event


@bp.get("")
def list_events():
    return [_event_to_api(e) for e in get_db().events.find().sort("start_date", -1)]


@bp.post("")
def create_event():
    data = EventIn.model_validate(request.get_json(force=True, silent=True) or {})
    document = {
        "name": data.name,
        "city": data.city,
        "start_date": _as_datetime(data.start_date),
        "end_date": _as_datetime(data.end_date),
    }
    result = get_db().events.insert_one(document)
    return _event_to_api({"_id": result.inserted_id, **document}), 201


@bp.get("/<event_id>")
def get_event(event_id: str):
    event = find_event(event_id)
    database = get_db()
    summary = {}
    for code, info in CATEGORIES.items():
        collection = database.matches if info["mode"] == "partidas" else database.runs
        count = collection.count_documents({"event_id": event["_id"], "category": code})
        if count:
            summary[code] = {"name": info["name"], "mode": info["mode"], "records": count}
    return {**_event_to_api(event), "categories": summary}


@bp.post("/<event_id>/matches")
def create_match(event_id: str):
    event = find_event(event_id)
    data = MatchIn.model_validate(request.get_json(force=True, silent=True) or {})
    robot_a, robot_b = find_robot(data.robot_a), find_robot(data.robot_b)

    if robot_a["category"] != robot_b["category"]:
        raise BusinessRule("Os robôs precisam ser da mesma categoria.")
    category = robot_a["category"]
    if CATEGORIES[category]["mode"] != "partidas":
        raise BusinessRule(f"A categoria {category} é disputada por tempo, não por partidas.")

    winner = None
    if data.score_a != data.score_b:
        winner = robot_a["_id"] if data.score_a > data.score_b else robot_b["_id"]

    document = {
        "event_id": event["_id"],
        "category": category,
        "round": data.round,
        "robot_a": robot_a["_id"],
        "robot_b": robot_b["_id"],
        "score_a": data.score_a,
        "score_b": data.score_b,
        "winner": winner,
        "played_at": datetime.now(UTC),
    }
    result = get_db().matches.insert_one(document)
    return to_api({"_id": result.inserted_id, **document}), 201


@bp.get("/<event_id>/matches")
def list_matches(event_id: str):
    event = find_event(event_id)
    query = {"event_id": event["_id"]}
    if category := request.args.get("category"):
        query["category"] = category
    pipeline = [
        {"$match": query},
        {"$sort": {"played_at": 1}},
        {"$lookup": {"from": "robots", "localField": "robot_a", "foreignField": "_id", "as": "a"}},
        {"$lookup": {"from": "robots", "localField": "robot_b", "foreignField": "_id", "as": "b"}},
        {
            "$addFields": {
                "robot_a_name": {"$first": "$a.name"},
                "robot_b_name": {"$first": "$b.name"},
            }
        },
        {"$project": {"a": 0, "b": 0}},
    ]
    return [to_api(m) for m in get_db().matches.aggregate(pipeline)]


@bp.post("/<event_id>/runs")
def create_run(event_id: str):
    event = find_event(event_id)
    data = RunIn.model_validate(request.get_json(force=True, silent=True) or {})
    robot = find_robot(data.robot_id)
    if CATEGORIES[robot["category"]]["mode"] != "tempo":
        raise BusinessRule(f"A categoria {robot['category']} é disputada em partidas, não por tempo.")

    document = {
        "event_id": event["_id"],
        "category": robot["category"],
        "robot_id": robot["_id"],
        "time_ms": data.time_ms,
        "valid": data.valid,
        "run_at": datetime.now(UTC),
    }
    result = get_db().runs.insert_one(document)
    return to_api({"_id": result.inserted_id, **document}), 201
