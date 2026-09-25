import streamlit as st
from fyers_apiv3 import fyersModel
import pandas as pd
from datetime import datetime
import time
import pyotp
import requests
import base64
import os
from urllib.parse import urlparse, parse_qs

# ==========================================
# 1. CREDENTIALS
# ==========================================
FY_ID = "XS39623"
PIN = "2112"
TOTP_KEY = "NKFQBHN5K4RSNOM5LZP4NW7AJ23KSBAN"
CLIENT_ID = "7VPVG6SDK8-100"
SECRET_KEY = "FWPRTCV2S2"
REDIRECT_URI = "https://127.0.0.1"

# ==========================================
# 2. BULLETPROOF AUTO-LOGIN ENGINE
# ==========================================
def cloud_auto_login():
    try:
        ses = requests.Session()
        ses.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        
        # Step A: OTP Request
        res1 = ses.post("https://api-t2.fyers.in/vagator/v2/send_login_otp_v2", 
                       json={"fy_id": base64.b64encode(f"{FY_ID}".encode()).decode(), "app_id": "2"})
        if res1.status_code != 200: return f"Fyers Blocked Streamlit IP (HTTP {res1.status_code})"
        
        r1 = res1.json()
        if r1.get("s") != "ok": return f"Step 1 Failed: {r1}"
        
        # Step B: TOTP Verification
        clean_key = TOTP_KEY.replace(" ", "").strip().upper()
        totp = pyotp.TOTP(clean_key).now()
        r2 = ses.post("https://api-t2.fyers.in/vagator/v2/verify_otp", 
                       json={"request_key": r1["request_key"], "otp": totp}).json()
        if r2.get("s") != "ok": return f"Step 2 (TOTP) Failed: {r2}"
        
        # Step C: PIN Verification
        r3 = ses.post("https://api-t2.fyers.in/vagator/v2/verify_pin_v2", 
                       json={"request_key": r2["request_key"], "identity_type": "pin", 
                             "identifier": base64.b64encode(f"{PIN}".encode()).decode()}).json()
        if r3.get("s") != "ok": return f"Step 3 (PIN) Failed: {r3}"
        token = r3["data"]["access_token"]
        
        # Step D: Auth Code
        auth_req = {"fyers_id": FY_ID, "app_id": CLIENT_ID[:-4], "redirect_uri": REDIRECT_URI, 
                    "appType": "100", "code_challenge": "", "state": "None", "scope": "", 
                    "nonce": "", "response_type": "code", "create_cookie": True}
        ses.headers.update({"authorization": f"Bearer {token}"})
        r4 = ses.post("https://api.fyers.in/api/v2/generate-authcode", json=auth_req).json()
        if "auth_code" not in r4: return f"Step 4 (Auth) Failed: {r4}"
        auth_code = parse_qs(urlparse(r4["auth_code"]).query)['auth_code'][0]
        
        # Step E: Final Token
        session = fyersModel.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, 
                                          redirect_uri=REDIRECT_URI, response_type="code", grant_type="authorization_code")
        session.set_token(auth_code)
        final = session.generate_token()
        if final.get("s") != "ok": return f"Step 5 (Final Token) Failed: {final}"
        
        return final['access_token']
    except Exception as e:
        return f"Code Error: {e}"

# ==========================================
# 3. FETCH DATA FUNCTION
# ==========================================
def get_fyers_data(access_token):
    try:
        fyers = fyersModel.FyersModel(client_id=CLIENT_ID, is_async=False, token=access_token, log_path="")
        today_date = datetime.now().strftime("%Y-%m-%d")
        data_payload = {
            "symbol": "NSE:NIFTY50-INDEX", "resolution": "1", "date_format": "1",
            "range_from": today_date, "range_to": today_date, "cont_flag": "1"
        }
        res = fyers.history(data=data_payload)
        
        if res.get('s') == 'ok' and len(res['candles']) > 0:
            df = pd.DataFrame(res['candles'], columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['typical_price'] = (df['high'] + df['low'] + df['close']) / 3
            if df['volume'].sum() > 0:
                df['cum_vol_price'] = (df['typical_price'] * df['volume']).cumsum()
                df['cum_vol'] = df['volume'].cumsum()
                df['current_volume'] = df['cum_vol_price'] / df['cum_vol']
            else:
                df['current_volume'] = df['typical_price'].expanding().mean()
            return df
        return None
    except:
        return None

# ==========================================
# 4. STREAMLIT UI DASHBOARD
# ==========================================
st.set_page_config(page_title="Nifty Scanner", layout="centered")
st.title("📈 Nifty 50 Smart Engine")

# Smart Session Management (Replaces bug-prone cache)
if "access_token" not in st.session_state:
    st.session_state.access_token = None
    st.session_state.login_msg = ""

if not st.session_state.access_token:
    status = cloud_auto_login()
    
    # Agar status lamba token hai (yani successful)
    if status and not status.startswith("Fyers") and not status.startswith("Step") and not status.startswith("Code"):
        st.session_state.access_token = status
        st.session_state.login_msg = "✅ Cloud Auto-Login Successful!"
    else:
        # Fallback Backup - Aapki uploaded token file use karega
        if os.path.exists("fyers_token_2.txt"):
            with open("fyers_token_2.txt", "r") as f:
                st.session_state.access_token = f.read().strip()
            st.session_state.login_msg = f"⚠️ Auto-Login Blocked by Fyers. But BACKUP TOKEN is Active!"
        else:
            st.session_state.login_msg = f"❌ Login Failed Details: {status}"

# Render UI Loop
if st.session_state.access_token:
    placeholder = st.empty()
    while True:
        df = get_fyers_data(st.session_state.access_token)
        with placeholder.container():
            if "⚠️" in st.session_state.login_msg:
                st.warning(st.session_state.login_msg)
            else:
                st.success(st.session_state.login_msg)
                
            if df is not None:
                ltp = df['close'].iloc[-1]
                cv = df['current_volume'].iloc[-1]
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Live Price", f"₹ {ltp:.2f}")
                col2.metric("Current Vol", f"₹ {cv:.2f}")
                col3.metric("Previous Vol", "Coming Soon")
                col4.metric("Difference", f"{(ltp - cv):.2f}")
                
                st.caption(f"Last Updated: {datetime.now().strftime('%I:%M:%S %p')}")
            else:
                st.error("Data missing or Market Closed (Token ho sakta hai expire ho gaya ho).")
        time.sleep(10)
else:
    st.error(st.session_state.login_msg)
