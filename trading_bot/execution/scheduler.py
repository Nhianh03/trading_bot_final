# scheduler.py – Lên lịch train model intraday mỗi ngày lúc 07:00 sáng
import os
import subprocess
import logging
from datetime import datetime
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.executors.pool import ThreadPoolExecutor
from pytz import timezone

# === CONFIG ===
TRAIN_SCRIPT_PATH = "trading_bot/execution/train_model.py"
LOG_TO_FILE = True  # ✅ True: log stdout + stderr vào file, False: chỉ log console
TIMEZONE = "Asia/Ho_Chi_Minh"

# === Logging setup ===
if LOG_TO_FILE:
    log_filename = f"logs/train_scheduler_{datetime.now().strftime('%Y%m%d')}.log"
    os.makedirs("logs", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename, mode='a', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
else:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# === Training job ===
def train_model():
    logging.info("🚀 Bắt đầu huấn luyện model intraday...")

    if not os.path.exists(TRAIN_SCRIPT_PATH):
        logging.error(f"❌ File train script không tồn tại: {TRAIN_SCRIPT_PATH}")
        return

    result = subprocess.run(
        ["python", TRAIN_SCRIPT_PATH],
        capture_output=True,
        text=True
    )

    if result.returncode == 0:
        logging.info("✅ Huấn luyện thành công.")
        logging.info(result.stdout)
    else:
        logging.error("❌ Huấn luyện thất bại:")
        logging.error(result.stderr)

# === Scheduler setup ===
scheduler = BlockingScheduler(
    executors={'default': ThreadPoolExecutor(1)},
    timezone=timezone(TIMEZONE)
)

# Huấn luyện mỗi ngày lúc 07:00 sáng
scheduler.add_job(train_model, 'cron', hour=7, minute=0)

logging.info(f"🕓 APScheduler đã khởi động. Đang chờ tới 07:00 ({TIMEZONE}) để bắt đầu training intraday.")
scheduler.start()
