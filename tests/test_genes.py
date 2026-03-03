from dataclasses import fields
from src.ai.genes import AIGenes, GENE_RANGES, CONTEXT_GENE_DEFAULTS


def _sample_genes(**overrides):
    """Cree un AIGenes avec des valeurs par defaut raisonnables."""
    defaults = {f.name: 1.0 for f in fields(AIGenes)}
    defaults.update(overrides)
    return AIGenes(**defaults)


def test_clamp_within_range():
    """Genes deja dans les bornes → identiques apres clamp."""
    genes = _sample_genes()
    clamped = genes.clamp()
    for f in fields(AIGenes):
        assert getattr(clamped, f.name) == getattr(genes, f.name)


def test_clamp_out_of_range():
    """Genes hors bornes → clampees aux bornes."""
    genes = _sample_genes(discard_threshold=99, risk_tolerance=-10)
    clamped = genes.clamp()

    lo, hi = GENE_RANGES["discard_threshold"]
    assert clamped.discard_threshold == hi

    lo, hi = GENE_RANGES["risk_tolerance"]
    assert clamped.risk_tolerance == lo


def test_to_dict_from_dict_roundtrip():
    """Serialisation → deserialisation preserve les valeurs."""
    genes = _sample_genes(discard_threshold=3.5, column_weight=1.7)
    restored = AIGenes.from_dict(genes.to_dict())
    for f in fields(AIGenes):
        assert getattr(restored, f.name) == getattr(genes, f.name)


def test_gene_ranges_cover_all_fields():
    """Chaque champ de AIGenes a un range defini."""
    gene_fields = {f.name for f in fields(AIGenes)}
    range_keys = set(GENE_RANGES.keys())
    assert gene_fields == range_keys


def test_from_dict_fills_context_defaults():
    """Dict avec 10 genes (v1/v2) → 5 nouveaux genes a 0.0."""
    old_dict = {
        "discard_threshold": 4.0, "keep_threshold": 3.0,
        "value_weight": 1.0, "hidden_weight": 0.5,
        "column_weight": 1.5, "column_completion": 2.0,
        "low_card_bonus": 1.0, "high_card_panic": 1.5,
        "swap_reluctance": 0.8, "risk_tolerance": 0.3,
    }
    genes = AIGenes.from_dict(old_dict)
    for gene_name, default_val in CONTEXT_GENE_DEFAULTS.items():
        assert getattr(genes, gene_name) == default_val


def test_from_dict_respects_new_genes():
    """Dict avec 15 genes → valeurs contextuelles respectees."""
    full_dict = {f.name: 1.0 for f in fields(AIGenes)}
    full_dict["endgame_aggression"] = 1.5
    full_dict["doubling_caution"] = 2.0
    genes = AIGenes.from_dict(full_dict)
    assert genes.endgame_aggression == 1.5
    assert genes.doubling_caution == 2.0
