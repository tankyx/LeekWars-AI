// V6 Module: strategy/multi_enemy.ls
// Multi-enemy target selection and management

// Global variables for multi-enemy tracking
global allEnemies = [];        // Array of all alive enemies
global primaryTarget = null;   // Primary target for focused fire
global secondaryTargets = [];  // Other enemies to consider for AoE

// Function: initializeEnemies
function initializeEnemies() {
    // Get all alive enemies
    enemies = getAliveEnemies();
    allEnemies = [];
    
    for (var i = 0; i < count(enemies); i++) {
        var e = enemies[i];
        var enemyData = [:];
        enemyData["entity"] = e;
        enemyData["cell"] = getCell(e);
        enemyData["hp"] = getLife(e);
        enemyData["maxHP"] = getTotalLife(e);
        enemyData["tp"] = getTP(e);
        enemyData["mp"] = getMP(e);
        enemyData["distance"] = getCellDistance(myCell, getCell(e));
        enemyData["strength"] = getStrength(e);
        enemyData["agility"] = getAgility(e);
        enemyData["science"] = getScience(e);
        enemyData["magic"] = getMagic(e);
        enemyData["absShield"] = getAbsoluteShield(e);
        enemyData["relShield"] = getRelativeShield(e);
        enemyData["threat"] = calculateThreatLevel(e);
        enemyData["killable"] = isKillable(e);
        push(allEnemies, enemyData);
    }
    
    // Sort by threat level (highest first)
    allEnemies = arraySort(allEnemies, function(a, b) {
        return b["threat"] - a["threat"];
    });
    
    // Set primary target
    selectPrimaryTarget();
    
    // Maintain backward compatibility with single enemy variable
    if (primaryTarget != null) {
        enemy = primaryTarget["entity"];
        enemyCell = primaryTarget["cell"];
        enemyHP = primaryTarget["hp"];
        enemyMaxHP = primaryTarget["maxHP"];
        enemyTP = primaryTarget["tp"];
        enemyMP = primaryTarget["mp"];
        enemyDistance = primaryTarget["distance"];
        enemyStrength = primaryTarget["strength"];
        enemyAgility = primaryTarget["agility"];
        enemyScience = primaryTarget["science"];
        enemyMagic = primaryTarget["magic"];
    }
}

// Function: selectPrimaryTarget
function selectPrimaryTarget() {
    if (count(allEnemies) == 0) {
        primaryTarget = null;
        return;
    }
    
    // Single enemy - simple choice
    if (count(allEnemies) == 1) {
        primaryTarget = allEnemies[0];
        secondaryTargets = [];
        return;
    }
    
    // Multiple enemies - smart target selection
    var bestTarget = null;
    var bestScore = -999999;
    
    for (var i = 0; i < count(allEnemies); i++) {
        var e = allEnemies[i];
        var score = 0;
        
        // Priority 1: Can we kill them this turn?
        if (e["killable"]) {
            score += 10000;
            // Prefer killing weaker enemies first (easier to reduce enemy count)
            score += (1000 - e["hp"]);
        }
        
        // Priority 2: Low HP enemies (finish them off)
        var hpPercent = e["hp"] / e["maxHP"];
        if (hpPercent < 0.3) {
            score += 5000;
        } else if (hpPercent < 0.5) {
            score += 3000;
        }
        
        // Priority 3: High threat enemies
        score += e["threat"] * 100;
        
        // Priority 4: Closer enemies (easier to hit)
        score -= e["distance"] * 50;
        
        // Priority 5: Enemies we have good weapons for
        if (e["distance"] >= 7 && e["distance"] <= 9) {
            score += 500;  // Rifle range
        } else if (e["distance"] >= 5 && e["distance"] <= 12 && isOnSameLine(myCell, e["cell"])) {
            score += 400;  // M-Laser range
        }
        
        // Penalty: Heavily shielded enemies
        if (e["absShield"] > 200 || e["relShield"] > 30) {
            score -= 1000;
        }
        
        if (score > bestScore) {
            bestScore = score;
            bestTarget = e;
        }
    }
    
    primaryTarget = bestTarget;
    
    // Set secondary targets (everyone except primary)
    secondaryTargets = [];
    for (var i = 0; i < count(allEnemies); i++) {
        if (allEnemies[i] != primaryTarget) {
            push(secondaryTargets, allEnemies[i]);
        }
    }
}

