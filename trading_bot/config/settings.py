# trading_bot/config/settings.py

DEFAULT_SLIPPAGE_PCT = 0.003   #buy_limit_with_slippageính limit price dựa vào slippageGửi lệnh LIMIT có kiểm soát slippage (mặc định lấy từ config).
DEFAULT_LEVERAGE = 5 # đòn bẩy x5
DEFAULT_RETRIES = 3 # Số lần thử lệnh giao dịch trên Binance. khi gửi lệnh thất bại
DEFAULT_SYMBOL = "BTCUSDT"
