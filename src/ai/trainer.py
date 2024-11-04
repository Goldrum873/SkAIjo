from typing import List, Tuple
import random
from .genes import AIGenes
from .genetic import GeneticAIStrategy
from ..game.skyjo import SkyjoGame

class GeneticTrainer:
    def __init__(self, population_size: int = 100, players_per_game: int = 8):
        self.population_size = population_size
        self.players_per_game = players_per_game
        self.population = [GeneticAIStrategy() for _ in range(population_size)]
        self.generation = 0
    
    def run_tournament(self, games_per_ai: int = 10):
        """Fait jouer toutes les IA entre elles"""
        for _ in range(games_per_ai * self.population_size // self.players_per_game):
            # Sélection aléatoire des joueurs pour une partie
            players = random.sample(self.population, self.players_per_game)
            
            # Création et exécution de la partie
            game = SkyjoGame([f"AI_{id(ai)}" for ai in players])
            for player, ai in zip(game.players, players):
                player.strategy = ai
            
            # Jouer la partie
            rankings = game.play_full_game(training_mode=True)
            
            # Mise à jour des scores de fitness
            for rank, (player_name, score) in enumerate(rankings):
                ai_index = next(i for i, ai in enumerate(players) 
                              if f"AI_{id(ai)}" == player_name)
                ai = players[ai_index]
                ai.games_played += 1
                ai.rankings.append(rank)
                # Score de fitness inversement proportionnel au classement
                ai.fitness_score += (self.players_per_game - rank) / self.players_per_game
    
    def evolve(self, elite_percentage: float = 0.1, mutation_rate: float = 0.1):
        """Fait évoluer la population en gardant les meilleures IA"""
        # Trier la population par fitness score
        self.population.sort(key=lambda ai: ai.fitness_score, reverse=True)
        
        # Garder l'élite
        elite_size = int(self.population_size * elite_percentage)
        new_population = self.population[:elite_size]
        
        # Créer de nouvelles IA par reproduction et mutation
        while len(new_population) < self.population_size:
            parent1, parent2 = random.sample(self.population[:elite_size*2], 2)
            # Crossover (moyenne des gènes)
            child_genes = AIGenes(
                value_weight=(parent1.genes.value_weight + parent2.genes.value_weight) / 2,
                risk_weight=(parent1.genes.risk_weight + parent2.genes.risk_weight) / 2,
                column_weight=(parent1.genes.column_weight + parent2.genes.column_weight) / 2,
                hidden_penalty=(parent1.genes.hidden_penalty + parent2.genes.hidden_penalty) / 2
            )
            child = GeneticAIStrategy(child_genes)
            # Mutation
            if random.random() < mutation_rate:
                child = child.mutate(mutation_rate)
            new_population.append(child)
        
        self.population = new_population
        self.generation += 1

    def train_ai(self, generations: int = 100):
        for gen in range(generations):
            print(f"\nGénération {gen + 1}/{generations}")
            self.run_tournament(games_per_ai=10)
            
            # Afficher les statistiques de la meilleure IA
            best_ai = max(self.population, key=lambda ai: ai.fitness_score)
            print(f"Meilleure IA - Fitness: {best_ai.fitness_score:.2f}")
            print(f"Gènes: {best_ai.genes}")
            
            self.evolve()
        
        return self.population[0]  # Retourne la meilleure IA