"""Tests pour le moteur ELO pairwise."""
from src.arena.elo import compute_k, expected_score, pairwise_updates


def test_expected_score_equal():
    """Deux joueurs a 1500 → probabilite 0.5 chacun."""
    assert expected_score(1500, 1500) == 0.5


def test_expected_score_stronger():
    """Joueur 1700 vs 1300 → ~0.91 pour le plus fort."""
    score = expected_score(1700, 1300)
    assert 0.90 < score < 0.92


def test_pairwise_2_players():
    """Le gagnant recoit un delta positif, le perdant negatif."""
    rankings = [("a", 10), ("b", 50)]  # a gagne (score bas)
    ratings = {"a": 1500.0, "b": 1500.0}
    games = {"a": 0, "b": 0}

    deltas = pairwise_updates(rankings, ratings, games)
    assert deltas["a"] > 0
    assert deltas["b"] < 0
    assert abs(deltas["a"] + deltas["b"]) < 0.01  # somme ~0


def test_pairwise_4_players():
    """4 joueurs → 6 comparaisons, somme des deltas ~0."""
    rankings = [("a", 10), ("b", 20), ("c", 30), ("d", 40)]
    ratings = {p: 1500.0 for p in "abcd"}
    games = {p: 0 for p in "abcd"}

    deltas = pairwise_updates(rankings, ratings, games)

    # 6 paires attendues (C(4,2))
    assert len(deltas) == 4
    assert abs(sum(deltas.values())) < 0.01

    # Le premier devrait gagner le plus, le dernier perdre le plus
    assert deltas["a"] > deltas["b"] > deltas["c"] > deltas["d"]


def test_k_factor_decay():
    """K=32 pour les nouveaux, K=16 apres 30 parties."""
    assert compute_k(0) == 32.0
    assert compute_k(29) == 32.0
    assert compute_k(30) == 16.0
    assert compute_k(100) == 16.0
