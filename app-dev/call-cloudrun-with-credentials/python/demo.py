import google.auth
from google.auth.credentials import Credentials, Scoped

def get_creds(audience: str) -> Credentials:
    print(f"👉 Acquiring application default credentials (ADC)...")
    creds, _ = google.auth.default()
    if isinstance(creds, Scoped):
        print(f"👉 Setting up '{audience}' scope...")
        scopes = [audience] if creds.scopes is None else [audience] + list(creds.scopes)
        creds = creds.with_scopes(scopes)
    return creds

def get_id_token(audience: str) -> str:

    creds = get_creds(audience)

    if hasattr(creds, "id_token") and creds.id_token:
        print(f"🎉 Id token is acquired from ADC.")
        return creds.id_token
    else:
        from google.oauth2 import id_token
        from google.auth.transport.requests import Request
        from google.auth.exceptions import RefreshError
        
        auth_req = Request()
        try:
            print(f"👉 Refreshing credentials to acquire ID token...")
            creds.refresh(auth_req)
        except RefreshError as e:
            if not "No access token in response" in str(e):
                raise
        if hasattr(creds, "id_token") and creds.id_token:
            print(f"🎉 Id token is acquired after refresh.")
            return creds.id_token
        elif audience:
            print(f"👉 Fetching ID token from metadata server...")
            return id_token.fetch_id_token(auth_req, audience)
        else:
            raise ValueError("Cannot obtain ID token without a specified audience.")

def main():
    import argparse
    import requests

    # Set up argument parser and read URL argument
    parser = argparse.ArgumentParser(description="Demo script for argument parsing.")
    parser.add_argument('--url', type=str, required=True, help='Cloud Run service URL')
    args = parser.parse_args()

    # Acquire credentials
    token = get_id_token(args.url)

    print(f"🎉 ID token is ready for use in authenticated call to Cloud Run.")
    # Send authenticated request to the Cloud Run service
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    try:
        print(f"👉 Calling Cloud Run service endpoint {args.url} with ID token...")
        response = requests.get(args.url, headers=headers)
        response.raise_for_status() # Raises an HTTPError for bad responses (4xx or 5xx)
    
        print(f"🎉 --- Response Content (First 200 chars) ---\n")
        print(response.text[:200] + "...")
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        print(f"❌ --- Response Content (First 200 chars) ---\n")
        print(response.text[:200] + "...")
    except requests.exceptions.RequestException as e:
        print(f"❌ HTTP Error: {e}")
        print(f"❌ --- Response Content (First 200 chars) ---\n")
        print(response.text[:200] + "...")
    
if __name__ == "__main__":
    main()
