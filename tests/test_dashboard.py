"""Headless UI tests with Streamlit AppTest in offline demo mode."""
import os

import pytest

st_testing = pytest.importorskip("streamlit.testing.v1")
APP = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "dashboard.py")


@pytest.fixture
def at(monkeypatch):
    monkeypatch.setenv("HEIMDALL_DEMO", "1")
    return st_testing.AppTest.from_file(APP, default_timeout=60)


def test_renders_all_tabs_without_errors(at):
    at.run()
    assert not at.exception and not at.error
    assert [t.label for t in at.tabs] == ["📊 Analysis", "⏳ Time Machine", "⚖️ Compare", "📂 Data"]
    labels = [m.label for m in at.metric]
    for want in ("Last close", "RSI (14)", "CAGR", "Volatility (ann.)", "Max drawdown", "Sharpe (rf=0)"):
        assert want in labels
    assert at.info[0].value.startswith("Demo mode")


def test_time_machine_reports_invested_amounts(at):
    at.run()
    at.sidebar.number_input[0].set_value(2000)
    at.sidebar.number_input[1].set_value(0)
    at.run()
    captions = " ".join(c.value for c in at.caption)
    assert captions.count("Invested $2,000.00") == 2  # lump sum == DCA with no monthly money


def test_invalid_custom_ticker_is_rejected(at):
    at.run()
    at.sidebar.selectbox[0].set_value("Other...").run()
    at.sidebar.text_input[0].set_value("AAPL; DROP TABLE").run()
    assert at.error and "not a valid ticker" in at.error[0].value


def test_custom_ticker_and_query_params(at):
    at.query_params["t"] = "thyao.is"
    at.query_params["r"] = "2y"
    at.run()
    assert not at.exception
    # split marker in 2y demo data
    assert any("stock split" in w.value for w in at.warning)


def test_compare_tab_builds_table(at):
    at.run()
    assert not at.exception
    assert len(at.dataframe) >= 3  # risk table, correlation, raw data
