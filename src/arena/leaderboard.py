"""Persistence du leaderboard ELO en JSON + historique CSV."""
import csv
import json
import os
from typing import Dict, List, Tuple

DEFAULT_ELO = 1500.0


def load_leaderboard(path: str) -> dict:
    """Charge le leaderboard depuis un fichier JSON. Structure vide si absent."""
    if not os.path.exists(path):
        return {"agents": {}, "total_matches": 0}
    with open(path) as f:
        return json.load(f)


def save_leaderboard(data: dict, path: str) -> None:
    """Sauvegarde le leaderboard en JSON."""
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def ensure_agent(
    data: dict,
    agent_id: str,
    filepath: str,
    training_config: dict,
) -> None:
    """Ajout idempotent d'un agent dans le leaderboard."""
    if agent_id in data["agents"]:
        return
    data["agents"][agent_id] = {
        "filepath": filepath,
        "training_config": training_config,
        "global_elo": DEFAULT_ELO,
        "global_games": 0,
        "per_table_size": {},
    }


def get_table_stats(agent_data: dict, table_size: int) -> dict:
    """Retourne (et cree si absent) les stats pour une taille de table."""
    key = str(table_size)
    if key not in agent_data["per_table_size"]:
        agent_data["per_table_size"][key] = {
            "elo": DEFAULT_ELO,
            "games": 0,
            "wins": 0,
        }
    return agent_data["per_table_size"][key]


def update_after_match(
    data: dict,
    rankings: List[Tuple[str, int]],
    table_size: int,
    deltas_global: Dict[str, float],
    deltas_table: Dict[str, float],
) -> None:
    """Met a jour le leaderboard apres un match."""
    winner_id = rankings[0][0]

    for agent_id, _ in rankings:
        agent = data["agents"][agent_id]

        # ELO global
        agent["global_elo"] += deltas_global[agent_id]
        agent["global_games"] += 1

        # ELO par taille de table
        table_stats = get_table_stats(agent, table_size)
        table_stats["elo"] += deltas_table[agent_id]
        table_stats["games"] += 1
        if agent_id == winner_id:
            table_stats["wins"] += 1

    data["total_matches"] += 1


def record_elo_snapshot(data: dict, history_path: str, table_size: int) -> None:
    """Ajoute un snapshot ELO au CSV d'historique (format long)."""
    file_exists = os.path.exists(history_path)
    match_num = data["total_matches"]

    with open(history_path, "a", newline="") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["match", "agent_id", "global_elo", "table_size", "table_elo"])

        for agent_id, agent in data["agents"].items():
            table_stats = agent["per_table_size"].get(str(table_size))
            table_elo = table_stats["elo"] if table_stats else None
            writer.writerow([
                match_num,
                agent_id,
                round(agent["global_elo"], 1),
                table_size,
                round(table_elo, 1) if table_elo is not None else "",
            ])


def format_leaderboard(data: dict, table_size: int | None = None) -> str:
    """Affichage tabulaire du classement, trie par ELO decroissant."""
    if not data["agents"]:
        return "Aucun agent enregistre."

    header = f"{'Agent':<30}| {'ELO':>6} | {'Parties':>7} | {'Victoires':>9}"
    separator = "-" * 30 + "|" + "-" * 8 + "|" + "-" * 9 + "|" + "-" * 11

    rows = []
    for agent_id, agent in data["agents"].items():
        if table_size is not None:
            stats = agent["per_table_size"].get(str(table_size))
            if not stats:
                continue
            elo = stats["elo"]
            games = stats["games"]
            wins = stats["wins"]
        else:
            elo = agent["global_elo"]
            games = agent["global_games"]
            wins = sum(
                s["wins"] for s in agent["per_table_size"].values()
            )
        rows.append((agent_id, elo, games, wins))

    rows.sort(key=lambda r: r[1], reverse=True)

    lines = [header, separator]
    for agent_id, elo, games, wins in rows:
        lines.append(
            f"{agent_id:<30}| {elo:>6.0f} | {games:>7} | {wins:>9}"
        )

    return "\n".join(lines)
