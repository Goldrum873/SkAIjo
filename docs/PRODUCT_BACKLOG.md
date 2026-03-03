# Product Backlog — SkAIjo

> Backlog priorise. Tout nouvel element commence ici.
> Le Planificateur est responsable de la priorisation.

---

## PB-1 — Corriger les regles du jeu ~~(Done — Sprint 1)~~

- Value : Si le moteur est faux, l'IA apprendra des strategies fausses.
- Acceptance Criteria :
  - [x] `check_complete_columns()` appele apres chaque tour
  - [x] Regle du doublement compare aux autres joueurs uniquement
  - [x] `reset_round()` remplace `__init__` re-call entre manches
  - [x] Dead code supprime (`is_game_over`, doublon score, `has_finished`)

---

## PB-2 — Decoupler le moteur de `input()`

- Value : Sans ca, l'IA ne peut pas jouer. Blocage total pour l'entrainement.
- Acceptance Criteria :
  - [ ] Si `player.strategy` existe, appeler la strategy au lieu de `input()`
  - [ ] Mode silencieux (pas de `print()` pendant l'entrainement)
  - [ ] Le moteur peut faire tourner une partie complete sans intervention humaine
  - [ ] Le mode humain existant continue de fonctionner
- Notes : Touche `skyjo.py` (reveal_one_card, player_draw_phase, player_placement_phase, initial_card_selection)

---

## PB-3 — Implementer la logique de decision IA

- Value : Le cerveau de l'IA. Chaque gene = un seuil de decision.
- Acceptance Criteria :
  - [ ] `AIGenes` enrichi (~10-12 genes couvrant toutes les decisions)
  - [ ] Les 5 methodes de `GeneticAIStrategy` implementees et fonctionnelles
  - [ ] Chaque decision utilise les genes + l'etat du plateau
  - [ ] Une partie IA-only tourne sans erreur
- Notes : Genes envisages — seuil de prise defausse, seuil de garde, preference positionnelle, bonus colonne, timing de fermeture, penalite carte cachee, valeur cible de remplacement, etc.

---

## PB-4 — Faire fonctionner le trainer

- Value : C'est lui qui fait evoluer les IA sur des centaines de generations.
- Acceptance Criteria :
  - [ ] Signature `play_full_game` compatible avec le trainer
  - [ ] Crossover par selection de genes (pas par moyenne)
  - [ ] Mutation appliquee par gene (pas globale)
  - [ ] Logging des stats par generation (meilleur fitness, genes, classement moyen)
  - [ ] Sauvegarde/chargement du meilleur modele (JSON)
  - [ ] Un entrainement de 50 generations tourne sans erreur
- Notes : Le trainer doit utiliser le mode silencieux de PB-2.

---

## PB-5 — Analyse et explication des strategies

- Value : Comprendre quelles strategies l'IA a appris. Objectif principal du projet.
- Acceptance Criteria :
  - [ ] Extraire les genes du meilleur AI en regles lisibles (ex: "prendre la defausse si valeur <= 3")
  - [ ] Mode "conseil" : afficher le meilleur coup dans une situation donnee
  - [ ] Rapport de fin d'entrainement avec les tendances observees
- Depends on : PB-4

---

## PB-6 — Mode Humain vs IA

- Value : Jouer contre l'IA entrainee pour valider ses strategies.
- Acceptance Criteria :
  - [ ] Charger un modele entraine depuis un fichier JSON
  - [ ] Mixer joueurs humains et IA dans une meme partie
  - [ ] L'IA joue ses tours automatiquement pendant que l'humain utilise `input()`
- Depends on : PB-3, PB-4

---

## PB-7 — Hygiene projet ~~(Partiellement done — Sprint 1)~~

- Value : Repo public propre et maintenable.
- Acceptance Criteria :
  - [x] `.gitignore` en place
  - [x] `__pycache__` retire du tracking
  - [x] `_init_.py` malformed supprime
  - [x] `requirements.txt` cree
  - [ ] Tests unitaires sur les regles du jeu
  - [ ] README.md avec instructions d'utilisation
- Notes : Tests et README a completer quand le moteur sera stable (apres PB-2).
