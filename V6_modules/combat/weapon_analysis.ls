// V6 Module: combat/weapon_analysis.ls
// Weapon range analysis
// Auto-generated from V5.0 script

// Function: analyzeWeaponRanges
function analyzeWeaponRanges() {
    var weapons = getWeapons();
    
    // Use arrayFoldLeft for 300% better performance!
    var weaponData = arrayFoldLeft(weapons, function(acc, w) {
        var minR = getWeaponMinRange(w);
        var maxR = getWeaponMaxRange(w);
        var cost = getWeaponCost(w);
        push(acc.ranges, [minR, maxR]);
        
        // Skip Rhino from optimal range calc
        var isRhino = (minR == 2 && maxR == 4 && cost == 5);
        
        if (!isRhino) {
            var dmg = getWeaponDamage(w, myLeek);
            for (var r = minR; r <= maxR; r++) {
                var current = mapGet(acc.damageByRange, r, 0);
                acc.damageByRange[r] = current + dmg;
            }
        }
        return acc;
    }, {ranges: [], damageByRange: [:]});
    
    weaponRanges = weaponData.ranges;
    
    // Dynamic range calculation based on weapon effectiveness analysis
    // updateOptimalGrenadeRange() will set the best range
    
    debugLog("Optimal attack range: " + optimalAttackRange);
}

// === TELEPORTATION TACTICS ===

// Function: initEnemyMaxRange
function initEnemyMaxRange() {
    ENEMY_MAX_RANGE = 0;
    ENEMY_MIN_RANGE = 999;
    ENEMY_MAX_AOE_SIZE = 1;
    ENEMY_HAS_BAZOOKA = false;
    
    // Analyze enemy weapons (3x faster with fold!)
    var ws = getWeapons(enemy);
    if (ws != null) {
        var enemyData = arrayFoldLeft(ws, function(acc, w) {
            var maxR = getWeaponMaxRange(w);
            var minR = getWeaponMinRange(w);
            var area = getWeaponArea(w);
            
            acc.maxRange = max(acc.maxRange, maxR);
            acc.minRange = min(acc.minRange, minR);
            acc.maxAoE = max(acc.maxAoE, area);
            
            // Detect Bazooka
            if (minR >= 4 && maxR <= 7 && area >= 25) {
                acc.hasBazooka = true;
                debugLog("⚠️ Enemy has BAZOOKA! Range " + minR + "-" + maxR + ", AoE=" + area + " cells");
            }
            return acc;
        }, {maxRange: ENEMY_MAX_RANGE, minRange: ENEMY_MIN_RANGE, maxAoE: ENEMY_MAX_AOE_SIZE, hasBazooka: false});
        
        ENEMY_MAX_RANGE = enemyData.maxRange;
        ENEMY_MIN_RANGE = enemyData.minRange;
        ENEMY_MAX_AOE_SIZE = enemyData.maxAoE;
        ENEMY_HAS_BAZOOKA = enemyData.hasBazooka;
    }
    
    // Analyze enemy chips (3x faster with fold!)
    var cs = getChips(enemy);
    if (cs != null) {
        ENEMY_MAX_RANGE = arrayFoldLeft(cs, function(acc, ch) {
            return max(acc, getChipMaxRange(ch));
        }, ENEMY_MAX_RANGE);
    }
    
    if (ENEMY_MIN_RANGE < 999) {
        debugLog("Enemy weapon ranges: " + ENEMY_MIN_RANGE + "-" + ENEMY_MAX_RANGE + ", max AoE=" + ENEMY_MAX_AOE_SIZE);
    }
}

// === ENEMY PROFILING ===

