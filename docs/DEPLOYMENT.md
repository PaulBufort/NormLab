# Déploiement Streamlit et smoke test jury

## Préparation

- dépôt Git distant contenant ce code et une suite de tests verte ;
- point d’entrée `demo/app.py` ;
- dépendances dans `requirements.txt` ;
- aucune clé dans Git, l’historique ou un fichier `.env` ;
- secret `OPENAI_API_KEY` configuré dans l’interface Streamlit Community Cloud.

## Déployer

1. Sur Streamlit Community Cloud, créer une application depuis le dépôt NormLab.
2. Choisir la branche candidate et `demo/app.py` comme main file.
3. Dans les secrets de l’application, ajouter uniquement :

   ```toml
   OPENAI_API_KEY = "..."
   ```

4. Déployer, attendre un démarrage propre puis noter l’URL dans le README et dans le
   journal de `BUILD_WEEK.md` avec date, commit et résultat du smoke test.

Une URL n’est déclarée « accessible au jury » qu’après test dans une session sans
authentification au dépôt ou à Streamlit.

## Smoke test public

- la page charge et affiche immédiatement « Pas une prévision » ;
- la pastille confirme « GPT‑5.6 Sol actif » ;
- une question libre produit un protocole et une critique inspectables ;
- les onglets distinguent fourni, inféré et défaut ;
- le protocole ne s’exécute qu’après approbation ;
- le tableau principal contient quatre stratégies avec le même nombre de pilotes ;
- broadcast apparaît hors classement ;
- la sensibilité et l’équivalence seuil/visibilité sont visibles ;
- la fiche comporte Résultats, Hypothèses, Limites et Prochaine donnée ;
- les trois exports JSON fonctionnent et la trace n’expose ni clé ni raisonnement ;
- un second lancement du même protocole produit le même `result_id`.

## Retour arrière

Conserver le dernier commit dont les tests et le smoke test public sont verts. En cas
d’échec de l’API, la page doit signaler l’erreur et ne pas présenter une fiche comme
terminée. Le mode fixture reste destiné aux tests et à la démonstration locale ; il ne
doit pas être confondu avec une démonstration Sol réussie.
