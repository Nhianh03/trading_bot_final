# Dưới đây là file order_utils.py được viết chuyên nghiệp, hỗ trợ:
# Tính quantity mua theo số USDT (với đòn bẩy tùy chọn)
# Lấy tick size và step size từ Binance để làm tròn chuẩn
# Tùy biến dễ dàng cho nhiều cặp symbol khác nhau

# trading_bot/excution/order_utils.py
# trading_bot/excution/order_utils.py

# trading_bot/excution/order_utils.py

import logging
from typing import Tuple, Optional
from binance.client import Client
from binance.exceptions import BinanceAPIException

from trading_bot.config.settings import DEFAULT_SLIPPAGE_PCT
from trading_bot.execution.retry_utils import retry_on_binance_error

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


# === Lấy dữ liệu cơ bản ===

def get_usdt_balance(client: Client) -> float:
    try:
        balance = retry_on_binance_error(client.futures_account_balance)
        for asset in balance:
            if asset['asset'] == 'USDT':
                return float(asset['balance'])
    except Exception as e:
        logger.error(f"❌ Lỗi lấy số dư: {e}")
    return 0.0


def get_price(client: Client, symbol: str) -> float:
    try:
        result = retry_on_binance_error(lambda: client.get_symbol_ticker(symbol=symbol))
        return float(result['price'])
    except BinanceAPIException as e:
        logger.error(f"❌ Lỗi lấy giá {symbol}: {e}")
        raise


def get_symbol_precision(client: Client, symbol: str) -> Tuple[float, float]:
    try:
        info = retry_on_binance_error(client.futures_exchange_info)
        for s in info["symbols"]:
            if s["symbol"] == symbol:
                filters = s["filters"]
                step_size = float([f for f in filters if f["filterType"] == "LOT_SIZE"][0]["stepSize"])
                tick_size = float([f for f in filters if f["filterType"] == "PRICE_FILTER"][0]["tickSize"])
                return step_size, tick_size
    except Exception as e:
        logger.error(f"❌ Lỗi lấy precision: {e}")
    raise ValueError(f"Không tìm thấy thông tin symbol {symbol}")


# === Xử lý làm tròn ===

def round_quantity(qty: float, step: float) -> float:
    return round(qty - (qty % step), 6)


# === Tính toán số lượng ===

def calculate_quantity(client: Client, symbol: str, usdt_amount: float, leverage: int = 1) -> float:
    try:
        price = get_price(client, symbol)
        raw_qty = (usdt_amount * leverage) / price
        step_size, _ = get_symbol_precision(client, symbol)
        qty = round_quantity(raw_qty, step_size)
        logger.info(f"📌 {symbol} | Giá: {price:.2f}, SL tính: {raw_qty:.6f}, Làm tròn: {qty}")
        return qty
    except Exception as e:
        logger.error(f"❌ Không tính được quantity: {e}")
        return 0.0


def calculate_quantity_by_balance_pct(client: Client, symbol: str, balance_pct: float, leverage: int = 1) -> float:
    usdt_balance = get_usdt_balance(client)
    usdt_amount = usdt_balance * balance_pct
    return calculate_quantity(client, symbol, usdt_amount, leverage)


def calculate_quantity_by_risk(
    client: Client,
    symbol: str,
    risk_pct: float,
    stop_loss_pct: float,
    leverage: int = 1
) -> float:
    try:
        price = get_price(client, symbol)
        balance = get_usdt_balance(client)
        max_loss = balance * risk_pct
        raw_qty = (max_loss / (price * stop_loss_pct)) * leverage
        step_size, _ = get_symbol_precision(client, symbol)
        return round_quantity(raw_qty, step_size)
    except Exception as e:
        logger.error(f"❌ Không tính được quantity theo risk: {e}")
        return 0.0


# === Đặt lệnh ===

def set_leverage(client: Client, symbol: str, leverage: int):
    try:
        retry_on_binance_error(lambda: client.futures_change_leverage(symbol=symbol, leverage=leverage))
        logger.info(f"✅ Đòn bẩy {symbol} đã đặt thành {leverage}x")
    except Exception as e:
        logger.warning(f"⚠️ Không thể đặt đòn bẩy: {e}")


def place_limit_order_with_slippage_control(
    client: Client,
    symbol: str,
    side: str,
    quantity: float,
    slippage_pct: float = DEFAULT_SLIPPAGE_PCT,
    max_retries: int = 3,
    delay: int = 1
) -> Optional[dict]:
    """
    Đặt lệnh LIMIT có kiểm soát trượt giá và retry khi lỗi Binance.

    Args:
        client: Binance client
        symbol: Cặp giao dịch
        side: "BUY" hoặc "SELL"
        quantity: Khối lượng đặt lệnh
        slippage_pct: % trượt giá tối đa cho phép
        max_retries: Số lần retry khi lỗi
        delay: Thời gian chờ giữa các lần retry

    Returns:
        dict: Thông tin lệnh nếu thành công
    """
    try:
        price = retry_on_binance_error(lambda: get_price(client, symbol), max_retries, delay)
        step_size, tick_size = retry_on_binance_error(lambda: get_symbol_precision(client, symbol), max_retries, delay)

        if side == "BUY":
            limit_price = price * (1 + slippage_pct)
        else:
            limit_price = price * (1 - slippage_pct)

        limit_price = round(limit_price - (limit_price % tick_size), 6)
        quantity = round_quantity(quantity, step_size)

        def order_func():
            return client.futures_create_order(
                symbol=symbol,
                side=Client.SIDE_BUY if side == "BUY" else Client.SIDE_SELL,
                type=Client.ORDER_TYPE_LIMIT,
                price=str(limit_price),
                quantity=quantity,
                timeInForce="GTC"
            )

        order = retry_on_binance_error(order_func, max_retries, delay)
        logger.info(f"✅ LIMIT {side} {quantity} {symbol} tại {limit_price} (slippage {slippage_pct*100:.2f}%)")
        return order

    except BinanceAPIException as e:
        logger.error(f"❌ Lỗi khi đặt lệnh LIMIT: {e}")
        return None
