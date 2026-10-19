"""Pipelines de agregação do MongoDB usados no ranking e nas estatísticas."""

from bson import ObjectId

# Cada partida vira dois "lados" (um por robô), com rounds a favor e contra.
_SIDES = [
    {
        "$project": {
            "sides": [
                {"robot": "$robot_a", "for": "$score_a", "against": "$score_b"},
                {"robot": "$robot_b", "for": "$score_b", "against": "$score_a"},
            ]
        }
    },
    {"$unwind": "$sides"},
    {"$replaceRoot": {"newRoot": "$sides"}},
]

_TOTALS = {
    "played": {"$sum": 1},
    "wins": {"$sum": {"$cond": [{"$gt": ["$for", "$against"]}, 1, 0]}},
    "draws": {"$sum": {"$cond": [{"$eq": ["$for", "$against"]}, 1, 0]}},
    "losses": {"$sum": {"$cond": [{"$lt": ["$for", "$against"]}, 1, 0]}},
    "rounds_for": {"$sum": "$for"},
    "rounds_against": {"$sum": "$against"},
}


def matches_ranking_pipeline(event_id: ObjectId, category: str) -> list[dict]:
    """Tabela de pontos: vitória 3, empate 1. Desempate por saldo de rounds e vitórias."""
    return [
        {"$match": {"event_id": event_id, "category": category}},
        *_SIDES,
        {"$group": {"_id": "$robot", **_TOTALS}},
        {
            "$addFields": {
                "points": {"$add": [{"$multiply": ["$wins", 3]}, "$draws"]},
                "round_diff": {"$subtract": ["$rounds_for", "$rounds_against"]},
            }
        },
        {"$lookup": {"from": "robots", "localField": "_id", "foreignField": "_id", "as": "robot"}},
        {"$unwind": "$robot"},
        # $rank aceita só uma chave de ordenação; a posição com desempate é calculada em assign_positions
        {"$sort": {"points": -1, "round_diff": -1, "wins": -1, "robot.name": 1}},
        {
            # $replaceWith mantém a ordem dos campos como escrita aqui
            "$replaceWith": {
                "robot_id": "$_id",
                "robot": "$robot.name",
                "team": "$robot.team",
                "points": "$points",
                "played": "$played",
                "wins": "$wins",
                "draws": "$draws",
                "losses": "$losses",
                "rounds_for": "$rounds_for",
                "rounds_against": "$rounds_against",
                "round_diff": "$round_diff",
            }
        },
    ]


TIEBREAK_KEYS = ("points", "round_diff", "wins")


def assign_positions(rows: list[dict], keys: tuple[str, ...] = TIEBREAK_KEYS) -> list[dict]:
    """Classificação "olímpica": empatados em todos os critérios dividem a posição (1, 1, 3...)."""
    ranked: list[dict] = []
    previous = None
    for index, row in enumerate(rows, start=1):
        current = tuple(row[k] for k in keys)
        position = ranked[-1]["position"] if current == previous else index
        ranked.append({"position": position, **row})
        previous = current
    return ranked


def time_ranking_pipeline(event_id: ObjectId, category: str) -> list[dict]:
    """Seguidor de linha: vale a melhor tomada de tempo válida de cada robô."""
    return [
        {"$match": {"event_id": event_id, "category": category, "valid": True}},
        {
            "$group": {
                "_id": "$robot_id",
                "best_ms": {"$min": "$time_ms"},
                "average_ms": {"$avg": "$time_ms"},
                "valid_runs": {"$sum": 1},
            }
        },
        {"$lookup": {"from": "robots", "localField": "_id", "foreignField": "_id", "as": "robot"}},
        {"$unwind": "$robot"},
        {"$setWindowFields": {"sortBy": {"best_ms": 1}, "output": {"position": {"$rank": {}}}}},
        {"$sort": {"position": 1, "robot.name": 1}},
        {
            "$replaceWith": {
                "position": "$position",
                "robot_id": "$_id",
                "robot": "$robot.name",
                "team": "$robot.team",
                "best_ms": "$best_ms",
                "average_ms": {"$toInt": {"$round": ["$average_ms", 0]}},
                "valid_runs": "$valid_runs",
            }
        },
    ]


def robot_stats_pipeline(robot_id: ObjectId) -> list[dict]:
    """Totais de carreira de um robô em todas as competições."""
    return [
        {"$match": {"$or": [{"robot_a": robot_id}, {"robot_b": robot_id}]}},
        *_SIDES,
        {"$match": {"robot": robot_id}},
        {"$group": {"_id": "$robot", **_TOTALS}},
    ]
