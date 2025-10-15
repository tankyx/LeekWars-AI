#!/usr/bin/env python3
"""
LeekWars AI Uploader using session cookies
"""

import requests
import json
from getpass import getpass
from config_loader import load_credentials

BASE_URL = "https://leekwars.com/api"

# Full optimized script (fixed for LeekScript - no scope issues)
OPTIMIZED_SCRIPT = """
// Smart Tank AI v3 - Optimized with key fixes
// Core improvements: TP budgeting, smarter targeting, better positioning

// ========== TARGET SELECTION ==========
function getBestTarget() {
    var enemies = getAliveEnemies();
    if (count(enemies) == 0) return null;
    if (count(enemies) == 1) return enemies[0];
    
    var best = null;
    var bestScore = -9999;
    
    for (var i = 0; i < count(enemies); i++) {
        var e = enemies[i];
        var hp = getLife(e);
        var dist = getCellDistance(getCell(), getCell(e));
        var los = lineOfSight(getCell(), getCell(e));
        
        // Prioritize: can hit > low HP > close
        var score = 0;
        if (los && dist <= 8) score = 1000 - hp;  // Can attack now
        else if (dist <= 10) score = 500 - hp;     // Can reach this turn
        else score = 100 - hp - dist * 10;         // Too far
        
        if (score > bestScore) {
            bestScore = score;
            best = e;
        }
    }
    return best;
}

// ========== TP BUDGET CALCULATION ==========
function getAttackTPNeeded(dist, los, aligned) {
    if (!los) return 3;  // Spark only
    if (aligned && dist <= 8) return 10;  // J-Laser + B-Laser
    if (dist <= 6) return 6;  // Destroyer
    return 3;  // Spark fallback
}

// ========== POSITION SCORING ==========
function scorePosition(cell, enemyCell, tpAvailable) {
    var dist = getCellDistance(cell, enemyCell);
    var los = lineOfSight(cell, enemyCell);
    if (!los) return -1;  // No LoS = bad
    
    var aligned = (getCellX(cell) == getCellX(enemyCell) || 
                   getCellY(cell) == getCellY(enemyCell));
    
    // Base score on expected damage output
    var score = 0;
    if (aligned && dist <= 8) {
        var laserShots = min(3, floor(max(0, tpAvailable - 5) / 5) + 1);
        score = 100 + laserShots * 60;  // High value for laser position
    } else if (dist <= 6) {
        var destroyerShots = min(2, floor(tpAvailable / 6));
        score = 50 + destroyerShots * 50;
    } else {
        score = 10;  // At least has LoS
    }
    
    // Prefer optimal range (6-8 for safety)
    if (dist >= 6 && dist <= 8) score += 20;
    
    return score;
}

// ========== MAIN AI LOOP ==========
var enemy = getBestTarget();
if (enemy == null) {
    moveTowardCell(getCellFromXY(17, 17));  // Center map
} else {
    // Cache all position data once
    var enemyCell = getCell(enemy);
    var myCell = getCell();
    var dist = getCellDistance(myCell, enemyCell);
    var los = lineOfSight(myCell, enemyCell);
    var aligned = (getCellX(myCell) == getCellX(enemyCell) || 
                   getCellY(myCell) == getCellY(enemyCell));
    var myHP = getLife();
    var hpPercent = (myHP * 100) / getTotalLife();
    var enemyHP = getLife(enemy);
    
    debugW("T" + getTurn() + " Enemy:" + enemyHP + "hp@" + dist + " Me:" + floor(hpPercent) + "%");
    
    // ========== EMERGENCY HEALING ==========
    if (hpPercent < 30) {
        if (getCooldown(CHIP_CURE) == 0) useChip(CHIP_CURE);
        if (getCooldown(CHIP_SHIELD) == 0) useChip(CHIP_SHIELD);
        if (getCooldown(CHIP_HELMET) == 0) useChip(CHIP_HELMET);
        // No Wall - can block our own attacks
    }
    
    // ========== MOVEMENT PHASE ==========
    var moved = false;
    
    // Too far? Move closer
    if (dist > 8 && getMP() > 0) {
        // Use Leather Boots if needed to reach attack range
        if ((dist - getMP()) > 8 && getCooldown(CHIP_LEATHER_BOOTS) == 0) {
            useChip(CHIP_LEATHER_BOOTS);
        }
        moveTowardCell(enemyCell);
        moved = true;
    }
    // Need LoS? Find best firing position
    else if (!los && dist <= 12 && getMP() > 0) {
        var bestCell = null;
        var bestScore = -9999;
        var tpAfterMove = getTP() - (getWeapon() != WEAPON_B_LASER ? 1 : 0);
        
        // Search reachable cells for best position
        for (var dx = -getMP(); dx <= getMP(); dx++) {
            for (var dy = -getMP(); dy <= getMP(); dy++) {
                if (abs(dx) + abs(dy) > getMP()) continue;
                
                var cell = getCellFromXY(getCellX(myCell) + dx, getCellY(myCell) + dy);
                if (cell == null || getCellContent(cell) != CELL_EMPTY) continue;
                
                var pathLen = getPathLength(myCell, cell);
                if (pathLen == null || pathLen > getMP()) continue;
                
                var score = scorePosition(cell, enemyCell, tpAfterMove);
                if (score > bestScore) {
                    bestScore = score;
                    bestCell = cell;
                }
            }
        }
        
        if (bestCell != null) {
            moveTowardCell(bestCell);
            moved = true;
        }
    }
    
    // Update state after movement
    if (moved) {
        dist = getCellDistance(getCell(), enemyCell);
        los = lineOfSight(getCell(), enemyCell);
        aligned = (getCellX(getCell()) == getCellX(enemyCell) || 
                   getCellY(getCell()) == getCellY(enemyCell));
    }
    
    // ========== CALCULATE TP BUDGET ==========
    var attackTPNeeded = getAttackTPNeeded(dist, los, aligned);
    
    // ========== BUFFS (WITH TP BUDGET) ==========
    if (hpPercent > 40 && los) {
        // Covetousness first (generates TP)
        if (getCooldown(CHIP_COVETOUSNESS) == 0 && getTP() >= attackTPNeeded + 4 && dist <= 8) {
            useChip(CHIP_COVETOUSNESS, enemy);
        }
        // Only buff if we have spare TP
        if (getCooldown(CHIP_STEROID) == 0 && getTP() >= attackTPNeeded + 8) {
            useChip(CHIP_STEROID);
        }
        if (getCooldown(CHIP_PROTEIN) == 0 && getTP() >= attackTPNeeded + 3) {
            useChip(CHIP_PROTEIN);
        }
    }
    
    // ========== COMBAT PHASE ==========
    var totalDamage = 0;
    var killThreshold = enemyHP + 50;  // Account for shields
    
    if (aligned && los && dist <= 9) {
        // === LASER COMBO ===
        var currentWeapon = getWeapon();
        
        if (dist == 9) {
            // Only J-Laser reaches
            if (currentWeapon != WEAPON_J_LASER) setWeapon(WEAPON_J_LASER);
            while (getTP() >= 5 && totalDamage < killThreshold) {
                if (useWeapon(enemy) != USE_SUCCESS) break;
                totalDamage += 51;
            }
        } else {
            // J-Laser for debuff if we have TP for combo
            if (getTP() >= 10 && currentWeapon != WEAPON_J_LASER) {
                setWeapon(WEAPON_J_LASER);
                if (useWeapon(enemy) == USE_SUCCESS) {
                    totalDamage += 51;
                }
            }
            
            // B-Laser for damage (or lifesteal if low HP)
            if (getTP() >= 5) {
                if (currentWeapon != WEAPON_B_LASER && getTP() >= 6) {
                    setWeapon(WEAPON_B_LASER);
                }
                if (getWeapon() == WEAPON_B_LASER) {
                    while (getTP() >= 5 && totalDamage < killThreshold) {
                        if (useWeapon(enemy) != USE_SUCCESS) break;
                        totalDamage += 55;  // More if debuffed, but simplified
                    }
                }
            }
        }
    } else if (los && dist <= 6) {
        // === DESTROYER MODE ===
        if (getWeapon() != WEAPON_DESTROYER && getTP() >= 7) {
            setWeapon(WEAPON_DESTROYER);
        }
        if (getWeapon() == WEAPON_DESTROYER) {
            while (getTP() >= 6 && totalDamage < killThreshold) {
                if (useWeapon(enemy) != USE_SUCCESS) break;
                totalDamage += 50;
            }
        }
    }
    
    // === DAMAGE CHIPS ===
    if (los && totalDamage < killThreshold) {
        if (dist <= 7 && getCooldown(CHIP_STALACTITE) == 0 && getTP() >= 6) {
            if (useChip(CHIP_STALACTITE, enemy) == USE_SUCCESS) {
                totalDamage += 65;
            }
        }
        if (dist <= 7 && getCooldown(CHIP_ROCKFALL) == 0 && getTP() >= 5) {
            if (useChip(CHIP_ROCKFALL, enemy) == USE_SUCCESS) {
                totalDamage += 55;
            }
        }
        if (getCooldown(CHIP_FLASH) == 0 && getTP() >= 3 && dist <= 10) {
            if (useChip(CHIP_FLASH, enemy) == USE_SUCCESS) {
                totalDamage += 30;
            }
        }
    }
    
    // === SPARK (last resort or finisher) ===
    if (dist <= 10 && getTP() >= 3 && getCooldown(CHIP_SPARK) == 0) {
        if (totalDamage + 20 >= enemyHP || (!los && totalDamage == 0)) {
            useChip(CHIP_SPARK, enemy);
        }
    }
    
    // ========== DEFENSIVE (only if couldn't kill) ==========
    if (totalDamage < enemyHP && hpPercent < 60 && getTP() >= 3) {
        if (getCooldown(CHIP_SHIELD) == 0) useChip(CHIP_SHIELD);
        else if (getCooldown(CHIP_HELMET) == 0) useChip(CHIP_HELMET);
    }
    
    // ========== POST-COMBAT REPOSITIONING ==========
    // Try to align for next turn if we have MP and it helps
    if (getMP() > 0 && !aligned && dist <= 10) {
        var bestCell = null;
        var bestNextTurnScore = 0;
        
        // Quick check for alignment moves
        for (var i = -getMP(); i <= getMP(); i++) {
            if (i == 0) continue;
            
            var cells = [
                getCellFromXY(getCellX(getCell()) + i, getCellY(getCell())),
                getCellFromXY(getCellX(getCell()), getCellY(getCell()) + i)
            ];
            
            for (var c = 0; c < 2; c++) {
                var cell = cells[c];
                if (cell == null || getCellContent(cell) != CELL_EMPTY) continue;
                if (getPathLength(getCell(), cell) > getMP()) continue;
                
                var newDist = getCellDistance(cell, enemyCell);
                if (newDist >= 6 && newDist <= 8 && lineOfSight(cell, enemyCell)) {
                    bestCell = cell;
                    break;
                }
            }
            if (bestCell != null) break;
        }
        
        if (bestCell != null) {
            moveTowardCell(bestCell);
        }
    }
}
"""

