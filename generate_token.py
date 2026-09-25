import base64
from urllib.parse import parse_qs, urlparse
from fyers_apiv3 import fyersModel
import pyotp
import requests

FY_ID = "XS39623"
PIN = "2112"
TOTP_KEY = "NKFQBHN5K4RSNOM5LZP4NW7AJ23KSBAN"
CLIENT_ID = "7VPVG6SDK8-100"
SECRET_KEY = "FWPRTCV2S2"
REDIRECT_URI = "https://127.0.0.1"


def generate():
    try:
        ses = requests.Session()
        ses.headers.update(
            {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )

        # Step 1: OTP
        res1 = ses.post(
            "https://api-t2.fyers.in/vagator/v2/send_login_otp_v2",
            json={
                "fy_id": base64.b64encode(f"{FY_ID}".encode()).decode(),
                "app_id": "2",
            },
        ).json()
        if res1.get("s") != "ok":
            print("Step 1 Error:", res1)
            return

        # Step 2: TOTP
        totp = pyotp.TOTP(TOTP_KEY).now()
        res2 = ses.post(
            "https://api-t2.fyers.in/vagator/v2/verify_otp",
            json={"request_key": res1["request_key"], "otp": totp},
        ).json()
        if res2.get("s") != "ok":
            print("Step 2 Error:", res2)
            return

        # Step 3: PIN
        res3 = ses.post(
            "https://api-t2.fyers.in/vagator/v2/verify_pin_v2",
            json={
                "request_key": res2["request_key"],
                "identity_type": "pin",
                "identifier": base64.b64encode(f"{PIN}".encode()).decode(),
            },
        ).json()
        if res3.get("s") != "ok":
            print("Step 3 Error:", res3)
            return

        # Step 4: Auth Code
        token = res3["data"]["access_token"]
        auth_req = {
            "fyers_id": FY_ID,
            "app_id": CLIENT_ID[:-4],
            "redirect_uri": REDIRECT_URI,
            "appType": "100",
            "code_challenge": "",
            "state": "None",
            "scope": "",
            "nonce": "",
            "response_type": "code",
            "create_cookie": True,
        }
        ses.headers.update({"authorization": f"Bearer {token}"})
        res4 = ses.post(
            "https://api.fyers.in/api/v2/generate-authcode", json=auth_req
        ).json()
        auth_code = parse_qs(urlparse(res4["auth_code"]).query)["auth_code"][0]

        # Step 5: Final Token
        session = fyersModel.SessionModel(
            client_id=CLIENT_ID,
            secret_key=SECRET_KEY,
            redirect_uri=REDIRECT_URI,
            response_type="code",
            grant_type="authorization_code",
        )
        session.set_token(auth_code)
        final_token = session.generate_token()["access_token"]

        with open("fyers_token.txt", "w") as f:
            f.write(final_token)
        print("✅ SUCCESS: Token fyers_token.txt me save ho gaya hai!")
    except Exception as e:
        print("❌ ERROR:", e)


if __name__ == "__main__":
    generate()
