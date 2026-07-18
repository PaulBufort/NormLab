# Baseline pré-Build Week

Ce document établit ce qui existait avant le 13 juillet 2026 et ce qui constitue une
extension NormLab. Il est fondé sur une inspection en lecture seule effectuée le
18 juillet 2026 ; il ne suppose pas qu’une intention documentée équivaut à une
fonctionnalité déployée.

## Identité et preuves de l’audit

| Élément | Valeur vérifiée |
| --- | --- |
| Dossier de référence | `../adoption-sim-reference/` |
| HEAD | `0e2d2601332b64981a80c816a4820e5a5a25c669` |
| Date du commit | `2026-06-17T23:12:51+02:00` |
| Sujet | `Fix 2 stale 20-rep citations: nb03 visibility caption + limitations #16` |
| État Git | HEAD détachée, arbre de travail propre lors de l’ouverture de l’audit |
| Hash de l’arbre racine | `3335a3f343aa235542850f9cacb34d713f03c57b` |
| Hash de l’arbre `core/` | `4b4551fde19e4ba5b75977bb49d17df60f7a1087` |
| Contenu suivi | 98 fichiers, 7 328 799 octets |
| Tests déclarés et comptés | 67 fonctions de test |
| Projet NormLab au départ | dépôt Git vide, branche `main`, aucun commit |

Les inspections structurantes ont utilisé `git status`, `git rev-parse`,
`git ls-tree`, `git show` et `git grep`. Une recherche insensible à la casse sur le
code et la documentation applicative n’a trouvé aucune occurrence d’OpenAI, GPT-5,
Responses API, structured output, natural language, experiment protocol ou decision
card dans la référence.

## Ce qui existait avant le 13 juillet

### Moteur scientifique

`adoption-sim` v0.1 est un package Python 3.11+ sous AGPL-3.0, installable comme
`adoption_sim`. Son cœur n’importe que NetworkX, NumPy et la bibliothèque standard.

- `core/orggen.py` génère une organisation hiérarchique synthétique : direction,
  départements, équipes, managers et contributeurs ; couche formelle et réseau
  informel pondéré ; silos, homophilie de tenure, connecteurs et bruit.
- `core/dynamics.py` exécute des mises à jour synchrones d’agents à seuil fractionnel
  avec portes ready/willing/able, crédibilité des liens, visibilité, broadcast,
  adoption, rechute optionnelle et attribution exclusive des non-adoptions.
- `core/seeding.py` implémente cinq stratégies : `broadcast`, `random`, `champions`,
  `cluster`, `line_manager_first`.
- `core/scenario.py` charge des scénarios TOML, fusionne les défauts, rejette les clés
  inconnues et écrit des CSV avec sidecar JSON de provenance.
- `core/sweep.py` construit des grilles de scénarios, exécute en série ou en
  multiprocessing et calcule des sensibilités one-at-a-time.
- `core/metrics.py` calcule plateau, rechute, temps d’atteinte, taux par département,
  poches mortes, attribution et pivots par knockout contrefactuel.
- `core/ingest.py` importe des edgelists et GraphML ; les attributs comportementaux
  restent synthétiques.

Le contrat de reproductibilité utilise un `master_seed` et des enfants
`numpy.random.SeedSequence`. Par défaut, chaque réplication régénère une organisation ;
les bandes décrivent donc des organisations synthétiques de même type, pas des
répétitions sur une entreprise donnée. Des tests établissent que série et parallèle
produisent les mêmes résultats.

### Modèle et paramètres de référence

Le scénario headline gèle notamment : 2 000 agents, 8 départements, équipes de taille
moyenne 8, force des silos 0,85, seuil moyen 0,30, concentration des seuils 20,
2,5 % d’innovateurs à seuil nul, volonté 0,85, capacité 1, visibilité 1, budget de
semis 5 %, 50 réplications et graine maître `20260610`.

Les stratégies semées reçoivent toutes `floor(0.05 * N)` adopteurs initiaux.
`broadcast` fait exception : zéro adopteur initial et une exposition temporaire de
communication de poids 0,3. Cette exception était explicitement documentée, mais le
projet antérieur ne convertissait pas communication et accompagnement en une unité de
coût commune.

La baseline affirme et teste l’équivalence suivante en absence de broadcast : une
visibilité globale `v < 1` est mathématiquement indiscernable d’une inflation des
seuils `theta / v`. C’est une non-identifiabilité, pas deux mécanismes séparément
estimables.

### Résultats et prudence scientifique

`RESULTS_VERIFIED.md` rapporte une réexécution intégrale le 17 juin : 67/67 tests,
CSV et figures reproduits bit-for-bit. Dans le scénario headline à kappa=20 et
50 réplications, les moyennes vérifiées sont : broadcast 5,50 %, random 69,54 %,
champions 73,37 %, cluster 31,93 %, line-manager-first 61,57 %.

