import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="NSE Accumulation Scanner", layout="wide")

st.title("🧠 NSE Pre-Breakout Accumulation Scanner")

# --------------------------------------------------
# LOAD CSV
# --------------------------------------------------

def load_csv():
    for file in os.listdir():
        if file.endswith(".csv"):
            return pd.read_csv(file)
    return None

data = load_csv()

if data is None:
    st.error("No CSV file found.")
    st.stop()

data.columns = data.columns.str.strip().str.upper()

required_cols = [
    "SECURITY",
    "NET_TRDQTY",
    "CLOSE_PRICE",
    "HI_52_WK",
    "LOW_PRICE",
    "HIGH_PRICE",
    "TRADES"
]

for col in required_cols:
    if col not in data.columns:
        st.error("Required columns not found in CSV.")
        st.stop()

# Convert numeric safely
for col in required_cols[1:]:
    data[col] = pd.to_numeric(data[col], errors="coerce")

data = data.dropna()

# --------------------------------------------------
# USER FILTER SETTINGS
# --------------------------------------------------

min_volume = st.slider("Minimum Volume (Lakhs)", 1, 500, 20)
max_distance = st.slider("Max % Below 52W High (Accumulation Zone)", 2, 15, 6)
min_trades = st.slider("Minimum Trades", 1000, 500000, 10000)

# --------------------------------------------------
# ACCUMULATION CONDITIONS
# --------------------------------------------------

# Volume filter
filtered = data[data["NET_TRDQTY"] > min_volume * 100000]

# Distance from 52W high
filtered["DIST_52W_%"] = (
    (filtered["HI_52_WK"] - filtered["CLOSE_PRICE"])
    / filtered["HI_52_WK"]
) * 100

filtered = filtered[
    (filtered["DIST_52W_%"] > 0.5) &   # Not already breakout
    (filtered["DIST_52W_%"] <= max_distance)
]

# Trade participation filter
filtered = filtered[filtered["TRADES"] > min_trades]

# Tight range detection (accumulation behavior)
filtered["DAY_RANGE_%"] = (
    (filtered["HIGH_PRICE"] - filtered["LOW_PRICE"])
    / filtered["CLOSE_PRICE"]
) * 100

filtered = filtered[filtered["DAY_RANGE_%"] < 5]  # Controlled move

# --------------------------------------------------
# ACCUMULATION SCORE
# --------------------------------------------------

def calculate_score(row):
    volume_score = min(row["NET_TRDQTY"] / 10000000, 1)
    trade_score = min(row["TRADES"] / 100000, 1)
    proximity_score = 1 - min(row["DIST_52W_%"] / max_distance, 1)

    return round(
        (volume_score * 0.4 +
         trade_score * 0.3 +
         proximity_score * 0.3) * 100, 2
    )

filtered["ACCUMULATION_%"] = filtered.apply(calculate_score, axis=1)

filtered = filtered.sort_values(by="ACCUMULATION_%", ascending=False)

# --------------------------------------------------
# DISPLAY
# --------------------------------------------------

st.subheader(f"📊 Found {len(filtered)} Accumulation Candidates")

if len(filtered) > 0:
    display_cols = [
        "SECURITY",
        "CLOSE_PRICE",
        "HI_52_WK",
        "DIST_52W_%",
        "NET_TRDQTY",
        "TRADES",
        "ACCUMULATION_%"
    ]

    st.dataframe(filtered[display_cols].reset_index(drop=True),
                 use_container_width=True)
else:
    st.warning("No accumulation setups found.")

# --------------------------------------------------
# DOWNLOAD
# --------------------------------------------------

if len(filtered) > 0:
    csv = filtered.to_csv(index=False).encode("utf-8")
    st.download_button(
        "⬇ Download Results",
        csv,
        "accumulation_results.csv",
        "text/csv"
    )