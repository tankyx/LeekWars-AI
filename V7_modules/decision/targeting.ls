// V7 Module: decision/targeting.ls
// TTK calculation and multi-enemy target prioritization

// === TTK (TIME-TO-KILL) CALCULATION ===
function calculateTTK(enemyEntity) {
    if (enemyEntity == null || getLife(enemyEntity) <= 0) {
        return 999; // Dead or invalid enemy
    }
    
    var currentEnemyHP = getLife(enemyEntity);
    var enemyResist = getResistance(enemyEntity);
    
    // Estimate our damage per turn against this enemy
    var myDamagePerTurn = estimateDamagePerTurn(enemyEntity);
    
    if (myDamagePerTurn <= 0) {
        return 999; // Can't damage this enemy
    }
    
    // Calculate TTK accounting for resistance
    var effectiveDamage = max(1, myDamagePerTurn * (1 - enemyResist / 100));
    var ttk = ceil(currentEnemyHP / effectiveDamage);
    
    if (debugEnabled) {
        debugW("TTK[" + enemyEntity + "]: HP=" + currentEnemyHP + ", MyDmg=" + myDamagePerTurn + ", EffDmg=" + effectiveDamage + ", TTK=" + ttk);
    }
    
    return ttk;
}

// === DAMAGE PER TURN ESTIMATION ===
function estimateDamagePerTurn(enemyEntity) {
    var weapons = getWeapons();
    var availableTP = myTP;
    var totalDamage = 0;
    
    // Calculate damage from our best weapon combination
    for (var i = 0; i < count(weapons); i++) {
        var weapon = weapons[i];
        var weaponCost = getWeaponCost(weapon);
        var weaponUses = getWeaponMaxUses(weapon);
        
        if (availableTP >= weaponCost) {
            // Calculate how many times we can use this weapon
            var usesThisTurn = (weaponUses > 0) ? min(weaponUses, floor(availableTP / weaponCost)) : floor(availableTP / weaponCost);
            
            // Estimate damage per use
            var damagePerUse = estimateWeaponDamage(weapon, enemyEntity);
            var weaponTotalDamage = damagePerUse * usesThisTurn;
            
            totalDamage += weaponTotalDamage;
            availableTP -= (weaponCost * usesThisTurn);
        }
    }
    
    // Add chip damage if available
    var chipDamage = estimateChipDamage(enemyEntity, availableTP);
    totalDamage += chipDamage;
    
    return totalDamage;
}

// === WEAPON DAMAGE ESTIMATION ===
function estimateWeaponDamage(weapon, enemyEntity) {
    var baseDamage = getWeaponBaseDamage(weapon);
    var strengthMultiplier = 1 + (myStrength / 100);
    var distance = getCellDistance(myCell, getCell(enemyEntity));
    var enemyResist = getResistance(enemyEntity);
    
    // Apply strength scaling
    var damage = baseDamage * strengthMultiplier;
    
    // Apply range penalties/bonuses
    if (weapon == WEAPON_KATANA && distance == 1) {
        damage *= 1.2; // 20% bonus at range 1
    }
    
    // Apply resistance
    damage = damage * (1 - enemyResist / 100);
    
    return max(1, floor(damage));
}

// === BASE WEAPON DAMAGE VALUES ===
function getWeaponBaseDamage(weapon) {
    if (weapon == WEAPON_ENHANCED_LIGHTNINGER) return 95; // Base damage ~95
    if (weapon == WEAPON_RIFLE) return 76;                // Base damage ~76
    if (weapon == WEAPON_M_LASER) return 91;              // Base damage ~91
    if (weapon == WEAPON_SWORD) return 55;                // Base damage ~55 (50-60 range)
    if (weapon == WEAPON_KATANA) return 77;               // Base damage ~77
    if (weapon == WEAPON_RHINO) return 90;                // Base damage ~90
    return 50; // Default
}

// === CHIP DAMAGE ESTIMATION ===
function estimateChipDamage(enemyEntity, availableTP) {
    var chipDamage = 0;
    
    // Lightning chip
    if (availableTP >= 4) {
        chipDamage += 50; // Approximate lightning damage
    }
    
    return chipDamage;
}

