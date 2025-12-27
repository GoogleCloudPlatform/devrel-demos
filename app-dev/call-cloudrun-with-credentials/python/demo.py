import argparse
import google.auth
from google.oauth2.service_account import Credentials
from google.auth import impersonated_credentials
from google.auth.transport.requests import Request
from google.oauth2 import id_token
import requests

def get_id_token(audience: str) -> str:

    creds, _ = google.auth.default()
    auth_req = Request()

    # Option D: Handle Impersonated Credentials
    if isinstance(creds, impersonated_credentials.Credentials):
        impersonated_creds = impersonated_credentials.Credentials(
            source_credentials=creds,
            target_principal=creds._target_principal,
            target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )        
        creds = impersonated_credentials.IDTokenCredentials(
            impersonated_creds,
            target_audience=audience,
            include_email=True
        )
        creds.refresh(auth_req)
        return creds.token

    # Option B: Handle User Credentials
    if hasattr(creds, "id_token") and creds.id_token:
        return creds.id_token
    creds.refresh(auth_req)
    if hasattr(creds, "id_token") and creds.id_token:
        return creds.id_token

    # Option A or C: Fetch from Metadata Server or Handle Service Account Credentials
    token = id_token.fetch_id_token(auth_req, audience)
    if token:
        return token

    raise ValueError("Cannot obtain ID token")

def main():
    parser = argparse.ArgumentParser(description="Cloud Run Auth Demo")
    parser.add_argument('--url', type=str, required=True, help='Cloud Run service URL')
    args = parser.parse_args()

    try:
        token = get_id_token(args.url)
    except Exception as e:
        print(f"❌ Authentication Failed: {e}")
        return

    print(f"🎉 ID token is ready for use.")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    
    try:
        print(f"👉 Calling Cloud Run service endpoint {args.url} ...")
        response = requests.get(args.url, headers=headers)
        
        if response.status_code == 200:
             print(f"🎉 --- Response Content (First 200 chars) ---\n")
        else:
             print(f"❌ HTTP Error: Status Code {response.status_code}")
             print(f"❌ --- Response Content (First 200 chars) ---\n")
             
        print(response.text[:200] + "...")
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Request Failed: {e}")

if __name__ == "__main__":
    main()