// V6 Module: movement/positioning.ls
// Movement and positioning
// Auto-generated from V5.0 script

// Function: bestApproachStep
function bestApproachStep(towardCell) {
    // Try A* pathfinding first if we have ops
    var currentMode = getOperationLevel();
    if ((currentMode == "OPTIMAL" || currentMode == "EFFICIENT") && canSpendOps(20000)) {
        var path = findBestPathTo(towardCell, myMP);
        if (path != null && count(path) > 0) {
            // Return the furthest cell we can reach along the path
            return path[count(path) - 1];
        }
    }
    
    // Fall back to simple evaluation
    var reach = getReachableCells(myCell, myMP);
    var best = myCell;
    var bestScore = -999999;
    
    for (var i = 0; i < count(reach); i++) {
        var c = reach[i];
        var d = getCellDistance(c, towardCell);
        var los = hasLOS(c, enemyCell) ? 1 : 0;
        var score = -d * 25 + los * 40 - abs(getCellDistance(c, enemyCell) - optimalAttackRange) * 20;
        if (score > bestScore) {
            bestScore = score;
            best = c;
        }
    }
    return best;
}

// === DECISION MAKING ===

// Function: moveToCell
function moveToCell(targetCell) {
    if (targetCell == myCell) return 0;
    
    // Use A* pathfinding for optimal movement
    var useAStar = shouldUseAlgorithm(30000);
    
    if (useAStar) {
        // Try A* pathfinding first
        var path = findBestPathTo(targetCell, myMP);
        
        if (path != null && count(path) > 0) {
            // Move along the path
            var mpUsed = 0;
            for (var i = 0; i < count(path); i++) {
                var step = path[i];
                var moved = moveTowardCell(step);
                if (moved > 0) {
                    mpUsed += moved;
                    myMP -= moved;
                    myCell = getCell();
                } else {
                    break;  // Can't move further
                }
            }
            
            if (mpUsed > 0) {
                debugLog("A* moved " + mpUsed + " MP toward target");
            }
            return mpUsed;
        }
    }
    
    // Fall back to direct movement
    var mpUsed = moveTowardCell(targetCell);
    if (mpUsed > 0) {
        myMP -= mpUsed;
        myCell = getCell();
    }
    
    return mpUsed;
}

// === POSITION FINDING ===
// Find all cells from which we can hit the enemy (calculated from enemy position)
// Returns array of [cell, bestWeapon, damageAtRange]

// Function: repositionDefensive
function repositionDefensive() {
    var safeCells = findSafeCells();
    
    if (count(safeCells) == 0) {
        // No strictly safe cells - find the LEAST dangerous cell
        var reachable = getReachableCells(myCell, myMP);
        var leastBadCell = myCell;
        var lowestEID = eidOf(myCell);
        
        // Find cell with minimum EID
        for (var i = 0; i < min(30, count(reachable)); i++) {
            if (!canSpendOps(5000)) break;
            var cell = reachable[i];
            var cellEID = eidOf(cell);
            if (cellEID < lowestEID) {
                lowestEID = cellEID;
                leastBadCell = cell;
            }
        }
        
        // If we found a better cell, use it as our "safe" option
        if (leastBadCell != myCell) {
            safeCells = [leastBadCell];
            debugLog("No safe cells found, using least dangerous: EID=" + lowestEID);
        }
    }
    
    if (count(safeCells) == 0) {
        // FALLBACK: Move to maintain 3-7 range (Rhino/Grenade/Lightninger coverage)
        var reachable = getReachableCells(myCell, myMP);
        var bestCell = myCell;
        var bestScore = -999999;
        
        for (var i = 0; i < min(30, count(reachable)); i++) {
            var cell = reachable[i];
            var dist = getCellDistance(cell, enemyCell);
            var score = 0;
            
            // Ideal kiting distance: 7-9 (can use all weapons)
            if (dist >= 7 && dist <= 9) {
                score += 1000;  // Perfect kiting range
            } else if (dist >= 6 && dist <= 10) {
                score += 500;   // Good kiting range
            } else if (dist > 10) {
                score += dist * 10;  // Further is safer but less damage
            }
            
            // Check if we can attack from this position
            if (hasLOS(cell, enemyCell)) {
                score += 300;
            }
            
            if (score > bestScore) {
                bestScore = score;
                bestCell = cell;
            }
        }
        
        if (bestCell != myCell) {
            var newDist = getCellDistance(bestCell, enemyCell);
            debugLog("Kiting to distance " + newDist);
            if (moveToCell(bestCell) > 0) {
                enemyDistance = getCellDistance(myCell, enemyCell);
                debugLog("New distance after kiting: " + enemyDistance);
            }
        }
    } else {
        // Move to safest cell that can still hit (KITING)
        var bestCell = myCell;
        var bestScore = -999999;
        
        for (var i = 0; i < count(safeCells); i++) {
            var cell = safeCells[i];
            var damage = calculateDamageFrom(cell);
            var eid = eidOf(cell);
            var dist = getCellDistance(cell, enemyCell);
            
            // Prefer cells where we can attack (kiting)
            var score = damage * 2 - eid * 3;  // Balance damage and safety
            
            // Bonus for ideal kiting range
            if (dist >= 6 && dist <= 10) {
                score += 500;  // Can use Lightninger
            }
            if (dist == 7) {
                score += 250;  // Good attack range
            }
            
            if (score > bestScore) {
                bestScore = score;
                bestCell = cell;
            }
        }
        
        if (bestCell != myCell) {
            if (moveToCell(bestCell) > 0) {
                enemyDistance = getCellDistance(myCell, enemyCell);
            }
        }
    }
}

