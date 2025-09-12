// V6 Module: movement/teleportation.ls
// Teleportation tactics - COMPLETELY FIXED
// Fixes: 1-cell teleports, post-teleport movement, visual debugging

// Function: shouldUseTeleport
function shouldUseTeleport() {
    if (!TELEPORT_AVAILABLE || myTP < 9) return false;
    
    // NEW STRATEGY: Conservative TP usage - only for emergencies and Katana positioning
    if (!USE_CONSERVATIVE_TP) {
        // Use old logic if conservative mode is disabled
        return shouldUseTeleportLegacy();
    }
    
    // Get FRESH positions
    var currentCell = getCell();
    var currentEnemyCell = getCell(enemy);
    var currentDistance = getCellDistance(currentCell, currentEnemyCell);
    
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("CONSERVATIVE TP: Checking teleport need: dist=" + currentDistance + ", MP=" + getMP() + ", TP=" + myTP);
    }
    
    // EMERGENCY TELEPORT: Life-threatening situations only
    if (myHP < myMaxHP * 0.2) { // Below 20% HP (more conservative than old 30%)
        var currentEID = calculateEID(currentCell);
        if (currentEID >= myHP * 0.8) { // Much higher threat threshold 
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("🚨 CONSERVATIVE: Emergency teleport - HP critical: " + myHP + ", EID: " + currentEID);
            }
            return true;
        }
    }
    
    // KATANA POSITIONING: Only use TP to get into Katana range for finishing moves
    var weapons = getWeapons();
    if (inArray(weapons, WEAPON_KATANA) && katanaUsesRemaining > 0) {
        var enemyHPPercent = getLife(enemy) / getTotalLife(enemy);
        
        // Only teleport for Katana if enemy is low HP (finishing move)
        if (enemyHPPercent <= 0.3 && currentDistance > 2) {
            // Check if we can't walk to Katana range (1-2)
            var reachable = getReachableCells(currentCell, getMP());
            var canWalkToKatana = false;
            
            for (var i = 0; i < count(reachable); i++) {
                var cell = reachable[i];
                var dist = getCellDistance(cell, currentEnemyCell);
                if (dist >= 1 && dist <= 2) {
                    canWalkToKatana = true;
                    break;
                }
            }
            
            if (!canWalkToKatana && myTP >= 15) { // Need enough TP for teleport + Katana attack
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("⚔️ CONSERVATIVE: Katana finishing teleport - enemy HP: " + (enemyHPPercent * 100) + "%");
                }
                return true;
            }
        }
    }
    
    // NEVER teleport for general positioning - save TP for attacks and chips
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("CONSERVATIVE: No teleport - saving TP for attacks/chips");
    }
    return false;
}

// Function: shouldUseTeleportLegacy
// Legacy teleport logic for fallback
function shouldUseTeleportLegacy() {
    // Get FRESH positions
    var currentCell = getCell();
    var currentEnemyCell = getCell(enemy);
    var currentDistance = getCellDistance(currentCell, currentEnemyCell);
    
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("LEGACY: Checking teleport need: dist=" + currentDistance + ", MP=" + getMP() + ", TP=" + myTP);
    }
    
    // Check if we can attack from current position
    var canAttackHere = false;
    if (hasLOS(currentCell, currentEnemyCell)) {
        if (currentDistance >= 7 && currentDistance <= 9) {
            canAttackHere = true;  // Rifle range
        } else if (currentDistance >= 5 && currentDistance <= 12 && isOnSameLine(currentCell, currentEnemyCell)) {
            canAttackHere = true;  // M-Laser range with alignment
        } else if (currentDistance >= 4 && currentDistance <= 7) {
            canAttackHere = true;  // Grenade range
        }
    } else if (currentDistance == 1) {
        canAttackHere = true;  // Dark Katana melee
    }
    
    // If we can already attack, no need to teleport
    if (canAttackHere) {
        return false;
    }
    
    // Check if we can WALK to attack range with LOS
    var reachable = getReachableCells(currentCell, getMP());
    var canWalkToAttack = false;
    
    for (var i = 0; i < count(reachable); i++) {
        var cell = reachable[i];
        var dist = getCellDistance(cell, currentEnemyCell);
        
        if (hasLOS(cell, currentEnemyCell)) {
            if ((dist >= 7 && dist <= 9) ||  // Rifle
                (dist >= 4 && dist <= 7) ||  // Grenade
                (dist >= 5 && dist <= 12 && isOnSameLine(cell, currentEnemyCell))) {  // M-Laser
                canWalkToAttack = true;
                break;
            }
        } else if (dist == 1) {  // Dark Katana
            canWalkToAttack = true;
            break;
        }
    }
    
    // Only teleport if we CAN'T walk into range
    if (!canWalkToAttack) {
        return true;
    }
    
    // Emergency situations
    if (myHP < myMaxHP * 0.3) {
        var currentEID = calculateEID(currentCell);
        if (currentEID >= myHP * 0.5) {
            return true;
        }
    }
    
    return false;
}


