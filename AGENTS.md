# AGENTS.md — NormLab

Ce fichier définit les règles durables pour tout agent de développement travaillant
dans ce dépôt pendant et après l’OpenAI Build Week 2026.

## Périmètre de fichiers

- Le seul périmètre modifiable est le dépôt `NormLab/` qui contient ce fichier.
- `../adoption-sim-reference/` est une référence strictement en lecture seule,
  figée au commit `0e2d2601332b64981a80c816a4820e5a5a25c669` du 17 juin 2026.
- Ne jamais modifier, reformater, installer de dépendances dans, exécuter une
  commande qui écrit dans, ni committer depuis `adoption-sim-reference/`.
- Pour inspecter la référence, préférer `git -C ../adoption-sim-reference show
  HEAD:<chemin>` et les autres commandes Git en lecture seule. Ne pas lancer ses
  tests ou notebooks depuis ce dossier : ils peuvent créer des caches ou résultats.
- Ne jamais ajouter de clé API, secret, donnée personnelle ou donnée d’entreprise au
  dépôt. Les secrets de développement viennent exclusivement de l’environnement ;
  les secrets de déploiement viennent du gestionnaire de secrets de la plateforme.

## Invariants scientifiques et produit

- GPT-5.6 Sol conçoit, formalise et critique l’expérience. Le moteur déterministe
  calcule les résultats. Ne jamais substituer un récit du modèle à une exécution.
- Les personnes simulées restent des agents à seuil. Ne pas créer de personnages ou
  de comportements individuels pilotés par un LLM.
- Chaque sortie visible porte la mention que les données sont synthétiques et non
  calibrées. Employer « résultat de simulation » ou « résultat sous hypothèses »,
  jamais « prévision ».
- Toute valeur du protocole doit porter une provenance : `provided` si elle est
  fournie par l’utilisateur, `inferred` si elle est proposée par Sol, et
  `system_default` si elle vient d’un défaut versionné. Ne jamais fusionner ces
  catégories dans l’interface ou la fiche de décision.
- Les stratégies classées ensemble doivent avoir un budget comparable et le même
  plan de réplication. Une référence non comparable doit être affichée séparément et
  explicitement étiquetée.
- Utiliser les mêmes graines et organisations simulées entre stratégies lorsque le
  protocole prévoit une comparaison appariée.
- Signaler les changements de classement dans les analyses de sensibilité, les
  résultats fragiles et toute non-identifiabilité connue. L’équivalence historique
  entre visibilité globale et inflation des seuils (`theta / visibility`) est un cas
  obligatoire.
- Une modification des équations, distributions, stratégies, métriques, règles de
  budget ou sémantique des réplications est une décision scientifique. L’arrêter et
  demander l’arbitrage du propriétaire avant implémentation.

## Frontière du moteur hérité

- La baseline scientifique est décrite dans `docs/BASELINE.md` ; sa source de vérité
  historique reste le commit figé de la référence.
- Si le moteur est importé dans NormLab après arbitrage, conserver son attribution et
  sa licence, enregistrer exactement les fichiers sources et le commit, puis établir
  des tests de parité avant toute adaptation.
- Les wrappers, schémas de protocole, validateurs, orchestrateurs, interfaces et
  fiches de décision sont des apports NormLab. Ils ne doivent pas modifier
  silencieusement les valeurs passées au moteur.
- Une exécution doit conserver au minimum : version du protocole, version du moteur,
  identifiant de scénario, graines, nombre de réplications, stratégies, budgets,
  paramètres, résultats bruts et avertissements.

## Intégration OpenAI

- La cible demandée est l’identifiant explicite `gpt-5.6-sol`, pas un alias familial.
- Pour le flux proposé, utiliser la Responses API avec un contrat de sortie structuré
  et un outil déterministe étroitement typé. Ce choix reste bloqué jusqu’à
  l’arbitrage produit A4 dans `BUILD_WEEK.md`.
- Rendre les limites d’autonomie explicites dans le prompt : Sol peut proposer,
  critiquer et demander l’exécution d’un protocole validé ; il ne peut ni inventer
  des données utilisateur, ni modifier le moteur, ni masquer un avertissement.
- Ne pas stocker de raisonnement privé. Conserver seulement les entrées utiles,
  sorties structurées, versions de prompt/modèle, appels d’outil, erreurs et mesures
  nécessaires à l’audit, après retrait des secrets.
- Prévoir un mode hors ligne ou des fixtures pour que les tests unitaires ne
  dépendent ni du réseau ni d’une clé API.

## Traçabilité Build Week

- Mettre à jour `BUILD_WEEK.md` à chaque lot significatif : date, auteur/agent,
  fichiers, validation, décision liée et statut.
- Mettre à jour `docs/CODEX_COLLABORATION.md` si les responsabilités de Codex, Sol,
  du moteur ou de l’humain changent.
- Marquer chaque fonctionnalité comme `legacy-port`, `build-week-new` ou
  `post-build-week` dans la documentation de provenance appropriée.
- Ne pas réécrire les journaux historiques. Corriger une erreur par une entrée datée
  qui explique l’ancienne et la nouvelle information.
- Les commits doivent être petits, descriptifs et ne mélanger ni données générées
  lourdes ni changements sans rapport. Ne pas créer de commit sans demande explicite.

## Validation minimale

Avant de déclarer un lot terminé :

1. exécuter les tests unitaires et les contrôles de schéma concernés ;
2. vérifier la déterminisme à graines identiques ;
3. vérifier la parité du moteur avec la baseline si son code est présent ;
4. exécuter un scénario complet sans API au moyen d’une fixture ;
5. exécuter un smoke test réel de l’intégration Sol seulement si une clé est fournie
   par l’environnement ;
6. vérifier visuellement l’interface et la présence des avertissements ;
7. inscrire les commandes et résultats dans `BUILD_WEEK.md`.

## Arbitrages ratifiés

Le propriétaire a ratifié A1 à A5 sans modification le 18 juillet 2026. Leur
implémentation devient la baseline scientifique et produit de la Build Week. Toute
modification ultérieure des équations, distributions, stratégies, métriques, règles
de budget, facteurs de sensibilité ou sémantique des réplications reste une nouvelle
décision scientifique et exige un arbitrage explicite avant implémentation.
