# trading_bot/execution/retry_utils.py
# ✅ Mục tiêu:
# Tái sử dụng logic retry (Gửi lệnh lại nếu lỗi tạm thời).
# Tách biệt rõ ràng giữa chiến lược và thực thi.
# Tích hợp sẵn retry vào mọi hàm gửi lệnh, bao gồm cả send_order, place_market_order_with_slippage_control,
import time
import logging
from binance.exceptions import BinanceAPIException

logger = logging.getLogger(__name__)

def retry_on_binance_error(func, max_retries=3, delay=1, *args, **kwargs):
    """
    Gửi lại lệnh nếu bị lỗi tạm thời từ Binance.
    """
    for attempt in range(1, max_retries + 1):
        try:
            return func(*args, **kwargs)
        except BinanceAPIException as e:
            logger.warning(f"❗️ Lỗi Binance (thử lần {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                time.sleep(delay)
            else:
                logger.error("❌ Gửi lệnh thất bại sau nhiều lần thử.")
                raise e
