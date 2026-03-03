from typing import List
from dataclasses import fields
from datetime import datetime
import csv
import json
import os
import random
from .genes import AIGenes
from .genetic import GeneticAIStrategy
from ..game.skyjo import SkyjoGame

_ADJECTIVES = [
    "Bold", "Calm", "Clever", "Crafty", "Daring",
    "Eager", "Fierce", "Gentle", "Grim", "Hardy",
    "Icy", "Jolly", "Keen", "Lucky", "Mad",
    "Noble", "Proud", "Quick", "Rash", "Shy",
    "Sly", "Swift", "Tame", "Vain", "Wild",
    "Wise", "Zen", "Zany", "Chill", "Snappy",
]

_NOUNS = [
    "Bear", "Cobra", "Dragon", "Eagle", "Fox",
    "Goat", "Hawk", "Jackal", "Koi", "Lion",
    "Moose", "Newt", "Owl", "Panda", "Quail",
    "Raven", "Shark", "Tiger", "Viper", "Wolf",
    "Yak", "Zebra", "Lynx", "Otter", "Puma",
    "Crane", "Falcon", "Squid", "Ibis", "Mantis",
]


def generate_agent_name(players: int, generations: int) -> str:
    """Genere un nom d'agent style Reddit : AdjectifAnimal-Xp-genY."""
    adj = random.choice(_ADJECTIVES)
    noun = random.choice(_NOUNS)
    return f"{adj}{noun}-{players}p-gen{generations}"


class GeneticTrainer:
    def __init__(self, population_size: int = 100, players_per_game: int = 8):
        self.population_size = population_size
        self.players_per_game = players_per_game
        self.population = [GeneticAIStrategy() for _ in range(population_size)]
        self.generation = 0
        # Snapshot du meilleur AI (avant reset fitness)
        self._best_genes: AIGenes | None = None
        self._best_fitness: float = 0.0

    # ── Tournament ────────────────────────────────────────

    def run_tournament(self, games_per_ai: int = 10):
        """Fait jouer toutes les IA entre elles."""
        num_games = games_per_ai * self.population_size // self.players_per_game
        for _ in range(num_games):
            players = random.sample(self.population, self.players_per_game)

            game = SkyjoGame(
                [f"AI_{id(ai)}" for ai in players],
                silent=True,
                strategies=players,
            )

            rankings = game.play_full_game()

            for rank, (player_name, score) in enumerate(rankings):
                ai_index = next(
                    i for i, ai in enumerate(players)
                    if f"AI_{id(ai)}" == player_name
                )
                ai = players[ai_index]
                ai.games_played += 1
                ai.rankings.append(rank)
                ai.fitness_score += (self.players_per_game - rank) / self.players_per_game

    # ── Evolution ─────────────────────────────────────────

    def evolve(self, elite_percentage: float = 0.1, mutation_rate: float = 0.1):
        """Fait evoluer la population (uniform crossover + mutation + clamping)."""
        self.population.sort(key=lambda ai: ai.fitness_score, reverse=True)

        elite_size = max(2, int(self.population_size * elite_percentage))
        new_population: List[GeneticAIStrategy] = self.population[:elite_size]

        # Pool de parents = top 2x elite
        parent_pool = self.population[:elite_size * 2]

        while len(new_population) < self.population_size:
            parent1, parent2 = random.sample(parent_pool, 2)
            # Uniform crossover: chaque gene est pris au hasard d'un parent
            child_values = {}
            for f in fields(AIGenes):
                child_values[f.name] = random.choice([
                    getattr(parent1.genes, f.name),
                    getattr(parent2.genes, f.name),
                ])
            child = GeneticAIStrategy(AIGenes(**child_values))
            # Mutation probabiliste
            if random.random() < mutation_rate:
                child = child.mutate(mutation_rate)
            new_population.append(child)

        self.population = new_population
        self.generation += 1

        # Reset fitness pour la prochaine generation
        for ai in self.population:
            ai.fitness_score = 0
            ai.games_played = 0
            ai.rankings = []

    # ── Training loop ─────────────────────────────────────

    def train_ai(
        self,
        generations: int = 100,
        log_path: str | None = None,
    ):
        """Boucle d'entrainement avec logging console + CSV optionnel."""
        gene_names = [f.name for f in fields(AIGenes)]

        # Initialiser le CSV si demande
        csv_file = None
        csv_writer = None
        if log_path:
            csv_file = open(log_path, "w", newline="")
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(
                ["generation", "best_fitness", "avg_fitness"] + gene_names
            )

        try:
            for gen in range(generations):
                self.run_tournament(games_per_ai=10)

                # Stats de la generation
                best_ai = max(self.population, key=lambda ai: ai.fitness_score)
                avg_fitness = sum(ai.fitness_score for ai in self.population) / len(self.population)

                # Logging console
                genes_str = ", ".join(
                    f"{name}={getattr(best_ai.genes, name):.2f}"
                    for name in gene_names
                )
                print(
                    f"Gen {gen + 1:>3}/{generations} | "
                    f"best={best_ai.fitness_score:.2f} avg={avg_fitness:.2f} | "
                    f"{genes_str}"
                )

                # Logging CSV
                if csv_writer:
                    gene_values = [getattr(best_ai.genes, n) for n in gene_names]
                    csv_writer.writerow(
                        [gen + 1, f"{best_ai.fitness_score:.4f}", f"{avg_fitness:.4f}"]
                        + [f"{v:.4f}" for v in gene_values]
                    )

                # Snapshot du meilleur avant reset
                self._best_genes = AIGenes.from_dict(best_ai.genes.to_dict())
                self._best_fitness = best_ai.fitness_score

                self.evolve()
        finally:
            if csv_file:
                csv_file.close()

        # Apres la derniere evolve(), la fitness est reset
        # → re-trier par la fitness de la derniere generation n'est plus possible
        # → le best est le premier (elite) de la derniere evolve
        return self.population[0]

    # ── Save / Load ───────────────────────────────────────

    def save_best(self, filepath: str, generations: int | None = None, agent_name: str | None = None):
        """Sauvegarde les genes du meilleur AI en JSON (format v2)."""
        gen_count = generations or self.generation
        agent_id = agent_name or generate_agent_name(self.players_per_game, gen_count)

        data = {
            "version": 2,
            "agent_id": agent_id,
            "generation": self.generation,
            "fitness_score": self._best_fitness,
            "training_config": {
                "players_per_game": self.players_per_game,
                "population_size": self.population_size,
                "generations": gen_count,
            },
            "genes": (self._best_genes or self.population[0].genes).to_dict(),
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def load_ai(filepath: str) -> GeneticAIStrategy:
        """Charge un GeneticAIStrategy depuis un fichier JSON (v1 et v2)."""
        with open(filepath) as f:
            data = json.load(f)
        genes = AIGenes.from_dict(data["genes"])
        return GeneticAIStrategy(genes)

    @staticmethod
    def load_agent_metadata(filepath: str) -> dict:
        """Retourne les metadonnees d'un agent (id, filepath, training_config)."""
        with open(filepath) as f:
            data = json.load(f)

        # v2 : metadonnees completes
        if data.get("version", 1) >= 2:
            return {
                "agent_id": data["agent_id"],
                "filepath": filepath,
                "training_config": data["training_config"],
            }

        # v1 : genere un id a partir du nom de fichier
        basename = os.path.splitext(os.path.basename(filepath))[0]
        return {
            "agent_id": basename,
            "filepath": filepath,
            "training_config": {},
        }
