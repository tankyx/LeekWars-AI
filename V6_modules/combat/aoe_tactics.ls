// V6 Module: combat/aoe_tactics.ls
// Area of effect calculations
// Auto-generated from V5.0 script

// Function: calculateOptimalAoEDamage
function calculateOptimalAoEDamage(fromCell, dist, tpAvailable) {
    if (dist > 10 || tpAvailable < 4) return 0;  // Too far or no TP
    
    var bestDamage = 0;
    
    // Get all alive enemies for multi-hit calculation
    enemies = getAliveEnemies();
    var enemyCells = [];
    for (var e = 0; e < count(enemies); e++) {
        push(enemyCells, getCell(enemies[e]));
    }
    
    // GRENADE LAUNCHER: AREA_CIRCLE_2 pattern
    // Range 4-7, costs 6 TP, hits in circle radius 2
    // Center: 100%, Ring 1 (4 cells): 80%, Ring 2 (8 cells): 60%
    if (tpAvailable >= 6) {
        // Find best grenade target for multi-hit
        var potentialTargets = getCellsInRange(fromCell, 7);
        
        for (var i = 0; i < min(20, count(potentialTargets)); i++) {
            var targetCell = potentialTargets[i];
            var shootDist = getCellDistance(fromCell, targetCell);
            
            // Can we shoot this cell?
            if (shootDist >= 4 && shootDist <= 7 && hasLOS(fromCell, targetCell)) {
                var totalGrenadeDamage = 0;
                var grenadeBase = 150 + myStrength * 2;
                
                // Calculate damage to all enemies in splash radius
                for (var j = 0; j < count(enemyCells); j++) {
                    var splashDist = getCellDistance(targetCell, enemyCells[j]);
                    if (splashDist <= 2) {
                        // Apply correct damage reduction: 1 - 0.2 * distance
                        var damageMultiplier = max(0, 1 - 0.2 * splashDist);
                        totalGrenadeDamage += grenadeBase * damageMultiplier;
                    }
                }
                
                bestDamage = max(bestDamage, totalGrenadeDamage);
            }
        }
    }
    
    // LIGHTNINGER: AREA_X_1 diagonal pattern  
    // Range 6-10, costs 5 TP, hits center + 4 diagonals
    // Center: 100%, Diagonals (distance 1): 80% each
    if (tpAvailable >= 5 && dist >= 6 && dist <= 10 && hasLOS(fromCell, enemyCell)) {
        var lightBase = 140 + floor(myStrength * 1.8);
        var totalLightDamage = lightBase;  // Primary target
        
        // Check if other enemies are in diagonal pattern
        var cx = getCellX(enemyCell);
        var cy = getCellY(enemyCell);
        var diagonals = [
            getCellFromXY(cx-1, cy-1),
            getCellFromXY(cx-1, cy+1),
            getCellFromXY(cx+1, cy-1),
            getCellFromXY(cx+1, cy+1)
        ];
        
        for (var d = 0; d < count(diagonals); d++) {
            if (inArray(enemyCells, diagonals[d])) {
                totalLightDamage += lightBase * 0.8;  // 80% damage on diagonals
            }
        }
        
        bestDamage = max(bestDamage, totalLightDamage);
    }
    
    return bestDamage;
}

// Find all positions where AoE can hit enemy (including through obstacles!)

// Function: findAoESplashPositions
function findAoESplashPositions(weapon, myPos, enemyPos) {
    var minRange = getWeaponMinRange(weapon);
    var maxRange = getWeaponMaxRange(weapon);
    var area = getWeaponArea(weapon);
    var splashPositions = [];
    
    // Get all cells we can potentially target
    var targetableCells = getCellsInRange(myPos, maxRange);
    
    for (var i = 0; i < count(targetableCells); i++) {
        var targetCell = targetableCells[i];
        var dist = getCellDistance(myPos, targetCell);
        
        // Check range
        if (dist < minRange || dist > maxRange) continue;
        
        // We need LOS to the TARGET cell, NOT the enemy!
        // This is key - AoE goes through walls from the impact point
        if (!hasLOS(myPos, targetCell)) continue;
        
        // Check if AoE would hit enemy from this target
        var hitCells = getAoEAffectedCells(targetCell, area);
        
        for (var j = 0; j < count(hitCells); j++) {
            if (hitCells[j] == enemyPos) {
                // Calculate damage based on distance from center
                var splashDist = getCellDistance(targetCell, enemyPos);
                var damagePercent = max(0, 1 - 0.2 * splashDist);
                
                var splashData = [:];
                splashData["target"] = targetCell;
                splashData["damagePercent"] = damagePercent;
                splashData["isIndirect"] = (targetCell != enemyPos);
                splashData["splashDistance"] = splashDist;
                
                push(splashPositions, splashData);
                break;  // Found hit from this target
            }
        }
    }
    
    return splashPositions;
}

// === LIGHTNINGER PATTERN OPTIMIZATION ===

