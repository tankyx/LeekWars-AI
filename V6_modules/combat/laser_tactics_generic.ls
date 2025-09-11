// ===================================================================
// V6 GENERIC LASER TACTICS MODULE
// ===================================================================
// Common functions for all laser weapons (M-Laser, B-Laser, J-Laser, etc.)
// All lasers pierce through entities allowing multi-hit damage

// ===================================================================
// GENERIC LASER FUNCTIONS
// ===================================================================

/**
 * Find the best laser target that hits the most enemies
 * @param weapon - The laser weapon constant (WEAPON_M_LASER, WEAPON_B_LASER, etc.)
 * @param fromCell - Cell to shoot from (usually myCell)
 * @param minRange - Minimum range of the laser
 * @param maxRange - Maximum range of the laser
 * @param enemies - Array of enemies to check
 * @return Array with target info or null
 */
function findBestLaserTargetGeneric(weapon, fromCell, minRange, maxRange, enemiesArray) {
    if (count(enemiesArray) == 0) return null;
    
    var bestTarget = null;
    var bestHits = 0;
    var bestTargetCell = null;
    var bestDamage = 0;
    
    // Check each enemy as a potential target
    for (var e in enemiesArray) {
        var eCell = getCell(e);
        var dist = getCellDistance(fromCell, eCell);
        
        // Check if this enemy is in laser range and aligned
        if (dist >= minRange && dist <= maxRange) {
            if (isOnSameLine(fromCell, eCell) && lineOfSight(fromCell, eCell)) {
                // Count how many enemies this line would hit
                var hitData = countLaserHitsGeneric(fromCell, eCell, minRange, maxRange, enemiesArray);
                var hits = hitData["count"];
                var totalDamage = hitData["totalDamage"];
                
                // Prioritize by total damage, then by number of hits
                if (totalDamage > bestDamage || (totalDamage == bestDamage && hits > bestHits)) {
                    bestHits = hits;
                    bestTarget = e;
                    bestTargetCell = eCell;
                    bestDamage = totalDamage;
                }
            }
        }
    }
    
    if (bestTarget != null) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Best laser target: " + getName(bestTarget) + " - hits " + bestHits + " enemies, damage: " + bestDamage);
        }
        return [
            "target": bestTarget, 
            "targetCell": bestTargetCell, 
            "hits": bestHits,
            "totalDamage": bestDamage
        ];
    }
    
    return null;
}

/**
 * Count how many enemies are hit by a laser and calculate total damage
 * @param fromCell - Origin cell of the laser
 * @param targetCell - Target cell (defines the line direction)
 * @param minRange - Minimum range of the laser
 * @param maxRange - Maximum range of the laser
 * @param enemies - Array of enemies to check
 * @return Array with count and total damage
 */
function countLaserHitsGeneric(fromCell, targetCell, minRange, maxRange, enemiesArray) {
    var hits = 0;
    var totalDamage = 0;
    var hitEnemies = [];
    
    // Lasers hit all enemies on the same line between shooter and max range
    for (var e in enemiesArray) {
        var eCell = getCell(e);
        
        // Check if enemy is on the same line as the target
        if (isOnSameLine(fromCell, eCell) && isOnSameLine(eCell, targetCell)) {
            var distToEnemy = getCellDistance(fromCell, eCell);
            
            // Check if enemy is in range
            if (distToEnemy >= minRange && distToEnemy <= maxRange) {
                hits++;
                push(hitEnemies, e);
                
                // Estimate damage (will be refined by weapon-specific functions)
                var enemyLife = getLife(e);
                totalDamage += min(enemyLife, 100); // Base estimate
            }
        }
    }
    
    return [
        "count": max(1, hits), 
        "totalDamage": totalDamage,
        "enemies": hitEnemies
    ];
}

/**
 * Find optimal position to maximize laser multi-hits
 * @param weapon - The laser weapon constant
 * @param minRange - Minimum range of the laser
 * @param maxRange - Maximum range of the laser
 * @param currentCell - Current position
 * @param availableMP - Available movement points
 * @param enemies - Array of enemies
 * @return Best cell for laser shots or null
 */
function findOptimalLaserPosition(weapon, minRange, maxRange, currentCell, availableMP, enemiesArray) {
    var bestCell = currentCell;
    var bestScore = evaluateLaserPosition(weapon, minRange, maxRange, currentCell, enemiesArray);
    
    // Get reachable cells
    var reachableCells = getReachableCells(currentCell, availableMP);
    
    for (var cell in reachableCells) {
        var score = evaluateLaserPosition(weapon, minRange, maxRange, cell, enemiesArray);
        if (score > bestScore) {
            bestScore = score;
            bestCell = cell;
        }
    }
    
    if (bestCell != currentCell) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Found better laser position with score: " + bestScore);
        }
    }
    
    return bestCell;
}