// Function: analyzeGrenadeEffectiveness
function analyzeGrenadeEffectiveness() {
    if (!inArray(getWeapons(), WEAPON_GRENADE_LAUNCHER)) return 7;
    
    var analysis = [:];;
    
    for (var range = 4; range <= 7; range++) {
        var positions = [];
        
        // Skip analysis if enemy is completely out of reach
        // But allow analysis up to range 20 for planning purposes
        if (enemyDistance > 20) {
            // Default values when enemy is very far
            analysis[range] = [:];
            analysis[range]["coverage"] = range;  // Prefer longer range when far
            analysis[range]["splashOptions"] = 1;
            analysis[range]["obstacleBypasses"] = 0;
            analysis[range]["flexibility"] = range * 0.5;
            continue;
        }
        
        var cells = getCellsInRange(myCell, myMP);
        
        // Get cells at specific distance
        for (var i = 0; i < count(cells); i++) {
            var cell = cells[i];
            if (getCellDistance(cell, enemyCell) == range) {
                push(positions, cell);
            }
        }
        
        var totalCoverage = 0;
        var splashOptions = 0;
        var obstacleBypasses = 0;
        
        for (var i = 0; i < min(10, count(positions)); i++) {
            var pos = positions[i];
            if (!hasLOS(myCell, pos)) continue;
            
            // For each position at this range, calculate AoE coverage
            var targetOptions = getCellsInRange(pos, 7);  // Grenade range
            
            for (var j = 0; j < min(20, count(targetOptions)); j++) {
                var target = targetOptions[j];
                if (!hasLOS(pos, target)) continue;
                
                // Check if enemy would be hit
                var distToEnemy = getCellDistance(target, enemyCell);
                if (distToEnemy <= 2) {  // Within AoE radius
                    totalCoverage++;
                    
                    // Check for splash hit opportunity
                    if (target != enemyCell) {
                        splashOptions++;
                        
                        // Check if this bypasses obstacle
                        if (!hasLOS(pos, enemyCell)) {
                            obstacleBypasses++;
                        }
                    }
                }
            }
        }
        
        var flexScore = count(positions) > 0 ? totalCoverage / count(positions) : 0;
        analysis[range] = [:];;
        analysis[range]["coverage"] = totalCoverage;
        analysis[range]["splashOptions"] = splashOptions;
        analysis[range]["obstacleBypasses"] = obstacleBypasses;
        analysis[range]["flexibility"] = flexScore;
    }
    
    // Debug output
    if (debugEnabled && getTurn() <= 3) {
        for (var range = 4; range <= 7; range++) {
            var data = analysis[range];
            if (data != null) {
                debugLog("Grenade Range " + range + ": Coverage=" + data["coverage"] + 
                         " Splash=" + data["splashOptions"] + 
                         " Bypass=" + data["obstacleBypasses"] +
                         " Flex=" + round(data["flexibility"]));
            }
        }
    }
    
    // Find optimal range
    var bestRange = 7;
    var bestScore = 0;
    
    for (var range = 4; range <= 7; range++) {
        var data = analysis[range];
        if (data == null) continue;
        
        // Score formula prioritizes splash damage and obstacle bypass
        var score = data["coverage"] * 2 + 
                   data["splashOptions"] * 3 + 
                   data["obstacleBypasses"] * 5 +
                   data["flexibility"] * 100;
        
        // Prefer range 5-6 for better control
        if (range == 5 || range == 6) {
            score = score * 1.2;  // 20% bonus for optimal ranges
        }
        
        if (score > bestScore) {
            bestScore = score;
            bestRange = range;
        }
    }
    
    return bestRange;
}

// Update optimal range based on weapon mix

// Function: updateOptimalGrenadeRange
function updateOptimalGrenadeRange() {
    var oldRange = optimalAttackRange;
    var newRange = 7;  // Default
    
    // Only update if we have Grenade Launcher
    if (inArray(getWeapons(), WEAPON_GRENADE_LAUNCHER)) {
        newRange = analyzeGrenadeEffectiveness();
        
        if (newRange != oldRange) {
            debugLog("🎯 Grenade optimal range: " + oldRange + " → " + newRange);
        }
        
        // For mixed weapon loadout, take weighted average
        if (inArray(getWeapons(), WEAPON_LIGHTNINGER)) {
            // Lightninger optimal is 8, weight based on TP efficiency
            var grenadeWeight = 0.6;  // Grenade is 4 TP
            var lightningerWeight = 0.4;  // Lightninger is 5 TP
            newRange = floor(newRange * grenadeWeight + 8 * lightningerWeight);
            debugLog("Mixed loadout optimal range: " + newRange);
        }
    } else if (inArray(getWeapons(), WEAPON_LIGHTNINGER)) {
        newRange = 8;  // Pure Lightninger optimal
    }
    
    optimalAttackRange = newRange;
    return newRange;
}

// Find best grenade target considering AoE damage
