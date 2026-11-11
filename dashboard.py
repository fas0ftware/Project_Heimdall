"""Heimdall | Market Dashboard (Streamlit)."""

import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

from indicators import (
    RSI_OVERBOUGHT,
    RSI_OVERSOLD,
    RSI_PERIOD,
    bollinger,
    calculate_rsi,
    classify_rsi,
    correlation,
    dca,
    demo_history,
    drawdown_series,
    format_split_ratio,
    lump_sum,
    ma_crosses,
    macd,
    normalize,
    normalize_ticker,
    risk_stats,
    sma,
)

__version__ = "2.0.0"

PRESETS = ("AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "AMZN", "META", "COIN")
RANGES = ("1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max")
GREEN, RED, PURPLE, ORANGE, BLUE = "#26a69a", "#ef5350", "#ab63fa", "#ffa726", "#42a5f5"

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(page_title="Heimdall | Market Dashboard", page_icon="🦅", layout="wide")


# --- 2. DATA ENGINE ---
@st.cache_data(ttl=900, show_spinner=False)
def get_stock_data(ticker: str, period: str, demo: bool) -> pd.DataFrame:
    """Daily OHLCV history. Prices are split/dividend-adjusted by yfinance and
    the Stock Splits column is kept so splits can be detected and marked."""
    if demo:
        return demo_history(ticker, period)
    import yfinance as yf  # imported lazily so demo mode works offline

    try:
        df = yf.Ticker(ticker).history(period=period, actions=True, auto_adjust=True)
    except Exception:  # network errors, unknown symbols
        return pd.DataFrame()
    if df.empty or "Close" not in df:
        return pd.DataFrame()
    if "Stock Splits" not in df:
        df["Stock Splits"] = 0.0
    df.index = df.index.tz_localize(None) if getattr(df.index, "tz", None) is not None else df.index
    return df


def money(x: float) -> str:
    return f"-${abs(x):,.2f}" if x < 0 else f"${x:,.2f}"


def pct(x) -> str:
    return "n/a" if x is None else f"{x * 100:+.1f}%"


# --- 3. SIDEBAR (CONTROL PANEL) ---
st.title("🦅 Heimdall | Market Dashboard")
st.caption("Signals, risk and 'what if' simulations for any Yahoo Finance symbol.")

qp = st.query_params
demo_default = os.getenv("HEIMDALL_DEMO") == "1"

st.sidebar.header("⚙️ Control Panel")
demo = st.sidebar.toggle("Offline demo data", value=demo_default,
                         help="Synthetic prices, no network. Useful for trying the app.")
preset_idx = PRESETS.index(qp["t"]) if qp.get("t") in PRESETS else 0
choice = st.sidebar.selectbox("Ticker", PRESETS + ("Other...",), index=preset_idx)
raw = st.sidebar.text_input("Symbol (e.g. BRK-B, THYAO.IS, ^GSPC, BTC-USD)",
                            value=qp.get("t", "") if qp.get("t") not in PRESETS else "") \
    if choice == "Other..." else choice
ticker = normalize_ticker(raw)
time_range = st.sidebar.selectbox("Time range", RANGES,
                                  index=RANGES.index(qp["r"]) if qp.get("r") in RANGES else 3)

st.sidebar.markdown("---")
st.sidebar.subheader("📈 Chart overlays")
show_sma = st.sidebar.checkbox("SMA 50 / 200", value=True)
show_bb = st.sidebar.checkbox("Bollinger Bands (20, 2σ)", value=False)
candles = st.sidebar.checkbox("Candlesticks", value=False)

st.sidebar.markdown("---")
st.sidebar.subheader("💰 Time Machine")
investment_amount = st.sidebar.number_input("Initial investment ($)", min_value=100, value=1000, step=100)
monthly = st.sidebar.number_input("Monthly contribution ($)", min_value=0, value=100, step=50)

if not ticker:
    st.error("❌ That is not a valid ticker symbol. Use letters, digits, '.', '-' (e.g. BRK-B).")
    st.stop()
qp["t"], qp["r"] = ticker, time_range

with st.spinner(f"Fetching {ticker}..."):
    df = get_stock_data(ticker, time_range, demo)

if df.empty:
    st.error(f"❌ Could not fetch data for **{ticker}**. Check the symbol or your connection, "
             "or turn on *Offline demo data* in the sidebar.")
    st.stop()

if demo:
    st.info("🧪 Demo mode: synthetic prices for illustration only.")

close = df["Close"]
df["RSI"] = calculate_rsi(close, RSI_PERIOD)
splits = df[df["Stock Splits"] > 0]
stats = risk_stats(close)
latest_rsi = df["RSI"].iloc[-1]

TABS = {"analysis": "📊 Analysis", "machine": "⏳ Time Machine", "compare": "⚖️ Compare", "data": "📂 Data"}
tab_analysis, tab_machine, tab_compare, tab_data = st.tabs(
    list(TABS.values()), default=TABS.get(qp.get("view", ""), TABS["analysis"]))

# --- 4. ANALYSIS ---
with tab_analysis:
    if not splits.empty:
        items = ", ".join(f"{d.strftime('%Y-%m-%d')} ({format_split_ratio(r)})"
                          for d, r in splits["Stock Splits"].items())
        st.warning(f"⚠️ {ticker} had **{len(splits)} stock split(s)** in this period: {items}. "
                   "Prices are split-adjusted, so the chart has no artificial drop.")

    c = st.columns(6)
    c[0].metric("Last close", money(close.iloc[-1]), pct(stats.total_return))
    rsi_label = classify_rsi(latest_rsi)
    c[1].metric(f"RSI ({RSI_PERIOD})", "n/a" if pd.isna(latest_rsi) else f"{latest_rsi:.1f}",
                rsi_label, delta_color="off", delta_arrow="off")
    c[2].metric("CAGR", pct(stats.cagr))
    c[3].metric("Volatility (ann.)", f"{stats.volatility * 100:.1f}%")
    c[4].metric("Max drawdown", f"{stats.max_drawdown * 100:.1f}%")
    c[5].metric("Sharpe (rf=0)", "n/a" if stats.sharpe is None else f"{stats.sharpe:.2f}")

    m = macd(close)
    fig = make_subplots(rows=4, cols=1, shared_xaxes=True, vertical_spacing=0.03,
                        row_heights=[0.5, 0.14, 0.18, 0.18],
                        subplot_titles=("", "Volume", f"RSI ({RSI_PERIOD})", "MACD (12, 26, 9)"))
    if candles:
        fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"],
                                     close=close, name="Price", increasing_line_color=GREEN,
                                     decreasing_line_color=RED), row=1, col=1)
        fig.update_layout(xaxis_rangeslider_visible=False)
    else:
        fig.add_trace(go.Scatter(x=df.index, y=close, mode="lines", name="Close",
                                 line=dict(color=GREEN, width=2)), row=1, col=1)
    if show_sma:
        fig.add_trace(go.Scatter(x=df.index, y=sma(close, 50), name="SMA 50",
                                 line=dict(color=ORANGE, width=1.2)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=sma(close, 200), name="SMA 200",
                                 line=dict(color=BLUE, width=1.2)), row=1, col=1)
        for d, row in ma_crosses(close).iterrows():
            golden = row["kind"] == "golden"
            fig.add_annotation(x=d, y=row["price"], text="Golden ✕" if golden else "Death ✕",
                               showarrow=True, arrowhead=2, ay=-35 if golden else 35,
                               font=dict(color=GREEN if golden else RED, size=11), row=1, col=1)
    if show_bb:
        bb = bollinger(close)
        fig.add_trace(go.Scatter(x=df.index, y=bb["upper"], name="BB upper",
                                 line=dict(color="rgba(200,200,200,0.5)", width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df.index, y=bb["lower"], name="BB lower", fill="tonexty",
                                 fillcolor="rgba(200,200,200,0.08)",
                                 line=dict(color="rgba(200,200,200,0.5)", width=1)), row=1, col=1)
    for d, row in splits.iterrows():
        fig.add_annotation(x=d, y=row["Close"], text=f"SPLIT {format_split_ratio(row['Stock Splits'])}",
                           showarrow=True, arrowhead=1, bgcolor="yellow", font=dict(color="black"),
                           row=1, col=1)

    up = close >= df["Open"]
    fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume",
                         marker_color=[GREEN if u else RED for u in up], opacity=0.6), row=2, col=1)

    fig.add_trace(go.Scatter(x=df.index, y=df["RSI"], name="RSI", line=dict(color=PURPLE, width=1.5)),
                  row=3, col=1)
    fig.add_hrect(y0=RSI_OVERBOUGHT, y1=100, fillcolor="red", opacity=0.12, line_width=0, row=3, col=1)
    fig.add_hrect(y0=0, y1=RSI_OVERSOLD, fillcolor="green", opacity=0.12, line_width=0, row=3, col=1)

    fig.add_trace(go.Bar(x=df.index, y=m["hist"], name="MACD hist",
                         marker_color=[GREEN if h >= 0 else RED for h in m["hist"]], opacity=0.5),
                  row=4, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=m["macd"], name="MACD", line=dict(color=BLUE, width=1.2)),
                  row=4, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=m["signal"], name="Signal", line=dict(color=ORANGE, width=1.2)),
                  row=4, col=1)

    fig.update_layout(title=f"{ticker} · {time_range}", template="plotly_dark", height=820,
                      showlegend=False, margin=dict(t=50, b=20, l=10, r=10))
    fig.update_yaxes(title_text="Price", row=1, col=1)
    fig.update_yaxes(range=[0, 100], row=3, col=1)
    st.plotly_chart(fig, width="stretch")