/**
 * Evaluate a position for laser shooting potential
 * @param weapon - The laser weapon constant
 * @param minRange - Minimum range of the laser
 * @param maxRange - Maximum range of the laser
 * @param fromCell - Cell to evaluate
 * @param enemies - Array of enemies
 * @return Score for this position
 */
function evaluateLaserPosition(weapon, minRange, maxRange, fromCell, enemiesArray) {
    var score = 0;
    var alignedEnemies = 0;
    
    // Check alignment with each enemy
    for (var e in enemiesArray) {
        var eCell = getCell(e);
        var dist = getCellDistance(fromCell, eCell);
        
        if (dist >= minRange && dist <= maxRange) {
            if (isOnSameLine(fromCell, eCell) && lineOfSight(fromCell, eCell)) {
                alignedEnemies++;
                
                // Check for multi-hit potential
                var hitData = countLaserHitsGeneric(fromCell, eCell, minRange, maxRange, enemiesArray);
                score += hitData["count"] * 500; // High value for multi-hits
                score += hitData["totalDamage"];
            }
        }
    }
    
    // Bonus for multiple alignment options
    score += alignedEnemies * 100;
    
    // Penalty for being too close (vulnerable position)
    if (enemiesArray[0] != null) {
        var closestDist = getCellDistance(fromCell, getCell(enemiesArray[0]));
        if (closestDist < minRange) {
            score -= 200; // Can't shoot if too close
        }
    }
    
    return score;
}

/**
 * Check if moving would give better laser opportunities
 * @param weapon - The laser weapon constant
 * @param minRange - Minimum range of the laser
 * @param maxRange - Maximum range of the laser
 * @param currentCell - Current position
 * @param availableMP - Available movement points
 * @param enemies - Array of enemies
 * @return true if should reposition, false otherwise
 */
function shouldRepositionForLaser(weapon, minRange, maxRange, currentCell, availableMP, enemiesArray) {
    if (availableMP <= 0) return false;
    
    var currentScore = evaluateLaserPosition(weapon, minRange, maxRange, currentCell, enemiesArray);
    var bestPosition = findOptimalLaserPosition(weapon, minRange, maxRange, currentCell, availableMP, enemiesArray);
    
    if (bestPosition != currentCell) {
        var newScore = evaluateLaserPosition(weapon, minRange, maxRange, bestPosition, enemiesArray);
        
        // Only reposition if significantly better (at least 30% improvement)
        return newScore > currentScore * 1.3;
    }
    
    return false;
}

/**
 * Get all enemies that would be hit by a laser shot
 * @param fromCell - Origin cell
 * @param targetCell - Target cell defining the line
 * @param minRange - Minimum range
 * @param maxRange - Maximum range
 * @param enemies - Array of enemies
 * @return Array of enemies that would be hit
 */
function getLaserHitTargets(fromCell, targetCell, minRange, maxRange, enemiesArray) {
    var hitData = countLaserHitsGeneric(fromCell, targetCell, minRange, maxRange, enemiesArray);
    return hitData["enemies"];
}

/**
 * Calculate actual damage for a laser shot considering all hits
 * @param weapon - The laser weapon
 * @param fromCell - Origin cell
 * @param targetCell - Target cell
 * @param minRange - Minimum range
 * @param maxRange - Maximum range
 * @param enemies - Array of enemies
 * @param myEntity - Shooting entity (for damage calculation)
 * @return Total damage dealt
 */
function calculateLaserTotalDamage(weapon, fromCell, targetCell, minRange, maxRange, enemiesArray, myEntity) {
    var targets = getLaserHitTargets(fromCell, targetCell, minRange, maxRange, enemiesArray);
    var totalDamage = 0;
    
    for (var target in targets) {
        // getWeaponDamage takes (weapon, entity)
        var damage = getWeaponDamage(weapon, target);
        totalDamage += damage;
    }
    
    return totalDamage;
}

/**
 * Visual debug for laser targeting
 * @param fromCell - Origin cell
 * @param targetCell - Target cell
 * @param hits - Number of enemies hit
 */
function debugLaserShot(fromCell, targetCell, hits) {
    if (hits > 1) {
        // Multi-hit - use special color
        mark(fromCell, COLOR_BLUE);
        mark(targetCell, COLOR_RED);
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("MULTI-HIT LASER: " + hits + " enemies!");
        }
    } else {
        // Single hit
        mark(fromCell, 3); // Green color
        mark(targetCell, 5); // Yellow color
    }
}

if (debugEnabled && canSpendOps(1000)) {
    debugLog("Generic laser tactics module loaded");
}