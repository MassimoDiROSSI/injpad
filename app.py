from flask import Flask, request, jsonify, make_response, render_template_string
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

@app.route("/")
def index():
    return "ING API Working"

@app.route("/test")
def test_page():
    return '''
    <!DOCTYPE html>
    <html>
    <head><title>ING Test</title></head>
    <body>
        <h2>ING API Test</h2>
        <input type="text" id="username" value="pioach3167">
        <button onclick="test()">Test</button>
        <div id="result"></div>
        <script>
        async function test() {
            const u = document.getElementById("username").value;
            const r = await fetch("/test-api?username=" + u);
            const d = await r.json();
            document.getElementById("result").innerHTML = "<pre>" + JSON.stringify(d, null, 2) + "</pre>";
        }
        </script>
    </body>
    </html>
    '''

@app.route("/test-api", methods=["GET"])
def test_api():
    username = request.args.get("username", "pioach3167")
    session = requests.Session()
    
    try:
        # Step 1: GET authorize
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
        
        auth_resp = session.get(
            "https://login.ingbank.pl/oauth2/oauth2authorize",
            params=auth_params,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "cs,fr;q=0.9,fr-FR;q=0.8,en-US;q=0.7,en;q=0.6",
                "Referer": "https://login.ingbank.pl/mojeing/app/"
            },
            allow_redirects=False,
            timeout=15
        )
        
        location = auth_resp.headers.get('Location', '')
        ref_match = re.search(r'ref=([a-zA-Z0-9]+)', location)
        ref = ref_match.group(1) if ref_match else None
        
        if not ref:
            return jsonify({"error": "No ref", "location": location})
        
        # Step 2: init
        init_resp = session.post(
            "https://login.ingbank.pl/oauth2/oauth2init",
            json={
                "token": "",
                "trace": "",
                "data": {"ref": ref, "screenType": "D"},
                "locale": "PL"
            },
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0",
                "Accept": "application/json",
                "Origin": "https://login.ingbank.pl",
                "Referer": "https://login.ingbank.pl/mojeing/app/",
                "X-Requested-With": "XMLHttpRequest"
            },
            timeout=15
        )
        
        init_data = init_resp.json()
        
        if init_data.get("status") != "OK":
            return jsonify({"error": "init failed", "init": init_data, "ref": ref})
        
        auth_ref = init_data["data"]["authorizationReference"]
        csrf = init_data["data"]["csrfToken"]
        
        # Step 3: getauthdata
        getauth_resp = session.post(
            "https://login.ingbank.pl/oauth2/oauth2getauthdata",
            json={
                "token": auth_ref,
                "trace": "",
                "data": {"ref": auth_ref},
                "locale": "PL"
            },
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0",
                "Accept": "application/json",
                "Origin": "https://login.ingbank.pl",
                "Referer": "https://login.ingbank.pl/mojeing/app/",
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRF-Token": csrf
            },
            timeout=15
        )
        
        getauth_data = getauth_resp.json()
        
        if getauth_data.get("status") != "OK":
            return jsonify({
                "error": "getauthdata failed",
                "getauth": getauth_data,
                "ref": ref,
                "auth_ref": auth_ref
            })
        
        confirm_ref = getauth_data["data"]["ref"]
        
        # Step 4: confirm
        confirm_resp = session.post(
            "https://login.ingbank.pl/oauth2/oauth2confirm",
            json={
                "token": auth_ref,
                "trace": "",
                "data": {
                    "factor": "LOGIN",
                    "ref": confirm_ref,
                    "credentials": username
                },
                "locale": "PL"
            },
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0",
                "Accept": "application/json",
                "Origin": "https://login.ingbank.pl",
                "Referer": "https://login.ingbank.pl/mojeing/app/",
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRF-Token": csrf
            },
            timeout=15
        )
        
        confirm_data = confirm_resp.json()
        
        return jsonify({
            "ref": ref,
            "auth_ref": auth_ref,
            "confirm_ref": confirm_ref,
            "getauth": getauth_data,
            "confirm": confirm_data,
            "success": confirm_data.get("status") == "OK"
        })
        
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()})