// Function: calculateThreatLevel
function calculateThreatLevel(e) {
    var threat = 0;
    
    // Base threat from stats
    threat += getStrength(e) * 2;     // Strength is most dangerous
    threat += getMagic(e) * 1.5;      // Magic damage is hard to defend
    threat += getAgility(e) * 1;      // Agility for crit chance
    threat += getScience(e) * 0.5;    // Science for poison/debuffs
    
    // Distance modifier (closer = more threatening)
    var dist = getCellDistance(myCell, getCell(e));
    if (dist <= 7) {
        threat *= 2;  // Can attack us immediately
    } else if (dist <= 13) {
        threat *= 1.5;  // Can reach us next turn
    }
    
    // HP modifier (healthy enemies are more threatening)
    var hpPercent = getLife(e) / getTotalLife(e);
    threat *= hpPercent;
    
    return threat;
}

// Function: isKillable
function isKillable(e) {
    // Calculate our maximum damage potential this turn
    var maxDamage = 0;
    var dist = getCellDistance(myCell, getCell(e));
    var hasLine = hasLOS(myCell, getCell(e));
    
    // Check weapon damage
    var weapons = getWeapons();
    for (var i = 0; i < count(weapons); i++) {
        var w = weapons[i];
        var minR = getWeaponMinRange(w);
        var maxR = getWeaponMaxRange(w);
        
        if (dist >= minR && dist <= maxR && (!weaponNeedLos(w) || hasLine)) {
            var dmg = getWeaponDamage(w, myLeek);
            var cost = getWeaponCost(w);
            var uses = floor(myTP / cost);
            
            // Special case for line weapons
            if (w == WEAPON_M_LASER && !isOnSameLine(myCell, getCell(e))) {
                continue;
            }
            
            maxDamage = max(maxDamage, dmg * uses);
        }
    }
    
    // Add chip damage
    if (myTP >= 4 && dist <= 10 && hasLine) {
        maxDamage += 120;  // Lightning chip estimate
    }
    
    // Check if we can kill considering shields
    var effectiveHP = getLife(e) + getAbsoluteShield(e);
    effectiveHP *= (1 + getRelativeShield(e) / 100);
    
    return maxDamage >= effectiveHP;
}

// Function: shouldSwitchTarget
function shouldSwitchTarget() {
    // Don't switch if no primary target
    if (primaryTarget == null) return false;
    
    // Don't switch in 1v1
    if (count(allEnemies) <= 1) return false;
    
    // Check if we should switch targets
    var shouldSwitch = false;
    
    // Switch if current target is dead
    if (primaryTarget["hp"] <= 0) {
        shouldSwitch = true;
    }
    
    // Switch if a new enemy became killable
    for (var i = 0; i < count(allEnemies); i++) {
        var e = allEnemies[i];
        if (e != primaryTarget && e["killable"] && !primaryTarget["killable"]) {
            shouldSwitch = true;
            break;
        }
    }
    
    // Switch if current target is too far and another is much closer
    if (primaryTarget["distance"] > 15) {
        for (var i = 0; i < count(allEnemies); i++) {
            var e = allEnemies[i];
            if (e["distance"] < primaryTarget["distance"] - 8) {
                shouldSwitch = true;
                break;
            }
        }
    }
    
    if (shouldSwitch) {
        selectPrimaryTarget();
        return true;
    }
    
    return false;
}

