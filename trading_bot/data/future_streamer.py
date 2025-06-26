#bước 3 build feature từ dữ liệu lưu ở mongodb
import pandas as pd
from pymongo import MongoClient
from sklearn.preprocessing import MinMaxScaler


def to_utc(ts):
    ts = pd.Timestamp(ts)
    return ts.tz_localize("UTC") if ts.tzinfo is None else ts


def build_features_from_mongo(
    db_name="market_data",
    start_date=None,
    end_date=None,
    n_days=1,
    use_latest=True,
    uri="mongodb://localhost:27017/"
):
    print(f"✅ Đang chạy build_features_from_mongo với start_date={start_date}, end_date={end_date}, use_latest={use_latest}")

    client = MongoClient(uri)
    db = client[db_name]
    tick_collection = db["market_ticks"]

    # === Xử lý mốc thời gian ===
    if use_latest:
        today = pd.Timestamp.utcnow().floor("D")
        start_ts = to_utc((today - pd.Timedelta(days=n_days)).isoformat())
        end_ts = to_utc(today.isoformat())
        print(f"🗓️ Dùng today - n_days để lấy dữ liệu từ {start_ts} đến {end_ts}")
    else:
        if not start_date or not end_date:
            raise ValueError("❌ Cần truyền start_date và end_date nếu use_latest=False")
        start_ts = to_utc(start_date)
        end_ts = to_utc(end_date)
        print(f"🗓️ Dùng start_date + end_date → {start_ts} đến {end_ts}")
        if start_ts >= end_ts:
            raise ValueError(f"❌ Ngày bắt đầu ({start_ts}) phải nhỏ hơn ngày kết thúc ({end_ts})")

    # === FORCE ORDER ===
    df_liq = pd.DataFrame(list(tick_collection.find({
        "source_type": "forceOrder",
        "timestamp": {"$gte": start_ts, "$lt": end_ts}
    })))

    liq_agg = pd.DataFrame()
    if not df_liq.empty:
        df_liq["timestamp"] = pd.to_datetime(df_liq["timestamp"])
        df_liq["price"] = df_liq["data"].apply(lambda x: float(x.get("price", 0)))
        df_liq["quantity"] = df_liq["data"].apply(lambda x: float(x.get("quantity", 0)))
        df_liq["side"] = df_liq["data"].apply(lambda x: x.get("side", x.get("S", None)))
        df_liq["usd_value"] = df_liq["price"] * df_liq["quantity"]
        df_liq["is_whale"] = df_liq["usd_value"] > 100_000
        df_liq = df_liq.set_index("timestamp").sort_index()

        liq_agg["liq_count"] = df_liq["price"].resample("1min").count()
        liq_agg["liq_volume"] = df_liq["quantity"].resample("1min").sum()
        liq_agg["liq_usd"] = df_liq["usd_value"].resample("1min").sum()
        liq_agg["liq_velocity"] = liq_agg["liq_count"].diff()
        liq_agg["liq_acceleration"] = liq_agg["liq_velocity"].diff()
        liq_agg["buy_volume"] = df_liq[df_liq["side"] == "BUY"]["quantity"].resample("1min").sum()
        liq_agg["sell_volume"] = df_liq[df_liq["side"] == "SELL"]["quantity"].resample("1min").sum()
        liq_agg["imbalance"] = (liq_agg["buy_volume"] - liq_agg["sell_volume"]) / (
            liq_agg["buy_volume"] + liq_agg["sell_volume"] + 1e-8
        )
        liq_agg["whale_ratio"] = df_liq["is_whale"].resample("1min").mean()
        liq_agg["usd_ma_3"] = liq_agg["liq_usd"].rolling(3).mean()
        liq_agg["imbalance_ma_3"] = liq_agg["imbalance"].rolling(3).mean()

    # === TRADES ===
    df_trade = pd.DataFrame(list(tick_collection.find({
        "source_type": "trade",
        "timestamp": {"$gte": start_ts, "$lt": end_ts}
    })))

    if df_trade.empty:
        raise ValueError("❌ Không có dữ liệu trade.")

    df_trade["timestamp"] = pd.to_datetime(df_trade["timestamp"])
    df_trade["price"] = df_trade["data"].apply(lambda x: float(x.get("price", 0)))
    df_trade["quantity"] = df_trade["data"].apply(lambda x: float(x.get("quantity", 0)))
    df_trade = df_trade.set_index("timestamp").sort_index()

    trade_agg = pd.DataFrame()
    trade_agg["avg_price"] = (df_trade["price"] * df_trade["quantity"]).resample("1min").sum() / df_trade["quantity"].resample("1min").sum()
    trade_agg["total_volume"] = df_trade["quantity"].resample("1min").sum()
    trade_agg["price_std"] = df_trade["price"].resample("1min").std()
    trade_agg["price_diff"] = df_trade["price"].resample("1min").apply(lambda x: x.iloc[-1] - x.iloc[0] if len(x) > 1 else 0)
    trade_agg["trade_count"] = df_trade["price"].resample("1min").count()

    # === MERGE & SCALE ===
    final_df = trade_agg.join(liq_agg, how="left").dropna().reset_index()
    scaler = MinMaxScaler()
    scaled = scaler.fit_transform(final_df.drop(columns=["timestamp"]))
    final_df_scaled = pd.DataFrame(scaled, columns=final_df.columns[1:])
    final_df_scaled["timestamp"] = final_df["timestamp"].values
    final_df_scaled = final_df_scaled[["timestamp"] + final_df_scaled.columns[:-1].tolist()]

    return final_df_scaled


# === Test standalone
if __name__ == "__main__":
    df = build_features_from_mongo(
        start_date="2025-06-20",
        end_date="2025-06-21",
        use_latest=False
    )
    print(df.head())
