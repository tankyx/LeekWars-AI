// V6 Module: movement/teleportation.ls
// Teleportation tactics
// Auto-generated from V5.0 script

// Function: shouldUseTeleport
function shouldUseTeleport() {
    if (!TELEPORT_AVAILABLE || myTP < 9) return false;
    
    // Scenario 1: BAZOOKA DANGER - Teleport immediately if in Bazooka kill range
    if (ENEMY_HAS_BAZOOKA && enemyDistance >= 4 && enemyDistance <= 7) {
        debugLog("💣 BAZOOKA DANGER! Distance " + enemyDistance + " - must teleport!");
        return true;
    }
    
    // Scenario 2: Emergency escape when taking heavy damage
    var myEHP = calculateEHP(myHP, myAbsShield, myRelShield, 0, myResistance);
    var currentEID = calculateEID(myCell);
    if (currentEID >= myEHP * 0.6 || myHP < myMaxHP * 0.4) {
        debugLog("🚨 Emergency teleport! EID=" + currentEID + " vs EHP=" + myEHP);
        return true;
    }
    
    // Scenario 3: Too close to STR enemy
    if (ENEMY_TYPE == "STR" && enemyDistance <= 5) {
        debugLog("⚠️ Too close to STR enemy! Distance " + enemyDistance);
        return true;
    }
    
    // Scenario 4: Break hide-and-seek - enemy is out of all attack range
    if (enemyDistance > 12 && !canAttackFromPosition(myCell)) {
        debugLog("🎯 Teleport to reach hiding enemy at distance " + enemyDistance);
        return true;
    }
    
    return false;
}


// Function: findBestTeleportTarget
function findBestTeleportTarget() {
    // Get all cells within teleport range (1-12, no LOS needed)
    var candidates = [];
    for (var dist = 1; dist <= 12; dist++) {
        var cellsAtDist = getCellsAtDistance(myCell, dist);
        for (var i = 0; i < count(cellsAtDist); i++) {
            var cell = cellsAtDist[i];
            if (cell != -1 && !isObstacle(cell) && cell != enemyCell) {
                push(candidates, cell);
            }
        }
    }
    
    var bestCell = myCell;
    var bestScore = -999999;
    
    for (var i = 0; i < min(50, count(candidates)); i++) {
        var cell = candidates[i];
        var score = 0;
        
        // Factor 1: Safety (negative EID)
        var eid = calculateEID(cell);
        score -= eid * 2;
        
        // Factor 2: Attack potential
        var damage = calculateDamageFrom(cell);
        score += damage * 3;
        
        // Factor 3: Distance to optimal range
        var distToEnemy = getCellDistance(cell, enemyCell);
        var rangePenalty = abs(distToEnemy - optimalAttackRange);
        score -= rangePenalty * 100;
        
        // Factor 4: Can we attack from there?
        if (hasLOS(cell, enemyCell) && distToEnemy <= 10) {
            score += 500;
        }
        
        if (score > bestScore) {
            bestScore = score;
            bestCell = cell;
        }
    }
    
    return bestCell;
}


// Function: executeTeleport
function executeTeleport(targetCell) {
    if (targetCell == myCell) return false;
    
    var result = useChipOnCell(CHIP_TELEPORTATION, targetCell);
    if (result == USE_SUCCESS) {
        myTP -= 9;
        myCell = getCell();
        enemyDistance = getCellDistance(myCell, enemyCell);
        TELEPORT_LAST_USED = turn;
        debugLog("🌀 Teleported to cell " + targetCell + ", new distance: " + enemyDistance);
        return true;
    }
    return false;
}


// Function: evaluateTeleportValue
function evaluateTeleportValue() {
    // Calculate the value of using teleport this turn vs saving it
    var currentDamage = calculateDamageFrom(myCell);
    var bestTeleportCell = findBestTeleportTarget();
    var teleportDamage = calculateDamageFrom(bestTeleportCell);
    
    // Value = damage gain + safety gain
    var damageGain = teleportDamage - currentDamage;
    var safetyGain = calculateEID(myCell) - calculateEID(bestTeleportCell);
    
    return damageGain * 2 + safetyGain * 3;
}

