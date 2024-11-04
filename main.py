from src.game.skyjo import SkyjoGame
from src.ai.trainer import GeneticTrainer

if __name__ == "__main__":
    # Mode normal
    print("Bienvenue dans le jeu de Skyjo!")
    while True:
        try:
            nb_players = int(input("Combien de joueurs? (2-8): "))
            if 2 <= nb_players <= 8:
                break
            print("Le nombre de joueurs doit être entre 2 et 8")
        except ValueError:
            print("Veuillez entrer un nombre valide")
    
    player_names = []
    for i in range(nb_players):
        name = input(f"Nom du joueur {i+1}: ")
        player_names.append(name)
    
    game = SkyjoGame(player_names)
    game.play_full_game()

    # Mode entrainement IA
    # trainer = GeneticTrainer()
    # best_ai = trainer.train_ai(generations=100)