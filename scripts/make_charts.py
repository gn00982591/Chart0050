"""
make_charts.py — Auto‑detect Elliott Waves & generate interactive chart for Yuanta 0050 ETF
========================================================================================
• Row 1  K 線（紅漲綠跌）+ 5/14/20 MA + 20 日布林 Bands  + Elliott Wave + 預測路線
• Row 2  成交量柱狀圖（紅漲綠跌）
• Row 3  KD(9)

產生單一 `0050_charts.html`，並在圖表標題顯示 **資料生成時間（台灣）**，方便辨識最新度。
"""

from datetime import datetime
from zoneinfo import ZoneInfo
from plotly.subplots import make_subplots
import plotly.graph_objects as go
import pandas as pd
import yfinance as yf

# ---------------- 參數 ----------------
TICKER = "0050.TW"
PERIOD  = "70d"              # 近 70 天足以計算 20 日布林
WINDOW  = 4                  # pivot window 大小 (Elliott wave 簡易偵測)
THRESH  = 0.02               # 2% 高低差視為 pivot

# -------------- 抓取資料 --------------
print("Downloading historical data…")
df = yf.Ticker(TICKER).history(period=PERIOD).reset_index()

# ------------- 技術指標計算 -------------
for n in (5, 14, 20):
    df[f"MA_{n}"] = df["Close"].rolling(n).mean()

df["BB_Mid"] = df["MA_20"]
df["BB_Std"] = df["Close"].rolling(20).std(ddof=0)
df["BB_Upper"] = df["BB_Mid"] + 2 * df["BB_Std"]
df["BB_Lower"] = df["BB_Mid"] - 2 * df["BB_Std"]

low_min  = df["Low"].rolling(9).min()
high_max = df["High"].rolling(9).max()
df["RSV"] = (df["Close"] - low_min) / (high_max - low_min) * 100
df["K"]   = df["RSV"].ewm(alpha=1/3, adjust=False).mean()
df["D"]   = df["K"].ewm(alpha=1/3, adjust=False).mean()

# --------- 簡易 Elliott Wave 偵測 ---------
# 使用 pivot 擷取轉折點
pivots = []
for i in range(WINDOW, len(df) - WINDOW):
    window = df.iloc[i - WINDOW:i + WINDOW + 1]
    price  = df.loc[i, "Close"]
    if price == window["Close"].max():
        pivots.append((i, price, "peak"))
    elif price == window["Close"].min():
        pivots.append((i, price, "trough"))

# 依序挑出 5+3 浪（啟發式：交替 peak/trough，價差 > THRESH）
waves = []
for idx, price, kind in pivots:
    if not waves:
        waves.append((idx, price))
    else:
        prev_idx, prev_price = waves[-1]
        if kind == ("peak" if price > prev_price else "trough") and abs(price - prev_price) / prev_price > THRESH:
            waves.append((idx, price))
    if len(waves) == 8:  # 0‑5 + A‑C 共 8 個點
        break

labels = ["0","1","2","3","4","5","A","B","C"]
wave_pts = dict(zip(labels[:len(waves)], waves))

# ---- 依 B 浪 → C 浪 預測 (0.382 & 0.618) ----
forecast_x = []
forecast_y = []
if "B" in wave_pts and "A" in wave_pts:
    b_idx, b_price = wave_pts["B"]
    a_idx, a_price = wave_pts["A"]
    direction = 1 if b_price > a_price else -1
    c_target = b_price + direction * abs(b_price - a_price) * 0.618
    last_date = df.loc[b_idx, "Date"]
    forecast_date = last_date + pd.Timedelta(days=25)
    forecast_x = [df.loc[b_idx, "Date"], forecast_date]
    forecast_y = [b_price, c_target]

# ------------- 畫圖 -------------
fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                    vertical_spacing=0.02, row_heights=[0.55, 0.25, 0.20])

# Row1: Candlestick
inc = df["Close"] >= df["Open"]
dec = ~inc
fig.add_trace(go.Candlestick(x=df["Date"], open=df["Open"], high=df["High"],
                             low=df["Low"], close=df["Close"],
                             increasing_line_color="red", decreasing_line_color="green", name="OHLC"),
              row=1, col=1)

for n,col in ((5,"orange"),(14,"blue"),(20,"purple")):
    fig.add_trace(go.Scatter(x=df["Date"], y=df[f"MA_{n}"], name=f"MA{n}", line=dict(color=col)), row=1, col=1)

fig.add_trace(go.Scatter(x=df["Date"], y=df["BB_Upper"], name="Boll Upper", line=dict(color="gray", dash="dash")), row=1, col=1)
fig.add_trace(go.Scatter(x=df["Date"], y=df["BB_Mid"],   name="Boll Mid",   line=dict(color="gray", dash="dot")),  row=1, col=1)
fig.add_trace(go.Scatter(x=df["Date"], y=df["BB_Lower"], name="Boll Lower", line=dict(color="gray", dash="dash")), row=1, col=1)

# Wave annotations
for lbl,(i,price) in wave_pts.items():
    fig.add_annotation(x=df.loc[i,"Date"], y=price, text=lbl, showarrow=True, arrowhead=1, row=1, col=1)

# Forecast line
if forecast_x:
    fig.add_trace(go.Scatter(x=forecast_x, y=forecast_y, mode="lines", name="Forecast", line=dict(color="dodgerblue", dash="dash")), row=1, col=1)

# Row2: Volume
fig.add_trace(go.Bar(x=df["Date"], y=df["Volume"], marker_color=["red" if inc[i] else "green" for i in range(len(df))], name="Volume"), row=2, col=1)

# Row3: KD
fig.add_trace(go.Scatter(x=df["Date"], y=df["K"], name="%K", line=dict(color="gold")), row=3, col=1)
fig.add_trace(go.Scatter(x=df["Date"], y=df["D"], name="%D", line=dict(color="darkorange")), row=3, col=1)
fig.add_hline(y=80, line_dash="dash", row=3, col=1)
fig.add_hline(y=20, line_dash="dash", row=3, col=1)

# 生成時間 (台灣)
now_tw = datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d %H:%M %Z")
fig.update_layout(title=f"0050 ETF 技術圖表  (生成時間：{now_tw})",
                  xaxis_rangeslider_visible=False, legend_orientation="h", legend_y=1.03)

print("Writing HTML…")
fig.write_html("0050_charts.html", include_plotlyjs="cdn")
print("✔  Done. 0050_charts.html generated.")
