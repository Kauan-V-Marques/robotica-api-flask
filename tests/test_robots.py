def test_create_and_get_robot(client):
    response = client.post(
        "/api/robots",
        json={"name": "Tornado", "team": "Equipe Alfa", "category": "sumo_3kg", "weight_g": 2980},
    )

    assert response.status_code == 201
    robot = response.get_json()
    assert robot["name"] == "Tornado"
    assert client.get(f"/api/robots/{robot['id']}").get_json()["team"] == "Equipe Alfa"


def test_weight_above_category_limit_is_rejected(client):
    response = client.post(
        "/api/robots",
        json={"name": "Pesado", "team": "Equipe Alfa", "category": "sumo_500g", "weight_g": 650},
    )

    assert response.status_code == 400
    assert "500 g" in response.get_json()["details"][0]["message"]


def test_unknown_fields_and_categories_are_rejected(client):
    response = client.post(
        "/api/robots",
        json={"name": "X1", "team": "Equipe", "category": "voador", "weight_g": 10, "cor": "azul"},
    )

    fields = {d["field"] for d in response.get_json()["details"]}
    assert response.status_code == 400
    assert {"category", "cor"} <= fields


def test_same_name_in_same_team_is_a_conflict(client, make_robot):
    make_robot(name="Gemeo", team="Equipe Beta")

    response = client.post(
        "/api/robots", json={"name": "Gemeo", "team": "Equipe Beta", "category": "sumo_3kg", "weight_g": 2000}
    )

    assert response.status_code == 409


def test_list_filters_by_category(client, make_robot):
    make_robot(category="sumo_3kg")
    line = make_robot(category="seguidor_de_linha")

    robots = client.get("/api/robots?category=seguidor_de_linha").get_json()

    assert [r["id"] for r in robots] == [line["id"]]


def test_malformed_or_missing_id_returns_404(client):
    assert client.get("/api/robots/123").status_code == 404
    assert client.get("/api/robots/64b7f0f0f0f0f0f0f0f0f0f0").status_code == 404


def test_patch_respects_weight_limit(client, make_robot):
    robot = make_robot(category="sumo_100g")

    ok = client.patch(f"/api/robots/{robot['id']}", json={"weight_g": 99})
    too_heavy = client.patch(f"/api/robots/{robot['id']}", json={"weight_g": 120})

    assert ok.get_json()["weight_g"] == 99
    assert too_heavy.status_code == 422


def test_robot_with_history_cannot_be_deleted(client, make_robot, play):
    a, b, free = make_robot(), make_robot(), make_robot()
    play(a, b, 2, 0)

    assert client.delete(f"/api/robots/{a['id']}").status_code == 422
    assert client.delete(f"/api/robots/{free['id']}").status_code == 204


def test_career_stats_aggregate_all_matches(client, make_robot, play):
    a, b, c = make_robot(), make_robot(), make_robot()
    play(a, b, 2, 1)
    play(c, a, 2, 0)
    play(a, c, 1, 1)

    stats = client.get(f"/api/robots/{a['id']}/stats").get_json()["stats"]

    assert stats["played"] == 3
    assert (stats["wins"], stats["draws"], stats["losses"]) == (1, 1, 1)
    assert (stats["rounds_for"], stats["rounds_against"]) == (3, 4)
    assert stats["win_rate"] == 0.333