# --- 5. TIME MACHINE ---
with tab_machine:
    ls = lump_sum(close, investment_amount)
    dc, dca_value = dca(close, investment_amount, monthly)
    st.markdown(f"#### If you had bought **{ticker}** {time_range} ago")
    a, b = st.columns(2)
    with a:
        st.markdown("**Lump sum** – everything on day one")
        st.metric("Value today", money(ls.value), f"{money(ls.profit)} ({pct(ls.roi)})")
        st.caption(f"Invested {money(ls.invested)} · {ls.shares:,.4f} shares")
    with b:
        st.markdown(f"**Dollar-cost averaging** – {money(investment_amount)} + {money(monthly)}/month")
        st.metric("Value today", money(dc.value), f"{money(dc.profit)} ({pct(dc.roi)})")
        st.caption(f"Invested {money(dc.invested)} · {dc.shares:,.4f} shares")

    lump_curve = ls.shares * close
    tm = go.Figure()
    tm.add_trace(go.Scatter(x=close.index, y=lump_curve, name="Lump sum", line=dict(color=GREEN)))
    tm.add_trace(go.Scatter(x=close.index, y=dca_value, name="DCA", line=dict(color=ORANGE)))
    tm.update_layout(template="plotly_dark", height=380, title="Portfolio value",
                     margin=dict(t=50, b=20, l=10, r=10), legend=dict(orientation="h"))
    st.plotly_chart(tm, width="stretch")

    dd = go.Figure(go.Scatter(x=close.index, y=drawdown_series(close) * 100, fill="tozeroy",
                              line=dict(color=RED), name="Drawdown"))
    dd.update_layout(template="plotly_dark", height=260, title="Drawdown from peak (%)",
                     margin=dict(t=50, b=20, l=10, r=10))
    st.plotly_chart(dd, width="stretch")
    st.caption("Historical calculation only – fees, taxes and slippage are ignored.")

