import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from indicators import calculate_rsi, classify_rsi, format_split_ratio  # noqa: E402


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


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
