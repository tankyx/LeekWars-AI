#!/usr/bin/env python3
"""
LeekWars Script Compilation Validator
Uses websocket API to check compilation errors for any AI script by ID
"""

import requests
import websocket
import json
import time
import threading
import sys
import argparse

class LeekWarsScriptValidator:
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
            print(f"✅ Login successful as: {self.farmer.get('login')} (ID: {self.farmer.get('id')})")
        except Exception as e:
            print(f"❌ Login parse error: {e}")
            return False
            
        # Step 3: Establish authenticated web session
        auth_headers = {
            'Authorization': f'Bearer {self.token}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        main_response = self.session.get("https://leekwars.com/", headers=auth_headers)
        return True
            
    def get_script_code(self, script_id):
        """Fetch script code from LeekWars API"""
        print(f"📥 Fetching code for script ID {script_id}...")
        
        response = self.session.get(f"https://leekwars.com/api/ai/get/{script_id}")
        
        if response.status_code != 200:
            print(f"❌ Failed to fetch script: {response.status_code}")
            return None
            
        try:
            data = response.json()
            ai_data = data.get("ai", {})
            
            script_name = ai_data.get("name", "Unknown")
            script_code = ai_data.get("code", "")
            
            print(f"✅ Retrieved script: {script_name}")
            print(f"   📊 Code length: {len(script_code)} characters")
            
            if len(script_code.strip()) == 0:
                print("⚠️  Warning: Script appears to be empty")
                
            return {
                "id": script_id,
                "name": script_name,
                "code": script_code,
                "info": ai_data
            }
            
        except Exception as e:
            print(f"❌ Error parsing script data: {e}")
            return None
            
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
                    print(f"   📨 Analysis response received")
                    # The response format: content is a dict with script_id as key
                    if content and isinstance(content, dict):
                        for script_id_key, errors in content.items():
                            self.analysis_results[script_id_key] = content
                            if script_id_key in self.pending_analyses:
                                self.pending_analyses.remove(script_id_key)
                elif message_type == 65:  # EDITOR_ANALYZE_ERROR response
                    print(f"   📨 Analysis error response: {content}")
                    if request_id and request_id in self.pending_analyses:
                        self.analysis_results[request_id] = {"error": content}
                        self.pending_analyses.remove(request_id)
                else:
                    print(f"   📨 Other message type {message_type}")
                    
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
        timeout = 10
        while timeout > 0 and not self.connected:
            time.sleep(0.2)
            timeout -= 0.2
            
        return self.connected
        
    def analyze_script_code(self, script_id, code):
        """Send script analysis request via websocket"""
        if not self.connected:
            print("❌ Websocket not connected")
            return None
            
        print(f"🔍 Analyzing script {script_id}...")
        
        # EDITOR_ANALYZE message format: [64, script_id, code]
        message = [64, str(script_id), code]
        request_id = str(script_id)
        
        self.pending_analyses.add(request_id)
        self.analysis_results.pop(request_id, None)  # Clear any previous results
        
        self.ws.send(json.dumps(message))
        print(f"   📤 Sent analysis request...")
        
        # Wait for response
        timeout = 15
        while timeout > 0 and request_id in self.pending_analyses:
            time.sleep(0.3)
            timeout -= 0.3
            
        if request_id in self.analysis_results:
            result = self.analysis_results[request_id]
            return result
        else:
            print(f"   ⏰ Timeout waiting for analysis response")
            return None
    
    def parse_compilation_errors(self, errors):
        """Parse compilation errors into readable format"""
        if not errors:
            return {"total": 0, "categories": {}}
            
        error_categories = {
            "undefined_variables": [],
            "syntax_errors": [],
            "include_errors": [],
            "other_errors": []
        }
        
        for error in errors:
            if len(error) >= 7:
                line = error[0] if len(error) > 0 else 0
                col = error[1] if len(error) > 1 else 0
                error_code = error[6] if len(error) > 6 else 0
                error_data = error[7] if len(error) > 7 else None
                
                if error_code == 33:  # Undefined variable
                    var_name = error_data[0] if error_data and len(error_data) > 0 else "unknown"
                    error_categories["undefined_variables"].append({
                        "line": line,
                        "column": col,
                        "variable": var_name
                    })
                elif error_code == 1:  # Syntax error
                    error_categories["syntax_errors"].append({
                        "line": line,
                        "column": col,
                        "data": error_data
                    })
                elif error_code == 2:  # Include error
                    error_categories["include_errors"].append({
                        "line": line,
                        "column": col,
                        "data": error_data
                    })
                else:
                    error_categories["other_errors"].append({
                        "line": line,
                        "column": col,
                        "code": error_code,
                        "data": error_data
                    })
        
        return {
            "total": len(errors),
            "categories": error_categories
        }
    
    def validate_script(self, script_id):
        """Main validation function for a script ID"""
        print(f"\n🎯 VALIDATING SCRIPT ID: {script_id}")
        print("=" * 60)
        
        # Fetch script code
        script_data = self.get_script_code(script_id)
        if not script_data:
            return False
            
        # Analyze compilation
        result = self.analyze_script_code(script_id, script_data["code"])
        
        if result is None:
            print("❌ Analysis failed - no response received")
            return False
            
        # Parse results
        script_key = str(script_id)
        
        if isinstance(result, dict) and "error" in result:
            print(f"❌ Analysis error: {result['error']}")
            return False
            
        if isinstance(result, dict) and script_key in result:
            errors = result[script_key]
            
            if not errors:
                print("✅ NO COMPILATION ERRORS FOUND!")
                print(f"   Script '{script_data['name']}' compiles successfully")
                return True
                
            # Parse and display errors
            parsed = self.parse_compilation_errors(errors)
            
            print(f"❌ FOUND {parsed['total']} COMPILATION ERRORS")
            print(f"   Script: {script_data['name']}")
            print()
            
            # Display undefined variables
            if parsed['categories']['undefined_variables']:
                print("🔴 UNDEFINED VARIABLES:")
                undefined_vars = {}
                for err in parsed['categories']['undefined_variables']:
                    var_name = err['variable']
                    if var_name not in undefined_vars:
                        undefined_vars[var_name] = []
                    undefined_vars[var_name].append(f"line {err['line']}")
                
                for var_name, locations in undefined_vars.items():
                    print(f"   • {var_name} ({', '.join(locations)})")
                print()
            
            # Display syntax errors
            if parsed['categories']['syntax_errors']:
                print("🔴 SYNTAX ERRORS:")
                for err in parsed['categories']['syntax_errors']:
                    print(f"   • Line {err['line']}, Column {err['column']}: {err.get('data', 'Syntax error')}")
                print()
            
            # Display include errors
            if parsed['categories']['include_errors']:
                print("🔴 INCLUDE ERRORS:")
                for err in parsed['categories']['include_errors']:
                    print(f"   • Line {err['line']}: {err.get('data', 'Include error')}")
                print()
            
            # Display other errors
            if parsed['categories']['other_errors']:
                print("🔴 OTHER ERRORS:")
                for err in parsed['categories']['other_errors']:
                    print(f"   • Line {err['line']}, Column {err['column']}: Code {err['code']} - {err.get('data', 'Unknown error')}")
                print()
                
            return False
        else:
            print(f"📊 Unexpected analysis result format: {result}")
            return False
            
    def close(self):
        """Close websocket connection"""
        if hasattr(self, 'ws') and self.ws:
            self.ws.close()
        self.connected = False

def main():
    parser = argparse.ArgumentParser(description='Validate LeekWars AI script compilation')
    parser.add_argument('script_id', nargs='?', type=int, default=445497,
                       help='AI script ID to validate (default: 445497 for V6_main)')
    parser.add_argument('--v7', action='store_true', 
                       help='Validate V7_main script (ID: 445760)')
    parser.add_argument('--v7-test', action='store_true',
                       help='Validate V7_test script (ID: 445761)')
    
    args = parser.parse_args()
    
    # Handle shortcuts
    if args.v7:
        script_id = 445760
        print("🚀 Validating V7_main script")
    elif args.v7_test:
        script_id = 445761
        print("🧪 Validating V7_test script")
    else:
        script_id = args.script_id
        
    validator = LeekWarsScriptValidator()
    
    try:
        # Authenticate
        if not validator.authenticate():
            print("❌ Authentication failed")
            return 1
            
        # Connect websocket
        if not validator.connect_websocket():
            print("❌ Websocket connection failed")
            return 1
            
        # Validate script
        success = validator.validate_script(script_id)
        
        if success:
            print("\n🎉 VALIDATION PASSED!")
            return 0
        else:
            print("\n💥 VALIDATION FAILED - Compilation errors found")
            return 1
        
    except KeyboardInterrupt:
        print("\n⏹️  Interrupted by user")
        return 1
    finally:
        validator.close()

if __name__ == "__main__":
    sys.exit(main())