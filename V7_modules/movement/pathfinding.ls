// V7 Module: movement/pathfinding.ls
// A* pathfinding to optimal damage cells

// === MAIN PATHFINDING FUNCTION (ARRAY-BASED) ===
function findOptimalPathFromArray(currentCell, damageArray) {
    if (debugEnabled) {
        debugW("PATHFIND ARRAY: " + count(damageArray) + " entries");
    }
    
    // Sort array by damage potential (highest first)
    var sortedArray = sortArrayByDamage(damageArray);
    
    // Try single-turn A* first to each high-damage cell
    for (var i = 0; i < min(MAX_PATHFIND_CELLS, count(sortedArray)); i++) {
        var targetData = sortedArray[i];
        var targetCell = targetData[0];
        var expectedDamage = targetData[1];
        
        var path = aStar(currentCell, targetCell, myMP);
        
        if (path != null && count(path) <= myMP + 1) {
            // Mark chosen path with text indicators
            if (debugEnabled) {
                for (var p = 0; p < count(path); p++) {
                    markText(path[p], ">" + p, getColor(255, 165, 0), 10); // Orange path steps
                }
                markText(targetCell, "!" + floor(expectedDamage + 0.5), getColor(255, 0, 0), 10); // Target with damage
                debug("Path found: " + count(path) + " steps to damage " + expectedDamage);
            }
            
            return {
                targetCell: targetCell,
                path: path,
                damage: expectedDamage,
                reachable: true,
                distance: count(path) - 1
            };
        }
    }
    
    // No single-turn path found - try multi-turn pathfinding
    var multiTurnResult = findMultiTurnPath(currentCell, sortedArray);
    if (multiTurnResult != null) {
        return multiTurnResult;
    }
    
    // No high-damage cell reachable - find max damage from array
    var maxDamage = 0;
    for (var i = 0; i < count(damageArray); i++) {
        var damage = damageArray[i][1];
        if (damage > maxDamage) {
            maxDamage = damage;
        }
    }
    
    // If all damage is 0, move toward enemy to get in weapon range
    if (debugEnabled) {
        debugW("PATHFIND ARRAY: maxDamage = " + maxDamage + ", sorted cells count = " + count(sortedArray));
    }
    
    if (maxDamage == 0) {
        // Check if we have M-Laser and should seek alignment
        var weapons = getWeapons();
        if (inArray(weapons, WEAPON_M_LASER)) {
            var alignmentTarget = findMLaserAlignmentPosition();
            if (alignmentTarget != null) {
                if (debugEnabled) {
                    debugW("PATHFIND ARRAY: Seeking M-Laser alignment position " + alignmentTarget);
                }
                var pathToAlignment = aStar(currentCell, alignmentTarget, myMP);
                if (pathToAlignment != null && count(pathToAlignment) > 1) {
                    var moveToCell = pathToAlignment[min(myMP, count(pathToAlignment) - 1)];
                    
                    return {
                        targetCell: moveToCell,
                        path: pathToAlignment,
                        damage: 0,
                        reachable: getCellDistance(currentCell, moveToCell) <= myMP,
                        distance: getCellDistance(currentCell, moveToCell)
                    };
                }
            }
        }
        
        // Move toward enemy when no damage zones available
        if (debugEnabled) {
            debugW("PATHFIND ARRAY: No damage zones, moving toward enemy from " + currentCell + " to " + enemyCell);
        }
        
        var pathToEnemy = aStar(currentCell, enemyCell, myMP);
        if (pathToEnemy != null && count(pathToEnemy) > 1) {
            var moveToCell = pathToEnemy[min(myMP, count(pathToEnemy) - 1)];
            
            return {
                targetCell: moveToCell,
                path: pathToEnemy,
                damage: 0,
                reachable: false,
                distance: min(myMP, count(pathToEnemy) - 1)
            };
        }
    }
    
    // Check if we should use teleportation due to low HP (late-game positioning)
    var currentHPPercent = getLife() / getTotalLife();
    var shouldUseTeleport = false;
    
    // Trigger teleportation if:
    // 1. HP < 40% (late-game threshold)
    // 2. No high-damage paths were found
    if (currentHPPercent < 0.4 && maxDamage > 0) {
        shouldUseTeleport = true;
        if (debugEnabled) {
            debugW("LATE-GAME TELEPORT: HP=" + floor(currentHPPercent * 100) + "% < 40%, trying teleportation for positioning");
        }
    }
    
    // Last resort: Try teleport + movement fallback (or forced teleport for late-game)
    if (shouldUseTeleport || maxDamage == 0) {
        if (debugEnabled) {
            var reason = shouldUseTeleport ? "Late-game positioning" : "No paths found";
            debugW("PATHFIND FALLBACK: " + reason + ", trying teleport + movement");
        }
        
        var teleportResult = tryTeleportMovementFallback(currentCell, damageArray);
        if (teleportResult != null) {
            return teleportResult;
        }
    }
    
    // Return null if no path found
    return null;
}

