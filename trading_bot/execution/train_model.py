#trading model mặc định
import os
import sys
from datetime import datetime, timedelta, timezone
import logging

from stable_baselines3 import PPO
from stable_baselines3.common.vec_env import DummyVecEnv

# Cho phép import module trading_bot
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from trading_bot.execution.trading_env import (
    get_env_for_date,
    evaluate_agent,
    compute_backtest_metrics
)

# ================================
# ⚙️ CONFIG
# ================================
INTRADAY_START_HOUR = 9   # Giờ bắt đầu lấy dữ liệu train (giờ VN)
INTRADAY_END_HOUR = 15    # Giờ kết thúc
TRAIN_DAYS = 5           # Số ngày gần nhất dùng để huấn luyện
TOTAL_TIMESTEPS = 50000   # Số bước học
MODEL_OUTPUT_DIR = "./saved_models"

# ================================
# 🚀 Train Function
# ================================
def train_intraday_model():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    now = datetime.utcnow().replace(tzinfo=timezone.utc)
    end_date = now.date()
    start_date = end_date - timedelta(days=TRAIN_DAYS)

    logging.info(f"🧠 Training intraday PPO model on {TRAIN_DAYS} days: {start_date} → {end_date}")

    # Format ISO with intraday hours in UTC
    vn_tz_offset = timedelta(hours=7)
    start_iso = datetime.combine(start_date, datetime.min.time()) + vn_tz_offset + timedelta(hours=INTRADAY_START_HOUR)
    end_iso = datetime.combine(end_date, datetime.min.time()) + vn_tz_offset + timedelta(hours=INTRADAY_END_HOUR)

    env = get_env_for_date(
        start_date=start_iso.isoformat(),
        end_date=end_iso.isoformat()
    )
    vec_env = DummyVecEnv([lambda: env])

    model = PPO("MlpPolicy", vec_env, verbose=1)
    model.learn(total_timesteps=TOTAL_TIMESTEPS)

    # Lưu mô hình
    os.makedirs(MODEL_OUTPUT_DIR, exist_ok=True)
    model_path = os.path.join(MODEL_OUTPUT_DIR, f"ppo_intraday_model_{now.strftime('%Y%m%d_%H%M')}.zip")
    model.save(model_path)
    logging.info(f"✅ Model saved to {model_path}")

    # Đánh giá hiệu suất
    results = evaluate_agent(env, model)
    metrics = compute_backtest_metrics(env.trades)

    logging.info("📊 Backtest Metrics:")
    for k, v in metrics.items():
        logging.info(f"{k}: {v:.4f}")

    return model_path, metrics

# ================================
# ▶️ Run
# ================================
if __name__ == "__main__":
    train_intraday_model()
