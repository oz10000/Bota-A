import pandas as pd
from config import *

def compute_atr(df):
    high = df["high"]
    low = df["low"]
    close = df["close"]
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(ATR_PERIOD).mean()

def generate_signal(df, asset):
    """Genera señal de trade o None"""
    ema = df["close"].ewm(span=EMA_PERIOD).mean()
    atr_val = compute_atr(df).iloc[-1]
    price = df["close"].iloc[-1]
    ema_val = ema.iloc[-1]

    deviation = (price - ema_val) / ema_val
    edge = abs(deviation)
    if edge < EDGE_THRESHOLD:
        return None

    tp_move = edge * TP_EDGE
    sl_move = (atr_val / price) * ATR_MULTIPLIER

    if deviation < 0:
        direction = "LONG"
        tp = price * (1 + tp_move)
        sl = price * (1 - sl_move)
    else:
        direction = "SHORT"
        tp = price * (1 - tp_move)
        sl = price * (1 + sl_move)

    return {
        "asset": asset,
        "direction": direction,
        "entry": price,
        "tp": tp,
        "sl": sl,
        "edge": edge,
        "mfe": 0,
        "mae": 0
    }
