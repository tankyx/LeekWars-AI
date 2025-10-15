#!/usr/bin/env python3
"""
LeekWars Fight Report Retriever
Fetches and displays fight reports from LeekWars given a fight ID
Usage: python3 lw_get_fight.py <fight_id>
"""

import requests
import json
import sys
import argparse
import re
from datetime import datetime
from html.parser import HTMLParser

BASE_URL = "https://leekwars.com"

class LeekWarsReportParser(HTMLParser):
    """Parse HTML report to extract text content"""
    def __init__(self):
        super().__init__()
        self.text = []
        self.in_action = False
        
    def handle_data(self, data):
        if data.strip():
            self.text.append(data.strip())
    
    def get_text(self):
        return '\n'.join(self.text)

class LeekWarsFightRetriever:
    def __init__(self):
        """Initialize session"""
        self.session = requests.Session()
        
    def get_fight_report(self, fight_id):
        """Fetch fight report from LeekWars"""
        url = f"{BASE_URL}/report/{fight_id}"
        
        print(f"🔍 Fetching fight report {fight_id}...")
        
        try:
            response = self.session.get(url)
            
            if response.status_code == 200:
                return response.text
            elif response.status_code == 404:
                print(f"❌ Fight {fight_id} not found")
                return None
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return None
    
    def get_fight_data(self, fight_id):
        """Fetch fight data from API"""
        url = f"{BASE_URL}/api/fight/get/{fight_id}"
        
        print(f"📊 Fetching fight data...")
        
        try:
            response = self.session.get(url)
            
            if response.status_code == 200:
                data = response.json()
                if "success" in data and data["success"]:
                    return data.get("fight", None)
            return None
                
        except:
            return None
    
    def parse_report(self, html_content, fight_id):
        """Parse the HTML report and extract battle actions"""
        if not html_content:
            return
        
        print("\n" + "="*60)
        print(f"FIGHT REPORT #{fight_id}")
        print("="*60)
        
        # Extract turn and action information using regex
        lines = []
        
        # Remove HTML tags but keep the structure
        # Look for specific patterns in the HTML
        
        # Extract turns
        turn_pattern = r'<div[^>]*class="[^"]*turn[^"]*"[^>]*>.*?Tour\s+(\d+).*?</div>'
        turns = re.finditer(turn_pattern, html_content, re.DOTALL | re.IGNORECASE)
        
        # Extract all action lines - they usually have specific classes
        action_pattern = r'<div[^>]*class="[^"]*action[^"]*"[^>]*>(.*?)</div>'
        
        # Also look for report content in general
        report_content = re.search(r'<div[^>]*class="[^"]*report[^"]*"[^>]*>(.*?)</div>', html_content, re.DOTALL)
        
        if report_content:
            content = report_content.group(1)
            
            # Parse out the actual text content
            # Remove script tags
            content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL)
            # Remove style tags
            content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL)
            
            # Extract text from divs with action information
            # Match patterns like "VirusLeek se déplace"
            movement_pattern = r'([^<>]+?)\s+se déplace\s*\((\d+)\s*PM\)'
            attack_pattern = r'([^<>]+?)\s+attaque avec\s+([^<>]+?)\s*\((\d+)\s*[PT]T\)'
            damage_pattern = r'([^<>]+?)\s+perd\s+(\d+)\s+PV'
            heal_pattern = r'([^<>]+?)\s+gagne\s+(\d+)\s+PV'
            chip_pattern = r'([^<>]+?)\s+lance\s+([^<>]+?)\s*\((\d+)\s*[PT]T\)'
            say_pattern = r'([^<>]+?)\s+dit\s*:\s*[«"]([^»"]+)[»"]'
            death_pattern = r'([^<>]+?)\s+est mort'
            critical_pattern = r'Coup critique\s*!'
            
            # Parse line by line
            lines = content.split('\n')
            current_turn = 0
            
            for line in lines:
                # Clean HTML tags
                clean_line = re.sub(r'<[^>]+>', '', line).strip()
                
                if not clean_line:
                    continue
                
                # Check for turn markers
                if 'Tour' in clean_line:
                    turn_match = re.search(r'Tour\s+(\d+)', clean_line)
                    if turn_match:
                        current_turn = int(turn_match.group(1))
                        print(f"\n📍 Turn {current_turn}")
                        print("-" * 40)
                        continue
                
                if 'Tour de' in clean_line:
                    leek_match = re.search(r'Tour de\s+(.+)', clean_line)
                    if leek_match:
                        leek_name = leek_match.group(1).strip()
                        print(f"  ▶️ {leek_name}'s turn")
                        continue
                
                # Parse actions
                move_match = re.search(movement_pattern, clean_line)
                if move_match:
                    print(f"  🏃 {move_match.group(1)} moves ({move_match.group(2)} MP)")
                    continue
                
                attack_match = re.search(attack_pattern, clean_line)
                if attack_match:
                    crit = " 💥 CRITICAL!" if re.search(critical_pattern, clean_line) else ""
                    print(f"  ⚔️ {attack_match.group(1)} attacks with {attack_match.group(2)} ({attack_match.group(3)} TP){crit}")
                    continue
                
                chip_match = re.search(chip_pattern, clean_line)
                if chip_match:
                    crit = " 💥 CRITICAL!" if re.search(critical_pattern, clean_line) else ""
                    print(f"  💊 {chip_match.group(1)} uses {chip_match.group(2)} ({chip_match.group(3)} TP){crit}")
                    continue
                
                damage_match = re.search(damage_pattern, clean_line)
                if damage_match:
                    print(f"  💔 {damage_match.group(1)} loses {damage_match.group(2)} HP")
                    continue
                
                heal_match = re.search(heal_pattern, clean_line)
                if heal_match:
                    print(f"  💚 {heal_match.group(1)} gains {heal_match.group(2)} HP")
                    continue
                
                say_match = re.search(say_pattern, clean_line)
                if say_match:
                    print(f"  💬 {say_match.group(1)} says: \"{say_match.group(2)}\"")
                    continue
                
                death_match = re.search(death_pattern, clean_line)
                if death_match:
                    print(f"  ☠️ {death_match.group(1)} dies!")
                    continue
                
                # Debug log lines
                if '[' in clean_line and ']' in clean_line:
                    debug_match = re.search(r'\[([^\]]+)\]\s*(.*)', clean_line)
                    if debug_match:
                        leek = debug_match.group(1)
                        message = debug_match.group(2)
                        print(f"  🐛 [{leek}] {message}")
                        continue
                
                # If we couldn't parse it but it has content, show it raw
                if len(clean_line) > 3 and not clean_line.startswith('function') and not clean_line.startswith('var'):
                    # Skip JavaScript code
                    if not any(x in clean_line for x in ['()', '{', '}', ';', '=', 'if', 'for', 'while']):
                        print(f"  ℹ️ {clean_line}")
        else:
            print("❌ Could not find report content in HTML")
    
    def extract_json_from_html(self, html_content):
        """Try to extract JSON data embedded in the HTML"""
        # Look for fight data in script tags
        json_pattern = r'<script[^>]*>.*?fight\s*=\s*({.*?});.*?</script>'
        match = re.search(json_pattern, html_content, re.DOTALL)
        
        if match:
            try:
                fight_data = json.loads(match.group(1))
                return fight_data
            except:
                pass
        
        # Alternative pattern
        json_pattern2 = r'var\s+fight\s*=\s*({.*?});'
        match2 = re.search(json_pattern2, html_content, re.DOTALL)
        
        if match2:
            try:
                fight_data = json.loads(match2.group(1))
                return fight_data
            except:
                pass
        
        return None
    
    def save_report(self, content, fight_id, format='txt'):
        """Save report to file"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        if format == 'html':
            filename = f"fight_{fight_id}_{timestamp}.html"
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
        else:
            filename = f"fight_{fight_id}_{timestamp}.txt"
            # Extract text from HTML
            parser = LeekWarsReportParser()
            parser.feed(content)
            text = parser.get_text()
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(text)
        
        print(f"\n💾 Report saved to {filename}")
        return filename

def main():
    parser = argparse.ArgumentParser(
        description='LeekWars Fight Report Retriever',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 lw_get_fight.py 12345678
  python3 lw_get_fight.py 12345678 --save
  python3 lw_get_fight.py 12345678 --save-html
  python3 lw_get_fight.py 12345678 --raw
        """
    )
    
    parser.add_argument('fight_id', type=int, help='The fight ID to retrieve')
    parser.add_argument('--save', action='store_true', help='Save report to text file')
    parser.add_argument('--save-html', action='store_true', help='Save raw HTML report')
    parser.add_argument('--raw', action='store_true', help='Display raw HTML')
    parser.add_argument('--api', action='store_true', help='Also fetch data from API')
    
    args = parser.parse_args()
    
    retriever = LeekWarsFightRetriever()
    
    # Get fight report
    report = retriever.get_fight_report(args.fight_id)
    
    if not report:
        print("\n❌ Could not retrieve fight report")
        return 1
    
    if args.raw:
        print(report)
    else:
        # Parse and display
        retriever.parse_report(report, args.fight_id)
        
        # Try to extract embedded JSON
        fight_data = retriever.extract_json_from_html(report)
        if fight_data:
            print("\n📊 Found embedded fight data")
            if "winner" in fight_data:
                winner = fight_data["winner"]
                print(f"🏆 Winner: Team {winner + 1}" if winner >= 0 else "🏆 Draw")
    
    # Get additional data from API if requested
    if args.api:
        print("\n" + "="*60)
        print("API DATA")
        print("="*60)
        api_data = retriever.get_fight_data(args.fight_id)
        if api_data:
            print(json.dumps(api_data, indent=2))
    
    # Save if requested
    if args.save:
        retriever.save_report(report, args.fight_id, 'txt')
    
    if args.save_html:
        retriever.save_report(report, args.fight_id, 'html')
    
    return 0

if __name__ == "__main__":
    exit(main())