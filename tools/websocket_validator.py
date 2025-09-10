#!/usr/bin/env python3
"""
LeekWars Websocket Compilation Validator
Uses session cookie authentication to validate LeekScript compilation via websocket
"""

import requests
import websocket
import json
import time
import threading
import sys

class LeekWarsValidator:
    def __init__(self):
        self.session = requests.Session()
        self.token = None
        self.farmer = None
        self.connected = False
        self.analysis_results = {}
        self.pending_analyses = set()
        
    def authenticate(self, email="tanguy.pedrazzoli@gmail.com", password="tanguy0211"):
        """Establish authenticated session with LeekWars"""
        print("🔐 Authenticating with LeekWars...")
        
        # Step 1: Get initial session cookies
        initial_response = self.session.get("https://leekwars.com/")
        print(f"   📋 Initial cookies: {dict(self.session.cookies)}")
        
        # Step 2: Login to get JWT token
        login_data = {"login": email, "password": password}
        response = self.session.post("https://leekwars.com/api/farmer/login-token", data=login_data)
        
        if response.status_code != 200:
            print(f"❌ Login failed: {response.status_code}")
            return False
            
        try:
            data = response.json()
            self.token = data.get('token')
            self.farmer = data.get('farmer')
            print(f"✅ Login successful as: {self.farmer.get('login')}")
            print(f"🍪 Session cookies: {dict(self.session.cookies)}")
        except Exception as e:
            print(f"❌ Login parse error: {e}")
            return False
            
        # Step 3: Establish authenticated web session
        auth_headers = {
            'Authorization': f'Bearer {self.token}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        main_response = self.session.get("https://leekwars.com/", headers=auth_headers)
        if '__FARMER__' in main_response.text:
            print("   ✅ Full session established!")
            return True
        else:
            print("   ⚠️  Session may not be fully authenticated")
            return True  # Try anyway
            
    def connect_websocket(self):
        """Connect to LeekWars websocket with session cookies"""
        print("🔌 Connecting to LeekWars websocket...")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Add session cookies to websocket headers
        if self.session.cookies:
            cookie_header = "; ".join([f"{cookie.name}={cookie.value}" for cookie in self.session.cookies])
            headers['Cookie'] = cookie_header
            
        def on_open(ws):
            print("   ✅ Websocket connected successfully!")
            self.connected = True
            
        def on_message(ws, message):
            try:
                data = json.loads(message)
                message_type = data[0]
                content = data[1] if len(data) > 1 else None
                request_id = data[2] if len(data) > 2 else None
                
                if message_type == 64:  # EDITOR_ANALYZE response
                    print(f"   📨 Analysis response: {message}")
                    # The response doesn't have request_id, so we match by script_id in content
                    if content and isinstance(content, dict):
                        for script_id_key, errors in content.items():
                            if script_id_key in self.pending_analyses:
                                self.analysis_results[script_id_key] = content
                                self.pending_analyses.remove(script_id_key)
                elif message_type == 65:  # EDITOR_ANALYZE_ERROR response
                    print(f"   📨 Analysis error response: {message}")
                    self.analysis_results[request_id] = {"error": content}
                    if request_id in self.pending_analyses:
                        self.pending_analyses.remove(request_id)
                else:
                    print(f"   📨 Other message: {message}")
                    
            except json.JSONDecodeError:
                print(f"   ❌ Invalid JSON message: {message}")
                
        def on_error(ws, error):
            print(f"   ❌ Websocket error: {error}")
            
        def on_close(ws, close_status_code, close_msg):
            print(f"   🔌 Websocket closed: {close_status_code} - {close_msg}")
            self.connected = False
            
        self.ws = websocket.WebSocketApp(
            "wss://leekwars.com/ws",
            subprotocols=['leek-wars', self.token],
            header=headers,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        # Run websocket in background thread
        self.ws_thread = threading.Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()
        
        # Wait for connection
        timeout = 5
        while timeout > 0 and not self.connected:
            time.sleep(0.2)
            timeout -= 0.2
            
        return self.connected
        
    def analyze_script(self, script_id, code):
        """Send script analysis request via websocket"""
        if not self.connected:
            print("❌ Websocket not connected")
            return None
            
        # EDITOR_ANALYZE message format: [64, script_id, code]
        message = [64, script_id, code]
        request_id = str(script_id)  # Use script_id as request identifier
        
        self.pending_analyses.add(request_id)
        self.ws.send(json.dumps(message))
        print(f"   📤 Sent analysis request for script {script_id}")
        
        # Wait for response
        timeout = 10
        while timeout > 0 and request_id in self.pending_analyses:
            time.sleep(0.2)
            timeout -= 0.2
            
        if request_id in self.analysis_results:
            result = self.analysis_results[request_id]
            # Remove from pending
            if request_id in self.pending_analyses:
                self.pending_analyses.remove(request_id)
            return result
        else:
            print(f"   ⏰ Timeout waiting for analysis of script {script_id}")
            return None
            
    def validate_v6_modules(self):
        """Validate all V6 modules that were reported to have errors"""
        print("\n🔍 Validating V6 modules with previous errors...")
        
        # Modules that were reported to have compilation issues
        problem_modules = [
            "damage_calculation",
            "combat_decisions", 
            "emergency_decisions",
            "tactical_decisions_ai"
        ]
        
        results = {}
        for module_name in problem_modules:
            print(f"\n📋 Checking {module_name}...")
            
            # Read module file
            module_path = f"/home/ubuntu/LeekWars-AI/V6_modules/{self._get_module_path(module_name)}"
            try:
                with open(module_path, 'r') as f:
                    code = f.read()
                    
                # Use the real V6_main script ID for analysis
                script_id = 445497  # V6_main script ID
                result = self.analyze_script(script_id, code)
                
                if result is not None:
                    if isinstance(result, dict) and str(script_id) in result:
                        errors = result[str(script_id)]
                        if errors:
                            print(f"   ❌ Found {len(errors)} compilation errors:")
                            # Parse and categorize errors
                            undefined_vars = set()
                            for error in errors:
                                if len(error) >= 7 and error[6] == 33:  # error code 33 = undefined variable
                                    if len(error) > 7 and error[7]:
                                        var_name = error[7][0] if error[7] else "unknown"
                                        undefined_vars.add(var_name)
                                        
                            print(f"      📝 Undefined variables ({len(undefined_vars)}): {sorted(list(undefined_vars))}")
                        else:
                            print(f"   ✅ No compilation errors found!")
                    elif isinstance(result, dict) and "error" in result:
                        print(f"   ❌ Analysis error: {result['error']}")
                    else:
                        print(f"   📊 Analysis result: {result}")
                    results[module_name] = result
                else:
                    print(f"   ❌ Analysis failed - no response received")
                    results[module_name] = None
                    
            except FileNotFoundError:
                print(f"   ❌ Module file not found: {module_path}")
                results[module_name] = "FILE_NOT_FOUND"
                
        return results
        
    def _get_module_path(self, module_name):
        """Get the file path for a module name"""
        module_paths = {
            "damage_calculation": "combat/damage_calculation.ls",
            "combat_decisions": "ai/combat_decisions.ls",
            "emergency_decisions": "ai/emergency_decisions.ls", 
            "tactical_decisions_ai": "ai/tactical_decisions_ai.ls"
        }
        return module_paths.get(module_name, f"{module_name}.ls")
        
    def close(self):
        """Close websocket connection"""
        if hasattr(self, 'ws') and self.ws:
            self.ws.close()
        self.connected = False

def main():
    validator = LeekWarsValidator()
    
    try:
        # Authenticate
        if not validator.authenticate():
            print("❌ Authentication failed")
            return 1
            
        # Connect websocket
        if not validator.connect_websocket():
            print("❌ Websocket connection failed")
            return 1
            
        # Validate modules
        results = validator.validate_v6_modules()
        
        # Summary
        print("\n" + "="*50)
        print("VALIDATION SUMMARY")
        print("="*50)
        
        for module, result in results.items():
            if result is None:
                print(f"❌ {module}: Analysis failed")
            elif result == "FILE_NOT_FOUND":
                print(f"❌ {module}: File not found")
            elif isinstance(result, dict):
                script_errors = list(result.values())[0] if result else []
                if script_errors:
                    print(f"❌ {module}: {len(script_errors)} errors found")
                else:
                    print(f"✅ {module}: No errors")
            else:
                print(f"📊 {module}: {result}")
        
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
    finally:
        validator.close()
        
    return 0

if __name__ == "__main__":
    sys.exit(main())