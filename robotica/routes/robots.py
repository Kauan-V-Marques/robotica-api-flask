"""Cadastro de robôs e estatísticas de carreira."""

from datetime import UTC, datetime

from flask import Blueprint, request
from pymongo import ReturnDocument

from robotica.db import get_db, object_id
from robotica.errors import BusinessRule, NotFound
from robotica.json_provider import to_api
from robotica.models import CATEGORIES, RobotIn, RobotPatch
from robotica.stats import robot_stats_pipeline

bp = Blueprint("robots", __name__, url_prefix="/api/robots")


def find_robot(robot_id: str) -> dict:
    robot = get_db().robots.find_one({"_id": object_id(robot_id, "Robô")})
    if robot is None:
        raise NotFound(f"Robô {robot_id} não encontrado.")
    return robot


@bp.get("")
def list_robots():
    query = {}
    if category := request.args.get("category"):
        query["category"] = category
    if team := request.args.get("team"):
        query["team"] = team
    robots = get_db().robots.find(query).sort([("team", 1), ("name", 1)])
    return [to_api(r) for r in robots]


@bp.get("/categories")
def list_categories():
    return [{"code": code, **info} for code, info in CATEGORIES.items()]


@bp.post("")
def create_robot():
    data = RobotIn.model_validate(request.get_json(force=True, silent=True) or {})
    document = {**data.model_dump(), "created_at": datetime.now(UTC)}
    result = get_db().robots.insert_one(document)
    return to_api({"_id": result.inserted_id, **document}), 201


@bp.get("/<robot_id>")
def get_robot(robot_id: str):
    return to_api(find_robot(robot_id))


@bp.patch("/<robot_id>")
def update_robot(robot_id: str):
    robot = find_robot(robot_id)
    changes = RobotPatch.model_validate(request.get_json(force=True, silent=True) or {}).model_dump(
        exclude_none=True
    )
    if "weight_g" in changes:
        limit = CATEGORIES[robot["category"]]["max_weight_g"]
        if changes["weight_g"] > limit:
            raise BusinessRule(f"Peso acima do limite da categoria ({limit} g).")
    if not changes:
        return to_api(robot)

    updated = get_db().robots.find_one_and_update(
        {"_id": robot["_id"]}, {"$set": changes}, return_document=ReturnDocument.AFTER
    )
    return to_api(updated)


@bp.delete("/<robot_id>")
def delete_robot(robot_id: str):
    robot = find_robot(robot_id)
    database = get_db()
    has_history = database.matches.find_one(
        {"$or": [{"robot_a": robot["_id"]}, {"robot_b": robot["_id"]}]}
    ) or database.runs.find_one({"robot_id": robot["_id"]})
    if has_history:
        raise BusinessRule("Robô já tem partidas ou tomadas de tempo registradas e não pode ser excluído.")
    database.robots.delete_one({"_id": robot["_id"]})
    return "", 204


@bp.get("/<robot_id>/stats")
def robot_stats(robot_id: str):
    robot = find_robot(robot_id)
    stats = next(get_db().matches.aggregate(robot_stats_pipeline(robot["_id"])), None)
    empty = {"played": 0, "wins": 0, "draws": 0, "losses": 0, "rounds_for": 0, "rounds_against": 0}
    stats = {**empty, **(stats or {})}
    stats.pop("_id", None)
    stats["win_rate"] = round(stats["wins"] / stats["played"], 3) if stats["played"] else None
    return {"robot": to_api(robot), "stats": stats}
