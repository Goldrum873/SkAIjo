"""Analyse et explication des strategies IA Skyjo.

Trois fonctions principales :
- explain_genes()    : profil strategique lisible
- decision_table()   : table de decisions par valeur de carte
- training_report()  : analyse du CSV d'entrainement
"""

import csv
from src.ai.genes import AIGenes, GENE_RANGES


# -- Qualificatifs par gene ------------------------------------------------

def _qualify_threshold(value: float) -> str:
    """Qualifie un seuil de prise/garde (range 0-8)."""
    if value <= 2:
        return "tres selectif"
    if value <= 5:
        return "equilibre"
    return "prend presque tout"


def _qualify_risk(value: float) -> str:
    """Qualifie la tolerance au risque (range -2 a 2)."""
    if value < -0.5:
        return "conservateur"
    if value <= 0.5:
        return "neutre"
    return "agressif"


def _qualify_hidden(value: float) -> str:
    """Qualifie la preference cachees (range -1 a 1)."""
    if value < -0.3:
        return "evite les cachees"
    if value <= 0.3:
        return "neutre"
    return "prefere les cachees"


def _qualify_completion(value: float) -> str:
    """Qualifie le bonus completion colonne (range 0-5)."""
    if value < 1.5:
        return "faible"
    if value <= 3:
        return "moderee"
    return "prioritaire"


def _qualify_low_high(value: float, lo: float, hi: float) -> str:
    """Qualifie un gene generique en 3 niveaux sur son range."""
    third = (hi - lo) / 3
    if value < lo + third:
        return "faible"
    if value < lo + 2 * third:
        return "modere"
    return "eleve"


# -- explain_genes ----------------------------------------------------------

def explain_genes(genes: AIGenes) -> str:
    """Traduit les 10 genes en profil strategique lisible."""
    g = genes
    eff_discard = g.discard_threshold + g.risk_tolerance
    eff_keep = g.keep_threshold + g.risk_tolerance

    lines = [
        "=== Profil strategique ===",
        "",
        "-- Prise de carte --",
        f"Seuil defausse : {g.discard_threshold:.1f}"
        f"  (prend dans la defausse si valeur <= {eff_discard:.0f})"
        f"  [{_qualify_threshold(g.discard_threshold)}]",
        f"Seuil pioche   : {g.keep_threshold:.1f}"
        f"  (garde une carte piochee si valeur <= {eff_keep:.0f})"
        f"  [{_qualify_threshold(g.keep_threshold)}]",
        f"Tolerance risque : {g.risk_tolerance:+.1f}"
        f"  (profil {_qualify_risk(g.risk_tolerance)},"
        f" seuils effectifs {g.risk_tolerance:+.1f})",
        f"Bonus cartes negatives : {g.low_card_bonus:+.1f}"
        f"  ({'tres attire' if g.low_card_bonus > 1.5 else 'attire' if g.low_card_bonus > 0.5 else 'peu attire'}"
        f" par les -2, -1, 0)",
        "",
        "-- Placement sur le plateau --",
        f"Poids valeur      : {g.value_weight:.1f}"
        f"  ({_qualify_low_high(g.value_weight, 0, 2)}"
        f" - remplace {'volontiers' if g.value_weight > 1 else 'parfois'}"
        f" les cartes de haute valeur)",
        f"Poids carte cachee : {g.hidden_weight:+.1f}"
        f"  ({_qualify_hidden(g.hidden_weight)})",
        f"Panique haute carte : {g.high_card_panic:.1f}"
        f"  (urgence {_qualify_low_high(g.high_card_panic, 0, 3)}"
        f" pour virer les 9, 10, 11, 12)",
        f"Reticence basse carte : {g.swap_reluctance:.1f}"
        f"  (protege {'fortement' if g.swap_reluctance > 1.3 else 'moderement' if g.swap_reluctance > 0.6 else 'peu'}"
        f" ses bonnes cartes)",
        "",
        "-- Strategie colonnes --",
        f"Bonus colonne      : {g.column_weight:.1f}"
        f"  ({_qualify_low_high(g.column_weight, 0, 2)}"
        f" - attire par les colonnes avec cartes identiques)",
        f"Bonus completion   : {g.column_completion:.1f}"
        f"  (priorite {_qualify_completion(g.column_completion)}"
        f" a completer une colonne de 3)",
        "",
        "-- Conscience du jeu --",
        f"Endgame aggression  : {g.endgame_aggression:+.1f}"
        f"  ({'agressif' if g.endgame_aggression > 0.5 else 'prudent' if g.endgame_aggression < -0.5 else 'neutre'}"
        f" quand adversaires proches de finir)",
        f"Doubling caution    : {g.doubling_caution:.1f}"
        f"  ({'tres prudent' if g.doubling_caution > 2 else 'prudent' if g.doubling_caution > 1 else 'peu prudent'}"
        f" pour eviter le doublement)",
        f"Opponent awareness  : {g.opponent_awareness:.1f}"
        f"  ({'attentif' if g.opponent_awareness > 1 else 'peu attentif' if g.opponent_awareness > 0.3 else 'ignore'}"
        f" aux besoins du joueur suivant)",
        f"Score pressure      : {g.score_pressure:+.1f}"
        f"  ({'prend des risques' if g.score_pressure > 0.3 else 'joue safe' if g.score_pressure < -0.3 else 'neutre'}"
        f" quand score cumule eleve)",
        f"Deck urgency        : {g.deck_urgency:.1f}"
        f"  ({'accepte plus' if g.deck_urgency > 1 else 'peu influence' if g.deck_urgency > 0.3 else 'ignore'}"
        f" quand le deck est bas)",
    ]
    return "\n".join(lines)


