// V7 Module: decision/evaluation.ls
// SIMPLIFIED enemy-centric damage zone calculation

// === MAIN MULTI-ENEMY DAMAGE ZONE CALCULATION WITH ENEMY ASSOCIATIONS ===
function calculateMultiEnemyDamageZones() {
    debugW("=== MULTI-ENEMY DAMAGE CALCULATION START ===");
    var mergedDamageArray = [];
    
    // Safety checks
    if (enemies == null || count(enemies) == 0) {
        return mergedDamageArray;
    }
    
    var aliveEnemies = [];
    for (var i = 0; i < count(enemies); i++) {
        if (getLife(enemies[i]) > 0) {
            push(aliveEnemies, enemies[i]);
        }
    }
    
    if (count(aliveEnemies) == 0) {
        return mergedDamageArray;
    }
    
    // Get weapons
    var weapons = getWeapons();
    var hasWeapons = (weapons != null && count(weapons) > 0);
    
    debugW("WEAPON CHECK: hasWeapons=" + hasWeapons + ", count=" + count(weapons));
    if (hasWeapons) {
        debugW("AVAILABLE WEAPONS: " + weapons);
        for (var i = 0; i < count(weapons); i++) {
            debugW("WEAPON[" + i + "] = " + weapons[i] + " (B_LASER=60, RHINO=153, GRENADE=43)");
        }
    }
    
    // NEW APPROACH: Store damage zones with enemy associations
    var enemyDamageZones = []; // Array of [cell, damage, weaponId, enemyEntity]
    var maxSearchDistance = min(myMP + 15, 20); // Movement + weapon range
    
    // Check positions within reach
    for (var distance = 0; distance <= maxSearchDistance; distance++) {
        var candidateCells = getCellsAtExactDistance(myCell, distance);
        var cellLimit = min(count(candidateCells), 30); // Limit for performance
        
        for (var c = 0; c < cellLimit; c++) {
            var attackPosition = candidateCells[c];
            
            // Safety check: ensure attackPosition is an integer
            if (attackPosition != floor(attackPosition)) {
                if (debugEnabled) {
                    debugW("DECIMAL CELL WARNING: attackPosition=" + attackPosition + " converted to " + floor(attackPosition));
                }
                attackPosition = floor(attackPosition);
            }
            
            // Check each enemy from this position
            for (var e = 0; e < count(aliveEnemies); e++) {
                var currentEnemy = aliveEnemies[e];
                var currentEnemyCell = getCell(currentEnemy);
                
                // Find best weapon for this specific enemy from this position
                var bestWeapon = null;
                var bestDamage = 0;
                
                for (var w = 0; w < count(weapons); w++) {
                    var weapon = weapons[w];
                    var damage = calculateWeaponDamageFromCell(weapon, attackPosition, currentEnemyCell);
                    if (damage > bestDamage) {
                        bestDamage = damage;
                        bestWeapon = weapon;
                    }
                }
                
                // Store enemy-specific damage zone
                if (bestDamage > 0 && bestWeapon != null) {
                    // Ensure cell ID is an integer (fix decimal values like 591.36)
                    var cellId = floor(attackPosition + 0.5); // Round to nearest integer
                    if (cellId >= 0 && cellId <= 612) {
                        // DEBUG: Check damage value before and after push (ALL WEAPONS)
                        if (count(enemyDamageZones) < 3) { // Show first few zones
                            debugW("PRE-PUSH: cellId=" + cellId + ", bestDamage=" + bestDamage + ", weapon=" + bestWeapon);
                        }
                        
                        push(enemyDamageZones, [cellId, bestDamage, bestWeapon, currentEnemy]);
                        
                        // Verify what was actually stored
                        if (count(enemyDamageZones) <= 3) {
                            var lastIndex = count(enemyDamageZones) - 1;
                            var storedEntry = enemyDamageZones[lastIndex];
                            debugW("POST-PUSH: stored[" + lastIndex + "] = [" + storedEntry[0] + ", " + storedEntry[1] + ", " + storedEntry[2] + "]");
                        }
                    } else if (debugEnabled) {
                        debugW("INVALID CELL: " + attackPosition + " -> " + cellId + " (out of bounds 0-612)");
                    }
                }
            }
        }
    }
    
    // Convert enemy-specific zones to cell-based aggregation for compatibility
    var damageByCell = [:];
    for (var i = 0; i < count(enemyDamageZones); i++) {
        var zone = enemyDamageZones[i];
        var cell = zone[0];
        var damage = zone[1];
        
        // DEBUG: Show every zone during aggregation
        if (debugEnabled && i < 5) {
            debugW("AGGREGATION[" + i + "]: zone=[" + zone[0] + ", " + zone[1] + ", " + zone[2] + "] cell=" + cell + ", damage=" + damage);
        }
        
        // Ensure cell is integer and damage is valid
        if (cell != null && damage != null && damage > 0) {
            var cellId = floor(cell + 0.5); // Ensure integer cell ID
            if (damageByCell[cellId] == null) {
                damageByCell[cellId] = 0;
            }
            damageByCell[cellId] += damage;
        } else if (debugEnabled) {
            debugW("AGGREGATION SKIP: cell=" + cell + ", damage=" + damage);
        }
    }
    
    // NO CHIP FALLBACK: If no weapon zones, the AI should move to get into weapon range
    // instead of falling back to weak chips like SPARK
    
    var cellMapHasEntries = false;
    for (var cell in damageByCell) {
        cellMapHasEntries = true;
        break;
    }
    
    if (debugEnabled && !cellMapHasEntries) {
        debugW("MULTI-ENEMY: No weapon damage zones found - AI will need to move to weapon range");
    }
    
    // PRIORITY 1: Return enemy-specific damage zones if we have weapons
    if (hasWeapons && count(enemyDamageZones) > 0) {
        if (debugEnabled) {
            debugW("MULTI-ENEMY: Returning " + count(enemyDamageZones) + " enemy-specific damage zones with weapon associations");
            // Debug first few zones - both valid and invalid
            for (var i = 0; i < count(enemyDamageZones) && i < 5; i++) {
                var zone = enemyDamageZones[i];
                debugW("RETURN ZONE[" + i + "]: cell=" + zone[0] + ", damage=" + zone[1] + ", weapon=" + zone[2] + " (valid=" + (zone[1] != null && zone[1] > 0) + ")");
            }
        }
        return enemyDamageZones; // [cell, damage, weaponId, enemyEntity]
    }
    
    // PRIORITY 2: Convert to array format for chip fallback compatibility
    for (var cell in damageByCell) {
        var damage = damageByCell[cell];
        if (damage > 0) {
            var cellId = floor(cell + 0.5); // Ensure integer cell ID
            push(mergedDamageArray, [cellId, damage, WEAPON_RIFLE]); // Default weapon ID for chips
        }
    }
    
    return mergedDamageArray;
}

