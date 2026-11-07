"""
Stock closing-price dashboard (last 1 year) with 50- and 200-day moving averages.

Setup (once):   pip install yfinance streamlit plotly
Run:            streamlit run stock_dashboard.py
Then open:      http://localhost:8501  (usually opens automatically)
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Stock Dashboard", layout="wide")
st.title("Stock Closing Prices — Last 12 Months")

ticker = st.text_input("Ticker symbol", value="AAPL").strip().upper()


@st.cache_data(ttl=3600)  # cache each ticker for an hour
def load_prices(symbol: str):
    # Pull 2 years so the 200-day average is fully formed across the whole
    # 1-year window shown, then trim to the last 12 months.
    df = yf.Ticker(symbol).history(period="2y", interval="1d")[["Close"]].dropna()
    if df.empty:
        return df
    df["MA50"] = df["Close"].rolling(window=50).mean()
    df["MA200"] = df["Close"].rolling(window=200).mean()
    cutoff = df.index[-1] - pd.DateOffset(years=1)
    return df[df.index >= cutoff]


if ticker:
    with st.spinner(f"Fetching {ticker} from Yahoo Finance..."):
        data = load_prices(ticker)

    if data.empty:
        st.error(f"No data found for '{ticker}'. Check the symbol and try again.")
    else:
        first, last = data["Close"].iloc[0], data["Close"].iloc[-1]
        change = (last - first) / first * 100

        c1, c2, c3 = st.columns(3)
        c1.metric("Latest close", f"${last:,.2f}")
        c2.metric("1-year change", f"{change:+.1f}%")
        c3.metric("1-year range",
                  f"${data['Close'].min():,.2f} – ${data['Close'].max():,.2f}")

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=data.index, y=data["Close"], mode="lines",
                                 name=f"{ticker} close",
                                 line=dict(color="#1f77b4", width=2)))
        fig.add_trace(go.Scatter(x=data.index, y=data["MA50"], mode="lines",
                                 name="50-day MA",
                                 line=dict(color="green", width=1.5)))
        fig.add_trace(go.Scatter(x=data.index, y=data["MA200"], mode="lines",
                                 name="200-day MA",
                                 line=dict(color="red", width=1.5)))
        fig.update_layout(xaxis_title="Date", yaxis_title="Price (USD)",
                          hovermode="x unified", height=500,
                          legend=dict(orientation="h", y=1.02, x=0),
                          margin=dict(l=20, r=20, t=30, b=20))
        st.plotly_chart(fig, use_container_width=True)

        with st.expander("Show raw data"):
            st.dataframe(data.sort_index(ascending=False).round(2))