// Function: getBestAoETarget
function getBestAoETarget(weapon) {
    // Find the best cell to hit multiple enemies with AoE weapons
    if (count(allEnemies) <= 1) {
        return primaryTarget != null ? primaryTarget["cell"] : null;
    }
    
    var bestCell = null;
    var bestScore = 0;
    var myPos = getCell();
    
    // Get weapon range
    var minRange = getWeaponMinRange(weapon);
    var maxRange = getWeaponMaxRange(weapon);
    
    // Check potential target cells in range
    var potentialTargets = getCellsInRange(myPos, maxRange);
    
    for (var i = 0; i < min(50, count(potentialTargets)); i++) {
        var targetCell = potentialTargets[i];
        var dist = getCellDistance(myPos, targetCell);
        
        // Check if we can shoot this cell
        if (dist < minRange || dist > maxRange) continue;
        if (weaponNeedLos(weapon) && !hasLOS(myPos, targetCell)) continue;
        
        var score = 0;
        var enemiesHit = 0;
        var totalDamage = 0;
        
        // Calculate damage to all enemies based on weapon type
        if (weapon == WEAPON_GRENADE_LAUNCHER) {
            // Grenade launcher has 2 cell AoE
            // Use proper damage calculation with strength scaling
            var grenadeBase = getWeaponDamage(WEAPON_GRENADE_LAUNCHER, myLeek);
            
            for (var j = 0; j < count(allEnemies); j++) {
                var e = allEnemies[j];
                var splashDist = getCellDistance(targetCell, e["cell"]);
                
                if (splashDist <= 2) {
                    var damageMultiplier = max(0, 1 - 0.2 * splashDist);
                    var damage = grenadeBase * damageMultiplier;
                    totalDamage += damage;
                    enemiesHit++;
                    
                    // Bonus for hitting low HP enemies
                    if (e["hp"] <= damage) {
                        score += 5000;  // Potential kill
                    }
                }
            }
        }
        
        // Base score from total damage
        score += totalDamage;
        
        // Massive bonus for hitting multiple enemies
        if (enemiesHit > 1) {
            score *= (1 + enemiesHit * 0.5);  // 50% bonus per additional enemy
            debugLog("Multi-hit opportunity at " + targetCell + ": " + enemiesHit + " enemies, " + totalDamage + " total damage");
        }
        
        if (score > bestScore) {
            bestScore = score;
            bestCell = targetCell;
        }
    }
    
    return bestCell;
}

// Function: getAllEnemiesInRange
function getAllEnemiesInRange(minRange, maxRange, needLOS) {
    var enemiesInRange = [];
    
    for (var i = 0; i < count(allEnemies); i++) {
        var e = allEnemies[i];
        if (e["distance"] >= minRange && e["distance"] <= maxRange) {
            if (!needLOS || hasLOS(myCell, e["cell"])) {
                push(enemiesInRange, e);
            }
        }
    }
    
    return enemiesInRange;
}

// Function: getBestLaserTarget
function getBestLaserTarget() {
    // Find best target for M-Laser to hit multiple enemies
    if (!inArray(getWeapons(), WEAPON_M_LASER) || getTP() < 8) return null;
    if (count(allEnemies) <= 1) {
        // Single enemy - just return their cell if in range
        if (primaryTarget != null) {
            var dist = primaryTarget["distance"];
            if (dist >= 5 && dist <= 12 && hasLOS(myCell, primaryTarget["cell"]) && 
                isOnSameLine(myCell, primaryTarget["cell"])) {
                return primaryTarget["cell"];
            }
        }
        return null;
    }
    
    var bestTarget = null;
    var bestScore = 0;
    var myPos = getCell();
    
    // Check each enemy as potential primary laser target
    for (var i = 0; i < count(allEnemies); i++) {
        var targetCell = allEnemies[i]["cell"];
        var dist = getCellDistance(myPos, targetCell);
        
        // Check if valid laser target
        if (dist < 5 || dist > 12) continue;
        if (!hasLOS(myPos, targetCell)) continue;
        if (!isOnSameLine(myPos, targetCell)) continue;
        
        // Count enemies in the laser line
        var enemiesHit = 0;
        var totalDamage = 0;
        var laserBase = 95;  // M-Laser average damage
        
        // Get line direction
        var fx = getCellX(myPos);
        var fy = getCellY(myPos);
        var tx = getCellX(targetCell);
        var ty = getCellY(targetCell);
        
        var dx = 0;
        var dy = 0;
        if (tx > fx) dx = 1;
        else if (tx < fx) dx = -1;
        if (ty > fy) dy = 1;
        else if (ty < fy) dy = -1;
        
        // Check all cells in the line for enemies
        var currentX = fx + dx;
        var currentY = fy + dy;
        var steps = 0;
        
        while (steps < 12) {
            var cell = getCellFromXY(currentX, currentY);
            if (cell == null || cell == -1) break;
            
            // Check if any enemy is in this cell
            for (var j = 0; j < count(allEnemies); j++) {
                if (allEnemies[j]["cell"] == cell) {
                    enemiesHit++;
                    totalDamage += laserBase;
                    
                    // Bonus for hitting low HP enemies
                    if (allEnemies[j]["hp"] <= laserBase) {
                        totalDamage += 1000;  // Potential kill bonus
                    }
                    break;
                }
            }
            
            currentX += dx;
            currentY += dy;
            steps++;
        }
        
        // Calculate score
        var score = totalDamage;
        
        // Massive bonus for multi-hits
        if (enemiesHit > 1) {
            score *= enemiesHit;  // Multiply by number of enemies hit
            debugLog("⚡ Laser can hit " + enemiesHit + " enemies in line to " + targetCell);
        }
        
        // Bonus for hitting primary target
        if (primaryTarget != null && targetCell == primaryTarget["cell"]) {
            score += 500;
        }
        
        if (score > bestScore) {
            bestScore = score;
            bestTarget = targetCell;
        }
    }
    
    return bestTarget;
}

