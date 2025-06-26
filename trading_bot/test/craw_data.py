# from pymongo import MongoClient
# from datetime import datetime
#
# client = MongoClient("mongodb://localhost:27017/")
# col = client["market_data"]["market_ticks"]
#
# start = datetime(2025, 6, 20)
# end = datetime(2025, 6, 21)
#
# count = col.count_documents({
#     "source_type": "trade",
#     "timestamp": {"$gte": start, "$lt": end}
# })
# print(f"Số lượng trade từ {start} đến {end}: {count}")



#log dữ liệu gần nhất trong MongoDB
from pymongo import MongoClient
import pandas as pd

client = MongoClient("mongodb://localhost:27017/")
col = client["market_data"]["market_ticks"]

latest_trade = col.find_one(
    {"source_type": "trade"},
    sort=[("timestamp", -1)],
    projection={"timestamp": 1}
)

if latest_trade:
    print(f"Dữ liệu mới nhất: {latest_trade['timestamp']}")
else:
    print(" Chưa có dữ liệu trade nào.")


# from pymongo import MongoClient
# from datetime import datetime, timezone
#
# client = MongoClient("mongodb://localhost:27017/")
# db = client["market_data"]
#
# start = datetime(2025, 6, 21, tzinfo=timezone.utc)
# end = datetime(2025, 6, 22, tzinfo=timezone.utc)
#
# count = db.market_ticks.count_documents({
#     "source_type": "trade",
#     "timestamp": { "$gte": start, "$lt": end }
# })
# print("Số dữ liệu trade:", count)