// === ENHANCED DANGEROUS ENEMY THREAT ASSESSMENT ===
function calculateEnemyThreat(enemyEntity) {
    var enemyStrength = getStrength(enemyEntity);
    var enemyMagic = getMagic(enemyEntity);
    var enemyWeapons = getWeapons(enemyEntity);
    var currentEnemyHP = getLife(enemyEntity);
    var maxEnemyHP = getTotalLife(enemyEntity);
    var distance = getCellDistance(myCell, getCell(enemyEntity));
    
    // 1. Calculate Enemy DPS (Damage Per Turn against us)
    var enemyDPS = calculateEnemyDPS(enemyEntity);
    
    // 2. Calculate Burst Potential (max damage in single turn)
    var burstPotential = calculateEnemyBurstPotential(enemyEntity);
    
    // 3. Calculate Kill Pressure (how quickly enemy can kill us)
    var killPressure = 0;
    if (enemyDPS > 0) {
        var turnsToKillUs = ceil(myHP / enemyDPS);
        killPressure = max(0, 10 - turnsToKillUs) * 100; // Higher pressure if enemy kills us faster
    }
    
    // 4. Base threat from stats (legacy)
    var baseThreat = max(enemyStrength, enemyMagic);
    
    // 5. Distance threat (closer = more dangerous)
    var distanceThreat = max(0, 20 - distance) * 10;
    
    // 6. Low HP High Damage bonus (dangerous glass cannons)
    var lowHPDangerBonus = 0;
    var hpPercent = currentEnemyHP / maxEnemyHP;
    if (hpPercent < LOW_HP_DANGER_THRESHOLD && enemyDPS > myHP * 0.3) {
        lowHPDangerBonus = LOW_HP_DANGER_BONUS; // Prioritize low-HP high-damage enemies
    }
    
    // 7. Weapon threat (in-range weapons)
    var weaponThreat = 0;
    for (var i = 0; i < count(enemyWeapons); i++) {
        var weapon = enemyWeapons[i];
        var minRange = getWeaponMinRange(weapon);
        var maxRange = getWeaponMaxRange(weapon);
        
        if (distance >= minRange && distance <= maxRange) {
            weaponThreat += getWeaponBaseDamage(weapon) * 2; // Double weight for in-range weapons
        }
    }
    
    // ENHANCED THREAT FORMULA: Focus on damage potential
    var totalThreat = enemyDPS * 5 + burstPotential * 2 + killPressure + baseThreat + distanceThreat + weaponThreat + lowHPDangerBonus;
    
    if (debugEnabled) {
        debugW("ENHANCED THREAT[" + enemyEntity + "]: DPS=" + enemyDPS + ", Burst=" + burstPotential + ", KillPress=" + killPressure + ", LowHPBonus=" + lowHPDangerBonus + ", Total=" + totalThreat);
    }
    
    return totalThreat;
}

// === CALCULATE ENEMY DPS (DAMAGE PER TURN) ===
function calculateEnemyDPS(enemyEntity) {
    var enemyStrength = getStrength(enemyEntity);
    var enemyMagic = getMagic(enemyEntity);
    var enemyWeapons = getWeapons(enemyEntity);
    var currentEnemyTP = getTP(enemyEntity);
    var distance = getCellDistance(myCell, getCell(enemyEntity));
    var totalDamage = 0;
    var availableTP = currentEnemyTP;
    
    // Calculate damage enemy can deal to us per turn
    for (var i = 0; i < count(enemyWeapons); i++) {
        var weapon = enemyWeapons[i];
        var weaponCost = getWeaponCost(weapon);
        var weaponUses = getWeaponMaxUses(weapon);
        
        if (availableTP >= weaponCost) {
            var minRange = getWeaponMinRange(weapon);
            var maxRange = getWeaponMaxRange(weapon);
            
            // Check if weapon can reach us
            if (distance >= minRange && distance <= maxRange) {
                var usesThisTurn = (weaponUses > 0) ? min(weaponUses, floor(availableTP / weaponCost)) : floor(availableTP / weaponCost);
                
                // Estimate weapon damage against us
                var baseDamage = getWeaponBaseDamage(weapon);
                var strengthMultiplier = 1 + (max(enemyStrength, enemyMagic) / 100);
                var damagePerUse = baseDamage * strengthMultiplier;
                
                // Apply our resistance
                damagePerUse = damagePerUse * (1 - myResistance / 100);
                
                var weaponTotalDamage = damagePerUse * usesThisTurn;
                totalDamage += weaponTotalDamage;
                availableTP -= (weaponCost * usesThisTurn);
            }
        }
    }
    
    // Add chip damage estimation
    if (availableTP >= 4) {
        totalDamage += 50; // Approximate lightning chip damage
    }
    
    return max(0, floor(totalDamage));
}

