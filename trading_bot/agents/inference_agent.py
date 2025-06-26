#model cho trading_env chạy RL inference real-time dùng Reinforcement Learning (RL)
import time
from pymongo import MongoClient, errors
from stable_baselines3 import PPO
from trading_bot.data.get_latest_state import get_latest_state
from datetime import datetime, timezone
from binance.client import Client
from trading_bot.execution.secrets_kpi import API_KEY, API_SECRET
# === Cấu hình ===
MODEL_PATH = "/Users/mac/Downloads/FINANCE/get_new_data/trading_bot/model/ppo_btcusdt_model.zip"
RETRY_DELAY_SECONDS = 5
MONGO_URI = "mongodb://localhost:27017"
SYMBOL = "BTCUSDT"
from trading_bot.execution.secrets_kpi import API_KEY, API_SECRET
ORDER_QUANTITY = 0.01

# === Kết nối Binance Testnet ===
binance_client = Client(API_KEY, API_SECRET)
binance_client.API_URL = 'https://testnet.binancefuture.com/fapi'

# === Hàm gửi lệnh ===
def send_order_to_binance(action: str, symbol: str, quantity=ORDER_QUANTITY):
    side = Client.SIDE_BUY if action == "BUY" else Client.SIDE_SELL
    try:
        order = binance_client.futures_create_order(
            symbol=symbol,
            side=side,
            type=Client.ORDER_TYPE_MARKET,
            quantity=quantity
        )
        print(f"[{datetime.now(timezone.utc)}] ✅ Order sent: {order}")
    except Exception as e:
        print(f"[{datetime.now(timezone.utc)}] ❌ Order failed: {e}")

# === Load model PPO ===
print(f"[{datetime.now(timezone.utc)}] 🚀 Loading model from {MODEL_PATH}...")
model = PPO.load(MODEL_PATH)
print(f"[{datetime.now(timezone.utc)}] ✅ Model loaded successfully.")

# === Hàm kiểm tra kết nối MongoDB ===
def check_mongo_connection(uri, retries=3):
    for i in range(retries):
        try:
            client = MongoClient(uri, serverSelectionTimeoutMS=3000)
            client.server_info()
            print(f"[{datetime.now(timezone.utc)}] ✅ MongoDB connection established.")
            return True
        except errors.ServerSelectionTimeoutError as e:
            print(f"[{datetime.now(timezone.utc)}] ⚠ MongoDB connection failed (retry {i+1}/{retries}): {e}")
            time.sleep(RETRY_DELAY_SECONDS)
    return False

# === Inference loop ===
def run_agent():
    if not check_mongo_connection(MONGO_URI):
        print(f"[{datetime.now(timezone.utc)}] ❌ Could not connect to MongoDB after retries. Exiting.")
        return

    print(f"[{datetime.now(timezone.utc)}] 🧠 Starting inference loop for {SYMBOL}...")

    while True:
        try:
            state = get_latest_state()
            action, _ = model.predict(state, deterministic=True)

            if action == 1:
                print(f"[{datetime.now(timezone.utc)}] 🟢 Action: BUY")
                send_order_to_binance("BUY", symbol=SYMBOL)

            elif action == 2:
                print(f"[{datetime.now(timezone.utc)}] 🔴 Action: SELL")
                send_order_to_binance("SELL", symbol=SYMBOL)

            else:
                print(f"[{datetime.now(timezone.utc)}] ⏸ Action: HOLD")

        except errors.ServerSelectionTimeoutError:
            print(f"[{datetime.now(timezone.utc)}] 🔌 Lost MongoDB connection. Retrying...")
            if not check_mongo_connection(MONGO_URI):
                print(f"[{datetime.now(timezone.utc)}] ❌ Persistent MongoDB failure. Exiting agent.")
                break

        except Exception as e:
            print(f"[{datetime.now(timezone.utc)}] ❌ Inference error: {e}")

        time.sleep(1)

# === Chạy nếu là file chính ===
if __name__ == "__main__":
    run_agent()