// === ARRAY SORTING FUNCTION ===
function sortArrayByDamage(damageArray) {
    if (debugEnabled) {
        debugW("SORT ARRAY: " + count(damageArray) + " entries");
    }
    
    // Make a copy to avoid modifying original array
    var sortedArray = [];
    for (var i = 0; i < count(damageArray); i++) {
        var entry = damageArray[i];
        var cellId = entry[0];
        var damage = entry[1];
        
        // Validate cell and damage
        if (cellId >= 0 && cellId <= 612 && damage > 0) {
            push(sortedArray, [cellId, damage]);
        } else if (debugEnabled && i < 3) {
            debugW("SORT REJECT: cell=" + cellId + ", damage=" + damage);
        }
    }
    
    // Sort by damage (highest first) - manual bubble sort
    for (var i = 0; i < count(sortedArray) - 1; i++) {
        for (var j = 0; j < count(sortedArray) - 1 - i; j++) {
            if (sortedArray[j][1] < sortedArray[j + 1][1]) {
                var temp = sortedArray[j];
                sortedArray[j] = sortedArray[j + 1];
                sortedArray[j + 1] = temp;
            }
        }
    }
    
    if (debugEnabled) {
        debugW("SORT COMPLETE: " + count(sortedArray) + " sorted entries");
        for (var i = 0; i < min(3, count(sortedArray)); i++) {
            var entry = sortedArray[i];
            debugW("TOP DAMAGE[" + i + "]: cell=" + entry[0] + ", damage=" + entry[1]);
        }
    }
    
    return sortedArray;
}

// === MAIN PATHFINDING FUNCTION (MAP-BASED - LEGACY) ===
function findOptimalPath(currentCell, damageZones) {
    // Sort cells by damage potential (highest first)
    var sortedCells = sortCellsByDamage(damageZones);
    
    // Try A* to each high-damage cell until we find a reachable one
    for (var i = 0; i < min(MAX_PATHFIND_CELLS, count(sortedCells)); i++) {
        var targetData = sortedCells[i];
        var targetCell = targetData[0];
        var expectedDamage = targetData[1];
        
        var path = aStar(currentCell, targetCell, myMP);
        
        if (path != null && count(path) <= myMP + 1) {
            // Mark chosen path in bright orange
            // TEMPORARILY DISABLED: Testing if mark() corrupts the map
            if (debugEnabled) {
                // for (var p = 0; p < count(path); p++) {
                //     mark(path[p], getColor(255, 165, 0)); // Orange color
                // }
                // mark(targetCell, getColor(255, 0, 0)); // Bright red for final target
                debug("Path found: " + count(path) + " steps to damage " + expectedDamage);
            }
            
            return {
                targetCell: targetCell,
                path: path,
                damage: expectedDamage,
                reachable: true,
                distance: count(path) - 1
            };
        }
    }
    
    // No high-damage cell reachable - check if all damage zones are 0
    var maxDamage = 0;
    for (var cell in damageZones) {
        var damage = damageZones[cell] + 0; // Convert to number
        if (damage > maxDamage) {
            maxDamage = damage;
        }
    }
    
    // If all damage is 0, move toward enemy to get in weapon range
    if (debugEnabled) {
        debugW("PATHFINDING: maxDamage = " + maxDamage + ", sorted cells count = " + count(sortedCells));
    }
    if (maxDamage == 0) {
        if (debugEnabled) {
            debugW("MOVING TOWARD ENEMY: currentCell=" + currentCell + ", enemyCell=" + enemyCell + ", myMP=" + myMP);
        }
        var moveTowardEnemy = aStar(currentCell, enemyCell, myMP);
        if (moveTowardEnemy != null && count(moveTowardEnemy) > 1) {
            var moveToCell = moveTowardEnemy[min(myMP, count(moveTowardEnemy) - 1)];
            
            if (debugEnabled) {
                debugW("No damage zones found, moving toward enemy from " + currentCell + " to " + moveToCell);
            }
            
            return {
                targetCell: moveToCell,
                path: arraySlice(moveTowardEnemy, 0, min(myMP + 1, count(moveTowardEnemy))),
                damage: 0,
                reachable: false,
                distance: min(myMP, count(moveTowardEnemy) - 1)
            };
        } else {
            // A* failed, try simple directional movement
            var simplePath = findMultiStepMovementToward(currentCell, enemyCell, myMP);
            if (simplePath != null && count(simplePath) > 1) {
                return {
                    targetCell: simplePath[count(simplePath) - 1],
                    path: simplePath,
                    damage: 0,
                    reachable: false,
                    distance: count(simplePath) - 1
                };
            }
        }
    }
    
    // Move toward best damage zone (even if 0)
    if (count(sortedCells) > 0) {
        var bestCell = sortedCells[0][0];
        var partialPath = aStar(currentCell, bestCell, myMP);
        
        if (partialPath != null && count(partialPath) > 1) {
            var moveToCell = partialPath[min(myMP + 1, count(partialPath) - 1)];
            return {
                targetCell: moveToCell,
                path: arraySlice(partialPath, 0, min(myMP + 1, count(partialPath))),
                damage: sortedCells[0][1],
                reachable: false,
                distance: min(myMP, count(partialPath) - 1)
            };
        }
    }
    
    // Fallback: stay in place
    return {
        targetCell: currentCell,
        path: [currentCell],
        damage: (damageZones[currentCell] + 0) || 0,
        reachable: true,
        distance: 0
    };
}

