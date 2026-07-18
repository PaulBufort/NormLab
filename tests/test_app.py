from __future__ import annotations

from streamlit.testing.v1 import AppTest


def test_offline_user_journey_reaches_separated_decision_card(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = AppTest.from_file("demo/app.py", default_timeout=30).run()
    assert not app.exception
    assert len(app.button) == 1
    assert any(item.label == "Temporary OpenAI API key" for item in app.text_input)
    temporary_key = next(
        item for item in app.text_input if item.label == "Temporary OpenAI API key"
    )
    assert temporary_key.value == ""

    app.button[0].click().run()
    assert not app.exception
    assert len(app.button) == 2
    assert any("deterministic fixture" in item.value for item in app.warning)

    app.button[1].click().run(timeout=30)
    assert not app.exception
    labels = {item.label for item in app.metric}
    assert {"Base-case leader", "Comparable budget", "Sensitive ranking"} <= labels
    assert len(app.download_button) == 3
    assert any("Non-identifiability" in item.value for item in app.warning)
    assert any("Not a forecast" in item.value for item in app.markdown)


def test_temporary_api_key_can_be_cleared_without_calling_api(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    app = AppTest.from_file("demo/app.py", default_timeout=30).run()
    temporary_key = next(
        item for item in app.text_input if item.label == "Temporary OpenAI API key"
    )

    temporary_key.input("temporary-test-key").run()
    assert not app.exception
    assert any("Temporary key loaded" in item.value for item in app.success)

    clear_button = next(
        item for item in app.button if item.label == "Clear key and session"
    )
    clear_button.click().run()
    assert not app.exception
    cleared_key = next(
        item for item in app.text_input if item.label == "Temporary OpenAI API key"
    )
    assert cleared_key.value == ""
    assert not any("Temporary key loaded" in item.value for item in app.success)
