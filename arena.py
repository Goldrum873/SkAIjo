"""CLI pour l'arena ELO entre agents Skyjo."""
import argparse

from src.arena.leaderboard import format_leaderboard, load_leaderboard
from src.arena.runner import load_agents_from_dir, run_simulation

AGENTS_DIR = "agents"
LEADERBOARD_PATH = "leaderboard.json"
HISTORY_PATH = "elo_history.csv"


def cmd_list(args: argparse.Namespace) -> None:
    """Liste les agents disponibles."""
    agents = load_agents_from_dir(AGENTS_DIR)
    if not agents:
        print("Aucun agent trouve dans agents/")
        return

    print(f"{'Agent ID':<35}| {'Table':>5} | {'Generations':>11}")
    print("-" * 35 + "|" + "-" * 7 + "|" + "-" * 13)
    for meta in agents:
        config = meta["training_config"]
        table = config.get("players_per_game", "?")
        gens = config.get("generations", "?")
        print(f"{meta['agent_id']:<35}| {str(table):>5} | {str(gens):>11}")


def cmd_simulate(args: argparse.Namespace) -> None:
    """Lance des matchs aleatoires et met a jour le leaderboard."""
    agents = load_agents_from_dir(AGENTS_DIR)
    if not agents:
        print("Aucun agent trouve dans agents/")
        return

    print(f"Simulation: {args.games} matchs a {args.players} joueurs")
    print(f"{len(agents)} agents disponibles\n")

    data = run_simulation(agents, args.players, args.games, LEADERBOARD_PATH, HISTORY_PATH)

    print(f"\nSimulation terminee. {data['total_matches']} matchs au total.")
    print(f"Historique ELO: {HISTORY_PATH}\n")
    print(format_leaderboard(data))


def cmd_leaderboard(args: argparse.Namespace) -> None:
    """Affiche le classement ELO."""
    data = load_leaderboard(LEADERBOARD_PATH)
    print(format_leaderboard(data, table_size=args.table_size))


def cmd_compare(args: argparse.Namespace) -> None:
    """Affiche les stats cross-table d'un agent."""
    data = load_leaderboard(LEADERBOARD_PATH)
    agent = data["agents"].get(args.agent_id)
    if not agent:
        print(f"Agent '{args.agent_id}' non trouve dans le leaderboard.")
        return

    config = agent.get("training_config", {})
    trained_for = config.get("players_per_game", "?")

    print(f"Agent: {args.agent_id}")
    print(f"Entraine pour: {trained_for} joueurs")
    print(f"ELO global: {agent['global_elo']:.0f} ({agent['global_games']} parties)\n")

    if not agent["per_table_size"]:
        print("Aucune donnee par taille de table.")
        return

    print(f"{'Table':>5} | {'ELO':>6} | {'Parties':>7} | {'Victoires':>9}")
    print("-" * 5 + "-|" + "-" * 8 + "|" + "-" * 9 + "|" + "-" * 11)

    for size in sorted(agent["per_table_size"].keys(), key=int):
        stats = agent["per_table_size"][size]
        print(
            f"  {size}p  | {stats['elo']:>6.0f} | {stats['games']:>7} | {stats['wins']:>9}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Arena ELO pour agents Skyjo")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="Lister les agents disponibles")

    sim = subparsers.add_parser("simulate", help="Lancer des matchs")
    sim.add_argument("-n", "--players", type=int, default=4,
                     choices=range(2, 9),
                     help="Joueurs par table (2-8, defaut: 4)")
    sim.add_argument("--games", type=int, default=200,
                     help="Nombre de matchs (defaut: 200)")

    lb = subparsers.add_parser("leaderboard", help="Afficher le classement")
    lb.add_argument("-t", "--table-size", type=int, default=None,
                    help="Filtrer par taille de table")

    comp = subparsers.add_parser("compare", help="Stats cross-table d'un agent")
    comp.add_argument("agent_id", help="ID de l'agent a comparer")

    args = parser.parse_args()

    commands = {
        "list": cmd_list,
        "simulate": cmd_simulate,
        "leaderboard": cmd_leaderboard,
        "compare": cmd_compare,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
