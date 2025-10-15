#!/usr/bin/env python3
"""
LeekWars Websocket Error Analyzer
Based on actual LeekWars editor source code analysis

This tool replicates the exact websocket communication used by the LeekWars editor
to get detailed compilation errors for AI scripts.

Key insights from ~/leek-wars/src/component/editor/analyzer.ts:
- Uses websocket with subprotocols ['leek-wars', token]
- Sends [SocketMessage.EDITOR_ANALYZE, ai.id, code] (message type 64)
- Receives response with problem arrays in format:
  [level, ai_id, line, start_col, end_line, end_col, error_code, error_params?]
- Level: 0=error, 1=warning, 2=todo
- ai_id: The specific included file ID that has the error
"""

import requests
import websocket
import json
import time
import threading
from queue import Queue, Empty
import sys
import argparse
from typing import Dict, List, Optional, Tuple

class LeekWarsErrorAnalyzer:
    def __init__(self):
        self.session = requests.Session()
        self.farmer = None
        self.token = None
        self.ws = None
        self.ws_connected = False
        self.analysis_results = Queue()
        self.base_url = "https://leekwars.com"
        self.ai_id_to_name = {}  # Map AI IDs to their names/paths
        
        # Socket message constants from LeekWars source
        self.SOCKET_MESSAGE_EDITOR_ANALYZE = 64
        self.SOCKET_MESSAGE_EDITOR_ANALYZE_ERROR = 65
        
    def login(self, email: str, password: str) -> bool:
        """Login to LeekWars using exact same method as editor"""
        print("🔐 Logging in...")
        
        login_url = f"{self.base_url}/api/farmer/login-token"
        login_data = {
            "login": email,
            "password": password
        }
        
        response = self.session.post(login_url, data=login_data)
        
        if response.status_code == 200:
            try:
                data = response.json()
                
                if "farmer" in data and "token" in data:
                    self.farmer = data["farmer"]
                    self.token = data["token"]
                    
                    print(f"✅ Connected as: {self.farmer.get('login')}")
                    return True
                else:
                    print(f"❌ Missing farmer or token in response")
            except Exception as e:
                print(f"❌ Failed to parse JSON response: {e}")
        else:
            print(f"❌ Login failed with status {response.status_code}")
        
        return False
        
    def get_ai_list(self) -> List[Dict]:
        """Get list of AI scripts using exact same endpoint as editor"""
        response = self.session.get(f"{self.base_url}/api/ai/get-farmer-ais")
        
        if response.status_code == 200:
            try:
                data = response.json()
                ais = data.get('ais', [])
                print(f"✅ Retrieved {len(ais)} AIs")
                
                # Build AI ID to name mapping using exact folder mapping from editor
                folder_names = {
                    29813: "core",
                    29814: "combat",
                    29815: "movement", 
                    29816: "strategy",
                    29817: "ai",
                    29818: "utils",
                    29828: "blaser",
                    29812: "V6",
                    0: "root"
                }
                
                for ai in ais:
                    ai_id = ai.get('id')
                    ai_name = ai.get('name', 'Unknown')
                    folder_id = ai.get('folder', 0)
                    
                    folder_name = folder_names.get(folder_id, "root")
                    display_name = f"{folder_name}/{ai_name}" if folder_name != "root" else ai_name
                    
                    self.ai_id_to_name[ai_id] = display_name
                
                return ais
            except Exception as e:
                print(f"❌ Failed to parse AI list JSON: {e}")
        else:
            print(f"❌ AI list request failed: {response.status_code}")
            
        return []
        
    def get_ai_code(self, ai_id: int) -> Optional[str]:
        """Get AI script code using exact same endpoint as editor"""
        response = self.session.get(f"{self.base_url}/api/ai/get/{ai_id}")
        if response.status_code == 200:
            try:
                data = response.json()
                return data.get('ai', {}).get('code', '')
            except Exception as e:
                print(f"❌ Failed to parse AI code response for {ai_id}: {e}")
        else:
            print(f"❌ Failed to get AI code: HTTP {response.status_code}")
        return None
        
    def connect_websocket(self) -> bool:
        """Connect to LeekWars websocket using exact format from editor source"""
        print("🔌 Connecting to websocket...")
        
        # Exact URL and subprotocols from socket.ts:109-110
        ws_url = "wss://leekwars.com/ws"
        
        def on_open(ws):
            print("✅ Websocket connected")
            self.ws_connected = True
            # No need to send auth - handled by subprotocols
            
        def on_message(ws, message):
            try:
                data = json.loads(message)
                if isinstance(data, list) and len(data) > 0:
                    message_type = data[0]
                    
                    # From socket.ts case SocketMessage.EDITOR_ANALYZE (64)
                    if message_type == self.SOCKET_MESSAGE_EDITOR_ANALYZE:
                        self.analysis_results.put(data)
                        print(f"📝 Received analysis result")
                    # From socket.ts case SocketMessage.EDITOR_ANALYZE_ERROR (65) 
                    elif message_type == self.SOCKET_MESSAGE_EDITOR_ANALYZE_ERROR:
                        self.analysis_results.put(data)
                        print(f"❌ Received analysis error")
                        
            except json.JSONDecodeError as e:
                print(f"Failed to parse WebSocket message: {e}")
                
        def on_error(ws, error):
            print(f"❌ Websocket error: {error}")
            self.ws_connected = False
            
        def on_close(ws, close_status_code, close_msg):
            print(f"🔌 Websocket closed (status: {close_status_code})")
            self.ws_connected = False
            
        # Exact subprotocols from socket.ts:110
        self.ws = websocket.WebSocketApp(
            ws_url,
            subprotocols=['leek-wars', self.token],
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close
        )
        
        # Start websocket in separate thread
        def run_websocket():
            self.ws.run_forever()
            
        ws_thread = threading.Thread(target=run_websocket)
        ws_thread.daemon = True
        ws_thread.start()
        
        # Wait for connection
        timeout = 10
        while not self.ws_connected and timeout > 0:
            time.sleep(0.5)
            timeout -= 0.5
            
        return self.ws_connected
        
    def analyze_ai(self, ai_id: int, code: str) -> Optional[Dict]:
        """Send analysis request using exact format from analyzer.ts:97"""
        if not self.ws_connected:
            return None
            
        print(f"🧪 Analyzing AI {ai_id}...")
        
        # Exact message format from analyzer.ts:97
        # LeekWars.socket.send([SocketMessage.EDITOR_ANALYZE, ai.id, code])
        analyze_message = [self.SOCKET_MESSAGE_EDITOR_ANALYZE, ai_id, code]
        self.ws.send(json.dumps(analyze_message))
        
        # Wait for response with timeout
        timeout = 30
        try:
            result = self.analysis_results.get(timeout=timeout)
            return result
        except Empty:
            print(f"⏰ Analysis timeout for AI {ai_id}")
            return None
            
    def parse_analysis_result(self, result: List) -> Tuple[bool, List[Dict], Dict[str, List]]:
        """Parse analysis result using exact format from analyzer.ts:218-263"""
        if not result or len(result) < 2:
            return True, [], {}
            
        # From handleProblems: data format is [message_type, result_data]
        analysis_data = result[1] if len(result) > 1 else {}
        
        errors = []
        warnings = []
        todos = []
        file_errors = {}  # Group by file
        
        # Handle different result formats - from editor source analysis
        problems = []
        if isinstance(analysis_data, dict) and 'result' in analysis_data:
            # Nested format with entrypoints
            result_data = analysis_data['result']
            if isinstance(result_data, dict):
                for entrypoint, entrypoint_problems in result_data.items():
                    if isinstance(entrypoint_problems, list):
                        problems.extend(entrypoint_problems)
            elif isinstance(result_data, list):
                problems = result_data
        elif isinstance(analysis_data, list):
            # Direct list format
            problems = analysis_data
        elif isinstance(analysis_data, dict) and any(isinstance(v, list) for v in analysis_data.values()):
            # Entrypoint-keyed format
            for entrypoint_key, entrypoint_problems in analysis_data.items():
                if isinstance(entrypoint_problems, list):
                    problems.extend(entrypoint_problems)
                    
        # Parse problems using exact format from analyzer.ts:226-250
        for problem in problems:
            if isinstance(problem, list) and len(problem) >= 6:
                level = problem[0]        # 0 = error, 1 = warning, 2 = todo
                ai_id = problem[1]        # The specific file ID with the error!
                line = problem[2]         # Line number
                start_col = problem[3]    # Start column  
                end_line = problem[4]     # End line
                end_col = problem[5]      # End column
                error_code = problem[6] if len(problem) > 6 else "UNKNOWN_ERROR"
                error_params = problem[7] if len(problem) > 7 else []
                
                # Get file name from AI ID
                file_name = self.ai_id_to_name.get(ai_id, f"Unknown (ID: {ai_id})")
                
                error_detail = {
                    'level': 'ERROR' if level == 0 else 'WARNING' if level == 1 else 'TODO',
                    'line': line,
                    'start_col': start_col,
                    'end_line': end_line,
                    'end_col': end_col,
                    'error_code': error_code,
                    'error_params': error_params,
                    'file_name': file_name,
                    'message': f"Line {line}:{start_col}-{end_col}: Code {error_code}"
                }
                
                if error_params:
                    error_detail['message'] += f" {error_params}"
                
                if level == 0:  # Error
                    errors.append(error_detail)
                elif level == 1:  # Warning
                    warnings.append(error_detail)
                elif level == 2:  # Todo
                    todos.append(error_detail)
                    
                # Group by file
                if file_name not in file_errors:
                    file_errors[file_name] = []
                file_errors[file_name].append(error_detail)
        
        has_errors = len(errors) > 0
        all_issues = errors + warnings + todos
        
        return not has_errors, all_issues, file_errors
        
    def analyze_script(self, ai_name: str, detailed: bool = True) -> bool:
        """Analyze a specific AI script with detailed error reporting"""
        print("=" * 80)
        print(f"LEEKWARS COMPILATION ERROR ANALYSIS - {ai_name}")
        print("Based on actual LeekWars editor websocket communication")
        print("=" * 80)
        
        # Get AI list
        ais = self.get_ai_list()
        if not ais:
            print("❌ No AIs found")
            return False
            
        # Connect to websocket
        if not self.connect_websocket():
            print("❌ Failed to connect to websocket")
            return False
            
        # Find target AI
        target_ai = None
        for ai in ais:
            if ai.get('name') == ai_name:
                target_ai = ai
                break
                
        if not target_ai:
            print(f"❌ AI '{ai_name}' not found")
            available = [ai.get('name') for ai in ais if 'V6' in self.ai_id_to_name.get(ai.get('id', 0), '')]
            if available:
                print(f"📋 Available V6 AIs: {', '.join(available[:10])}")
            return False
            
        ai_id = target_ai.get('id')
        print(f"📄 Found {ai_name} (ID: {ai_id})")
        
        # Get AI code
        code = self.get_ai_code(ai_id)
        if not code:
            print(f"❌ Could not retrieve code for {ai_name}")
            return False
            
        print(f"📝 Retrieved code ({len(code)} characters)")
        
        # Analyze with websocket
        print(f"🔍 Analyzing {ai_name} for compilation errors...")
        analysis_result = self.analyze_ai(ai_id, code)
        
        if not analysis_result:
            print("❌ Failed to get analysis result")
            return False
            
        # Parse results with file identification  
        is_valid, all_issues, file_errors = self.parse_analysis_result(analysis_result)
        
        if is_valid:
            print(f"✅ {ai_name} compiles successfully!")
            return True
        else:
            print(f"❌ {ai_name} has {len(all_issues)} compilation issues")
            
            if detailed and file_errors:
                self._print_detailed_errors(file_errors)
            else:
                self._print_summary_errors(all_issues)
                
        return False
        
    def analyze_all_v6(self) -> Dict[str, bool]:
        """Analyze all V6-related AI scripts"""
        print("=" * 80)
        print("COMPREHENSIVE V6 MODULE ANALYSIS")
        print("=" * 80)
        
        # Get AI list
        ais = self.get_ai_list()
        if not ais:
            print("❌ No AIs found")
            return {}
            
        # Connect to websocket
        if not self.connect_websocket():
            print("❌ Failed to connect to websocket")
            return {}
            
        # Find all V6-related AIs
        v6_ais = []
        for ai in ais:
            ai_id = ai.get('id')
            display_name = self.ai_id_to_name.get(ai_id, '')
            if any(folder in display_name for folder in ['V6', 'core', 'combat', 'ai', 'movement', 'strategy', 'utils', 'blaser']):
                v6_ais.append((ai, display_name))
                
        print(f"📋 Found {len(v6_ais)} V6-related AIs")
        
        results = {}
        errors_found = []
        
        for ai, display_name in v6_ais:
            ai_id = ai.get('id')
            ai_name = ai.get('name')
            
            print(f"\n🔍 Analyzing {display_name}...")
            
            # Get code
            code = self.get_ai_code(ai_id)
            if not code:
                print(f"❌ Could not get code for {ai_name}")
                results[display_name] = False
                continue
                
            # Analyze
            analysis_result = self.analyze_ai(ai_id, code)
            if not analysis_result:
                print(f"❌ Analysis failed for {ai_name}")
                results[display_name] = False
                continue
                
            # Parse results
            is_valid, all_issues, file_errors = self.parse_analysis_result(analysis_result)
            results[display_name] = is_valid
            
            if is_valid:
                print(f"   ✅ Valid")
            else:
                print(f"   ❌ {len(all_issues)} issues")
                errors_found.append((display_name, file_errors))
                
        # Summary
        print(f"\n" + "=" * 60)
        print("FINAL RESULTS")
        print("=" * 60)
        
        valid_count = sum(1 for v in results.values() if v)
        total_count = len(results)
        
        print(f"✅ Valid: {valid_count}/{total_count}")
        print(f"❌ Errors: {total_count - valid_count}/{total_count}")
        
        if errors_found:
            print(f"\n🔴 MODULES WITH ERRORS:")
            for display_name, file_errors in errors_found:
                error_count = sum(len([e for e in errors if e['level'] == 'ERROR']) for errors in file_errors.values())
                warning_count = sum(len([e for e in errors if e['level'] == 'WARNING']) for errors in file_errors.values())
                print(f"   {display_name}: {error_count} errors, {warning_count} warnings")
                
        return results
        
    def _print_detailed_errors(self, file_errors: Dict[str, List]):
        """Print detailed error breakdown by file"""
        print(f"\n📋 ERRORS BY FILE:")
        print("=" * 50)
        
        for file_name, errors in file_errors.items():
            error_count = len([e for e in errors if e['level'] == 'ERROR'])
            warning_count = len([e for e in errors if e['level'] == 'WARNING'])
            todo_count = len([e for e in errors if e['level'] == 'TODO'])
            
            print(f"\n🔴 {file_name}")
            if error_count > 0 or warning_count > 0:
                print(f"   📊 {error_count} errors, {warning_count} warnings, {todo_count} todos")
            
            for error in errors:
                level_icon = "🔴" if error['level'] == 'ERROR' else "🟡" if error['level'] == 'WARNING' else "🔵"
                print(f"   {level_icon} {error['message']}")
                
        # Summary by module type
        print(f"\n📈 ERROR SUMMARY BY MODULE TYPE:")
        print("=" * 40)
        
        module_types = {}
        for file_name, errors in file_errors.items():
            if '/' in file_name:
                module_type = file_name.split('/')[0]
            else:
                module_type = 'root'
                
            if module_type not in module_types:
                module_types[module_type] = {'errors': 0, 'warnings': 0, 'files': set()}
                
            module_types[module_type]['files'].add(file_name)
            for error in errors:
                if error['level'] == 'ERROR':
                    module_types[module_type]['errors'] += 1
                elif error['level'] == 'WARNING':
                    module_types[module_type]['warnings'] += 1
                    
        for module_type, stats in module_types.items():
            print(f"   📂 {module_type}: {stats['errors']} errors, {stats['warnings']} warnings in {len(stats['files'])} files")
            
    def _print_summary_errors(self, all_issues: List[Dict]):
        """Print summary of all issues"""
        print(f"\n📋 ALL ISSUES:")
        print("=" * 30)
        for issue in all_issues:
            level_icon = "🔴" if issue['level'] == 'ERROR' else "🟡" if issue['level'] == 'WARNING' else "🔵"
            print(f"{level_icon} {issue['file_name']}: {issue['message']}")

def main():
    """Main function with command line interface"""
    parser = argparse.ArgumentParser(description='LeekWars AI Compilation Error Analyzer')
    parser.add_argument('--email', required=True, help='LeekWars account email')
    parser.add_argument('--password', required=True, help='LeekWars account password') 
    parser.add_argument('--ai', help='Specific AI name to analyze (e.g., V6_main)')
    parser.add_argument('--all-v6', action='store_true', help='Analyze all V6-related modules')
    parser.add_argument('--summary', action='store_true', help='Show summary only (not detailed errors)')
    
    args = parser.parse_args()
    
    analyzer = LeekWarsErrorAnalyzer()
    
    # Login
    if not analyzer.login(args.email, args.password):
        print("❌ Failed to login")
        return False
        
    # Analyze
    if args.all_v6:
        results = analyzer.analyze_all_v6()
        success = all(results.values())
    elif args.ai:
        success = analyzer.analyze_script(args.ai, detailed=not args.summary)
    else:
        print("❌ Must specify either --ai <name> or --all-v6")
        return False
        
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)