// Function: calculateMultiHitValue
function calculateMultiHitValue(weapon, targetCell) {
    // Calculate the value of using a weapon considering multi-hit potential
    var value = 0;
    var myPos = getCell();
    
    if (weapon == WEAPON_M_LASER) {
        // Check laser multi-hit
        if (!isOnSameLine(myPos, targetCell)) return 0;
        
        // Use proper damage calculation with strength scaling
        var laserBase = getWeaponDamage(WEAPON_M_LASER, myLeek);
        var enemiesHit = 0;
        
        // Get line direction and check for enemies
        var fx = getCellX(myPos);
        var fy = getCellY(myPos);
        var tx = getCellX(targetCell);
        var ty = getCellY(targetCell);
        
        var dx = (tx > fx) ? 1 : (tx < fx) ? -1 : 0;
        var dy = (ty > fy) ? 1 : (ty < fy) ? -1 : 0;
        
        var currentX = fx + dx;
        var currentY = fy + dy;
        var steps = 0;
        
        while (steps < 12) {
            var cell = getCellFromXY(currentX, currentY);
            if (cell == null || cell == -1) break;
            
            for (var j = 0; j < count(allEnemies); j++) {
                if (allEnemies[j]["cell"] == cell) {
                    value += laserBase;
                    enemiesHit++;
                    break;
                }
            }
            
            currentX += dx;
            currentY += dy;
            steps++;
        }
        
        // Multiply value for multi-hits
        if (enemiesHit > 1) {
            value *= 1.5;  // 50% bonus for multi-hit
        }
    } else if (weapon == WEAPON_GRENADE_LAUNCHER) {
        // Check grenade AoE
        // Use proper damage calculation with strength scaling
        var grenadeBase = getWeaponDamage(WEAPON_GRENADE_LAUNCHER, myLeek);
        var enemiesHit = 0;
        
        for (var i = 0; i < count(allEnemies); i++) {
            var splashDist = getCellDistance(targetCell, allEnemies[i]["cell"]);
            if (splashDist <= 2) {
                var damageMultiplier = max(0, 1 - 0.2 * splashDist);
                value += grenadeBase * damageMultiplier;
                enemiesHit++;
            }
        }
        
        // Multiply value for multi-hits
        if (enemiesHit > 1) {
            value *= 1.5;  // 50% bonus for multi-hit
        }
    } else {
        // Single target weapons (Rifle, Dark Katana)
        // Use proper damage calculation with strength scaling
        if (weapon == WEAPON_RIFLE) {
            value = getWeaponDamage(WEAPON_RIFLE, myLeek);
        } else if (weapon == WEAPON_DARK_KATANA) {
            value = getWeaponDamage(WEAPON_DARK_KATANA, myLeek);
        }
    }
    
    return value;
}

// Function: getTotalIncomingDamage
function getTotalIncomingDamage(fromCell) {
    var totalDamage = 0;
    
    for (var i = 0; i < count(allEnemies); i++) {
        var e = allEnemies[i];
        var dist = getCellDistance(fromCell, e["cell"]);
        
        // Estimate damage based on enemy strength and distance
        if (dist <= 7) {
            // Enemy can likely attack
            totalDamage += e["strength"] * 2;  // Rough estimate
        } else if (dist <= 13) {
            // Enemy can reach us with movement
            totalDamage += e["strength"];
        }
    }
    
    return totalDamage;
}