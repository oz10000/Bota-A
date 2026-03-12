# =========================================================
# CONFIGURACIÓN CORREGIDA
# =========================================================
INITIAL_CAPITAL = 100
ASSETS = ["BTC","ETH","SOL"]
TIMEFRAME = "3min"
LOOKBACK = 200
LOOP_DELAY = 60  # segundos entre cada scan
EMA_PERIOD = 20
ATR_PERIOD = 14
EDGE_THRESHOLD = 0.003
ATR_MULTIPLIER = 1.5
TP_EDGE = 0.30
BASE_URL = "https://api.kucoin.com/api/v1/market/candles"

# Fallback para obtención de velas
FALLBACK_SOURCES = [
    "https://api.coingecko.com/api/v3/coins/{asset}/market_chart?vs_currency=usd&days=1&interval=minute",
    "https://api.crypto.com/v2/public/get-candlestick?instrument_name={asset}-USD&timeframe=3m"
]

# Archivos de runtime
TRADES_FILE = "runtime/trades.csv"
METRICS_FILE = "runtime/metrics.json"
BOT_LOG = "runtime/bot_log.txt"
STATE_FILE = "runtime/state.json"

# =========================================================
# AJUSTES PARA ESTABILIDAD
# =========================================================
MIN_CANDLES_REQUIRED = EMA_PERIOD + ATR_PERIOD + 2  # prevenir index out-of-bounds
ENABLE_FALLBACK = True  # activa el fallback automático
