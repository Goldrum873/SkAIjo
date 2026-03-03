# SkAIjo

Implementation Python du jeu de cartes **Skyjo** avec deux approches d'IA : algorithme genetique et arbres gradient-boostes (self-play).

## Presentation

Skyjo est un jeu de cartes (2-8 joueurs) ou l'objectif est d'obtenir le score le plus bas possible. Les joueurs gerent un plateau de 12 cartes (3x4), echangent des cartes avec la pioche ou la defausse, et tentent de completer des colonnes identiques pour les eliminer.

Ce projet propose :

- une implementation complete des regles du Skyjo,
- un mode humain (en ligne de commande),
- une IA pilotee par 15 genes evolues via un algorithme genetique (dont 5 genes contextuels),
- une IA par arbres gradient-boostes (GBT) entrainee par self-play iteratif,
- des outils d'analyse pour comprendre les strategies apprises,
- une arena ELO pour confronter les agents (genetiques et GBT) et mesurer leur force.

## Installation

```bash
python -m venv venv
source venv/bin/activate   # Linux/macOS
venv\Scripts\activate      # Windows

pip install -r requirements.txt
```

## Utilisation

### Jouer une partie

```bash
python main.py
```

Deux modes disponibles :

1. **Partie entre humains** — chaque joueur joue a son tour via le terminal.
2. **Partie avec IA** — melange joueurs humains et IA pre-entrainees.

### Entrainer une IA

```bash
python train.py -n 4 -g 50          # 50 generations, tables de 4 joueurs
python train.py -n 8 -g 100 --csv   # 100 generations, tables de 8, log CSV
```

Chaque agent recoit un nom aleatoire (ex: `BoldFox-4p-gen50`) et est sauvegarde dans `agents/`. Le fichier JSON contient les genes du meilleur individu et peut etre charge en mode jeu.

Options :

| Flag | Description | Defaut |
|---|---|---|
| `-n` / `--players` | Joueurs par partie (2-8) | 8 |
| `-g` / `--generations` | Nombre de generations | 50 |
| `-p` / `--population` | Taille de la population | 100 |
| `-o` / `--output` | Fichier de sortie | `agents/<nom>.json` |
| `--csv` | Log d'entrainement CSV | desactive |

### Analyser les strategies

```bash
python -m src.ai.analysis
```

Affiche le profil strategique et la table de decisions de l'IA entrainee.

## Tests

```bash
pytest -v
```

56 tests couvrant : cartes, joueurs, regles du jeu, genes (backward-compat v1/v2), decisions IA, contexte de jeu, coordonnees, ELO, leaderboard, features GBT, collecteur et strategie tree.

## Arena

Le systeme d'arena confronte les agents et mesure leur force via un classement ELO pairwise. Il faut au moins autant d'agents que de places par table (ex: 4 agents minimum pour `-n 4`).

```bash
python arena.py list                         # lister les agents disponibles
python arena.py simulate -n 4 --games 300    # 300 matchs a tables de 4
```

L'historique ELO est enregistre dans `elo_history.csv` (un snapshot toutes les 50 parties). Format CSV long, plottable directement :

```python
import pandas as pd
df = pd.read_csv("elo_history.csv")
df.pivot(index="match", columns="agent_id", values="global_elo").plot()
```

### Voir le classement

```bash
python arena.py leaderboard          # classement global
python arena.py leaderboard -t 4     # filtre par taille de table
```

### Comparer un agent cross-table

```bash
python arena.py compare <agent_id>
```

## IA contextuelle (v3)

Depuis la version 3, l'IA ne regarde plus uniquement sa propre main. Un `GameContext` est construit a chaque tour et passe a toutes les decisions. Il contient :

- la taille du deck et de la defausse,
- le score visible et les cartes cachees de chaque adversaire (ordonne par tour),
- le score cumule multi-manches,
- le numero de tour et de manche,
- si le dernier tour est en cours et qui l'a declenche.

### Les 15 genes

Les 10 genes originaux (prise de carte, placement, colonnes) sont conserves. 5 genes contextuels s'ajoutent :

| Gene | Range | Role |
|---|---|---|
| `endgame_aggression` | -2 a 2 | Ajuster les seuils quand un adversaire est proche de finir |
| `doubling_caution` | 0 a 3 | Penaliser le fait de finir si risque de doublement |
| `opponent_awareness` | 0 a 2 | Eviter de defausser une carte utile au joueur suivant |
| `score_pressure` | -1 a 1 | Prendre plus de risques quand le score cumule est eleve |
| `deck_urgency` | 0 a 2 | Accepter des cartes moins bonnes quand le deck est bas |