# -- decision_table ---------------------------------------------------------

def decision_table(genes: AIGenes) -> str:
    """Table de decisions pour chaque valeur de carte (-2 a 12)."""
    g = genes
    eff_discard = g.discard_threshold + g.risk_tolerance
    eff_keep = g.keep_threshold + g.risk_tolerance

    lines = [
        "=== Table de decisions (sans bonus colonne) ===",
        "",
        f"Seuil effectif defausse : {eff_discard:.1f}"
        f"  (discard_threshold + risk_tolerance)",
        f"Seuil effectif pioche   : {eff_keep:.1f}"
        f"  (keep_threshold + risk_tolerance)",
        "",
        "Carte | Defausse? | Garder pioche?",
        "------|-----------|---------------",
    ]

    for value in range(-2, 13):
        # Seuil effectif avec bonus cartes negatives
        bonus = g.low_card_bonus if value <= 0 else 0.0
        take_discard = value <= eff_discard + bonus
        keep_draw = value <= eff_keep + bonus

        discard_action = "PRENDRE " if take_discard else "PIOCHER "
        keep_action = "GARDER   " if keep_draw else "DEFAUSSER"
        suffix = f"  (bonus carte negative: {g.low_card_bonus:+.1f})" if value <= 0 and g.low_card_bonus > 0.1 else ""
        lines.append(f"  {value:3d}  | {discard_action} | {keep_action}{suffix}")

    lines.append("")
    lines.append(
        f"Note : en jeu, le bonus colonne"
        f" (+{g.column_weight:.1f} par carte identique) peut"
    )
    lines.append(
        f"changer la decision. Ex: un 7 avec 1 match colonne"
        f" -> seuil {eff_discard + g.column_weight:.1f} -> "
        f"{'PRENDRE' if 7 <= eff_discard + g.column_weight else 'PIOCHER'}."
    )
    return "\n".join(lines)


# -- training_report -------------------------------------------------------

def training_report(csv_path: str) -> str:
    """Analyse le CSV d'entrainement et produit un resume textuel."""
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = [h.strip() for h in next(reader)]
        rows = [[cell.strip() for cell in row] for row in reader if row]

    if not rows:
        return "=== Rapport d'entrainement ===\n\nAucune donnee."

    gene_names = [
        "discard_threshold", "keep_threshold", "value_weight",
        "hidden_weight", "column_weight", "column_completion",
        "low_card_bonus", "high_card_panic", "swap_reluctance",
        "risk_tolerance", "endgame_aggression", "doubling_caution",
        "opponent_awareness", "score_pressure", "deck_urgency",
    ]

    # Indices des colonnes
    idx = {name: header.index(name) for name in gene_names}
    idx_best = header.index("best_fitness")
    idx_avg = header.index("avg_fitness")

    total_gen = len(rows)
    first = rows[0]
    last = rows[-1]

    best_start = float(first[idx_best])
    best_end = float(last[idx_best])
    avg_end = float(last[idx_avg])
    progression = best_end - best_start

    lines = [
        "=== Rapport d'entrainement ===",
        "",
        f"Generations : {total_gen}",
        f"Fitness finale (best) : {best_end:.2f}",
        f"Fitness finale (avg)  : {avg_end:.2f}",
        f"Progression fitness : {progression:+.1f}"
        f" (de {best_start:.1f} a {best_end:.1f})",
        "",
        "-- Evolution des genes --",
        f"{'Gene':<22}| {'Debut':>7} | {'Fin':>7} | {'Delta':>7} | Stable?",
        f"{'-' * 22}|{'-' * 9}|{'-' * 9}|{'-' * 9}|{'-' * 20}",
    ]

    # Analyse par gene
    deltas: list[tuple[str, float]] = []  # (gene_name, delta_relatif)
    stability_info: dict[str, str] = {}

    for gene in gene_names:
        col = idx[gene]
        start_val = float(first[col])
        end_val = float(last[col])
        delta = end_val - start_val

        # Delta relatif par rapport au range
        lo, hi = GENE_RANGES[gene]
        gene_range = hi - lo
        delta_rel = abs(delta) / gene_range if gene_range > 0 else 0

        deltas.append((gene, delta_rel))

        # Stabilite : gene ne bouge plus de > 5% du range
        # sur les 20 dernieres generations
        stable_label = _check_stability(rows, col, gene_range, total_gen)
        stability_info[gene] = stable_label

        lines.append(
            f"{gene:<22}| {start_val:7.2f} | {end_val:7.2f} |"
            f" {delta:+7.2f} | {stable_label}"
        )

    # Tendances cles : top 3 genes par delta relatif
    deltas.sort(key=lambda x: x[1], reverse=True)
    top3 = deltas[:3]

    lines.append("")
    lines.append("-- Tendances cles --")
    for gene, _ in top3:
        col = idx[gene]
        start_val = float(first[col])
        end_val = float(last[col])
        direction = "augmente" if end_val > start_val else "diminue"
        lines.append(f"- {gene} a {direction}"
                      f" ({start_val:.1f} -> {end_val:.1f})"
                      f" : {_trend_phrase(gene, start_val, end_val)}")

    return "\n".join(lines)


