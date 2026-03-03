"""Tests des regles du jeu Skyjo — coeur du projet."""
from src.models.card import Card
from src.models.player import Player
from src.ai.genetic import GeneticAIStrategy
from src.game.skyjo import SkyjoGame


def _make_game(nb_players=2):
    """Cree une partie silent avec des IA pour pouvoir manipuler l'etat."""
    strategies = [GeneticAIStrategy() for _ in range(nb_players)]
    names = [f"P{i}" for i in range(nb_players)]
    return SkyjoGame(names, silent=True, strategies=strategies)


def _set_board(player, values, visible_mask=None):
    """Remplace le board d'un joueur (3x4)."""
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
    player.board = board


# ── Deck ──────────────────────────────────────────────

def test_deck_composition():
    """150 cartes avec la bonne distribution."""
    game = _make_game()
    # Reconstituer un deck frais (le constructeur distribue les cartes)
    game.deck = []
    game.create_deck()

    assert len(game.deck) == 150

    from collections import Counter
    counts = Counter(c.value for c in game.deck)

    assert counts[-2] == 5
    assert counts[-1] == 10
    assert counts[0] == 15
    for v in range(1, 13):
        assert counts[v] == 10, f"carte {v}: attendu 10, eu {counts[v]}"


# ── Distribution initiale ─────────────────────────────

def test_deal_initial_cards():
    """12 cartes par joueur, 3 lignes x 4 colonnes, toutes cachees."""
    game = _make_game()
    # Reinitialiser: remettre toutes les cartes dans le deck
    game.deck = []
    game.create_deck()
    import random
    random.shuffle(game.deck)

    game.deal_initial_cards()

    for player in game.players:
        assert len(player.board) == 3
        for row in player.board:
            assert len(row) == 4
            for card in row:
                assert card is not None
                assert card.visible is False


# ── Premier joueur ────────────────────────────────────

def test_determine_first_player():
    """Le joueur avec la plus haute somme visible commence."""
    game = _make_game(3)

    # P0 : somme visible = 2
    _set_board(game.players[0],
               [1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
               [True, True, False, False, False, False,
                False, False, False, False, False, False])

    # P1 : somme visible = 20
    _set_board(game.players[1],
               [10, 10, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
               [True, True, False, False, False, False,
                False, False, False, False, False, False])

    # P2 : somme visible = 5
    _set_board(game.players[2],
               [3, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
               [True, True, False, False, False, False,
                False, False, False, False, False, False])

    game.determine_first_player()
    assert game.current_player_index == 1


# ── Colonnes completes ────────────────────────────────

def test_check_complete_columns_match():
    """3 cartes identiques visibles dans une colonne → remplacees par None."""
    game = _make_game()
    player = game.players[0]

    # Colonne 0 : trois 5 visibles
    _set_board(player,
               [5, 1, 2, 3, 5, 4, 5, 6, 5, 7, 8, 9],
               [True, True, True, True, True, True,
                True, True, True, True, True, True])

    game.check_complete_columns(player)

    # Colonne 0 doit etre None
    for row in range(3):
        assert player.board[row][0] is None
    # Les autres colonnes intactes
    assert player.board[0][1].value == 1


def test_check_complete_columns_no_match():
    """Valeurs differentes → colonne inchangee."""
    game = _make_game()
    player = game.players[0]

    _set_board(player,
               [5, 1, 2, 3, 6, 4, 5, 6, 7, 7, 8, 9],
               [True] * 12)

    game.check_complete_columns(player)

    # Aucune colonne supprimee
    for row in range(3):
        for col in range(4):
            assert player.board[row][col] is not None


def test_check_complete_columns_hidden():
    """Cartes identiques mais une cachee → colonne inchangee."""
    game = _make_game()
    player = game.players[0]

    # Colonne 0 : trois 5, mais board[2][0] (index 8) cachee
    _set_board(player,
               [5, 1, 2, 3, 5, 4, 5, 6, 5, 7, 8, 9],
               [True, True, True, True, True, True,
                True, True, False, True, True, True])

    game.check_complete_columns(player)

    # Colonne 0 intacte car board[2][0] est cachee
    for row in range(3):
        assert player.board[row][0] is not None


# ── Score final ───────────────────────────────────────

def test_calculate_final_score():
    """Revele les cachees et somme tout (ignore les None)."""
    game = _make_game()
    player = game.players[0]

    _set_board(player,
               [1, 2, None, 4, 5, 6, 7, 8, 9, 10, 11, 12],
               [True, False, False, True, False, False,
                True, False, True, False, False, False])

    score = game.calculate_final_score(player)
    # 1+2+4+5+6+7+8+9+10+11+12 = 75 (None ignoree)
    assert score == 75

    # Toutes les cartes doivent maintenant etre visibles
    for row in player.board:
        for card in row:
            if card is not None:
                assert card.visible is True


# ── Doublement ────────────────────────────────────────

def test_doubling_triggered():
    """Finisseur >= min(autres) et > 0 → score double."""
    game = _make_game(3)

    # Simuler les scores de fin de manche
    game.first_to_finish = game.players[0]

    # Mettre des boards avec scores connus (toutes visibles)
    _set_board(game.players[0],
               [5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
               [True] * 12)
    _set_board(game.players[1],
               [3, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
               [True] * 12)
    _set_board(game.players[2],
               [4, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
               [True] * 12)

    game.end_round()

    # P0 score 5, min(autres) = 3, P0 >= 3 et > 0 → double = 10
    assert game.total_scores["P0"] == 10
    assert game.total_scores["P1"] == 3
    assert game.total_scores["P2"] == 4


def test_doubling_not_triggered():
    """Finisseur < min(autres) → pas de doublement."""
    game = _make_game(3)
    game.first_to_finish = game.players[0]

    _set_board(game.players[0],
               [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
               [True] * 12)
    _set_board(game.players[1],
               [5, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
               [True] * 12)
    _set_board(game.players[2],
               [8, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
               [True] * 12)

    game.end_round()

    # P0 score 1, min(autres) = 5, P0 < 5 → pas double
    assert game.total_scores["P0"] == 1


def test_doubling_zero_score():
    """Finisseur a 0 → pas de doublement (regle > 0)."""
    game = _make_game(2)
    game.first_to_finish = game.players[0]

    _set_board(game.players[0],
               [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
               [True] * 12)
    _set_board(game.players[1],
               [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
               [True] * 12)

    game.end_round()

    # P0 score 0, condition exige > 0 → pas double
    assert game.total_scores["P0"] == 0
