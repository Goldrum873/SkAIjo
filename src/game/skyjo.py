import random
from typing import List, Optional, Tuple
from ..models.card import Card
from ..models.player import Player
from ..utils.display import display_board, display_game_state, convert_coordinates
from ..ai.context import GameContext, OpponentInfo

class SkyjoGame:
    def __init__(self, player_names: List[str], silent: bool = False, strategies: Optional[list] = None):
        if not (2 <= len(player_names) <= 8):
            raise ValueError("Le nombre de joueurs doit être entre 2 et 8")

        self.silent = silent

        # Initialisation des joueurs (avec strategies optionnelles)
        strats = strategies or [None] * len(player_names)
        self.players = [Player(name, strategy=s) for name, s in zip(player_names, strats)]
        
        # Création et mélange du deck
        self.deck: List[Card] = []
        self.create_deck()
        random.shuffle(self.deck)
        
        # Pile de défausse
        self.discard_pile: List[Card] = []
        
        # État du jeu
        self.current_player_index = 0
        self.first_to_finish = None
        self.total_scores = {name: 0 for name in player_names}
        self._turn_number = 0
        self._round_number = 1

        # Distribution initiale des cartes (sans révélation automatique)
        self.deal_initial_cards()

        # Phase d'initialisation où chaque joueur choisit ses cartes
        self.initial_card_selection()

        # Déterminer le premier joueur
        self.determine_first_player()

    def _print(self, *args, **kwargs):
        """Print uniquement en mode non-silent (partie humaine)."""
        if not self.silent:
            print(*args, **kwargs)

    def _build_context(self, player: Player) -> GameContext:
        """Construit le snapshot du jeu pour une decision IA."""
        player_idx = self.players.index(player)
        n = len(self.players)

        # Adversaires ordonnes par tour (prochain joueur en premier)
        opponents = []
        for offset in range(1, n):
            opp = self.players[(player_idx + offset) % n]
            vis_score = 0
            hidden = 0
            board_rows = []
            for row in opp.board:
                row_tuple = []
                for card in row:
                    if card is not None:
                        if card.visible:
                            vis_score += card.value
                        else:
                            hidden += 1
                    row_tuple.append(card)
                board_rows.append(tuple(row_tuple))
            opponents.append(OpponentInfo(
                name=opp.name,
                visible_score=vis_score,
                hidden_count=hidden,
                board=tuple(board_rows),
                total_score=self.total_scores.get(opp.name, 0),
            ))

        # Score visible et cartes cachees du joueur actif
        my_vis = 0
        my_hidden = 0
        for row in player.board:
            for card in row:
                if card is not None:
                    if card.visible:
                        my_vis += card.value
                    else:
                        my_hidden += 1

        opp_vis_scores = [o.visible_score for o in opponents] or [0]
        opp_hidden_counts = [o.hidden_count for o in opponents] or [0]

        return GameContext(
            deck_size=len(self.deck),
            discard_pile_size=len(self.discard_pile),
            turn_number=self._turn_number,
            my_total_score=self.total_scores.get(player.name, 0),
            round_number=self._round_number,
            opponents=tuple(opponents),
            is_last_round=self.first_to_finish is not None,
            finisher_name=self.first_to_finish.name if self.first_to_finish else None,
            min_opponent_visible_score=min(opp_vis_scores),
            min_opponent_hidden_count=min(opp_hidden_counts),
            my_visible_score=my_vis,
            my_hidden_count=my_hidden,
        )

    def reset_round(self):
        """Réinitialise le jeu pour une nouvelle manche, en préservant les scores."""
        self.deck = []
        self.create_deck()
        random.shuffle(self.deck)
        self.discard_pile = []
        self.first_to_finish = None
        self._turn_number = 0
        self._round_number += 1

        for player in self.players:
            player.score = 0

        self.deal_initial_cards()
        self.initial_card_selection()
        self.determine_first_player()

    def play_full_game(self) -> List[Tuple[str, int]]:
        """Joue une partie complète et retourne le classement (nom, score) trié par score croissant."""
        round_number = 1
        while True:
            self._print(f"\n=== Début de la manche {round_number} ===")
            self.play_game()
            if any(score >= 100 for score in self.total_scores.values()):
                break
            round_number += 1
            self.reset_round()

        return sorted(self.total_scores.items(), key=lambda x: x[1])
        
    def play_game(self):
        """Boucle principale du jeu"""
        # Première carte de la défausse
        first_card = self.deck.pop()
        first_card.visible = True
        self.discard_pile.append(first_card)
        
        last_round = False
        players_to_play = set()  # Pour suivre qui doit jouer son dernier tour
        max_turns = 200  # Securite contre les boucles infinies
        turn = 0

        while self.deck and turn < max_turns:
            turn += 1
            current_player = self.players[self.current_player_index]
            self._print(f"\n=== Tour de {current_player.name} ===")
            
            # Si on est dans le dernier tour et ce joueur a déjà joué, on passe
            if last_round and current_player not in players_to_play:
                self.current_player_index = (self.current_player_index + 1) % len(self.players)
                continue
                
            self._turn_number = turn

            # Jouer le tour
            if not self.silent:
                display_game_state(len(self.deck), self.discard_pile[-1], self.players, current_player)
            drawn_card, ctx = self.player_draw_phase(current_player)
            if drawn_card is not None:
                self.player_placement_phase(current_player, drawn_card, ctx)

            # Vérifier les colonnes complètes (3 cartes identiques)
            self.check_complete_columns(current_player)

            # Vérifier si le joueur vient de terminer son plateau
            if current_player.all_cards_visible() and not last_round:
                self._print(f"\n{current_player.name} a révélé toutes ses cartes! Dernier tour pour les autres joueurs!")
                self.first_to_finish = current_player
                last_round = True
                # Tous les autres joueurs doivent jouer une dernière fois
                players_to_play = {p for p in self.players if p != current_player}
            
            # Si on est dans le dernier tour, retirer ce joueur de la liste
            if last_round and current_player in players_to_play:
                players_to_play.remove(current_player)
                
            # Si plus personne n'a à jouer dans le dernier tour, on arrête
            if last_round and not players_to_play:
                self._print("\nTous les joueurs ont joué leur dernier tour!")
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
            if player.strategy:
                ctx = self._build_context(player)
                positions = player.strategy.choose_initial_cards(player.board, ctx)
                for row, col in positions:
                    player.board[row][col].visible = True
                continue

            self._print(f"\n{player.name}, c'est à vous de choisir vos deux cartes initiales.")

            # Révélation des deux premières cartes
            for i in range(2):
                self._print(f"\nSélection de la carte {i + 1}/2")
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
        self._print(f"\n{self.players[first_player_index].name} commence la partie!")
            
    def reveal_one_card(self, player: Player, ctx=None):
        """Permet au joueur de révéler une de ses cartes cachées."""
        if player.strategy:
            row, col = player.strategy.choose_card_to_reveal(player.board, ctx)
            player.board[row][col].visible = True
            coord = f"{chr(65 + row)}{col + 1}"
            self._print(f"{player.name} révèle la carte en {coord}: {player.board[row][col].value}.")
            return

        self._print("\nVous devez révéler une de vos cartes cachées.")
        if not self.silent:
            display_board(player)

        while True:
            try:
                coord = input("Quelle carte voulez-vous révéler (ex: A1)? ")
                row, col = convert_coordinates(coord)  # Au lieu de self.convert_coordinates
                
                if player.board[row][col] is None:
                    self._print("Cette case est vide!")
                    continue

                if player.board[row][col].visible:
                    self._print("Cette carte est déjà visible!")
                    continue

                # Révéler la carte
                player.board[row][col].visible = True
                self._print(f"Vous avez révélé un {player.board[row][col].value}")
                break
                
            except (ValueError, IndexError) as e:
                self._print(str(e))
    
    def player_placement_phase(self, player: Player, card: Card, ctx=None):
        """Phase où le joueur place sa carte"""
        if player.strategy:
            row, col = player.strategy.choose_card_position(card, player.board, ctx)
            old_card = player.board[row][col]
            old_card.visible = True
            player.board[row][col] = card
            self.discard_pile.append(old_card)
            coord = f"{chr(65 + row)}{col + 1}"
            self._print(f"{player.name} place le {card.value} en {coord}, remplace un {old_card.value}.")
            if not self.silent:
                display_board(player)
            return

        self._print(f"\nVous avez la carte: {card.value}")
        if not self.silent:
            display_board(player)

        while True:
            try:
                coord = input("Choisissez une position (ex: A1, B2, C3): ").strip()
                row, col = convert_coordinates(coord)

                if player.board[row][col] is None:
                    self._print("Cette position est vide!")
                    continue

                # Échange des cartes
                old_card = player.board[row][col]
                old_card.visible = True
                player.board[row][col] = card
                self.discard_pile.append(old_card)
                self._print(f"Carte {old_card.value} révélée et défaussée.")
                break
            except ValueError as e:
                self._print(str(e))
    
    def player_draw_phase(self, player: Player) -> Tuple[Optional[Card], Optional[GameContext]]:
        """Phase où le joueur choisit de piocher ou prendre la défausse.

        Returns (card_to_place, ctx) — ctx is forwarded to placement phase.
        """
        top_discard = self.discard_pile[-1]

        if player.strategy:
            ctx = self._build_context(player)
            choice = player.strategy.choose_draw_or_discard(top_discard, player.board, ctx)
            if choice == 'P':
                card = self.deck.pop()
                card.visible = True
                self._print(f"{player.name} pioche une carte...")
                keep = player.strategy.choose_keep_or_discard(card, player.board, ctx)
                if keep == 'G':
                    self._print(f"{player.name} garde la carte piochée ({card.value}).")
                    return card, ctx
                self.discard_pile.append(card)
                self._print(f"{player.name} défausse la carte piochée ({card.value}).")
                self.reveal_one_card(player, ctx)
                return None, ctx
            # choice == 'D'
            taken = self.discard_pile.pop()
            self._print(f"{player.name} prend dans la défausse ({taken.value}).")
            return taken, ctx

        self._print(f"\nCarte visible de la défausse: {top_discard.value}")

        while True:
            choice = input("Voulez-vous piocher (P) ou prendre la défausse (D)? ").upper()
            if choice == 'P':
                card = self.deck.pop()
                card.visible = True
                self._print(f"Vous avez pioché un {card.value}")

                # Choix de garder ou défausser la carte piochée
                keep_choice = input("Voulez-vous garder cette carte (G) ou la défausser (D)? ").upper()
                if keep_choice == 'G':
                    return card, None
                else:
                    self.discard_pile.append(card)
                    self._print(f"La carte {card.value} a été défaussée.")
                    # Le joueur doit révéler une de ses cartes
                    self.reveal_one_card(player)
                    return None, None
            elif choice == 'D':
                return self.discard_pile.pop(), None

    def check_complete_columns(self, player: Player):
        """Vérifie et supprime les colonnes de 3 cartes identiques visibles."""
        for col in range(4):
            column = [player.board[row][col] for row in range(3)]

            if any(card is None for card in column):
                continue
            if not all(card.visible for card in column):
                continue
            if not all(card.value == column[0].value for card in column):
                continue

            self._print(f"\nColonne {col + 1} complète avec des {column[0].value}!")
            for row in range(3):
                self.discard_pile.append(player.board[row][col])
                player.board[row][col] = None

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
        self._print("\n=== Fin de la manche ===")

        # Calcul des scores finaux
        round_scores = {}
        for player in self.players:
            score = self.calculate_final_score(player)
            round_scores[player.name] = score
            self._print(f"Score de {player.name}: {score}")

        # Vérification de la règle du doublement
        # Le finisseur doit avoir STRICTEMENT le plus petit score, sinon doublement
        if self.first_to_finish:
            first_player_score = round_scores[self.first_to_finish.name]
            other_scores = [s for name, s in round_scores.items()
                           if name != self.first_to_finish.name]
            min_other_score = min(other_scores)

            if first_player_score >= min_other_score and first_player_score > 0:
                self._print(f"\n{self.first_to_finish.name} a fini premier mais n'a pas le plus petit score!")
                self._print(f"Son score est doublé: {first_player_score} → {first_player_score * 2}")
                round_scores[self.first_to_finish.name] *= 2

        # Mise à jour des scores totaux
        game_over = False
        for name, score in round_scores.items():
            self.total_scores[name] += score
            if self.total_scores[name] >= 100:
                game_over = True

        # Affichage des scores totaux
        self._print("\n=== Scores totaux ===")
        for name, total in self.total_scores.items():
            self._print(f"{name}: {total}")

        if game_over:
            self._print("\nUn joueur a dépassé 100 points, la partie est terminée!")
            winner = min(self.total_scores.items(), key=lambda x: x[1])
            self._print(f"\nLe gagnant est {winner[0]} avec {winner[1]} points!")
        else:
            self._print("\nPrêt pour la prochaine manche!")
            return False

        return True