// Function: findBestTeleportTarget
function findBestTeleportTarget() {
    var currentCell = getCell();
    var currentEnemyCell = getCell(enemy);
    
    // Finding teleport target - debug removed to reduce spam
    
    // Get walkable cells to avoid teleporting where we can walk
    var walkableCells = getReachableCells(currentCell, getMP());
    var walkableSet = [:];
    for (var i = 0; i < count(walkableCells); i++) {
        walkableSet[walkableCells[i]] = true;
    }
    
    var bestCell = currentCell;
    var bestScore = -999999;
    var evaluated = 0;
    
    // Check all cells within teleport range (1-12)
    for (var dist = 1; dist <= 12; dist++) {
        var cellsAtDist = getCellsAtDistance(currentCell, dist);
        
        for (var i = 0; i < count(cellsAtDist); i++) {
            var cell = cellsAtDist[i];
            
            // Skip invalid cells
            if (cell == -1 || isObstacle(cell) || cell == currentEnemyCell) continue;
            
            // CRITICAL: Skip cells we can walk to!
            if (mapContainsKey(walkableSet, cell)) {
                // Skipping walkable cell - debug removed to reduce spam
                continue;
            }
            
            evaluated++;
            var score = evaluateTeleportCell(cell, currentEnemyCell);
            
            if (score > bestScore) {
                bestScore = score;
                bestCell = cell;
            }
        }
    }
    
    // Teleport candidates evaluated - debug removed to reduce spam
    
    // Visual debugging - show best target
    if (bestCell != currentCell) {
        mark(bestCell, COLOR_BLUE);  // Blue for best teleport target
    }
    
    return bestCell;
}


// NEW: Resource pressure teleportation
function shouldTeleportForResourcePressure(myCell, enemyCell) {
    // Don't use if low on TP
    if (myTP < 14) return false;
    
    var currentDist = getCellDistance(myCell, enemyCell);
    
    // Scenario 1: Enemy is at their optimal range → force them to reposition
    if (currentDist >= 7 && currentDist <= 9) {
        // We're both in rifle range - teleport to force their reaction
        if (hasLOS(myCell, enemyCell)) {
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("📍 Resource pressure: Both in optimal range - forcing enemy reposition");
            }
            return true;
        }
    }
    
    // Scenario 2: Create range advantage opportunity
    // If they're in their optimal range but we can create better positioning
    var enemyOptimalRange = isEnemyInOptimalRange(enemyCell, myCell);
    if (enemyOptimalRange && myTP > (enemyTP + 4)) {
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("📍 Resource pressure: Enemy optimal, we have TP advantage - repositioning");
        }
        return true;
    }
    
    // Scenario 3: Turn sequence manipulation
    // Teleport to create a position where they MUST move next turn
    if (turn >= 5 && (turn % 3 == 1)) {  // Every 3rd turn starting turn 5
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("📍 Resource pressure: Turn sequence manipulation");
        }
        return true;
    }
    
    return false;
}


// Helper: Check if enemy is in their optimal range relative to us
function isEnemyInOptimalRange(enemyCell, myCell) {
    var dist = getCellDistance(enemyCell, myCell);
    
    // Most leeks optimize for similar ranges to us
    if (dist >= 7 && dist <= 9) {
        return hasLOS(enemyCell, myCell);
    }
    
    // Also check melee range (aggressive builds)
    if (dist <= 3) {
        return true;
    }
    
    return false;
}


