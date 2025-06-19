import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
from zoneinfo import ZoneInfo

# === 1. 抓資料，保留最近 90 天 ===
df_raw = yf.Ticker("0050.TW").history(period="100d").reset_index()
df = df_raw.tail(90)

# === 2. 清洗資料：去掉無成交量或無收盤價 ===
df = df.dropna(subset=["Close", "Volume"])
df = df[df["Volume"] > 0]

# === 3. 依日期調整前期資料：
#     2025-06-15 之前，成交量×4、價格欄位 ÷4
cutoff = pd.Timestamp("2025-06-15")
mask = df["Date"] < cutoff

# 成交量放大
df.loc[mask, "Volume"] = df.loc[mask, "Volume"] * 4

# 價格縮小
price_cols = ["Open", "High", "Low", "Close"]
df.loc[mask, price_cols] = df.loc[mask, price_cols] / 4

# === 4. 顯示用日期字串 ===
df["DateStr"] = df["Date"].dt.strftime("%Y-%m-%d")

# === 5. 計算技術指標 ===
for n in (5, 14, 20):
    df[f"MA_{n}"] = df["Close"].rolling(n).mean()

df["BB_Mid"]   = df["MA_20"]
df["BB_Std"]   = df["Close"].rolling(20).std(ddof=0)
df["BB_Upper"] = df["BB_Mid"] + 2 * df["BB_Std"]
df["BB_Lower"] = df["BB_Mid"] - 2 * df["BB_Std"]

low_min  = df["Low"].rolling(9).min()
high_max = df["High"].rolling(9).max()
df["RSV"] = (df["Close"] - low_min) / (high_max - low_min) * 100
df["K"]   = df["RSV"].ewm(alpha=1/3, adjust=False).mean()
df["D"]   = df["K"].ewm(alpha=1/3, adjust=False).mean()

# === 6. 時間戳 ===
tst_now = datetime.now(ZoneInfo("Asia/Taipei")).strftime("%Y-%m-%d %H:%M TST")

# === 7. 建立三層子圖 ===
fig = make_subplots(
    rows=3, cols=1, shared_xaxes=True,
    row_heights=[0.6, 0.2, 0.2],
    vertical_spacing=0.03,
    subplot_titles=(
        f"0050 ETF 技術走勢（生成：{tst_now}）",
        "成交量",
        "KD 指標"
    )
)

# 7-1. 第一層：K 線 + MA + 布林通道
fig.add_trace(
    go.Candlestick(
        x=df["DateStr"], open=df["Open"], high=df["High"],
        low=df["Low"], close=df["Close"],
        name="OHLC", increasing_line_color="red", decreasing_line_color="green"
    ),
    row=1, col=1
)
for n in (5, 14, 20):
    fig.add_trace(
        go.Scatter(
            x=df["DateStr"], y=df[f"MA_{n}"],
            mode="lines", name=f"MA {n}"
        ),
        row=1, col=1
    )
fig.add_trace(
    go.Scatter(x=df["DateStr"], y=df["BB_Upper"], name="Boll Upper", line=dict(dash="dot")),
    row=1, col=1
)
fig.add_trace(
    go.Scatter(x=df["DateStr"], y=df["BB_Mid"],   name="Boll Mid",   line=dict(dash="dash")),
    row=1, col=1
)
fig.add_trace(
    go.Scatter(x=df["DateStr"], y=df["BB_Lower"], name="Boll Lower", line=dict(dash="dot")),
    row=1, col=1
)

# 7-2. 第二層：成交量
colors = ["red" if c >= o else "green" for c, o in zip(df["Close"], df["Open"])]
fig.add_trace(
    go.Bar(x=df["DateStr"], y=df["Volume"], name="Volume", marker_color=colors, showlegend=False),
    row=2, col=1
)

# 7-3. 第三層：KD 指標
fig.add_trace(
    go.Scatter(x=df["DateStr"], y=df["K"], name="%K", line=dict(color="magenta")),
    row=3, col=1
)
fig.add_trace(
    go.Scatter(x=df["DateStr"], y=df["D"], name="%D", line=dict(color="blue")),
    row=3, col=1
)
fig.add_hline(y=80, line_dash="dot", row=3, col=1)
fig.add_hline(y=20, line_dash="dot", row=3, col=1)

# === 8. 版面設定 ===
fig.update_layout(
    height=900,
    template="plotly_white",
    hovermode="x unified",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)
for i in [1, 2, 3]:
    fig.update_xaxes(type="category", row=i, col=1)
fig.update_yaxes(title_text="價格", row=1, col=1)
fig.update_yaxes(title_text="交易量", row=2, col=1)
fig.update_yaxes(title_text="KD 值", row=3, col=1)

# === 9. 輸出 HTML ===
fig.write_html("0050_charts.html", include_plotlyjs="cdn")
