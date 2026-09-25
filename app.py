from datetime import datetime, timedelta
import os
import time
from fyers_apiv3 import fyersModel
import pandas as pd
import streamlit as st

CLIENT_ID = "7VPVG6SDK8-100"

st.set_page_config(page_title="Nifty Scanner", layout="centered")
st.title("📈 Nifty 50 Smart Engine")


def check_profile(access_token):
    try:
        fyers = fyersModel.FyersModel(
            client_id=CLIENT_ID, is_async=False, token=access_token, log_path=""
        )
        profile = fyers.get_profile()
        if profile.get("s") == "ok":
            return profile.get("data", {}).get("name", "User")
        return None
    except Exception:
        return None


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

        if res.get("s") == "ok" and len(res.get("candles", [])) > 0:
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
    user_name = check_profile(token)
    if user_name:
        st.success(f"✅ Token Active! Welcome, {user_name}")

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

                    st.caption(
                        f"Last Updated: {datetime.now().strftime('%I:%M:%S %p')}"
                    )
                else:
                    st.info(
                        "ℹ️ Token Valid Hai! Par abhi Market Off Hai (Live Data 9:15 AM par shuru hoga)."
                    )
            time.sleep(10)
    else:
        st.error(
            "❌ Token Expire Ho Gaya Hai. GitHub Actions se Naya Token Run Karo."
        )
else:
    st.error("❌ fyers_token.txt File Nahi Mili.")