// === CELL SORTING BY DAMAGE ===
function sortCellsByDamage(damageZones) {
    var cellArray = [];
    
    var debugCount = 0;
    for (var cell in damageZones) {
        if (debugEnabled && debugCount < 3) {
            debugW("SIMPLE SORT DEBUG: cell=" + cell + ", damage=" + damageZones[cell]);
            debugCount++;
        }
        
        // Use cell ID directly
        var cellId = cell + 0;  // Convert to number
        if (cellId != null && !isNaN(cellId) && cellId >= 0 && cellId <= 612) {
            var damage = damageZones[cell] + 0; // Convert damage to number
            push(cellArray, [cellId, damage]);
        } else if (debugEnabled && debugCount < 3) {
            debugW("SORT REJECT: Invalid cell " + cell + " -> " + cellId);
        }
    }
    
    if (debugEnabled) {
        debugW("SORT RESULT: " + count(cellArray) + " valid cells to sort");
    }
    
    // Sort by damage (highest first) - manual bubble sort
    for (var i = 0; i < count(cellArray) - 1; i++) {
        for (var j = 0; j < count(cellArray) - 1 - i; j++) {
            if (cellArray[j][1] < cellArray[j + 1][1]) {
                var temp = cellArray[j];
                cellArray[j] = cellArray[j + 1];
                cellArray[j + 1] = temp;
            }
        }
    }
    
    return cellArray;
}

// === A* PATHFINDING IMPLEMENTATION ===
function aStar(startCell, goalCell, maxDistance) {
    // Check cache first
    var cacheKey = startCell + "_" + goalCell + "_" + maxDistance;
    if (pathCache[cacheKey] != null) {
        return pathCache[cacheKey];
    }
    
    
    var openSet = [startCell];
    var cameFrom = [:];
    var gScore = [:];
    var fScore = [:];
    
    gScore[startCell] = 0;
    fScore[startCell] = heuristic(startCell, goalCell);
    
    var searchCount = 0;
    var maxSearchSteps = 100; // Prevent infinite loops
    
    while (count(openSet) > 0 && searchCount < maxSearchSteps) {
        searchCount++;
        // Find node with lowest fScore
        var current = openSet[0];
        var currentIndex = 0;
        for (var i = 1; i < count(openSet); i++) {
            if (fScore[openSet[i]] < fScore[current]) {
                current = openSet[i];
                currentIndex = i;
            }
        }
        
        // Remove current from openSet
        // Remove current from openSet by shifting elements
        for (var k = currentIndex; k < count(openSet) - 1; k++) {
            openSet[k] = openSet[k + 1];
        }
        // Remove last element
        var newOpenSet = [];
        for (var m = 0; m < count(openSet) - 1; m++) {
            push(newOpenSet, openSet[m]);
        }
        openSet = newOpenSet;
        
        // Goal reached
        if (current == goalCell) {
            var path = reconstructPath(cameFrom, current);
            pathCache[cacheKey] = path;
            return path;
        }
        
        // Don't search beyond max distance (AFTER goal check)
        if (gScore[current] > maxDistance) continue;
        
        // Check neighbors
        var neighbors = getWalkableNeighbors(current);
        for (var i = 0; i < count(neighbors); i++) {
            var neighbor = neighbors[i];
            var tentativeGScore = gScore[current] + 1;
            
            if (gScore[neighbor] == null || tentativeGScore < gScore[neighbor]) {
                cameFrom[neighbor] = current;
                gScore[neighbor] = tentativeGScore;
                fScore[neighbor] = gScore[neighbor] + heuristic(neighbor, goalCell);
                
                if (!inArray(openSet, neighbor)) {
                    push(openSet, neighbor);
                }
            }
        }
    }
    
    // No path found
    pathCache[cacheKey] = null;
    return null;
}

