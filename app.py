import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import time
import os
from fyers_apiv3 import fyersModel

CLIENT_ID = "7VPVG6SDK8-100"

st.set_page_config(page_title="A+ Sniper Engine", layout="wide")
st.title("🎯 Nifty 50 A+ Sniper State Engine")

# 1. AUTO LOGIN FIX: Direct fyers_token.txt se read karna
def get_token_from_file():
    try:
        if os.path.exists("fyers_token.txt"):
            with open("fyers_token.txt", "r") as f:
                return f.read().strip()
        return None
    except Exception as e:
        return None

auto_token = get_token_from_file()

st.sidebar.header("🔑 Fyers Setup")
st.sidebar.markdown("✅ Auto-Login Active via GitHub Actions")

if auto_token:
    st.session_state['fyers_token'] = auto_token
else:
    st.sidebar.error("⚠️ Token file missing. Manual mode active:")
    manual_token = st.sidebar.text_input("Enter Fyers Access Token", type="password")
    if manual_token:
        st.session_state['fyers_token'] = manual_token

# 2. VWAP & PDVWAP Engine
def calculate_vwap_and_pdvwap(df):
    df['date'] = pd.to_datetime(df['timestamp'], unit='s').dt.date
    dates = df['date'].unique()
    
    if len(dates) < 2:
        return None, None, None # Required min 2 days data for PDVWAP
        
    prev_date = dates[-2]
    curr_date = dates[-1]
    
    # Typical Price logic
    df["typical_price"] = (df["high"] + df["low"] + df["close"]) / 3
    df["cum_vol_price"] = (df["typical_price"] * df["volume"])
    
    # Calculate PDVWAP (Previous Day)
    prev_df = df[df['date'] == prev_date].copy()
    if prev_df["volume"].sum() > 0:
        pdvwap = prev_df["cum_vol_price"].sum() / prev_df["volume"].sum()
    else:
        pdvwap = prev_df["typical_price"].mean()
        
    # Calculate Current VWAP
    curr_df = df[df['date'] == curr_date].copy()
    if curr_df["volume"].sum() > 0:
        curr_df["cum_vol_price_cumsum"] = curr_df["cum_vol_price"].cumsum()
        curr_df["cum_vol_cumsum"] = curr_df["volume"].cumsum()
        curr_df["vwap"] = curr_df["cum_vol_price_cumsum"] / curr_df["cum_vol_cumsum"]
        vwap = curr_df["vwap"].iloc[-1]
    else:
        vwap = curr_df["typical_price"].expanding().mean().iloc[-1]
        
    ltp = curr_df["close"].iloc[-1]
    return ltp, vwap, pdvwap

def get_fyers_data(access_token, symbol):
    try:
        fyers = fyersModel.FyersModel(client_id=CLIENT_ID, is_async=False, token=access_token, log_path="")
        today = datetime.now()
        past = today - timedelta(days=5) # Include weekends buffer
        
        data_payload = {
            "symbol": symbol,
            "resolution": "1", 
            "date_format": "1",
            "range_from": past.strftime("%Y-%m-%d"), 
            "range_to": today.strftime("%Y-%m-%d"), 
            "cont_flag": "1"
        }
        return fyers.history(data=data_payload)
    except Exception as e:
        return {"s": "error", "message": str(e)}

# 3. Execution Engine
if 'fyers_token' in st.session_state and st.session_state['fyers_token']:
    placeholder = st.empty()
    
    while True:
        # Step 1: Spot Logic Check
        res = get_fyers_data(st.session_state['fyers_token'], "NSE:NIFTY50-INDEX")
        
        with placeholder.container():
            if res.get("s") == "ok" and "candles" in res and len(res["candles"]) > 0:
                df = pd.DataFrame(res["candles"], columns=["timestamp", "open", "high", "low", "close", "volume"])
                ltp, vwap, pdvwap = calculate_vwap_and_pdvwap(df)
                
                if ltp is not None:
                    st.success("✅ Dashboard Connected & Authenticated Automatically")
                    
                    # Applying your A+ Logic
                    bias = "SIDEWAYS / NO TRADE"
                    color = "⚪"
                    
                    if ltp > pdvwap and ltp > vwap:
                        bias = "A+ BULLISH BIAS (Focus CE Buyer)"
                        color = "🟢"
                    elif ltp < pdvwap and ltp < vwap:
                        bias = "A+ BEARISH BIAS (Focus PE Buyer)"
                        color = "🔴"
                    elif ltp > pdvwap and ltp < vwap:
                        bias = "Old Bullish / Intraday Bearish (Choppy)"
                        color = "🟡"
                    elif ltp < pdvwap and ltp > vwap:
                        bias = "Old Bearish / Intraday Bullish (Choppy)"
                        color = "🟡"
                        
                    st.subheader(f"{color} Nifty Spot Status: {bias}")
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Nifty Spot LTP", f"₹ {ltp:.2f}")
                    c2.metric("Intraday VWAP", f"₹ {vwap:.2f}")
                    c3.metric("Previous Day VWAP (PDVWAP)", f"₹ {pdvwap:.2f}")
                    
                    st.markdown("---")
                    st.info("💡 Next Update Module: Code spot LTP ko nearest ATM par round karega aur CE/PE symbols ki similar calculations trigger karega.")
                    st.caption(f"Last Fetched: {datetime.now().strftime('%I:%M:%S %p')}")
            else:
                st.error(f"❌ API Error or Token Expired: {res}")
        
        time.sleep(10)
else:
    st.warning("⚠️ Waiting for token... Please ensure fyers_token.txt is updated.")
