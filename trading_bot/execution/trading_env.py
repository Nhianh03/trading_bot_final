import gym
from gym import spaces
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from pymongo import MongoClient

from trading_bot.data.future_streamer import build_features_from_mongo
from trading_bot.data.make_state_window_30 import make_state

class TradingEnv(gym.Env):
    def __init__(self, state_tensor, price_series, initial_balance=1000, reward_mode="basic"):
        super().__init__()
        self.state_tensor = state_tensor
        self.price_series = price_series
        self.initial_balance = initial_balance
        self.reward_mode = reward_mode

        self.action_space = spaces.Discrete(3)
        self.observation_space = spaces.Box(
            low=-np.inf, high=np.inf,
            shape=self.state_tensor.shape[1:],
            dtype=np.float32
        )
        self.reset()

    def reset(self):
        self.current_step = 0
        self.balance = self.initial_balance
        self.position = 0
        self.entry_price = 0
        self.trades = []
        self.step_holding = 0
        return self._get_obs()

    def _get_obs(self):
        return self.state_tensor[self.current_step]

    def _compute_reward(self, profit, current_price):
        fee = current_price * 0.0004 * 2  # giả định phí 0.04% mỗi chiều
        reward = 0

        if self.reward_mode == "basic":
            reward = profit - fee
        elif self.reward_mode == "sharpe":
            recent_trades = np.array(self.trades[-10:])
            if len(recent_trades) > 1:
                mean_r = np.mean(recent_trades)
                std_r = np.std(recent_trades) + 1e-6
                reward = mean_r / std_r
            else:
                reward = profit - fee
        elif self.reward_mode == "penalty":
            penalty = 0.01 * self.step_holding if self.position != 0 else 0
            if abs(profit) < 0.1:
                penalty += 0.01
            reward = profit - fee - penalty
        return reward

    def step(self, action):
        done = False
        reward = 0
        current_price = self.price_series[self.current_step]

        if self.position != 0:
            self.step_holding += 1
        else:
            self.step_holding = 0

        if action == 1:
            if self.position == 0:
                self.position = 1
                self.entry_price = current_price
            elif self.position == -1:
                profit = self.entry_price - current_price
                self.balance += profit
                reward = self._compute_reward(profit, current_price)
                self.trades.append(profit)
                self.position = 0

        elif action == 2:
            if self.position == 0:
                self.position = -1
                self.entry_price = current_price
            elif self.position == 1:
                profit = current_price - self.entry_price
                self.balance += profit
                reward = self._compute_reward(profit, current_price)
                self.trades.append(profit)
                self.position = 0

        self.current_step += 1
        done = self.current_step >= len(self.state_tensor) - 1

        return self._get_obs(), reward, done, {
            "position": self.position,
            "entry_price": self.entry_price,
            "balance": self.balance,
            "cumulative_reward": sum(self.trades)
        }


def get_latest_trade_date():
    client = MongoClient("mongodb://localhost:27017/")
    col = client["market_data"]["market_ticks"]
    latest = col.find_one(
        {"source_type": "trade"},
        sort=[("timestamp", -1)],
        projection={"timestamp": 1}
    )
    return latest["timestamp"].date() if latest else None

def normalize_state_tensor(state_tensor):
    N, window, n_features = state_tensor.shape
    reshaped = state_tensor.reshape(-1, n_features)
    scaler = StandardScaler()
    normalized = scaler.fit_transform(reshaped)
    return normalized.reshape(N, window, n_features), scaler

def get_env_for_date(start_date=None, end_date=None, window=30, reward_mode="basic"):
    if start_date is None or end_date is None:
        latest = get_latest_trade_date()
        if not latest:
            raise ValueError("Không tìm thấy dữ liệu trade mới nhất.")
        start_date = latest.isoformat()
        end_date = (pd.Timestamp(latest) + pd.Timedelta(days=1)).isoformat()
        use_latest = True
    else:
        use_latest = False

    df = build_features_from_mongo(start_date=start_date, end_date=end_date, use_latest=use_latest)
    state_tensor = make_state(df, window=window)
    state_tensor, _ = normalize_state_tensor(state_tensor)
    price_series = state_tensor[:, -1, 0]
    return TradingEnv(state_tensor, price_series, reward_mode=reward_mode)

def evaluate_agent(env, model):
    obs = env.reset()
    done = False
    rewards, cumulative, actions, prices, positions = [], [], [], [], []

    while not done:
        action, _ = model.predict(obs, deterministic=True)
        obs, reward, done, info = env.step(action)
        rewards.append(reward)
        actions.append(int(action))
        prices.append(env.price_series[env.current_step])
        positions.append(env.position)
        cumulative.append(sum(env.trades))

    return {
        "rewards": rewards,
        "cumulative_rewards": cumulative,
        "actions": actions,
        "positions": positions,
        "prices": prices
    }

def compute_backtest_metrics(trades):
    pnl = np.array(trades)
    cumulative = np.cumsum(pnl)
    sharpe = np.mean(pnl) / (np.std(pnl) + 1e-8) * np.sqrt(252)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = running_max - cumulative
    max_drawdown = np.max(drawdown)
    win_rate = np.sum(pnl > 0) / len(pnl) if len(pnl) > 0 else 0

    return {
        "sharpe_ratio": sharpe,
        "max_drawdown": max_drawdown,
        "win_rate": win_rate,
        "total_trades": len(pnl)
    }
