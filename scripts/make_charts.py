import pandas as pd, plotly.graph_objects as go, yfinance as yf
from datetime import datetime

# 取得最近 70 天資料
df = yf.Ticker("0050.TW").history(period="70d").reset_index()

# 計算 MA5/14/20
for n in (5, 14, 20):
    df[f"MA_{n}"] = df["Close"].rolling(n).mean()

# 20 日布林
df["BB_Mid"]   = df["MA_20"]
df["BB_Std"]   = df["Close"].rolling(20).std(ddof=0)
df["BB_Upper"] = df["BB_Mid"] + 2 * df["BB_Std"]
df["BB_Lower"] = df["BB_Mid"] - 2 * df["BB_Std"]

# KD9
low_min  = df["Low"].rolling(9).min()
high_max = df["High"].rolling(9).max()
df["RSV"] = (df["Close"] - low_min) / (high_max - low_min) * 100
df["K"]   = df["RSV"].ewm(alpha=1/3, adjust=False).mean()
df["D"]   = df["K"].ewm(alpha=1/3, adjust=False).mean()

# Candlestick + Bollinger
fig = go.Figure()
fig.add_trace(go.Candlestick(
    x=df["Date"], open=df["Open"], high=df["High"],
    low=df["Low"], close=df["Close"], name="OHLC"))
for n in (5, 14, 20):
    fig.add_trace(go.Scatter(x=df["Date"], y=df[f"MA_{n}"], name=f"MA{n}"))
fig.add_trace(go.Scatter(x=df["Date"], y=df["BB_Upper"], line=dict(dash="dash"), name="Boll Upper"))
fig.add_trace(go.Scatter(x=df["Date"], y=df["BB_Mid"],   line=dict(dash="dot"),  name="Boll Mid"))
fig.add_trace(go.Scatter(x=df["Date"], y=df["BB_Lower"], line=dict(dash="dash"), name="Boll Lower"))
fig.update_layout(title="0050 ETF — K 線 + 布林", xaxis_rangeslider_visible=False)
fig.write_html("0050_candlestick.html", include_plotlyjs="cdn")

# KD
fig_kd = go.Figure()
fig_kd.add_trace(go.Scatter(x=df["Date"], y=df["K"], name="%K"))
fig_kd.add_trace(go.Scatter(x=df["Date"], y=df["D"], name="%D"))
fig_kd.add_hline(y=80, line_dash="dash")
fig_kd.add_hline(y=20, line_dash="dash")
fig_kd.update_layout(title="KD 指標")
fig_kd.write_html("0050_kd.html", include_plotlyjs="cdn")
