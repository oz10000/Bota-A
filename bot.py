import pandas as pd
import numpy as np
import requests
import time
import os
from datetime import datetime

# ==========================================================
# CONFIG
# ==========================================================
ASSETS = ["BTC","ETH","SOL"]
TIMEFRAME = "3m"
LOOKBACK = 200
EMA_PERIOD = 20
ATR_PERIOD = 14
EDGE_THRESHOLD = 0.003
ATR_MULT = 1.5
TP_EDGE = 0.30
BASE_URL = "https://api.binance.com/api/v3/klines"
POSITION = None

# Paths para reportes
REPORT_DIR = "reports"
TRADES_FILE = "trades.csv"
METRICS_FILE = "metrics.json"
LOOP_DELAY = 60
REPORT_INTERVAL = 300  # 5 minutos
LAST_REPORT = 0

# ==========================================================
# DATA
# ==========================================================
def fetch(symbol):
    params = {
        "symbol": f"{symbol}USDT",
        "interval": TIMEFRAME,
        "limit": LOOKBACK
    }
    r = requests.get(BASE_URL, params=params)
    data = r.json()
    df = pd.DataFrame(data, columns=[
        "open_time","open","high","low","close","volume",
        "close_time","qav","num_trades",
        "taker_base_vol","taker_quote_vol","ignore"
    ])
    df[['open','high','low','close']] = df[['open','high','low','close']].astype(float)
    return df

# ==========================================================
# ATR
# ==========================================================
def atr(df):
    high = df["high"]
    low = df["low"]
    close = df["close"]
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(ATR_PERIOD).mean()

# ==========================================================
# SCANNER
# ==========================================================
def scan():
    signals = []
    for asset in ASSETS:
        df = fetch(asset)
        ema = df["close"].ewm(span=EMA_PERIOD).mean()
        atr_val = atr(df).iloc[-1]
        price = df["close"].iloc[-1]
        ema_val = ema.iloc[-1]
        deviation = (price - ema_val)/ema_val
        edge = abs(deviation)
        if edge < EDGE_THRESHOLD:
            continue
        tp_move = edge * TP_EDGE
        sl_move = (atr_val/price)*ATR_MULT
        if deviation < 0:
            direction = "LONG"
            tp = price*(1+tp_move)
            sl = price*(1-sl_move)
        else:
            direction = "SHORT"
            tp = price*(1-tp_move)
            sl = price*(1+sl_move)
        signals.append({
            "asset": asset,
            "direction": direction,
            "entry": price,
            "tp": tp,
            "sl": sl,
            "edge": edge,
            "mfe": 0,
            "mae": 0
        })
    if len(signals) == 0:
        return None
    return max(signals, key=lambda x:x["edge"])

# ==========================================================
# CHECK POSITION
# ==========================================================
def check_position(pos):
    df = fetch(pos["asset"])
    price = df["close"].iloc[-1]
    move = (price - pos["entry"]) / pos["entry"] if pos["direction"]=="LONG" else (pos["entry"] - price)/pos["entry"]
    pos["mfe"] = max(pos["mfe"], move)
    pos["mae"] = min(pos["mae"], move)
    if pos["direction"]=="LONG":
        if price >= pos["tp"]: return "TP", price
        if price <= pos["sl"]: return "SL", price
    else:
        if price <= pos["tp"]: return "TP", price
        if price >= pos["sl"]: return "SL", price
    return None, price

# ==========================================================
# REPORTS
# ==========================================================
def save_report():
    os.makedirs(REPORT_DIR, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    report_file = os.path.join(REPORT_DIR, f"report_{timestamp}.txt")
    trades = pd.read_csv(TRADES_FILE) if os.path.exists(TRADES_FILE) else pd.DataFrame()
    metrics = pd.read_json(METRICS_FILE) if os.path.exists(METRICS_FILE) else {}
    with open(report_file, "w") as f:
        f.write("=== TRADES ===\n")
        f.write(trades.to_string(index=False))
        f.write("\n\n=== METRICS ===\n")
        f.write(str(metrics))

# ==========================================================
# MAIN LOOP
# ==========================================================
metrics = {"capital": 100, "trades":0, "wins":0, "losses":0}

while True:
    try:
        if POSITION is None:
            signal = scan()
            if signal:
                POSITION = signal
                print(f"OPEN: {signal}")
            else:
                print("No signal")
        else:
            result, price = check_position(POSITION)
            if result:
                entry = POSITION["entry"]
                pnl = (price-entry)/entry if POSITION["direction"]=="LONG" else (entry-price)/entry
                metrics["capital"] *= 1 + pnl
                metrics["trades"] += 1
                if pnl>0:
                    metrics["wins"] += 1
                else:
                    metrics["losses"] += 1
                trade_record = {
                    "time": datetime.utcnow(),
                    **POSITION,
                    "exit": price,
                    "pnl": pnl,
                    "capital": metrics["capital"],
                    "winrate": metrics["wins"]/metrics["trades"]
                }
                # Guardar trade y métricas
                os.makedirs(os.path.dirname(TRADES_FILE), exist_ok=True)
                pd.DataFrame([trade_record]).to_csv(TRADES_FILE, mode="a", header=not os.path.exists(TRADES_FILE), index=False)
                pd.DataFrame([metrics]).to_json(METRICS_FILE)
                print(f"CLOSE: {trade_record}")
                POSITION = None
            else:
                print("Trade running...")

        # Guardado de reportes cada 5 minutos
        if time.time() - LAST_REPORT >= REPORT_INTERVAL:
            save_report()
            LAST_REPORT = time.time()

        time.sleep(LOOP_DELAY)
    except Exception as e:
        print("ERROR:", e)
        time.sleep(LOOP_DELAY)