// === M-LASER ALIGNMENT SEEKING ===
function findMLaserAlignmentPosition() {
    // Find the best position to align M-Laser with enemy
    var enemyX = getCellX(enemyCell);
    var enemyY = getCellY(enemyCell);
    var myX = getCellX(myCell);
    var myY = getCellY(myCell);
    
    var bestTarget = null;
    var bestScore = 0;
    
    if (debugEnabled) {
        debugW("=== M-LASER ALIGNMENT SEARCH ===");
        debugW("Enemy at (" + enemyX + "," + enemyY + "), seeking X/Y axis alignment");
    }
    
    // Check cells on same X axis as enemy (vertical line)
    for (var y = enemyY - 10; y <= enemyY + 10; y++) {
        var cell = getCellFromXY(enemyX, y);
        if (cell != null && cell != -1 && cell != enemyCell) {
            var score = evaluateMLaserPosition(cell);
            if (score > bestScore) {
                bestScore = score;
                bestTarget = cell;
                if (debugEnabled) {
                    debugW("M-Laser vertical: Cell " + cell + " (" + enemyX + "," + y + ") score: " + score);
                }
            }
        }
    }
    
    // Check cells on same Y axis as enemy (horizontal line)
    for (var x = enemyX - 10; x <= enemyX + 10; x++) {
        var cell = getCellFromXY(x, enemyY);
        if (cell != null && cell != -1 && cell != enemyCell) {
            var score = evaluateMLaserPosition(cell);
            if (score > bestScore) {
                bestScore = score;
                bestTarget = cell;
                if (debugEnabled) {
                    debugW("M-Laser horizontal: Cell " + cell + " (" + x + "," + enemyY + ") score: " + score);
                }
            }
        }
    }
    
    if (bestTarget != null && debugEnabled) {
        debugW("BEST M-LASER POSITION: Cell " + bestTarget + " (score: " + bestScore + ")");
        markText(bestTarget, "M-LASER", getColor(255, 255, 0), 8);
    }
    
    return bestTarget;
}

function evaluateMLaserPosition(cell) {
    var distance = getCellDistance(cell, enemyCell);
    
    // Must be in M-Laser range (6-10)
    if (distance < 6 || distance > 10) return 0;
    
    // Must be walkable
    var isWalkable = (getCellContent(cell) == CELL_EMPTY);
    if (!isWalkable) return 0;
    
    // Must have LOS to enemy
    if (!hasLOS(cell, enemyCell)) return 0;
    
    var score = 0;
    
    // Base score: favor optimal range (7-9 for M-Laser)
    if (distance >= 7 && distance <= 9) {
        score += 50; // Optimal range bonus
    } else {
        score += 20; // Still in range bonus
    }
    
    // Reachability bonus (closer to current position is better)
    var reachability = max(0, 15 - getCellDistance(myCell, cell));
    score += reachability;
    
    // Cover bonus - check adjacent cells for obstacles
    var coverBonus = 0;
    var adjacentCells = getCellsAtDistance(cell, 1);
    for (var i = 0; i < count(adjacentCells); i++) {
        var adjCell = adjacentCells[i];
        if (getCellContent(adjCell) == CELL_OBSTACLE) {
            coverBonus += 2; // Small bonus for each adjacent obstacle
        }
    }
    score += min(coverBonus, 8); // Cap cover bonus at 8
    
    // Penalty for being on same line as current position (avoids minimal movement)
    if (isOnSameLine(myCell, cell)) {
        score -= 5;
    }
    
    return score;
}

