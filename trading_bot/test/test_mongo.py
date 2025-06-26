# from pymongo import MongoClient
#
# client = MongoClient("mongodb://localhost:27017")
#
# # Xem tất cả DBs
# print("📦 Databases:")
# for db_name in client.list_database_names():
#     print(f" - {db_name}")
#     db = client[db_name]
#     print("   📁 Collections:")
#     for coll in db.list_collection_names():
#         print(f"     - {coll}")
#

from pymongo import MongoClient
client = MongoClient("mongodb://localhost:27017/")
print(client.server_info())  # Nếu dòng này lỗi thì Mongo chưa chạy
