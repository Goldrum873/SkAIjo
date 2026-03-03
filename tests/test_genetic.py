from src.models.card import Card
from src.ai.genes import AIGenes
from src.ai.genetic import GeneticAIStrategy


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


def test_count_column_matches():
    """Compte correct des cartes visibles matchant dans une colonne."""
    ai = GeneticAIStrategy()
    board = _make_board_3x4(
        [5, 1, 2, 3,
         5, 4, 5, 6,
         5, 7, 8, 9],
        [True, True, True, True,
         True, True, True, True,
         False, True, True, True],
    )
    # Colonne 0 : deux 5 visibles (row 0 et 1), row 2 cachee
    assert ai._count_column_matches(board, 0, 5) == 2
    # Colonne 1 : aucun match pour 5
    assert ai._count_column_matches(board, 1, 5) == 0


def test_score_position_prefers_high_replace():
    """Remplacer une carte haute score mieux qu'une carte basse."""
    genes = AIGenes(
        discard_threshold=4, keep_threshold=4,
        value_weight=1.0, hidden_weight=0.0,
        column_weight=0.0, column_completion=0.0,
        low_card_bonus=0.0, high_card_panic=0.0,
        swap_reluctance=0.0, risk_tolerance=0.0,
        endgame_aggression=0.0, doubling_caution=0.0,
        opponent_awareness=0.0, score_pressure=0.0, deck_urgency=0.0,
    )
    ai = GeneticAIStrategy(genes)

    board = _make_board_3x4(
        [12, 1, 0, 0,
         0, 0, 0, 0,
         0, 0, 0, 0],
        [True] * 12,
    )

    new_card = Card(3)
    new_card.visible = True

    score_high = ai._score_position(new_card, board, 0, 0)  # replace 12
    score_low = ai._score_position(new_card, board, 0, 1)   # replace 1
    assert score_high > score_low


def test_choose_draw_or_discard_low_card():
    """Carte basse en defausse → prendre la defausse ('D')."""
    genes = AIGenes(
        discard_threshold=4, keep_threshold=4,
        value_weight=1.0, hidden_weight=0.0,
        column_weight=0.0, column_completion=0.0,
        low_card_bonus=1.0, high_card_panic=0.0,
        swap_reluctance=0.0, risk_tolerance=0.0,
        endgame_aggression=0.0, doubling_caution=0.0,
        opponent_awareness=0.0, score_pressure=0.0, deck_urgency=0.0,
    )
    ai = GeneticAIStrategy(genes)

    board = _make_board_3x4(
        [5, 6, 7, 8, 9, 10, 11, 12, 3, 4, 5, 6],
        [True] * 12,
    )

    low_card = Card(0)
    low_card.visible = True
    assert ai.choose_draw_or_discard(low_card, board) == 'D'
