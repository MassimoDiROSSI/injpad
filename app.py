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

TEST_HTML = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>ING API Test</title>
    <style>
        body { font-family: Arial; padding: 40px; background: #f5f5f5; }
        .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; }
        input { width: 100%; padding: 12px; margin: 10px 0; border: 1px solid #ddd; border-radius: 4px; }
        button { padding: 12px 30px; background: #ff6b00; color: white; border: none; border-radius: 4px; cursor: pointer; }
        .step { margin: 20px 0; padding: 15px; border-radius: 4px; }
        .step1 { background: #e3f2fd; }
        .step2 { background: #fff3e0; }
        .step3 { background: #e8f5e9; }
        .step4 { background: #f3e5f5; }
        .error { background: #ffebee; color: #c62828; }
        pre { background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto; font-size: 12px; }
        h3 { margin-top: 0; }
    </style>
</head>
<body>
<div class="container">
    <h2>ING API Test</h2>
    <input type="text" id="username" value="pioach3167" placeholder="Username">
    <button onclick="test()">Test API Flow</button>
    <div id="result"></div>
</div>
<script>
async function test() {
    const username = document.getElementById("username").value;
    const result = document.getElementById("result");
    result.innerHTML = "Loading...";
    
    try {
        const res = await fetch("/test-api?username=" + encodeURIComponent(username));
        const data = await res.json();
        
        let html = "";
        
        if (data.step1) {
            html += `<div class="step step1">
                <h3>Step 1: GET /oauth2/oauth2authorize</h3>
                <p>Status: ${data.step1.status}</p>
                <p>Ref: ${data.step1.ref}</p>
            </div>`;
        }
        
        if (data.step2) {
            html += `<div class="step step2">
                <h3>Step 2: POST /oauth2/oauth2init</h3>
                <p>AuthRef: ${data.step2.auth_ref}</p>
            </div>`;
        }
        
        if (data.step3) {
            html += `<div class="step step3">
                <h3>Step 3: POST /oauth2/oauth2getauthdata</h3>
                <p>ConfirmRef: ${data.step3.confirm_ref}</p>
                <p>Response:</p>
                <pre>${JSON.stringify(data.step3.response, null, 2)}</pre>
            </div>`;
        }
        
        if (data.step4) {
            html += `<div class="step step4">
                <h3>Step 4: POST /oauth2/oauth2confirm</h3>
                <p>Response:</p>
                <pre>${JSON.stringify(data.step4.response, null, 2)}</pre>
            </div>`;
        }
        
        if (data.error) {
            html += `<div class="step error">
                <h3>Error</h3>
                <p>${data.error}</p>
            </div>`;
        }
        
        result.innerHTML = html;
        
    } catch (err) {
        result.innerHTML = `<div class="step error">Fetch error: ${err.message}</div>`;
    }
}
</script>
</body>
</html>
'''

@app.route("/")
def index():
    return "ING API - Visit /test to debug"

@app.route("/test")
def test_page():
    return render_template_string(TEST_HTML)

@app.route("/test-api", methods=["GET"])
def test_api():
    username = request.args.get("username", "pioach3167")
    session = requests.Session()
    
    result = {}
    
    try:
        # STEP 1: GET /oauth2/oauth2authorize
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
        
        auth_resp = session.get(
            "https://login.ingbank.pl/oauth2/oauth2authorize",
            params=auth_params,
            headers=auth_headers,
            allow_redirects=False,
            timeout=15
        )
        
        location = auth_resp.headers.get('Location', '')
        ref_match = re.search(r'ref=([a-zA-Z0-9]+)', location)
        ref = ref_match.group(1) if ref_match else None
        
        result["step1"] = {
            "status": auth_resp.status_code,
            "ref": ref
        }
        
        if not ref:
            result["error"] = "No ref found"
            return jsonify(result)
        
        # STEP 2: POST to /oauth2/oauth2init
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
            result["error"] = "oauth2init failed"
            result["init_response"] = init_data
            return jsonify(result)
        
        auth_reference = init_data["data"]["authorizationReference"]
        csrf_token = init_data["data"]["csrfToken"]
        
        result["step2"] = {
            "auth_ref": auth_reference,
            "csrf": csrf_token[:10] + "..."
        }
        
        # STEP 3: NEW! POST to /oauth2/oauth2getauthdata
        getauth_payload = {
            "token": auth_reference,
            "trace": "",
            "data": {
                "ref": auth_reference  # use auth_reference here
            },
            "locale": "PL"
        }
        
        getauth_headers = {
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
        
        getauth_resp = session.post(
            "https://login.ingbank.pl/oauth2/oauth2getauthdata",
            json=getauth_payload,
            headers=getauth_headers,
            timeout=15
        )
        
        getauth_data = getauth_resp.json()
        
        if getauth_data.get("status") != "OK":
            result["error"] = "oauth2getauthdata failed"
            result["getauth_response"] = getauth_data
            return jsonify(result)
        
        # Get the confirm ref from getauthdata response
        confirm_ref = getauth_data["data"]["ref"]
        
        result["step3"] = {
            "confirm_ref": confirm_ref,
            "response": getauth_data
        }
        
        # STEP 4: POST to /oauth2/oauth2confirm with confirm_ref
        confirm_payload = {
            "token": auth_reference,
            "trace": "",
            "data": {
                "factor": "LOGIN",
                "ref": confirm_ref,  # <-- Use confirm_ref from getauthdata!
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
        
        result["step4"] = {
            "response": confirm_data
        }
        
        if confirm_data.get("status") == "OK":
            result["success"] = True
            result["mask"] = confirm_data["data"]["challenge"]["mask"]
        else:
            result["error"] = confirm_data.get("msg", "confirm failed")
        
        return jsonify(result)
        
    except Exception as e:
        import traceback
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()
        return jsonify(result)

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
        # Same 4-step flow but return simplified response
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
        
        auth_resp = session.get(
            "https://login.ingbank.pl/oauth2/oauth2authorize",
            params=auth_params,
            headers=auth_headers,
            allow_redirects=False,
            timeout=15
        )
        
        location = auth_resp.headers.get('Location', '')
        ref_match = re.search(r'ref=([a-zA-Z0-9]+)', location)
        ref = ref_match.group(1) if ref_match else None
        
        if not ref:
            return jsonify({"success": False, "error": "No ref"})
        
        # Step 2: init
        init_payload = {
            "token": "",
            "trace": "",
            "data": {"ref": ref, "screenType": "D"},
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
            return jsonify({"success": False, "error": "init failed"})
        
        auth_reference = init_data["data"]["authorizationReference"]
        csrf_token = init_data["data"]["csrfToken"]
        
        # Step 3: getauthdata
        getauth_payload = {
            "token": auth_reference,
            "trace": "",
            "data": {"ref": auth_reference},
            "locale": "PL"
        }
        
        getauth_headers = {
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
        
        getauth_resp = session.post(
            "https://login.ingbank.pl/oauth2/oauth2getauthdata",
            json=getauth_payload,
            headers=getauth_headers,
            timeout=15
        )
        
        getauth_data = getauth_resp.json()
        
        if getauth_data.get("status") != "OK":
            return jsonify({"success": False, "error": "getauthdata failed", "getauth": getauth_data})
        
        confirm_ref = getauth_data["data"]["ref"]
        
        # Step 4: confirm
        confirm_payload = {
            "token": auth_reference,
            "trace": "",
            "data": {
                "factor": "LOGIN",
                "ref": confirm_ref,
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
