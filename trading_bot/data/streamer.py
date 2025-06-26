#Thu thập dữ liệu thị trường theo thời gian thực (real-time) + snapshot định kỳ và lưu vào MongoDB.
#Lưu từng tick vào MongoDB
#Lấy dữ liệu funding rate (/fapi/v1/fundingRate)
#Lấy dữ liệu open interest (/futures/data/openInterestHist)
import websocket
import threading
import json
import requests
from pymongo import MongoClient
from datetime import datetime, timezone
import time
from trading_bot.data.mongo_utils import insert_tick, insert_snapshot

class BinanceMarketStream:
    def __init__(self, symbol="BTCUSDT", db_name="market_data"):
        self.symbol = symbol.upper()
        self.mongo_client = MongoClient("mongodb://localhost:27017/")
        self.db = self.mongo_client[db_name]
        self.snapshot_collection = self.db["market_snapshot"]
        self.tick_collection = self.db["market_ticks"]
        self.streams = {
            "trade": f"wss://fstream.binance.com/ws/{self.symbol.lower()}@trade",
            "forceOrder": f"wss://fstream.binance.com/ws/{self.symbol.lower()}@forceOrder",
            "depth": f"wss://fstream.binance.com/ws/{self.symbol.lower()}@depth20@100ms",
            "kline": f"wss://fstream.binance.com/ws/{self.symbol.lower()}@kline_1m"
        }

    def start(self):
        for source_type, url in self.streams.items():
            thread = threading.Thread(target=self.start_ws, args=(url, source_type), daemon=True)
            thread.start()
        print(f"[✓] WebSocket streams started for {self.symbol}")

    def start_ws(self, url, source_type):
        def on_message(ws, message):
            msg = json.loads(message)
            self.handle_message(msg, source_type)

        ws = websocket.WebSocketApp(url, on_message=on_message)
        ws.run_forever()

    def handle_message(self, msg, source_type):
        now = datetime.now(timezone.utc).isoformat()
        if source_type == "trade":
            data_summary = {
                "price": msg.get("p"),
                "quantity": msg.get("q"),
                "trade_time": msg.get("T")
            }
        elif source_type == "kline":
            k = msg.get("k", {})
            data_summary = {
                "open_time": k.get("t"),
                "open": k.get("o"),
                "close": k.get("c"),
                "volume": k.get("v")
            }
        elif source_type == "depth":
            bids = msg.get("b", [])
            data_summary = {
                "best_bid_price": bids[0][0] if bids else None,
                "best_bid_volume": bids[0][1] if bids else None
            }
        elif source_type == "forceOrder":
            o = msg.get("o", {})
            data_summary = {
                "price": o.get("p"),
                "quantity": o.get("q"),
                "side": o.get("S"),
                "order_type": o.get("o")
            }
        else:
            data_summary = {}


        print(f"[{source_type.upper()}] {now} | {data_summary}")

        event_time = msg.get("T") or msg.get("E") or int(datetime.now(timezone.utc).timestamp() * 1000)
        event_dt = datetime.fromtimestamp(event_time / 1000, tz=timezone.utc)

        tick_doc = {
            "timestamp": event_dt,
            "source_type": source_type,
            "symbol": msg.get("s", self.symbol),
            "data": data_summary
        }

        insert_tick("market_data", tick_doc)

    def fetch_funding_rate(self):
        url = "https://fapi.binance.com/fapi/v1/fundingRate"
        params = {"symbol": self.symbol, "limit": 1}
        try:
            r = requests.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            print("Funding Rate:", data)
            return data[0]
        except Exception as e:
            print(f"[!] Funding fetch error: {e}")
            return {}

    def fetch_open_interest(self):
        url = "https://fapi.binance.com/futures/data/openInterestHist"
        params = {"symbol": self.symbol, "period": "5m", "limit": 1}
        try:
            r = requests.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            print("Open Interest:", data)
            return data[0]
        except Exception as e:
            print(f"[!] Open interest fetch error: {e}")
            return {}

    def save_snapshot(self):
        funding_data = self.fetch_funding_rate()
        open_interest_data = self.fetch_open_interest()
        if funding_data and open_interest_data:
            now = datetime.now(timezone.utc)
            doc = {
                "timestamp": now,
                "symbol": self.symbol,
                "source_type": "snapshot",
                "funding_rate": {
                    "rate": funding_data.get("fundingRate"),
                    "mark_price": funding_data.get("markPrice"),
                    "funding_time": datetime.fromtimestamp(funding_data.get("fundingTime") / 1000, tz=timezone.utc)
                },
                "open_interest": {
                    "value": open_interest_data.get("sumOpenInterestValue"),
                    "contracts": open_interest_data.get("sumOpenInterest"),
                    "snapshot_time": datetime.fromtimestamp(open_interest_data.get("timestamp") / 1000, tz=timezone.utc)
                }
            }
            insert_snapshot("market_data", doc)
            print("[✓] Snapshot saved to MongoDB.")
if __name__ == "__main__":
    stream = BinanceMarketStream(symbol="BTCUSDT")
    stream.save_snapshot()  # Gọi snapshot ngay khi khởi chạy
    stream.start()          # Bắt đầu WebSocket

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopped.")