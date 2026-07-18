from __future__ import annotations

from streamlit.testing.v1 import AppTest


def test_offline_user_journey_reaches_separated_decision_card(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = AppTest.from_file("demo/app.py", default_timeout=30).run()
    assert not app.exception
    assert len(app.button) == 1

    app.button[0].click().run()
    assert not app.exception
    assert len(app.button) == 2
    assert any("fixture déterministe" in item.value for item in app.warning)

    app.button[1].click().run(timeout=30)
    assert not app.exception
    labels = {item.label for item in app.metric}
    assert {"Leader central", "Budget comparable", "Classement sensible"} <= labels
    assert len(app.download_button) == 3
    assert any("Non-identifiabilité" in item.value for item in app.warning)
    assert any("Pas une prévision" in item.value for item in app.markdown)
