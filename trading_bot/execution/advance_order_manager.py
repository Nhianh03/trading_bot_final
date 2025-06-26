# trading_bot/execution/advance_order_manager.py

import logging
from binance.client import Client
from binance.exceptions import BinanceAPIException

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def place_bracket_order(
    client: Client,
    symbol: str,
    side: str,
    quantity: float,
    entry_price: float,
    stop_loss_pct: float = 0.01,  # 1% stop loss
    take_profit_pct: float = 0.02  # 2% take profit
):
    """
    Tạo lệnh bracket (entry + SL + TP).
    Binance Futures không hỗ trợ OCO trực tiếp, nên cần tuỳ biến bằng cách đặt các lệnh rời:
    - Lệnh chính: LIMIT entry
    - Lệnh SL: STOP_MARKET
    - Lệnh TP: LIMIT
    """
    try:
        side = side.upper()
        opposite_side = "SELL" if side == "BUY" else "BUY"

        # Entry order (limit)
        entry_order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type=Client.ORDER_TYPE_LIMIT,
            quantity=quantity,
            price=str(entry_price),
            timeInForce="GTC"
        )
        logger.info(f"Entry order placed: {entry_order['orderId']}")

        # Stop-loss
        stop_price = round(entry_price * (1 - stop_loss_pct) if side == "BUY" else entry_price * (1 + stop_loss_pct), 2)
        stop_order = client.futures_create_order(
            symbol=symbol,
            side=opposite_side,
            type=Client.ORDER_TYPE_STOP_MARKET,
            stopPrice=str(stop_price),
            closePosition=True,
            timeInForce="GTC"
        )
        logger.info(f"Stop-loss set at {stop_price}")

        # Take-profit
        tp_price = round(entry_price * (1 + take_profit_pct) if side == "BUY" else entry_price * (1 - take_profit_pct), 2)
        tp_order = client.futures_create_order(
            symbol=symbol,
            side=opposite_side,
            type=Client.ORDER_TYPE_LIMIT,
            price=str(tp_price),
            quantity=quantity,
            reduceOnly=True,
            timeInForce="GTC"
        )
        logger.info(f"Take-profit set at {tp_price}")

        return {
            "entry_order": entry_order,
            "stop_order": stop_order,
            "take_profit_order": tp_order
        }

    except BinanceAPIException as e:
        logger.error(f"Binance API Error: {e.message}")
    except Exception as e:
        logger.error(f"Unknown Error: {e}")
    return None