// === SIMPLE DAMAGE ZONE CALCULATION ===
function calculateDamageZones(enemyCell) {
    var damageMap = [:];
    
    if (enemyCell == null) return damageMap;
    
    var weapons = getWeapons();
    var hasWeapons = (weapons != null && count(weapons) > 0);
    
    // Check positions within movement + weapon range
    var maxDistance = min(myMP + 15, 20);
    
    for (var distance = 0; distance <= maxDistance; distance++) {
        var cells = getCellsAtExactDistance(myCell, distance);
        var cellLimit = min(count(cells), 50);
        
        for (var i = 0; i < cellLimit; i++) {
            var cell = cells[i];
            
            // Safety check: ensure cell is an integer
            if (cell != floor(cell)) {
                if (debugEnabled) {
                    debugW("DECIMAL CELL WARNING: cell=" + cell + " converted to " + floor(cell));
                }
                cell = floor(cell);
            }
            var totalDamage = 0;
            
            // Check all weapons from this position
            for (var w = 0; w < count(weapons); w++) {
                var weapon = weapons[w];
                var damage = calculateWeaponDamageFromCell(weapon, cell, enemyCell);
                totalDamage += damage;
            }
            
            if (totalDamage > 0) {
                damageMap[cell] = totalDamage;
            }
        }
    }
    
    // NO CHIP FALLBACK: If no weapon zones, the AI should move to get into weapon range
    // instead of falling back to weak chips like SPARK
    
    var mapHasEntries = false;
    for (var cell in damageMap) {
        mapHasEntries = true;
        break;
    }
    
    if (debugEnabled && !mapHasEntries) {
        debugW("SINGLE-ENEMY: No weapon damage zones found - AI will need to move to weapon range");
    }
    
    return damageMap;
}

