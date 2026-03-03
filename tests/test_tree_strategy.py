"""Tests pour src/ai/tree/strategy.py et integration collector."""

import os
import tempfile

from src.models.card import Card
from src.ai.tree.collector import CollectorStrategy, collect_data
from src.ai.tree.features import feature_names


def _make_board(values, visible_mask):
    """Cree un board 3x4 a partir de listes plates."""
    board = []
    idx = 0
    for r in range(3):
        row = []
        for c in range(4):
            if values[idx] is None:
                row.append(None)
            else:
                card = Card(values[idx])
                card.visible = visible_mask[idx]
                row.append(card)
            idx += 1
        board.append(row)
    return board


# ── CollectorStrategy ────────────────────────────────────

def test_collector_records_decisions():
    """Le collector enregistre des records pour chaque decision."""
    coll = CollectorStrategy()
    board = _make_board([5] * 12, [True, True] + [False] * 10)

    # Simuler des decisions
    card = Card(3)
    card.visible = True
    coll.choose_draw_or_discard(card, board)

    # draw enregistre 2 records (choisi + contrefactuel)
    draw_records = [r for r in coll.records if r["type"] == "draw"]
    assert len(draw_records) == 2
    assert any(r["chosen"] for r in draw_records)
    assert any(not r["chosen"] for r in draw_records)


def test_collector_labels_round_score():
    """label_records() rempli le round_score."""
    coll = CollectorStrategy()
    board = _make_board([5] * 12, [True, True] + [False] * 10)

    card = Card(3)
    card.visible = True
    coll.choose_draw_or_discard(card, board)

    assert all(r["round_score"] is None for r in coll.records)
    coll.label_records(42)
    assert all(r["round_score"] == 42 for r in coll.records)


def test_collect_data_produces_records():
    """collect_data() produit des records pour les 4 types de decision."""
    records = collect_data(num_games=10, players_per_game=2, progress_every=0)

    assert "draw" in records
    assert "keep" in records
    assert "position" in records
    assert "reveal" in records

    # Au minimum des decisions draw (chaque joueur decide au moins une fois)
    assert len(records["draw"]) > 0

    # Verifier la structure d'un record
    for dtype in ("draw", "keep", "position", "reveal"):
        if records[dtype]:
            rec = records[dtype][0]
            assert "features" in rec
            assert "round_score" in rec
            assert rec["round_score"] is not None
            expected_len = len(feature_names(dtype))
            assert len(rec["features"]) == expected_len, (
                f"{dtype}: expected {expected_len} features, got {len(rec['features'])}"
            )


# ── TreeAIStrategy (avec modeles mock) ───────────────────

def test_tree_strategy_with_trained_models():
    """TreeAIStrategy joue une partie complete apres entrainement rapide."""
    # Ce test necessite sklearn — skip si absent
    try:
        from sklearn.ensemble import HistGradientBoostingRegressor
        import joblib
    except ImportError:
        return

    from src.ai.tree.strategy import TreeAIStrategy
    from src.game.skyjo import SkyjoGame

    # Entrainer des mini-modeles sur des donnees minimales
    records = collect_data(num_games=50, players_per_game=2, progress_every=0)

    with tempfile.TemporaryDirectory() as tmpdir:
        for dtype in ("draw", "keep", "position", "reveal"):
            recs = records[dtype]
            if len(recs) < 10:
                continue
            X = [r["features"] for r in recs]
            y = [float(r["round_score"]) for r in recs]
            model = HistGradientBoostingRegressor(
                max_iter=10, max_depth=3, random_state=42,
            )
            model.fit(X, y)
            joblib.dump(model, os.path.join(tmpdir, f"{dtype}_model.joblib"))

        # Jouer une partie avec TreeAIStrategy
        strategy = TreeAIStrategy(tmpdir)
        names = ["TreeAI", "RandomAI"]
        from src.ai.genetic import GeneticAIStrategy
        game = SkyjoGame(
            names, silent=True,
            strategies=[strategy, GeneticAIStrategy()],
        )
        rankings = game.play_full_game()

        # La partie se termine sans erreur
        assert len(rankings) == 2
        assert all(isinstance(name, str) for name, _ in rankings)
        assert all(isinstance(score, int) for _, score in rankings)