// === CALCULATE ENEMY BURST POTENTIAL ===
function calculateEnemyBurstPotential(enemyEntity) {
    var enemyDPS = calculateEnemyDPS(enemyEntity);
    var enemyWeapons = getWeapons(enemyEntity);
    var burstMultiplier = 1.0;
    
    // AoE weapons have higher burst potential
    for (var i = 0; i < count(enemyWeapons); i++) {
        var weapon = enemyWeapons[i];
        if (getWeaponArea(weapon) > 0) {
            burstMultiplier += 0.5; // 50% bonus for each AoE weapon
        }
    }
    
    // High TP enemies can burst harder
    var currentEnemyTP = getTP(enemyEntity);
    if (currentEnemyTP > 20) {
        burstMultiplier += 0.3; // 30% bonus for high TP enemies
    }
    
    return floor(enemyDPS * burstMultiplier);
}

// === CALCULATE TEAM FOCUS BONUS ===
function calculateTeamFocusBonus(enemyEntity) {
    // For now, return 0 - this would require ally information
    // In future, check how many allies can also attack this enemy
    var teamFocusBonus = 0;
    
    // If enemy is reachable by us and low HP, assume team can focus
    var currentEnemyHP = getLife(enemyEntity);
    var maxEnemyHP = getTotalLife(enemyEntity);
    var hpPercent = currentEnemyHP / maxEnemyHP;
    
    if (hpPercent < TEAM_FOCUS_HP_THRESHOLD) {
        teamFocusBonus = TEAM_FOCUS_BONUS; // Bonus for low HP enemies (easier team focus target)
    }
    
    return teamFocusBonus;
}

// === LIGHTWEIGHT REACHABILITY CHECK ===
function hasReachableDamageZones(enemyEntity) {
    var targetEnemyCell = getCell(enemyEntity);
    var distance = getCellDistance(myCell, targetEnemyCell);
    
    // Fast early checks to avoid expensive damage zone calculation
    
    // 1. Check if enemy is within any weapon's range + movement range
    var weapons = getWeapons();
    var canReachWithMovement = false;
    
    for (var i = 0; i < count(weapons); i++) {
        var weapon = weapons[i];
        var weaponCost = getWeaponCost(weapon);
        if (weaponCost > myTP) continue; // Skip unaffordable weapons
        
        var minRange = getWeaponMinRange(weapon);
        var maxRange = getWeaponMaxRange(weapon);
        
        // Check if we can move to get in range
        var closestRangeDistance = max(0, minRange - distance);
        var farthestRangeDistance = max(0, distance - maxRange);
        var movementNeeded = min(closestRangeDistance, farthestRangeDistance);
        
        if (movementNeeded <= myMP) {
            canReachWithMovement = true;
            break;
        }
    }
    
    // 2. Check teleportation range if movement isn't enough
    var canReachWithTeleport = false;
    if (!canReachWithMovement && canUseChip(CHIP_TELEPORTATION, getCell())) {
        // Teleport range is 12, check if that helps reach weapon range
        for (var i = 0; i < count(weapons); i++) {
            var weapon = weapons[i];
            if (getWeaponCost(weapon) > myTP) continue;
            
            var maxRange = getWeaponMaxRange(weapon);
            if (distance <= maxRange + 12) { // Can teleport + weapon range
                canReachWithTeleport = true;
                break;
            }
        }
    }
    
    // 3. If basic checks pass, verify with quick damage zone sampling
    if (canReachWithMovement || canReachWithTeleport) {
        // Quick sampling: check a few key positions instead of full calculation
        return quickDamageZoneCheck(targetEnemyCell);
    }
    
    return false;
}

