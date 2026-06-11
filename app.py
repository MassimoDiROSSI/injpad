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
    # Launch Chrome
    browser = await launch(
        headless=True,
        executablePath='/usr/bin/google-chrome-stable',
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--no-first-run',
            '--no-zygote',
            '--single-process'
        ]
    )
    
    page = await browser.newPage()
    await page.setViewport({'width': 1920, 'height': 1080})
    await page.setUserAgent('Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
    
    # Step 1: Navigate to login page and get ref from URL
    await page.goto('https://login.ingbank.pl/mojeing/app/', waitUntil='networkidle2')
    await asyncio.sleep(2)  # Wait for JS redirect
    
    # Get current URL with ref
    current_url = page.url
    print(f"Current URL: {current_url}")
    
    # Extract ref from URL
    import re
    ref_match = re.search(r'ref=([a-zA-Z0-9]+)', current_url)
    if not ref_match:
        await browser.close()
        return {"error": "Could not extract ref from URL", "url": current_url}
    
    ref = ref_match.group(1)
    print(f"Extracted ref: {ref}")
    
    # Step 2: POST ref to /oauth2/oauth2init to get tokens
    init_response = await page.evaluate(f'''async () => {{
        const response = await fetch('/oauth2/oauth2init', {{
            method: 'POST',
            headers: {{
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest'
            }},
            body: JSON.stringify({{
                "token": "",
                "trace": "",
                "data": {{
                    "ref": "{ref}",
                    "screenType": "D"
                }},
                "locale": "PL"
            }})
        }});
        return await response.json();
    }}''')
    
    print(f"Init response: {init_response}")
    
    if init_response.get('status') != 'OK':
        await browser.close()
        return {"error": "Init failed", "response": init_response}
    
    auth_ref = init_response['data']['authorizationReference']
    csrf_token = init_response['data']['csrfToken']
    
    # Step 3: POST to /oauth2/oauth2confirm with username
    confirm_response = await page.evaluate(f'''async () => {{
        const response = await fetch('/oauth2/oauth2confirm', {{
            method: 'POST',
            headers: {{
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRF-Token': '{csrf_token}'
            }},
            body: JSON.stringify({{
                "token": "{auth_ref}",
                "trace": "",
                "data": {{
                    "factor": "LOGIN",
                    "ref": "{auth_ref}",
                    "credentials": "{username}"
                }},
                "locale": "PL"
            }})
        }});
        return await response.json();
    }}''')
    
    print(f"Confirm response: {confirm_response}")
    
    await browser.close()
    
    if confirm_response.get('status') == 'OK':
        challenge = confirm_response['data']['challenge']
        return {
            "success": True,
            "mask": challenge['mask'],
            "key": challenge['key'],
            "salt": challenge['salt'],
            "ref": confirm_response['data']['ref']
        }
    else:
        return {
            "success": False,
            "error": confirm_response.get('msg', 'Unknown error'),
            "response": confirm_response
        }

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
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(get_ing_challenge(username))
        loop.close()
        
        return jsonify(result)
        
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
