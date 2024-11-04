from abc import ABC, abstractmethod
from typing import List, Tuple
from ..models.card import Card

class PlayerStrategy(ABC):
    @abstractmethod
    def choose_initial_cards(self, board: List[List[Card]]) -> List[Tuple[int, int]]:
        """Choisit les deux cartes à révéler au début."""
        pass
    
    @abstractmethod
    def choose_draw_or_discard(self, visible_card: Card, board: List[List[Card]]) -> str:
        """Décide de piocher (P) ou prendre la défausse (D)."""
        pass
    
    @abstractmethod
    def choose_keep_or_discard(self, drawn_card: Card, board: List[List[Card]]) -> str:
        """Décide de garder (G) ou défausser (D) la carte piochée."""
        pass
    
    @abstractmethod
    def choose_card_position(self, card: Card, board: List[List[Card]]) -> Tuple[int, int]:
        """Choisit où placer la carte."""
        pass
    
    @abstractmethod
    def choose_card_to_reveal(self, board: List[List[Card]]) -> Tuple[int, int]:
        """Choisit quelle carte révéler quand nécessaire."""
        pass

