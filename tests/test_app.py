from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]


def _app(monkeypatch) -> AppTest:
    monkeypatch.setenv("DASHBOARD_SAMPLE_MODE", "1")
    return AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()


def test_app_renders(monkeypatch) -> None:
    app = _app(monkeypatch)
    assert not app.exception
    assert app.title[0].value == "Does getting richer mean living longer?"


def test_empty_income_selection_shows_message(monkeypatch) -> None:
    app = _app(monkeypatch)
    app.multiselect(key="income_health_income").set_value([]).run()
    assert any("No countries match" in item.value for item in app.info)


def test_factor_switch_runs(monkeypatch) -> None:
    app = _app(monkeypatch)
    app.radio(key="factors_choice").set_value("PM2.5 air pollution (µg/m³)").run()
    assert not app.exception
