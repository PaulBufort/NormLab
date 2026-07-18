# Intégration GPT‑5.6 Sol

## Contrat runtime

NormLab cible exactement `gpt-5.6-sol` via la Responses API. L’adaptateur utilise un
effort de raisonnement `medium`, `store=False` et un `safety_identifier` dérivé par
SHA‑256 d’un identifiant de session éphémère. Aucun secret ni raisonnement privé n’est
conservé.

Le flux ratifié A4 comporte deux moments visibles :

1. `responses.parse` demande à Sol un `ProtocolPackage` strict : protocole,
   provenance, hypothèses, données manquantes et critique ;
2. les garde-fous locaux imposent la question exacte, corrigent les nombres non
   étayés, recalculent `protocol_id` et injectent les critiques obligatoires ;
3. l’utilisateur inspecte ou modifie le protocole puis l’approuve ;
4. `responses.create` force un unique appel de fonction strict
   `run_deterministic_experiment({protocol_id})` ;
5. l’adaptateur rejette tout identifiant différent, exécute localement le protocole
   approuvé et renvoie un résultat compact à Sol ;
6. `responses.parse` produit une `DecisionCard` structurée ;
7. le vérificateur local rejette une référence numérique absente ou différente du
   résultat, ainsi que l’omission des limites obligatoires.

Le contenu de raisonnement chiffré est inclus uniquement pour poursuivre l’appel
d’outil avec `store=False`; il n’est ni écrit sur disque ni exposé dans la trace.
La trace conserve seulement modèle, effort, versions de prompt, identifiants de
réponses et d’appel d’outil.

## Limites d’autonomie

Les prompts versionnés autorisent Sol à proposer, critiquer et synthétiser. Ils lui
interdisent d’inventer des données utilisateur, d’appeler une sortie « prévision »,
de changer l’équation, de cacher broadcast ou une sensibilité, et de fabriquer un
chiffre. Ces interdictions sont doublées par des validations codées ; le prompt seul
n’est pas une barrière de sécurité.

## Clé temporaire du testeur et mode hors ligne

La démonstration publique ne requiert aucune clé propriétaire dans les secrets de
déploiement. Un testeur peut saisir une clé de projet dans un champ `password` de la
section repliable « Tester GPT‑5.6 Sol ». Elle reste dans l’état mémoire de sa session
Streamlit, est transmise uniquement au client OpenAI, n’est ni écrite sur disque ni
incluse dans les exports, et peut être effacée avec tous les artefacts de session. Les
appels sont facturés au compte associé à cette clé.

En absence de clé temporaire ou de `OPENAI_API_KEY` local, l’interface utilise
`design_offline_protocol` et `build_offline_decision_card`. Les deux sont
déterministes et affichés comme `offline_fixture`; aucun texte ne prétend provenir de
Sol. Ce mode permet les tests, la CI et un parcours complet sans réseau.

## Smoke test réel

En local, une clé peut être fournie par l’environnement. Sur la démonstration
publique, le testeur la saisit temporairement dans cette section. Lancer ensuite :

```bash
streamlit run demo/app.py
```

Vérifier que la pastille indique « GPT‑5.6 Sol actif — clé temporaire du juré », que
la provenance reste visible avant le clic d’exécution, que l’outil appelle exactement
le protocole approuvé et que la trace contient trois identifiants de réponse sans
contenu privé. Vérifier ensuite que le bouton d’effacement retire la clé et les
artefacts de la session.
Un smoke test réel local a réussi le 18 juillet 2026. Le 19 juillet, le parcours réel
a également réussi sur le déploiement public entièrement anglophone avec une clé
temporaire fournie par le propriétaire : protocole, appel d’outil, moteur, fiche
vérifiée et trois exports cohérents. La clé n’a été ni partagée avec Codex, ni stockée
dans le dépôt ou les exports.

Références officielles :
[guide GPT‑5.6](https://developers.openai.com/api/docs/guides/model-guidance?model=gpt-5.6),
[function calling](https://developers.openai.com/api/docs/guides/function-calling),
[structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs).
