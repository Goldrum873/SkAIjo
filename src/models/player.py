from typing import List, Optional
from .card import Card
from ..ai.strategy import PlayerStrategy

class Player:
    def __init__(self, name: str, strategy: Optional[PlayerStrategy] = None):
        self.name = name
        self.board: List[List[Card]] = []  # 3 lignes x 4 colonnes
        self.score = 0
        self.strategy = strategy
        self.has_finished = False
    
    def calculate_current_score(self) -> int:
        """Calcule le score actuel du joueur."""
        score = 0
        for row in self.board:
            for card in row:
                if card is not None and card.visible:
                    score += card.value
        return score

    def all_cards_visible(self) -> bool:
        """Vérifie si toutes les cartes non-None sont visibles."""
        return all(card is None or card.visible 
                  for row in self.board 
                  for card in row)