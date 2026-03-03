from abc import ABC, abstractmethod
from typing import List, Optional, Tuple
from ..models.card import Card


class PlayerStrategy(ABC):
    @abstractmethod
    def choose_initial_cards(self, board: List[List[Card]], ctx=None) -> List[Tuple[int, int]]:
        """Choisit les deux cartes a reveler au debut."""
        pass

    @abstractmethod
    def choose_draw_or_discard(self, visible_card: Card, board: List[List[Card]], ctx=None) -> str:
        """Decide de piocher (P) ou prendre la defausse (D)."""
        pass

    @abstractmethod
    def choose_keep_or_discard(self, drawn_card: Card, board: List[List[Card]], ctx=None) -> str:
        """Decide de garder (G) ou defausser (D) la carte piochee."""
        pass

    @abstractmethod
    def choose_card_position(self, card: Card, board: List[List[Card]], ctx=None) -> Tuple[int, int]:
        """Choisit ou placer la carte."""
        pass

    @abstractmethod
    def choose_card_to_reveal(self, board: List[List[Card]], ctx=None) -> Tuple[int, int]:
        """Choisit quelle carte reveler quand necessaire."""
        pass
