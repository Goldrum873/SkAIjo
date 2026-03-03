"""Tests pour les fonctionnalites contextuelles (GameContext + 5 genes v3)."""

import pytest
from src.models.card import Card
from src.ai.genes import AIGenes
from src.ai.genetic import GeneticAIStrategy
from src.ai.context import GameContext, OpponentInfo


def _make_board_3x4(values, visible_mask):
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


def _make_board_tuples(values, visible_mask):
    """Cree un board en tuples (pour OpponentInfo)."""
    board = _make_board_3x4(values, visible_mask)
    return tuple(tuple(row) for row in board)


def _base_genes(**overrides):
    """Genes neutres (contextuels a 0) avec overrides."""
    defaults = dict(
        discard_threshold=4, keep_threshold=4,
        value_weight=1.0, hidden_weight=0.0,
        column_weight=0.0, column_completion=0.0,
        low_card_bonus=0.0, high_card_panic=0.0,
        swap_reluctance=0.0, risk_tolerance=0.0,
        endgame_aggression=0.0, doubling_caution=0.0,
        opponent_awareness=0.0, score_pressure=0.0,
        deck_urgency=0.0,
    )
    defaults.update(overrides)
    return AIGenes(**defaults)


def _minimal_ctx(**overrides):
    """GameContext minimal avec overrides."""
    opp_board = _make_board_tuples(
        [5] * 12, [True] * 12,
    )
    defaults = dict(
        deck_size=50,
        discard_pile_size=10,
        turn_number=5,
        my_total_score=0,
        round_number=1,
        opponents=(OpponentInfo(
            name="Opp1", visible_score=30, hidden_count=4,
            board=opp_board, total_score=0,
        ),),
        is_last_round=False,
        finisher_name=None,
        min_opponent_visible_score=30,
        min_opponent_hidden_count=4,
        my_visible_score=20,
        my_hidden_count=4,
    )
    defaults.update(overrides)
    return GameContext(**defaults)


# -- Test: frozen --

def test_game_context_frozen():
    """GameContext est immutable."""
    ctx = _minimal_ctx()
    with pytest.raises(AttributeError):
        ctx.deck_size = 99


# -- Test: endgame aggression --

def test_endgame_aggression_shifts_threshold():
    """Seuil augmente quand adversaire a 1 carte cachee + endgame_aggression positif."""
    genes = _base_genes(endgame_aggression=2.0, discard_threshold=4.0)
    ai = GeneticAIStrategy(genes)

    board = _make_board_3x4(
        [5, 6, 7, 8, 9, 10, 11, 12, 3, 4, 5, 6],
        [True] * 12,
    )

    # Sans contexte: carte 5 > seuil 4 → piocher
    card = Card(5)
    card.visible = True
    assert ai.choose_draw_or_discard(card, board) == 'P'

    # Avec contexte: adversaire a 1 hidden → endgame boost seuil
    ctx = _minimal_ctx(min_opponent_hidden_count=1)
    result = ai.choose_draw_or_discard(card, board, ctx)
    # endgame modifier: 2.0 * (3-1)/3 = +1.33, seuil effectif ~5.33
    assert result == 'D'


# -- Test: doubling caution --

def test_doubling_caution_penalizes_finishing():
    """Position score baisse quand finir = risque doublement."""
    genes = _base_genes(
        doubling_caution=3.0, value_weight=1.0, hidden_weight=1.0,
    )
    ai = GeneticAIStrategy(genes)

    # Board avec 1 seule carte cachee en (1, 1) — placer = finir
    board = _make_board_3x4(
        [5, 6, 7, 8,
         9, 10, 11, 12,
         3, 4, 5, 6],
        [True, True, True, True,
         True, False, True, True,
         True, True, True, True],
    )

    new_card = Card(3)
    new_card.visible = True

    # Score sans contexte (baseline)
    score_no_ctx = ai._score_position(new_card, board, 1, 1)

    # Score avec contexte: mon visible_score > min adversaire → penalite
    ctx = _minimal_ctx(
        my_visible_score=40,
        min_opponent_visible_score=30,
    )
    score_with_ctx = ai._score_position(new_card, board, 1, 1, ctx)

    # La penalite de doublement doit reduire le score
    assert score_with_ctx < score_no_ctx


# -- Test: opponent awareness --

def test_opponent_awareness_penalizes_helpful_discard():
    """Defausser une carte utile au joueur suivant = penalite."""
    genes = _base_genes(opponent_awareness=2.0, value_weight=1.0)
    ai = GeneticAIStrategy(genes)

    # Board du joueur: carte 5 en (0, 0) visible
    board = _make_board_3x4(
        [5, 6, 7, 8,
         9, 10, 11, 12,
         3, 4, 5, 6],
        [True] * 12,
    )

    # Board adversaire: colonne 0 a deux 5 visibles (besoin d'un 3eme)
    opp_board = _make_board_tuples(
        [5, 1, 2, 3,
         5, 4, 5, 6,
         7, 7, 8, 9],
        [True, True, True, True,
         True, True, True, True,
         True, True, True, True],
    )
    ctx = _minimal_ctx(
        opponents=(OpponentInfo(
            name="NextPlayer", visible_score=30, hidden_count=0,
            board=opp_board, total_score=0,
        ),),
    )

    new_card = Card(3)
    new_card.visible = True

    # Placer en (0, 0) defausserait le 5, que l'adversaire veut
    score_aware = ai._score_position(new_card, board, 0, 0, ctx)
    score_no_ctx = ai._score_position(new_card, board, 0, 0)

    assert score_aware < score_no_ctx


# -- Test: reveal prefers column match --

def test_reveal_prefers_column_match():
    """Revelation cible les colonnes avec 2 cartes visibles identiques."""
    genes = _base_genes()
    ai = GeneticAIStrategy(genes)

    # Board: colonne 0 a deux 5 visibles, colonne 3 n'a pas de match
    # Cartes cachees en (2, 0) et (2, 3)
    board = _make_board_3x4(
        [5, 1, 2, 3,
         5, 4, 5, 6,
         7, 7, 8, 9],
        [True, True, True, True,
         True, True, True, True,
         False, True, True, False],
    )

    ctx = _minimal_ctx()

    # Avec contexte, devrait preferer (2, 0) — colonne avec 2 matchs
    choices = set()
    for _ in range(50):
        choices.add(ai.choose_card_to_reveal(board, ctx))

    # (2, 0) doit etre choisi (colonne avec 2 cartes identiques visibles)
    assert (2, 0) in choices
