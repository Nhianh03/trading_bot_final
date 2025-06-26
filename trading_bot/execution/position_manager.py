# trading_bot/execution/position_manager.py

import logging
from binance.client import Client
from binance.exceptions import BinanceAPIException

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class PositionManager:
    def __init__(self, client: Client, symbol: str = "BTCUSDT"):
        self.client = client
        self.symbol = symbol.upper()
        self.position = self._fetch_position()

    def _fetch_position(self) -> dict or None:
        """Lấy thông tin vị thế hiện tại từ Binance Futures"""
        try:
            positions = self.client.futures_position_information(symbol=self.symbol)
            for p in positions:
                amt = float(p["positionAmt"])
                if amt != 0:
                    pos = {
                        "symbol": self.symbol,
                        "amount": amt,
                        "entry_price": float(p["entryPrice"]),
                        "side": "LONG" if amt > 0 else "SHORT",
                        "unrealized_pnl": float(p["unrealizedProfit"])
                    }
                    logger.info(f"✅ Đã phát hiện vị thế đang mở: {pos}")
                    return pos
        except BinanceAPIException as e:
            logger.error(f"❌ Không thể lấy thông tin vị thế: {e}")
        return None

    def refresh(self):
        """Cập nhật lại vị thế hiện tại"""
        self.position = self._fetch_position()

    def has_open_position(self) -> bool:
        """Kiểm tra xem có vị thế đang mở không"""
        return self.position is not None

    def close_position(self, quantity: float = None) -> dict or None:
        """Đóng vị thế hiện tại bằng lệnh đối ứng"""
        if not self.has_open_position():
            logger.warning("⚠️ Không có vị thế để đóng.")
            return None

        side = "SELL" if self.position["side"] == "LONG" else "BUY"
        qty = abs(self.position["amount"]) if quantity is None else quantity

        try:
            logger.info(f"🛑 Đang gửi lệnh đóng vị thế: {side} {qty} {self.symbol}")
            order = self.client.futures_create_order(
                symbol=self.symbol,
                side=Client.SIDE_BUY if side == "BUY" else Client.SIDE_SELL,
                type=Client.ORDER_TYPE_MARKET,
                quantity=qty
            )
            logger.info(f"✅ Đã đóng vị thế: {order}")
            self.position = None
            return order
        except BinanceAPIException as e:
            logger.error(f"❌ Lỗi khi đóng vị thế: {e}")
            return None

    def get_unrealized_pnl(self) -> float:
        """Lấy PnL chưa chốt (nếu có)"""
        return self.position.get("unrealized_pnl", 0.0) if self.position else 0.0

    def get_side(self) -> str or None:
        """Lấy hướng của vị thế hiện tại: LONG / SHORT"""
        return self.position.get("side") if self.position else None
