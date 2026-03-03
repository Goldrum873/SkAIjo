import os
from src.game.skyjo import SkyjoGame
from src.ai.trainer import GeneticTrainer


DEFAULT_MODEL = "best_ai.json"


def ask_int(prompt: str, lo: int, hi: int) -> int:
    """Demande un entier valide entre lo et hi (inclus), boucle sinon."""
    while True:
        try:
            value = int(input(prompt))
            if lo <= value <= hi:
                return value
            print(f"Veuillez entrer un nombre entre {lo} et {hi}.")
        except ValueError:
            print("Veuillez entrer un nombre valide.")


def ask_mode() -> int:
    """Demande le mode de jeu : 1 (humains) ou 2 (avec IA)."""
    print("\n1. Partie entre humains")
    print("2. Partie avec IA")
    return ask_int("Votre choix (1 ou 2): ", 1, 2)


def load_ai_model(path: str):
    """Charge un modèle IA depuis un fichier JSON. Retourne le strategy ou None."""
    try:
        return GeneticTrainer.load_ai(path)
    except (FileNotFoundError, KeyError, Exception) as e:
        print(f"Erreur: impossible de charger '{path}' ({e})")
        return None


def setup_players(nb: int):
    """Configure chaque joueur (humain ou IA). Retourne (names, strategies)."""
    names = []
    strategies = []

    for i in range(nb):
        while True:
            choice = input(f"\nJoueur {i + 1} — humain (H) ou IA (I)? ").strip().upper()
            if choice in ("H", "I"):
                break
            print("Veuillez répondre H ou I.")

        if choice == "H":
            name = input("  Nom: ").strip() or f"Joueur {i + 1}"
            names.append(name)
            strategies.append(None)
        else:
            # IA : demander le chemin du modèle, boucle tant que invalide
            while True:
                path = input(f"  Chemin du modèle IA (défaut: {DEFAULT_MODEL}): ").strip()
                path = path or DEFAULT_MODEL
                strategy = load_ai_model(path)
                if strategy is not None:
                    break
                print("  Veuillez réessayer avec un chemin valide.")

            filename = os.path.basename(path)
            names.append(f"IA({filename})")
            strategies.append(strategy)

    return names, strategies


if __name__ == "__main__":
    print("Bienvenue dans le jeu de Skyjo!")

    mode = ask_mode()

    if mode == 1:
        # Mode humains uniquement (comportement original)
        nb_players = ask_int("Combien de joueurs? (2-8): ", 2, 8)
        player_names = []
        for i in range(nb_players):
            name = input(f"Nom du joueur {i + 1}: ").strip() or f"Joueur {i + 1}"
            player_names.append(name)
        game = SkyjoGame(player_names)
        game.play_full_game()

    else:
        # Mode avec IA
        nb_players = ask_int("Combien de joueurs au total? (2-8): ", 2, 8)
        player_names, strategies = setup_players(nb_players)
        game = SkyjoGame(player_names, strategies=strategies)
        game.play_full_game()
