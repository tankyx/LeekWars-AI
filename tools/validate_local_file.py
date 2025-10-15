#!/usr/bin/env python3
"""
LeekWars Local File Validation
Validates a local LeekScript file by uploading it temporarily for compilation checking
"""

import requests
import websocket
import json
import time
import threading
import sys
import argparse
import os
from config_loader import load_credentials

class LeekWarsLocalValidator:
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
        
    def analyze_file_code(self, file_path, code):
        """Send script analysis request via websocket"""
        if not self.connected:
            print("❌ Websocket not connected")
            return None
            
        print(f"🔍 Analyzing file {file_path}...")
        
        # Use a dummy script ID for local validation
        dummy_id = "local_validation"
        
        # EDITOR_ANALYZE message format: [64, script_id, code]
        message = [64, dummy_id, code]
        request_id = dummy_id
        
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
            "reserved_keywords": [],
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
                elif error_code == 17:  # Reserved keyword or similar
                    error_categories["reserved_keywords"].append({
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
    
    def validate_file(self, file_path):
        """Main validation function for a local file"""
        if not os.path.exists(file_path):
            print(f"❌ File not found: {file_path}")
            return False
            
        print(f"\n🎯 VALIDATING LOCAL FILE: {os.path.basename(file_path)}")
        print("=" * 60)
        
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
        except Exception as e:
            print(f"❌ Failed to read file: {e}")
            return False
            
        print(f"✅ File loaded successfully")
        print(f"   📊 Code length: {len(code)} characters")
        print(f"   📊 Lines of code: {len(code.splitlines())}")
        
        # Analyze compilation
        result = self.analyze_file_code(file_path, code)
        
        if result is None:
            print("❌ Analysis failed - no response received")
            return False
            
        # Parse results
        dummy_id = "local_validation"
        
        if isinstance(result, dict) and "error" in result:
            print(f"❌ Analysis error: {result['error']}")
            return False
            
        if isinstance(result, dict) and dummy_id in result:
            errors = result[dummy_id]
            
            if not errors:
                print("✅ NO COMPILATION ERRORS FOUND!")
                print(f"   File '{os.path.basename(file_path)}' compiles successfully")
                return True
                
            # Parse and display errors
            parsed = self.parse_compilation_errors(errors)
            
            print(f"❌ FOUND {parsed['total']} COMPILATION ERRORS")
            print(f"   File: {os.path.basename(file_path)}")
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
            
            # Display reserved keyword errors
            if parsed['categories']['reserved_keywords']:
                print("🔴 RESERVED KEYWORD/NAMING CONFLICTS:")
                for err in parsed['categories']['reserved_keywords']:
                    print(f"   • Line {err['line']}, Column {err['column']}: {err.get('data', 'Naming conflict')}")
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
    parser = argparse.ArgumentParser(description='Validate local LeekScript file compilation')
    parser.add_argument('file_path', help='Path to the LeekScript file to validate')
    
    args = parser.parse_args()
    
    validator = LeekWarsLocalValidator()
    
    try:
        # Authenticate
        if not validator.authenticate():
            print("❌ Authentication failed")
            return 1
            
        # Connect websocket
        if not validator.connect_websocket():
            print("❌ Websocket connection failed")
            return 1
            
        # Validate file
        success = validator.validate_file(args.file_path)
        
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