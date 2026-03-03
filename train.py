"""Entraine une IA Skyjo par algorithme genetique."""
import argparse
import os
from src.ai.trainer import GeneticTrainer, generate_agent_name


def main():
    parser = argparse.ArgumentParser(description="Entrainer une IA Skyjo")
    parser.add_argument("-g", "--generations", type=int, default=50,
                        help="Nombre de generations (defaut: 50)")
    parser.add_argument("-p", "--population", type=int, default=100,
                        help="Taille de la population (defaut: 100)")
    parser.add_argument("-n", "--players", type=int, default=8,
                        choices=range(2, 9),
                        help="Nombre de joueurs par partie (2-8, defaut: 8)")
    parser.add_argument("-o", "--output", default=None,
                        help="Fichier de sortie (defaut: agents/<auto>.json)")
    parser.add_argument("--csv", nargs="?", const="training.csv", default=None,
                        help="Log CSV (defaut: training.csv si flag seul)")
    args = parser.parse_args()

    players_per_game = min(args.players, args.population)
    agent_name = generate_agent_name(players_per_game, args.generations)

    # Auto-save dans agents/ si --output absent
    if args.output is None:
        os.makedirs("agents", exist_ok=True)
        args.output = f"agents/{agent_name}.json"

    print(f"Agent: {agent_name}")
    print(f"Entrainement: {args.generations} generations, "
          f"population {args.population}, {players_per_game} joueurs/partie")
    print(f"Sortie: {args.output}")
    if args.csv:
        print(f"Log CSV: {args.csv}")
    print()

    trainer = GeneticTrainer(
        population_size=args.population,
        players_per_game=players_per_game,
    )
    trainer.train_ai(generations=args.generations, log_path=args.csv)
    trainer.save_best(args.output, generations=args.generations, agent_name=agent_name)

    print(f"\n{agent_name} sauvegarde dans {args.output}")


if __name__ == "__main__":
    main()
