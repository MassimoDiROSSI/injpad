from flask import Flask, request, jsonify, make_response
import asyncio
from pyppeteer import launch
import os

app = Flask(__name__)

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type')
    response.headers.add('Access-Control-Allow-Methods', 'GET,POST,OPTIONS')
    return response

async def get_ing_challenge(username):
    browser = await launch(
        headless=True,
        args=['--no-sandbox', '--disable-setuid-sandbox']
    )
    page = await browser.newPage()
    
    # Set user agent
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    # Navigate to login page
    await page.goto('https://login.ingbank.pl/', waitUntil='networkidle2')
    
    # Wait for login input and fill it
    await page.waitForSelector('input[name="login"]', timeout=10000)
    await page.type('input[name="login"]', username)
    
    # Click next/submit
    await page.click('button[type="submit"]')
    
    # Wait for challenge response
    await page.waitForTimeout(3000)
    
    # Extract challenge data from page or network
    challenge = await page.evaluate('''() => {
        // Try to find challenge data in window object or DOM
        if (window.__INITIAL_STATE__ && window.__INITIAL_STATE__.challenge) {
            return window.__INITIAL_STATE__.challenge;
        }
        return null;
    }''')
    
    await browser.close()
    return challenge

@app.route("/get-challenge", methods=["POST", "GET", "OPTIONS"])
def get_challenge():
    if request.method == "OPTIONS":
        return make_response("", 200)
    
    if request.method == "GET":
        username = request.args.get("username", "pioach3167")
    else:
        data = request.get_json() or {}
        username = data.get("username", "pioach3167")
    
    try:
        # Run async function
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(get_ing_challenge(username))
        loop.close()
        
        if result:
            return jsonify({
                "success": True,
                "mask": result.get("mask"),
                "key": result.get("key"),
                "salt": result.get("salt"),
                "ref": result.get("ref")
            })
        else:
            return jsonify({
                "success": False,
                "error": "Could not extract challenge data"
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
