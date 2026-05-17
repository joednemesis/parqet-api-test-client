import os
import hashlib
import base64
import requests
import secrets
import json
from flask import Flask, redirect, request

app = Flask(__name__)

# --- Please provide your Client ID from the Parqet integration. ---
CLIENT_ID = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" 
# --- Connection settings and API resource URLs. ---
REDIRECT_URI = "http://localhost:3000/callback"
AUTH_URL = "https://connect.parqet.com/oauth2/authorize"
TOKEN_URL = "https://connect.parqet.com/oauth2/token"
USER_INFO_URL = "https://connect.parqet.com/user"
PORTFOLIO_API_URL = "https://connect.parqet.com/portfolios"
PORTFOLIO_API_URL_2 = "/activities"

# Generates PKCE (Proof Key for Code Exchange) verifier and challenge for secure OAuth2 authentication.
def generate_pkce():
    verifier = secrets.token_urlsafe(32)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
    return verifier, challenge

# Root route that displays the landing page with the Client ID and a link to start the login process.
# Root route that displays the landing page with the Client ID and a link to start the login process.
@app.route('/')
def index():    
    return f"""
    <body style="font-family: sans-serif; padding: 20px; line-height: 1.6; background-color: #f8f9fa;">
        
        <h1 style="color: #333;">Parqet API Connector</h1>

        <div style="background: #e7f3ff; border: 1px solid #007bff; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <h3 style="margin-top:0;">1. Full Data Analysis Pipeline</h3>
            <p>This tool performs a multi-step analysis of your Parqet account:</p>
            <ul style="margin-bottom: 15px;">
                <li><b>Identity Check:</b> Verifies user status and API privileges.</li>
                <li><b>Portfolio Overview:</b> Lists all connected portfolios and metadata.</li>
                <li><b>Activity Deep-Dive:</b> Fetches and analyzes recent transactions.</li>
            </ul>
            <p><b>Client ID:</b> <code>{CLIENT_ID}</code></p>
        </div>

        <div style="padding: 10px;">
            <a href="/login" style="
                background-color: #28a745; 
                color: white; 
                padding: 15px 30px; 
                text-decoration: none; 
                border-radius: 5px; 
                font-weight: bold; 
                font-size: 1.1em;
                display: inline-block;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                Authorize & Start Analysis
            </a>
            <p style="margin-top: 15px; color: #6c757d; font-size: 0.9em;">
                Securely connects via OAuth2 (S256 PKCE). No credentials are stored locally.
            </p>
        </div>
    </body>
    """

# Starts the OAuth2 flow by generating security keys, saving the verifier, and redirecting the user to Parqet.
@app.route('/login')
def login():
    verifier, challenge = generate_pkce()
    with open("verifier.txt", "w") as f:
        f.write(verifier)
    
    params = {
        'response_type': 'code',
        'client_id': CLIENT_ID,
        'redirect_uri': REDIRECT_URI,
        'scope': 'portfolio:read',
        'audience': 'api.parqet.com',
        'state': secrets.token_urlsafe(16),
        'code_challenge': challenge,
        'code_challenge_method': 'S256'
    }
    return redirect(requests.Request('GET', AUTH_URL, params=params).prepare().url)

@app.route('/callback')
def callback():
    auth_code = request.args.get('code')
    if not os.path.exists("verifier.txt"): return "Verifier fehlt", 400
    with open("verifier.txt", "r") as f: verifier = f.read()

    # Phase 1: Exchange the authorization code and verifier for an access token.
    payload = {
        'grant_type': 'authorization_code',
        'code': auth_code,
        'redirect_uri': REDIRECT_URI,
        'client_id': CLIENT_ID,
        'code_verifier': verifier
    }

    token_res = requests.post(
        TOKEN_URL, 
        data=payload,
        headers={'Content-Type': 'application/x-www-form-urlencoded'}
    ).json()
    
    access_token = token_res.get('access_token')
    if not access_token: return f"Token-Error: {token_res}"

    # Phase 2: Set up authorization headers using the Bearer token and browser-like masking.
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "*/*",
    }
    # Phase 3: Fetch user information, portfolio list, and specific activity data from the API.
    # 1st connect: User Status and Privileges
    user_res = requests.get(USER_INFO_URL, headers=headers)
    # 2nd connect: Portfolio Overview
    portfolio_res = requests.get(PORTFOLIO_API_URL, headers=headers)
    #Deserializing the JSON response to a dictionary
    portfolio_data = portfolio_res.json()
    #Access the dictionary (the .get method works here)
    if portfolio_data.get('items'):
        first_portfolio_id = portfolio_data['items'][0]['id']
    else:
        first_portfolio_id = None
        print("No portfolios found.")
    # 3rd connect: fetch activities from portfolio
    single_res = requests.get(f"{PORTFOLIO_API_URL}/{first_portfolio_id}{PORTFOLIO_API_URL_2}", headers=headers)
 
    # Phase 4: Render the results into a structured HTML dashboard for analysis.
    return f"""
    <body style="font-family: sans-serif; padding: 20px; line-height: 1.6;">
        <h2>Result Analysis (Confidential Client)</h2>
        
        <div style="background: #e7f3ff; border: 1px solid #007bff; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <h3 style="margin-top:0;">1. Identity Check: Verifies user status and API privileges.</h3>
            <p>Status: <b>{user_res.status_code}</b></p>
            <p>{USER_INFO_URL}</p>
            <pre style="background: white; padding: 10px; border: 1px solid #ccc; overflow-x: auto; white-space: pre-wrap;">
        {json.dumps(user_res.json(), indent=4) if user_res.status_code == 200 else user_res.text}
    </pre>
        </div>

        <div style="background: #fff3cd; border: 1px solid #dc3545; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
            <h3 style="margin-top:0;">2. Portfolio Overview: Lists all connected portfolios and metadata. </h3>
            <p>Listen-Status: <b>{portfolio_res.status_code}</b></p>
            <p>{PORTFOLIO_API_URL}</p>            
            <pre style="background: white; padding: 10px; border: 1px solid #ccc; overflow-x: auto; white-space: pre-wrap;">
        {json.dumps(portfolio_res.json(), indent=4) if portfolio_res.status_code == 200 else portfolio_res.text}
    </pre>
            
        </div>

        <div style="background: #f2fdf2; border: 1px solid #28a745; padding: 15px; border-radius: 8px;">
            <h3 style="margin-top:0;">3. Activity Deep-Dive: Fetches recent transactions. ({first_portfolio_id}) </h3>
            <p>Status: <b>{single_res.status_code}</b></p>            
            <p>{PORTFOLIO_API_URL}/{first_portfolio_id}{PORTFOLIO_API_URL_2}</p>
            <pre style="background: white; padding: 10px; border: 1px solid #ccc; overflow-x: auto; white-space: pre-wrap;">
        {json.dumps(single_res.json(), indent=4) if single_res.status_code == 200 else single_res.text}
        </div>

        <hr>
        <p><small>Token-Typ: {token_res.get('token_type')} | Expires in: {token_res.get('expires_in')}s</small></p>
        <a href="/">Neuer Versuch</a>
    </body>
    """

# Main entry point: starts the Flask development server on port 3000 with debug mode enabled.
if __name__ == '__main__':
    # Flask auf Port 3000 starten
    app.run(port=3000, debug=True)
