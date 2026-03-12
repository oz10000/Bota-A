import pandas as pd
import numpy as np
import requests
import time
import json
import os
from datetime import datetime

# =========================================================
# CONFIG
# =========================================================

ASSETS = ["BTC","ETH","SOL"]
TIMEFRAME = "3m"
LOOKBACK = 200

EMA_PERIOD = 20
ATR_PERIOD = 14

EDGE_THRESHOLD = 0.003
ATR_MULTIPLIER = 1.5

TP_OPTIMAL = {
    "BTC":0.50,
    "ETH":0.30,
    "SOL":0.50
}

BASE_URL="https://api.binance.com/api/v3/klines"

INITIAL_CAPITAL = 100

TRADES_FILE="trades_log.csv"
METRICS_FILE="metrics.json"
BOT_LOG="bot_log.txt"
STATE_FILE="state.json"

POSITION=None

# =========================================================
# LOG
# =========================================================

def log(msg):

    text=f"{datetime.utcnow()} | {msg}"
    print(text)

    with open(BOT_LOG,"a") as f:
        f.write(text+"\n")

# =========================================================
# METRICS
# =========================================================

def load_metrics():

    if not os.path.exists(METRICS_FILE):

        data={
            "capital":INITIAL_CAPITAL,
            "trades":0,
            "wins":0,
            "losses":0
        }

        with open(METRICS_FILE,"w") as f:
            json.dump(data,f)

    with open(METRICS_FILE) as f:
        return json.load(f)

def save_metrics(m):

    with open(METRICS_FILE,"w") as f:
        json.dump(m,f,indent=4)

# =========================================================
# STATE (posición abierta)
# =========================================================

def save_state(pos):

    with open(STATE_FILE,"w") as f:
        json.dump(pos,f)

def load_state():

    if not os.path.exists(STATE_FILE):
        return None

    with open(STATE_FILE) as f:
        return json.load(f)

# =========================================================
# DATA
# =========================================================

def fetch(symbol):

    params={
        "symbol":f"{symbol}USDT",
        "interval":TIMEFRAME,
        "limit":LOOKBACK
    }

    r=requests.get(BASE_URL,params=params)

    data=r.json()

    df=pd.DataFrame(data,columns=[
    "open_time","open","high","low","close","volume",
    "close_time","qav","num_trades",
    "taker_base_vol","taker_quote_vol","ignore"
    ])

    df[['open','high','low','close']] = df[['open','high','low','close']].astype(float)

    return df

# =========================================================
# ATR
# =========================================================

def compute_atr(df):

    high=df["high"]
    low=df["low"]
    close=df["close"]

    tr1=high-low
    tr2=abs(high-close.shift())
    tr3=abs(low-close.shift())

    tr=pd.concat([tr1,tr2,tr3],axis=1).max(axis=1)

    return tr.rolling(ATR_PERIOD).mean()

# =========================================================
# SCANNER
# =========================================================

def scan():

    signals=[]

    for asset in ASSETS:

        try:

            df=fetch(asset)

            ema=df["close"].ewm(span=EMA_PERIOD).mean()
            atr=compute_atr(df)

            price=df["close"].iloc[-1]
            ema_val=ema.iloc[-1]
            atr_val=atr.iloc[-1]

            deviation=(price-ema_val)/ema_val
            edge=abs(deviation)

            if edge < EDGE_THRESHOLD:
                continue

            tp_coef=TP_OPTIMAL[asset]

            tp_move=edge*tp_coef
            sl_move=(atr_val/price)*ATR_MULTIPLIER

            if deviation < 0:

                direction="LONG"
                tp=price*(1+tp_move)
                sl=price*(1-sl_move)

            else:

                direction="SHORT"
                tp=price*(1-tp_move)
                sl=price*(1+sl_move)

            signals.append({
                "asset":asset,
                "direction":direction,
                "entry":price,
                "tp":tp,
                "sl":sl,
                "edge":edge,
                "mfe":0,
                "mae":0
            })

        except Exception as e:

            log(f"SCAN ERROR {asset} {e}")

    if len(signals)==0:
        return None

    return max(signals,key=lambda x:x["edge"])

# =========================================================
# POSITION CHECK
# =========================================================

def check_position(pos):

    df=fetch(pos["asset"])

    price=df["close"].iloc[-1]

    entry=pos["entry"]

    if pos["direction"]=="LONG":

        move=(price-entry)/entry

    else:

        move=(entry-price)/entry

    pos["mfe"]=max(pos["mfe"],move)
    pos["mae"]=min(pos["mae"],move)

    if pos["direction"]=="LONG":

        if price>=pos["tp"]:
            return "TP",price,pos

        if price<=pos["sl"]:
            return "SL",price,pos

    else:

        if price<=pos["tp"]:
            return "TP",price,pos

        if price>=pos["sl"]:
            return "SL",price,pos

    return None,price,pos

# =========================================================
# SAVE TRADE
# =========================================================

def save_trade(trade):

    df=pd.DataFrame([trade])

    if not os.path.exists(TRADES_FILE):

        df.to_csv(TRADES_FILE,index=False)

    else:

        df.to_csv(TRADES_FILE,mode="a",header=False,index=False)

# =========================================================
# MAIN
# =========================================================

metrics=load_metrics()

POSITION=load_state()

log("BOT STARTED")

while True:

    try:

        if POSITION is None:

            signal=scan()

            if signal:

                POSITION=signal

                save_state(POSITION)

                log(f"OPEN {signal}")

            else:

                log("NO SIGNAL")

        else:

            result,price,POSITION=check_position(POSITION)

            if result:

                entry=POSITION["entry"]

                if POSITION["direction"]=="LONG":

                    pnl=(price-entry)/entry

                else:

                    pnl=(entry-price)/entry

                metrics["capital"]*=1+pnl
                metrics["trades"]+=1

                if pnl>0:
                    metrics["wins"]+=1
                else:
                    metrics["losses"]+=1

                winrate=metrics["wins"]/metrics["trades"]

                trade_data={

                    "time":datetime.utcnow(),
                    "asset":POSITION["asset"],
                    "direction":POSITION["direction"],
                    "entry":entry,
                    "exit":price,
                    "pnl":pnl,
                    "mfe":POSITION["mfe"],
                    "mae":POSITION["mae"],
                    "capital":metrics["capital"],
                    "winrate":winrate
                }

                save_trade(trade_data)

                save_metrics(metrics)

                log(f"CLOSE {trade_data}")

                POSITION=None

                save_state(None)

            else:

                save_state(POSITION)

                log("TRADE RUNNING")

        time.sleep(60)

    except Exception as e:

        log(f"MAIN ERROR {e}")

        time.sleep(60)
