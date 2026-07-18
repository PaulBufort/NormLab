# NormLab — OpenAI Build Week 2026

**Fenêtre officielle :** 13–21 juillet 2026

**État de ce document :** créé le 18 juillet 2026

**Deadline de livraison visée :** 21 juillet 2026

**Modèle produit demandé :** GPT-5.6 Sol (`gpt-5.6-sol`)

**Référence historique :** `adoption-sim-reference` au commit
`0e2d2601332b64981a80c816a4820e5a5a25c669` du 17 juin 2026

## Promesse produit

NormLab transforme une question de changement organisationnel formulée en langage
naturel en protocole expérimental explicite. GPT-5.6 Sol sépare les faits fournis des
hypothèses, critique le protocole et demande au moteur déterministe d’exécuter des
interventions comparables. NormLab restitue les résultats comme des conséquences
synthétiques conditionnelles, accompagnées des hypothèses, limites, sensibilités,
non-identifiabilités et prochaines données à recueillir.

NormLab n’est ni un outil de prévision, ni un simulateur de personnages LLM, ni un
substitut à des données organisationnelles réelles.

## Ligne de partage temporelle

### Existant avant le 13 juillet

Le projet antérieur `adoption-sim` existait intégralement avant la Build Week. Son
dernier commit de référence date du 17 juin. Il apporte un moteur Python déterministe
de contagion complexe, un générateur d’organisations synthétiques, cinq stratégies,
des sweeps reproductibles, des métriques, 67 tests, des expériences et une démo
Streamlit paramétrique. L’inventaire détaillé et les preuves sont dans
`docs/BASELINE.md`.

### Nouveau pendant la Build Week

Au début de cette tâche, le 18 juillet, le dépôt NormLab était vide : branche `main`,
aucun commit, aucun fichier applicatif. Les premiers apports Build Week sont les
quatre documents de gouvernance demandés :

- `AGENTS.md` ;
- `BUILD_WEEK.md` ;
- `docs/BASELINE.md` ;
- `docs/CODEX_COLLABORATION.md`.

Tout le reste ci-dessous est un plan, pas une fonctionnalité déjà construite, tant
qu’une entrée du journal ne dit pas le contraire.

## Architecture ratifiée et implémentée

1. **Intake** — texte libre et quelques contraintes explicites de l’utilisateur.
2. **Conception Sol** — sortie structurée `ExperimentProtocol` avec provenance de
   chaque champ, hypothèses, facteurs incertains et critères de comparaison.
3. **Critique Sol** — contrôle de validité, comparabilité des budgets, facteurs
   confondus, non-identifiabilité et données manquantes.
4. **Validation locale** — schémas et règles codées rejettent tout protocole hors du
   domaine du moteur ; le LLM ne contourne pas ces règles.
5. **Exécution** — appel d’outil vers le moteur déterministe avec graines appariées.
6. **Analyse codée** — agrégats, intervalles descriptifs, changements de classement
   et drapeaux de sensibilité calculés sans LLM.
7. **Fiche de décision Sol** — synthèse fondée uniquement sur le protocole validé et
   les résultats de l’outil, avec quatre blocs distincts : résultats, hypothèses,
   limites, prochaine donnée à recueillir.