// === PATHFINDING UTILITIES ===
function heuristic(cellA, cellB) {
    // Manhattan distance heuristic
    return getCellDistance(cellA, cellB);
}

function reconstructPath(cameFrom, current) {
    var path = [current];
    
    while (cameFrom[current] != null) {
        current = cameFrom[current];
        unshift(path, current);
    }
    
    return path;
}

function getWalkableNeighbors(cell) {
    var neighbors = [];
    var x = getCellX(cell);
    var y = getCellY(cell);
    
    var directions = [
        [0, 1], [0, -1], [1, 0], [-1, 0]  // North, South, East, West
    ];
    
    for (var i = 0; i < count(directions); i++) {
        var dir = directions[i];
        var neighborCell = getCellFromXY(x + dir[0], y + dir[1]);
        
        // Enhanced walkability checks with debugging
        if (neighborCell != null && neighborCell != -1 && neighborCell >= 0 && neighborCell <= 612) {
            // Check if cell is empty and not an obstacle
            var isEmpty = isEmptyCell(neighborCell);
            var isObst = isObstacle(neighborCell);
            
            
            // Simplified walkability check: only use isEmpty
            if (isEmpty) {
                push(neighbors, neighborCell);
            }
        }
    }
    
    return neighbors;
}

// === SIMPLE MOVEMENT (FALLBACK) ===
function findMultiStepMovementToward(fromCell, toCell, maxMP) {
    var path = [fromCell];
    var currentCell = fromCell;
    
    for (var step = 0; step < maxMP; step++) {
        var nextCell = findSimpleMovementToward(currentCell, toCell, 1);
        if (nextCell == null || nextCell == currentCell) {
            if (debugEnabled) {
                debugW("MULTI-STEP: Step " + step + " blocked, trying alternative");
            }
            // Try alternative directions if blocked
            nextCell = findAlternativeMovement(currentCell, toCell);
            if (nextCell == null || nextCell == currentCell) {
                break; // Really can't move further
            }
        }
        push(path, nextCell);
        currentCell = nextCell;
        
        // Stop if we've reached the target
        if (currentCell == toCell) {
            break;
        }
    }
    
    if (debugEnabled) {
        debugW("MULTI-STEP PATH: " + count(path) + " steps, from " + fromCell + " to " + currentCell);
    }
    
    return (count(path) > 1) ? path : null;
}

function findSimpleMovementToward(fromCell, toCell, maxMP) {
    var fromX = getCellX(fromCell);
    var fromY = getCellY(fromCell);
    var toX = getCellX(toCell);
    var toY = getCellY(toCell);
    
    if (debugEnabled) {
        debugW("SIMPLE MOVE: from (" + fromX + "," + fromY + ") to (" + toX + "," + toY + ")");
    }
    
    // Try moving directly toward enemy
    var deltaX = toX - fromX;
    var deltaY = toY - fromY;
    
    // Normalize to get direction
    var dirX = (deltaX > 0) ? 1 : ((deltaX < 0) ? -1 : 0);
    var dirY = (deltaY > 0) ? 1 : ((deltaY < 0) ? -1 : 0);
    
    // Try the direction with the largest delta first (greedy approach)
    var tryX = (abs(deltaX) >= abs(deltaY));
    
    if (tryX && dirX != 0) {
        var targetCell = getCellFromXY(fromX + dirX, fromY);
        if (targetCell != null && targetCell != -1) {
            if (debugEnabled) {
                debugW("SIMPLE MOVE: X direction to " + targetCell);
            }
            return targetCell;
        }
    }
    
    if (!tryX && dirY != 0) {
        var targetCell = getCellFromXY(fromX, fromY + dirY);
        if (targetCell != null && targetCell != -1) {
            if (debugEnabled) {
                debugW("SIMPLE MOVE: Y direction to " + targetCell);
            }
            return targetCell;
        }
    }
    
    // Try the other direction if first choice failed
    if (tryX && dirY != 0) {
        var targetCell = getCellFromXY(fromX, fromY + dirY);
        if (targetCell != null && targetCell != -1) {
            if (debugEnabled) {
                debugW("SIMPLE MOVE: Y direction to " + targetCell + " (fallback)");
            }
            return targetCell;
        }
    }
    
    if (!tryX && dirX != 0) {
        var targetCell = getCellFromXY(fromX + dirX, fromY);
        if (targetCell != null && targetCell != -1) {
            if (debugEnabled) {
                debugW("SIMPLE MOVE: X direction to " + targetCell + " (fallback)");
            }
            return targetCell;
        }
    }
    
    if (debugEnabled) {
        debugW("SIMPLE MOVE: No valid directions found");
    }
    return null;
}

