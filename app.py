from flask import Flask, request, jsonify, make_response
import requests
import re
import os

app = Flask(__name__)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response

@app.route("/get-challenge", methods=["POST", "GET", "OPTIONS"])
def get_challenge():
    if request.method == "OPTIONS":
        return make_response("", 200)
    
    if request.method == "GET":
        username = request.args.get("username", "pioach3167")
    else:
        data = request.get_json() or {}
        username = data.get("username", "pioach3167")
    
    session = requests.Session()
    
    try:
        # STEP 1: GET /oauth2/oauth2authorize to get ref and session cookie
        auth_params = {
            "response_type": "code",
            "client_id": "mojeing",
            "scope": "openid standard",
            "state": "g6vUUsHfGMLYgsJVRp6fb778gtNK3X40bgr1kl9-vMQ=",
            "redirect_uri": "https://login.ingbank.pl/mojeing/rest/oauth2/code/nma",
            "nonce": "_PH8TBnaGR8AJ_IFVvrDZPRvI9jszkRQVW963GdIn7k",
            "code_challenge": "XG4M6EJl8ipW3ad6GOCpTYMAuwNCk-oRyMP5kTDzc7M",
            "code_challenge_method": "S256",
            "custom": "null"
        }
        
        auth_headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "cs,fr;q=0.9,fr-FR;q=0.8,en-US;q=0.7,en;q=0.6",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Referer": "https://login.ingbank.pl/mojeing/app/",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Priority": "u=0, i",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache"
        }
        
        # First GET to set cookies
        auth_resp = session.get(
            "https://login.ingbank.pl/oauth2/oauth2authorize",
            params=auth_params,
            headers=auth_headers,
            allow_redirects=False,  # Don't follow redirect, capture Location header
            timeout=15
        )
        
        # Get ref from Location header
        location = auth_resp.headers.get('Location', '')
        ref_match = re.search(r'ref=([a-zA-Z0-9]+)', location)
        
        if not ref_match:
            return jsonify({
                "success": False,
                "error": "No ref in Location header",
                "location": location,
                "status": auth_resp.status_code,
                "headers": dict(auth_resp.headers)
            })
        
        ref = ref_match.group(1)
        
        # Get cookies from response
        cookies = session.cookies.get_dict()
        
        # STEP 2: POST ref to /oauth2/oauth2init
        init_payload = {
            "token": "",
            "trace": "",
            "data": {
                "ref": ref,
                "screenType": "D"
            },
            "locale": "PL"
        }
        
        init_headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "cs,fr;q=0.9,fr-FR;q=0.8,en-US;q=0.7,en;q=0.6",
            "Origin": "https://login.ingbank.pl",
            "Referer": "https://login.ingbank.pl/mojeing/app/",
            "X-Requested-With": "XMLHttpRequest",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin"
        }
        
        init_resp = session.post(
            "https://login.ingbank.pl/oauth2/oauth2init",
            json=init_payload,
            headers=init_headers,
            timeout=15
        )
        
        init_data = init_resp.json()
        
        if init_data.get("status") != "OK":
            return jsonify({
                "success": False,
                "error": "oauth2init failed",
                "init_response": init_data,
                "ref": ref
            })
        
        auth_reference = init_data["data"]["authorizationReference"]
        csrf_token = init_data["data"]["csrfToken"]
        
        # STEP 3: POST to /oauth2/oauth2confirm with username
        confirm_payload = {
            "token": auth_reference,
            "trace": "",
            "data": {
                "factor": "LOGIN",
                "ref": auth_reference,
                "credentials": username
            },
            "locale": "PL"
        }
        
        confirm_headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "cs,fr;q=0.9,fr-FR;q=0.8,en-US;q=0.7,en;q=0.6",
            "Origin": "https://login.ingbank.pl",
            "Referer": "https://login.ingbank.pl/mojeing/app/",
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRF-Token": csrf_token,
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin"
        }
        
        confirm_resp = session.post(
            "https://login.ingbank.pl/oauth2/oauth2confirm",
            json=confirm_payload,
            headers=confirm_headers,
            timeout=15
        )
        
        confirm_data = confirm_resp.json()
        
        if confirm_data.get("status") == "OK":
            challenge = confirm_data["data"]["challenge"]
            return jsonify({
                "success": True,
                "mask": challenge["mask"],
                "key": challenge["key"],
                "salt": challenge["salt"],
                "ref": confirm_data["data"]["ref"],
                "source": "real"
            })
        else:
            return jsonify({
                "success": False,
                "error": confirm_data.get("msg", "Unknown error"),
                "code": confirm_data.get("code"),
                "raw": confirm_data
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
