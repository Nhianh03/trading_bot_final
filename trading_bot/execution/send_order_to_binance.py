import logging
from binance.client import Client
from binance.exceptions import BinanceAPIException
from trading_bot.execution.retry_utils import retry_on_binance_error

# Cấu hình log
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_binance_client(api_key: str, api_secret: str, use_testnet: bool = True) -> Client:
    """
    Khởi tạo Binance Client cho testnet hoặc mainnet.
    """
    client = Client(api_key, api_secret)
    if use_testnet:
        client.API_URL = 'https://testnet.binancefuture.com/fapi'
    return client


def send_order(client: Client, symbol: str, side: str, order_type: str, quantity: float, max_retries=3, delay=1):
    """
    Gửi lệnh Futures đến Binance với retry nếu gặp lỗi tạm thời.

    Args:
        client (Client): Binance Client.
        symbol (str): Ví dụ "BTCUSDT".
        side (str): "BUY" hoặc "SELL".
        order_type (str): "MARKET", "LIMIT", v.v.
        quantity (float): Số lượng cần giao dịch.
        max_retries (int): Số lần thử lại nếu lỗi.
        delay (int): Thời gian chờ giữa các lần retry.

    Returns:
        dict | None: Lệnh nếu thành công, None nếu lỗi.
    """
    def create_order():
        return client.futures_create_order(
            symbol=symbol,
            side=side,
            type=order_type,
            quantity=quantity
        )

    try:
        logger.info(f"📤 Gửi lệnh {side} {order_type}: {symbol} x {quantity}")
        order = retry_on_binance_error(create_order, max_retries=max_retries, delay=delay)
        logger.info(f"✅ Đã gửi lệnh thành công: {order['orderId']}")
        return order
    except BinanceAPIException as e:
        logger.error(f"❌ Binance API lỗi: {e.message}")
    except Exception as e:
        logger.error(f"❌ Lỗi không xác định: {e}")
    return None
