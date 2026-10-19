def ranking(client, event, category):
    response = client.get(f"/api/events/{event['id']}/ranking?category={category}")
    assert response.status_code == 200, response.get_json()
    return response.get_json()["ranking"]


def test_event_end_date_cannot_be_before_start(client):
    response = client.post(
        "/api/events",
        json={"name": "Copa", "city": "Sorocaba", "start_date": "2026-11-15", "end_date": "2026-11-14"},
    )

    assert response.status_code == 400


def test_match_sets_winner_from_score(make_robot, play):
    a, b = make_robot(), make_robot()

    match = play(a, b, 1, 2)
    draw = play(a, b, 1, 1)

    assert match["winner"] == b["id"]
    assert draw["winner"] is None


def test_match_requires_same_category(client, event, make_robot):
    heavy, light = make_robot("sumo_3kg"), make_robot("sumo_500g")

    response = client.post(
        f"/api/events/{event['id']}/matches",
        json={"robot_a": heavy["id"], "robot_b": light["id"], "score_a": 2, "score_b": 0},
    )

    assert response.status_code == 422


def test_robot_cannot_fight_itself(client, event, make_robot):
    robot = make_robot()

    response = client.post(
        f"/api/events/{event['id']}/matches",
        json={"robot_a": robot["id"], "robot_b": robot["id"], "score_a": 2, "score_b": 0},
    )

    assert response.status_code == 400


def test_line_follower_has_runs_not_matches(client, event, make_robot):
    a, b = make_robot("seguidor_de_linha"), make_robot("seguidor_de_linha")
    sumo = make_robot("sumo_3kg")

    match = client.post(
        f"/api/events/{event['id']}/matches",
        json={"robot_a": a["id"], "robot_b": b["id"], "score_a": 1, "score_b": 0},
    )
    run = client.post(f"/api/events/{event['id']}/runs", json={"robot_id": sumo["id"], "time_ms": 15000})

    assert match.status_code == 422
    assert run.status_code == 422


def test_points_table_with_tiebreak_and_shared_position(client, event, make_robot, play):
    tornado = make_robot(name="Tornado")
    muralha = make_robot(name="Muralha")
    bigorna = make_robot(name="Bigorna")
    rolo = make_robot(name="Rolo")

    play(tornado, bigorna, 2, 0)  # vitória do Tornado
    play(muralha, rolo, 2, 1)  # vitória da Muralha
    play(tornado, muralha, 1, 1)  # empate
    play(bigorna, rolo, 1, 1)  # empate

    table = ranking(client, event, "sumo_3kg")

    # Empatados em pontos, desempata o saldo de rounds
    assert [(r["robot"], r["points"], r["round_diff"], r["position"]) for r in table] == [
        ("Tornado", 4, 2, 1),
        ("Muralha", 4, 1, 2),
        ("Rolo", 1, -1, 3),
        ("Bigorna", 1, -2, 4),
    ]
    assert (table[0]["wins"], table[0]["draws"], table[0]["losses"]) == (1, 1, 0)


def test_exact_tie_shares_position(client, event, make_robot, play):
    a, b = make_robot(name="Alfa"), make_robot(name="Beta")
    play(a, b, 1, 1)

    table = ranking(client, event, "sumo_3kg")

    assert [(r["robot"], r["position"]) for r in table] == [("Alfa", 1), ("Beta", 1)]


def test_line_follower_ranking_uses_best_valid_time(client, event, make_robot):
    cometa = make_robot("seguidor_de_linha", name="Cometa")
    raio = make_robot("seguidor_de_linha", name="Raio")
    for robot, time_ms, valid in [
        (cometa, 18_400, True),
        (cometa, 17_900, True),
        (raio, 16_000, False),  # saiu da pista: não conta
        (raio, 18_100, True),
    ]:
        response = client.post(
            f"/api/events/{event['id']}/runs",
            json={"robot_id": robot["id"], "time_ms": time_ms, "valid": valid},
        )
        assert response.status_code == 201

    table = ranking(client, event, "seguidor_de_linha")

    assert [(r["robot"], r["best_ms"], r["valid_runs"]) for r in table] == [
        ("Cometa", 17_900, 2),
        ("Raio", 18_100, 1),
    ]
    assert table[0]["average_ms"] == 18_150


def test_ranking_requires_valid_category(client, event):
    response = client.get(f"/api/events/{event['id']}/ranking?category=futebol")

    assert response.status_code == 400
    assert "sumo_3kg" in response.get_json()["details"]["allowed"]


def test_event_summary_counts_records_per_category(client, event, make_robot, play):
    a, b = make_robot(), make_robot()
    play(a, b, 2, 0)
    play(b, a, 2, 1)

    summary = client.get(f"/api/events/{event['id']}").get_json()

    assert summary["categories"]["sumo_3kg"]["records"] == 2
    assert summary["start_date"] == "2026-11-14"


def test_matches_list_includes_robot_names(client, event, make_robot, play):
    a, b = make_robot(name="Alfa"), make_robot(name="Beta")
    play(a, b, 2, 0)

    matches = client.get(f"/api/events/{event['id']}/matches").get_json()

    assert (matches[0]["robot_a_name"], matches[0]["robot_b_name"]) == ("Alfa", "Beta")


def test_seed_command_loads_sample_competition(app):
    result = app.test_cli_runner().invoke(args=["seed"])

    assert "Competicao de exemplo criada" in result.output
    assert app.extensions["mongo_db"].robots.count_documents({}) == 10
