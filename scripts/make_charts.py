"""
make_charts.py — Auto‑detect Elliott Waves & generate interactive chart for Yuanta 0050 ETF
========================================================================================
• Row 1  K 線（紅漲綠跌）+ 5/14/20 MA + 20 日布林 Bands
          ＋**自動偵測 5 浪 + A‑B‑C**（簡易 pivot 演算法）
          ＋**預測路線**：以 0.382、0.618 費波納契延伸推估 C 浪目標
• Row 2  成交量柱狀圖（紅漲綠跌）
• Row 3  KD(9) 指標

輸出單一 `0050_charts.html`，可由 GitHub Pages 直接展示。

⚠️ **說明**：本腳本使用極簡啟發式來偵測波浪，僅供視覺參考，不保證完全符合嚴格波浪理論定義。
"""

from datetime import timedelta
from functools import lru_cache

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import yfinance as yf

# ────────────────────────────────────────────────────────────────
# 讀取近 120 天資料（足夠產生 5 浪 + ABC + 技術指標）
# ────────────────────────────────────────────────────────────────

df = yf.Ticker("0050.TW").history(period="120d").reset_index()

# 計算移動均線 & 布林
for n in (5, 14, 20):
    df[f"MA_{n}"] = df["Close"].rolling(n).mean()

WINDOW_BB = 20
bb_mid = df["Close"].rolling(WINDOW_BB).mean()
bb_std = df["Close"].rolling(WINDOW_BB).std(ddof=0)
df["BB_Mid"] = bb_mid
df["BB_Upper"] = bb_mid + 2 * bb_std
df["BB_Lower"] = bb_mid - 2 * bb_std

# KD(9)
low_min = df["Low"].rolling(9).min()
high_max = df["High"].rolling(9).max()
df["RSV"] = (df["Close"] - low_min) / (high_max - low_min) * 100
df["K"] = df["RSV"].ewm(alpha=1/3, adjust=False).mean()
df["D"] = df["K"].ewm(alpha=1/3, adjust=False).mean()

# ────────────────────────────────────────────────────────────────
# 簡易 Elliott Wave 偵測（pivot 高低）
# ────────────────────────────────────────────────────────────────

def pivot_points(series: pd.Series, window: int = 3):
    """Return indices of local maxima & minima using symmetric window."""
    pivots_high, pivots_low = [], []
    for i in range(window, len(series) - window):
        segment = series[i - window : i + window + 1]
        if series[i] == segment.max():
            pivots_high.append(i)
        if series[i] == segment.min():
            pivots_low.append(i)
    return pivots_high, pivots_low

hi_idx, lo_idx = pivot_points(df["Close"], window=3)

# 合併後依時間排序，交替高低（過濾太近點）
all_idx = sorted(set(hi_idx + lo_idx))

# Filter: 保留波幅 > 1% & 距前點 ≥ 3 日
filtered = []
for idx in all_idx:
    if not filtered:
        filtered.append(idx)
        continue
    if (idx - filtered[-1]) < 3:
        continue
    delta = abs(df.loc[idx, "Close"] - df.loc[filtered[-1], "Close"]) / df.loc[filtered[-1], "Close"]
    if delta < 0.01:
        continue
    filtered.append(idx)

# 取最後 7 個 pivot 作為 1‑5 & A‑B‑C（若不足自動放棄標註）
labels = {}
wave_marks = ["①", "②", "③", "④", "⑤", "A", "B", "C"]
if len(filtered) >= 8:
    piv = filtered[-8:]
    for w, idx in zip(wave_marks, piv):
        labels[idx] = w

# 預測：若已完成 B 浪 (倒數第 2 個 pivot)，假設 C 浪至 0.382‑0.618 回檔
pred_path_x, pred_path_y = [], []
if "B" in labels.values():
    b_idx = [k for k, v in labels.items() if v == "B"][0]
    a_idx = [k for k, v in labels.items() if v == "A"][0]
    price_a, price_b = df.loc[a_idx, "Close"], df.loc[b_idx, "Close"]
    # 目標區間
    c_target = price_b + (price_b - price_a) * 0.618
    last_date = df.loc[b_idx, "Date"]
    pred_end = last_date + timedelta(days=20)
    pred_path_x = [last_date, pred_end]
    pred_path_y = [price_b, c_target]

# ────────────────────────────────────────────────────────────────
# Plotly 子圖：Row1 K 線、Row2 成交量、Row3 KD
# ────────────────────────────────────────────────────────────────

fig = make_subplots(rows=3, cols=1, shared_xaxes=True, row_heights=[0.55, 0.25, 0.20], vertical_spacing=0.02, specs=[[{"type": "candlestick"}], [{"type": "bar"}], [{"type": "scatter"}]])

# --- Row1 Candlestick ---
fig.add_trace(go.Candlestick(
    x=df["Date"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
    name="OHLC",
    increasing=dict(line=dict(color="red"), fillcolor="red"),
    decreasing=dict(line=dict(color="green"), fillcolor="green")
), row=1, col=1)

# MAs
for n, color in zip((5, 14, 20), ("#ffa500", "#0000ff", "#8b008b")):
    fig.add_trace(go.Scatter(x=df["Date"], y=df[f"MA_{n}"], name=f"MA{n}", line=dict(width=1, color=color)), row=1, col=1)

# Bollinger
fig.add_trace(go.Scatter(x=df["Date"], y=df["BB_Upper"], name="Boll Upper", line=dict(width=1, dash="dash", color="#888")), row=1, col=1)
fig.add_trace(go.Scatter(x=df["Date"], y=df["BB_Mid"],   name="Boll Mid",   line=dict(width=1, dash="dot",  color="#aaa")), row=1, col=1)
fig.add_trace(go.Scatter(x=df["Date"], y=df["BB_Lower"], name="Boll Lower", line=dict(width=1, dash="dash", color="#888")), row=1, col=1)

# 波浪文字標註
for idx, label in labels.items():
    fig.add_annotation(x=df.loc[idx, "Date"], y=df.loc[idx, "High"] * 1.01, text=label, showarrow=False, font=dict(color="black", size=12), row=1, col=1)

# 預測路線
if pred_path_x:
    fig.add_trace(go.Scatter(x=pred_path_x, y=pred_path_y, mode="lines", line=dict(color="blue", dash="dot"), name="C-wave projection"), row=1, col=1)

# --- Row2 Volume ---
colors = np.where(df["Close"] >= df["Open"], "red", "green")
fig.add_trace(go.Bar(x=df["Date"], y=df["Volume"], marker_color=colors, name="Volume"), row=2, col=1)

# --- Row3 KD ---
fig.add_trace(go.Scatter(x=df["Date"], y=df["K"], name="%K", line=dict(color="#ffa500")), row=3, col=1)
fig.add_trace(go.Scatter(x=df["Date"], y=df["D"], name="%D", line=dict(color="#0000ff")), row=3, col=1)
fig.add_hline(y=80, line_dash="dash", line_color="#888", row=3, col=1)
fig.add_hline(y=20, line_dash="dash", line_color="#888", row=3, col=1)

# Layout
fig.update_layout(
    title="0050 ETF — K線/Volume/KD with Auto‑detected Elliott Waves",
    xaxis_rangeslider_visible=False,
    height=900,
    legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
)

fig.write_html("0050_charts.html", include_plotlyjs="cdn")
print("0050_charts.html generated")
