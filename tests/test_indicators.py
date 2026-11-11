import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import math  # noqa: E402

import numpy as np  # noqa: E402
import pytest  # noqa: E402

from indicators import (bollinger, calculate_rsi, classify_rsi, correlation, dca,  # noqa: E402
                        demo_history, drawdown_series, format_split_ratio, lump_sum,
                        ma_crosses, macd, max_drawdown, normalize, normalize_ticker,
                        risk_stats, sma)


def daily(values, start="2024-01-01"):
    return pd.Series(values, index=pd.bdate_range(start, periods=len(values)), dtype=float)


def test_rsi_all_gains_is_100():
    prices = pd.Series(range(1, 40), dtype=float)
    assert calculate_rsi(prices).iloc[-1] == 100


def test_rsi_all_losses_is_0():
    prices = pd.Series(range(40, 1, -1), dtype=float)
    assert calculate_rsi(prices).iloc[-1] < 1e-9


def test_rsi_warmup_is_nan():
    prices = pd.Series(range(1, 40), dtype=float)
    rsi = calculate_rsi(prices)
    assert rsi.iloc[:14].isna().all()
    assert not pd.isna(rsi.iloc[14])


def test_rsi_stays_in_range():
    prices = pd.Series([10, 11, 10.5, 12, 11.8, 13, 12.2, 12.9, 11, 10, 9.5, 10.2,
                        11.1, 12.4, 12.0, 13.3, 12.7, 13.9, 14.2, 13.1], dtype=float)
    rsi = calculate_rsi(prices).dropna()
    assert ((rsi >= 0) & (rsi <= 100)).all()


def test_classify_rsi():
    assert classify_rsi(float("nan")) == "Not enough data"
    assert classify_rsi(25) == "Oversold"
    assert classify_rsi(50) == "Neutral"
    assert classify_rsi(75) == "Overbought"


def test_format_split_ratio():
    assert format_split_ratio(10.0) == "10-for-1"
    assert format_split_ratio(1.5) == "1.5-for-1"
    assert format_split_ratio(0.1) == "1-for-10 (reverse)"



# --- v2 -------------------------------------------------------------------------

@pytest.mark.parametrize("raw,expected", [
    ("aapl", "AAPL"), (" brk-b ", "BRK-B"), ("thyao.is", "THYAO.IS"), ("^gspc", "^GSPC"),
    ("eurusd=x", "EURUSD=X"), ("btc-usd", "BTC-USD"), ("GC=F", "GC=F"),
    ("", None), ("AAPL; rm -rf", None), ("<script>", None), ("A" * 20, None), ("../x", None),
])
def test_normalize_ticker(raw, expected):
    assert normalize_ticker(raw) == expected


def test_sma_and_bollinger():
    p = daily(range(1, 31))
    assert sma(p, 5).iloc[4] == 3 and sma(p, 5).iloc[:4].isna().all()
    bb = bollinger(p, window=20)
    last = bb.iloc[-1]
    assert last["lower"] < last["mid"] < last["upper"]
    assert last["mid"] == pytest.approx(p.iloc[-20:].mean())
    flat = bollinger(daily([5.0] * 25))
    assert (flat.dropna()["upper"] == 5).all()


def test_macd_sign_follows_trend():
    up = macd(daily(np.linspace(10, 50, 120)))
    down = macd(daily(np.linspace(50, 10, 120)))
    assert up["macd"].iloc[-1] > 0 and down["macd"].iloc[-1] < 0
    assert (up["hist"] == up["macd"] - up["signal"]).all()


def test_golden_and_death_cross_detected():
    # falls, then rises strongly (golden cross), then falls hard (death cross)
    path = list(np.linspace(100, 60, 260)) + list(np.linspace(60, 200, 260)) + list(np.linspace(200, 40, 260))
    crosses = ma_crosses(daily(path), fast=50, slow=200)
    assert list(crosses["kind"]) == ["golden", "death"]
    assert crosses.index.is_monotonic_increasing


def test_no_cross_without_enough_history():
    assert ma_crosses(daily(range(1, 100))).empty


def test_max_drawdown_and_series():
    p = daily([100, 120, 60, 90, 130, 65])
    assert max_drawdown(p) == pytest.approx(-0.5)
    dd = drawdown_series(p)
    assert dd.iloc[0] == 0 and dd.min() == pytest.approx(-0.5) and (dd <= 0).all()


def test_risk_stats_known_values():
    p = daily([100.0 * 1.001 ** i for i in range(253)])  # constant +0.1 % per day
    r = risk_stats(p)
    assert r.total_return == pytest.approx(1.001 ** 252 - 1)
    assert r.volatility == pytest.approx(0, abs=1e-9) and r.sharpe is None
    assert r.max_drawdown == 0 and r.cagr is not None and r.cagr > 0.25
    with pytest.raises(ValueError):
        risk_stats(daily([1.0]))


def test_risk_stats_short_period_has_no_cagr():
    assert risk_stats(daily([10, 11, 12, 11, 13])).cagr is None


def test_lump_sum():
    sim = lump_sum(daily([10, 20, 40]), 1000)
    assert sim.shares == 100 and sim.value == 4000 and sim.profit == 3000 and sim.roi == 3


def test_dca_buys_once_per_month():
    idx = pd.bdate_range("2024-01-01", "2024-03-29")
    p = pd.Series(10.0, index=idx)
    sim, value = dca(p, 1000, 100)
    assert sim.invested == 1000 + 100 * 2  # Jan initial, then Feb and Mar
    assert sim.value == pytest.approx(1200) and sim.shares == pytest.approx(120)
    assert value.iloc[0] == pytest.approx(1000)


def test_dca_beats_lump_sum_in_a_falling_then_recovering_market():
    p = daily(list(np.linspace(100, 50, 120)) + list(np.linspace(50, 100, 120)))
    sim, _ = dca(p, 1000, 200)
    assert sim.roi > lump_sum(p, 1000).roi


def test_normalize_and_correlation():
    df = pd.DataFrame({"A": [2.0, 4.0, 6.0], "B": [10.0, 5.0, 20.0]})
    n = normalize(df)
    assert list(n.iloc[0]) == [100, 100] and n["A"].iloc[-1] == 300
    c = correlation(pd.DataFrame({"A": [1.0, 2, 3, 2, 4], "B": [2.0, 4, 6, 4, 8]}))
    assert c.loc["A", "B"] == pytest.approx(1)


def test_demo_history_shape_and_determinism():
    a, b = demo_history("AAPL", "1y"), demo_history("AAPL", "1y")
    pd.testing.assert_frame_equal(a, b)
    assert len(a) == 252 and set(["Open", "High", "Low", "Close", "Volume", "Stock Splits"]) <= set(a)
    assert (a["High"] >= a[["Open", "Close"]].max(axis=1)).all()
    assert (a["Low"] <= a[["Open", "Close"]].min(axis=1)).all()
    assert not demo_history("TSLA", "1y")["Close"].equals(a["Close"])
    assert (demo_history("AAPL", "2y")["Stock Splits"] > 0).sum() == 1
    assert math.isfinite(risk_stats(a["Close"]).volatility)