La [documentation OpenAI actuelle pour GPT-5.6](https://developers.openai.com/api/docs/guides/model-guidance?model=gpt-5.6)
recommande la Responses API pour le raisonnement, les outils et les flux multi-tours.
Elle recommande aussi des prompts centrés sur le résultat, un niveau d’effort
explicite et des limites d’autonomie compactes. Le plan retient ces principes sans
adopter automatiquement les fonctions optionnelles Pro, multi-agent, persisted
reasoning, cache explicite ou Programmatic Tool Calling.

## Plan de réalisation jusqu’au 21 juillet

| Date cible (CEST) | Lot | Preuve de fin |
| --- | --- | --- |
| 18 juillet, avant arbitrage | Audit et gouvernance | quatre documents présents, référence toujours propre |
| 18 juillet, après arbitrage | Socle Python, import du moteur, licence et tests de parité | mêmes résultats à graines fixes sur scénarios golden |
| 19 juillet matin | Schémas `ExperimentProtocol`, provenance champ par champ, validateur et fixtures | tests de schéma et exemples inspectables |
| 19 juillet après-midi | Client Sol via Responses API, prompt versionné, outil d’exécution déterministe | trace complète texte → protocole → appel outil |
| 20 juillet matin | Comparateur apparié, budgets, sensibilité et drapeaux de non-identifiabilité | résultats reproductibles et tests des classements fragiles |
| 20 juillet après-midi | Interface Streamlit et fiche de décision exportable | parcours utilisateur complet et QA visuelle |
| 20 juillet soir | Tests, evals de protocole, erreurs, mode sans clé et sécurité | suite verte, aucun secret, cas limites couverts |
| 21 juillet matin | Déploiement, smoke test public, README et preuves concours | URL jury, commande de reproduction, rôle de Codex/Sol documenté |
| 21 juillet midi | Gel de démonstration et marge corrective | tag ou commit candidat, journal final, limites restantes explicites |

Le chemin critique est : arbitrage → moteur paritaire → protocole typé → exécution
appariée → interface → déploiement. Les notebooks, l’import de graphes réels, une UI
React séparée et toute calibration sont hors chemin critique.

## Arbitrages ratifiés

Le propriétaire a validé A1–A5 le 18 juillet 2026. Les recommandations ci-dessous
sont devenues la baseline produit de la Build Week. Toute modification ultérieure des
équations, distributions, stratégies, budgets, métriques ou réplications demande un
nouvel arbitrage explicite.

### A1 — Réutilisation et licence du moteur

**Recommandation :** copier dans NormLab uniquement le package moteur nécessaire,
verbatim au départ, conserver l’AGPL-3.0 et l’attribution au dépôt/commit source,
puis entourer ce code de tests de parité. Cela rend la démo autonome sans écrire
dans la référence et donne une frontière vérifiable entre héritage et nouveauté.

Alternative : dépendre du dépôt externe à un commit. C’est plus léger, mais rend le
déploiement et la démonstration dépendants d’un autre dépôt. Réimplémenter le moteur
avant le 21 juillet est exclu : risque scientifique et délai disproportionnés.

### A2 — Interface et déploiement

**Recommandation :** application Streamlit unique, parce que le moteur et la démo
antérieure sont Python et qu’un déploiement Community Cloud est documenté. Elle peut
être nettement nouvelle sur le plan produit tout en restant livrable.

Alternative : API Python + React/Next.js. Elle offre plus de contrôle visuel mais
ajoute deux surfaces de build, de test et de déploiement à trois jours de la date
limite.

### A3 — Comparabilité du budget

**Recommandation :** classer ensemble `random`, `champions`, `cluster` et
`line_manager_first` avec exactement `floor(budget * N)` adopteurs initiaux et les
mêmes organisations/graines. Afficher `broadcast` dans un panneau de référence
séparé, car le moteur historique lui donne zéro adopteur et une exposition de
communication : sans données de coût, ce n’est pas la même unité de ressource.

Alternative : convertir communication et accompagnement en un budget commun. Cette
conversion serait une nouvelle hypothèse scientifique/économique qui exige vos
unités et valeurs ; Sol ne doit pas les inventer.

### A4 — Moment de l’exécution Sol

**Recommandation :** flux en deux temps. Sol produit et critique un protocole visible ;
l’utilisateur peut l’inspecter et clique « Exécuter ». Sol demande alors l’appel de
l’outil déterministe avec ce protocole validé, puis rédige la fiche à partir du
résultat. C’est plus auditable qu’une exécution immédiate.

Alternative : génération et exécution en un clic. Plus spectaculaire, mais les
hypothèses inférées sont moins faciles à contester avant calcul.

### A5 — Domaine scientifique du MVP

**Recommandation :** organisations synthétiques seulement ; entrée textuelle sans
upload de données réelles ; analyse de sensibilité sur seuil moyen, hétérogénéité des
seuils, force des silos et visibilité ; réplications appariées. La fiche doit signaler
explicitement l’équivalence visibilité/seuil et les changements de classement.

Alternative : accepter des graphes d’entreprise ou promettre une calibration. Cela
ajoute sécurité, confidentialité, nettoyage de données et interprétation causale ; ce
n’est pas compatible avec le 21 juillet sans réduire les fonctions centrales.

| Décision | Statut | Conséquence implémentée |
| --- | --- | --- |
| A1 | ratifiée le 18 juillet | six fichiers moteur portés verbatim, AGPL et manifeste de hashes |
| A2 | ratifiée le 18 juillet | application Streamlit unique dans `demo/app.py` |
| A3 | ratifiée le 18 juillet | quatre stratégies à seeds égaux ; broadcast hors classement |
| A4 | ratifiée le 18 juillet | protocole visible, approbation humaine, appel d’outil puis fiche |
| A5 | ratifiée le 18 juillet | synthétique uniquement et quatre facteurs de sensibilité |

## Définition de terminé

- [x] Un utilisateur décrit un problème d’adoption de l’IA en langage naturel.
- [ ] Sol produit un protocole structuré, inspectable et versionné.
- [x] Les faits utilisateur et hypothèses inférées sont visuellement distincts.
- [x] Sol critique le protocole et expose les problèmes de comparabilité et
      d’identification.
- [x] Le moteur déterministe exécute des scénarios reproductibles.
- [x] Les stratégies classées partagent budget, graines et réplications comparables.
- [x] L’interface compare les interventions et montre leur sensibilité.
- [x] La fiche sépare résultats, hypothèses, limites et prochaine donnée.
- [x] Aucun résultat synthétique n’est présenté comme une prévision réelle.
- [ ] Les tests, contrôles de schéma et smoke tests passent (tests et smoke local
      verts ; smoke réel Sol/public encore requis).
- [x] Une démonstration publique est accessible au jury en mode fixture à
      `https://normlab-build-week-2026.streamlit.app/` ; activation et smoke test Sol
      réels encore requis.
- [x] Le README et ce fichier expliquent exactement le rôle de Codex et de GPT-5.6.
- [x] La provenance de chaque composant legacy et Build Week est vérifiable.

## Journal de construction

| Date/heure (CEST) | Auteur | Catégorie | Changement | Validation |
| --- | --- | --- | --- | --- |
| 2026-07-18 | Codex, tâche courante | `build-week-new` | Audit en lecture seule de la référence et création de `AGENTS.md`, `BUILD_WEEK.md`, `docs/BASELINE.md`, `docs/CODEX_COLLABORATION.md` | SHA/date/état Git, 98 fichiers, 67 tests et absence d’intégration OpenAI vérifiés ; quatre fichiers relus ; référence encore propre au SHA figé |
| 2026-07-18 | Propriétaire | décision | Ratification sans modification de A1–A5 | Message « A1-A5 validés » dans cette tâche Codex |
| 2026-07-18 | Codex, tâche courante | `legacy-port` | Portage verbatim de six fichiers du moteur et de la licence ; ajout du NOTICE et du manifeste de provenance | SHA-256 de chaque destination égal au manifeste ; commit et arbre source vérifiés propres |
| 2026-07-18 | Codex, tâche courante | `build-week-new` | Schémas stricts, provenance, garde-fous, protocole hors ligne, orchestrateur apparié, budget ledger, réplications brutes, sensibilité et non-identifiabilité | tests de schéma, deux résultats complets identiques et 111 raw runs vérifiés |
| 2026-07-18 | Codex, tâche courante | `build-week-new` | Adaptateur Responses API pour `gpt-5.6-sol`, outil strict, prompts versionnés, fiche et vérificateur de preuves | doubles API : modèle/effort/store/tool choice contrôlés ; substitution et preuve inventée rejetées ; aucun appel réel faute de clé |
| 2026-07-18 | Codex, tâche courante | `build-week-new` | Interface Streamlit question → protocole → approbation → résultats → fiche → exports/trace | parcours hors ligne complet vérifié dans le navigateur local ; avertissements visibles ; corrections des warnings Arrow/dépréciation |
| 2026-07-18 | Codex, tâche courante | `build-week-new` | README, architecture, intégration OpenAI, déploiement, script jury, evals et CI | `python -m compileall -q normlab demo` réussi ; 24 tests passés en 2,68 s ; `pip check` sans dépendance cassée ; scan de motif de clé propre |
| 2026-07-18 | Propriétaire | autorisation | Autorisation explicite de créer la branche et le commit `codex/build-week-mvp`, pousser vers `origin`, puis déployer sur Streamlit | Message d’autorisation dans cette tâche Codex ; aucun secret communiqué ni demandé dans le dépôt |
| 2026-07-18 | Codex, tâche courante | publication | Création du dépôt public `PaulBufort/NormLab` et push de `codex/build-week-mvp` | Commit racine `b142bd2` visible publiquement ; README, AGPL et 42 fichiers vérifiés sur GitHub |
| 2026-07-18 | Codex, tâche courante | déploiement | Déploiement Streamlit Community Cloud de `demo/app.py` sur `https://normlab-build-week-2026.streamlit.app/` | Smoke public hors ligne complet réussi : protocole, exécution, budgets, sensibilité, fiche et exports ; pastille « Sol non appelé » vérifiée faute de secret OpenAI |
| 2026-07-18 | Propriétaire | décision produit | Remplacement du secret propriétaire envisagé par une clé API temporaire apportée par chaque testeur | Le propriétaire estime que le jury OpenAI disposera de clés ; conservation obligatoire du mode fixture si ce n’est pas le cas |
| 2026-07-18 | Codex, tâche courante | `build-week-new` | Ajout du mode BYOK en mémoire de session, champ masqué, statut explicite et effacement clé + artefacts | Tests Streamlit et suite complète à exécuter ; aucun changement du moteur, des budgets ou des équations |
| 2026-07-18 | Codex, tâche courante | validation | Validation du lot BYOK sans clé réelle ni appel réseau | 25 tests passés ; compilation et `git diff --check` réussis ; champ HTML `password`, activation et libellés vérifiés sur l’application locale ; aucun motif de clé détecté |
| 2026-07-18 | Propriétaire + Codex | correction UX | La capture du déploiement a montré que le panneau latéral d’activation n’était pas découvrable ; déplacement du champ BYOK dans une section repliable explicite en haut de page | Changement d’interface uniquement ; aucun changement du moteur ou du contrat Sol |

Le dernier lot restant est le smoke test public réel de `gpt-5.6-sol` avec une clé
temporaire fournie par le testeur, sans jamais inscrire la clé dans Git, les secrets
du déploiement, les exports ou ce journal.
