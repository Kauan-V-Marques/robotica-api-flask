"""Carrega uma competição de exemplo (dados fictícios): flask --app robotica seed"""

import random
from datetime import UTC, date, datetime, time

import click
from flask import Flask

from robotica.db import get_db

ROBOTS = [
    ("Tornado", "Equipe Alfa", "sumo_3kg", 2980),
    ("Rolo Compressor", "Equipe Beta", "sumo_3kg", 2995),
    ("Bigorna", "Equipe Gama", "sumo_3kg", 2970),
    ("Muralha", "Equipe Delta", "sumo_3kg", 2990),
    ("Faisca", "Equipe Alfa", "sumo_500g", 498),
    ("Pimenta", "Equipe Beta", "sumo_500g", 495),
    ("Formiga", "Equipe Gama", "sumo_500g", 499),
    ("Cometa", "Equipe Alfa", "seguidor_de_linha", 410),
    ("Raio", "Equipe Delta", "seguidor_de_linha", 385),
    ("Coruja", "Equipe Gama", "seguidor_de_linha", 450),
]

# (robô A, robô B, rounds A, rounds B, fase)
MATCHES = [
    ("Tornado", "Rolo Compressor", 2, 1, "classificatoria"),
    ("Bigorna", "Muralha", 0, 2, "classificatoria"),
    ("Tornado", "Bigorna", 2, 0, "classificatoria"),
    ("Rolo Compressor", "Muralha", 1, 1, "classificatoria"),
    ("Tornado", "Muralha", 1, 2, "classificatoria"),
    ("Rolo Compressor", "Bigorna", 2, 0, "classificatoria"),
    ("Muralha", "Tornado", 2, 1, "final"),
    ("Faisca", "Pimenta", 2, 0, "classificatoria"),
    ("Pimenta", "Formiga", 2, 1, "classificatoria"),
    ("Formiga", "Faisca", 0, 2, "classificatoria"),
]

RUNS = {"Cometa": [18432, 17950, 18110], "Raio": [17620, 19870, 17705], "Coruja": [21004, 20456]}


def _midnight(value: date) -> datetime:
    return datetime.combine(value, time.min, tzinfo=UTC)


def load_sample_data() -> dict:
    database = get_db()
    for name in ("robots", "events", "matches", "runs"):
        database[name].delete_many({})

    event_id = database.events.insert_one(
        {
            "name": "Copa Sorocaba de Robotica 2026",
            "city": "Sorocaba, SP",
            "start_date": _midnight(date(2026, 11, 14)),
            "end_date": _midnight(date(2026, 11, 15)),
        }
    ).inserted_id

    now = datetime.now(UTC)
    ids = {}
    for name, team, category, weight in ROBOTS:
        ids[name] = database.robots.insert_one(
            {"name": name, "team": team, "category": category, "weight_g": weight, "created_at": now}
        ).inserted_id

    categories = {name: category for name, _, category, _ in ROBOTS}
    for a, b, score_a, score_b, round_name in MATCHES:
        winner = None if score_a == score_b else (ids[a] if score_a > score_b else ids[b])
        database.matches.insert_one(
            {
                "event_id": event_id,
                "category": categories[a],
                "round": round_name,
                "robot_a": ids[a],
                "robot_b": ids[b],
                "score_a": score_a,
                "score_b": score_b,
                "winner": winner,
                "played_at": now,
            }
        )

    rng = random.Random(42)
    for name, times in RUNS.items():
        for time_ms in times:
            database.runs.insert_one(
                {
                    "event_id": event_id,
                    "category": "seguidor_de_linha",
                    "robot_id": ids[name],
                    "time_ms": time_ms,
                    "valid": rng.random() > 0.1,
                    "run_at": now,
                }
            )

    return {"event_id": str(event_id), "robots": len(ROBOTS), "matches": len(MATCHES)}


def register_seed_command(app: Flask) -> None:
    @app.cli.command("seed")
    def seed():
        """Apaga os dados e carrega a competição de exemplo."""
        result = load_sample_data()
        click.echo(f"Competicao de exemplo criada: {result}")
