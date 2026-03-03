"""Contexte de jeu passe aux strategies IA pour decisions contextuelles."""

from dataclasses import dataclass
from typing import Optional, Tuple
from ..models.card import Card


@dataclass(frozen=True)
class OpponentInfo:
    """Informations visibles sur un adversaire (lecture seule)."""
    name: str
    visible_score: int
    hidden_count: int
    board: Tuple[Tuple[Optional[Card], ...], ...]
    total_score: int


@dataclass(frozen=True)
class GameContext:
    """Snapshot du jeu au moment d'une decision IA."""
    deck_size: int
    discard_pile_size: int
    turn_number: int
    my_total_score: int
    round_number: int
    opponents: Tuple[OpponentInfo, ...]
    is_last_round: bool
    finisher_name: Optional[str]
    # Pre-calcules pour simplifier les strategies
    min_opponent_visible_score: int
    min_opponent_hidden_count: int
    my_visible_score: int
    my_hidden_count: int
