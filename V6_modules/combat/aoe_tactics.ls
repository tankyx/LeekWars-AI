// V6 Module: combat/aoe_tactics.ls
// Area of effect calculations
// Auto-generated from V5.0 script

// Function: calculateOptimalAoEDamage
function calculateOptimalAoEDamage(fromCell, dist, tpAvailable) {
    if (dist > 10 || tpAvailable < 4) return 0;  // Too far or no TP
    
    var bestDamage = 0;
    
    // GRENADE LAUNCHER: AREA_CIRCLE_2 pattern
    // Range 4-7, costs 6 TP, hits in circle radius 2
    // Center: 100%, Ring 1 (4 cells): 80%, Ring 2 (8 cells): 60%
    if (tpAvailable >= 6) {
        // Can we hit directly?
        if (dist >= 4 && dist <= 7 && hasLOS(fromCell, enemyCell)) {
            var grenadeBase = 150 + myStrength * 2;
            bestDamage = grenadeBase;  // 100% damage on direct hit
        } 
        // Can we hit with splash from a nearby position?
        else if (dist >= 2 && dist <= 9) {
            // Find cells we can shoot that would splash the enemy
            var potentialTargets = getCellsInRange(fromCell, 7);
            
            for (var i = 0; i < min(10, count(potentialTargets)); i++) {
                var targetCell = potentialTargets[i];
                var shootDist = getCellDistance(fromCell, targetCell);
                
                // Can we shoot this cell?
                if (shootDist >= 4 && shootDist <= 7 && hasLOS(fromCell, targetCell)) {
                    // Will it splash the enemy?
                    var splashDist = getCellDistance(targetCell, enemyCell);
                    if (splashDist <= 2) {
                        // Apply correct damage reduction: 1 - 0.2 * distance
                        var damageMultiplier = max(0, 1 - 0.2 * splashDist);
                        var grenadeBase = 150 + myStrength * 2;
                        var splashDamage = grenadeBase * damageMultiplier;
                        
                        // Distance 0: 100%, Distance 1: 80%, Distance 2: 60%
                        bestDamage = max(bestDamage, splashDamage);
                    }
                }
            }
        }
    }
    
    // LIGHTNINGER: AREA_X_1 diagonal pattern  
    // Range 6-10, costs 5 TP, hits center + 4 diagonals
    // Center: 100%, Diagonals (distance 1): 80% each
    if (tpAvailable >= 5 && dist >= 6 && dist <= 10 && hasLOS(fromCell, enemyCell)) {
        var lightBase = 140 + floor(myStrength * 1.8);
        
        // Direct hit = 100% damage
        // If enemy is large or we're lucky with positioning, might hit diagonals too
        // Average case: just the center hit
        bestDamage = max(bestDamage, lightBase);
        
        // Note: In a real implementation, we'd check if enemy occupies diagonal cells
        // For now, assume single-cell enemy and just center hit
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
    
    // Calculate base damage for the weapon
    if (weapon == WEAPON_GRENADE_LAUNCHER) {
        baseDamage = 150 + myStrength * 2;
    } else if (weapon == WEAPON_LIGHTNINGER) {
        baseDamage = 140 + floor(myStrength * 1.8);
    } else {
        return 0;  // Not an AoE weapon
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
                    break;
                }
            }
        }
    }
    // LIGHTNINGER: X pattern (diagonals)
    else if (weapon == WEAPON_LIGHTNINGER) {
        var cx = getCellX(targetCell);
        var cy = getCellY(targetCell);
        
        // Center + 4 diagonal cells
        var diagonalPattern = [
            targetCell,                   // Center: distance 0 = 100%
            getCellFromXY(cx-1, cy-1),   // NW: distance 1 = 80%
            getCellFromXY(cx-1, cy+1),   // SW: distance 1 = 80%
            getCellFromXY(cx+1, cy-1),   // NE: distance 1 = 80%
            getCellFromXY(cx+1, cy+1)    // SE: distance 1 = 80%
        ];
        
        for (var i = 0; i < count(diagonalPattern); i++) {
            var cell = diagonalPattern[i];
            if (cell == null || cell == -1) continue;
            
            // Distance is 0 for center, 1 for diagonals
            var distance = (i == 0) ? 0 : 1;
            var damageMultiplier = max(0, 1 - 0.2 * distance);
            
            // Check if enemy is in this cell
            for (var j = 0; j < count(enemyPositions); j++) {
                if (enemyPositions[j] == cell) {
                    totalDamage += baseDamage * damageMultiplier;
                    break;
                }
            }
        }
    }
    
    return totalDamage;
}

// FIX: Kill probability with mitigation and chips
