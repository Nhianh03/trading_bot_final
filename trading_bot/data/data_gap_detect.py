# data_gap_detect.py
from pymongo import MongoClient
import requests
import logging
from datetime import datetime, timezone


# === Config ===
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "market_data"
COLLECTION_NAME = "market_ticks"
THRESHOLD_SECONDS = 60

TELEGRAM_TOKEN = "77576316062:AAEvjGHBT5zMdgEl-khqo0a0x8p10zPSAIs"
TELEGRAM_CHAT_ID = "7576316062"

# === Logging ===
logging.basicConfig(
    filename='data_gap.log',
    level=logging.WARNING,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getMe"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logging.error(f" Telegram error: {e}")

def detect_data_gap():
    client = MongoClient(MONGO_URI)
    collection = client[DB_NAME][COLLECTION_NAME]

    latest_doc = collection.find_one(sort=[("timestamp", -1)])
    if latest_doc:
        last_ts = latest_doc["timestamp"]
        if last_ts.tzinfo is None:
            last_ts = last_ts.replace(tzinfo=timezone.utc)  # ensure timezone-aware

        now = datetime.now(timezone.utc)
        delay = (now - last_ts).total_seconds()
        if delay > THRESHOLD_SECONDS:
            msg = f"Data gap detected! Last data was {delay:.0f} seconds ago (at {last_ts})"
            logging.warning(msg)
            send_telegram_alert(msg)
    else:
        msg = "No data found in MongoDB!"
        logging.warning(msg)
        send_telegram_alert(msg)

if __name__ == "__main__":
    send_telegram_alert("Bot đang hoạt động – test OK!")