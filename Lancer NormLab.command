#!/bin/zsh
# Lanceur macOS en double-clic pour la démo locale NormLab.
# Aucune clé API n'est enregistrée ici : elle reste saisie dans l'application.

set -e

cd "$(dirname "$0")"

if lsof -nP -iTCP:8501 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Une application utilise déjà http://localhost:8501."
  echo "Si c'est une ancienne instance de NormLab, revenez dans sa fenêtre Terminal,"
  echo "arrêtez-la avec Ctrl+C, puis relancez ce fichier une seule fois."
  read "?Appuyez sur Entrée pour fermer cette fenêtre..."
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "Python 3 est requis pour lancer NormLab."
  echo "Installe Python 3, puis relance ce fichier."
  read "?Appuyez sur Entrée pour fermer cette fenêtre..."
  exit 1
fi

if [[ ! -x ".venv/bin/python" ]]; then
  echo "Préparation de l'environnement local (premier lancement uniquement)…"
  python3 -m venv .venv
fi

NORM_PYTHON=".venv/bin/python"
if ! "$NORM_PYTHON" -c "import streamlit, normlab" >/dev/null 2>&1; then
  echo "Installation des dépendances NormLab…"
  "$NORM_PYTHON" -m pip install --upgrade pip
  "$NORM_PYTHON" -m pip install -e '.[dev]'
fi

echo "NormLab démarre. Le navigateur va s'ouvrir sur http://localhost:8501"
( sleep 2; open "http://localhost:8501" ) &
"$NORM_PYTHON" -m streamlit run demo/app.py --server.port 8501
