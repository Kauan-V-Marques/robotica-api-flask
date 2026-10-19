"""Cada sessão de testes usa um banco MongoDB próprio, apagado no final.

Servidor: variável TEST_MONGO_URI (padrão: mongodb://localhost:27017).
"""

import os
import uuid

import pytest
from pymongo import MongoClient

from robotica import create_app

SERVER = os.environ.get("TEST_MONGO_URI", "mongodb://localhost:27017")


@pytest.fixture(scope="session")
def database_name():
    name = f"robotica_test_{uuid.uuid4().hex[:8]}"
    yield name
    MongoClient(SERVER).drop_database(name)


@pytest.fixture()
def app(database_name):
    app = create_app({"TESTING": True, "MONGO_URI": f"{SERVER.rstrip('/')}/{database_name}"})
    database = app.extensions["mongo_db"]
    for name in ("robots", "events", "matches", "runs"):
        database[name].delete_many({})
    yield app
    app.extensions["mongo_client"].close()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def make_robot(client):
    counter = iter(range(1, 1000))

    def _make(category="sumo_3kg", weight_g=None, name=None, team="Equipe Teste"):
        weight = weight_g or {"sumo_3kg": 2900, "sumo_500g": 480, "sumo_100g": 95}.get(category, 400)
        response = client.post(
            "/api/robots",
            json={
                "name": name or f"Robo {next(counter)}",
                "team": team,
                "category": category,
                "weight_g": weight,
            },
        )
        assert response.status_code == 201, response.get_json()
        return response.get_json()

    return _make


@pytest.fixture()
def event(client):
    response = client.post(
        "/api/events",
        json={
            "name": "Torneio de Teste",
            "city": "Sorocaba, SP",
            "start_date": "2026-11-14",
            "end_date": "2026-11-15",
        },
    )
    assert response.status_code == 201
    return response.get_json()


@pytest.fixture()
def play(client, event):
    def _play(robot_a, robot_b, score_a, score_b, round_name="classificatoria"):
        response = client.post(
            f"/api/events/{event['id']}/matches",
            json={
                "robot_a": robot_a["id"],
                "robot_b": robot_b["id"],
                "score_a": score_a,
                "score_b": score_b,
                "round": round_name,
            },
        )
        assert response.status_code == 201, response.get_json()
        return response.get_json()

    return _play
