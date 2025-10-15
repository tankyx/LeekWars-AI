#!/usr/bin/env python3
"""
Debug LeekWars Websocket Connection
Detailed debugging of the websocket connection to understand why it's failing
"""

import requests
import websocket
import json
import time
import threading
from urllib.parse import urlparse
import ssl

def debug_websocket_connection():
    """Debug the websocket connection step by step"""
    
    # First, login and get token + establish session cookies
    print("🔐 Step 1: Login and establish session cookies...")
    session = requests.Session()
    
    # Step 1a: Get initial cookies by visiting the site
    print("   📋 Getting initial session cookies...")
    initial_response = session.get("https://leekwars.com/")
    print(f"   📋 Initial cookies: {dict(session.cookies)}")
    
    # Step 1b: Login to get JWT token
    email, password = load_credentials()
    login_data = {"login": email, "password": password}

    response = session.post("https://leekwars.com/api/farmer/login-token", data=login_data)
    
    if response.status_code != 200:
        print(f"❌ Login failed: {response.status_code}")
        return False
        
    try:
        data = response.json()
        token = data.get('token')
        farmer = data.get('farmer')
        print(f"✅ Login successful as: {farmer.get('login')}")
        print(f"🎫 Token: {token[:20]}...")
        print(f"🍪 Session cookies after login: {dict(session.cookies)}")
    except Exception as e:
        print(f"❌ Login parse error: {e}")
        return False
        
    # Step 1c: Try to establish authenticated session like browser would
    print("   🌐 Establishing authenticated web session...")
    auth_headers = {
        'Authorization': f'Bearer {token}',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    # Visit main site with auth to establish full session
    main_response = session.get("https://leekwars.com/", headers=auth_headers)
    print(f"   🌐 Main site response: {main_response.status_code}")
    print(f"   🍪 Final cookies: {dict(session.cookies)}")
    
    # Check if __FARMER__ data gets injected (look for it in HTML)
    if '__FARMER__' in main_response.text:
        print("   ✅ Found __FARMER__ in response - session established!")
    else:
        print("   ⚠️  No __FARMER__ found - session may not be fully authenticated")
        
    # Test websocket URLs with session cookies
    test_urls = [
        "wss://leekwars.com/ws",           # PRODUCTION URL from socket.ts - should work with cookies!
        "wss://leekwars.com/websocket",    # Alternative endpoint (returns HTML normally)
    ]
    
    for ws_url in test_urls:
        print(f"\n🔌 Step 2: Testing websocket URL: {ws_url}")
        
        # Test with different subprotocol configurations
        subprotocol_configs = [
            ['leek-wars', token],
            ['leek-wars'],
            [token],
            []
        ]
        
        for subprotocols in subprotocol_configs:
            print(f"   🧪 Testing subprotocols: {subprotocols[:1]}..." if subprotocols else "   🧪 Testing no subprotocols")
            
            try:
                # Create websocket with debug enabled
                websocket.enableTrace(True)
                
                connected = False
                error_msg = None
                
                def on_open(ws):
                    nonlocal connected
                    print(f"   ✅ Connected successfully!")
                    connected = True
                    # Try sending a test message
                    test_msg = [64, 445497, "// test"]  # EDITOR_ANALYZE message
                    ws.send(json.dumps(test_msg))
                    
                def on_message(ws, message):
                    print(f"   📨 Received message: {message[:100]}...")
                    
                def on_error(ws, error):
                    nonlocal error_msg
                    print(f"   ❌ Error: {error}")
                    error_msg = str(error)
                    
                def on_close(ws, close_status_code, close_msg):
                    print(f"   🔌 Closed: {close_status_code} - {close_msg}")
                
                # Create websocket with session cookies
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                }
                
                # Add session cookies to websocket headers
                if session.cookies:
                    cookie_header = "; ".join([f"{cookie.name}={cookie.value}" for cookie in session.cookies])
                    headers['Cookie'] = cookie_header
                    print(f"   🍪 Adding cookies to websocket: {cookie_header[:50]}...")
                
                ws = websocket.WebSocketApp(
                    ws_url,
                    subprotocols=subprotocols if subprotocols else None,
                    header=headers,
                    on_open=on_open,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close
                )
                
                # Run with timeout
                def run_ws():
                    ws.run_forever(
                        sslopt={"cert_reqs": ssl.CERT_NONE},
                        ping_interval=30,
                        ping_timeout=10
                    )
                
                ws_thread = threading.Thread(target=run_ws)
                ws_thread.daemon = True
                ws_thread.start()
                
                # Wait for connection or error
                timeout = 5
                while timeout > 0 and not connected and error_msg is None:
                    time.sleep(0.2)
                    timeout -= 0.2
                    
                if connected:
                    print(f"   🎉 SUCCESS with {ws_url} and subprotocols {subprotocols}")
                    time.sleep(2)  # Wait for any messages
                    ws.close()
                    return True
                elif error_msg:
                    print(f"   ❌ Failed: {error_msg}")
                else:
                    print(f"   ⏰ Timeout")
                    
                if ws:
                    ws.close()
                    
            except Exception as e:
                print(f"   ❌ Exception: {e}")
                
            time.sleep(0.5)  # Brief pause between attempts
            
    print(f"\n❌ All websocket connection attempts failed")
    return False

