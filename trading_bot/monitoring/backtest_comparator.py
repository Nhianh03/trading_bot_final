import pandas as pd
import matplotlib.pyplot as plt

# Load backtest & live data
live_path = "live_log.csv"
backtest_path = "backtest_result.csv"

live_df = pd.read_csv(live_path, parse_dates=['timestamp'])
backtest_df = pd.read_csv(backtest_path, parse_dates=['timestamp'])

# Align by timestamp
merged = pd.merge_asof(
    live_df.sort_values('timestamp'),
    backtest_df.sort_values('timestamp'),
    on='timestamp',
    suffixes=('_live', '_backtest'),
    direction='nearest',
    tolerance=pd.Timedelta(seconds=10)
)

# Plot comparison
plt.figure(figsize=(12, 5))
plt.plot(merged['timestamp'], merged['reward_live'], label='Live')
plt.plot(merged['timestamp'], merged['reward_backtest'], label='Backtest')
plt.xlabel("Time")
plt.ylabel("Reward")
plt.title("Live vs Backtest Reward")
plt.legend()
plt.tight_layout()
plt.show()
