"""Entrainement des modeles GBT et sauvegarde des agents tree."""

import json
import os
from typing import Dict, List, Optional

from .features import feature_names

# Import sklearn au moment de l'utilisation pour ne pas bloquer
# si sklearn n'est pas installe (ex: dans les tests sans modeles)
DECISION_TYPES = ("draw", "keep", "position", "reveal")

DEFAULT_PARAMS = {
    "max_iter": 200,
    "max_depth": 6,
    "learning_rate": 0.1,
    "min_samples_leaf": 50,
    "validation_fraction": 0.1,
    "early_stopping": True,
    "n_iter_no_change": 10,
}


def train_models(
    records: Dict[str, List[dict]],
    params: Optional[dict] = None,
) -> Dict[str, object]:
    """Entraine un modele GBT par type de decision.

    Args:
        records: {"draw": [...], "keep": [...], ...} tel que retourne par collect_data
        params: hyperparametres pour HistGradientBoostingRegressor

    Returns:
        {"draw": model, "keep": model, "position": model, "reveal": model}
        + {"draw_metrics": {...}, ...}
    """
    from sklearn.ensemble import HistGradientBoostingRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

    hparams = {**DEFAULT_PARAMS, **(params or {})}
    models = {}
    metrics = {}

    for dtype in DECISION_TYPES:
        recs = records.get(dtype, [])
        if len(recs) < 100:
            print(f"  [!] {dtype}: seulement {len(recs)} records, modele ignore")
            continue

        # Construire X et y
        X = [r["features"] for r in recs]
        y = [float(r["round_score"]) for r in recs]

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42,
        )

        print(f"  {dtype}: {len(X_train)} train, {len(X_test)} test")

        model = HistGradientBoostingRegressor(**hparams, random_state=42)
        model.fit(X_train, y_train)

        # Evaluation
        y_pred = model.predict(X_test)
        mse = mean_squared_error(y_test, y_pred)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)

        print(f"    MSE={mse:.2f}  MAE={mae:.2f}  R2={r2:.4f}")

        # Feature importances (si disponibles)
        names = feature_names(dtype)
        if hasattr(model, "feature_importances_"):
            importances = model.feature_importances_
            top_features = sorted(
                zip(names, importances), key=lambda x: x[1], reverse=True,
            )[:5]
            print(f"    Top features: {', '.join(f'{n}={v:.3f}' for n, v in top_features)}")

        models[dtype] = model
        metrics[f"{dtype}_mse"] = round(mse, 4)
        metrics[f"{dtype}_mae"] = round(mae, 4)
        metrics[f"{dtype}_r2"] = round(r2, 4)
        metrics[f"{dtype}_samples"] = len(recs)

    return {"models": models, "metrics": metrics}


def save_agent(
    models: Dict[str, object],
    agent_dir: str,
    agent_id: str,
    iteration: int,
    training_config: dict,
    metrics: dict,
    parent_agent: Optional[str] = None,
) -> str:
    """Sauvegarde un agent tree (modeles + metadata).

    Args:
        models: {"draw": model, ...}
        agent_dir: dossier de destination (ex: agents/BoldFox-tree-v1-4p/)
        agent_id: identifiant de l'agent
        iteration: numero d'iteration
        training_config: config d'entrainement
        metrics: metriques d'evaluation
        parent_agent: agent source des donnees (None pour iteration 1)

    Returns:
        Chemin du dossier de l'agent.
    """
    import joblib

    os.makedirs(agent_dir, exist_ok=True)

    # Sauvegarder les modeles
    for dtype, model in models.items():
        model_path = os.path.join(agent_dir, f"{dtype}_model.joblib")
        joblib.dump(model, model_path)

    # Metadata
    feat_names = {dtype: feature_names(dtype) for dtype in DECISION_TYPES}

    metadata = {
        "version": 3,
        "type": "tree",
        "agent_id": agent_id,
        "iteration": iteration,
        "parent_agent": parent_agent,
        "training_config": training_config,
        "metrics": metrics,
        "feature_names": feat_names,
    }

    meta_path = os.path.join(agent_dir, "metadata.json")
    with open(meta_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"  Agent sauvegarde: {agent_dir}")
    return agent_dir


def load_agent_metadata(agent_dir: str) -> dict:
    """Charge les metadonnees d'un agent tree."""
    meta_path = os.path.join(agent_dir, "metadata.json")
    with open(meta_path) as f:
        data = json.load(f)
    return {
        "agent_id": data["agent_id"],
        "filepath": agent_dir,
        "training_config": data.get("training_config", {}),
        "type": "tree",
    }
