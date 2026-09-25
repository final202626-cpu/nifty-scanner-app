import streamlit as st
from fyers_apiv3 import fyersModel
import pandas as pd
from datetime import datetime
import time
import pyotp
import requests
import base64
from urllib.parse import urlparse, parse_qs

# ==========================================
# 1. CREDENTIALS (YAHAN APNI DETAILS DAALO)
# ==========================================
FY_ID = "XS39623"
PIN = "2112"
TOTP_KEY = "NKFQBHN5K4RSNOM5LZP4NW7AJ23KSBAN"    # Bina kisi space ke daalna
CLIENT_ID = "7VPVG6SDK8-100"
SECRET_KEY = "FWPRTCV2S2"
REDIRECT_URI = "https://127.0.0.1"

# ==========================================
# 2. CLOUD AUTO-LOGIN ENGINE (NO MAGAJMARI)
# ==========================================
@st.cache_data(ttl=36000) # Token ko 10 ghante tak cloud memory me save rakhega
def get_fyers_token():
    try:
        ses = requests.Session()
        ses.headers.update({"User-Agent": "Mozilla/5.0"})
        
        # A. OTP Request
        res1 = ses.post("https://api-t2.fyers.in/vagator/v2/send_login_otp_v2", 
                       json={"fy_id": base64.b64encode(f"{FY_ID}".encode()).decode(), "app_id": "2"}).json()
        
        # B. Verify TOTP (Cloud servers have perfect time)
        clean_key = TOTP_KEY.replace(" ", "").strip().upper()
        totp = pyotp.TOTP(clean_key).now()
        res2 = ses.post("https://api-t2.fyers.in/vagator/v2/verify_otp", 
                       json={"request_key": res1["request_key"], "otp": totp}).json()
        
        # C. Verify PIN
        res3 = ses.post("https://api-t2.fyers.in/vagator/v2/verify_pin_v2", 
                       json={"request_key": res2["request_key"], "identity_type": "pin", 
                             "identifier": base64.b64encode(f"{PIN}".encode()).decode()}).json()
        token = res3["data"]["access_token"]
        
        # D. Get Auth Code
        auth_req = {"fyers_id": FY_ID, "app_id": CLIENT_ID[:-4], "redirect_uri": REDIRECT_URI, 
                    "appType": "100", "code_challenge": "", "state": "None", "scope": "", 
                    "nonce": "", "response_type": "code", "create_cookie": True}
        ses.headers.update({"authorization": f"Bearer {token}"})
        res4 = ses.post("https://api.fyers.in/api/v2/generate-authcode", json=auth_req).json()
        auth_code = parse_qs(urlparse(res4["auth_code"]).query)['auth_code'][0]
        
        # E. Generate Final Token
        session = fyersModel.SessionModel(client_id=CLIENT_ID, secret_key=SECRET_KEY, 
                                          redirect_uri=REDIRECT_URI, response_type="code", grant_type="authorization_code")
        session.set_token(auth_code)
        return session.generate_token()['access_token']
    except Exception as e:
        return None

# ==========================================
# 3. FETCH NIFTY DATA
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

access_token = get_fyers_token()

if access_token:
    placeholder = st.empty()
    while True:
        df = get_fyers_data(access_token)
        with placeholder.container():
            if df is not None:
                ltp = df['close'].iloc[-1]
                cv = df['current_volume'].iloc[-1]
                
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Live Price", f"₹ {ltp:.2f}")
                col2.metric("Current Vol", f"₹ {cv:.2f}")
                col3.metric("Previous Vol", "Coming Soon")
                col4.metric("Difference", f"{(ltp - cv):.2f}")
                
                st.success("✅ Cloud Auto-Login Successful! Ready for Sniper Logic.")
                st.caption(f"Last Updated: {datetime.now().strftime('%I:%M:%S %p')}")
            else:
                st.warning("Market is closed or data fetching delayed.")
        time.sleep(10)
else:
    st.error("Login Failed. Please check Credentials in code.")
