from typing import List, Tuple
from ..models.player import Player
from ..models.card import Card

def display_board(player: Player):
    """Affiche le plateau d'un joueur avec les coordonnées."""
    print(f"\nPlateau de {player.name}:")
    print("    1   2   3   4")  # En-têtes des colonnes
    for i, row in enumerate(player.board):
        print(f"{chr(65+i)}", end=" ")  # A, B ou C
        for card in row:
            if card is None:
                print("[---]", end=" ")
            else:
                print(f"[{str(card)}]", end=" ")
        print()

def display_game_state(deck_size: int, top_discard: Card, players: List[Player], current_player: Player):
    """Affiche l'état actuel du jeu"""
    print(f"\nCartes restantes dans le deck: {deck_size}")
    print(f"Carte visible de la défausse: {top_discard.value if top_discard else 'Aucune'}")
    
    for player in players:
        print(f"\nScore actuel de {player.name}: {player.calculate_current_score()}")
        if player == current_player:
            display_board(player)

def convert_coordinates(coord_str: str) -> Tuple[int, int]:
    """Convertit les coordonnées style 'A1' en indices (row, col)."""
    if len(coord_str) != 2:
        raise ValueError("Format invalide. Utilisez par exemple 'A1', 'B2', etc.")
    
    row = ord(coord_str[0].upper()) - ord('A')
    if not 0 <= row <= 2:
        raise ValueError("Ligne invalide. Utilisez A, B ou C.")
    
    try:
        col = int(coord_str[1]) - 1
        if not 0 <= col <= 3:
            raise ValueError()
    except ValueError:
        raise ValueError("Colonne invalide. Utilisez 1, 2, 3 ou 4.")
    
    return row, col