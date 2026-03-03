"""Moteur ELO pairwise — fonctions pures, zero I/O."""
import itertools
from typing import Dict, List, Tuple


def expected_score(rating_a: float, rating_b: float) -> float:
    """Probabilite de victoire de A contre B (formule ELO standard)."""
    return 1.0 / (1.0 + 10.0 ** ((rating_b - rating_a) / 400.0))


def compute_k(games_played: int) -> float:
    """Facteur K adaptatif : convergence rapide puis stabilite."""
    return 32.0 if games_played < 30 else 16.0


def pairwise_updates(
    rankings: List[Tuple[str, int]],
    ratings: Dict[str, float],
    games_count: Dict[str, int],
) -> Dict[str, float]:
    """Calcule les deltas ELO a partir d'un classement de match.

    rankings : [(agent_id, score)] trie par score croissant
               (score bas = meilleur, format play_full_game)
    ratings  : {agent_id: elo_actuel}
    games_count : {agent_id: nb_parties_jouees}

    Retourne {agent_id: delta_elo} (deltas, pas les ratings finaux).
    """
    deltas: Dict[str, float] = {agent_id: 0.0 for agent_id, _ in rankings}

    for (id_a, score_a), (id_b, score_b) in itertools.combinations(rankings, 2):
        # score bas = gagnant dans Skyjo
        if score_a < score_b:
            actual_a, actual_b = 1.0, 0.0
        elif score_a > score_b:
            actual_a, actual_b = 0.0, 1.0
        else:
            actual_a, actual_b = 0.5, 0.5

        exp_a = expected_score(ratings[id_a], ratings[id_b])
        exp_b = 1.0 - exp_a

        k_a = compute_k(games_count.get(id_a, 0))
        k_b = compute_k(games_count.get(id_b, 0))

        deltas[id_a] += k_a * (actual_a - exp_a)
        deltas[id_b] += k_b * (actual_b - exp_b)

    return deltas
