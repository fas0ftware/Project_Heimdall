import streamlit as st
import yfinance as yf
import plotly.graph_objects as go

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Aesthesius Global Dashboard",
    page_icon="🦅",
    layout="wide"
)

# --- ASCII SIGNATURE (BRANDING) ---
st.code(r"""
     _    ____ ____ _____ _   _ _____ ____ ___ _   _ ____  
    / \  |  __|  __|__ __| | | |  __|  __||_ _| | | |  __| 
   / _ \ |  __|__  |  |  | |_| |  __|__  | | || |_| |__  | 
  /_/ \_\|____|____|  |  |_|___|____|____|___|___/|____| 
     >>> MARKET ORACLE SYSTEM v2.0 (GLOBAL) <<<
""", language="text")

# --- 2. SIDEBAR (CONTROL PANEL) ---
st.sidebar.header("⚙️ Control Panel")

# Ticker Selection
selected_ticker = st.sidebar.selectbox(
    "Select Ticker:",
    ("AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "AMZN", "META", "COIN")
)

# Time Range Selection
time_range = st.sidebar.selectbox(
    "Time Range:",
    ("1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "max")
)

st.sidebar.markdown("---")

# Investment Input for Time Machine
st.sidebar.subheader("💰 Time Machine")
investment_amount = st.sidebar.number_input(
    "Initial Investment ($):",
    min_value=100,
    value=1000,
    step=100
)

# --- 3. DATA ENGINE (BACKEND) ---
@st.cache_data
def get_stock_data(ticker, period):
    """
    Fetches historical stock data from Yahoo Finance.
    Includes stock split actions for analysis.
    """
    stock = yf.Ticker(ticker)
    # actions=True is crucial to detect stock splits
    df = stock.history(period=period, actions=True)
    return df

# Fetch Data
with st.spinner('Fetching data from Wall Street...'):
    df = get_stock_data(selected_ticker, time_range)

# --- 4. VISUALIZATION & LOGIC ---
if not df.empty:
    
    # --- SPLIT DETECTOR LOGIC ---
    # Filter rows where 'Stock Splits' is greater than 0
    splits = df[df['Stock Splits'] > 0]
    
    if not splits.empty:
        st.warning(f"⚠️ **NOTICE:** {selected_ticker} underwent **{len(splits)} stock split(s)** during this period.")
        for date, row in splits.iterrows():
            ratio = row['Stock Splits']
            st.caption(f"📅 **{date.strftime('%Y-%m-%d')}**: Split ratio **1:{int(ratio)}**")
    
    # --- TIME MACHINE CALCULATION ---
    initial_price = df['Close'].iloc[0]  # Price at the start of the period
    final_price = df['Close'].iloc[-1]   # Current price
    
    # Calculate how many shares could be bought
    shares_bought = investment_amount / initial_price
    
    # Calculate current value of that investment
    current_value = shares_bought * final_price
    
    # Calculate Profit/Loss
    profit_loss = current_value - investment_amount
    percentage_change = ((final_price - initial_price) / initial_price) * 100

    # --- DISPLAY METRICS ---
    st.markdown(f"### 📊 Analysis Report: {selected_ticker}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("Current Price", f"${final_price:.2f}", f"{percentage_change:.1f}%")
    col2.metric("Entry Price (Adj)", f"${initial_price:.2f}")
    col3.metric("Initial Investment", f"${investment_amount:,.0f}")
    
    # Conditional formatting for Profit (Green) or Loss (Red)
    if profit_loss >= 0:
        col4.metric("Total Value", f"${current_value:,.2f}", f"+${profit_loss:.2f}", delta_color="normal")
    else:
        col4.metric("Total Value", f"${current_value:,.2f}", f"-${abs(profit_loss):.2f}", delta_color="inverse")

    # Scenario Description
    st.info(f"💡 **Scenario:** If you had invested **${investment_amount}** in **{selected_ticker}** {time_range} ago, you would have **{shares_bought:.2f} shares**, now worth **${current_value:,.2f}**.")

    # --- PLOTLY CHART ---
    st.subheader("📈 Price History & Split Events")
    
    fig = go.Figure()
    
    # Main Price Line
    fig.add_trace(go.Scatter(
        x=df.index, 
        y=df['Close'], 
        mode='lines', 
        name='Close Price',
        line=dict(color='#00ff00', width=2)
    ))
    
    # Annotate Splits on the Chart
    for date, row in splits.iterrows():
        fig.add_annotation(
            x=date, 
            y=row['Close'],
            text="SPLIT", 
            showarrow=True, 
            arrowhead=1,
            bgcolor="yellow", 
            bordercolor="black", 
            font=dict(color="black")
        )

    # Chart Layout Settings
    fig.update_layout(
        title=f"{selected_ticker} Performance ({time_range})",
        xaxis_title="Date",
        yaxis_title="Price (USD)",
        template="plotly_dark", # Dark mode for professional look
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # Raw Data Expander
    with st.expander("📂 View Raw Historical Data"):
        st.dataframe(df)

else:
    st.error("❌ Error: Could not fetch data. Please check your connection or ticker symbol.")

# --- FOOTER ---
st.markdown("---")
st.caption("🦅 **Aesthesius Systems** | Developed by Anıl | Powered by Yahoo Finance API")