class LeekWarsSession:
    def __init__(self):
        # Use a session to maintain cookies
        self.session = requests.Session()
        self.farmer_id = None
        self.leeks = {}
        
    def login(self, email, password):
        """Login and maintain session cookies"""
        print("🔐 Logging in...")
        
        login_url = f"{BASE_URL}/farmer/login-token"
        login_data = {
            "login": email,
            "password": password
        }
        
        # Login - this sets cookies in the session
        response = self.session.post(login_url, data=login_data)
        
        if response.status_code == 200:
            data = response.json()
            
            if "farmer" in data:
                farmer = data["farmer"]
                self.farmer_id = farmer.get("id")
                farmer_name = farmer.get("login")
                
                # Store leeks
                if "leeks" in farmer:
                    self.leeks = farmer["leeks"]
                    print(f"✅ Logged in as {farmer_name}")
                    print(f"   Session cookies set")
                    print(f"   Found {len(self.leeks)} leek(s)")
                    
                    # Debug: Show cookies
                    print(f"   Cookies: {list(self.session.cookies.keys())}")
                    
                    return True
                    
        print("❌ Login failed")
        return False
    
    def save_ai(self, ai_id, code):
        """Save AI using session cookies (no token in request)"""
        print(f"\n📤 Saving to AI #{ai_id}...")
        
        url = f"{BASE_URL}/ai/save"
        
        # Don't include token - use session cookies
        save_data = {
            "ai_id": str(ai_id),
            "code": code
        }
        
        # The session has cookies from login
        response = self.session.post(url, data=save_data)
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                data = response.json()
                
                # Save full response to file for debugging
                with open("leekwars_response.json", "w") as f:
                    json.dump(data, f, indent=2)
                print("   📁 Full response saved to: leekwars_response.json")
                
                # Also save just the result/errors to a separate file
                if "result" in data:
                    with open("compilation_result.json", "w") as f:
                        json.dump(data["result"], f, indent=2)
                    print("   📁 Compilation result saved to: compilation_result.json")
                
                print(f"   Response: {json.dumps(data, indent=2)[:500]}")
                
                # Check different possible success indicators
                if data.get("success") == True:
                    print("✅ Script saved successfully!")
                    
                    if "result" in data:
                        result = data["result"]
                        print(f"   Lines: {result.get('lines', 'N/A')}")
                        print(f"   Characters: {result.get('chars', 'N/A')}")
                        
                        if result.get("errors"):
                            print("⚠️ Compilation errors:")
                            for error in result["errors"]:
                                print(f"   - {error}")
                            
                            # Save errors to separate file
                            with open("compilation_errors.txt", "w") as f:
                                f.write("Compilation Errors:\n")
                                f.write("==================\n\n")
                                for error in result["errors"]:
                                    f.write(f"- {error}\n")
                            print("   📁 Errors saved to: compilation_errors.txt")
                                
                    return True
                elif "result" in data:
                    # Sometimes success is indicated by presence of result
                    result = data["result"]
                    print("✅ Script compiled and saved!")
                    print(f"   Lines: {result.get('lines', 'N/A')}")
                    print(f"   Characters: {result.get('chars', 'N/A')}")
                    
                    if result.get("errors"):
                        print("⚠️ Compilation errors:")
                        for error in result["errors"]:
                            print(f"   - {error}")
                            
                        # Save errors to separate file
                        with open("compilation_errors.txt", "w") as f:
                            f.write("Compilation Errors:\n")
                            f.write("==================\n\n")
                            for error in result["errors"]:
                                f.write(f"- {error}\n")
                        print("   📁 Errors saved to: compilation_errors.txt")
                    else:
                        print("   No compilation errors")
                            
                    return True
                elif "ai" in data:
                    # Sometimes it returns the AI object
                    print("✅ Script saved (AI object returned)")
                    return True
                else:
                    print(f"❓ Unexpected response format")
                    print(f"   Keys in response: {list(data.keys())}")
                    
                    # If no error field, might still be success
                    if "error" not in data:
                        print("✅ Assuming success (no error in response)")
                        return True
                    else:
                        print(f"❌ Error: {data.get('error')}")
                        return False
                        
            except json.JSONDecodeError:
                print(f"   Response was not JSON: {response.text[:200]}")
                # Save raw response
                with open("leekwars_response_raw.txt", "w") as f:
                    f.write(response.text)
                print("   📁 Raw response saved to: leekwars_response_raw.txt")
                return False
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            
        return False
    
    def get_ai(self, ai_id):
        """Get AI details using session"""
        url = f"{BASE_URL}/ai/get/{ai_id}"
        response = self.session.get(url)
        
        if response.status_code == 200:
            return response.json()
        return None
    
    def create_ai(self):
        """Create new AI using session"""
        url = f"{BASE_URL}/ai/new"
        data = {
            "folder_id": 0,
            "v2": 1
        }
        
        response = self.session.post(url, data=data)
        
        if response.status_code == 200:
            result = response.json()
            if "ai" in result:
                new_id = result["ai"]["id"]
                print(f"✅ Created new AI #{new_id}")
                return new_id
                
        print("❌ Failed to create AI")
        return None