// Function: getAoEAffectedCells
function getAoEAffectedCells(center, areaType) {
    if (center == null || center == -1) return [];
    
    var cells = [];
    var cx = getCellX(center);
    var cy = getCellY(center);
    
    if (areaType == AREA_CIRCLE_2 || areaType == 2) {
        // Circle radius 2 - 13 cells total
        // Use Manhattan distance for circle calculation
        for (var dx = -2; dx <= 2; dx++) {
            for (var dy = -2; dy <= 2; dy++) {
                if (abs(dx) + abs(dy) <= 2) {  // Manhattan distance <= 2
                    var cell = getCellFromXY(cx + dx, cy + dy);
                    if (cell != null && cell != -1) {
                        push(cells, cell);
                    }
                }
            }
        }
    } else if (areaType == AREA_X_1 || areaType == 3) {
        // X pattern (5 cells - center + 4 diagonals)
        var offsets = [[0,0], [1,1], [-1,-1], [1,-1], [-1,1]];
        for (var i = 0; i < count(offsets); i++) {
            var dx = offsets[i][0];
            var dy = offsets[i][1];
            var cell = getCellFromXY(cx + dx, cy + dy);
            if (cell != null && cell != -1) {
                push(cells, cell);
            }
        }
    } else if (areaType == AREA_CIRCLE_3 || areaType == 3) {
        // Circle radius 3 - for bazooka
        for (var dx = -3; dx <= 3; dx++) {
            for (var dy = -3; dy <= 3; dy++) {
                if (abs(dx) + abs(dy) <= 3) {
                    var cell = getCellFromXY(cx + dx, cy + dy);
                    if (cell != null && cell != -1) {
                        push(cells, cell);
                    }
                }
            }
        }
    }
    
    return cells;
}

// Comprehensive AoE damage calculator with proper formula

// Function: calculateAoEDamageAtCell
function calculateAoEDamageAtCell(weapon, targetCell, enemyPositions) {
    var baseDamage = 0;
    var totalDamage = 0;
    var enemiesHit = 0;
    
    // Calculate base damage for the weapon
    if (weapon == WEAPON_GRENADE_LAUNCHER) {
        baseDamage = 150 + myStrength * 2;
    } else if (weapon == WEAPON_M_LASER) {
        baseDamage = 95;  // M-Laser avg damage (90-100)
    } else {
        return 0;  // Not an AoE/line weapon
    }
    
    // GRENADE LAUNCHER: Circle radius 2
    if (weapon == WEAPON_GRENADE_LAUNCHER) {
        // Get all cells within radius 2 of target
        var affectedCells = [];
        for (var dx = -2; dx <= 2; dx++) {
            for (var dy = -2; dy <= 2; dy++) {
                var testCell = getCellFromOffset(targetCell, dx, dy);
                if (testCell != -1 && getCellDistance(targetCell, testCell) <= 2) {
                    push(affectedCells, testCell);
                }
            }
        }
        
        for (var i = 0; i < count(affectedCells); i++) {
            var cell = affectedCells[i];
            var distance = getCellDistance(targetCell, cell);
            
            // Apply correct LeekWars formula: 1 - 0.2 * distance
            var damageMultiplier = max(0, 1 - 0.2 * distance);
            
            // Check if enemy is in this cell
            for (var j = 0; j < count(enemyPositions); j++) {
                if (enemyPositions[j] == cell) {
                    totalDamage += baseDamage * damageMultiplier;
                    enemiesHit++;
                    break;
                }
            }
        }
        
        // Multi-hit bonus: multiply damage if hitting multiple enemies
        if (enemiesHit > 1) {
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("💥 Grenade multi-hit! Hitting " + enemiesHit + " enemies");
            }
        }
    }
    // M-LASER: Line pattern (goes through entities)
    else if (weapon == WEAPON_M_LASER) {
        // M-Laser goes through ALL entities in a straight line
        var myPos = getCell();
        
        // Check if we're aligned with the target
        if (!isOnSameLine(myPos, targetCell)) {
            return 0;  // Can't hit with laser if not aligned
        }
        
        // Get all cells in the laser line
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
        
        // Trace the line and check for enemies
        var currentX = fx + dx;
        var currentY = fy + dy;
        var steps = 0;
        
        while (steps < 12) {  // M-Laser max range
            var cell = getCellFromXY(currentX, currentY);
            if (cell == null || cell == -1) break;
            
            // Check if enemy is in this cell
            for (var j = 0; j < count(enemyPositions); j++) {
                if (enemyPositions[j] == cell) {
                    totalDamage += baseDamage;  // Full damage to all enemies in line
                    enemiesHit++;
                    break;
                }
            }
            
            currentX += dx;
            currentY += dy;
            steps++;
        }
        
        if (enemiesHit > 1) {
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("⚡ M-Laser multi-hit! Piercing " + enemiesHit + " enemies");
            }
        }
    }
    
    return totalDamage;
}

// FIX: Kill probability with mitigation and chips