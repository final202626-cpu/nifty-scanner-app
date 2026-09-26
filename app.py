import streamlit as st
import pandas as pd
from datetime import datetime
import time
from fyers_apiv3 import fyersModel

CLIENT_ID = "7VPVG6SDK8-100"

st.set_page_config(page_title="A+ Sniper Engine", layout="wide")
st.title("🎯 Nifty 50 A+ Sniper State Engine")

# ==========================================
# 1. NO GITHUB NEEDED - MANUAL TOKEN INPUT
# ==========================================
st.sidebar.header("🔑 Fyers Login")
st.sidebar.markdown("GitHub errors se bachne ke liye aaj ka token yahan paste karein:")
manual_token = st.sidebar.text_input("Enter Fyers Access Token", type="password")

if manual_token:
    st.session_state['fyers_token'] = manual_token

# ==========================================
# 2. FETCH LIVE DATA
# ==========================================
def get_fyers_data(access_token):
    try:
        fyers = fyersModel.FyersModel(client_id=CLIENT_ID, is_async=False, token=access_token, log_path="")
        today_date = datetime.now().strftime("%Y-%m-%d")
        data_payload = {
            "symbol": "NSE:NIFTY50-INDEX", "resolution": "1", "date_format": "1",
            "range_from": today_date, "range_to": today_date, "cont_flag": "1"
        }
        return fyers.history(data=data_payload)
    except Exception as e:
        return {"s": "error", "message": str(e)}

# ==========================================
# 3. SNIPER LOGIC & UI DASHBOARD
# ==========================================
if 'fyers_token' in st.session_state and st.session_state['fyers_token']:
    placeholder = st.empty()
    while True:
        res = get_fyers_data(st.session_state['fyers_token'])
        
        with placeholder.container():
            if res.get("s") == "ok" and "candles" in res and len(res["candles"]) > 0:
                df = pd.DataFrame(res["candles"], columns=["timestamp", "open", "high", "low", "close", "volume"])
                
                # VWAP Calculation (Exact Math)
                df["typical_price"] = (df["high"] + df["low"] + df["close"]) / 3
                if df["volume"].sum() > 0:
                    df["cum_vol_price"] = (df["typical_price"] * df["volume"]).cumsum()
                    df["cum_vol"] = df["volume"].cumsum()
                    df["vwap"] = df["cum_vol_price"] / df["cum_vol"]
                else:
                    df["vwap"] = df["typical_price"].expanding().mean()
                
                ltp = df["close"].iloc[-1]
                vwap = df["vwap"].iloc[-1]
                
                st.success("✅ Live Data Running - Emotionless Trading Active")
                
                # State Engine Dashboard
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Nifty Live Spot", f"₹ {ltp:.2f}")
                c2.metric("VWAP Level", f"₹ {vwap:.2f}")
                
                diff = ltp - vwap
                c3.metric("LTP vs VWAP", f"{diff:.2f}")
                
                # Condition 1: CE / PE Focus (No Manual Errors)
                if diff > 0:
                    c4.metric("Market State", "🟢 BULLISH (Focus CE)")
                else:
                    c4.metric("Market State", "🔴 BEARISH (Focus PE)")
                    
                st.caption(f"Last Updated: {datetime.now().strftime('%I:%M:%S %p')}")
                
            else:
                st.error("❌ Token invalid hai ya market closed hai.")
        
        time.sleep(10) # 10 seconds refresh
else:
    st.info("👈 Left panel me aaj ka Fyers token daalo taaki system chalu ho sake.")
