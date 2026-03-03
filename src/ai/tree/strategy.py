"""TreeAIStrategy : joue en utilisant des modeles GBT entraines."""

import os
import random
from typing import Dict, List, Optional, Tuple

from ..strategy import PlayerStrategy
from ...models.card import Card
from ..context import GameContext
from .features import build_feature_vector


class TreeAIStrategy(PlayerStrategy):
    """Strategie basee sur des arbres gradient-boostes.

    Charge 4 modeles (draw, keep, position, reveal) depuis un dossier
    et predit le round_score pour chaque action possible, en choisissant
    celle qui minimise le score predit.
    """

    def __init__(self, model_dir: str):
        self.model_dir = model_dir
        self.models = self._load_models(model_dir)

    def _load_models(self, model_dir: str) -> Dict[str, object]:
        """Charge les 4 modeles joblib."""
        import joblib

        models = {}
        for dtype in ("draw", "keep", "position", "reveal"):
            path = os.path.join(model_dir, f"{dtype}_model.joblib")
            if os.path.exists(path):
                models[dtype] = joblib.load(path)
        return models

    def _predict(self, dtype: str, features: List[float]) -> float:
        """Predit le round_score pour un vecteur de features."""
        model = self.models.get(dtype)
        if model is None:
            return 0.0
        return float(model.predict([features])[0])

    # ── Decisions ────────────────────────────────────────

    def choose_initial_cards(
        self, board: List[List[Card]], ctx=None,
    ) -> List[Tuple[int, int]]:
        """Choix aveugle : random (cartes cachees, aucun signal)."""
        hidden = [
            (r, c)
            for r in range(len(board))
            for c in range(len(board[0]))
            if board[r][c] is not None and not board[r][c].visible
        ]
        return random.sample(hidden, min(2, len(hidden)))

    def choose_draw_or_discard(
        self, visible_card: Card, board: List[List[Card]], ctx=None,
    ) -> str:
        """Predit le score pour D vs P, choisit le plus bas."""
        feat_d = build_feature_vector(
            "draw", board, ctx, card=visible_card, action=0.0,
        )
        feat_p = build_feature_vector(
            "draw", board, ctx, card=visible_card, action=1.0,
        )
        score_d = self._predict("draw", feat_d)
        score_p = self._predict("draw", feat_p)
        return "D" if score_d <= score_p else "P"

    def choose_keep_or_discard(
        self, drawn_card: Card, board: List[List[Card]], ctx=None,
    ) -> str:
        """Predit le score pour G vs D, choisit le plus bas."""
        feat_g = build_feature_vector(
            "keep", board, ctx, card=drawn_card, action=0.0,
        )
        feat_d = build_feature_vector(
            "keep", board, ctx, card=drawn_card, action=1.0,
        )
        score_g = self._predict("keep", feat_g)
        score_d = self._predict("keep", feat_d)
        return "G" if score_g <= score_d else "D"

    def choose_card_position(
        self, card: Card, board: List[List[Card]], ctx=None,
    ) -> Tuple[int, int]:
        """Evalue chaque position, choisit celle avec le score predit le plus bas."""
        best_score = float("inf")
        best_positions: List[Tuple[int, int]] = []

        for r in range(len(board)):
            for c in range(len(board[0])):
                if board[r][c] is None:
                    continue
                features = build_feature_vector(
                    "position", board, ctx, card=card, row=r, col=c,
                )
                score = self._predict("position", features)
                if score < best_score:
                    best_score = score
                    best_positions = [(r, c)]
                elif score == best_score:
                    best_positions.append((r, c))

        return random.choice(best_positions)

    def choose_card_to_reveal(
        self, board: List[List[Card]], ctx=None,
    ) -> Tuple[int, int]:
        """Evalue chaque position cachee, choisit celle avec le score predit le plus bas."""
        hidden = [
            (r, c)
            for r in range(len(board))
            for c in range(len(board[0]))
            if board[r][c] is not None and not board[r][c].visible
        ]

        if not hidden:
            # Fallback improbable
            return (0, 0)

        best_score = float("inf")
        best_positions: List[Tuple[int, int]] = []

        for r, c in hidden:
            features = build_feature_vector(
                "reveal", board, ctx, row=r, col=c,
            )
            score = self._predict("reveal", features)
            if score < best_score:
                best_score = score
                best_positions = [(r, c)]
            elif score == best_score:
                best_positions.append((r, c))

        return random.choice(best_positions)
