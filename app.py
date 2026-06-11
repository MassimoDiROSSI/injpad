from flask import Flask, request, jsonify, make_response
import requests
import os

app = Flask(__name__)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route("/")
def index():
    return "ING Challenge API - Working"

@app.route("/get-challenge", methods=["POST", "GET", "OPTIONS"])
def get_challenge():
    if request.method == "OPTIONS":
        return make_response("", 200)
    
    if request.method == "GET":
        username = request.args.get("username", "pioach3167")
    else:
        data = request.get_json() or {}
        username = data.get("username", "pioach3167")
    
    # Step 1: First GET to establish session
    session = requests.Session()
    
    try:
        # Get the login page first (to get cookies)
        get_resp = session.get(
            "https://login.ingbank.pl/",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7"
            },
            timeout=15,
            allow_redirects=True
        )
        
        # Step 2: Now POST with the session cookies
        payload = {
            "token": "6Pq8RVwBnXJJdbUbggoVtiRSr8VAPaCN",
            "trace": "",
            "data": {
                "factor": "LOGIN",
                "ref": "07acbd40-ce2d-4d6d-a8e8-7530e5a1a847",
                "credentials": username
            },
            "locale": "PL"
        }
        
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
            "Origin": "https://login.ingbank.pl",
            "Referer": "https://login.ingbank.pl/",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        resp = session.post(
            "https://login.ingbank.pl/oauth2/oauth2confirm",
            json=payload,
            headers=headers,
            timeout=15
        )
        
        data = resp.json()
        
        # Return full response for debugging
        return jsonify({
            "success": data.get("status") == "OK",
            "mask": data.get("data", {}).get("challenge", {}).get("mask") if data.get("status") == "OK" else None,
            "key": data.get("data", {}).get("challenge", {}).get("key") if data.get("status") == "OK" else None,
            "salt": data.get("data", {}).get("challenge", {}).get("salt") if data.get("status") == "OK" else None,
            "ref": data.get("data", {}).get("ref") if data.get("status") == "OK" else None,
            "error": data.get("msg") if data.get("status") != "OK" else None,
            "raw": data,
            "http_status": resp.status_code,
            "cookies": dict(session.cookies)
        })
        
    except Exception as e:
        import traceback
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
