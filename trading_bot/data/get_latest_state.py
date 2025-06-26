#cung câops state mới nhất dưới dạng ténor và giá hiện tại
# •	Gửi vào mô hình PPO/LSTM để lấy action (Buy/Sell/Hold)
# Gắn vào vòng lặp dự đoán/cảnh báo Lấy 1 state gần nhất → để predict realtime -  1 state: (1, window, num_features) - Khi triển khai (inference real-time)
# Có bản safe_ để không raise lỗi - Có thể xuất window mới nhất
import numpy as np
import pandas as pd
import logging
from trading_bot.data.future_streamer import build_features_from_mongo

logging.basicConfig(level=logging.INFO)

def _get_feature_dataframe(window: int) -> pd.DataFrame:
    """
    Truy vấn dữ liệu đã chuẩn hóa từ Mongo và đảm bảo đủ độ dài.
    """
    df = build_features_from_mongo(
    start_date="2025-06-20",
    end_date="2025-06-21",
    use_latest=False,
    n_days=None
)

    if df is None or df.empty:
        raise ValueError("Dữ liệu MongoDB rỗng hoặc không tồn tại")

    df = df.sort_values("timestamp")

    if len(df) < window:
        raise ValueError(f"Không đủ dữ liệu để tạo window. Cần ≥ {window}, hiện có {len(df)}")

    return df.iloc[-window:].copy()

def get_latest_state(window: int = 30, save_path: str = None) -> np.ndarray:
    """
    Trả về tensor (1, window, num_features) làm input cho PPO model.
    Có thể lưu ra file CSV để debug.
    """
    df = _get_feature_dataframe(window)
    feature_cols = df.columns.drop("timestamp")
    feature_values = df[feature_cols].values.astype(np.float32)
    state = feature_values.reshape(1, window, -1)

    if save_path:
        pd.DataFrame(state[0], columns=feature_cols).to_csv(save_path, index=False)
        logging.info(f"✅ State window đã lưu tại: {save_path}")

    return state

def safe_get_latest_state(window: int = 30, save_path: str = None):
    """
    Phiên bản an toàn của get_latest_state (dùng trong vòng lặp real-time).
    """
    try:
        return get_latest_state(window=window, save_path=save_path)
    except ValueError as e:
        logging.warning(f"[SAFE STATE] {e}")
        return None

def get_latest_price() -> float:
    """
    Trả về giá 'close' gần nhất từ dữ liệu Mongo.
    """
    df = build_features_from_mongo()
    if df is None or df.empty:
        raise ValueError("Dữ liệu MongoDB trống")

    df = df.sort_values("timestamp")
    last_row = df.iloc[-1]

    if "close" not in df.columns:
        raise KeyError("Không tìm thấy cột 'close' trong dataframe")

    return float(last_row["close"])


# Test độc lập
if __name__ == "__main__":
    try:
        state = get_latest_state(save_path="debug_state.csv")
        print("✅ State shape:", state.shape)
        print("📊 Last row in window:\n", state[0][-1])
        print("💰 Latest close price:", get_latest_price())
    except Exception as e:
        logging.error(f"Lỗi khi test module: {e}")
