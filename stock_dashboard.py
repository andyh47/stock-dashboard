"""
Stock closing-price dashboard (last 1 year) with 50- and 200-day moving averages,
plus the current P/E ratio and Peter Lynch's PEGY ratio:

    PEGY = P/E / (dividend yield % + earnings growth rate %)

Growth rate: a 1-year forward analyst projection is used when Yahoo has one;
otherwise the 1-year trailing EPS growth. The dashboard shows which was used.

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


def _num(x):
    """Return x as a float, or None if missing/NaN/not numeric."""
    try:
        x = float(x)
    except (TypeError, ValueError):
        return None
    return None if pd.isna(x) else x


def pick_growth_rate(growth_estimates, income_stmt, info):
    """Return (growth as a fraction, description of the source), or (None, reason).

    Preference order:
      1. 1-year forward analyst estimate for next fiscal year  (growth_estimates '+1y')
      2. 1-year forward analyst estimate for current fiscal year ('0y')
      3. 1-year trailing growth in annual diluted EPS (last two fiscal years)
      4. 1-year trailing quarterly EPS growth, year over year (info 'earningsGrowth')
    """
    labels = {"+1y": "1-yr forward (analyst estimate, next fiscal year)",
              "0y": "1-yr forward (analyst estimate, current fiscal year)"}
    if growth_estimates is not None and not growth_estimates.empty \
            and "stockTrend" in growth_estimates.columns:
        for period, label in labels.items():
            if period in growth_estimates.index:
                g = _num(growth_estimates.loc[period, "stockTrend"])
                if g is not None:
                    return g, label

    if income_stmt is not None and not income_stmt.empty:
        for row in ("Diluted EPS", "Basic EPS"):
            if row in income_stmt.index:
                eps = income_stmt.loc[row].dropna().sort_index(ascending=False)
                if len(eps) >= 2:
                    latest, prior = float(eps.iloc[0]), float(eps.iloc[1])
                    if prior > 0:
                        fy = pd.Timestamp(eps.index[0]).year
                        return ((latest - prior) / prior,
                                f"1-yr trailing (annual {row}, FY{fy} vs FY{fy - 1})")

    g = _num(info.get("earningsGrowth"))
    if g is not None:
        return g, "1-yr trailing (latest quarter EPS vs same quarter last year)"

    return None, "No growth rate available"


def compute_valuation(info, growth_estimates, income_stmt):
    """Compute P/E, dividend yield, growth rate and PEGY. Percentages are in % units."""
    price = _num(info.get("currentPrice")) or _num(info.get("regularMarketPrice")) \
        or _num(info.get("previousClose"))

    pe = _num(info.get("trailingPE"))
    eps = _num(info.get("trailingEps"))
    if pe is None and price and eps and eps > 0:
        pe = price / eps

    # Dividend yield from the annual dividend / price (avoids yfinance's
    # inconsistent units for 'dividendYield' across versions).
    div_rate = _num(info.get("dividendRate"))
    if price and div_rate is not None:
        div_yield = div_rate / price * 100
    else:
        trailing_yield = _num(info.get("trailingAnnualDividendYield"))
        div_yield = trailing_yield * 100 if trailing_yield is not None else 0.0

    growth, growth_source = pick_growth_rate(growth_estimates, income_stmt, info)
    growth_pct = growth * 100 if growth is not None else None

    pegy, pegy_note = None, ""
    if pe is None or pe <= 0:
        pegy_note = "P/E unavailable or negative (no positive trailing earnings)"
    elif growth_pct is None:
        pegy_note = "No growth rate available"
    elif div_yield + growth_pct <= 0:
        pegy_note = "Dividend yield + growth is zero or negative"
    else:
        pegy = pe / (div_yield + growth_pct)

    return dict(pe=pe, div_yield=div_yield, growth_pct=growth_pct,
                growth_source=growth_source, pegy=pegy, pegy_note=pegy_note)


@st.cache_data(ttl=3600)
def load_valuation(symbol: str):
    t = yf.Ticker(symbol)
    try:
        info = t.info or {}
    except Exception:
        info = {}
    try:
        growth_estimates = t.growth_estimates
    except Exception:
        growth_estimates = None
    try:
        income_stmt = t.income_stmt
    except Exception:
        income_stmt = None
    return compute_valuation(info, growth_estimates, income_stmt)


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

        val = load_valuation(ticker)
        v1, v2, v3, v4 = st.columns(4)
        v1.metric("P/E (trailing 12 mo)",
                  f"{val['pe']:.1f}" if val["pe"] else "n/a")
        v2.metric("Dividend yield", f"{val['div_yield']:.2f}%")
        v3.metric("Growth rate",
                  f"{val['growth_pct']:+.1f}%" if val["growth_pct"] is not None else "n/a")
        v4.metric("PEGY", f"{val['pegy']:.2f}" if val["pegy"] else "n/a")
        st.caption(
            f"**Growth rate used:** {val['growth_source']}.  "
            "PEGY = P/E ÷ (dividend yield % + growth rate %). "
            "Peter Lynch's rule of thumb: below 1 suggests the stock may be undervalued."
            + (f"  \nPEGY not calculated: {val['pegy_note']}." if val["pegy_note"] else "")
        )

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
