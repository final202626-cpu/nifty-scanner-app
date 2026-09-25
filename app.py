from datetime import datetime
import os
import time
from fyers_apiv3 import fyersModel
import pandas as pd
import streamlit as st

CLIENT_ID = "7VPVG6SDK8-100"

st.set_page_config(page_title="Nifty Scanner", layout="centered")
st.title("📈 Nifty 50 Smart Engine")


def get_fyers_data(access_token):
    try:
        fyers = fyersModel.FyersModel(
            client_id=CLIENT_ID, is_async=False, token=access_token, log_path=""
        )
        today_date = datetime.now().strftime("%Y-%m-%d")
        data_payload = {
            "symbol": "NSE:NIFTY50-INDEX",
            "resolution": "1",
            "date_format": "1",
            "range_from": today_date,
            "range_to": today_date,
            "cont_flag": "1",
        }
        res = fyers.history(data=data_payload)

        if res.get("s") == "ok" and len(res["candles"]) > 0:
            df = pd.DataFrame(
                res["candles"],
                columns=[
                    "timestamp",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                ],
            )
            df["typical_price"] = (df["high"] + df["low"] + df["close"]) / 3
            if df["volume"].sum() > 0:
                df["cum_vol_price"] = (
                    df["typical_price"] * df["volume"]
                ).cumsum()
                df["cum_vol"] = df["volume"].cumsum()
                df["current_volume"] = df["cum_vol_price"] / df["cum_vol"]
            else:
                df["current_volume"] = df["typical_price"].expanding().mean()
            return df
        return None
    except Exception:
        return None


# Read Token File
token = None
if os.path.exists("fyers_token.txt"):
    with open("fyers_token.txt", "r") as f:
        token = f.read().strip()

if token:
    placeholder = st.empty()
    while True:
        df = get_fyers_data(token)
        with placeholder.container():
            if df is not None:
                ltp = df["close"].iloc[-1]
                cv = df["current_volume"].iloc[-1]

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Live Price", f"₹ {ltp:.2f}")
                col2.metric("Current Vol", f"₹ {cv:.2f}")
                col3.metric("Previous Vol", "Calculating..")
                col4.metric("Difference", f"{(ltp - cv):.2f}")

                st.success("✅ Fyers Live Feed Active!")
                st.caption(
                    f"Last Updated: {datetime.now().strftime('%I:%M:%S %p')}"
                )
            else:
                st.warning(
                    "Market Band Hai ya Aaj Ka Token Expire Ho Gaya Hai."
                )
        time.sleep(10)
else:
    st.error("fyers_token.txt File Nahi Mili.")
