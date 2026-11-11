"""Pure calculation helpers for the Heimdall dashboard (no Streamlit dependency).

Everything here takes pandas objects in and returns pandas objects or plain
numbers out, so it is easy to test and to reuse from other tools.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

import numpy as np
import pandas as pd

RSI_PERIOD = 14
RSI_OVERSOLD = 30
RSI_OVERBOUGHT = 70
TRADING_DAYS = 252

# Yahoo symbols: AAPL, BRK-B, THYAO.IS, ^GSPC, EURUSD=X, BTC-USD
_TICKER_RE = re.compile(r"^\^?[A-Z0-9][A-Z0-9.\-]{0,14}(=X|=F)?$")


def normalize_ticker(raw: str) -> str | None:
    """Upper-case and validate a Yahoo Finance symbol; None if it is not one."""
    t = (raw or "").strip().upper()
    return t if _TICKER_RE.match(t) else None


# --- Momentum / trend -----------------------------------------------------------

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


def sma(prices: pd.Series, window: int) -> pd.Series:
    return prices.rolling(window, min_periods=window).mean()


def macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
    """MACD line, signal line and histogram."""
    ema_fast = prices.ewm(span=fast, adjust=False).mean()
    ema_slow = prices.ewm(span=slow, adjust=False).mean()
    line = ema_fast - ema_slow
    sig = line.ewm(span=signal, adjust=False).mean()
    return pd.DataFrame({"macd": line, "signal": sig, "hist": line - sig})


def bollinger(prices: pd.Series, window: int = 20, k: float = 2.0) -> pd.DataFrame:
    mid = sma(prices, window)
    std = prices.rolling(window, min_periods=window).std(ddof=0)
    return pd.DataFrame({"mid": mid, "upper": mid + k * std, "lower": mid - k * std})


def ma_crosses(prices: pd.Series, fast: int = 50, slow: int = 200) -> pd.DataFrame:
    """Dates where the fast SMA crosses the slow SMA.

    Returns a DataFrame indexed by date with a `kind` column: 'golden' (fast
    crosses above slow) or 'death' (fast crosses below)."""
    f, s = sma(prices, fast), sma(prices, slow)
    above = (f > s).where(f.notna() & s.notna())
    prev = above.shift(1)
    valid = above.notna() & prev.notna()
    golden = valid & (above == 1) & (prev == 0)
    death = valid & (above == 0) & (prev == 1)
    out = pd.DataFrame(index=prices.index[golden | death])
    out["kind"] = np.where(golden[golden | death], "golden", "death")
    out["price"] = prices[golden | death]
    return out


# --- Risk / return --------------------------------------------------------------

@dataclass(frozen=True)
class RiskStats:
    total_return: float      # 0.25 = +25 %
    cagr: float | None       # annualized, None for < 30 days of data
    volatility: float        # annualized std of daily returns
    max_drawdown: float      # -0.30 = worst peak-to-trough drop of 30 %
    sharpe: float | None     # annualized, risk-free rate 0
    best_day: float
    worst_day: float


def max_drawdown(prices: pd.Series) -> float:
    peak = prices.cummax()
    dd = prices / peak - 1
    return float(dd.min()) if len(dd) else 0.0


def drawdown_series(prices: pd.Series) -> pd.Series:
    return prices / prices.cummax() - 1


def risk_stats(prices: pd.Series) -> RiskStats:
    prices = prices.dropna()
    if len(prices) < 2:
        raise ValueError("Need at least two prices.")
    rets = prices.pct_change().dropna()
    total = float(prices.iloc[-1] / prices.iloc[0] - 1)
    days = (prices.index[-1] - prices.index[0]).days if isinstance(prices.index, pd.DatetimeIndex) else len(prices)
    cagr = (1 + total) ** (365.25 / days) - 1 if days >= 30 and total > -1 else None
    vol = float(rets.std(ddof=1) * math.sqrt(TRADING_DAYS)) if len(rets) > 1 else 0.0
    mean = float(rets.mean()) * TRADING_DAYS
    sharpe = mean / vol if vol > 1e-12 else None
    return RiskStats(total, cagr, vol, max_drawdown(prices), sharpe,
                     float(rets.max()) if len(rets) else 0.0, float(rets.min()) if len(rets) else 0.0)


# --- Investment simulations -------------------------------------------------------

@dataclass(frozen=True)
class Simulation:
    invested: float
    shares: float
    value: float

    @property
    def profit(self) -> float:
        return self.value - self.invested

    @property
    def roi(self) -> float:
        return self.profit / self.invested if self.invested else 0.0


def lump_sum(prices: pd.Series, amount: float) -> Simulation:
    prices = prices.dropna()
    shares = amount / float(prices.iloc[0])
    return Simulation(amount, shares, shares * float(prices.iloc[-1]))


def dca(prices: pd.Series, amount: float, monthly: float) -> tuple[Simulation, pd.Series]:
    """Initial `amount` on day one, then `monthly` on the first trading day of
    every following month. Returns the result and the portfolio value over time."""
    prices = prices.dropna()
    if not isinstance(prices.index, pd.DatetimeIndex):
        raise TypeError("dca needs a DatetimeIndex")
    month = prices.index.to_period("M")
    first_of_month = ~month.duplicated()
    buys = pd.Series(0.0, index=prices.index)
    buys[first_of_month] = monthly
    buys.iloc[0] = amount
    shares = (buys / prices).cumsum()
    value = shares * prices
    invested = float(buys.sum())
    return Simulation(invested, float(shares.iloc[-1]), float(value.iloc[-1])), value


# --- Comparison -------------------------------------------------------------------

def normalize(prices: pd.DataFrame | pd.Series, base: float = 100.0):
    """Rebase every column so it starts at `base` (first non-NaN value)."""
    first = prices.bfill().iloc[0]
    return prices / first * base


def correlation(closes: pd.DataFrame) -> pd.DataFrame:
    return closes.pct_change().corr()


# --- Splits -------------------------------------------------------------------------

def format_split_ratio(ratio: float) -> str:
    """Human-readable split ratio, e.g. 10.0 -> '10-for-1', 0.1 -> '1-for-10 (reverse)'."""
    if ratio >= 1:
        return f"{ratio:g}-for-1"
    return f"1-for-{1 / ratio:g} (reverse)"


# --- Demo data ----------------------------------------------------------------------

def demo_history(ticker: str, period: str = "1y", seed: int | None = None) -> pd.DataFrame:
    """Deterministic synthetic OHLCV history (geometric Brownian motion) shaped
    like a yfinance frame. Used by demo mode and tests; never real prices."""
    days = {"1mo": 21, "3mo": 63, "6mo": 126, "1y": 252, "2y": 504, "5y": 1260,
            "10y": 2520, "max": 2520}.get(period, 252)
    rng = np.random.default_rng(seed if seed is not None else sum(map(ord, ticker)) * 7919)
    drift, vol = rng.uniform(-0.05, 0.35), rng.uniform(0.18, 0.55)
    rets = rng.normal(drift / TRADING_DAYS, vol / math.sqrt(TRADING_DAYS), days)
    close = 50 * rng.uniform(0.5, 6) * np.exp(np.cumsum(rets))
    idx = pd.bdate_range(end=pd.Timestamp("2026-11-06"), periods=days, name="Date")
    spread = np.abs(rng.normal(0, vol / 25, days)) * close
    open_ = close * (1 + rng.normal(0, vol / 40, days))
    df = pd.DataFrame({
        "Open": open_,
        "High": np.maximum(open_, close) + spread,
        "Low": np.minimum(open_, close) - spread,
        "Close": close,
        "Volume": rng.integers(5_000_000, 90_000_000, days),
        "Dividends": 0.0,
        "Stock Splits": 0.0,
    }, index=idx)
    if days > 300:  # one illustrative split
        at = idx[days // 2]
        df.loc[at, "Stock Splits"] = 4.0
    return df
