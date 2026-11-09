# stock-dashboard

Sample dashboard project: enter a stock ticker and see a chart of its daily closing prices for the past 12 months, with 50-day and 200-day moving averages. Data comes from Yahoo Finance via `yfinance`.

## Features

- Ticker input (defaults to AAPL)
- Line chart of closing prices with 50- and 200-day moving averages
- Summary metrics: latest close, 1-year change, 1-year range
- Valuation: trailing P/E, dividend yield, earnings growth rate, and Peter Lynch's PEGY ratio
  (P/E ÷ (dividend yield % + growth rate %)). Uses a 1-year forward analyst growth estimate
  when available, otherwise 1-year trailing EPS growth; the dashboard labels which was used.
- Expandable raw-data table
- Results cached for an hour per ticker

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
streamlit run stock_dashboard.py
```

The app opens at http://localhost:8501.
