import os
import time
from datetime import datetime
import pandas as pd
import streamlit as st
from fyers_apiv3 import fyersModel

CLIENT_ID = "7VPVG6SDK8-100"

st.set_page_config(page_title="Nifty Scanner", layout="centered")
st.title("📈 Nifty 50 Smart Engine")

def get_fyers_data(access_token):
    try:
        fyers = fyersModel.FyersModel(client_id=CLIENT_ID, is_async=False, token=access_token, log_path="")
        today_date = datetime.now().strftime("%Y-%m-%d")
        data_payload = {
            "symbol": "NSE:NIFTY50-INDEX",
            "resolution": "1",
            "date_format": "1",
            "range_from": today_date,
            "range_to": today_date,
            "cont_flag": "1"
        }
        return fyers.history(data=data_payload)
    except Exception as e:
        return {"s": "error", "message": str(e)}

# Token file read karo
token = None
if os.path.exists("fyers_token.txt"):
    with open("fyers_token.txt", "r") as f:
        token = f.read().strip()

if token:
    placeholder = st.empty()
    while True:
        res = get_fyers_data(token)
        
        with placeholder.container():
            # Agar data successfully aa gaya
            if res.get("s") == "ok" and "candles" in res and len(res["candles"]) > 0:
                df = pd.DataFrame(res["candles"], columns=["timestamp", "open", "high", "low", "close", "volume"])
                df["typical_price"] = (df["high"] + df["low"] + df["close"]) / 3
                
                if df["volume"].sum() > 0:
                    df["cum_vol_price"] = (df["typical_price"] * df["volume"]).cumsum()
                    df["cum_vol"] = df["volume"].cumsum()
                    df["current_volume"] = df["cum_vol_price"] / df["cum_vol"]
                else:
                    df["current_volume"] = df["typical_price"].expanding().mean()
                    
                ltp = df["close"].iloc[-1]
                cv = df["current_volume"].iloc[-1]

                st.success("✅ Fyers Live Data Connected!")
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Live Price", f"₹ {ltp:.2f}")
                col2.metric("Current Vol", f"₹ {cv:.2f}")
                col3.metric("Previous Vol", "6th Condition..")
                col4.metric("Difference", f"{(ltp - cv):.2f}")
                st.caption(f"Last Updated: {datetime.now().strftime('%I:%M:%S %p')}")
                
            # Agar Fyers ne API block ki ya token sach me expire hua
            elif res.get("s") == "error":
                st.error(f"❌ Token Ya Data Error: {res.get('message')}")
                st.info("💡 GitHub Actions me ja kar ek baar 'Run workflow' daba do.")
                
            # Agar market band ho
            else:
                st.warning("ℹ️ Market Data Fetch Nahi Ho Raha (Market band ho sakti hai).")
        
        time.sleep(10)
else:
    st.error("❌ fyers_token.txt File Nahi Mili. Pehle GitHub Actions chalayein.")