Ces nombres sont entièrement synthétiques. Le projet les présente comme résultats
conditionnels sur le modèle, jamais comme prévisions. Il signale notamment :

- le chevauchement des intervalles champions/random, qui interdit un classement
  propre entre eux ;
- la forte dépendance à la distribution inconnue des seuils ;
- l’absence de calibration temporelle et organisationnelle ;
- la parité, et non une victoire du cluster, sous le paramétrage de rechute commis ;
- l’absence de pivot individuel dans les organisations générées ;
- l’échec de l’hypothèse selon laquelle la visibilité des pilotes sauverait la
  stratégie cluster dans cette famille de modèles.

### Expériences, interface et qualité

- Quatre notebooks exécutés : tutoriel, comparaison headline, sanity checks et
  observabilité.
- Scénarios TOML, CSV versionnés, sidecars de provenance, neuf figures finales et un
  script de régénération.
- Un article court et ses outils d’extraction de nombres.
- Une démo Streamlit avec contrôles de taille, silos, seuil, stratégie, budget,
  réplications, graine, rechute et visibilité ; courbes, référence broadcast, poches
  mortes par département et attribution ready/willing/able.
- Une bannière et des légendes « synthetic data » déjà présentes.
- CI GitHub Actions sur Python 3.11 et 3.13, test du package installable, smoke test de
  l’expérience et job de reproduction des résultats.
- Des instructions de déploiement Streamlit existaient, mais l’audit du dépôt ne
  fournit pas de preuve d’une URL publique active. Une instruction n’est pas une
  démonstration déployée vérifiée.

### Décisions et documentation historiques

La référence contient une spécification, le modèle mathématique, les hypothèses, les
limitations, les sanity checks, un journal et 17 décisions D1–D17 ratifiées le
10 juin 2026. Elle exclut explicitement les personas LLM, les données d’entreprise,
la calibration et une interface de production.

## Ce qui n’existait pas avant la Build Week

La référence ne fournit pas :

- d’entrée en langage naturel pour décrire un problème organisationnel ;
- d’intégration OpenAI ou GPT-5.6 Sol ;
- de schéma `ExperimentProtocol` ou de protocole inspectable généré ;
- de provenance champ par champ distinguant fourni, inféré et défaut système ;
- de phase explicite de critique de l’expérience par un modèle ;
- d’appel d’outil LLM vers le moteur déterministe ;
- de comparateur produit garantissant et affichant les budgets et graines appariés ;
- de détection générique des inversions de classement sous sensibilité ;
- de fiche de décision séparant résultat, hypothèse, limite et prochaine donnée ;
- de jeu d’evals pour la traduction langage naturel → protocole ;
- de démo jury NormLab déployée et vérifiée ;
- de documentation du rôle de Codex et GPT-5.6 pendant la Build Week.

## Frontière de nouveauté NormLab

| Couche | Statut historique | Apport NormLab attendu |
| --- | --- | --- |
| Agents à seuil et dynamique | pré-Build Week | réutilisation contrôlée, pas remplacement LLM |
| Génération d’organisation et stratégies | pré-Build Week | exposition via protocole typé |
| Sweeps et métriques de base | pré-Build Week | orchestration appariée et contrat de résultat |
| Démo à sliders | pré-Build Week | parcours centré sur une question en langage naturel |
| Conception d’expérience | absente | GPT-5.6 Sol + schéma + provenance |
| Critique scientifique | décisions historiques manuelles | critique de chaque protocole et drapeaux codés |
| Comparabilité | égalité du nombre de seeds seulement | ledger visible, règles de classement et exceptions |
| Sensibilité | sweeps de recherche prédéfinis | analyse ciblée du protocole et fragilité du classement |
| Restitution | graphiques pédagogiques | fiche de décision en quatre catégories strictes |
| Traçabilité Build Week | absente de NormLab | journal, attribution des composants et tests/evals |

## Conséquence pour l’implémentation

La nouveauté du concours ne peut pas être revendiquée pour le moteur historique ou sa
démo paramétrique. Elle doit être démontrée par le contrat complet : question libre →
protocole fourni/inféré → critique → validation → appel déterministe → comparaison
appariée → sensibilité/non-identifiabilité → fiche de décision. Toute présentation
publique devra maintenir cette frontière.

## Portage réalisé le 18 juillet 2026

Après ratification A1, `defaults.py`, `orggen.py`, `dynamics.py`, `seeding.py`,
`metrics.py` et le fichier d’initialisation ont été copiés verbatim dans
`normlab/legacy_engine/`. La licence AGPL‑3.0 a été conservée. Les blobs Git et SHA‑256
de chaque fichier figurent dans `docs/provenance/LEGACY_ENGINE.json` et sont vérifiés
par `tests/test_legacy_parity.py`. Aucun fichier de la référence n’a été exécuté ou
modifié pendant ce portage ; son arbre de travail est resté propre au commit figé.