def test_http_endpoints():
    """Test if HTTP endpoints are accessible"""
    print(f"\n🌐 Step 3: Testing HTTP endpoints...")
    
    session = requests.Session()
    
    # Login first
    email, password = load_credentials()
    login_data = {"login": email, "password": password}

    response = session.post("https://leekwars.com/api/farmer/login-token", data=login_data)
    if response.status_code != 200:
        print("❌ Cannot test - login failed")
        return
        
    token = response.json().get('token')
    
    # Test various endpoints
    test_endpoints = [
        "https://leekwars.com/api/ai/get-farmer-ais",
        "https://leekwars.com/api/ai/get/445497",  # V6_main
        "https://leekwars.com/websocket",
        "https://leekwars.com/ws",
    ]
    
    for endpoint in test_endpoints:
        try:
            response = session.get(endpoint, timeout=5)
            print(f"   {endpoint}: {response.status_code}")
            if response.status_code == 404:
                print(f"     ❌ 404 Not Found")
            elif response.status_code == 200:
                print(f"     ✅ OK")
                # Show first bit of response for context
                content_type = response.headers.get('content-type', '')
                if 'json' in content_type:
                    try:
                        data = response.json()
                        print(f"     📄 JSON response with {len(data)} keys")
                    except:
                        print(f"     📄 {len(response.text)} chars")
                else:
                    print(f"     📄 {content_type}: {len(response.text)} chars")
            else:
                print(f"     ⚠️  Status: {response.status_code}")
                
        except Exception as e:
            print(f"   {endpoint}: ❌ {e}")

def check_websocket_libraries():
    """Check websocket library configuration"""
    print(f"\n📚 Step 4: Checking websocket libraries...")
    
    try:
        import websocket
        print(f"✅ websocket-client version: {websocket.__version__ if hasattr(websocket, '__version__') else 'unknown'}")
    except ImportError:
        print("❌ websocket-client not available")
        
    try:
        import ssl
from config_loader import load_credentials
        print(f"✅ SSL support: {ssl.OPENSSL_VERSION}")
    except ImportError:
        print("❌ SSL not available")
        
    # Test basic websocket functionality
    try:
        print("🧪 Testing basic websocket creation...")
        ws = websocket.WebSocket()
        print("✅ WebSocket object created successfully")
    except Exception as e:
        print(f"❌ WebSocket creation failed: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("LEEKWARS WEBSOCKET DEBUG")
    print("=" * 60)
    
    check_websocket_libraries()
    test_http_endpoints()
    debug_websocket_connection()