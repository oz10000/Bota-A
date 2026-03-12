# =========================================================
# CONFIGURACIÓN
# =========================================================
INITIAL_CAPITAL = 100
ASSETS = ["BTC","ETH","SOL"]
TIMEFRAME = "3min"
LOOKBACK = 200
LOOP_DELAY = 60  # segundos
EMA_PERIOD = 20
ATR_PERIOD = 14
EDGE_THRESHOLD = 0.003
ATR_MULTIPLIER = 1.5
TP_EDGE = 0.30
BASE_URL = "https://api.kucoin.com/api/v1/market/candles"

# Archivos de runtime
TRADES_FILE = "runtime/trades.csv"
METRICS_FILE = "runtime/metrics.json"
BOT_LOG = "runtime/bot_log.txt"
STATE_FILE = "runtime/state.json"
