"""
make_charts.py — Generate 0050 ETF interactive chart (last 90 days, clean rows w/ missing Close or Volume)
====================================================================================
• Row 1  Candlestick + 5/14/20 MA + 20‑day Bollinger + Elliott 5‑wave + A‑B‑C + 預測路線
• Row 2  成交量柱狀圖
• Row 3  KD(9)

規則：
1. **僅取最近 90 天**（含今日；抓 100 天原始資料再截 90）
2. **排除** `Close` 或 `Volume` 缺值，及 `Volume == 0` 的列 → 三層子圖同步
3. 輸出單檔 `0050_charts.html`，標題附台灣生成時間。
"""

from datetime import datetime
from zoneinfo import ZoneInfo
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import pandas as pd
import yfinance as yf

# ---------------- 參數設定 ------------------
WINDOW      = 4        # pivot window for wave detection
THRESHOLD   = 0.02     # 2% threshold for pivots
TICKER      = "0050.TW"
HTML_FILE   = "0050_charts.html"

# ----------- 取得最近 100 天資料 -------------
now_tw   = datetime.now(ZoneInfo("Asia/Taipei"))
df_raw   = yf.Ticker(TICKER).history(period="100d").reset_index()

# *** 排除沒有收盤價或成交量的列 ***
df = df_raw.dropna(subset=["Close", "Volume"]).copy()
# 亦排除成交量為 0 的例外情況
df = df[df["Volume"] > 0]

# ----------- 技術指標計算 -------------------
for n in (5, 14, 20):
    df[f"MA_{n}"] = df["Close"].rolling(n).mean()

df["BB_Mid"]   = df["MA_20"]
df["BB_Std"]   = df["Close"].rolling(20).std(ddof=0)
df["BB_Upper"] = df["BB_Mid"] + 2 * df["BB_Std"]
df["BB_Lower"] = df["BB_Mid"] - 2 * df["BB_Std"]

# KD 9
low_min   = df["Low"].rolling(9).min()
high_max  = df["High"].rolling(9).max()
df["RSV"] = (df["Close"] - low_min) / (high_max - low_min) * 100
df["K"]   = df["RSV"].ewm(alpha=1/3, adjust=False).mean()
df["D"]   = df["K"].ewm(alpha=1/3, adjust=False).mean()

# ----------- 波浪偵測（簡化） ---------------
pivots = []
for i in range(WINDOW, len(df)-WINDOW):
    hi_cond = df.loc[i, "High"] == df.loc[i-WINDOW:i+WINDOW, "High"].max()
    lo_cond = df.loc[i, "Low"]  == df.loc[i-WINDOW:i+WINDOW, "Low"].min()
    if hi_cond or lo_cond:
        pivots.append(i)

# 精簡選出 5+3 浪（以相鄰 pivot 價差 > THRESHOLD 判定）
waves = []
for idx in pivots:
    if not waves:
        waves.append(idx)
    elif abs(df.loc[idx, "Close"] - df.loc[waves[-1], "Close"]) / df.loc[waves[-1], "Close"] > THRESHOLD:
        waves.append(idx)
    if len(waves) >= 8:
        break
labels = ["①","②","③","④","⑤","A","B","C"][:len(waves)]

# ----------- 預測路線 (C 浪延伸) ------------
forecast_x = []
forecast_y = []
if len(waves) >= 7:  # 至少到 B 浪
    b_idx   = waves[6]
    a_idx   = waves[5]
    c_target = df.loc[b_idx, "Close"] + (df.loc[a_idx, "Close"] - df.loc[waves[4], "Close"]) * 0.618
    forecast_x = [df.loc[b_idx, "Date"], df.loc[b_idx, "Date"].replace(day=df.loc[b_idx, "Date"].day+15)]
    forecast_y = [df.loc[b_idx, "Close"], c_target]

# ------------ 建立子圖 ----------------------
fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                    vertical_spacing=0.02,
                    row_heights=[0.5, 0.25, 0.25])

# Row1: K 線
for i,row in df.iterrows():
    color = "red" if row.Close >= row.Open else "green"
    fig.add_trace(go.Candlestick(x=[row.Date], open=[row.Open], high=[row.High],
                                 low=[row.Low], close=[row.Close],
                                 increasing_line_color="red", decreasing_line_color="green",
                                 showlegend=False), row=1, col=1)
# MA & Bollinger
for n,colr in zip((5,14,20),("#FF5733","#FFC300","#3498DB")):
    fig.add_trace(go.Scatter(x=df.Date, y=df[f"MA_{n}"], name=f"MA{n}", line=dict(color=colr)), row=1, col=1)
fig.add_trace(go.Scatter(x=df.Date, y=df.BB_Upper, name="Boll Upper", line=dict(dash="dash")), row=1, col=1)
fig.add_trace(go.Scatter(x=df.Date, y=df.BB_Mid, name="Boll Mid", line=dict(dash="dot")), row=1, col=1)
fig.add_trace(go.Scatter(x=df.Date, y=df.BB_Lower, name="Boll Lower", line=dict(dash="dash")), row=1, col=1)

# 波浪標籤
for idx,label in zip(waves, labels):
    fig.add_annotation(x=df.loc[idx,"Date"], y=df.loc[idx,"High"]*1.02,
                        text=label, showarrow=False, row=1, col=1)
# 預測線
if forecast_x:
    fig.add_trace(go.Scatter(x=forecast_x, y=forecast_y, mode="lines", line=dict(color="blue", dash="dot"),
                             name="Forecast"), row=1, col=1)

# Row2: Volume
fig.add_trace(go.Bar(x=df.Date, y=df.Volume,
                     marker_color=["red" if c>=o else "green" for c,o in zip(df.Close, df.Open)],
                     name="Volume"), row=2, col=1)

# Row3: KD
fig.add_trace(go.Scatter(x=df.Date, y=df.K, name="%K", line=dict(color="#FF00FF")), row=3, col=1)
fig.add_trace(go.Scatter(x=df.Date, y=df.D, name="%D", line=dict(color="#0000FF")), row=3, col=1)
fig.add_hline(y=80, line_dash="dash", row=3, col=1)
fig.add_hline(y=20, line_dash="dash", row=3, col=1)

# Layout
fig.update_layout(title=f"0050 ETF ‧ 技術圖表（生成：{now_tw.strftime('%Y-%m-%d %H:%M')} TST）",
                  xaxis_rangeslider_visible=False, legend=dict(orientation="h", yanchor="bottom", y=1.02))

fig.write_html(HTML_FILE, include_plotlyjs="cdn")
print(f"Generated {HTML_FILE} with {len(df)} records (filtered from {len(df_raw)})")