// Helper: Evaluate a teleport destination
function evaluateTeleportCell(cell, enemyCell) {
    var score = 0;
    var distToEnemy = getCellDistance(cell, enemyCell);
    
    // Check if we can attack DIRECTLY from this cell
    var canAttackDirectly = false;
    if (hasLOS(cell, enemyCell)) {
        if (distToEnemy >= 7 && distToEnemy <= 9) {
            score += 5000;  // Rifle range - excellent!
            canAttackDirectly = true;
        } else if (distToEnemy >= 5 && distToEnemy <= 12 && isOnSameLine(cell, enemyCell)) {
            score += 4500;  // M-Laser range - very good!
            canAttackDirectly = true;
        } else if (distToEnemy >= 4 && distToEnemy <= 7) {
            score += 2000;  // Grenade range - okay
            canAttackDirectly = true;
        }
    } else if (distToEnemy == 1) {
        score += 3000;  // Melee range
        canAttackDirectly = true;
    }
    
    // If can't attack directly, check if we can WALK to attack after teleporting
    if (!canAttackDirectly) {
        var reachableAfterTP = getReachableCells(cell, 6);  // 6 MP after teleport
        var canReachAttack = false;
        
        for (var r = 0; r < min(10, count(reachableAfterTP)); r++) {
            var testCell = reachableAfterTP[r];
            var testDist = getCellDistance(testCell, enemyCell);
            
            if (hasLOS(testCell, enemyCell)) {
                if ((testDist >= 7 && testDist <= 9) ||  // Rifle
                    (testDist >= 5 && testDist <= 12 && isOnSameLine(testCell, enemyCell)) ||  // M-Laser  
                    (testDist >= 4 && testDist <= 7)) {  // Grenade
                    score += 1000;  // Can reach attack position
                    canReachAttack = true;
                    break;
                }
            } else if (testDist == 1) {
                score += 800;  // Can reach melee
                canReachAttack = true;
                break;
            }
        }
        
        // If can't reach attack even after walking, heavily penalize
        if (!canReachAttack) {
            score -= 5000;
        }
    }
    
    // Factor in safety
    var eid = calculateEID(cell);
    score -= eid * 0.3;
    
    // Prefer optimal distances
    if (distToEnemy == 8) score += 200;  // Perfect rifle range
    
    // RESOURCE PRESSURE BONUS: Positions that force enemy repositioning
    if (turn >= 3 && myTP >= 14) {
        // Positions that break enemy optimal range
        if (distToEnemy > 9 || distToEnemy < 7) {
            score += 300;  // Force them out of rifle range
        }
        
        // Positions behind cover that they can't easily reach
        if (!hasLOS(enemyCell, cell)) {
            var enemyReachable = getReachableCells(enemyCell, 6);  // Assume 6 MP
            var canEnemyReachUs = false;
            for (var i = 0; i < min(10, count(enemyReachable)); i++) {
                var enemyOption = enemyReachable[i];
                var enemyNewDist = getCellDistance(enemyOption, cell);
                if (hasLOS(enemyOption, cell) && enemyNewDist >= 7 && enemyNewDist <= 9) {
                    canEnemyReachUs = true;
                    break;
                }
            }
            if (!canEnemyReachUs) {
                score += 500;  // They'll waste TP trying to get LOS
            }
        }
    }
    
    return score;
}


