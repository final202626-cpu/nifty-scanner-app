import streamlit as st
from fyers_apiv3 import fyersModel
import pandas as pd
from datetime import datetime
import time
import pyotp
import requests
from urllib.parse import urlparse, parse_qs
import base64

# ==========================================
# 1. CREDENTIALS (YAHAN APNI DETAILS DAALO)
# ==========================================
FY_ID = "XS39623"          # Example: "XS12345"
PIN = "2112"         # Example: "1234"
TOTP_KEY = "O3I2V3Z5YJDVU2DPEIMZP5DRCVU3C2FX"    # Example: "JBSWY3DPEHPK3PXP"
CLIENT_ID = "7VPVG6SDK8-100"              # App ID
SECRET_KEY = "FWPRTCV2S2"                 # Secret Key
REDIRECT_URI = "https://127.0.0.1"

# ==========================================
# 2. AUTO-LOGIN ENGINE (BACKGROUND)
# ==========================================
def auto_login_fyers():
    try:
        ses = requests.Session()
        
        # Step A: Send OTP Request
        res = ses.post("https://api-t2.fyers.in/vagator/v2/send_login_otp_v2", 
                       json={"fy_id": base64.b64encode(f"{FY_ID}".encode()).decode(), "app_id": "2"}).json()
        request_key = res.get("request_key")
        
        # Step B: Verify TOTP
        totp = pyotp.TOTP(TOTP_KEY).now()
        res = ses.post("https://api-t2.fyers.in/vagator/v2/verify_otp", 
                       json={"request_key": request_key, "otp": totp}).json()
        request_key = res.get("request_key")
        
        # Step C: Verify PIN
        res = ses.post("https://api-t2.fyers.in/vagator/v2/verify_pin_v2", 
                       json={"request_key": request_key, "identity_type": "pin", 
                             "identifier": base64.b64encode(f"{PIN}".encode()).decode()}).json()
        token = res["data"]["access_token"]
        
        # Step D: Get Auth Code
        auth_req = {
            "fyers_id": FY_ID, "app_id": CLIENT_ID[:-4], "redirect_uri": REDIRECT_URI, 
            "appType": "100", "code_challenge": "", "state": "None", "scope": "", 
            "nonce": "", "response_type": "code", "create_cookie": True
        }
        ses.headers.update({"authorization": f"Bearer {token}"})
        res = ses.post("https://api.fyers.in/api/v2/generate-authcode", json=auth_req).json()
        auth_code = parse_qs(urlparse(res["auth_code"]).query)['auth_code'][0]
        
        # Step E: Generate Final API Token
        session = fyersModel.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, 
                                          redirect_uri=REDIRECT_URI, response_type="code", 
                                          grant_type="authorization_code")
        session.set_token(auth_code)
        token_response = session.generate_token()
        
        if token_response.get('s') == 'ok':
            final_token = token_response['access_token']
            with open("fyers_token.txt", "w") as f:
                f.write(final_token)
            return final_token
        return None
    except Exception as e:
        return None

# ==========================================
# 3. DATA FETCHING (SMART RETRY)
# ==========================================
def get_fyers_data(retry=True):
    try:
        # File se token read karne ki koshish
        try:
            with open("fyers_token.txt", "r") as f:
                access_token = f.read().strip()
        except FileNotFoundError:
            access_token = auto_login_fyers() # File nahi mili to Auto-Login
            
        if not access_token:
            return None
            
        fyers = fyersModel.FyersModel(client_id=CLIENT_ID, is_async=False, token=access_token, log_path="")
        today_date = datetime.now().strftime("%Y-%m-%d")
        data_payload = {
            "symbol": "NSE:NIFTY50-INDEX", "resolution": "1", "date_format": "1",
            "range_from": today_date, "range_to": today_date, "cont_flag": "1"
        }
        
        res = fyers.history(data=data_payload)
        
        # Agar Token expire ho gaya hai, to error aayega. Hum dobara login karke retry karenge.
        if res.get('s') == 'error' and retry:
            auto_login_fyers()
            return get_fyers_data(retry=False)
            
        if res.get('s') == 'ok' and len(res['candles']) > 0:
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

# ==========================================
# 4. STREAMLIT UI DASHBOARD
# ==========================================
st.set_page_config(page_title="Nifty Scanner", layout="centered")
st.title("📈 Nifty 50 Smart Engine")
st.markdown("100% Automated - Live Fyers Data")

placeholder = st.empty()

while True:
    df = get_fyers_data()
    
    with placeholder.container():
        if df is not None:
            ltp = df['close'].iloc[-1]
            current_vol_val = df['current_volume'].iloc[-1]
            
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("LTP (Live Price)", f"₹ {ltp:.2f}")
            col2.metric("Current Volume", f"₹ {current_vol_val:.2f}")
            col3.metric("Previous Volume", "Calculating..")
            col4.metric("Difference", f"{(ltp - current_vol_val):.2f} pts")
            
            current_time = datetime.now().strftime('%I:%M:%S %p')
            st.success("✅ Auto-Login Active & Data Fetching Smoothly.")
            st.caption(f"Last Updated: {current_time}")
        else:
            st.error("Market Band Hai Ya Credential Galat Hain.")
    
    time.sleep(10)
