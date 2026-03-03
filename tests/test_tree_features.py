"""Tests pour src/ai/tree/features.py"""

from src.models.card import Card
from src.ai.tree.features import build_feature_vector, feature_names


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


# ── Longueur du vecteur ─────────────────────────────────

def test_vector_length_draw():
    """Le vecteur draw a la bonne longueur."""
    board = _make_board([5] * 12, [True] * 12)
    card = Card(3)
    vec = build_feature_vector("draw", board, ctx=None, card=card, action=0.0)
    names = feature_names("draw")
    assert len(vec) == len(names)


def test_vector_length_keep():
    board = _make_board([5] * 12, [True] * 12)
    card = Card(3)
    vec = build_feature_vector("keep", board, ctx=None, card=card, action=1.0)
    names = feature_names("keep")
    assert len(vec) == len(names)


def test_vector_length_position():
    board = _make_board([5] * 12, [True] * 12)
    card = Card(3)
    vec = build_feature_vector("position", board, ctx=None, card=card, row=1, col=2)
    names = feature_names("position")
    assert len(vec) == len(names)


def test_vector_length_reveal():
    board = _make_board([5] * 12, [False] * 12)
    vec = build_feature_vector("reveal", board, ctx=None, row=0, col=0)
    names = feature_names("reveal")
    assert len(vec) == len(names)


# ── Board features ──────────────────────────────────────

def test_all_visible_board():
    """Board tout visible : hidden_count=0, visible_count=12."""
    board = _make_board(
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        [True] * 12,
    )
    card = Card(0)
    vec = build_feature_vector("draw", board, ctx=None, card=card, action=0.0)
    names = feature_names("draw")

    idx_hidden = names.index("my_hidden_count")
    idx_visible = names.index("my_visible_count")
    idx_score = names.index("my_visible_score")

    assert vec[idx_hidden] == 0.0
    assert vec[idx_visible] == 12.0
    assert vec[idx_score] == sum(range(1, 13))


def test_hidden_cards():
    """Board avec 6 cachees : hidden_count=6, visible_count=6."""
    board = _make_board(
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        [True, True, True, True, True, True,
         False, False, False, False, False, False],
    )
    card = Card(0)
    vec = build_feature_vector("draw", board, ctx=None, card=card, action=0.0)
    names = feature_names("draw")

    assert vec[names.index("my_hidden_count")] == 6.0
    assert vec[names.index("my_visible_count")] == 6.0


def test_cleared_columns():
    """Colonnes clearees (None) gerees correctement."""
    # Colonne 0 entierement None
    values = [None, 5, 6, 7, None, 8, 9, 10, None, 11, 12, 1]
    vis = [False, True, True, True, False, True, True, True, False, True, True, True]
    board = _make_board(values, vis)

    card = Card(3)
    vec = build_feature_vector("draw", board, ctx=None, card=card, action=0.0)
    names = feature_names("draw")

    assert vec[names.index("cleared_columns")] == 1.0


def test_ctx_none_zeros():
    """ctx=None → tous les features contextuels a 0."""
    board = _make_board([5] * 12, [True] * 12)
    card = Card(3)

    vec = build_feature_vector("draw", board, ctx=None, card=card, action=0.0)
    names = feature_names("draw")

    ctx_names = [
        "deck_size", "discard_pile_size", "turn_number",
        "my_total_score", "round_number", "is_last_round",
        "num_opponents", "min_opp_visible_score", "min_opp_hidden_count",
        "score_gap",
    ]
    for name in ctx_names:
        assert vec[names.index(name)] == 0.0, f"{name} should be 0.0 when ctx=None"


# ── Decision features ───────────────────────────────────

def test_column_pair_detection():
    """Colonne avec paire detectee dans les features."""
    board = _make_board(
        [5, 1, 2, 3,
         5, 4, 6, 7,
         8, 9, 10, 11],
        [True] * 12,
    )
    card = Card(0)
    vec = build_feature_vector("draw", board, ctx=None, card=card, action=0.0)
    names = feature_names("draw")

    # Colonne 0 a une paire de 5
    assert vec[names.index("col_0_has_pair")] == 1.0
    assert vec[names.index("col_0_pair_value")] == 5.0
    assert vec[names.index("potential_clears")] >= 1.0


def test_invalid_decision_type():
    """Type de decision invalide → ValueError."""
    board = _make_board([5] * 12, [True] * 12)
    try:
        build_feature_vector("invalid", board)
        assert False, "Should have raised ValueError"
    except ValueError:
        pass
