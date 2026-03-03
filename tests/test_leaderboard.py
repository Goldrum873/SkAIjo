"""Tests pour la persistence du leaderboard."""
import csv
import os

from src.arena.leaderboard import (
    ensure_agent,
    load_leaderboard,
    record_elo_snapshot,
    save_leaderboard,
)


def test_load_empty(tmp_path):
    """Fichier absent → structure vide avec agents={} et total_matches=0."""
    data = load_leaderboard(str(tmp_path / "nonexistent.json"))
    assert data == {"agents": {}, "total_matches": 0}


def test_save_load_roundtrip(tmp_path):
    """Persistence correcte : save puis load retourne les memes donnees."""
    path = str(tmp_path / "lb.json")
    original = {
        "agents": {
            "test-agent": {
                "filepath": "agents/test.json",
                "training_config": {"players_per_game": 4},
                "global_elo": 1550.0,
                "global_games": 10,
                "per_table_size": {},
            }
        },
        "total_matches": 10,
    }
    save_leaderboard(original, path)
    loaded = load_leaderboard(path)
    assert loaded == original


def test_ensure_agent_idempotent():
    """Double ajout du meme agent ne duplique pas et ne modifie pas."""
    data = {"agents": {}, "total_matches": 0}
    ensure_agent(data, "agent-1", "agents/a1.json", {"players_per_game": 8})
    initial_elo = data["agents"]["agent-1"]["global_elo"]

    # Deuxieme appel avec des valeurs differentes
    ensure_agent(data, "agent-1", "agents/other.json", {"players_per_game": 2})

    assert len(data["agents"]) == 1
    assert data["agents"]["agent-1"]["filepath"] == "agents/a1.json"
    assert data["agents"]["agent-1"]["global_elo"] == initial_elo


def test_record_elo_snapshot(tmp_path):
    """Les snapshots s'ajoutent au CSV avec header + une ligne par agent."""
    path = str(tmp_path / "history.csv")
    data = {
        "agents": {
            "agent-a": {
                "global_elo": 1520.0,
                "per_table_size": {"4": {"elo": 1530.0, "games": 5, "wins": 2}},
            },
            "agent-b": {
                "global_elo": 1480.0,
                "per_table_size": {},
            },
        },
        "total_matches": 50,
    }

    record_elo_snapshot(data, path, table_size=4)

    with open(path) as f:
        rows = list(csv.reader(f))

    # Header + 2 agents
    assert rows[0] == ["match", "agent_id", "global_elo", "table_size", "table_elo"]
    assert len(rows) == 3
    assert rows[1][1] == "agent-a"
    assert rows[1][2] == "1520.0"
    assert rows[1][4] == "1530.0"
    # agent-b n'a pas de stats table 4 → table_elo vide
    assert rows[2][1] == "agent-b"
    assert rows[2][4] == ""

    # Deuxieme snapshot → s'ajoute sans re-ecrire le header
    data["total_matches"] = 100
    record_elo_snapshot(data, path, table_size=4)

    with open(path) as f:
        rows = list(csv.reader(f))

    assert len(rows) == 5  # header + 2 + 2
    assert rows[3][0] == "100"
