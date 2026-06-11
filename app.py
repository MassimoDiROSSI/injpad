from flask import Flask, render_template_string, request, jsonify, make_response
import requests
import json
import os

app = Flask(__name__)

# Manual CORS headers for all responses
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

@app.route("/")
def index():
    return "ING Challenge API - Use /get-challenge endpoint"

@app.route("/get-challenge", methods=["POST", "GET", "OPTIONS"])
def get_challenge():
    if request.method == "OPTIONS":
        return make_response("", 200)
    
    if request.method == "GET":
        username = request.args.get("username", "pioach3167")
    else:
        data = request.get_json() or {}
        username = data.get("username", "pioach3167")
    
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
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "pl-PL,pl;q=0.9,en-US;q=0.8,en;q=0.7",
        "Origin": "https://login.ingbank.pl",
        "Referer": "https://login.ingbank.pl/"
    }
    
    try:
        s = requests.Session()
        resp = s.post(
            "https://login.ingbank.pl/oauth2/oauth2confirm",
            json=payload,
            headers=headers,
            timeout=15,
            allow_redirects=True
        )
        
        data = resp.json()
        
        if data.get("status") == "OK":
            challenge = data["data"]["challenge"]
            return jsonify({
                "success": True,
                "mask": challenge["mask"],
                "key": challenge["key"],
                "salt": challenge["salt"],
                "ref": data["data"]["ref"],
                "finished": data["data"]["finished"],
                "factor": data["data"]["factor"]
            })
        else:
            return jsonify({
                "success": False,
                "error": data.get("message", "Unknown error"),
                "raw": data
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
