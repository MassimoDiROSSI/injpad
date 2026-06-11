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

@app.route("/")
def index():
    return "ING API Working - <a href='/test'>Go to test page</a>"

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

@app.route("/test-api")
def test_api():
    username = request.args.get("username", "pioach3167")
    session = requests.Session()
    
    try:
        # Step 1: GET authorize
        auth_resp = session.get(
            "https://login.ingbank.pl/oauth2/oauth2authorize",
            params={
                "response_type": "code",
                "client_id": "mojeing",
                "scope": "openid standard",
                "state": "test",
                "redirect_uri": "https://login.ingbank.pl/mojeing/rest/oauth2/code/nma",
                "nonce": "test",
                "code_challenge": "test",
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
            return jsonify({"error": "No ref", "location": location})
        
        # Step 2: init
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
            return jsonify({"error": "init failed", "init": init_data})
        
        auth_ref = init_data["data"]["authorizationReference"]
        csrf = init_data["data"]["csrfToken"]
        
        # Step 3: getauthdata
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
            return jsonify({"error": "getauthdata failed", "getauth": getauth_data})
        
        confirm_ref = getauth_data["data"]["ref"]
        
        # Step 4: confirm
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
        
        return jsonify({
            "success": confirm_data.get("status") == "OK",
            "ref": ref,
            "auth_ref": auth_ref,
            "confirm_ref": confirm_ref,
            "confirm": confirm_data
        })
        
    except Exception as e:
        import traceback
        return jsonify({"error": str(e), "traceback": traceback.format_exc()})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