// Function: executeTeleport
function executeTeleport(targetCell) {
    var currentCell = getCell();
    if (targetCell == currentCell) {
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Teleport target is current cell - aborting");
        }
        return false;
    }
    
    // Final check: NEVER teleport to walkable cells
    var path = getPath(currentCell, targetCell);
    if (path != null && count(path) <= getMP()) {
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("❌ BLOCKED: Target is walkable in " + count(path) + " MP - walking instead!");
        }
        moveToward(targetCell, getMP());
        return false;
    }
    if (debugEnabled && canSpendOps(1000)) {
		debugLog("🌀 Teleporting from " + currentCell + " to " + targetCell);
    }
    
    // Visual debugging BEFORE teleport
    mark(currentCell, COLOR_CAUTION);  // Yellow for source
    mark(targetCell, COLOR_SAFE);  // Green for destination
    // Note: drawLine doesn't exist in LeekScript, using marks only
    
    // Double-check we have the chip before trying to use it
    if (!inArray(getChips(), CHIP_TELEPORTATION)) {
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("ERROR: Teleportation chip not equipped!");
        }
        return false;
    }
    var result = useChipOnCell(CHIP_TELEPORTATION, targetCell);
    if (result == USE_SUCCESS) {
        myTP -= 9;
        
        // Update positions
        myCell = getCell();
        enemyCell = getCell(enemy);
        enemyDistance = getCellDistance(myCell, enemyCell);
        TELEPORT_LAST_USED = turn;
        
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("✅ Teleported successfully! New position: " + myCell + ", distance: " + enemyDistance);
        }
        
        // NOW CHECK IF WE NEED TO MOVE TO ATTACK!
        var canAttackNow = false;
        if (hasLOS(myCell, enemyCell)) {
            if ((enemyDistance >= 7 && enemyDistance <= 9) ||
                (enemyDistance >= 5 && enemyDistance <= 12 && isOnSameLine(myCell, enemyCell)) ||
                (enemyDistance >= 4 && enemyDistance <= 7)) {
                canAttackNow = true;
            }
        } else if (enemyDistance == 1) {
            canAttackNow = true;
        }
        
        // If we can't attack, MOVE towards attack position!
        if (!canAttackNow && getMP() > 0) {
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("📍 Can't attack yet, moving to attack position...");
            }
            
            // Find nearest attack position
            var attackPos = findNearestAttackPosition();
            if (attackPos != null && attackPos != myCell) {
                var movePath = getPath(myCell, attackPos);
                if (movePath != null && count(movePath) > 0) {
                    // Visual debug: show movement path
                    for (var p = 0; p < min(getMP(), count(movePath)); p++) {
                        mark(movePath[p], COLOR_BLUE);  // Blue for movement path
                    }
                    
                    // Move as far as we can
                    var steps = min(getMP(), count(movePath));
                    moveToward(attackPos, steps);
                    
                    // Update position again
                    myCell = getCell();
                    enemyDistance = getCellDistance(myCell, enemyCell);
                    if (debugEnabled && canSpendOps(1000)) {
		debugLog("➡️ Moved to " + myCell + ", final distance: " + enemyDistance);
                    }
                }
            }
        }
        
        return true;
    }
    
    if (debugEnabled && canSpendOps(1000)) {
		debugLog("❌ Teleport failed with error: " + result);
    }
    return false;
}


// Helper: Find nearest position from which we can attack
function findNearestAttackPosition() {
    var myPos = getCell();
    var enemyPos = getCell(enemy);
    var reachable = getReachableCells(myPos, getMP());
    
    var bestCell = null;
    var bestDist = 999;
    
    for (var i = 0; i < count(reachable); i++) {
        var cell = reachable[i];
        var dist = getCellDistance(cell, enemyPos);
        
        var canAttack = false;
        if (hasLOS(cell, enemyPos)) {
            if ((dist >= 7 && dist <= 9) ||  // Rifle
                (dist >= 5 && dist <= 12 && isOnSameLine(cell, enemyPos)) ||  // M-Laser
                (dist >= 4 && dist <= 7)) {  // Grenade
                canAttack = true;
            }
        } else if (dist == 1) {  // Melee
            canAttack = true;
        }
        
        if (canAttack) {
            var pathDist = count(getPath(myPos, cell));
            if (pathDist < bestDist) {
                bestDist = pathDist;
                bestCell = cell;
            }
        }
    }
    
    if (bestCell != null) {
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Found attack position at " + bestCell + " (" + bestDist + " MP away)");
        }
    }
    
    return bestCell;
}


// Function: evaluateTeleportValue
function evaluateTeleportValue() {
    var currentCell = getCell();
    var currentDamage = calculateDamageFrom(currentCell);
    var bestTeleportCell = findBestTeleportTarget();
    var teleportDamage = calculateDamageFrom(bestTeleportCell);
    
    var damageGain = teleportDamage - currentDamage;
    var safetyGain = calculateEID(currentCell) - calculateEID(bestTeleportCell);
    
    return damageGain * 2 + safetyGain * 3;
}
