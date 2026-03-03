from dataclasses import dataclass, asdict, fields

# Bornes valides pour chaque gene (min, max)
GENE_RANGES: dict[str, tuple[float, float]] = {
    "discard_threshold": (0, 8),
    "keep_threshold":    (0, 8),
    "value_weight":      (0, 2),
    "hidden_weight":     (-1, 1),
    "column_weight":     (0, 2),
    "column_completion": (0, 5),
    "low_card_bonus":    (0, 3),
    "high_card_panic":   (0, 3),
    "swap_reluctance":   (0, 2),
    "risk_tolerance":    (-2, 2),
    # Genes contextuels (v3)
    "endgame_aggression": (-2, 2),
    "doubling_caution":   (0, 3),
    "opponent_awareness": (0, 2),
    "score_pressure":     (-1, 1),
    "deck_urgency":       (0, 2),
}

# Valeurs par defaut pour backward-compat (agents v1/v2 sans ces genes)
CONTEXT_GENE_DEFAULTS: dict[str, float] = {
    "endgame_aggression": 0.0,
    "doubling_caution": 0.0,
    "opponent_awareness": 0.0,
    "score_pressure": 0.0,
    "deck_urgency": 0.0,
}


@dataclass
class AIGenes:
    """15 genes qui pilotent les decisions de l'IA Skyjo."""
    discard_threshold: float   # Prendre la defausse si valeur <= seuil
    keep_threshold: float      # Garder la carte piochee si valeur <= seuil
    value_weight: float        # Poids: remplacer les cartes visibles de haute valeur
    hidden_weight: float       # Preference pour remplacer les cartes cachees
    column_weight: float       # Bonus par carte identique dans la colonne
    column_completion: float   # Bonus quand le placement complete une colonne (3 match)
    low_card_bonus: float      # Desir supplementaire pour cartes <= 0
    high_card_panic: float     # Urgence pour remplacer cartes >= 9
    swap_reluctance: float     # Reticence a remplacer des cartes visibles de faible valeur
    risk_tolerance: float      # Modificateur general sur les seuils draw/keep
    # Genes contextuels (v3)
    endgame_aggression: float  # Adversaires proches de finir → ajuster seuils
    doubling_caution: float    # Penalite pour finir quand risque de doublement
    opponent_awareness: float  # Eviter de defausser ce qui aide le joueur suivant
    score_pressure: float      # Score cumule eleve → prendre plus de risques
    deck_urgency: float        # Deck bas → accepter des cartes moins bonnes

    def clamp(self) -> 'AIGenes':
        """Retourne un nouvel AIGenes avec chaque gene clamp dans son range."""
        clamped = {}
        for f in fields(self):
            lo, hi = GENE_RANGES[f.name]
            clamped[f.name] = max(lo, min(hi, getattr(self, f.name)))
        return AIGenes(**clamped)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> 'AIGenes':
        filled = {**CONTEXT_GENE_DEFAULTS, **d}
        return cls(**filled)
