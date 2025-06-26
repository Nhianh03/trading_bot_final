from pymongo import MongoClient
from datetime import datetime, timezone

def get_mongo_client(uri="mongodb://localhost:27017/"):
    return MongoClient(uri)

def get_collection(db_name, collection_name, uri="mongodb://localhost:27017/"):
    client = get_mongo_client(uri)
    db = client[db_name]
    return db[collection_name]

def insert_tick(db_name, doc, uri="mongodb://localhost:27017/"):
    collection = get_collection(db_name, "market_ticks", uri)
    collection.insert_one(doc)

def insert_snapshot(db_name, doc, uri="mongodb://localhost:27017/"):
    collection = get_collection(db_name, "market_snapshot", uri)
    collection.insert_one(doc)

def insert_many_records(db_name, collection_name, records, uri="mongodb://localhost:27017/"):
    if not records:
        print(f"[!] Không có dữ liệu để insert vào collection {collection_name}")
        return
    collection = get_collection(db_name, collection_name, uri)
    collection.insert_many(records)