def _check_stability(
    rows: list[list[str]], col: int, gene_range: float, total_gen: int
) -> str:
    """Verifie si un gene est stable sur les 20 dernieres generations."""
    window = min(20, total_gen)
    if window < 2:
        return "trop peu de donnees"

    recent = [float(rows[i][col]) for i in range(total_gen - window, total_gen)]
    val_min = min(recent)
    val_max = max(recent)
    variation = (val_max - val_min) / gene_range if gene_range > 0 else 0

    if variation <= 0.05:
        # Trouver depuis quelle generation c'est stable
        stable_since = _find_stable_since(rows, col, gene_range, total_gen)
        return f"oui (depuis gen {stable_since})"
    return "non (encore volatile)"


def _find_stable_since(
    rows: list[list[str]], col: int, gene_range: float, total_gen: int
) -> int:
    """Trouve la generation depuis laquelle le gene est stable."""
    end_val = float(rows[-1][col])
    threshold = 0.05 * gene_range

    # Remonte depuis la fin
    stable_since = total_gen
    for i in range(total_gen - 1, -1, -1):
        val = float(rows[i][col])
        if abs(val - end_val) > threshold:
            stable_since = i + 2  # generation 1-indexed
            break
    else:
        stable_since = 1
    return stable_since


def _trend_phrase(gene: str, start: float, end: float) -> str:
    """Genere une phrase de tendance pour un gene."""
    phrases = {
        "discard_threshold": (
            "l'IA est devenue plus selective" if end < start
            else "l'IA accepte plus facilement les defausses"
        ),
        "keep_threshold": (
            "l'IA est devenue plus exigeante en pioche" if end < start
            else "l'IA garde plus facilement les cartes piochees"
        ),
        "value_weight": (
            "moins focalisee sur le remplacement des hautes cartes" if end < start
            else "cible davantage les cartes de haute valeur"
        ),
        "hidden_weight": (
            "prefere les cartes visibles" if end < start
            else "prefere remplacer les cartes cachees"
        ),
        "column_weight": (
            "moins attiree par les colonnes identiques" if end < start
            else "strategie colonnes renforcee"
        ),
        "column_completion": (
            "priorite completion en baisse" if end < start
            else "completion de colonnes devenue prioritaire"
        ),
        "low_card_bonus": (
            "moins attiree par les cartes negatives" if end < start
            else "chasse davantage les -2, -1, 0"
        ),
        "high_card_panic": (
            "moins de panique face aux hautes cartes" if end < start
            else "urgence accrue pour virer les 9-12"
        ),
        "swap_reluctance": (
            "protege moins ses bonnes cartes" if end < start
            else "protege davantage ses bonnes cartes"
        ),
        "risk_tolerance": (
            "devenue plus conservatrice" if end < start
            else "devenue plus agressive"
        ),
        "endgame_aggression": (
            "moins reactive en fin de partie" if end < start
            else "plus agressive quand adversaires proches de finir"
        ),
        "doubling_caution": (
            "moins prudente sur le doublement" if end < start
            else "evite davantage le risque de doublement"
        ),
        "opponent_awareness": (
            "moins attentive aux adversaires" if end < start
            else "prend davantage en compte le joueur suivant"
        ),
        "score_pressure": (
            "moins influencee par le score cumule" if end < start
            else "prend plus de risques quand score eleve"
        ),
        "deck_urgency": (
            "moins influencee par la taille du deck" if end < start
            else "plus reactive quand le deck diminue"
        ),
    }
    return phrases.get(gene, "evolution notable")


# -- CLI --------------------------------------------------------------------

def _cli() -> None:
    """Point d'entree CLI : python -m src.ai.analysis <model.json> [--csv log.csv]"""
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description="Analyse d'une strategie IA Skyjo"
    )
    parser.add_argument("model", help="Chemin vers le fichier JSON du modele")
    parser.add_argument("--csv", help="Chemin vers le CSV d'entrainement",
                        default=None)
    args = parser.parse_args()

    with open(args.model, "r", encoding="utf-8") as f:
        data = json.load(f)

    genes = AIGenes.from_dict(data["genes"])

    print(explain_genes(genes))
    print()
    print(decision_table(genes))

    if args.csv:
        print()
        print(training_report(args.csv))


if __name__ == "__main__":
    _cli()