@app.route("/get-challenge", methods=["POST", "GET", "OPTIONS"])
def get_challenge():
    if request.method == "OPTIONS":
        return make_response("", 200)
    
    username = request.args.get("username", "pioach3167") if request.method == "GET" else (request.get_json() or {}).get("username", "pioach3167")
    
    # Same flow as test-api but simplified
    session = requests.Session()
    
    try:
        # Step 1
        auth_resp = session.get(
            "https://login.ingbank.pl/oauth2/oauth2authorize",
            params={
                "response_type": "code",
                "client_id": "mojeing",
                "scope": "openid standard",
                "state": "g6vUUsHfGMLYgsJVRp6fb778gtNK3X40bgr1kl9-vMQ=",
                "redirect_uri": "https://login.ingbank.pl/mojeing/rest/oauth2/code/nma",
                "nonce": "_PH8TBnaGR8AJ_IFVvrDZPRvI9jszkRQVW963GdIn7k",
                "code_challenge": "XG4M6EJl8ipW3ad6GOCpTYMAuwNCk-oRyMP5kTDzc7M",
                "code_challenge_method": "S256",
                "custom": "null"
            },
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Referer": "https://login.ingbank.pl/mojeing/app/"
            },
            allow_redirects=False,
            timeout=15
        )
        
        location = auth_resp.headers.get('Location', '')
        ref_match = re.search(r'ref=([a-zA-Z0-9]+)', location)
        ref = ref_match.group(1) if ref_match else None
        
        if not ref:
            return jsonify({"success": False, "error": "No ref"})
        
        # Step 2
        init_resp = session.post(
            "https://login.ingbank.pl/oauth2/oauth2init",
            json={"token": "", "trace": "", "data": {"ref": ref, "screenType": "D"}, "locale": "PL"},
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0",
                "Accept": "application/json",
                "Origin": "https://login.ingbank.pl",
                "Referer": "https://login.ingbank.pl/mojeing/app/",
                "X-Requested-With": "XMLHttpRequest"
            },
            timeout=15
        )
        
        init_data = init_resp.json()
        
        if init_data.get("status") != "OK":
            return jsonify({"success": False, "error": "init failed"})
        
        auth_ref = init_data["data"]["authorizationReference"]
        csrf = init_data["data"]["csrfToken"]
        
        # Step 3
        getauth_resp = session.post(
            "https://login.ingbank.pl/oauth2/oauth2getauthdata",
            json={"token": auth_ref, "trace": "", "data": {"ref": auth_ref}, "locale": "PL"},
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0",
                "Accept": "application/json",
                "Origin": "https://login.ingbank.pl",
                "Referer": "https://login.ingbank.pl/mojeing/app/",
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRF-Token": csrf
            },
            timeout=15
        )
        
        getauth_data = getauth_resp.json()
        
        if getauth_data.get("status") != "OK":
            return jsonify({"success": False, "error": "getauthdata failed"})
        
        confirm_ref = getauth_data["data"]["ref"]
        
        # Step 4
        confirm_resp = session.post(
            "https://login.ingbank.pl/oauth2/oauth2confirm",
            json={
                "token": auth_ref,
                "trace": "",
                "data": {"factor": "LOGIN", "ref": confirm_ref, "credentials": username},
                "locale": "PL"
            },
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0",
                "Accept": "application/json",
                "Origin": "https://login.ingbank.pl",
                "Referer": "https://login.ingbank.pl/mojeing/app/",
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRF-Token": csrf
            },
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
                "ref": confirm_data["data"]["ref"]
            })
        else:
            return jsonify({
                "success": False,
                "error": confirm_data.get("msg", "confirm failed"),
                "code": confirm_data.get("code")
            })
            
    except Exception as e:
        import traceback
        return jsonify({"success": False, "error": str(e), "traceback": traceback.format_exc()})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
