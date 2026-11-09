"""Pure calculation helpers for the Heimdall dashboard (no Streamlit dependency)."""

import pandas as pd

RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70


def calculate_rsi(prices: pd.Series, period: int = RSI_PERIOD) -> pd.Series:
    """Relative Strength Index using Wilder's smoothing.

    The first `period` values are NaN because there is not enough history yet.
    """
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    # No losses at all in the window means RSI is 100 by definition.
    rsi = rsi.where(~((avg_loss == 0) & (avg_gain > 0)), 100.0)
    return rsi


def classify_rsi(value: float) -> str:
    """Return a short label for an RSI value."""
    if pd.isna(value):
        return "Not enough data"
    if value < RSI_OVERSOLD:
        return "Oversold"
    if value > RSI_OVERBOUGHT:
        return "Overbought"
    return "Neutral"


def format_split_ratio(ratio: float) -> str:
    """Human-readable split ratio, e.g. 10.0 -> '10-for-1', 0.1 -> '1-for-10 (reverse)'."""
    if ratio >= 1:
        return f"{ratio:g}-for-1"
    return f"1-for-{1 / ratio:g} (reverse)"
