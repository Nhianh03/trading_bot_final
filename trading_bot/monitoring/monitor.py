# monitor.py
# Ghi log reward, action, latency, symbol và mode vào MongoDB

import time
import logging
from datetime import datetime, timezone
from pymongo import MongoClient, errors

# ====== CONFIG ======
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "ppo_monitor"
COLLECTION_NAME = "reward_logs"

# ====== LOGGING CONFIG ======
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class RewardMonitor:
    def __init__(self, uri=MONGO_URI, db=DB_NAME, collection=COLLECTION_NAME):
        self.uri = uri
        self.db_name = db
        self.collection_name = collection
        self.client = Nonea
        self.collection = None
        self.connected = False
        self._connect()

    def _connect(self):
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=3000)
            self.client.server_info()  # Test kết nối
            self.collection = self.client[self.db_name][self.collection_name]
            self.connected = True
            logging.info(f"✅ Đã kết nối MongoDB tại {self.uri} → {self.db_name}.{self.collection_name}")
        except errors.ServerSelectionTimeoutError as e:
            logging.error(f"❌ Kết nối MongoDB thất bại: {e}")
            self.connected = False

    def log(self, reward: float, action: str, latency_ms: float = None, symbol: str = "BTCUSDT", mode: str = "live"):
        if not self.connected:
            logging.warning("⚠️ MongoDB chưa kết nối. Bỏ qua ghi log.")
            return

        entry = {
            "timestamp": datetime.now(timezone.utc),
            "reward": reward,
            "action": action,
            "latency_ms": latency_ms,
            "symbol": symbol,
            "mode": mode
        }

        try:
            self.collection.insert_one(entry)
            logging.info(f"📌 Ghi log: {entry}")
        except Exception as e:
            logging.error(f"❌ Không thể ghi log vào MongoDB: {e}")

# === Test riêng ===
if __name__ == "__main__":
    monitor = RewardMonitor()
    for i in range(5):
        reward = round(0.1 * i, 3)
        action = "BUY" if i % 2 == 0 else "SELL"
        latency = round(10 + i * 1.2, 2)
        monitor.log(reward, action, latency, symbol="BTCUSDT", mode="test")
        time.sleep(1)
