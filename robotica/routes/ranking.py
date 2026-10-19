"""Classificação de uma categoria em uma competição."""

from flask import Blueprint, request

from robotica.db import get_db
from robotica.errors import ApiError
from robotica.models import CATEGORIES
from robotica.routes.events import find_event
from robotica.stats import assign_positions, matches_ranking_pipeline, time_ranking_pipeline

bp = Blueprint("ranking", __name__, url_prefix="/api/events")


@bp.get("/<event_id>/ranking")
def ranking(event_id: str):
    event = find_event(event_id)
    category = request.args.get("category", "")
    if category not in CATEGORIES:
        raise ApiError("Informe uma categoria válida.", {"allowed": list(CATEGORIES)})

    info = CATEGORIES[category]
    database = get_db()
    if info["mode"] == "partidas":
        rows = assign_positions(
            list(database.matches.aggregate(matches_ranking_pipeline(event["_id"], category)))
        )
    else:
        rows = list(database.runs.aggregate(time_ranking_pipeline(event["_id"], category)))

    return {
        "event": {"id": event["_id"], "name": event["name"]},
        "category": {"code": category, **info},
        "ranking": rows,
    }