// === QUICK DAMAGE ZONE SAMPLING ===
function quickDamageZoneCheck(targetEnemyCell) {
    // Sample 8-12 key positions around the enemy instead of full calculation
    var weapons = getWeapons();
    var samplePositions = [];
    
    // Sample positions at weapon ranges in cardinal and diagonal directions
    for (var i = 0; i < count(weapons); i++) {
        var weapon = weapons[i];
        if (getWeaponCost(weapon) > myTP) continue;
        
        var minRange = getWeaponMinRange(weapon);
        var maxRange = getWeaponMaxRange(weapon);
        
        // Sample 4 positions per weapon: N, S, E, W at optimal range
        var optimalRange = min(maxRange, (minRange + maxRange) / 2);
        var directions = [
            [0, optimalRange],   // North
            [0, -optimalRange],  // South  
            [optimalRange, 0],   // East
            [-optimalRange, 0]   // West
        ];
        
        for (var d = 0; d < count(directions); d++) {
            var dx = directions[d][0];
            var dy = directions[d][1];
            
            var cellX = getCellX(targetEnemyCell) + dx;
            var cellY = getCellY(targetEnemyCell) + dy;
            var sampleCell = getCellFromXY(cellX, cellY);
            
            if (sampleCell != null && sampleCell != -1) {
                var distance = getCellDistance(myCell, sampleCell);
                
                // Check if reachable by movement or teleport
                if (distance <= myMP || (distance <= 12 && canUseChip(CHIP_TELEPORTATION, getCell()))) {
                    // Verify can actually attack from this position
                    if (checkLineOfSight(sampleCell, targetEnemyCell)) {
                        var weaponDistance = getCellDistance(sampleCell, targetEnemyCell);
                        if (weaponDistance >= minRange && weaponDistance <= maxRange) {
                            return true;
                        }
                    }
                }
            }
        }
    }
    
    return false;
}

// === TARGET PRIORITIZATION ===
function prioritizeTargets() {
    if (count(allEnemies) == 0) {
        return [];
    }
    
    // Calculate TTK and priority for each enemy
    for (var i = 0; i < count(allEnemies); i++) {
        var enemyEntity = allEnemies[i];
        
        if (getLife(enemyEntity) <= 0) {
            continue; // Skip dead enemies
        }
        
        var ttk = calculateTTK(enemyEntity);
        var threat = calculateEnemyThreat(enemyEntity);
        var distance = getCellDistance(myCell, getCell(enemyEntity));
        var isReachable = hasReachableDamageZones(enemyEntity);
        
        // TEAM FOCUS BONUS: Calculate before priority formula
        var teamFocusBonus = calculateTeamFocusBonus(enemyEntity);
        
        // ENHANCED PRIORITY FORMULA: Focus on dangerous enemies first
        // Lower value = higher priority
        // Using configurable constants for easy tuning
        var priority = ttk * TTK_WEIGHT + distance * DISTANCE_WEIGHT - threat * THREAT_WEIGHT;
        
        // MAJOR REACHABILITY BONUS: Reachable enemies get massive priority boost
        if (isReachable) {
            priority -= REACHABILITY_BONUS;
        }
        
        // Apply team focus bonus
        priority -= teamFocusBonus;
        
        // BURST KILL BONUS: Enemies we can kill this turn get extra priority
        if (ttk <= 1 && isReachable) {
            priority -= BURST_KILL_BONUS;
        }
        
        // Update enemy data with enhanced metrics
        if (enemyData[enemyEntity] != null) {
            enemyData[enemyEntity].ttk = ttk;
            enemyData[enemyEntity].threat = threat;
            enemyData[enemyEntity].priority = priority;
            enemyData[enemyEntity].reachable = isReachable;
            enemyData[enemyEntity].teamFocusBonus = teamFocusBonus;
            enemyData[enemyEntity].canBurstKill = (ttk <= 1 && isReachable);
        }
    }
    
    // Sort enemies by priority (lowest priority value = highest actual priority)
    var sortedEnemies = [];
    for (var i = 0; i < count(allEnemies); i++) {
        push(sortedEnemies, allEnemies[i]);
    }
    
    // Simple bubble sort by priority
    for (var i = 0; i < count(sortedEnemies) - 1; i++) {
        for (var j = 0; j < count(sortedEnemies) - i - 1; j++) {
            var enemy1 = sortedEnemies[j];
            var enemy2 = sortedEnemies[j + 1];
            
            if (getLife(enemy1) <= 0) {
                // Move dead enemies to end
                var temp = sortedEnemies[j];
                sortedEnemies[j] = sortedEnemies[j + 1];
                sortedEnemies[j + 1] = temp;
                continue;
            }
            
            if (getLife(enemy2) <= 0) {
                continue; // Keep dead enemy at end
            }
            
            var priority1 = (enemyData[enemy1] != null) ? enemyData[enemy1].priority : 9999;
            var priority2 = (enemyData[enemy2] != null) ? enemyData[enemy2].priority : 9999;
            
            if (priority1 > priority2) {
                // Swap enemies
                var temp = sortedEnemies[j];
                sortedEnemies[j] = sortedEnemies[j + 1];
                sortedEnemies[j + 1] = temp;
            }
        }
    }
    
    if (debugEnabled && count(sortedEnemies) > 0) {
        debugW("DANGEROUS ENEMY PRIORITY ORDER:");
        for (var i = 0; i < min(3, count(sortedEnemies)); i++) {
            var enemyEntity = sortedEnemies[i];
            if (getLife(enemyEntity) > 0 && enemyData[enemyEntity] != null) {
                var data = enemyData[enemyEntity];
                var burstTag = data.canBurstKill ? " [BURST KILL]" : "";
                var teamTag = data.teamFocusBonus > 0 ? " [TEAM FOCUS]" : "";
                debugW("  [" + (i + 1) + "] Enemy " + enemyEntity + ": TTK=" + data.ttk + ", Threat=" + data.threat + ", Priority=" + data.priority + ", Reachable=" + data.reachable + burstTag + teamTag);
            }
        }
    }
    
    return sortedEnemies;
}