// === MOVEMENT EXECUTION ===
function executeMovement(pathResult) {
    if (pathResult == null) {
        return; // No movement needed
    }
    
    // Handle teleport + movement combo
    if (pathResult.useTeleport) {
        if (debugEnabled) {
            debugW("EXECUTE TELEPORT: Using teleportation to " + pathResult.teleportCell);
        }
        
        var chips = getChips();
        if (inArray(chips, CHIP_TELEPORTATION) && canUseChip(CHIP_TELEPORTATION, pathResult.teleportCell)) {
            useChip(CHIP_TELEPORTATION, pathResult.teleportCell);
            
            // Update position after teleport
            myCell = getCell();
            myMP = getMP(); // MP should be unchanged after teleport
            
            if (debugEnabled) {
                debugW("TELEPORT SUCCESS: Now at " + myCell + " with " + myMP + " MP remaining");
            }
            
            // If target cell is different from teleport cell, move there
            if (pathResult.targetCell != pathResult.teleportCell) {
                var pathAfterTeleport = aStar(myCell, pathResult.targetCell, myMP);
                if (pathAfterTeleport != null && count(pathAfterTeleport) > 1) {
                    executeNormalMovement({path: pathAfterTeleport, targetCell: pathResult.targetCell});
                }
            }
        } else {
            if (debugEnabled) {
                debugW("TELEPORT FAILED: Cannot use teleportation chip");
            }
        }
        return;
    }
    
    // Normal movement execution
    executeNormalMovement(pathResult);
}

function executeNormalMovement(pathResult) {
    if (pathResult == null || pathResult.path == null || count(pathResult.path) <= 1) {
        return; // No movement needed
    }
    
    var path = pathResult.path;
    var mpRemaining = myMP;
    
    // Execute movement along path
    for (var i = 1; i < count(path) && mpRemaining > 0; i++) {
        var targetCell = path[i];
        
        var mpUsed = moveTowardCells([targetCell], 1);
        if (mpUsed > 0) {
            mpRemaining -= mpUsed;
            if (debugEnabled) {
                debugW("Moved to " + targetCell + " (MP used: " + mpUsed + ", remaining: " + mpRemaining + ")");
            }
        } else {
            if (debugEnabled) {
                debugW("Movement blocked to " + targetCell + ", trying alternative");
            }
            // Try alternative movement when blocked
            var currentPos = getCell();
            var alternative = findAlternativeMovement(currentPos, targetCell);
            if (alternative != null) {
                var altMpUsed = moveTowardCells([alternative], 1);
                if (altMpUsed > 0) {
                    mpRemaining -= altMpUsed;
                    if (debugEnabled) {
                        debugW("Alternative move to " + alternative + " (MP used: " + altMpUsed + ", remaining: " + mpRemaining + ")");
                    }
                } else {
                    if (debugEnabled) {
                        debugW("Alternative movement also blocked, stopping");
                    }
                    break;
                }
            } else {
                break;
            }
        }
    }
    
    // Update global state after movement
    myCell = getCell();
    myMP = getMP();
}

// === TELEPORTATION SUPPORT ===
function considerTeleportation(damageZones) {
    if (!canUseChip(CHIP_TELEPORTATION, getEntity())) return null;
    
    // Find best teleport target within range
    var teleportRange = 12;
    var bestCell = null;
    var bestDamage = 0;
    
    for (var cell in damageZones) {
        var cellId = cell + 0; // Convert to number
        var distance = getCellDistance(myCell, cellId);
        var damage = damageZones[cell] + 0; // Convert to number
        if (distance <= teleportRange && damage > bestDamage) {
            bestDamage = damage;
            bestCell = cellId;
        }
    }
    
    var currentDamage = (damageZones[myCell] != null) ? (damageZones[myCell] + 0) : 0;
    if (bestCell != null && bestDamage > currentDamage * 1.5) {
        return {
            targetCell: bestCell,
            damage: bestDamage,
            cost: getChipCost(CHIP_TELEPORTATION)
        };
    }
    
    return null;
}

