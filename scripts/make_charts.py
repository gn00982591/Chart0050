import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
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

# === 5. 子圖（K線 + 成交量 + KD） ===
from plotly.subplots import make_subplots
fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                    row_heights=[0.55, 0.25, 0.20],
                    vertical_spacing=0.02,
                    subplot_titles=(f"0050 ETF 技術走勢圖（生成：{twn_now}）", "", "KD 指標"))


# === 5-3 KD 指標層 ===
fig.add_trace(go.Scatter(x=df["DateStr"], y=df["K"], name="%K", line=dict(color="magenta")), row=3, col=1)
fig.add_trace(go.Scatter(x=df["DateStr"], y=df["D"], name="%D", line=dict(color="blue")), row=3, col=1)
fig.add_hline(y=80, line_dash="dot", row=3, col=1)
fig.add_hline(y=20, line_dash="dot", row=3, col=1)

# === 6. 格式設定 ===
fig.update_layout(
    height=900,
    xaxis=dict(type="category"),  # 最關鍵：不保留缺日空格
    xaxis2=dict(type="category"),
    xaxis3=dict(type="category"),
    hovermode="x unified",
    template="plotly_white",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

# === 7. 輸出 ===
fig.write_html("0050_charts.html", include_plotlyjs="cdn")
