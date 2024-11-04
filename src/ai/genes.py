from dataclasses import dataclass

@dataclass
class AIGenes:
    """Représente les "gènes" qui influencent les décisions de l'IA"""
    value_weight: float  # Importance de la valeur d'une carte
    risk_weight: float  # Tendance à prendre des risques
    column_weight: float  # Importance de compléter une colonne
    hidden_penalty: float  # Pénalité pour les cartes cachées