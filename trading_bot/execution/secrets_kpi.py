from backtesting import Backtest, Strategy
from binance.client import Client
import pandas as pd
import numpy as np

# Nhập API Key và API Secret của bạn ở đây
api_key = 'jCA2Cq7UwLKOSFlByIsx8CrJ9NA2KXOCf5XPKYcupe5UlKSVqH8bchZmg8VPdGVT'
api_secret = 'XjAZOnAI6pW4E36iu6C1oC1kQXicYN2YHOCiS4Ee22U2mrieLy1waDqnsO9VY75w'


# Tạo đối tượng Client
client = Client(api_key, api_secret)

# ✅ Gán URL endpoint testnet thủ công (Spot)
client.API_URL = 'https://testnet.binance.vision/api'

# Lấy thông tin tài khoản
try:
    account = client.get_account()
    print(account)
except Exception as e:
    print("❌ Lỗi khi lấy thông tin tài khoản:", e)