function findAlternativeMovement(fromCell, toCell) {
    var fromX = getCellX(fromCell);
    var fromY = getCellY(fromCell);
    var toX = getCellX(toCell);
    var toY = getCellY(toCell);
    
    // Try different movement priorities when primary direction is blocked
    var directions = [
        [1, 0], [-1, 0], [0, 1], [0, -1],  // Cardinal directions
        [1, 1], [1, -1], [-1, 1], [-1, -1]  // Diagonal directions
    ];
    
    // Find any valid alternative that's NOT the blocked target
    for (var i = 0; i < count(directions); i++) {
        var dir = directions[i];
        var testX = fromX + dir[0];
        var testY = fromY + dir[1];
        var testCell = getCellFromXY(testX, testY);
        
        // Skip if invalid cell or same as blocked target
        if (testCell == null || testCell == -1 || testCell < 0 || testCell > 612 || testCell == toCell) {
            continue;
        }
        
        if (debugEnabled) {
            debugW("ALTERNATIVE: Trying " + testCell + " from direction [" + dir[0] + "," + dir[1] + "]");
        }
        
        return testCell; // Return first valid alternative
    }
    
    if (debugEnabled) {
        debugW("ALTERNATIVE: No alternatives found from " + fromCell);
    }
    
    return null;
}

// === MULTI-TURN PATHFINDING ===
function findMultiTurnPath(currentCell, sortedArray) {
    
    // Try to find paths to high-damage cells with extended range
    var maxTurnDistance = myMP * 3; // Allow paths up to 3 turns away
    var bestTarget = null;
    var bestDamagePerTurn = 0;
    
    for (var i = 0; i < min(MAX_PATHFIND_CELLS, count(sortedArray)); i++) {
        var targetData = sortedArray[i];
        var targetCell = targetData[0];
        var expectedDamage = targetData[1];
        
        // Skip if damage is 0
        if (expectedDamage <= 0) continue;
        
        // Try A* with extended range
        var fullPath = aStar(currentCell, targetCell, maxTurnDistance);
        
        if (fullPath != null && count(fullPath) > 1) {
            var totalDistance = count(fullPath) - 1;
            var turnsNeeded = ceil(totalDistance * 1.0 / myMP);
            var damagePerTurn = expectedDamage / turnsNeeded;
            
            
            // Consider this target if it offers good damage per turn
            if (damagePerTurn > bestDamagePerTurn) {
                bestDamagePerTurn = damagePerTurn;
                bestTarget = {
                    targetCell: targetCell,
                    fullPath: fullPath,
                    damage: expectedDamage,
                    turnsNeeded: turnsNeeded,
                    damagePerTurn: damagePerTurn
                };
            }
        }
    }
    
    // If we found a good multi-turn target, take first steps toward it
    if (bestTarget != null && bestDamagePerTurn > 100) { // Minimum threshold
        var firstTurnPath = [];
        var pathLength = min(myMP + 1, count(bestTarget.fullPath));
        
        for (var j = 0; j < pathLength; j++) {
            push(firstTurnPath, bestTarget.fullPath[j]);
        }
        
        if (debugEnabled) {
            var pathStr = "";
            for (var p in firstTurnPath) {
                pathStr += (pathStr == "" ? "" : ",") + firstTurnPath[p];
            }
            debugW("Multi-turn path (" + count(firstTurnPath) + " cells): [" + pathStr + "]");
            markText(bestTarget.targetCell, "T" + floor(bestTarget.damage + 0.5), getColor(255, 255, 0), 10); // Yellow target
        }
        
        return {
            targetCell: firstTurnPath[count(firstTurnPath) - 1],
            path: firstTurnPath,
            damage: 0, // No immediate damage, moving toward future damage
            reachable: false, // Not reachable this turn
            distance: count(firstTurnPath) - 1,
            multiTurn: true,
            finalTarget: bestTarget.targetCell,
            finalDamage: bestTarget.damage,
            turnsNeeded: bestTarget.turnsNeeded
        };
    }
    
    return null;
}

