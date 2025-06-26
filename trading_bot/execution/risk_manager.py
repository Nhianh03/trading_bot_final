# trading_bot/execution/risk_manager.py

import logging
from typing import Optional
from binance.client import Client
from trading_bot.execution.order_utils import (
    calculate_quantity_by_risk,
    set_leverage
)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class RiskManager:
    def __init__(self, client: Client, symbol: str = "BTCUSDT", leverage: int = 1):
        self.client = client
        self.symbol = symbol.upper()
        self.leverage = leverage
        set_leverage(self.client, self.symbol, leverage)

    def get_quantity_by_risk(self, risk_pct: float, stop_loss_pct: float) -> float:
        """
        Tính khối lượng giao dịch dựa trên mức rủi ro mong muốn và mức dừng lỗ.
        """
        qty = calculate_quantity_by_risk(
            self.client,
            self.symbol,
            risk_pct=risk_pct,
            stop_loss_pct=stop_loss_pct,
            leverage=self.leverage
        )
        logger.info(f"Khối lượng theo risk: {qty} {self.symbol} | Risk: {risk_pct*100:.2f}%, SL: {stop_loss_pct*100:.2f}%")
        return qty

    def adjust_leverage(self, leverage: int):
        """
        Cập nhật lại đòn bẩy và thiết lập lại trên Binance.
        """
        self.leverage = leverage
        set_leverage(self.client, self.symbol, leverage)
        logger.info(f"⚙️ Đòn bẩy mới: {leverage}x cho {self.symbol}")

    def evaluate_position_size(self, account_risk_pct: float, stop_loss_pct: float) -> Optional[float]:
        """
        Tính toán và xác định khối lượng giao dịch nên đặt dựa trên risk/reward.
        """
        try:
            qty = self.get_quantity_by_risk(account_risk_pct, stop_loss_pct)
            if qty <= 0:
                logger.warning("️ Số lượng tính được bằng 0 hoặc không hợp lệ.")
                return None
            return qty
        except Exception as e:
            logger.error(f"❌ Lỗi khi đánh giá khối lượng vị thế: {e}")
            return None

if __name__ == "__main__":
    from secrets_kpi import API_KEY, API_SECRET
    from trading_bot.execution.send_order_to_binance import create_binance_client

    client = create_binance_client(API_KEY, API_SECRET, use_testnet=True)
    risk = RiskManager(client, symbol="BTCUSDT", leverage=5)

    qty = risk.evaluate_position_size(account_risk_pct=0.01, stop_loss_pct=0.02)
    print("Khối lượng khuyến nghị:", qty)
