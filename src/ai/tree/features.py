"""Extraction de features depuis l'etat de jeu pour les modeles GBT.

Module pur (fonctions sans effet de bord). Transforme un etat de jeu
(board + context + carte/action) en vecteur numerique plat.
"""

from typing import List, Optional
from ...models.card import Card
from ..context import GameContext


# ── Board features ──────────────────────────────────────────────

def _board_features(board: List[List[Card]]) -> List[float]:
    """~25 features decrivant l'etat du plateau du joueur."""
    visible_values: List[int] = []
    hidden_count = 0
    visible_count = 0

    # Par colonne : visible_count, has_pair, pair_value, sum
    num_cols = len(board[0]) if board else 4
    num_rows = len(board)
    col_visible: List[List[int]] = [[] for _ in range(num_cols)]

    for r in range(num_rows):
        for c in range(num_cols):
            card = board[r][c]
            if card is None:
                continue
            if card.visible:
                visible_values.append(card.value)
                visible_count += 1
                col_visible[c].append(card.value)
            else:
                hidden_count += 1

    my_visible_score = sum(visible_values) if visible_values else 0.0
    my_max_visible = max(visible_values) if visible_values else 13.0
    my_min_visible = min(visible_values) if visible_values else -3.0
    high_cards = sum(1 for v in visible_values if v >= 9)
    negative_cards = sum(1 for v in visible_values if v <= 0)

    # Colonnes clearees (toutes les cartes None)
    cleared_columns = 0
    for c in range(num_cols):
        if all(board[r][c] is None for r in range(num_rows)):
            cleared_columns += 1

    features = [
        float(my_visible_score),
        float(hidden_count),
        float(visible_count),
        float(my_max_visible),
        float(my_min_visible),
        float(high_cards),
        float(negative_cards),
        float(cleared_columns),
    ]

    # Features par colonne
    potential_clears = 0
    for c in range(num_cols):
        vals = col_visible[c]
        col_vis_count = float(len(vals))
        col_sum = float(sum(vals)) if vals else 0.0

        # Paire : 2+ cartes visibles identiques
        has_pair = 0.0
        pair_value = -3.0
        if len(vals) >= 2:
            from collections import Counter
            counts = Counter(vals)
            most_common_val, most_common_count = counts.most_common(1)[0]
            if most_common_count >= 2:
                has_pair = 1.0
                pair_value = float(most_common_val)
                potential_clears += 1

        features.extend([col_vis_count, has_pair, pair_value, col_sum])

    features.append(float(potential_clears))

    return features


def _board_feature_names() -> List[str]:
    """Noms des features plateau."""
    names = [
        "my_visible_score", "my_hidden_count", "my_visible_count",
        "my_max_visible", "my_min_visible",
        "my_high_cards", "my_negative_cards", "cleared_columns",
    ]
    for c in range(4):
        names.extend([
            f"col_{c}_visible_count",
            f"col_{c}_has_pair",
            f"col_{c}_pair_value",
            f"col_{c}_sum",
        ])
    names.append("potential_clears")
    return names


# ── Context features ────────────────────────────────────────────

def _context_features(ctx: Optional[GameContext]) -> List[float]:
    """~18 features decrivant le contexte de jeu."""
    if ctx is None:
        return [0.0] * len(_context_feature_names())

    opps = ctx.opponents
    num_opponents = float(len(opps))

    # Prochain adversaire (opp1)
    opp1_vis = float(opps[0].visible_score) if opps else 0.0
    opp1_hid = float(opps[0].hidden_count) if opps else 0.0
    opp1_total = float(opps[0].total_score) if opps else 0.0

    # 2e adversaire (opp2)
    opp2_vis = float(opps[1].visible_score) if len(opps) > 1 else 0.0
    opp2_hid = float(opps[1].hidden_count) if len(opps) > 1 else 0.0
    opp2_total = float(opps[1].total_score) if len(opps) > 1 else 0.0

    score_gap = float(ctx.my_visible_score - ctx.min_opponent_visible_score)

    return [
        float(ctx.deck_size),
        float(ctx.discard_pile_size),
        float(ctx.turn_number),
        float(ctx.my_total_score),
        float(ctx.round_number),
        1.0 if ctx.is_last_round else 0.0,
        num_opponents,
        float(ctx.min_opponent_visible_score),
        float(ctx.min_opponent_hidden_count),
        score_gap,
        opp1_vis,
        opp1_hid,
        opp1_total,
        opp2_vis,
        opp2_hid,
        opp2_total,
    ]


