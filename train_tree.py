"""Entraine une IA Skyjo par arbres gradient-boostes (self-play iteratif)."""

import argparse
import os
import random
import shutil

from src.ai.tree.collector import collect_data
from src.ai.tree.training import train_models, save_agent, DECISION_TYPES
from src.ai.tree.strategy import TreeAIStrategy
from src.ai.trainer import _ADJECTIVES, _NOUNS


def generate_tree_name() -> str:
    """Genere un prefixe AdjectifAnimal pour la lignee."""
    adj = random.choice(_ADJECTIVES)
    noun = random.choice(_NOUNS)
    return f"{adj}{noun}"


def main():
    parser = argparse.ArgumentParser(
        description="Entrainer une IA Skyjo par arbres gradient-boostes",
    )
    parser.add_argument(
        "-g", "--games", type=int, default=20000,
        help="Nombre de parties par iteration (defaut: 20000)",
    )
    parser.add_argument(
        "-n", "--players", type=int, default=4, choices=range(2, 9),
        help="Joueurs par partie (2-8, defaut: 4)",
    )
    parser.add_argument(
        "--iterations", type=int, default=1,
        help="Nombre d'iterations self-play (defaut: 1)",
    )
    parser.add_argument(
        "--name", default=None,
        help="Prefixe de lignee (defaut: auto-genere)",
    )
    parser.add_argument(
        "--agents-dir", default="agents",
        help="Dossier des agents (defaut: agents/)",
    )
    args = parser.parse_args()

    lineage_name = args.name or generate_tree_name()
    agents_dir = args.agents_dir
    os.makedirs(agents_dir, exist_ok=True)

    print(f"Lignee: {lineage_name}")
    print(f"Iterations: {args.iterations}")
    print(f"Parties/iteration: {args.games}")
    print(f"Joueurs/partie: {args.players}")
    print()

    prev_agent_dir = None
    prev_agent_id = None

    for iteration in range(1, args.iterations + 1):
        agent_id = f"{lineage_name}-tree-v{iteration}-{args.players}p"
        agent_dir = os.path.join(agents_dir, agent_id)

        print(f"=== Iteration {iteration}/{args.iterations} : {agent_id} ===")

        # Factory de strategie interne
        if prev_agent_dir is not None:
            # Self-play avec l'agent precedent
            loaded_dir = prev_agent_dir
            print(f"  Self-play avec: {prev_agent_id}")
            strategy_factory = lambda d=loaded_dir: TreeAIStrategy(d)
        else:
            # Iteration 1 : IA random
            print("  Self-play avec: IA random")
            strategy_factory = None

        # Collecte
        print(f"  Collecte de donnees ({args.games} parties)...")
        records = collect_data(
            num_games=args.games,
            players_per_game=args.players,
            inner_strategy_factory=strategy_factory,
        )

        for dtype, recs in records.items():
            print(f"    {dtype}: {len(recs)} records")

        # Entrainement
        print("  Entrainement des modeles...")
        result = train_models(records)
        models = result["models"]
        metrics = result["metrics"]

        if not models:
            print("  [!] Aucun modele entraine, pas assez de donnees")
            break

        # Sauvegarde
        training_config = {
            "num_games": args.games,
            "players_per_game": args.players,
        }

        # Copier les modeles manquants depuis le parent
        if prev_agent_dir is not None:
            for dtype in DECISION_TYPES:
                if dtype not in models:
                    parent_model = os.path.join(prev_agent_dir, f"{dtype}_model.joblib")
                    if os.path.exists(parent_model):
                        os.makedirs(agent_dir, exist_ok=True)
                        shutil.copy2(parent_model, os.path.join(agent_dir, f"{dtype}_model.joblib"))
                        print(f"  {dtype}: copie depuis le parent ({prev_agent_id})")

        save_agent(
            models=models,
            agent_dir=agent_dir,
            agent_id=agent_id,
            iteration=iteration,
            training_config=training_config,
            metrics=metrics,
            parent_agent=prev_agent_id,
        )

        prev_agent_dir = agent_dir
        prev_agent_id = agent_id
        print()

    print(f"Entrainement termine. {args.iterations} agent(s) cree(s).")


if __name__ == "__main__":
    main()
