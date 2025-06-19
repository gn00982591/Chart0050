import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from zoneinfo import ZoneInfo

# === 1. 抓資料，保留最近 90 天 ===
df_raw = yf.Ticker("0050.TW").history(period="100d").reset_index()
df = df_raw.tail(90)

# === 2. 清洗資料：無成交量、無收盤價不處理 ===
df = df.dropna(subset=["Close", "Volume"])
df = df[df["Volume"] > 0]
df["DateStr"] = df["Date"].dt.strftime("%Y-%m-%d")  # 顯示用

# === 3. 技術指標 ===
for n in (5, 14, 20):
    df[f"MA_{n}"] = df["Close"].rolling(n).mean()
df["BB_Mid"]   = df["MA_20"]
df["BB_Std"]   = df["Close"].rolling(20).std(ddof=0)
df["BB_Upper"] = df["BB_Mid"] + 2 * df["BB_Std"]
df["BB_Lower"] = df["BB_Mid"] - 2 * df["BB_Std"]
low_min  = df["Low"].rolling(9).min()
high_max = df["High"].rolling(9).max()
df["RSV"] = (df["Close"] - low_min) / (high_max - low_min) * 100
df["K"] = df["RSV"].ewm(alpha=1/3, adjust=False).mean()
df["D"] = df["K"].ewm(alpha=1/3, adjust=False).mean()

# === 4. 圖表時間戳 ===
twn_now = datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d %H:%M TST")

# === 5. 建立兩層子圖：第一層啟用 secondary_y（放成交量） ===
fig = make_subplots(
    rows=2, cols=1, shared_xaxes=True,
    row_heights=[0.7, 0.3], vertical_spacing=0.03,
    specs=[[{"secondary_y": True}], [{}]],
    subplot_titles=(f"0050 ETF 技術走勢圖（生成：{twn_now}）", "KD 指標")
)

# --- 5-1 第一層：K 線 + 均線 + 布林
fig.add_trace(
    go.Candlestick(
        x=df["DateStr"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        name="OHLC", increasing_line_color="red", decreasing_line_color="green"
    ),
    row=1, col=1, secondary_y=False
)
for n in (5, 14, 20):
    fig.add_trace(
        go.Scatter(x=df["DateStr"], y=df[f"MA_{n}"], mode="lines", name=f"MA {n}"),
        row=1, col=1, secondary_y=False
    )
fig.add_trace(
    go.Scatter(x=df["DateStr"], y=df["BB_Upper"], name="Boll Upper", line=dict(dash="dot")),
    row=1, col=1, secondary_y=False
)
fig.add_trace(
    go.Scatter(x=df["DateStr"], y=df["BB_Mid"], name="Boll Mid", line=dict(dash="dash")),
    row=1, col=1, secondary_y=False
)
fig.add_trace(
    go.Scatter(x=df["DateStr"], y=df["BB_Lower"], name="Boll Lower", line=dict(dash="dot")),
    row=1, col=1, secondary_y=False
)

# --- 5-2 第一層 secondary_y：成交量
colors = ["red" if c >= o else "green" for c, o in zip(df["Close"], df["Open"])]
fig.add_trace(
    go.Bar(x=df["DateStr"], y=df["Volume"], name="Volume", marker_color=colors, showlegend=False),
    row=1, col=1, secondary_y=True
)

# --- 5-3 第二層：KD 指標
fig.add_trace(
    go.Scatter(x=df["DateStr"], y=df["K"], name="%K", line=dict(color="magenta")),
    row=2, col=1
)
fig.add_trace(
    go.Scatter(x=df["DateStr"], y=df["D"], name="%D", line=dict(color="blue")),
    row=2, col=1
)
# KD 超買/超賣線
fig.add_hline(y=80, line_dash="dot", row=2, col=1)
fig.add_hline(y=20, line_dash="dot", row=2, col=1)

# === 6. 圖表樣式設定 ===
fig.update_layout(
    height=900,
    xaxis=dict(type="category"),
    xaxis2=dict(type="category"),
    hovermode="x unified",
    template="plotly_white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
# 如果需要可分別調整 primary/secondary y 軸標籤
fig.update_yaxes(title_text="價格", row=1, col=1, secondary_y=False)
fig.update_yaxes(title_text="成交量", row=1, col=1, secondary_y=True)
fig.update_yaxes(title_text="KD 值", row=2, col=1)

# === 7. 輸出 HTML ===
fig.write_html("0050_charts.html", include_plotlyjs="cdn")
