# trading_bot/excution/ezbot.py - Manual Trading Bot Controller (Trade thủ công hoặc làm trung gian AI)
#đùng dể run tự động abwnfg tay Bạn muốn tạo một UI frontend đặt lệnh dễ dàng Bạn muốn viết bot semi-auto (người chọn action, bot thực thi)
import time
import logging
from binance.client import Client
from binance.exceptions import BinanceAPIException
from trading_bot.config.settings import DEFAULT_SLIPPAGE_PCT
from trading_bot.execution.send_order_to_binance import send_order
from trading_bot.execution.risk_manager import RiskManager
from trading_bot.execution.order_utils import (
    calculate_quantity,
    get_price,
    place_limit_order_with_slippage_control
)
from trading_bot.execution.advance_order_manager import place_bracket_order
from trading_bot.execution.position_manager import PositionManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class EZBot:
    def __init__(self, api_key: str, api_secret: str, symbol="BTCUSDT", use_testnet=True):
        self.symbol = symbol.upper()
        self.client = Client(api_key, api_secret)
        if use_testnet:
            self.client.API_URL = 'https://testnet.binance.vision/api'
        self.position_manager = PositionManager(self.client, symbol=self.symbol)
        self.risk_manager = RiskManager(self.client)

    # ====== GỬI LỆNH MUA / BÁN ======
    def _place_order_with_retry(self, side, order_type, quantity, retries=3):
        for attempt in range(retries):
            try:
                logger.info(f"[{side}] Gửi lệnh: {self.symbol} x {quantity}")
                order = send_order(self.client, self.symbol, side, order_type, quantity)
                self.position_manager.refresh()
                return order
            except BinanceAPIException as e:
                logger.error(f"Lỗi gửi lệnh: {e} - Thử lại ({attempt+1}/{retries})")
                time.sleep(1)
        logger.error(f"❌ Gửi lệnh thất bại sau {retries} lần thử")
        return None

    def buy_market(self, quantity: float):
        if self.position_manager.has_open_position():
            logger.warning("⚠Đã có vị thế mở, nên đóng trước khi mua thêm.")
            return None
        return self._place_order_with_retry("BUY", "MARKET", quantity)

    def sell_market(self, quantity: float):
        if self.position_manager.has_open_position():
            logger.warning(" Đã có vị thế mở, nên đóng trước khi bán thêm.")
            return None
        return self._place_order_with_retry("SELL", "MARKET", quantity)

    def buy_by_risk(self, risk_pct: float, stop_loss_pct: float, leverage=1):
        qty = self.risk_manager.get_quantity_by_risk(self.symbol, risk_pct, stop_loss_pct, leverage)
        if qty <= 0:
            logger.warning("❌ Không thể tính được khối lượng giao dịch từ risk")
            return None
        return self.buy_market(qty)

    def sell_by_risk(self, risk_pct: float, stop_loss_pct: float, leverage=1):
        qty = self.risk_manager.get_quantity_by_risk(self.symbol, risk_pct, stop_loss_pct, leverage)
        if qty <= 0:
            logger.warning("❌ Không thể tính được khối lượng giao dịch từ risk")
            return None
        return self.sell_market(qty)

    # ====== MUA / BÁN THEO USDT ======
    def buy_from_usdt(self, usdt_amount: float, leverage=1):
        qty = calculate_quantity(self.client, self.symbol, usdt_amount, leverage)
        return self.buy_market(qty)

    def sell_from_usdt(self, usdt_amount: float, leverage=1):
        qty = calculate_quantity(self.client, self.symbol, usdt_amount, leverage)
        return self.sell_market(qty)

    # ====== SLIPPAGE MARKET ORDER ======
    def buy_with_slippage(self, usdt_amount: float, leverage=1, slippage_pct: float = DEFAULT_SLIPPAGE_PCT):
        qty = calculate_quantity(self.client, self.symbol, usdt_amount, leverage)
        return place_limit_order_with_slippage_control(self.client, self.symbol, "BUY", qty, slippage_pct)

    def sell_with_slippage(self, usdt_amount: float, leverage=1, slippage_pct: float = DEFAULT_SLIPPAGE_PCT):
        qty = calculate_quantity(self.client, self.symbol, usdt_amount, leverage)
        return place_limit_order_with_slippage_control(self.client, self.symbol, "SELL", qty, slippage_pct)

    # ====== MUA / BÁN KÈM TP/SL ======
    def buy_with_tp_sl(self, usdt_amount: float, stop_loss_pct=0.01, take_profit_pct=0.02, leverage=1):
        qty = calculate_quantity(self.client, self.symbol, usdt_amount, leverage)
        if qty <= 0:
            logger.warning("❌ Không thể tính được khối lượng giao dịch.")
            return None
        entry_price = get_price(self.client, self.symbol)
        logger.info(f"📈 Buy with TP/SL | Giá entry: {entry_price}, SL: {stop_loss_pct*100}%, TP: {take_profit_pct*100}%")
        return place_bracket_order(
            client=self.client,
            symbol=self.symbol,
            side="BUY",
            quantity=qty,
            entry_price=entry_price,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct
        )

    def sell_with_tp_sl(self, usdt_amount: float, stop_loss_pct=0.01, take_profit_pct=0.02, leverage=1):
        qty = calculate_quantity(self.client, self.symbol, usdt_amount, leverage)
        if qty <= 0:
            logger.warning("❌ Không thể tính được khối lượng giao dịch.")
            return None
        entry_price = get_price(self.client, self.symbol)
        logger.info(f"📉 Sell with TP/SL | Giá entry: {entry_price}, SL: {stop_loss_pct*100}%, TP: {take_profit_pct*100}%")
        return place_bracket_order(
            client=self.client,
            symbol=self.symbol,
            side="SELL",
            quantity=qty,
            entry_price=entry_price,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct
        )

    # ====== ĐÓNG VỊ THẾ ======
    def close_position(self):
        return self.position_manager.close_position()

    # ====== LẤY THÔNG TIN ======
    def get_unrealized_pnl(self):
        pnl = self.position_manager.get_unrealized_pnl()
        logger.info(f"💰 PnL chưa chốt: {pnl:.2f} USDT")
        return pnl

    def get_account_summary(self):
        try:
            account = self.client.get_account()
            balances = {
                b['asset']: float(b['free']) for b in account['balances'] if float(b['free']) > 0
            }
            logger.info("🧾 Tài khoản hiện có:")
            for asset, balance in sorted(balances.items()):
                logger.info(f"🔹 {asset}: {balance}")
            return balances
        except Exception as e:
            logger.error(f"❌ Lỗi lấy tài khoản: {e}")
            return dict()

    def get_position(self):
        return self.position_manager._fetch_position()

if __name__ == "__main__":
    from secrets_kpi import API_KEY, API_SECRET

    bot = EZBot(API_KEY, API_SECRET, symbol="BTCUSDT", use_testnet=True)

    # Kiểm tra tài khoản & vị thế
    bot.get_account_summary()
    bot.get_position()

    # Gửi lệnh mua có kiểm soát slippage
    bot.buy_with_slippage(usdt_amount=20, leverage=3)

    # Gửi lệnh buy kèm TP/SL
    # bot.buy_with_tp_sl(usdt_amount=20, stop_loss_pct=0.01, take_profit_pct=0.03, leverage=3)

    # Kiểm tra lãi/lỗ chưa chốt
    bot.get_unrealized_pnl()

    # Đóng nếu cần
    # bot.close_position()