### Backward-compatibilite

Les agents v1/v2 (10 genes) sont charges sans probleme — les 5 genes contextuels sont initialises a `0.0`, ce qui desactive les modificateurs contextuels. Le comportement est strictement identique a l'ancienne version.

## IA par arbres gradient-boostes (GBT)

Approche alternative a l'algorithme genetique. Au lieu de 15 genes ajustes par evolution, le systeme collecte des decisions de jeu en masse et entraine des modeles `HistGradientBoostingRegressor` (scikit-learn) pour predire quel choix mene au score le plus bas.

### Principe

1. **Collecte** — Jouer N parties (self-play), enregistrer chaque decision avec ~50 features (etat du plateau, contexte, carte consideree) et le score de la manche.
2. **Entrainement** — Un modele GBT par type de decision (draw, keep, position, reveal).
3. **Inference** — Pour chaque decision, predire le score de chaque action possible, choisir celle qui minimise le score predit.

### Self-play iteratif

Chaque iteration produit un agent distinct :

- **Iteration 1** : collecte avec IA random, entraine `tree-v1`
- **Iteration 2** : collecte avec tree-v1, entraine `tree-v2`
- **Iteration N** : collecte avec tree-v(N-1), entraine `tree-vN`

Les agents de toutes les iterations coexistent dans `agents/` et se confrontent dans l'arena.

### Entrainer un agent GBT

```bash
python train_tree.py -g 20000 -n 4                  # 1 iteration (tree-v1)
python train_tree.py -g 20000 -n 4 --iterations 3   # 3 iterations (v1, v2, v3)
python train_tree.py -g 50000 -n 4 --iterations 5   # 5 iterations, plus de donnees
```

Options :

| Flag | Description | Defaut |
|---|---|---|
| `-g` / `--games` | Parties par iteration | 20000 |
| `-n` / `--players` | Joueurs par partie (2-8) | 4 |
| `--iterations` | Nombre d'iterations self-play | 1 |
| `--name` | Prefixe de lignee | auto-genere |
| `--agents-dir` | Dossier des agents | `agents/` |

### Structure d'un agent GBT

```
agents/BoldFox-tree-v1-4p/
  metadata.json           # version, type, iteration, metriques, feature_names
  draw_model.joblib       # modele prise de carte
  keep_model.joblib       # modele garder/defausser
  position_model.joblib   # modele placement
  reveal_model.joblib     # modele revelation
```

L'arena detecte automatiquement les deux types d'agents (genetiques en `*.json`, GBT en `*/metadata.json`).

## Structure du projet

```
src/
├── ai/
│   ├── analysis.py    # Analyse et explication des strategies
│   ├── context.py     # GameContext et OpponentInfo (snapshot du jeu)
│   ├── genes.py       # Definition des 15 genes de l'IA
│   ├── genetic.py     # Strategie IA basee sur les genes + contexte
│   ├── strategy.py    # Interface abstraite PlayerStrategy
│   ├── trainer.py     # Entrainement par algorithme genetique
│   └── tree/
│       ├── features.py   # Extraction de ~50 features depuis l'etat de jeu
│       ├── collector.py  # Collecte de decisions via self-play
│       ├── training.py   # Entrainement GBT + sauvegarde agents
│       └── strategy.py   # TreeAIStrategy (inference par modeles)
├── arena/
│   ├── elo.py         # Moteur ELO pairwise (fonctions pures)
│   ├── leaderboard.py # Persistence du classement en JSON
│   └── runner.py      # Execution des matchs (genetique + tree)
├── game/
│   └── skyjo.py       # Moteur de jeu complet
├── models/
│   ├── card.py        # Modele Card (valeur + visibilite)
│   └── player.py      # Modele Player (board 3x4 + score)
└── utils/
    └── display.py     # Affichage console et conversion coordonnees
```

## Regles du Skyjo

Les regles completes sont disponibles dans le fichier [`regles.txt`](regles.txt).

En resume :

- Chaque joueur a un plateau de 12 cartes face cachee (3 lignes x 4 colonnes).
- A chaque tour : piocher ou prendre la defausse, puis echanger une carte du plateau.
- 3 cartes identiques dans une colonne → colonne eliminee (bonus).
- Quand un joueur revele toutes ses cartes, les autres jouent un dernier tour.
- Le finisseur qui n'a pas le score le plus bas voit son score double.
- Premiere partie a 100+ points → fin de la partie, le plus bas score gagne.
