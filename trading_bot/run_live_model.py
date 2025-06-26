import os
import time
import logging
import numpy as np
from datetime import datetime
from stable_baselines3 import PPO
from glob import glob
import pandas as pd

from trading_bot.execution.ezbot import EZBot
from trading_bot.data.future_streamer import build_features_from_mongo
from trading_bot.data.make_state_window_30 import make_state

# ==== CONFIG ====
api_key = 'jCA2Cq7UwLKOSFlByIsx8CrJ9NA2KXOCf5XPKYcupe5UlKSVqH8bchZmg8VPdGVT'
api_secret = 'XjAZOnAI6pW4E36iu6C1oC1kQXicYN2YHOCiS4Ee22U2mrieLy1waDqnsO9VY75w'
MODEL_DIR = "./saved_models"
SYMBOL = "BTCUSDT"
USDT_AMOUNT = 20
USE_TESTNET = True
SLEEP_SECONDS = 300  # 5 phút
LOG_FILE = "trade_logs.csv"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# ======================
# 🔁 Reload model nếu có file mới
# ======================
def find_latest_model(model_dir: str):
    zip_files = sorted(
        glob(os.path.join(model_dir, "ppo_intraday_model_*.zip")),
        reverse=True
    )
    return zip_files[0] if zip_files else None

def run_live_model():
    logging.info("🚀 AI Trading Bot (Live) - Đang chạy...")

    current_model_path = None
    model = None

    bot = EZBot(api_key, api_secret, symbol=SYMBOL, use_testnet=USE_TESTNET)

    # Tạo log file nếu chưa tồn tại
    if not os.path.exists(LOG_FILE):
        pd.DataFrame(columns=[
            "timestamp", "model", "action", "balance", "reward", "position", "latency_ms"
        ]).to_csv(LOG_FILE, index=False)

    while True:
        tick_start = time.time()

        # Check mô hình mới
        latest_model_path = find_latest_model(MODEL_DIR)
        if latest_model_path and latest_model_path != current_model_path:
            try:
                model = PPO.load(latest_model_path)
                current_model_path = latest_model_path
                logging.info(f"✅ Đã load mô hình mới: {latest_model_path}")
            except Exception as e:
                logging.error(f"❌ Lỗi load model: {e}")
                time.sleep(SLEEP_SECONDS)
                continue

        if model is None:
            logging.warning("⚠️ Chưa có mô hình để dự đoán.")
            time.sleep(SLEEP_SECONDS)
            continue

        try:
            # --- Dữ liệu đầu vào ---
            df = build_features_from_mongo(n_days=1)
            state_tensor = make_state(df, window=30)
            latest_state = state_tensor[-1][np.newaxis, ...]  # (1, 30, features)

            # --- Dự đoán hành động ---
            action, _ = model.predict(latest_state, deterministic=True)
            action_str = ["HOLD", "BUY", "SELL"][action]

            # --- Kiểm tra có đang giữ vị thế không ---
            position = bot.get_position()
            if position and position.get("positionAmt") not in [0, "0", "0.0"]:
                logging.info(f"📛 Đã có vị thế mở, bỏ qua lệnh mới (position = {position.get('positionAmt')})")
                action_str = "HOLD"
            else:
                if action == 1:
                    bot.buy_from_usdt(usdt_amount=USDT_AMOUNT)
                elif action == 2:
                    bot.sell_from_usdt(usdt_amount=USDT_AMOUNT)

            latency = (time.time() - tick_start) * 1000  # ms
            reward = bot.get_unrealized_pnl() or 0.0
            balance = bot.get_account_summary().get("USDT", None)

            logging.info(f"🤖 Hành động: {action_str} | Reward: {reward:.2f} | Balance: {balance}")

            # --- Ghi log ra file ---
            pd.DataFrame([{
                "timestamp": datetime.utcnow().isoformat(),
                "model": os.path.basename(current_model_path),
                "action": action_str,
                "balance": balance,
                "reward": reward,
                "position": position.get("positionAmt") if position else None,
                "latency_ms": latency
            }]).to_csv(LOG_FILE, mode="a", header=False, index=False)

        except Exception as e:
            logging.error(f"⚠️ Lỗi bot: {e}")

        logging.info(f"⏳ Chờ {SLEEP_SECONDS // 60} phút...\n")
        time.sleep(SLEEP_SECONDS)

if __name__ == "__main__":
    run_live_model()
