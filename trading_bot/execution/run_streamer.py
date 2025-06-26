#run-streamer Ghi log ra file + console

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))

import time
import logging
from trading_bot.data.streamer import BinanceMarketStream

# === Cấu hình log path tuyệt đối ===
log_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../../trading_bot/data/streamer.log')
)
file_handler = logging.FileHandler(log_path)

# === Cấu hình log ra file & console ===
log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
file_handler.setFormatter(log_formatter)

console_handler = logging.StreamHandler()
console_handler.setFormatter(log_formatter)

logger = logging.getLogger()
logger.setLevel(logging.INFO)
logger.addHandler(file_handler)
logger.addHandler(console_handler)

def run_stream(symbol="BTCUSDT"):
    logger.info(f"Starting market stream for symbol: {symbol}")
    streamer = BinanceMarketStream(symbol=symbol)
    streamer.start()
    logger.info("Streamer started successfully.")

    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        logger.warning("Streamer stopped manually (Ctrl+C).")
    except Exception as e:
        logger.error(f"Unhandled error in streamer: {e}", exc_info=True)

if __name__ == "__main__":
    run_stream()
