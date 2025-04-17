"""Daily chart generator for Yuanta 0050 ETF

Generates a single HTML file (0050_charts.html) that contains:
  • Candlestick chart with 5/14/20‑day moving averages & 20‑day Bollinger Bands
    ‑ Up (Close ≥ Open) candles: **red**
    ‑ Down (Close < Open) candles: **green**
  • KD indicator (9‑day stochastic %K & %D) as a subplot under the K‑chart

The script is meant to be executed by GitHub Actions (see update_charts.yml).
All required packages are installed in the workflow step:
    pip install yfinance pandas plotly
"""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf

TICKER = "0050.TW"
LOOKBACK_DAYS = "70d"  # enough to compute 20‑day Bollinger
OUTPUT_FILE = "0050_charts.html"

# ------------------------------------------------------------------
# Fetch historical data (adjusted) -------------------------------------------------
# ------------------------------------------------------------------

data = yf.Ticker(TICKER).history(period=LOOKBACK_DAYS).reset_index()
if data.empty:
    raise RuntimeError(f"No data returned for {TICKER}. Check symbol or internet connectivity.")

# ------------------------------------------------------------------
# Technical indicators ------------------------------------------------------------
# ------------------------------------------------------------------

for n in (5, 14, 20):
    data[f"MA_{n}"] = data["Close"].rolling(n).mean()

# 20‑day Bollinger Bands
mid = data["MA_20"]
std = data["Close"].rolling(20).std(ddof=0)
data["BB_Upper"] = mid + 2 * std
data["BB_Lower"] = mid - 2 * std
data["BB_Mid"] = mid

# KD (Stochastic 9)
low_min = data["Low"].rolling(9).min()
high_max = data["High"].rolling(9).max()
RSV = (data["Close"] - low_min) / (high_max - low_min) * 100
K = RSV.ewm(alpha=1/3, adjust=False).mean()
D = K.ewm(alpha=1/3, adjust=False).mean()

data["K"] = K
data["D"] = D

# ------------------------------------------------------------------
# Plotting ------------------------------------------------------------------------
# ------------------------------------------------------------------

fig = make_subplots(
    rows=2,
    cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    row_heights=[0.7, 0.3],
)

# --- Candlestick row -------------------------------------------------------------
fig.add_trace(
    go.Candlestick(
        x=data["Date"],
        open=data["Open"],
        high=data["High"],
        low=data["Low"],
        close=data["Close"],
        name="OHLC",
        increasing_line_color="#d62728",   # red for up
        increasing_fillcolor="#d62728",
        decreasing_line_color="#2ca02c",   # green for down
        decreasing_fillcolor="#2ca02c",
    ),
    row=1,
    col=1,
)

# Moving averages
for n, color in zip((5, 14, 20), ("#9467bd", "#8c564b", "#1f77b4")):
    fig.add_trace(
        go.Scatter(
            x=data["Date"],
            y=data[f"MA_{n}"],
            mode="lines",
            name=f"MA{n}",
            line=dict(width=1),
        ),
        row=1,
        col=1,
    )

# Bollinger bands (upper / mid / lower)
fig.add_trace(go.Scatter(x=data["Date"], y=data["BB_Upper"], name="Boll Upper", line=dict(width=1, dash="dash")), row=1, col=1)
fig.add_trace(go.Scatter(x=data["Date"], y=data["BB_Mid"],   name="Boll Mid",   line=dict(width=1, dash="dot")),  row=1, col=1)
fig.add_trace(go.Scatter(x=data["Date"], y=data["BB_Lower"], name="Boll Lower", line=dict(width=1, dash="dash")), row=1, col=1)

# --- KD subplot ------------------------------------------------------------------
fig.add_trace(go.Scatter(x=data["Date"], y=data["K"], name="%K"), row=2, col=1)
fig.add_trace(go.Scatter(x=data["Date"], y=data["D"], name="%D"), row=2, col=1)

# Overbought / oversold lines
fig.add_hline(y=80, line_dash="dash", row=2, col=1)
fig.add_hline(y=20, line_dash="dash", row=2, col=1)

# Layout tweaks -------------------------------------------------------------------
fig.update_layout(
    title=f"{TICKER} — Candlestick & KD ({data['Date'].min().date()} – {data['Date'].max().date()})",
    xaxis_rangeslider_visible=False,
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    margin=dict(t=50, b=30, l=65, r=30),
)

# ------------------------------------------------------------------
# Output --------------------------------------------------------------------------
# ------------------------------------------------------------------

fig.write_html(OUTPUT_FILE, include_plotlyjs="cdn")
print(f"✔ Saved {OUTPUT_FILE} with candlestick & KD charts.")
