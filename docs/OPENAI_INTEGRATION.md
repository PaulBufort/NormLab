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

## Mode hors ligne

En absence de `OPENAI_API_KEY`, l’interface utilise `design_offline_protocol` et
`build_offline_decision_card`. Les deux sont déterministes et affichés comme
`offline_fixture`; aucun texte ne prétend provenir de Sol. Ce mode permet les tests,
la CI et un parcours complet sans réseau.

## Smoke test réel

Une clé doit être fournie exclusivement par l’environnement ou le gestionnaire de
secrets Streamlit. Lancer ensuite :

```bash
streamlit run demo/app.py
```

Vérifier que la pastille indique « GPT‑5.6 Sol actif », que la provenance reste
visible avant le clic d’exécution, que l’outil appelle exactement le protocole
approuvé et que la trace contient trois identifiants de réponse sans contenu privé.
Le 18 juillet 2026, aucun smoke test réel n’a été exécuté dans cette tâche car aucune
clé n’était présente ; les doubles de test couvrent le contrat API sans réseau.

Références officielles :
[guide GPT‑5.6](https://developers.openai.com/api/docs/guides/model-guidance?model=gpt-5.6),
[function calling](https://developers.openai.com/api/docs/guides/function-calling),
[structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs).