def _context_feature_names() -> List[str]:
    return [
        "deck_size", "discard_pile_size", "turn_number",
        "my_total_score", "round_number", "is_last_round",
        "num_opponents",
        "min_opp_visible_score", "min_opp_hidden_count", "score_gap",
        "opp1_visible_score", "opp1_hidden_count", "opp1_total_score",
        "opp2_visible_score", "opp2_hidden_count", "opp2_total_score",
    ]


# ── Decision-specific features ──────────────────────────────────

def _card_board_interaction(
    card_value: int, board: List[List[Card]],
) -> tuple:
    """Calcule les interactions carte-plateau communes a draw/keep."""
    visible_values = [
        board[r][c].value
        for r in range(len(board))
        for c in range(len(board[0]))
        if board[r][c] is not None and board[r][c].visible
    ]
    avg_visible = sum(visible_values) / len(visible_values) if visible_values else 5.0
    worst_card = max(visible_values) if visible_values else 0.0

    # Meilleur match colonne
    best_col_match = 0
    can_clear = 0.0
    num_cols = len(board[0]) if board else 4
    for c in range(num_cols):
        matches = 0
        col_cards = 0
        for r in range(len(board)):
            cell = board[r][c]
            if cell is not None and cell.visible and cell.value == card_value:
                matches += 1
            if cell is not None:
                col_cards += 1
        if matches > best_col_match:
            best_col_match = matches
        if matches == 2 and col_cards == 3:
            can_clear = 1.0

    return best_col_match, can_clear, worst_card, avg_visible


def _draw_features(
    board: List[List[Card]], card_value: int, action: float,
) -> List[float]:
    """Features pour la decision draw_or_discard."""
    best_match, can_clear, worst, avg = _card_board_interaction(card_value, board)
    return [
        float(card_value),
        1.0 if card_value <= 0 else 0.0,
        float(best_match),
        can_clear,
        float(worst),
        float(card_value) - avg,
        action,  # 0.0 = prendre defausse (D), 1.0 = piocher (P)
    ]


def _draw_feature_names() -> List[str]:
    return [
        "card_value", "card_is_negative", "best_col_match",
        "can_clear", "worst_board_card", "value_vs_avg", "action",
    ]


def _keep_features(
    board: List[List[Card]], card_value: int, action: float,
) -> List[float]:
    """Features pour la decision keep_or_discard."""
    best_match, can_clear, worst, avg = _card_board_interaction(card_value, board)
    return [
        float(card_value),
        1.0 if card_value <= 0 else 0.0,
        float(best_match),
        can_clear,
        float(worst),
        float(card_value) - avg,
        action,  # 0.0 = garder (G), 1.0 = defausser (D)
    ]


def _keep_feature_names() -> List[str]:
    return [
        "card_value", "card_is_negative", "best_col_match",
        "can_clear", "worst_board_card", "value_vs_avg", "action",
    ]


def _position_features(
    board: List[List[Card]], card_value: int, row: int, col: int,
) -> List[float]:
    """Features pour la decision card_position."""
    existing = board[row][col]
    existing_visible = 0.0
    existing_value = 5.0  # estimation pour carte cachee
    if existing is not None and existing.visible:
        existing_visible = 1.0
        existing_value = float(existing.value)

    value_delta = float(card_value) - existing_value

    # Matches dans la colonne
    col_matches = 0
    for r in range(len(board)):
        cell = board[r][col]
        if cell is not None and cell.visible and cell.value == card_value:
            col_matches += 1

    # Est-ce que placer ici clear la colonne ?
    would_clear = 0.0
    clear_value_saved = 0.0
    if col_matches == 2:
        col_cards = [board[r][col] for r in range(len(board)) if board[r][col] is not None]
        if len(col_cards) == 3:  # colonne pleine
            would_clear = 1.0
            clear_value_saved = sum(
                c.value for c in col_cards if c.visible
            ) + card_value

    # Est-ce que ca termine la manche ?
    would_finish = 0.0
    finish_risk = 0.0
    hidden_remaining = sum(
        1 for r in range(len(board)) for c in range(len(board[0]))
        if board[r][c] is not None and not board[r][c].visible
    )
    if existing is not None and not existing.visible:
        # On revele la derniere carte cachee + on remplace
        if hidden_remaining <= 1:
            would_finish = 1.0
    elif hidden_remaining == 0:
        would_finish = 1.0

    # Risque de finir = score visible actuel (haut = risque de doublement)
    if would_finish > 0:
        vis_score = sum(
            board[r][c].value
            for r in range(len(board)) for c in range(len(board[0]))
            if board[r][c] is not None and board[r][c].visible
        )
        finish_risk = float(vis_score)

    return [
        float(card_value),
        float(row),
        float(col),
        existing_visible,
        existing_value,
        value_delta,
        float(col_matches),
        would_clear,
        clear_value_saved,
        would_finish,
        finish_risk,
    ]


