import streamlit as st
import pandas as pd
import pymongo
from datetime import datetime
import matplotlib.pyplot as plt

MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "trading_logs"
COLLECTION_NAME = "rewards"

@st.cache_data(show_spinner=False)
@st.cache_data(show_spinner=False)
def load_data():
    client = pymongo.MongoClient(MONGO_URI)
    collection = client[DB_NAME][COLLECTION_NAME]
    data = list(collection.find())
    df = pd.DataFrame(data)

    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values('timestamp')
    else:
        st.warning("'timestamp' field is missing in MongoDB data.")
        df['timestamp'] = pd.NaT  # tạo cột rỗng để tránh lỗi sau

    return df

st.title("PPO Trading Reward Dashboard")

try:
    df = load_data()

    if df.empty:
        st.warning("No data available in MongoDB.")
    else:
        st.subheader("Reward Over Time")
        st.line_chart(df.set_index('timestamp')['reward'])

        st.subheader("Action Distribution")
        action_counts = df['action'].value_counts().sort_index()
        st.bar_chart(action_counts)

        st.subheader("Latency (ms)")
        st.line_chart(df.set_index('timestamp')['latency_ms'])

except Exception as e:
    st.error(f"Failed to load or render dashboard: {e}")
