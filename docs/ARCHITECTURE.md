# Architecture et frontières scientifiques

## Composants

| Composant | Fichiers | Provenance | Autorité |
| --- | --- | --- | --- |
| Moteur à seuil | `normlab/legacy_engine/*` | `legacy-port`, verbatim | calcul numérique |
| Contrats | `normlab/models.py` | `build-week-new` | forme et domaine des données |
| Protocole | `normlab/protocols.py` | `build-week-new` | provenance et garde-fous locaux |
| Orchestrateur | `normlab/runner.py` | `build-week-new` | appariement, budget, agrégats, sensibilité |
| Adaptateur Sol | `normlab/sol.py`, `normlab/prompts.py` | `build-week-new` | conception, critique et synthèse structurées |
| Vérificateur | `normlab/decisions.py` | `build-week-new` | exactitude des références numériques |
| Produit | `demo/app.py` | `build-week-new` | inspection, approbation, comparaison, export |

## Contrat scientifique

Le moteur applique les équations historiques sans adaptation. NormLab ajoute une
expérience appariée : pour une réplication donnée, toutes les stratégies classées
partagent l’organisation synthétique et les tirages d’agents. Elles reçoivent chacune
`floor(seed_budget_fraction × n_agents)` adopteurs initiaux ; leurs graines de
sélection et de dynamique sont déterministes et conservées dans `raw_runs`.

`broadcast` sème zéro agent et ajoute une exposition centrale temporaire. Il utilise
donc une unité `communication_exposure`, tandis que les autres stratégies utilisent
`initial_adopters`. Faute de conversion de coût fournie, NormLab l’exclut du
classement et l’affiche séparément.

Les sensibilités one-at-a-time évaluent deux niveaux pour chacun des quatre facteurs
ratifiés : `theta_mean`, `theta_concentration`, `silo_strength` et `visibility`. Toute
inversion du classement central est codée dans le résultat. Une grille restreinte ne
prouve jamais la robustesse dans le monde réel.

## Provenance et identifiants

Chaque valeur configurable du protocole contient une valeur, une source et une
justification. Le garde-fou local conserve la question textuelle exacte et rétrograde
une quantité marquée `provided` si aucun nombre compatible n’apparaît dans la
question. Ce contrôle lexical empêche une invention simple ; il ne résout pas la
sémantique des unités et l’inspection humaine reste obligatoire.

`protocol_id` est un condensat du protocole canonique. `result_id` dépend du
protocole, du classement, des résultats centraux et des sensibilités. Le résultat
exporté contient le snapshot complet du protocole, la version/commit du moteur et
chaque réplication brute avec toutes ses graines. `card_id` relie protocole et
résultat.

## Non-identifiabilité obligatoire

Sans broadcast, une visibilité globale `v` multiplie chaque exposition. La condition
d’adoption est donc équivalente à une visibilité 1 avec des seuils `theta / v`.
Observer une trajectoire faible ne permet pas d’identifier séparément « seuils élevés »
et « usages peu visibles ». Le protocole, le résultat et la fiche portent tous ce
drapeau ; Sol ne peut pas le supprimer.

## Capacités exclues du MVP

- aucune calibration ou prévision organisationnelle réelle ;
- aucun upload de graphe, fichier RH ou donnée d’entreprise ;
- aucun agent/persona LLM dans la simulation ;
- aucune conversion inventée entre communication et accompagnement ;
- aucune modification des équations, distributions ou métriques héritées ;
- aucune persistance du raisonnement privé du modèle.