// === UPDATE PRIMARY TARGET ===
function updatePrimaryTarget() {
    var sortedEnemies = prioritizeTargets();
    
    if (count(sortedEnemies) > 0 && getLife(sortedEnemies[0]) > 0) {
        var newTarget = sortedEnemies[0];
        
        if (primaryTarget != newTarget) {
            if (debugEnabled) {
                debugW("TARGET SWITCH: " + primaryTarget + " → " + newTarget);
            }
            primaryTarget = newTarget;
            
            // Update legacy enemy variable for backward compatibility
            enemy = primaryTarget;
            if (enemyData[enemy] != null) {
                enemyCell = enemyData[enemy].cell;
                enemyHP = enemyData[enemy].hp;
                enemyMaxHP = enemyData[enemy].maxHp;
                enemyTP = enemyData[enemy].tp;
                enemyMP = enemyData[enemy].mp;
            }
        }
    }
    
    return primaryTarget;
}

// === FIND BEST AOE TARGET ===
function findBestAoETarget() {
    var weapons = getWeapons();
    var bestAoEOption = null;
    var bestAoEScore = 0;
    
    for (var i = 0; i < count(weapons); i++) {
        var weapon = weapons[i];
        
        if (getWeaponArea(weapon) > 0) { // AoE weapon
            var aoeOption = evaluateAoEWeapon(weapon);
            if (aoeOption != null && aoeOption.score > bestAoEScore) {
                bestAoEScore = aoeOption.score;
                bestAoEOption = aoeOption;
            }
        }
    }
    
    return bestAoEOption;
}

// === EVALUATE AOE WEAPON EFFECTIVENESS ===
function evaluateAoEWeapon(weapon) {
    if (primaryTarget == null || getLife(primaryTarget) <= 0) {
        return null;
    }
    
    var primaryCell = getCell(primaryTarget);
    var weaponRange = getWeaponArea(weapon);
    var totalDamage = 0;
    var enemiesHit = [];
    
    // For Enhanced Lightninger (3x3 square area)
    if (weapon == WEAPON_ENHANCED_LIGHTNINGER) {
        var affectedCells = get3x3Area(primaryCell);
        
        for (var j = 0; j < count(affectedCells); j++) {
            var cell = affectedCells[j];
            
            for (var k = 0; k < count(allEnemies); k++) {
                var enemyEntity = allEnemies[k];
                
                if (getLife(enemyEntity) > 0 && getCell(enemyEntity) == cell) {
                    var damage = estimateWeaponDamage(weapon, enemyEntity);
                    totalDamage += damage;
                    push(enemiesHit, enemyEntity);
                }
            }
        }
    }
    
    var enemyCount = count(enemiesHit);
    var score = totalDamage * enemyCount; // Bonus for hitting multiple enemies
    
    if (debugEnabled && enemyCount > 1) {
        debugW("AOE OPTION: Weapon " + weapon + " can hit " + enemyCount + " enemies for " + totalDamage + " total damage (score: " + score + ")");
    }
    
    return {
        weapon: weapon,
        targetCell: primaryCell,
        enemies: enemiesHit,
        totalDamage: totalDamage,
        enemyCount: enemyCount,
        score: score
    };
}

// === GET 3x3 AREA AROUND CELL ===
function get3x3Area(centerCell) {
    var cells = [];
    var centerX = getCellX(centerCell);
    var centerY = getCellY(centerCell);
    
    for (var dx = -1; dx <= 1; dx++) {
        for (var dy = -1; dy <= 1; dy++) {
            var cell = getCellFromXY(centerX + dx, centerY + dy);
            if (cell != null && cell != -1) {
                push(cells, cell);
            }
        }
    }
    
    return cells;
}