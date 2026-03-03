"""Collecte de donnees de jeu pour entrainer les modeles GBT.

CollectorStrategy enregistre chaque decision avec ses features.
collect_data() orchestre le self-play massif.
"""

from typing import Dict, List, Optional
import random

from ..strategy import PlayerStrategy
from ..genetic import GeneticAIStrategy
from ...models.card import Card
from ...game.skyjo import SkyjoGame
from .features import build_feature_vector


class CollectorStrategy(PlayerStrategy):
    """Wrapper qui enregistre chaque decision avec ses features.

    Delegue a `inner` pour les choix, ou joue random si inner=None.
    """

    def __init__(self, inner: Optional[PlayerStrategy] = None):
        self.inner = inner or GeneticAIStrategy()
        self.records: List[dict] = []

    def label_records(self, round_score: int) -> None:
        """Rempli le round_score de tous les records non etiquetes."""
        for rec in self.records:
            if rec["round_score"] is None:
                rec["round_score"] = round_score

    # ── Decisions ────────────────────────────────────────

    def choose_initial_cards(self, board, ctx=None):
        return self.inner.choose_initial_cards(board, ctx)

    def choose_draw_or_discard(self, visible_card, board, ctx=None):
        choice = self.inner.choose_draw_or_discard(visible_card, board, ctx)

        # Enregistrer les deux actions (choisie + contrefactuelle)
        for action_val, action_label in [(0.0, "D"), (1.0, "P")]:
            features = build_feature_vector(
                "draw", board, ctx, card=visible_card, action=action_val,
            )
            self.records.append({
                "type": "draw",
                "features": features,
                "round_score": None,
                "chosen": action_label == choice,
            })

        return choice

    def choose_keep_or_discard(self, drawn_card, board, ctx=None):
        choice = self.inner.choose_keep_or_discard(drawn_card, board, ctx)

        # Enregistrer les deux actions
        for action_val, action_label in [(0.0, "G"), (1.0, "D")]:
            features = build_feature_vector(
                "keep", board, ctx, card=drawn_card, action=action_val,
            )
            self.records.append({
                "type": "keep",
                "features": features,
                "round_score": None,
                "chosen": action_label == choice,
            })

        return choice

    def choose_card_position(self, card, board, ctx=None):
        row, col = self.inner.choose_card_position(card, board, ctx)

        # Enregistrer la position choisie
        features = build_feature_vector(
            "position", board, ctx, card=card, row=row, col=col,
        )
        self.records.append({
            "type": "position",
            "features": features,
            "round_score": None,
            "chosen": True,
        })

        return (row, col)

    def choose_card_to_reveal(self, board, ctx=None):
        row, col = self.inner.choose_card_to_reveal(board, ctx)

        features = build_feature_vector(
            "reveal", board, ctx, row=row, col=col,
        )
        self.records.append({
            "type": "reveal",
            "features": features,
            "round_score": None,
            "chosen": True,
        })

        return (row, col)


def collect_data(
    num_games: int,
    players_per_game: int = 4,
    inner_strategy_factory=None,
    progress_every: int = 1000,
) -> Dict[str, List[dict]]:
    """Joue des parties single-round et collecte les decisions.

    Args:
        num_games: nombre de parties a jouer
        players_per_game: joueurs par partie (2-8)
        inner_strategy_factory: callable() -> PlayerStrategy (None = random genetic)
        progress_every: affiche la progression tous les N jeux

    Returns:
        {"draw": [...], "keep": [...], "position": [...], "reveal": [...]}
        Chaque record = {"features": [...], "round_score": int, "chosen": bool}
    """
    all_records: Dict[str, List[dict]] = {
        "draw": [], "keep": [], "position": [], "reveal": [],
    }

    for game_idx in range(num_games):
        # Creer les collectors
        collectors = []
        for _ in range(players_per_game):
            inner = inner_strategy_factory() if inner_strategy_factory else None
            collectors.append(CollectorStrategy(inner))

        names = [f"P{i}" for i in range(players_per_game)]

        game = SkyjoGame(names, silent=True, strategies=collectors)

        # Scores avant la manche
        scores_before = dict(game.total_scores)

        # Jouer une seule manche
        game.play_game()

        # Etiqueter les records avec le round_score
        for player, coll in zip(game.players, collectors):
            round_score = game.total_scores[player.name] - scores_before[player.name]
            coll.label_records(round_score)

            for rec in coll.records:
                dtype = rec["type"]
                all_records[dtype].append({
                    "features": rec["features"],
                    "round_score": rec["round_score"],
                    "chosen": rec["chosen"],
                })

        if progress_every and (game_idx + 1) % progress_every == 0:
            total = sum(len(v) for v in all_records.values())
            print(f"  Parties {game_idx + 1}/{num_games} — {total} records")

    return all_records
