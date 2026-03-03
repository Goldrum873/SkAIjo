"""Execution des matchs d'arena entre agents."""
import glob
import json
import os
import random
from typing import Dict, List, Tuple

from ..ai.trainer import GeneticTrainer
from ..ai.tree.strategy import TreeAIStrategy
from ..ai.tree.training import load_agent_metadata as load_tree_metadata
from ..game.skyjo import SkyjoGame
from .elo import pairwise_updates
from .leaderboard import (
    ensure_agent,
    get_table_stats,
    load_leaderboard,
    record_elo_snapshot,
    save_leaderboard,
    update_after_match,
)


def load_agents_from_dir(agent_dir: str) -> List[dict]:
    """Scan agents genetiques (*.json) et tree (*/metadata.json)."""
    agents = []

    # Agents genetiques : agents/*.json
    pattern = os.path.join(agent_dir, "*.json")
    for filepath in sorted(glob.glob(pattern)):
        # Ignorer leaderboard.json et autres fichiers non-agents
        basename = os.path.basename(filepath)
        if basename in ("leaderboard.json",):
            continue
        try:
            meta = GeneticTrainer.load_agent_metadata(filepath)
            meta.setdefault("type", "genetic")
            agents.append(meta)
        except (json.JSONDecodeError, KeyError):
            continue

    # Agents tree : agents/*/metadata.json
    tree_pattern = os.path.join(agent_dir, "*", "metadata.json")
    for filepath in sorted(glob.glob(tree_pattern)):
        try:
            agent_dir_path = os.path.dirname(filepath)
            meta = load_tree_metadata(agent_dir_path)
            agents.append(meta)
        except (json.JSONDecodeError, KeyError):
            continue

    return agents


def _load_strategy(meta: dict):
    """Charge la strategie selon le type d'agent."""
    if meta.get("type") == "tree":
        return TreeAIStrategy(meta["filepath"])
    return GeneticTrainer.load_ai(meta["filepath"])


def run_match(
    agent_metas: List[dict],
    table_size: int,
) -> List[Tuple[str, int]]:
    """Charge les strategies, joue un match, retourne le classement."""
    strategies = []
    names = []
    for meta in agent_metas:
        ai = _load_strategy(meta)
        strategies.append(ai)
        names.append(meta["agent_id"])

    game = SkyjoGame(names, silent=True, strategies=strategies)
    return game.play_full_game()


def run_simulation(
    agent_metas: List[dict],
    table_size: int,
    num_games: int,
    leaderboard_path: str,
    history_path: str = "elo_history.csv",
) -> dict:
    """Lance num_games matchs aleatoires et met a jour le leaderboard."""
    data = load_leaderboard(leaderboard_path)

    # Enregistrer tous les agents
    for meta in agent_metas:
        ensure_agent(data, meta["agent_id"], meta["filepath"], meta["training_config"])

    if len(agent_metas) < table_size:
        raise ValueError(
            f"Pas assez d'agents ({len(agent_metas)}) "
            f"pour des tables de {table_size}"
        )

    for i in range(1, num_games + 1):
        selected = random.sample(agent_metas, table_size)
        rankings = run_match(selected, table_size)

        # Construire ratings/games_count pour le calcul ELO
        agent_ids = [agent_id for agent_id, _ in rankings]

        ratings_global: Dict[str, float] = {
            aid: data["agents"][aid]["global_elo"] for aid in agent_ids
        }
        games_global: Dict[str, int] = {
            aid: data["agents"][aid]["global_games"] for aid in agent_ids
        }
        deltas_global = pairwise_updates(rankings, ratings_global, games_global)

        ratings_table: Dict[str, float] = {
            aid: get_table_stats(data["agents"][aid], table_size)["elo"]
            for aid in agent_ids
        }
        games_table: Dict[str, int] = {
            aid: get_table_stats(data["agents"][aid], table_size)["games"]
            for aid in agent_ids
        }
        deltas_table = pairwise_updates(rankings, ratings_table, games_table)

        update_after_match(data, rankings, table_size, deltas_global, deltas_table)

        if i % 50 == 0 or i == num_games:
            save_leaderboard(data, leaderboard_path)
            record_elo_snapshot(data, history_path, table_size)
            print(f"Partie {i}/{num_games}...")

    return data