def _position_feature_names() -> List[str]:
    return [
        "card_value", "row", "col", "existing_visible", "existing_value",
        "value_delta", "col_matches", "would_clear", "clear_value_saved",
        "would_finish", "finish_risk",
    ]


def _reveal_features(board: List[List[Card]], row: int, col: int) -> List[float]:
    """Features pour la decision card_to_reveal."""
    # Visible dans la colonne
    col_values = []
    for r in range(len(board)):
        cell = board[r][col]
        if cell is not None and cell.visible:
            col_values.append(cell.value)

    col_visible_count = float(len(col_values))

    has_pair = 0.0
    pair_value = -3.0
    prob_clear = 0.0
    if len(col_values) >= 2:
        from collections import Counter
        counts = Counter(col_values)
        val, cnt = counts.most_common(1)[0]
        if cnt >= 2:
            has_pair = 1.0
            pair_value = float(val)
            # Probabilite de clear : ~10/150 cartes ont la bonne valeur
            # Approximation grossiere mais utile comme signal
            prob_clear = 0.07

    return [
        float(row),
        float(col),
        col_visible_count,
        has_pair,
        pair_value,
        prob_clear,
    ]


def _reveal_feature_names() -> List[str]:
    return [
        "row", "col", "col_visible_count",
        "col_has_pair", "col_pair_value", "prob_clear",
    ]


# ── API publique ────────────────────────────────────────────────

_DECISION_BUILDERS = {
    "draw": (_draw_features, _draw_feature_names),
    "keep": (_keep_features, _keep_feature_names),
    "position": (_position_features, _position_feature_names),
    "reveal": (_reveal_features, _reveal_feature_names),
}


def build_feature_vector(
    decision_type: str,
    board: List[List[Card]],
    ctx: Optional[GameContext] = None,
    card: Optional[Card] = None,
    action: Optional[float] = None,
    row: Optional[int] = None,
    col: Optional[int] = None,
) -> List[float]:
    """Construit le vecteur de features complet pour une decision.

    Args:
        decision_type: "draw", "keep", "position", ou "reveal"
        board: plateau 3x4 du joueur
        ctx: contexte de jeu (None -> features contextuels a 0)
        card: carte consideree (draw/keep/position)
        action: action encodee (draw: 0=D/1=P, keep: 0=G/1=D)
        row, col: position sur le plateau (position/reveal)

    Returns:
        Vecteur plat de features numeriques.
    """
    if decision_type not in _DECISION_BUILDERS:
        raise ValueError(f"Type de decision inconnu: {decision_type}")

    base = _board_features(board) + _context_features(ctx)

    if decision_type == "draw":
        card_value = card.value if card is not None else 0
        extra = _draw_features(board, card_value, action if action is not None else 0.0)
    elif decision_type == "keep":
        card_value = card.value if card is not None else 0
        extra = _keep_features(board, card_value, action if action is not None else 0.0)
    elif decision_type == "position":
        card_value = card.value if card is not None else 0
        extra = _position_features(board, card_value, row or 0, col or 0)
    else:  # reveal
        extra = _reveal_features(board, row or 0, col or 0)

    return base + extra


def feature_names(decision_type: str) -> List[str]:
    """Retourne les noms de features pour un type de decision."""
    if decision_type not in _DECISION_BUILDERS:
        raise ValueError(f"Type de decision inconnu: {decision_type}")

    base = _board_feature_names() + _context_feature_names()
    _, extra_names_fn = _DECISION_BUILDERS[decision_type]
    return base + extra_names_fn()
