from src.models.card import Card
from src.models.player import Player


def _make_board(values, visible_mask=None):
    """Cree un board 3x4 a partir d'une liste de valeurs."""
    board = []
    idx = 0
    for r in range(3):
        row = []
        for c in range(4):
            if values[idx] is None:
                row.append(None)
            else:
                card = Card(values[idx])
                if visible_mask and visible_mask[idx]:
                    card.visible = True
                row.append(card)
            idx += 1
        board.append(row)
    return board


def test_calculate_current_score():
    """Somme uniquement les cartes visibles."""
    player = Player("Test")
    # 12 valeurs, seules les 4 premieres visibles
    player.board = _make_board(
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        [True, True, True, True, False, False,
         False, False, False, False, False, False],
    )
    assert player.calculate_current_score() == 10  # 1+2+3+4


def test_calculate_current_score_with_none():
    """Ignore les cases None (colonnes completees)."""
    player = Player("Test")
    player.board = _make_board(
        [None, 2, 3, 4, None, 6, 7, 8, None, 10, 11, 12],
        [False, True, False, False, False, True, False, False,
         False, True, False, False],
    )
    assert player.calculate_current_score() == 18  # 2+6+10


def test_all_cards_visible():
    player = Player("Test")
    # Toutes visibles
    player.board = _make_board(
        [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
        [True] * 12,
    )
    assert player.all_cards_visible() is True

    # Une cachee
    player.board[1][2].visible = False
    assert player.all_cards_visible() is False

    # None sont ignorees (comptent comme "visibles")
    player.board = _make_board(
        [None, 2, 3, 4, None, 6, 7, 8, None, 10, 11, 12],
        [False, True, True, True, False, True, True, True,
         False, True, True, True],
    )
    assert player.all_cards_visible() is True
