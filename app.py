import streamlit as st
from fyers_apiv3 import fyersModel
import pandas as pd
from datetime import datetime
import time

# -----------------------------------------
# 1. FYERS SETUP & DATA FETCH FUNCTION
# -----------------------------------------
CLIENT_ID = "7VPVG6SDK8-100"  # Aapka App ID

def get_fyers_data():
    try:
        with open("fyers_token.txt", "r") as f:
            access_token = f.read().strip()
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
        
        res = fyers.history(data=data_payload)
        if res['s'] == 'ok' and len(res['candles']) > 0:
            df = pd.DataFrame(res['candles'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
            total_vol = df['volume'].sum()
            
            if total_vol > 0:
                df['cum_vol_price'] = (df['typical_price'] * df['volume']).cumsum()
                df['cum_vol'] = df['volume'].cumsum()
                df['current_volume'] = df['cum_vol_price'] / df['cum_vol']
            else:
                df['current_volume'] = df['typical_price'].expanding().mean()
            return df
        return None
    except Exception as e:
        return None

# -----------------------------------------
# 2. 6-CONDITION STATE ENGINE
# -----------------------------------------
def get_market_state(price, current_vol):
    diff_points = price - current_vol
    diff_pct = (diff_points / current_vol) * 100

    if diff_pct >= 0.25:
        return "🚀 STRONG BULLISH", "Price Current Volume se kafi upar hai. Buying pressure strong hai.", "success"
    elif 0 <= diff_pct < 0.25:
        return "🟢 WEAK BULLISH", "Price Current Volume ke upar hai par nazdeek hai. Support le raha hai.", "success"
    elif -0.10 <= diff_pct < 0:
        return "⚠️ BREAKDOWN ALERT", "Price ne Current Volume ko just neeche cross kiya hai. Savdhaan rahein.", "warning"
    elif 0 <= diff_pct < 0.10:
         return "⚡ BREAKOUT ALERT", "Price ne Current Volume ko just upar cross kiya hai. Momentum ban sakta hai.", "warning"
    elif -0.25 < diff_pct < -0.10:
        return "🔴 WEAK BEARISH", "Price Current Volume ke neeche hai. Selling shuru ho chuki hai.", "error"
    else: # diff_pct <= -0.25
        return "🩸 STRONG BEARISH", "Price Current Volume se kafi neeche hai. Heavy selling pressure.", "error"

# -----------------------------------------
# 3. STREAMLIT UI DASHBOARD
# -----------------------------------------
st.set_page_config(page_title="Nifty Scanner", layout="centered")
st.title("📈 Nifty 50 State Engine")
st.markdown("Live Fyers API Data & Volume Analysis")

# Placeholder for auto-refresh
placeholder = st.empty()

# 10 second refresh loop
while True:
    df = get_fyers_data()
    
    with placeholder.container():
        if df is not None:
            ltp = df['close'].iloc[-1]
            current_vol_val = df['current_volume'].iloc[-1]
            
            # State Engine Analysis
            state_name, state_desc, alert_type = get_market_state(ltp, current_vol_val)
            
            # Metrics Row (4 columns)
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("LTP (Live Price)", f"₹ {ltp:.2f}")
            col2.metric("Current Volume", f"₹ {current_vol_val:.2f}")
            col3.metric("Previous Volume", "Calculating..") # Logic will be added in next phase
            col4.metric("Difference", f"{(ltp - current_vol_val):.2f} pts")
            
            # State Engine Alert
            st.markdown("### Market State")
            if alert_type == "success":
                st.success(f"**{state_name}**: {state_desc}")
            elif alert_type == "error":
                st.error(f"**{state_name}**: {state_desc}")
            else:
                st.warning(f"**{state_name}**: {state_desc}")
            
            # AM/PM Time Format
            current_time = datetime.now().strftime('%I:%M:%S %p')
            st.caption(f"Last Updated: {current_time}")
        else:
            st.error("Data fetch nahi ho pa raha. Token check karein ya market band hai.")
    
    # 10 seconds wait before fetching again
    time.sleep(10)