// === WEAPON DAMAGE CALCULATION ===
function calculateWeaponDamageFromCell(weapon, fromCell, targetCell) {
    if (debugEnabled && weapon == 60) { // Debug B-Laser specifically
        debugW("DAMAGE CALC DEBUG: Weapon " + weapon + " from cell " + fromCell + " to " + targetCell);
    }
    
    if (myTP == null || myStrength == null) {
        if (debugEnabled && weapon == 60) debugW("DAMAGE FAIL: myTP or myStrength is null");
        return 0;
    }
    
    // Check weapon cost
    var weaponCost = getWeaponCost(weapon);
    if (weaponCost > myTP) {
        if (debugEnabled && weapon == 60) debugW("DAMAGE FAIL: Cost " + weaponCost + " > TP " + myTP);
        return 0;
    }
    
    // Check range
    var distance = getCellDistance(fromCell, targetCell);
    var minRange = getWeaponMinRange(weapon);
    var maxRange = getWeaponMaxRange(weapon);
    
    if (distance < minRange || distance > maxRange) {
        if (debugEnabled && weapon == 60) debugW("DAMAGE FAIL: Distance " + distance + " not in range " + minRange + "-" + maxRange);
        return 0;
    }
    
    // Check LOS
    if (!lineOfSight(fromCell, targetCell)) {
        if (debugEnabled && weapon == 60) debugW("DAMAGE FAIL: No LOS from " + fromCell + " to " + targetCell);
        return 0;
    }
    
    // Check alignment for line weapons (lasers and flame thrower)
    if (isLineWeapon(weapon)) {
        if (debugEnabled && weapon == 60) debugW("DAMAGE DEBUG: Line weapon detected, checking alignment");
        
        var fromX = getCellX(fromCell);
        var fromY = getCellY(fromCell);
        var toX = getCellX(targetCell);
        var toY = getCellY(targetCell);
        
        var xAligned = (fromX == toX);
        var yAligned = (fromY == toY);
        
        if (debugEnabled && weapon == 60) {
            debugW("ALIGNMENT: From(" + fromX + "," + fromY + ") To(" + toX + "," + toY + ") xAligned=" + xAligned + " yAligned=" + yAligned);
        }
        
        if (!(xAligned != yAligned)) { // Must be aligned on exactly one axis
            if (debugEnabled && weapon == 60) debugW("DAMAGE FAIL: Not aligned on exactly one axis");
            return 0;
        }
    }
    
    // Get base damage
    var effects = getWeaponEffects(weapon);
    // Minimal weapon debugging for M-Laser vs Enhanced Lightninger only
    var baseDamage = 0;
    
    for (var i = 0; i < count(effects); i++) {
        if (effects[i][0] == 1) { // EFFECT_DAMAGE
            var minDmg = effects[i][1];
            var maxDmg = effects[i][2];
            baseDamage = (minDmg + maxDmg) / 2;
            break;
        }
    }
    
    if (baseDamage == 0) {
        if (debugEnabled && weapon == 60) debugW("DAMAGE FAIL: No damage effects found");
        return 0;
    }
    
    // Apply strength scaling
    var scaledDamage = baseDamage * (1 + myStrength / 100.0);
    
    // Calculate uses
    var maxUses = getWeaponMaxUses(weapon);
    var tpUses = floor(myTP / weaponCost);
    var actualUses = (maxUses > 0) ? min(tpUses, maxUses) : tpUses;
    
    var totalDamage = scaledDamage * actualUses;
    
    // Debug key weapons only (no bonuses/penalties, natural stats)
    if ((weapon == WEAPON_M_LASER || weapon == WEAPON_ENHANCED_LIGHTNINGER) && myTP >= 16) {
        debugW("WEAPON " + weapon + " NATURAL: base=" + baseDamage + ", uses=" + actualUses + ", cost=" + weaponCost + ", totalDmg=" + floor(totalDamage));
    }
    
    // REMOVED: Artificial bonuses and penalties
    // Let weapons compete on their natural stats: damage, cost, uses, range
    
    if (debugEnabled && weapon == 60) {
        debugW("FINAL DAMAGE: base=" + baseDamage + " scaled=" + scaledDamage + " uses=" + actualUses + " total=" + totalDamage);
    }
    
    // Weapon-specific bonuses
    if (weapon == WEAPON_KATANA && distance == 1) {
        totalDamage *= 1.2; // Melee bonus
    }
    if (weapon == WEAPON_SWORD && distance == 1) {
        totalDamage *= 1.1; // Melee bonus for sword
    }
    
    return totalDamage;
}


