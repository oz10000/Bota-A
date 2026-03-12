import pandas as pd
import requests
import time
import json
import os
from datetime import datetime
from strategy import generate_signal
from config import *

POSITION = None

# ---------------- LOG ----------------
def log(msg):
    text = f"{datetime.utcnow()} | {msg}"
    print(text)
    os.makedirs(os.path.dirname(BOT_LOG), exist_ok=True)
    with open(BOT_LOG, "a") as f:
        f.write(text + "\n")

# ---------------- METRICS ----------------
def load_metrics():
    os.makedirs(os.path.dirname(METRICS_FILE), exist_ok=True)
    if not os.path.exists(METRICS_FILE):
        data = {"capital": INITIAL_CAPITAL, "trades":0, "wins":0, "losses":0}
        with open(METRICS_FILE, "w") as f:
            json.dump(data, f)
    with open(METRICS_FILE) as f:
        return json.load(f)

def save_metrics(metrics):
    with open(METRICS_FILE, "w") as f:
        json.dump(metrics, f, indent=4)

# ---------------- STATE ----------------
def save_state(pos):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(pos, f)

def load_state():
    if not os.path.exists(STATE_FILE):
        return None
    with open(STATE_FILE) as f:
        return json.load(f)

# ---------------- DATA ----------------
def fetch(symbol):
    interval_map = {"1m":"1min","3min":"3min","5min":"5min","15min":"15min","1h":"1hour","1day":"1day"}
    params = {
        "symbol": f"{symbol}-USDT",
        "type": interval_map.get(TIMEFRAME,"3min"),
        "limit": LOOKBACK
    }
    r = requests.get(BASE_URL, params=params)
    data = r.json()
    if "data" not in data:
        raise Exception(f"FETCH ERROR {symbol} {data}")
    df = pd.DataFrame(data["data"], columns=["time","open","close","high","low","volume","turnover"])
    df[['open','high','low','close','volume']] = df[['open','high','low','close','volume']].astype(float)
    df = df.sort_values("time").reset_index(drop=True)
    return df

# ---------------- SCAN ----------------
def scan():
    signals = []
    for asset in ASSETS:
        try:
            df = fetch(asset)
            signal = generate_signal(df, asset)
            if signal:
                signals.append(signal)
        except Exception as e:
            log(f"SCAN ERROR {asset} {e}")
    if not signals:
        return None
    return max(signals, key=lambda x:x["edge"])

# ---------------- CHECK POSITION ----------------
def check_position(pos):
    df = fetch(pos["asset"])
    price = df["close"].iloc[-1]
    move = (price - pos["entry"]) / pos["entry"] if pos["direction"]=="LONG" else (pos["entry"] - price)/pos["entry"]
    pos["mfe"] = max(pos["mfe"], move)
    pos["mae"] = min(pos["mae"], move)

    if pos["direction"]=="LONG":
        if price >= pos["tp"]:
            return "TP", price, pos
        if price <= pos["sl"]:
            return "SL", price, pos
    else:
        if price <= pos["tp"]:
            return "TP", price, pos
        if price >= pos["sl"]:
            return "SL", price, pos
    return None, price, pos

# ---------------- SAVE TRADE ----------------
def save_trade(trade):
    os.makedirs(os.path.dirname(TRADES_FILE), exist_ok=True)
    df = pd.DataFrame([trade])
    if not os.path.exists(TRADES_FILE):
        df.to_csv(TRADES_FILE, index=False)
    else:
        df.to_csv(TRADES_FILE, mode="a", header=False, index=False)

# ---------------- MAIN ----------------
metrics = load_metrics()
POSITION = load_state()
log("KUCOIN BOT STARTED")

while True:
    try:
        if POSITION is None:
            signal = scan()
            if signal:
                POSITION = signal
                save_state(POSITION)
                log(f"OPEN {signal}")
            else:
                log("NO SIGNAL")
        else:
            result, price, POSITION = check_position(POSITION)
            if result:
                entry = POSITION["entry"]
                pnl = (price-entry)/entry if POSITION["direction"]=="LONG" else (entry-price)/entry
                metrics["capital"] *= 1 + pnl
                metrics["trades"] += 1
                if pnl > 0:
                    metrics["wins"] += 1
                else:
                    metrics["losses"] += 1
                winrate = metrics["wins"]/metrics["trades"]
                trade_data = {
                    "time": datetime.utcnow(),
                    "asset": POSITION["asset"],
                    "direction": POSITION["direction"],
                    "entry": entry,
                    "exit": price,
                    "pnl": pnl,
                    "mfe": POSITION["mfe"],
                    "mae": POSITION["mae"],
                    "capital": metrics["capital"],
                    "winrate": winrate
                }
                save_trade(trade_data)
                save_metrics(metrics)
                log(f"CLOSE {trade_data}")
                POSITION = None
                save_state(None)
            else:
                save_state(POSITION)
                log("TRADE RUNNING")
        time.sleep(LOOP_DELAY)
    except Exception as e:
        log(f"MAIN ERROR {e}")
        time.sleep(LOOP_DELAY)