def main():
    print("=== LeekWars Cookie-Based Uploader ===\n")
    
    # Create session
    lw = LeekWarsSession()
    
    # Login
    email, password = load_credentials()  # Changed from input prompt
    password = getpass("Password: ")
    
    if not lw.login(email, password):
        print("Failed to login")
        return 1
    
    # Get first leek
    if not lw.leeks:
        print("No leeks found")
        return 1
    
    leek_data = list(lw.leeks.values())[0]
    leek_name = leek_data.get("name")
    ai_id = leek_data.get("ai")
    
    print(f"\n📋 Selected leek: {leek_name}")
    print(f"   Level: {leek_data.get('level')}")
    print(f"   Stats: {leek_data.get('strength')} STR, {leek_data.get('tp')} TP")
    
    if not ai_id:
        print("⚠️ No AI assigned, creating new one...")
        ai_id = lw.create_ai()
        if not ai_id:
            return 1
    else:
        print(f"   AI ID: {ai_id}")
    
    # Save the full optimized script
    print("\n📝 Using full optimized combat script...")
    
    code = OPTIMIZED_SCRIPT
    
    if lw.save_ai(ai_id, code):
        print("\n🎉 Success! Your AI has been updated with the optimized script.")
        print("You can now test it in battles!")
        return 0
    else:
        print("\n❌ Failed to save AI")
        return 1

if __name__ == "__main__":
    exit(main())
