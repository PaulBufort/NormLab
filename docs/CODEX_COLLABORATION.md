# Collaboration Codex, GPT-5.6 Sol, moteur et humain

Ce document rend attribuable le travail de construction et le comportement runtime de
NormLab. Les quatre acteurs ont des responsabilités différentes et non substituables.

## Répartition des responsabilités

### Propriétaire scientifique et produit

Le propriétaire :

- arbitre les choix qui modifient le périmètre, les équations, les hypothèses, les
  budgets, la licence ou l’expérience utilisateur ;
- fournit les contraintes réelles et décide quelles hypothèses inférées sont
  acceptables ;
- décide du déploiement public et des secrets associés ;
- garde l’autorité sur les affirmations présentées au jury.

Les arbitrages A1–A5 ont été ratifiés par le propriétaire le 18 juillet 2026 et sont
consignés dans `BUILD_WEEK.md`.

### Codex pendant la Build Week

Codex a construit dans cette tâche le produit exécutable : audit, architecture,
portage traçable du moteur, schémas, orchestration, adaptateur Sol, interface, tests,
evals, documentation et préparation du déploiement. La majorité des fonctionnalités
centrales est ainsi attribuable à cette tâche Codex afin que son identifiant
`/feedback` puisse être transmis au concours.

Codex peut inspecter, modifier et valider les fichiers NormLab dans le périmètre
autorisé. Il ne peut pas :

- écrire dans le projet de référence ;
- ratifier seul une nouvelle hypothèse scientifique ou économique ;
- transformer une absence de données en fait utilisateur ;
- committer, publier ou déployer sans autorisation correspondante ;
- ajouter un secret au dépôt.

Chaque lot Codex est ajouté au journal de `BUILD_WEEK.md` avec ses fichiers et preuves
de validation. Les changements de code issus du moteur antérieur seront étiquetés
`legacy-port`; la couche produit créée ici sera étiquetée `build-week-new`.

### GPT-5.6 Sol dans le produit

Sol est le concepteur et critique de l’expérience, pas le moteur de simulation.

Entrée : question de changement organisationnel et contraintes utilisateur.

Sorties attendues :

1. un protocole structuré dont chaque champ indique sa valeur, sa provenance et sa
   justification ;
2. une critique structurée couvrant validité, budget, facteurs confondus, sensibilité,
   non-identifiabilité, limites du moteur et données manquantes ;
3. un appel d’outil contenant uniquement un protocole validé ;
4. une fiche de décision fondée uniquement sur le protocole et les résultats renvoyés
   par le moteur.

Sol peut proposer une hypothèse, mais doit la marquer `inferred`. Il ne peut pas la
présenter comme fournie, modifier les sorties numériques, appeler les résultats une
prévision, cacher un résultat négatif, ni inventer une conversion de budget.

### Moteur déterministe

Le moteur est l’autorité numérique. À protocole, version, graines et dépendances
identiques, il doit produire les mêmes résultats. Il :

- génère les organisations synthétiques ;
- applique les règles d’agents à seuil ;
- exécute les stratégies et réplications ;
- retourne résultats bruts et métriques calculables.

Il ne comprend pas le langage naturel, ne choisit pas les hypothèses et ne produit pas
de recommandation métier. Une phrase de Sol ne peut jamais remplacer une exécution du
moteur.

## Contrats inspectables implémentés

### `ExperimentProtocol`

Le schéma versionné comprend :

- question et objectif expérimental ;
- population synthétique et structure organisationnelle ;
- comportement d’adoption modélisé ;
- interventions, budget et unité de comparaison ;
- paramètres, provenance (`provided`, `inferred`, `system_default`) et confiance ;
- plan de réplication, graines appariées et métriques ;
- facteurs de sensibilité ;
- hypothèses, exclusions et données manquantes ;
- statut de validation et version du moteur.

### `ExperimentCritique`

La critique comporte des codes stables et testables : budget non comparable,
paramètre hors domaine, donnée utilisateur manquante, hypothèse forte, classement
sensible, non-identifiabilité, demande de prévision réelle ou capacité absente du
moteur. Un avertissement codé ne pourra pas être supprimé par la prose finale.

### `DecisionCard`

La fiche a quatre blocs obligatoires et distincts :

- **Résultats de simulation** — chiffres et comparaisons, avec protocole et graines ;
- **Hypothèses** — valeurs inférées et défauts qui conditionnent ces résultats ;
- **Limites** — ce que le modèle ne permet pas de conclure, sensibilités et
  non-identifiabilités ;
- **Prochaine donnée à recueillir** — mesure réelle qui réduirait le plus
  l’incertitude, sans prétendre qu’elle existe déjà.

## Trace d’une exécution

Une exécution auditable doit relier :

`question exacte → protocol_id → prompt_version/model → critique → approbation →
engine_version/commit → result_id/graines → raw_runs → analysis_flags → card_id`.

La trace conserve les entrées et sorties structurées nécessaires à la reproduction,
pas le raisonnement privé du modèle. Elle expurge les secrets. En démonstration, elle
peut utiliser un identifiant de session éphémère et permettre le téléchargement du
protocole et de la fiche.

## Tests de collaboration

- Fixtures sans API pour les protocoles valides, ambigus, impossibles et demandant
  abusivement une prévision.
- Tests de schéma pour empêcher Sol d’omettre provenance, limites ou données à
  recueillir.
- Test de falsification : une valeur numérique inventée par la fiche doit échouer si
  elle n’existe pas dans les résultats calculés.
- Test de budget : aucune stratégie non comparable ne peut apparaître dans le même
  classement principal.
- Test de déterminisme : même protocole et mêmes graines, mêmes résultats.
- Evals Sol sur des questions réalistes, avec critères explicites de fidélité aux
  informations utilisateur et de visibilité des hypothèses.
- Smoke test public du parcours complet avant remise au jury.

## État au 18 juillet 2026

Le parcours hors ligne complet, les contrats, le moteur porté, l’orchestration
appariée, les garde-fous, la fiche et l’interface sont fonctionnels et testés. Le
contrat GPT‑5.6 Sol est couvert par des doubles unitaires ; son smoke test réel reste
à exécuter lorsqu’un testeur fournira temporairement sa clé de projet dans la session.
Le propriétaire ne finance donc pas les appels publics et ne configure aucun secret
OpenAI sur le déploiement. Le déploiement public est accessible à
`https://normlab-build-week-2026.streamlit.app/` et son parcours fixture a été vérifié
de bout en bout. Cette limite Sol reste visible et n’est pas présentée comme terminée.
