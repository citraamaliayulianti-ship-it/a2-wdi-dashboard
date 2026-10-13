from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT = Path(__file__).resolve().parents[1]
PAGES = [
    "sections/1_income_and_life_expectancy.py",
    "sections/2_longer_or_shorter.py",
    "sections/3_spending_or_pollution.py",
    "sections/4_conclusion.py",
    "sections/5_country_spotlight.py",
]


def _app(monkeypatch, page: str | None = None) -> AppTest:
    monkeypatch.setenv("DASHBOARD_SAMPLE_MODE", "1")
    app = AppTest.from_file(str(ROOT / "app.py"), default_timeout=30).run()
    if page:
        app.switch_page(page).run()
    return app


def test_overview_renders(monkeypatch) -> None:
    app = _app(monkeypatch)
    assert not app.exception
    assert any("Does getting richer mean living longer?" in item.value for item in app.markdown)


def test_every_page_renders(monkeypatch) -> None:
    for page in PAGES:
        app = _app(monkeypatch, page)
        assert not app.exception, page
        assert app.header, page


def test_empty_income_selection_shows_message(monkeypatch) -> None:
    app = _app(monkeypatch, PAGES[0])
    app.multiselect(key="income_health_income").set_value([]).run()
    assert any("No countries match" in item.value for item in app.info)


def test_factor_switch_runs(monkeypatch) -> None:
    app = _app(monkeypatch, PAGES[2])
    app.radio(key="factors_choice").set_value("PM2.5 air pollution (µg/m³)").run()
    assert not app.exception


def test_spotlight_switches_country(monkeypatch) -> None:
    app = _app(monkeypatch, PAGES[4])
    app.selectbox(key="spotlight_country").set_value("Nigeria").run()
    assert not app.exception
    assert any("Nigeria" in item.value for item in app.markdown)