// === TELEPORT + MOVEMENT FALLBACK ===
function tryTeleportMovementFallback(currentCell, damageArray) {
    // Only try if we have teleportation available
    var chips = getChips();
    if (!inArray(chips, CHIP_TELEPORTATION) || !canUseChip(CHIP_TELEPORTATION, currentCell)) {
        if (debugEnabled) {
            debugW("TELEPORT FALLBACK: Teleportation not available");
        }
        return null;
    }
    
    var bestOption = null;
    var bestScore = 0;
    
    if (debugEnabled) {
        debugW("TELEPORT FALLBACK: Searching teleport + movement combinations");
    }
    
    // Try teleporting to various positions within range
    var teleportRange = 6; // CHIP_TELEPORTATION range
    for (var range = 1; range <= teleportRange; range++) {
        var teleportCells = getCellsAtDistance(currentCell, range);
        
        for (var i = 0; i < count(teleportCells); i++) {
            var teleportCell = teleportCells[i];
            
            // Check if teleport destination is valid
            var isWalkable = (getCellContent(teleportCell) == CELL_EMPTY);
            if (!isWalkable) continue;
            
            // Calculate what we could achieve from this teleport position
            var option = evaluateTeleportPosition(teleportCell, damageArray);
            if (option != null && option.score > bestScore) {
                bestScore = option.score;
                bestOption = option;
            }
        }
    }
    
    if (bestOption != null) {
        if (debugEnabled) {
            debugW("TELEPORT FALLBACK: Best option - teleport to " + bestOption.teleportCell + 
                   " then move to " + bestOption.targetCell + " (score: " + bestScore + ")");
            markText(bestOption.teleportCell, "TELE", getColor(255, 0, 255), 8);
            if (bestOption.targetCell != bestOption.teleportCell) {
                markText(bestOption.targetCell, "MOVE", getColor(255, 128, 255), 8);
            }
        }
        
        return {
            targetCell: bestOption.targetCell,
            path: bestOption.path,
            damage: bestOption.damage,
            reachable: true,
            distance: bestOption.distance,
            useTeleport: true,
            teleportCell: bestOption.teleportCell
        };
    }
    
    if (debugEnabled) {
        debugW("TELEPORT FALLBACK: No viable teleport + movement combinations found");
    }
    
    return null;
}

function evaluateTeleportPosition(teleportCell, damageArray) {
    var bestDamage = 0;
    var bestCell = null;
    var bestPath = null;
    
    // First, check if teleport cell itself gives good damage
    for (var i = 0; i < count(damageArray); i++) {
        var targetData = damageArray[i];
        var targetCell = targetData[0];
        var damage = targetData[1];
        
        if (targetCell == teleportCell && damage > bestDamage) {
            bestDamage = damage;
            bestCell = teleportCell;
            bestPath = [teleportCell];
        }
    }
    
    // Then check cells reachable from teleport position
    var remainingMP = myMP; // After teleport, we still have all MP for movement
    
    for (var i = 0; i < count(damageArray); i++) {
        var targetData = damageArray[i];
        var targetCell = targetData[0];
        var damage = targetData[1];
        
        if (damage <= bestDamage) continue; // Skip if not better than current best
        
        var pathFromTeleport = aStar(teleportCell, targetCell, remainingMP);
        if (pathFromTeleport != null && count(pathFromTeleport) <= remainingMP + 1) {
            bestDamage = damage;
            bestCell = targetCell;
            bestPath = pathFromTeleport;
        }
    }
    
    // If no damage cells reachable, try cover positions
    if (bestDamage == 0) {
        var coverCell = findCoverFromPosition(teleportCell, remainingMP);
        if (coverCell != null) {
            var pathToCover = aStar(teleportCell, coverCell, remainingMP);
            if (pathToCover != null) {
                // Score cover based on safety (distance from enemy + cover quality)
                var coverScore = calculateCoverScore(coverCell);
                return {
                    teleportCell: teleportCell,
                    targetCell: coverCell,
                    path: pathToCover,
                    damage: 0,
                    distance: count(pathToCover) - 1,
                    score: coverScore * 0.5 // Cover worth less than damage
                };
            }
        }
    }
    
    if (bestCell != null) {
        return {
            teleportCell: teleportCell,
            targetCell: bestCell,
            path: bestPath,
            damage: bestDamage,
            distance: count(bestPath) - 1,
            score: bestDamage + 10 // Base bonus for any viable option
        };
    }
    
    return null;
}

function findCoverFromPosition(startCell, maxMP) {
    var bestCover = null;
    var bestCoverScore = 0;
    
    // Check cells within movement range from start position
    for (var range = 1; range <= maxMP; range++) {
        var cells = getCellsAtDistance(startCell, range);
        
        for (var i = 0; i < count(cells); i++) {
            var cell = cells[i];
            
            // Must be walkable
            var isWalkable = (getCellContent(cell) == CELL_EMPTY);
            if (!isWalkable) continue;
            
            // Calculate cover score
            var coverScore = calculateCoverScore(cell);
            if (coverScore > bestCoverScore) {
                bestCoverScore = coverScore;
                bestCover = cell;
            }
        }
    }
    
    return bestCover;
}