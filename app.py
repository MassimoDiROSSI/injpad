from flask import Flask, request, jsonify
import requests
import re
import os

app = Flask(__name__)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response

@app.route("/")
def index():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>ING Mask Grab</title>
        <meta charset="UTF-8">
    </head>
    <body style="font-family:Arial, sans-serif; padding:40px; background:#f5f5f5;">
        <div style="max-width:500px; margin:0 auto; background:white; padding:30px; border-radius:8px; box-shadow:0 2px 10px rgba(0,0,0,0.1);">
            <h2 style="color:#ff6200; margin-top:0;">ING Mask Grab</h2>
            <input type="text" id="username" placeholder="Enter username (e.g. malbuc2876)" 
                style="width:100%; padding:12px; margin:10px 0; border:1px solid #ddd; border-radius:4px; font-size:16px; box-sizing:border-box;">
            <button id="btn" onclick="getMask()" 
                style="width:100%; padding:12px; background:#ff6200; color:white; border:none; border-radius:4px; font-size:16px; cursor:pointer;">
                Get Mask
            </button>
            <div id="loading" style="display:none; margin-top:15px; color:#666; text-align:center;">Loading...</div>
            <div id="result" style="margin-top:20px; font-family:monospace; white-space:pre-wrap; word-break:break-all; background:#f8f8f8; padding:15px; border-radius:4px; border:1px solid #e0e0e0;"></div>
        </div>
        <script>
        async function getMask() {
            const u = document.getElementById("username").value.trim();
            const btn = document.getElementById("btn");
            const loading = document.getElementById("loading");
            const result = document.getElementById("result");

            if (!u) {
                result.innerHTML = "<span style=\'color:red\'>Error: Please enter a username</span>";
                return;
            }

            btn.disabled = true;
            btn.style.opacity = "0.6";
            loading.style.display = "block";
            result.innerHTML = "";

            try {
                const url = "/get-mask?username=" + encodeURIComponent(u);
                const r = await fetch(url, {
                    method: "GET",
                    headers: {
                        "Accept": "application/json"
                    }
                });

                if (!r.ok) {
                    throw new Error("HTTP " + r.status + ": " + r.statusText);
                }

                const d = await r.json();
                result.innerHTML = JSON.stringify(d, null, 2);

                if (d.success && d.mask) {
                    result.innerHTML += "\n\n--- MASK VISUAL ---\n";
                    result.innerHTML += "Position: " + Array.from({length: d.mask_length}, (_, i) => i.toString().padStart(2, "0")).join(" ") + "\n";
                    result.innerHTML += "Mask:     " + d.mask.split("").map(c => c === "*" ? "[*]" : " + ").join(" ") + "\n";
                    result.innerHTML += "Required positions: " + d.required_positions.join(", ") + "\n";
                }
            } catch(e) {
                result.innerHTML = "<span style=\'color:red\'>Error: " + e.message + "</span>";
                console.error(e);
            } finally {
                btn.disabled = false;
                btn.style.opacity = "1";
                loading.style.display = "none";
            }
        }

        // Allow Enter key to submit
        document.getElementById("username").addEventListener("keypress", function(e) {
            if (e.key === "Enter") getMask();
        });
        </script>
    </body>
    </html>
    """

@app.route("/get-mask")
def get_mask():
    username = request.args.get("username", "").strip()
    if not username:
        return jsonify({"error": "Username required"}), 400

    session = requests.Session()

    try:
        # Step 1: GET /mojeing/app/ to establish session
        app_resp = session.get(
            "https://login.ingbank.pl/mojeing/app/",
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "cs,fr;q=0.9,fr-FR;q=0.8,en-US;q=0.7,en;q=0.6",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1",
                "Upgrade-Insecure-Requests": "1",
                "Connection": "keep-alive",
                "Priority": "u=0, i"
            },
            timeout=15
        )

        # Step 2: GET authorize to get ref
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
                "Accept-Language": "cs,fr;q=0.9,fr-FR;q=0.8,en-US;q=0.7,en;q=0.6",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Referer": "https://login.ingbank.pl/mojeing/app/",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "same-origin",
                "Connection": "keep-alive"
            },
            allow_redirects=False,
            timeout=15
        )

        location = auth_resp.headers.get("Location", "")
        ref_match = re.search(r"ref=([a-zA-Z0-9]+)", location)
        ref = ref_match.group(1) if ref_match else None

        if not ref:
            return jsonify({
                "error": "No ref found in authorize redirect",
                "location": location,
                "status": auth_resp.status_code,
                "headers": dict(auth_resp.headers)
            }), 500

        # Step 3: POST init
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
                "Accept-Language": "cs,fr;q=0.9,fr-FR;q=0.8,en-US;q=0.7,en;q=0.6",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Origin": "https://login.ingbank.pl",
                "Referer": "https://login.ingbank.pl/mojeing/app/",
                "X-Requested-With": "XMLHttpRequest",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "Connection": "keep-alive"
            },
            timeout=15
        )

        init_data = init_resp.json()

        if init_data.get("status") != "OK":
            return jsonify({
                "error": "init failed",
                "init_response": init_data,
                "init_status": init_resp.status_code
            }), 500

        auth_ref = init_data["data"]["authorizationReference"]
        csrf = init_data["data"]["csrfToken"]

        # Step 4: POST getauthdata (token = CSRF, ref = auth_ref)
        getauth_resp = session.post(
            "https://login.ingbank.pl/oauth2/oauth2getauthdata",
            json={
                "token": csrf,
                "trace": "",
                "data": {"ref": auth_ref},
                "locale": "PL"
            },
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:151.0) Gecko/20100101 Firefox/151.0",
                "Accept": "application/json",
                "Accept-Language": "cs,fr;q=0.9,fr-FR;q=0.8,en-US;q=0.7,en;q=0.6",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Origin": "https://login.ingbank.pl",
                "Referer": "https://login.ingbank.pl/mojeing/app/",
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRF-Token": csrf,
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "Connection": "keep-alive"
            },
            timeout=15
        )

        getauth_data = getauth_resp.json()

        if getauth_data.get("status") != "OK":
            return jsonify({
                "error": "getauthdata failed",
                "getauth_response": getauth_data,
                "getauth_status": getauth_resp.status_code
            }), 500

        confirm_ref = getauth_data["data"]["ref"]

        # Step 5: POST confirm with username (token = CSRF, ref = confirm_ref, credentials = username)
        confirm_resp = session.post(
            "https://login.ingbank.pl/oauth2/oauth2confirm",
            json={
                "token": csrf,
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
                "Accept-Language": "cs,fr;q=0.9,fr-FR;q=0.8,en-US;q=0.7,en;q=0.6",
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Origin": "https://login.ingbank.pl",
                "Referer": "https://login.ingbank.pl/mojeing/app/",
                "X-Requested-With": "XMLHttpRequest",
                "X-CSRF-Token": csrf,
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "Connection": "keep-alive"
            },
            timeout=15
        )

        confirm_data = confirm_resp.json()

        if confirm_data.get("status") != "OK":
            return jsonify({
                "error": "confirm failed",
                "confirm_response": confirm_data,
                "confirm_status": confirm_resp.status_code
            }), 500

        # Extract mask details
        challenge = confirm_data.get("data", {}).get("challenge", {})
        mask = challenge.get("mask")
        salt = challenge.get("salt")
        key = challenge.get("key")
        factor = confirm_data.get("data", {}).get("factor")

        # Parse mask
        if mask:
            required_positions = [i for i, c in enumerate(mask) if c == "*"]
            optional_positions = [i for i, c in enumerate(mask) if c == "+"]
        else:
            required_positions = []
            optional_positions = []

        return jsonify({
            "success": True,
            "username": username,
            "factor": factor,
            "mask": mask,
            "mask_length": len(mask) if mask else 0,
            "required_positions": required_positions,
            "required_count": len(required_positions),
            "optional_positions": optional_positions,
            "optional_count": len(optional_positions),
            "salt": salt,
            "key": key,
            "auth_ref": auth_ref,
            "csrf": csrf,
            "confirm_ref": confirm_ref,
            "expiry_seconds": confirm_data.get("data", {}).get("expirySeconds")
        })

    except Exception as e:
        import traceback
        return jsonify({
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
