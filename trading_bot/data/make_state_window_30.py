# dùng dữ liệu build feature chuyển dữ liệu thị trường (đã chuẩn hóa) thành tensor 3D, dùng để:
#Huấn luyện mô hình Reinforcement Learning (ví dụ PPO) hoặc Deep Learning khác
#Huấn luyện mô hình PPOMỗi state là 1 quan sát (30 bước trước đó)
#Tạo tập nhiều sample state từ quá khứ → để train / backtest - Nhiều state: (num_samples, window, num_features)
# Khi huấn luyện PPO, LSTM, Transformer, hoặc backtest - Dữ liệu lịch sử dài (hàng trăm điểm) - Raise lỗi luôn -Có thể xuất sample đầu


import numpy as np
import pandas as pd
import logging
from trading_bot.data.future_streamer import build_features_from_mongo

logging.basicConfig(level=logging.INFO)


def make_state(df: pd.DataFrame, window: int = 30, save_path: str = None) -> np.ndarray:
    """
    Biến DataFrame thành tensor trạng thái 3D: (num_samples, window, num_features),
    dùng để huấn luyện hoặc backtest mô hình PPO.

    Args:
        df (pd.DataFrame): DataFrame đầu vào đã chuẩn hóa. Cần có đủ dữ liệu (≥ window).
        window (int): Kích thước cửa sổ thời gian (mỗi state là 1 đoạn dài `window`)
        save_path (str): Nếu cung cấp, lưu tensor đầu ra thành CSV để kiểm tra.

    Returns:
        np.ndarray: Tensor (num_samples, window, num_features)

    Raises:
        ValueError: Nếu đầu vào không hợp lệ hoặc thiếu dữ liệu.
    """
    if df is None or df.empty:
        raise ValueError("❌ DataFrame đầu vào rỗng.")

    if "timestamp" in df.columns:
        df = df.drop(columns=["timestamp"])

    if len(df) < window:
        raise ValueError(f"❌ Không đủ dữ liệu để tạo sliding window. Cần ≥ {window}, hiện có {len(df)}")

    data = df.values
    num_samples = len(data) - window

    states = np.array([
        data[i:i + window]
        for i in range(num_samples)
    ]).astype(np.float32)

    logging.info(f"✅ Tạo thành công {states.shape[0]} state(s) với shape {states.shape[1:]}")

    if save_path:
        # Lưu 1 vài sample đầu tiên để kiểm tra
        preview = states[0]
        #pd.DataFrame(preview).to_csv(save_path, index=False)
        logging.info(f"📁 Saved 1st state to: {save_path}")

    return states


# Test độc lập
if __name__ == "__main__":
    df = build_features_from_mongo(start_date="2025-06-20", end_date="2025-06-21", use_latest=False)

    try:
        tensor = make_state(df, window=30, save_path="debug_first_state.csv")
        print(f"✅ Tensor shape: {tensor.shape}")

        for i in range(min(3, tensor.shape[0])):
            print(f"📌 State {i + 1}:\n", tensor[i])
    except Exception as e:
        logging.error(f"Lỗi tạo state: {e}")