# --- 6. COMPARE ---
with tab_compare:
    picks = st.multiselect("Compare with", [p for p in PRESETS if p != ticker],
                           default=[p for p in ("MSFT", "NVDA") if p != ticker][:2])
    extra = normalize_ticker(st.text_input("Add another symbol (optional)", value=""))
    symbols = [ticker] + picks + ([extra] if extra and extra not in picks and extra != ticker else [])
    closes = {s: get_stock_data(s, time_range, demo)["Close"] for s in symbols}
    closes = pd.DataFrame({s: c for s, c in closes.items() if not c.empty}).dropna(how="all")
    if closes.shape[1] < 2:
        st.info("Pick at least one other symbol to compare.")
    else:
        norm = normalize(closes)
        cf = go.Figure([go.Scatter(x=norm.index, y=norm[s], name=s) for s in norm.columns])
        cf.update_layout(template="plotly_dark", height=420, title="Growth of 100 (rebased)",
                         margin=dict(t=50, b=20, l=10, r=10), legend=dict(orientation="h"))
        st.plotly_chart(cf, width="stretch")
        rows = []
        for s in closes.columns:
            r = risk_stats(closes[s])
            rows.append({"Symbol": s, "Return": pct(r.total_return), "CAGR": pct(r.cagr),
                         "Volatility": f"{r.volatility * 100:.1f}%",
                         "Max drawdown": f"{r.max_drawdown * 100:.1f}%",
                         "Sharpe": "n/a" if r.sharpe is None else f"{r.sharpe:.2f}"})
        st.dataframe(pd.DataFrame(rows).set_index("Symbol"), width="stretch")
        st.markdown("**Correlation of daily returns**")
        st.dataframe(correlation(closes).round(2), width="stretch")

# --- 7. DATA ---
with tab_data:
    st.dataframe(df, width="stretch")
    st.download_button("⬇️ Download CSV", df.to_csv().encode("utf-8"),
                       file_name=f"{ticker}_{time_range}.csv", mime="text/csv")

# --- FOOTER ---
st.markdown("---")
st.caption(f"🦅 **FA Software** · Heimdall v{__version__} · Data: Yahoo Finance via yfinance · "
           "Educational use only. Not financial advice.")