// === GET AVAILABLE DAMAGE CHIPS ===
function getAvailableDamageChips() {
    var chips = getChips();
    var damageChips = [];
    
    for (var i = 0; i < count(chips); i++) {
        var chip = chips[i];
        if (chip == CHIP_LIGHTNING || chip == CHIP_SPARK) {
            push(damageChips, chip);
        }
    }
    
    return damageChips;
}

// === CALCULATE CHIP-BASED DAMAGE ZONES ===
function calculateChipDamageZones() {
    var chipDamageArray = [];
    var chips = getChips();
    
    if (chips == null || count(chips) == 0) {
        return chipDamageArray;
    }
    
    // Prioritize high-damage chips over SPARK
    var damageChips = [
        {id: CHIP_LIGHTNING, range: 10, damage: 400, cost: 4},
        {id: CHIP_METEORITE, range: 8, damage: 350, cost: 5},
        {id: CHIP_SPARK, range: 12, damage: 256, cost: 3}
    ];
    
    if (debugEnabled) {
        debugW("CHIP ZONES: Calculating damage zones for chips");
    }
    
    for (var c = 0; c < count(damageChips); c++) {
        var chipData = damageChips[c];
        if (!inArray(chips, chipData.id)) continue;
        if (chipData.cost > myTP) continue; // Can't afford this chip
        
        if (debugEnabled) {
            debugW("CHIP ZONES: Processing " + chipData.id + " (range: " + chipData.range + ", damage: " + chipData.damage + ")");
        }
        
        // Calculate zones for this chip against all enemies
        for (var e = 0; e < count(enemies); e++) {
            var currentEnemy = enemies[e];
            if (getLife(currentEnemy) <= 0) continue;
            
            var currentEnemyCell = getCell(currentEnemy);
            
            // Check cells within movement + chip range
            var maxSearchDistance = min(myMP + chipData.range, 20);
            for (var d = 0; d <= maxSearchDistance; d++) {
                var candidateCells = getCellsAtExactDistance(myCell, d);
                var cellLimit = min(count(candidateCells), 20); // Performance limit
                
                for (var i = 0; i < cellLimit; i++) {
                    var attackCell = candidateCells[i];
                    var distanceToEnemy = getCellDistance(attackCell, currentEnemyCell);
                    
                    // Check if chip can reach enemy from this position
                    if (distanceToEnemy <= chipData.range) {
                        // SPARK doesn't need LOS, others do
                        var needsLOS = (chipData.id != CHIP_SPARK);
                        var hasLOSCheck = true;
                        
                        if (needsLOS) {
                            hasLOSCheck = lineOfSight(attackCell, currentEnemyCell);
                        }
                        
                        if (hasLOSCheck) {
                            push(chipDamageArray, [attackCell, chipData.damage, chipData.id]);
                        }
                    }
                }
            }
        }
        
        // Only use the best chip for zones to avoid duplicate calculations
        if (count(chipDamageArray) > 0) {
            break;
        }
    }
    
    if (debugEnabled) {
        debugW("CHIP ZONES: Generated " + count(chipDamageArray) + " chip-based damage zones");
    }
    
    return chipDamageArray;
}

// === UTILITY FUNCTIONS ===
function getCellsAtExactDistance(centerCell, distance) {
    var cells = [];
    
    for (var cell = 0; cell < 613; cell++) {
        if (getCellDistance(centerCell, cell) == distance) {
            push(cells, cell);
        }
    }
    
    return cells;
}

function hasLOS(fromCell, toCell) {
    return lineOfSight(fromCell, toCell);
}

function countAdjacentObstacles(cell) {
    var obstacles = 0;
    var neighbors = [
        getCellFromXY(getCellX(cell) + 1, getCellY(cell)),
        getCellFromXY(getCellX(cell) - 1, getCellY(cell)),
        getCellFromXY(getCellX(cell), getCellY(cell) + 1),
        getCellFromXY(getCellX(cell), getCellY(cell) - 1)
    ];
    
    for (var i = 0; i < count(neighbors); i++) {
        var neighbor = neighbors[i];
        if (neighbor == null || neighbor == -1) {
            obstacles++;
        }
    }
    
    return obstacles;
}