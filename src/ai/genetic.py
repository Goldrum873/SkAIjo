from typing import List, Optional, Tuple
from dataclasses import fields
import random
from .strategy import PlayerStrategy
from .genes import AIGenes, GENE_RANGES
from .context import GameContext
from ..models.card import Card


class GeneticAIStrategy(PlayerStrategy):
    def __init__(self, genes: 'AIGenes | None' = None):
        self.genes = genes or self.random_genes()
        self.fitness_score = 0
        self.games_played = 0
        self.rankings: List[int] = []

    @staticmethod
    def random_genes() -> AIGenes:
        return AIGenes(
            discard_threshold=random.uniform(0, 8),
            keep_threshold=random.uniform(0, 8),
            value_weight=random.uniform(0, 2),
            hidden_weight=random.choice([-1.0, 1.0]),
            column_weight=random.uniform(0, 2),
            column_completion=random.uniform(0, 5),
            low_card_bonus=random.uniform(0, 3),
            high_card_panic=random.uniform(0, 3),
            swap_reluctance=random.uniform(0, 2),
            risk_tolerance=random.uniform(-2, 2),
            endgame_aggression=random.uniform(-2, 2),
            doubling_caution=random.uniform(0, 3),
            opponent_awareness=random.uniform(0, 2),
            score_pressure=random.uniform(-1, 1),
            deck_urgency=random.uniform(0, 2),
        )

    def mutate(self, mutation_rate: float = 0.1) -> 'GeneticAIStrategy':
        """Cree une copie avec des genes legerement mutes, clampes dans les ranges."""
        gene_values = {}
        for f in fields(AIGenes):
            old = getattr(self.genes, f.name)
            lo, hi = GENE_RANGES[f.name]
            sigma = mutation_rate * (hi - lo)
            gene_values[f.name] = old + random.gauss(0, sigma)
        return GeneticAIStrategy(AIGenes(**gene_values).clamp())

    # -- Helpers ------------------------------------------------

    def _count_column_matches(
        self, board: List[List[Card]], col: int, target_value: int,
    ) -> int:
        """Nombre de cartes visibles dans la colonne qui matchent target_value."""
        count = 0
        for row in range(len(board)):
            card = board[row][col]
            if card is not None and card.visible and card.value == target_value:
                count += 1
        return count

    def _would_finish_after_placement(
        self, board: List[List[Card]], row: int, col: int,
    ) -> bool:
        """Verifie si placer une carte a (row, col) revelerait toutes les cartes."""
        for r in range(len(board)):
            for c in range(len(board[0])):
                if board[r][c] is None:
                    continue
                if r == row and c == col:
                    # Cette carte sera remplacee (donc visible)
                    continue
                if not board[r][c].visible:
                    return False
        return True

    def _count_opponent_column_matches(
        self, opp_board: Tuple[Tuple[Optional[Card], ...], ...],
        col: int, value: int,
    ) -> int:
        """Compte les cartes visibles matchant value dans la colonne d'un adversaire."""
        count = 0
        for row in range(len(opp_board)):
            card = opp_board[row][col]
            if card is not None and card.visible and card.value == value:
                count += 1
        return count

    def _apply_threshold_modifiers(
        self, threshold: float, ctx: Optional[GameContext],
    ) -> float:
        """Applique les modificateurs contextuels aux seuils draw/keep."""
        if ctx is None:
            return threshold
        g = self.genes

        # Endgame: adversaire proche de finir → ajuster agressivite
        if ctx.min_opponent_hidden_count <= 2:
            hidden = ctx.min_opponent_hidden_count
            threshold += g.endgame_aggression * (3 - hidden) / 3

        # Deck urgency: deck bas → accepter plus
        if ctx.deck_size < 20:
            threshold += g.deck_urgency * (20 - ctx.deck_size) / 20

        # Score pressure: score cumule eleve → plus de risques
        if ctx.my_total_score > 50:
            threshold += g.score_pressure * (ctx.my_total_score - 50) / 50

        return threshold

    def _score_position(
        self, card: Card, board: List[List[Card]], row: int, col: int,
        ctx: Optional[GameContext] = None,
    ) -> float:
        """Score de desirabilite pour placer `card` a la position (row, col)."""
        g = self.genes
        existing = board[row][col]
        if existing is None:
            return float('-inf')

        score = 0.0

        if existing.visible:
            # Envie de remplacer proportionnelle a la valeur existante
            score += existing.value * g.value_weight
            # Urgence supplementaire pour les cartes >= 9
            if existing.value >= 9:
                score += g.high_card_panic * (existing.value - 8)
            # Reticence a remplacer les bonnes cartes (valeur <= 2)
            if existing.value <= 2:
                score -= g.swap_reluctance * (3 - existing.value)
        else:
            # Carte cachee: valeur inconnue, on estime a 5 (moyenne du deck)
            score += g.hidden_weight * 5

        # Bonus colonne: cartes deja identiques dans cette colonne
        matches = self._count_column_matches(board, col, card.value)
        score += matches * g.column_weight

        # Bonus completion: si 2 cartes matchent deja, on complete la colonne
        if matches == 2:
            score += g.column_completion

        # -- Modificateurs contextuels --
        if ctx is not None:
            # Doubling caution: penaliser si finir = risque de doublement
            if self._would_finish_after_placement(board, row, col):
                if ctx.my_visible_score >= ctx.min_opponent_visible_score and ctx.my_visible_score > 0:
                    score -= g.doubling_caution * 3

            # Opponent awareness: eviter de defausser ce qui aide le suivant
            if existing is not None and existing.visible and ctx.opponents:
                next_opp = ctx.opponents[0]
                for opp_col in range(len(next_opp.board[0]) if next_opp.board else 0):
                    opp_matches = self._count_opponent_column_matches(
                        next_opp.board, opp_col, existing.value,
                    )
                    if opp_matches >= 2:
                        score -= g.opponent_awareness
                        break

            # Endgame column boost: adversaires proches + completion possible
            if ctx.min_opponent_hidden_count <= 2 and matches == 2:
                score += g.endgame_aggression * 0.5

        return score

    # -- Strategy methods ---------------------------------------

    def choose_initial_cards(
        self, board: List[List[Card]], ctx=None,
    ) -> List[Tuple[int, int]]:
        """Choix aveugle: 2 positions aleatoires parmi les cartes cachees."""
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
        g = self.genes
        value = visible_card.value
        threshold = g.discard_threshold + g.risk_tolerance

        # Carte tres basse → bonus supplementaire
        if value <= 0:
            threshold += g.low_card_bonus

        # Modificateurs contextuels
        threshold = self._apply_threshold_modifiers(threshold, ctx)

        if value <= threshold:
            return 'D'

        # Verifier si un bonus colonne rend la carte attractive
        for col in range(len(board[0])):
            matches = self._count_column_matches(board, col, value)
            if matches > 0 and value <= threshold + matches * g.column_weight:
                return 'D'

        return 'P'

    def choose_keep_or_discard(
        self, drawn_card: Card, board: List[List[Card]], ctx=None,
    ) -> str:
        g = self.genes
        value = drawn_card.value
        threshold = g.keep_threshold + g.risk_tolerance

        if value <= 0:
            threshold += g.low_card_bonus

        # Modificateurs contextuels
        threshold = self._apply_threshold_modifiers(threshold, ctx)

        if value <= threshold:
            return 'G'

        for col in range(len(board[0])):
            matches = self._count_column_matches(board, col, value)
            if matches > 0 and value <= threshold + matches * g.column_weight:
                return 'G'

        return 'D'

    def choose_card_position(
        self, card: Card, board: List[List[Card]], ctx=None,
    ) -> Tuple[int, int]:
        best_score = float('-inf')
        best_positions: List[Tuple[int, int]] = []

        for r in range(len(board)):
            for c in range(len(board[0])):
                if board[r][c] is None:
                    continue
                s = self._score_position(card, board, r, c, ctx)
                if s > best_score:
                    best_score = s
                    best_positions = [(r, c)]
                elif s == best_score:
                    best_positions.append((r, c))

        return random.choice(best_positions)

    def choose_card_to_reveal(
        self, board: List[List[Card]], ctx=None,
    ) -> Tuple[int, int]:
        """Revelation contextuelle: prefere les colonnes avec matchs visibles."""
        hidden = [
            (r, c)
            for r in range(len(board))
            for c in range(len(board[0]))
            if board[r][c] is not None and not board[r][c].visible
        ]

        if not hidden or ctx is None:
            return random.choice(hidden)

        # Score par position: preference colonnes avec matchs visibles
        scored: List[Tuple[float, int, int]] = []
        for r, c in hidden:
            col_values: List[int] = []
            for row in range(len(board)):
                card = board[row][c]
                if card is not None and card.visible:
                    col_values.append(card.value)

            pos_score = 0.0
            if len(col_values) >= 2 and len(set(col_values)) == 1:
                # 2 cartes visibles identiques → forte chance de clear
                pos_score += 2.0
            elif len(col_values) >= 1:
                # Au moins 1 carte visible
                pos_score += 0.5

            scored.append((pos_score, r, c))

        max_score = max(s for s, _, _ in scored)
        best = [(r, c) for s, r, c in scored if s == max_score]
        return random.choice(best)
