from robotica.stats import assign_positions


def row(name, points, diff, wins):
    return {"robot": name, "points": points, "round_diff": diff, "wins": wins}


def test_positions_follow_order_when_there_is_no_tie():
    rows = [row("A", 6, 3, 2), row("B", 4, 1, 1), row("C", 0, -4, 0)]

    assert [r["position"] for r in assign_positions(rows)] == [1, 2, 3]


def test_full_tie_shares_position_and_skips_the_next():
    rows = [row("A", 4, 2, 1), row("B", 4, 2, 1), row("C", 1, -4, 0)]

    assert [r["position"] for r in assign_positions(rows)] == [1, 1, 3]


def test_partial_tie_is_broken_by_next_criterion():
    rows = [row("A", 4, 2, 1), row("B", 4, 1, 1)]

    assert [r["position"] for r in assign_positions(rows)] == [1, 2]


def test_position_is_the_first_field():
    ranked = assign_positions([row("A", 3, 1, 1)])

    assert next(iter(ranked[0])) == "position"
