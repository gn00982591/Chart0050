"""
make_charts.py – Generate combined interactive HTML chart for Yuanta 0050 ETF
--------------------------------------------------------------------------
• Row 1  Candlestick  (上漲＝紅、下跌＝綠)  + 5/14/20 MA + 20‑day Bollinger Bands
• Row 2  成交量柱狀圖（同色系：漲＝紅、跌＝綠）
• Row 3  KD(9) 指標線圖

產生單一檔案 0050_charts.html，供 GitHub Pages 部署。
"""

import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# ------------- 下載最近 70 天資料 -------------
df = yf.Ticker("0050.TW").history(period="70d").reset_index()

# --------- 均線 & 布林計算 ---------
for n in (5, 14, 20):
    df[f"MA_{n}"] = df["Close"].rolling(n).mean()

df["BB_Mid"]   = df["MA_20"]
df["BB_Std"]   = df["Close"].rolling(20).std(ddof=0)
df["BB_Upper"] = df["BB_Mid"] + 2 * df["BB_Std"]
df["BB_Lower"] = df["BB_Mid"] - 2 * df["BB_Std"]

# --------- KD(9) ---------
low_min   = df["Low"].rolling(9).min()
high_max  = df["High"].rolling(9).max()
df["RSV"] = (df["Close"] - low_min) / (high_max - low_min) * 100
df["K"]    = df["RSV"].ewm(alpha=1/3, adjust=False).mean()
df["D"]    = df["K"].ewm(alpha=1/3, adjust=False).mean()

# --------- 顏色設定 ---------
inc_color = "red"   # 上漲 (Close >= Open)
dec_color = "green" # 下跌

# --------- 建立子圖: 3 行 1 列 ---------
fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                    row_heights=[0.55, 0.20, 0.25],
                    vertical_spacing=0.02,
                    subplot_titles=("Candlestick + MAs + Bollinger",
                                     "Volume",
                                     "KD 指標"))

# ----- Row 1: Candlestick -----
fig.add_trace(
    go.Candlestick(
        x=df["Date"], open=df["Open"], high=df["High"],
        low=df["Low"],  close=df["Close"],
        increasing=dict(line=dict(color=inc_color), fillcolor=inc_color),
        decreasing=dict(line=dict(color=dec_color), fillcolor=dec_color),
        name="OHLC"),
    row=1, col=1)

# Moving averages
for n in (5, 14, 20):
    fig.add_trace(go.Scatter(x=df["Date"], y=df[f"MA_{n}"], name=f"MA{n}"), row=1, col=1)

# Bollinger Bands
fig.add_trace(go.Scatter(x=df["Date"], y=df["BB_Upper"], name="Boll Upper", line=dict(dash="dash")), row=1, col=1)
fig.add_trace(go.Scatter(x=df["Date"], y=df["BB_Mid"],   name="Boll Mid",   line=dict(dash="dot")),  row=1, col=1)
fig.add_trace(go.Scatter(x=df["Date"], y=df["BB_Lower"], name="Boll Lower", line=dict(dash="dash")), row=1, col=1)

# ----- Row 2: Volume bars -----
colors = [inc_color if c >= o else dec_color for c, o in zip(df["Close"], df["Open"])]
fig.add_trace(
    go.Bar(x=df["Date"], y=df["Volume"], marker_color=colors, name="Volume"),
    row=2, col=1)

# ----- Row 3: KD -----
fig.add_trace(go.Scatter(x=df["Date"], y=df["K"], name="%K"), row=3, col=1)
fig.add_trace(go.Scatter(x=df["Date"], y=df["D"], name="%D"), row=3, col=1)
fig.add_hline(y=80, line_dash="dash", row=3, col=1)
fig.add_hline(y=20, line_dash="dash", row=3, col=1)

# --------- 版面設定 ---------
fig.update_layout(
    title="0050 ETF – Candlestick, Volume & KD",
    xaxis3_title="Date",   # KD 區 x 軸編號由 plotly 自動給 xaxis3
    yaxis_title="Price (TWD)",
    yaxis2_title="Volume", # 第二行 y 軸
    yaxis3_title="Value",  # 第三行 y 軸
    xaxis_rangeslider_visible=False,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

# --------- 輸出 ---------
fig.write_html("0050_charts.html", include_plotlyjs="cdn")
print("Saved 0050_charts.html")
