import random
from typing import List, Optional
from ..models.card import Card
from ..models.player import Player
from ..utils.display import display_board, display_game_state, convert_coordinates

class SkyjoGame:
    def __init__(self, player_names: List[str]):
        if not (2 <= len(player_names) <= 8):
            raise ValueError("Le nombre de joueurs doit être entre 2 et 8")
        
        # Initialisation des joueurs
        self.players = [Player(name) for name in player_names]
        
        # Création et mélange du deck
        self.deck: List[Card] = []
        self.create_deck()
        random.shuffle(self.deck)
        
        # Pile de défausse
        self.discard_pile: List[Card] = []
        
        # État du jeu
        self.current_player_index = 0
        
        # Distribution initiale des cartes (sans révélation automatique)
        self.deal_initial_cards()
        
        # Phase d'initialisation où chaque joueur choisit ses cartes
        self.initial_card_selection()

        # Déterminer le premier joueur
        self.determine_first_player()

        self.first_to_finish = None  # Pour tracker qui finit en premier
        self.total_scores = {name: 0 for name in player_names}  # Scores cumulés
        self.last_round_starter_index = None
    
    def play_full_game(self):
        """Joue une partie complète jusqu'à ce qu'un joueur dépasse 100 points."""
        round_number = 1
        while True:
            print(f"\n=== Début de la manche {round_number} ===")
            self.play_game()
            if any(score >= 100 for score in self.total_scores.values()):
                break
            round_number += 1
            # Réinitialisation pour la prochaine manche
            self.__init__([player.name for player in self.players])
        
    def play_game(self):
        """Boucle principale du jeu"""
        # Première carte de la défausse
        first_card = self.deck.pop()
        first_card.visible = True
        self.discard_pile.append(first_card)
        
        last_round = False
        players_to_play = set()  # Pour suivre qui doit jouer son dernier tour
        
        while self.deck:
            current_player = self.players[self.current_player_index]
            print(f"\n=== Tour de {current_player.name} ===")
            
            # Si on est dans le dernier tour et ce joueur a déjà joué, on passe
            if last_round and current_player not in players_to_play:
                self.current_player_index = (self.current_player_index + 1) % len(self.players)
                continue
                
            # Jouer le tour
            display_game_state(len(self.deck), self.discard_pile[-1], self.players, current_player)
            drawn_card = self.player_draw_phase(current_player)
            if drawn_card is not None:
                self.player_placement_phase(current_player, drawn_card)
                
            # Vérifier si le joueur vient de terminer son plateau
            if current_player.all_cards_visible() and not last_round:
                print(f"\n{current_player.name} a révélé toutes ses cartes! Dernier tour pour les autres joueurs!")
                self.first_to_finish = current_player
                last_round = True
                # Tous les autres joueurs doivent jouer une dernière fois
                players_to_play = {p for p in self.players if p != current_player}
            
            # Si on est dans le dernier tour, retirer ce joueur de la liste
            if last_round and current_player in players_to_play:
                players_to_play.remove(current_player)
                
            # Si plus personne n'a à jouer dans le dernier tour, on arrête
            if last_round and not players_to_play:
                print("\nTous les joueurs ont joué leur dernier tour!")
                break
                
            # Passer au joueur suivant
            self.current_player_index = (self.current_player_index + 1) % len(self.players)

        # Fin de la manche et calcul des scores
        self.end_round()

    def create_deck(self):
        # Création des cartes selon les règles du Skyjo
        card_distribution = {
            -2: 5, -1: 10, 0: 15,
            1: 10, 2: 10, 3: 10, 4: 10,
            5: 10, 6: 10, 7: 10, 8: 10,
            9: 10, 10: 10, 11: 10, 12: 10
        }
        for value, count in card_distribution.items():
            self.deck.extend([Card(value) for _ in range(count)])
    
    def deal_initial_cards(self):
        # Distribution de 12 cartes à chaque joueur (sans révélation)
        for player in self.players:
            player.board = [
                [self.deck.pop() for _ in range(4)]
                for _ in range(3)
            ]
    
    def initial_card_selection(self):
        """Phase où chaque joueur choisit ses deux cartes initiales à révéler."""
        for player in self.players:
            print(f"\n{player.name}, c'est à vous de choisir vos deux cartes initiales.")
            
            # Révélation des deux premières cartes
            for i in range(2):
                print(f"\nSélection de la carte {i + 1}/2")
                self.reveal_one_card(player)
    
    def determine_first_player(self):
        """Détermine le premier joueur basé sur la somme de ses cartes visibles."""
        max_sum = float('-inf')
        first_player_index = 0
        
        for i, player in enumerate(self.players):
            visible_sum = sum(card.value for row in player.board 
                            for card in row if card.visible)
            if visible_sum > max_sum:
                max_sum = visible_sum
                first_player_index = i
        
        self.current_player_index = first_player_index
        print(f"\n{self.players[first_player_index].name} commence la partie!")
            
    def reveal_one_card(self, player: Player):
        """Permet au joueur de révéler une de ses cartes cachées."""
        print("\nVous devez révéler une de vos cartes cachées.")
        display_board(player)
        
        while True:
            try:
                coord = input("Quelle carte voulez-vous révéler (ex: A1)? ")
                row, col = convert_coordinates(coord)  # Au lieu de self.convert_coordinates
                
                if player.board[row][col] is None:
                    print("Cette case est vide!")
                    continue
                
                if player.board[row][col].visible:
                    print("Cette carte est déjà visible!")
                    continue
                
                # Révéler la carte
                player.board[row][col].visible = True
                print(f"Vous avez révélé un {player.board[row][col].value}")
                break
                
            except (ValueError, IndexError) as e:
                print(str(e))
    
    def player_placement_phase(self, player: Player, card: Card):
        """Phase où le joueur place sa carte"""
        print(f"\nVous avez la carte: {card.value}")
        display_board(player)
        
        while True:
            try:
                coord = input("Choisissez une position (ex: A1, B2, C3): ").strip()
                row, col = convert_coordinates(coord)
                
                if player.board[row][col] is None:
                    print("Cette position est vide!")
                    continue
                    
                # Échange des cartes
                old_card = player.board[row][col]
                old_card.visible = True
                player.board[row][col] = card
                self.discard_pile.append(old_card)
                print(f"Carte {old_card.value} révélée et défaussée.")
                break
            except ValueError as e:
                print(str(e))
    
    def is_game_over(self) -> bool:
        """Vérifie si la partie est terminée"""
        if not self.deck:
            print("\nPlus de cartes dans le deck!")
            return True
        
        # La partie est terminée si tous les joueurs ont fini
        if all(player.has_finished for player in self.players):
            print("\nTous les joueurs ont joué leur dernier tour!")
            return True
        
        return False
    
    def player_draw_phase(self, player: Player) -> Optional[Card]:
        """Phase où le joueur choisit de piocher ou prendre la défausse"""
        top_discard = self.discard_pile[-1]
        print(f"\nCarte visible de la défausse: {top_discard.value}")
        
        while True:
            choice = input("Voulez-vous piocher (P) ou prendre la défausse (D)? ").upper()
            if choice == 'P':
                card = self.deck.pop()
                card.visible = True
                print(f"Vous avez pioché un {card.value}")
                
                # Choix de garder ou défausser la carte piochée
                keep_choice = input("Voulez-vous garder cette carte (G) ou la défausser (D)? ").upper()
                if keep_choice == 'G':  # <-- Changé de 'P' à 'G'
                    return card
                else:
                    self.discard_pile.append(card)
                    print(f"La carte {card.value} a été défaussée.")
                    # Le joueur doit révéler une de ses cartes
                    self.reveal_one_card(player)
                    return None
            elif choice == 'D':
                return self.discard_pile.pop()

    def check_complete_columns(self, player: Player):
        """Vérifie et traite les colonnes complètes"""
        for col in range(4):
            column = [player.board[row][col] for row in range(3)]
            
            # Si un élément est None, on passe à la colonne suivante
            if any(card is None for card in column):
                continue
            
            try:
                if (all(card is not None for card in column) and  # Pas de None
                    all(card.visible for card in column) and      # Toutes visibles
                    all(card.value == column[0].value for card in column)):  # Même valeur
                    print(f"\nColonne {col + 1} complète avec des {column[0].value}!")
                    # Défausse des cartes
                    for row in range(3):
                        self.discard_pile.append(player.board[row][col])
                        player.board[row][col] = None
            except AttributeError:
                continue  # Si erreur, on passe simplement à la colonne suivante

    def calculate_current_score(self, player: Player) -> int:
        """Calcule le score actuel en ignorant les cases vides."""
        score = 0
        for row in player.board:
            for card in row:
                if card is not None and card.visible:
                    score += card.value
        return score

    def calculate_final_score(self, player: Player) -> int:
        """Calcule le score final en incluant les cartes non révélées"""
        score = 0
        for row in player.board:
            for card in row:
                if card is None:  # Case vide (colonne complétée)
                    continue
                if not card.visible:
                    # Révéler la carte
                    card.visible = True
                score += card.value
        return score
    
    def end_round(self):
        """Gère la fin de la manche et le calcul des scores."""
        print("\n=== Fin de la manche ===")
        
        # Calcul des scores finaux
        round_scores = {}
        for player in self.players:
            score = self.calculate_final_score(player)
            round_scores[player.name] = score
            print(f"Score de {player.name}: {score}")
        
        # Vérification de la règle du doublement
        if self.first_to_finish:
            min_score = min(round_scores.values())
            first_player_score = round_scores[self.first_to_finish.name]
            
            if first_player_score > min_score and first_player_score > 0:
                print(f"\n{self.first_to_finish.name} a fini premier mais n'a pas le plus petit score!")
                print(f"Son score est doublé: {first_player_score} → {first_player_score * 2}")
                round_scores[self.first_to_finish.name] *= 2
        
        # Mise à jour des scores totaux
        game_over = False
        for name, score in round_scores.items():
            self.total_scores[name] += score
            if self.total_scores[name] >= 100:
                game_over = True
        
        # Affichage des scores totaux
        print("\n=== Scores totaux ===")
        for name, total in self.total_scores.items():
            print(f"{name}: {total}")
        
        if game_over:
            print("\nUn joueur a dépassé 100 points, la partie est terminée!")
            winner = min(self.total_scores.items(), key=lambda x: x[1])
            print(f"\nLe gagnant est {winner[0]} avec {winner[1]} points!")
        else:
            print("\nPrêt pour la prochaine manche!")
            return False
        
        return True



