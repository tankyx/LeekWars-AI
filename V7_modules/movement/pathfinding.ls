// V7 Module: movement/pathfinding.ls
// A* pathfinding to optimal damage cells
// Version 7.0.1 - Object literal fixes (Jan 2025)

// === HELPER FUNCTIONS ===
function createPathResult(targetCell, path, damage, weaponId, reachable, distance, useTeleport) {
    // Use push() instead of direct array indexing which doesn't work in LeekScript V4+
    var result = [];
    push(result, (targetCell != null) ? targetCell : -1);    // [0] targetCell
    push(result, (path != null) ? path : []);                // [1] path
    push(result, (damage != null) ? damage : 0);             // [2] damage
    push(result, weaponId);                                  // [3] weaponId (can be null)
    push(result, (reachable != null) ? reachable : false);   // [4] reachable
    push(result, (distance != null) ? distance : 0);        // [5] distance
    push(result, (useTeleport != null) ? useTeleport : false); // [6] useTeleport
    
    // PathResult created
    
    return result;
}

// === MAIN PATHFINDING FUNCTION (ARRAY-BASED) ===
function findOptimalPathFromArray(currentCell, damageArray) {
    // Pathfinding array processed
    
    // Sort array by damage potential (highest first)
    var sortedArray = sortArrayByDamage(damageArray);
    
    // Try single-turn A* first to each high-damage cell
    // Trying top damage cells
    
    for (var i = 0; i < min(MAX_PATHFIND_CELLS, count(sortedArray)); i++) {
        var targetData = sortedArray[i];
        var targetCell = targetData[0];
        var expectedDamage = targetData[1];
        var weaponId = targetData[2]; // Get weapon/chip ID from damage calculation

        // Only pass weapon IDs, not chip IDs, to prevent setWeapon errors
        if (weaponId != null && !isWeapon(weaponId)) {
            weaponId = null; // Don't recommend chips as weapons
        }
        
        // Trying pathfinding to damage cell
        
        var path = aStar(currentCell, targetCell, myMP);
        
        if (path != null && count(path) <= myMP + 1) {
            // Mark chosen path with text indicators
            // Path found and marked
            
            return createPathResult(targetCell, path, expectedDamage, weaponId, true, count(path) - 1, false);
        } else {
            // Path attempt failed
        }
    }
    
    // No single-turn path found - move toward best damage zone
    // No single-turn paths found, moving toward damage zone
    
    // Try to move toward the highest damage cell (even if unreachable this turn)
    if (count(sortedArray) > 0) {
        var bestTarget = sortedArray[0];
        var bestCell = bestTarget[0];
        var bestDamage = bestTarget[1];
        var bestWeapon = bestTarget[2];
        
        // Moving toward best damage cell
        
        // IMPROVED: Instead of moving toward damage zone, move to weapon range of enemy
        // Get equipped weapons to find optimal positioning
        var weapons = getWeapons();
        var targetPosition = null;
        
        if (weapons != null && count(weapons) > 0 && enemyCell != null) {
            // Find the best weapon we can afford and its optimal range
            var affordableWeapon = null;
            var weaponRange = null;
            var bestWeaponValue = 0;
            
            // Weapon selection based on build type
            
            for (var w = 0; w < count(weapons); w++) {
                var weapon = weapons[w];
                var cost = getWeaponCost(weapon);
                
                if (myTP >= cost) {
                    var minRange = getWeaponMinRange(weapon);
                    var maxRange = getWeaponMaxRange(weapon);
                    
                    // Use dynamic weapon selection to find best weapon for current situation
                    // For pathfinding, use weapon's optimal range instead of current distance
                    var optimalDistance = floor((minRange + maxRange) / 2);
                    var testScenario = buildScenarioForWeapon(weapon, myTP, getChips(), optimalDistance, false);
                    if (testScenario != null) {
                        var weaponValue = calculateScenarioValue(testScenario, weapon);
                        
                        // Select weapon with highest value
                        if (affordableWeapon == null || weaponValue > bestWeaponValue) {
                            affordableWeapon = weapon;
                            weaponRange = [minRange, maxRange];
                            bestWeaponValue = weaponValue;
                            // Weapon selected for pathfinding
                        }
                    }
                }
            }
            
            if (affordableWeapon != null && weaponRange != null) {
                // Targeting optimal weapon range
                
                // Find optimal distance within weapon range
                var targetDistance = weaponRange[0]; // Start with minimum range
                if (affordableWeapon == WEAPON_RHINO) {
                    targetDistance = 3; // Middle of 2-4 range for flexibility
                } else if (affordableWeapon == WEAPON_ELECTRISOR) {
                    targetDistance = 7; // Exact range required
                } else if (weaponRange[1] > weaponRange[0]) {
                    targetDistance = floor((weaponRange[0] + weaponRange[1]) / 2); // Middle of range
                }
                
                // Find cells at target distance from enemy
                var targetCells = getCellsAtExactDistance(enemyCell, targetDistance);
                var bestTargetCell = null;
                var bestTargetDistance = 999;
                
                for (var t = 0; t < count(targetCells) && t < 15; t++) {
                    var cell = targetCells[t];
                    if (getCellContent(cell) == CELL_EMPTY) {
                        var distanceFromUs = getCellDistance(currentCell, cell);
                        if (distanceFromUs < bestTargetDistance) {
                            bestTargetDistance = distanceFromUs;
                            bestTargetCell = cell;
                        }
                    }
                }
                
                if (bestTargetCell != null) {
                    targetPosition = bestTargetCell;
                    if (debugEnabled) {
                        // Optimal weapon position found
                    }
                }
            }
        }
        
        // If no weapon-specific position found, fall back to original logic
        if (targetPosition == null) {
            targetPosition = bestCell;
        }
        
        // Try to get as close as possible to the target position
        var pathToBest = aStar(currentCell, targetPosition, myMP * 4); // Allow longer path for distant enemies
        if (pathToBest != null && count(pathToBest) > 1) {
            // Take as many steps as possible toward the target
            var stepsToTake = min(myMP, count(pathToBest) - 1);
            var moveToCell = pathToBest[stepsToTake];

            // Create a path with only the steps we can take this turn
            var actualPath = [];
            for (var step = 0; step <= stepsToTake; step++) {
                push(actualPath, pathToBest[step]);
            }

            // Moving steps toward target position

            // ALWAYS move if we can - even if we can't attack immediately, we're making progress
            if (stepsToTake > 0) {
                return createPathResult(moveToCell, actualPath, 0, bestWeapon, false, stepsToTake, false);
            }
        }
    }
    
    // Multi-turn pathfinding fallback
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
    // Damage analysis complete
    
    if (maxDamage == 0) {
        // Check if we have M-Laser and should seek alignment
        var weapons = getWeapons();
        if (inArray(weapons, WEAPON_M_LASER)) {
            var alignmentTarget = findMLaserAlignmentPosition();
            if (alignmentTarget != null) {
                // Seeking M-Laser alignment position
                var pathToAlignment = aStar(currentCell, alignmentTarget, myMP);
                if (pathToAlignment != null && count(pathToAlignment) > 1) {
                    var moveToCell = pathToAlignment[min(myMP, count(pathToAlignment) - 1)];
                    
                    return createPathResult(moveToCell, pathToAlignment, 0, WEAPON_M_LASER, getCellDistance(currentCell, moveToCell) <= myMP, getCellDistance(currentCell, moveToCell), false);
                }
            }
        }
        
        // Smart positioning based on equipped weapons and their DPS potential
        var bestPosition = findBestWeaponPosition(currentCell, weapons);
        if (bestPosition != null) {
            // Moving to optimal weapon position
            
            var pathToPosition = aStar(currentCell, bestPosition.cell, myMP);
            if (pathToPosition != null && count(pathToPosition) > 1) {
                var moveToCell = pathToPosition[min(myMP, count(pathToPosition) - 1)];
                
                return createPathResult(moveToCell, pathToPosition, 0, bestPosition.weapon, false, min(myMP, count(pathToPosition) - 1), false);
            }
        }
        
        // IMPROVED: If smart positioning failed, use weapon-specific targeting
        if (enemyCell != null) {
            var targetPosition = findWeaponSpecificPosition(currentCell, weapons, enemyCell);
            if (targetPosition != null) {
                // Using weapon-specific position
                
                var pathToTarget = aStar(currentCell, targetPosition.cell, myMP);
                if (pathToTarget != null && count(pathToTarget) > 1) {
                    var moveToCell = pathToTarget[min(myMP, count(pathToTarget) - 1)];
                    
                    // VALIDATION: Ensure destination allows attack with the weapon
                    var destDistance = getCellDistance(moveToCell, enemyCell);
                    var minRange = getWeaponMinRange(targetPosition.weapon);
                    var maxRange = getWeaponMaxRange(targetPosition.weapon);
                    var canAttack = (destDistance >= minRange && destDistance <= maxRange);
                    
                    // Weapon-specific validation complete
                    
                    if (canAttack) {
                        return createPathResult(moveToCell, pathToTarget, 0, targetPosition.weapon, false, min(myMP, count(pathToTarget) - 1), false);
                    } else if (debugEnabled) {
                        // Position rejected - not in attack range
                    }
                }
            }
        }
        
        // Fallback: Move toward enemy when no smart position found
        if (debugEnabled) {
            // Fallback - moving toward enemy
        }

        var pathToEnemy = aStar(currentCell, enemyCell, myMP * 4); // Allow longer search for distant enemies
        if (pathToEnemy != null && count(pathToEnemy) > 1) {
            var stepsToTake = min(myMP, count(pathToEnemy) - 1);
            var moveToCell = pathToEnemy[stepsToTake];

            // Create path with only the steps we can take
            var actualPath = [];
            for (var step = 0; step <= stepsToTake; step++) {
                push(actualPath, pathToEnemy[step]);
            }

            // Moving toward enemy as fallback

            return createPathResult(moveToCell, actualPath, 0, null, false, stepsToTake, false);
        }
    }
    
    // Check if we should use teleportation for strategic positioning
    var currentHPPercent = getLife() / getTotalLife();
    var shouldUseTeleport = false;
    
    // Trigger teleportation if:
    // 1. HP < 40% (late-game threshold)
    // 2. No high-damage paths were found by movement
    // 3. We have high-damage cells that are only reachable by teleport
    if (currentHPPercent < 0.4 && maxDamage > 0) {
        shouldUseTeleport = true;
        // Late-game teleportation triggered
    } else if (maxDamage == 0 && count(damageArray) > 0) {
        // No movement paths found, but damage zones exist - try teleport
        shouldUseTeleport = true;
        // Strategic teleportation for positioning
    }
    
    // Last resort: Try teleport + movement fallback (or forced teleport for late-game)
    if (shouldUseTeleport || maxDamage == 0) {
        // Pathfinding fallback with teleportation
        
        var teleportResult = tryTeleportMovementFallback(currentCell, damageArray);
        if (teleportResult != null) {
            return teleportResult;
        }
    }
    
    // ABSOLUTE FALLBACK: Use simple directional movement if everything else fails
    // Absolute fallback - simple movement toward enemy

    if (enemyCell != null) {
        var simpleMovePath = findMultiStepMovementToward(currentCell, enemyCell, myMP);
        if (simpleMovePath != null && count(simpleMovePath) > 1) {
            // Simple movement path found
            return createPathResult(
                simpleMovePath[count(simpleMovePath) - 1], // Final position
                simpleMovePath,                            // Path
                0,                                         // No immediate damage
                null,                                      // No specific weapon
                false,                                     // Not immediately reachable
                count(simpleMovePath) - 1,                 // Distance moved
                false                                      // No teleport
            );
        }
    }

    // Return null if no path found
    return null;
}

// === ARRAY SORTING FUNCTION ===
function sortArrayByDamage(damageArray) {
    // Sorting damage array by priority
    
    // Make a copy to avoid modifying original array
    var sortedArray = [];
    for (var i = 0; i < count(damageArray); i++) {
        var entry = damageArray[i];
        var cellId = entry[0];
        var damage = entry[1];
        var weaponId = (count(entry) > 2) ? entry[2] : null; // Preserve weapon ID
        var enemyEntity = (count(entry) > 3) ? entry[3] : null; // NEW: Preserve enemy association
        
        // Validate cell and damage
        if (cellId >= 0 && cellId <= 612 && damage > 0) {
            // Enhanced format: [cellId, damage, weaponId, enemyEntity]
            push(sortedArray, [cellId, damage, weaponId, enemyEntity]);
        } else if (debugEnabled && i < 3) {
            // Rejecting invalid cell
        }
    }
    
    // Sort by damage AND weapon priority (highest first) - optimized for small arrays
    var arraySize = count(sortedArray);
    if (arraySize > 50) {
        // If array too large, take top entries and skip full sort
        var topEntries = [];
        var maxEntries = 20; // Limit to top 20 entries
        
        for (var k = 0; k < min(maxEntries, arraySize); k++) {
            var maxIndex = k;
            var maxScore = getWeaponSortScore(sortedArray[k]);
            
            // Find max in remaining elements
            for (var m = k + 1; m < arraySize; m++) {
                var score = getWeaponSortScore(sortedArray[m]);
                if (score > maxScore) {
                    maxIndex = m;
                    maxScore = score;
                }
            }
            
            // Swap if needed
            if (maxIndex != k) {
                var temp = sortedArray[k];
                sortedArray[k] = sortedArray[maxIndex];
                sortedArray[maxIndex] = temp;
            }
        }
        
        // Truncate to top entries only
        var truncated = [];
        for (var t = 0; t < min(maxEntries, arraySize); t++) {
            push(truncated, sortedArray[t]);
        }
        sortedArray = truncated;
    } else {
        // Use simple selection sort for small arrays with weapon prioritization
        for (var i = 0; i < arraySize - 1; i++) {
            var maxIndex = i;
            var maxScore = getWeaponSortScore(sortedArray[i]);
            for (var j = i + 1; j < arraySize; j++) {
                var score = getWeaponSortScore(sortedArray[j]);
                if (score > maxScore) {
                    maxIndex = j;
                    maxScore = score;
                }
            }
            if (maxIndex != i) {
                var temp = sortedArray[i];
                sortedArray[i] = sortedArray[maxIndex];
                sortedArray[maxIndex] = temp;
            }
        }
    }
    
    // Array sorting complete
    
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
        var weaponId = (count(targetData) > 2) ? targetData[2] : null;
        
        var path = aStar(currentCell, targetCell, myMP);
        
        if (path != null && count(path) <= myMP + 1) {
            // Mark chosen path in bright orange
            // TEMPORARILY DISABLED: Testing if mark() corrupts the map
            // Path found and marked
            
            return createPathResult(targetCell, path, expectedDamage, weaponId, true, count(path) - 1, false);
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
    // Pathfinding damage analysis complete
    if (maxDamage == 0) {
        // Moving toward enemy
        var moveTowardEnemy = aStar(currentCell, enemyCell, myMP);
        if (moveTowardEnemy != null && count(moveTowardEnemy) > 1) {
            var moveToCell = moveTowardEnemy[min(myMP, count(moveTowardEnemy) - 1)];
            
            if (debugEnabled) {
                // Moving toward enemy - no damage zones
            }
            
            return createPathResult(moveToCell, arraySlice(moveTowardEnemy, 0, min(myMP + 1, count(moveTowardEnemy))), 0, null, false, min(myMP, count(moveTowardEnemy) - 1), false);
        } else {
            // A* failed, try simple directional movement
            var simplePath = findMultiStepMovementToward(currentCell, enemyCell, myMP);
            if (simplePath != null && count(simplePath) > 1) {
                return createPathResult(simplePath[count(simplePath) - 1], simplePath, 0, null, false, count(simplePath) - 1, false);
            }
        }
    }
    
    // Move toward best damage zone (even if 0)
    if (count(sortedCells) > 0) {
        var bestCell = sortedCells[0][0];
        var bestDamage = sortedCells[0][1];
        var bestWeapon = (count(sortedCells[0]) > 2) ? sortedCells[0][2] : null;
        var partialPath = aStar(currentCell, bestCell, myMP);
        
        if (partialPath != null && count(partialPath) > 1) {
            var moveToCell = partialPath[min(myMP + 1, count(partialPath) - 1)];
            return createPathResult(moveToCell, arraySlice(partialPath, 0, min(myMP + 1, count(partialPath))), bestDamage, bestWeapon, false, min(myMP, count(partialPath) - 1), false);
        }
    }
    
    // Fallback: stay in place
    return createPathResult(currentCell, [currentCell], (damageZones[currentCell] + 0) || 0, null, true, 0, false);
}

// === CELL SORTING BY DAMAGE ===
function sortCellsByDamage(damageZones) {
    var cellArray = [];
    
    for (var cell in damageZones) {
        // Use cell ID directly
        var cellId = cell + 0;  // Convert to number
        if (cellId != null && !isNaN(cellId) && cellId >= 0 && cellId <= 612) {
            var damage = damageZones[cell] + 0; // Convert damage to number
            push(cellArray, [cellId, damage]);
        }
    }
    
    // Cell array prepared for sorting
    
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
        // M-Laser alignment search
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
                    // M-Laser vertical alignment checked
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
                    // M-Laser horizontal alignment checked
                }
            }
        }
    }
    
    if (bestTarget != null && debugEnabled) {
        // Best M-Laser position found
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
    if (!checkLineOfSight(cell, enemyCell)) return 0;
    
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
    var adjacentCells = getCellsAtExactDistance(cell, 1);
    for (var i = 0; i < count(adjacentCells); i++) {
        var adjCell = adjacentCells[i];
        if (getCellContent(adjCell) == CELL_OBSTACLE) {
            coverBonus += 2; // Small bonus for each adjacent obstacle
        }
    }
    score += min(coverBonus, 8); // Cap cover bonus at 8
    
    // MAGIC BUILD HIDE-AND-SEEK BONUSES
    if (isMagicBuild && count(allEnemies) > 0) {
        // Enhanced cover bonus for magic builds (hit-and-run tactics)
        score += min(coverBonus * 2, 15); // Double cover bonus for magic builds
        
        // Escape route bonus - prefer positions with multiple movement options
        var escapeRoutes = 0;
        var escapeDistance = 3; // Check 3 cells in each direction for escape routes
        var directions = [
            [-1, 0], [1, 0], [0, -1], [0, 1],  // Cardinal directions
            [-1, -1], [-1, 1], [1, -1], [1, 1] // Diagonal directions
        ];
        
        for (var d = 0; d < count(directions); d++) {
            var dx = directions[d][0];
            var dy = directions[d][1];
            var routeOpen = true;
            
            for (var step = 1; step <= escapeDistance; step++) {
                var escapeCell = cell + (dx * step) + (dy * step * MAP_WIDTH);
                if (getCellContent(escapeCell) != CELL_EMPTY) {
                    routeOpen = false;
                    break;
                }
            }
            
            if (routeOpen) {
                escapeRoutes++;
            }
        }
        
        // Bonus for having multiple escape routes (max 8 directions)
        var escapeBonus = min(escapeRoutes * 2, 16); // Max 16 points for escape routes
        score += escapeBonus;
        
        // Line of sight penalty for magic builds - prefer positions where enemies can't see you
        var losBlockedFromEnemies = 0;
        for (var e = 0; e < count(allEnemies); e++) {
            var targetEnemyCell = getCell(allEnemies[e]);
            if (!lineOfSight(cell, targetEnemyCell, targetEnemyCell)) {
                losBlockedFromEnemies++;
            }
        }
        
        // Bonus for breaking line of sight with enemies
        var stealthBonus = losBlockedFromEnemies * 10; // 10 points per enemy we can hide from
        score += stealthBonus;
        
        if (debugEnabled && stealthBonus > 0) {
            // Magic stealth bonus applied
        }
    }
    
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
                // Multi-step blocked, trying alternative
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
        // Multi-step path created
    }
    
    return (count(path) > 1) ? path : null;
}

function findSimpleMovementToward(fromCell, toCell, maxMP) {
    var fromX = getCellX(fromCell);
    var fromY = getCellY(fromCell);
    var toX = getCellX(toCell);
    var toY = getCellY(toCell);
    
    if (debugEnabled) {
        // Simple directional movement
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
                // Moving in X direction
            }
            return targetCell;
        }
    }
    
    if (!tryX && dirY != 0) {
        var targetCell = getCellFromXY(fromX, fromY + dirY);
        if (targetCell != null && targetCell != -1) {
            if (debugEnabled) {
                // Moving in Y direction
            }
            return targetCell;
        }
    }
    
    // Try the other direction if first choice failed
    if (tryX && dirY != 0) {
        var targetCell = getCellFromXY(fromX, fromY + dirY);
        if (targetCell != null && targetCell != -1) {
            if (debugEnabled) {
                // Moving in Y direction (fallback)
            }
            return targetCell;
        }
    }
    
    if (!tryX && dirX != 0) {
        var targetCell = getCellFromXY(fromX + dirX, fromY);
        if (targetCell != null && targetCell != -1) {
            if (debugEnabled) {
                // Moving in X direction (fallback)
            }
            return targetCell;
        }
    }
    
    if (debugEnabled) {
        // No valid movement directions found
    }
    return null;
}

// === MOVEMENT EXECUTION ===
function executeMovement(pathResult) {
    if (pathResult == null) {
        return; // No movement needed
    }
    
    // Handle teleport + movement combo  
    if (pathResult[6]) { // pathResult[6] = useTeleport
        if (debugEnabled) {
            // Executing teleportation
        }
        
        var chips = getChips();
        if (inArray(chips, CHIP_TELEPORTATION) && canUseChip(CHIP_TELEPORTATION, pathResult[0])) {
            useChip(CHIP_TELEPORTATION, pathResult[0]);
            
            // Update position after teleport
            myCell = getCell();
            myMP = getMP(); // MP should be unchanged after teleport
            
            if (debugEnabled) {
                // Teleport successful
            }
            
            // Target cell reached after teleport - no additional movement needed
            if (debugEnabled) {
                // Teleport completed to target
            }
        } else {
            if (debugEnabled) {
                // Teleport failed
            }
        }
        return;
    }
    
    // Normal movement execution
    executeNormalMovement(pathResult);
}

function executeNormalMovement(pathResult) {
    if (pathResult == null || pathResult[1] == null || count(pathResult[1]) <= 1) {
        return; // No movement needed
    }
    
    var path = pathResult[1]; // pathResult[1] = path
    var mpRemaining = myMP;
    
    // Execute movement along path
    for (var i = 1; i < count(path) && mpRemaining > 0; i++) {
        var targetCell = path[i];
        
        var mpUsed = moveTowardCells([targetCell], 1);
        if (mpUsed > 0) {
            mpRemaining -= mpUsed;
            if (debugEnabled) {
                // Movement completed
            }
        } else {
            if (debugEnabled) {
                // Movement blocked, trying alternative
            }
            // Try alternative movement when blocked
            var currentPos = getCell();
            var alternative = findAlternativeMovement(currentPos, targetCell);
            if (alternative != null) {
                var altMpUsed = moveTowardCells([alternative], 1);
                if (altMpUsed > 0) {
                    mpRemaining -= altMpUsed;
                    if (debugEnabled) {
                        // Alternative movement completed
                    }
                } else {
                    if (debugEnabled) {
                        // Alternative movement blocked
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
            // Trying alternative direction
        }
        
        return testCell; // Return first valid alternative
    }
    
    if (debugEnabled) {
        // No movement alternatives found
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
        var weaponId = targetData[2]; // Get weapon ID
        
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
                // Create array instead of object: [targetCell, fullPath, damage, weaponId, turnsNeeded, damagePerTurn]
                bestTarget = [];
                push(bestTarget, targetCell);       // [0] targetCell
                push(bestTarget, fullPath);         // [1] fullPath
                push(bestTarget, expectedDamage);   // [2] damage
                push(bestTarget, weaponId);         // [3] weaponId
                push(bestTarget, turnsNeeded);      // [4] turnsNeeded  
                push(bestTarget, damagePerTurn);    // [5] damagePerTurn
            }
        } else {
            // Debug invalid path
            if (debugEnabled && i < 3) {
                // Multi-turn path invalid
            }
        }
    }
    
    // If we found a good multi-turn target, take first steps toward it
    if (bestTarget != null && bestDamagePerTurn > 100) { // Minimum threshold
        // Validate bestTarget[1] (fullPath) before using it
        if (bestTarget[1] != null && count(bestTarget[1]) > 1) {
            var firstTurnPath = [];
            var pathLength = min(myMP + 1, count(bestTarget[1]));
            
            for (var j = 0; j < pathLength; j++) {
                if (j < count(bestTarget[1])) {
                    push(firstTurnPath, bestTarget[1][j]);
                }
            }
            
            if (debugEnabled) {
                var pathStr = "";
                for (var p = 0; p < count(firstTurnPath); p++) {
                    pathStr += (pathStr == "" ? "" : ",") + firstTurnPath[p];
                }
                // Multi-turn path created
                markText(bestTarget[0], "T" + floor(bestTarget[2] + 0.5), getColor(255, 255, 0), 10); // Yellow target
            }
        
            if (count(firstTurnPath) > 0) {
                return createPathResult(
                    firstTurnPath[count(firstTurnPath) - 1], // targetCell
                    firstTurnPath,                           // path
                    0,                                       // damage (no immediate damage)
                    bestTarget[3],                           // weaponId for future use
                    false,                                   // reachable (not reachable this turn)
                    count(firstTurnPath) - 1,                // distance
                    false                                    // useTeleport
                );
            } else {
                if (debugEnabled) {
                    // Empty path generated, falling back
                }
            }
        } else {
            if (debugEnabled) {
                // Best target has invalid path
            }
        }
    }
    
    // If no damage zones reachable, find best cover position toward target
    if (debugEnabled) {
        // No damage zones reachable, seeking cover
    }
    
    var targetDirection = null;
    if (count(sortedArray) > 0) {
        targetDirection = sortedArray[0][0]; // Highest damage cell
    } else if (enemyCell != null) {
        targetDirection = enemyCell; // Fall back to enemy position
    }
    
    if (targetDirection != null) {
        // Find cover positions along path to target
        var pathToTarget = aStar(currentCell, targetDirection, myMP * 2);
        if (pathToTarget != null && count(pathToTarget) > 1) {
            var bestCoverCell = null;
            var bestCoverScore = 0;
            
            // Check each cell along the path for cover quality
            var checkLimit = min(myMP + 1, count(pathToTarget));
            for (var p = 1; p < checkLimit; p++) {
                var pathCell = pathToTarget[p];
                
                // Must be walkable
                if (getCellContent(pathCell) != CELL_EMPTY) continue;
                
                var coverScore = calculateCoverScore(pathCell);
                
                // Bonus for being closer to target
                var distanceToTarget = getCellDistance(pathCell, targetDirection);
                coverScore += (50 - distanceToTarget); // Closer is better
                
                // Additional bonus for being along the optimal path
                coverScore += 10;
                
                if (coverScore > bestCoverScore) {
                    bestCoverScore = coverScore;
                    bestCoverCell = pathCell;
                }
            }
            
            if (bestCoverCell != null) {
                var coverPath = aStar(currentCell, bestCoverCell, myMP);
                if (coverPath != null && count(coverPath) > 1) {
                    if (debugEnabled) {
                        // Moving to cover position
                        markText(bestCoverCell, "C" + floor(bestCoverScore), getColor(0, 255, 255), 10); // Cyan cover marker
                    }
                    
                    return createPathResult(
                        bestCoverCell,           // targetCell
                        coverPath,               // path
                        0,                       // damage
                        null,                    // weaponId
                        true,                    // reachable
                        count(coverPath) - 1,    // distance
                        false                    // useTeleport
                    );
                }
            }
        }
    }
    
    return null;
}

// === TELEPORT + MOVEMENT FALLBACK ===
function tryTeleportMovementFallback(currentCell, damageArray) {
    // Only try if we have teleportation available
    var chips = getChips();
    if (!inArray(chips, CHIP_TELEPORTATION) || !canUseChip(CHIP_TELEPORTATION, currentCell)) {
        if (debugEnabled) {
            // Teleportation not available
        }
        return null;
    }
    
    var bestOption = null;
    var bestScore = 0;
    
    if (debugEnabled) {
        // Searching teleport + movement combinations
    }
    
    // Try teleporting to various positions within range
    var teleportRange = 12; // CHIP_TELEPORTATION range
    for (var range = 1; range <= teleportRange; range++) {
        var teleportCells = getCellsAtExactDistance(currentCell, range);
        
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
        
        return createPathResult(
            bestOption.targetCell,     // targetCell
            bestOption.path,           // path
            bestOption.damage,         // damage
            bestOption.weaponId,       // weaponId from teleport option
            true,                      // reachable
            bestOption.distance,       // distance
            true                       // useTeleport
        );
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
    var bestWeaponId = null;
    
    // First, check if teleport cell itself gives good damage
    for (var i = 0; i < count(damageArray); i++) {
        var targetData = damageArray[i];
        var targetCell = targetData[0];
        var damage = targetData[1];
        var weaponId = targetData[2];
        
        if (targetCell == teleportCell && damage > bestDamage) {
            bestDamage = damage;
            bestCell = teleportCell;
            bestPath = [teleportCell];
            bestWeaponId = weaponId;
        }
    }
    
    // Then check cells reachable from teleport position
    var remainingMP = myMP; // After teleport, we still have all MP for movement
    
    for (var i = 0; i < count(damageArray); i++) {
        var targetData = damageArray[i];
        var targetCell = targetData[0];
        var damage = targetData[1];
        var weaponId = targetData[2];
        
        if (damage <= bestDamage) continue; // Skip if not better than current best
        
        var pathFromTeleport = aStar(teleportCell, targetCell, remainingMP);
        if (pathFromTeleport != null && count(pathFromTeleport) <= remainingMP + 1) {
            bestDamage = damage;
            bestCell = targetCell;
            bestPath = pathFromTeleport;
            bestWeaponId = weaponId;
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
                    weaponId: null, // No weapon for cover movement
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
            weaponId: bestWeaponId, // Pass best weapon ID
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
        var cells = getCellsAtExactDistance(startCell, range);
        
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

// === COVER SCORING FUNCTION ===
function calculateCoverScore(cell) {
    var score = 0;
    
    // Base score: distance from enemy
    if (enemyCell != null) {
        score = getCellDistance(cell, enemyCell);
    }
    
    // Bonus for adjacent obstacles (cover)
    var obstacles = countAdjacentObstacles(cell);
    score += obstacles * 2;
    
    // Penalty for being too close to map edges
    var x = getCellX(cell);
    var y = getCellY(cell);
    if (x < 2 || x > 15 || y < 2 || y > 15) {
        score -= 5;
    }
    
    return score;
}

// === SMART WEAPON POSITIONING ===
function findBestWeaponPosition(currentCell, weapons) {
    if (enemyCell == null) return null;
    
    var bestPosition = null;
    var bestScore = 0;
    
    if (debugEnabled) {
        debugW("SMART POSITION: Finding best position for " + count(weapons) + " weapons");
    }
    
    // Define weapon priorities based on build type and DPS potential
    var weaponPriorities = [];
    
    if (isMagicBuild) {
        // MAGIC BUILD: Prioritize DoT weapons as main DPS, DESTROYER for tactical debuffing
        if (debugEnabled) {
            debugW("SMART POSITION: Magic build detected, prioritizing DoT weapons as main DPS");
        }
        weaponPriorities = [
            {weapon: WEAPON_FLAME_THROWER, priority: 100, dps: 2, range: [2, 8]},   // Main DoT DPS (max 2 uses)
            {weapon: WEAPON_RHINO, priority: 90, dps: 3, range: [2, 4]},            // High DPS backup
            {weapon: WEAPON_ELECTRISOR, priority: 80, dps: 2, range: [7, 7]},       // AoE backup
            {weapon: WEAPON_DESTROYER, priority: 75, dps: 2, range: [1, 6]},        // Tactical debuff
            {weapon: WEAPON_GRENADE_LAUNCHER, priority: 70, dps: 2, range: [4, 7]}, // AoE backup
            {weapon: WEAPON_SWORD, priority: 60, dps: 2, range: [1, 1]},            // Melee backup
            {weapon: WEAPON_KATANA, priority: 50, dps: 1, range: [1, 1]},           // Melee backup
            {weapon: WEAPON_RIFLE, priority: 40, dps: 2, range: [7, 9]},            // Standard backup
            {weapon: WEAPON_M_LASER, priority: 35, dps: 2, range: [5, 12]},         // Alignment needed
            {weapon: WEAPON_LIGHTNINGER, priority: 32, dps: 2, range: [6, 10]},     // Star pattern AoE
            {weapon: WEAPON_ENHANCED_LIGHTNINGER, priority: 30, dps: 2, range: [6, 10]} // Healing
        ];
    } else {
        // STRENGTH BUILD: Standard DPS priorities
        weaponPriorities = [
            {weapon: WEAPON_RHINO, priority: 100, dps: 3, range: [2, 4]},           // 3 uses = highest DPS
            {weapon: WEAPON_ELECTRISOR, priority: 80, dps: 2, range: [7, 7]},       // 2 uses + AoE
            {weapon: WEAPON_GRENADE_LAUNCHER, priority: 75, dps: 2, range: [4, 7]}, // 2 uses + AoE
            {weapon: WEAPON_SWORD, priority: 60, dps: 2, range: [1, 1]},            // 2 uses melee
            {weapon: WEAPON_KATANA, priority: 50, dps: 1, range: [1, 1]},           // 1 use melee
            {weapon: WEAPON_RIFLE, priority: 40, dps: 2, range: [7, 9]},            // 2 uses
            {weapon: WEAPON_M_LASER, priority: 35, dps: 2, range: [5, 12]},         // Alignment needed
            {weapon: WEAPON_DESTROYER, priority: 32, dps: 2, range: [1, 6]},        // Lower priority for strength
            {weapon: WEAPON_FLAME_THROWER, priority: 31, dps: 2, range: [2, 8]},    // Lower priority for strength (max 2 uses)
            {weapon: WEAPON_LIGHTNINGER, priority: 30, dps: 2, range: [6, 10]},     // Star pattern AoE
            {weapon: WEAPON_ENHANCED_LIGHTNINGER, priority: 29, dps: 2, range: [6, 10]} // Healing
        ];
    }
    
    // Find highest priority weapon we have equipped
    var targetWeapon = null;
    var targetPriority = 0;
    var targetRange = null;
    
    for (var w = 0; w < count(weapons); w++) {
        var weapon = weapons[w];
        
        for (var p = 0; p < count(weaponPriorities); p++) {
            var wpn = weaponPriorities[p];
            if (wpn.weapon == weapon && wpn.priority > targetPriority) {
                targetWeapon = weapon;
                targetPriority = wpn.priority;
                targetRange = wpn.range;
                
                if (debugEnabled) {
                    debugW("SMART POSITION: Priority weapon " + weapon + " (priority=" + wpn.priority + ", DPS=" + wpn.dps + ")");
                }
                break;
            }
        }
    }
    
    if (targetWeapon == null) return null;
    
    // For high-DPS weapons, prioritize getting into range quickly
    var minRange = targetRange[0];
    var maxRange = targetRange[1];
    
    if (debugEnabled) {
        debugW("SMART POSITION: Target weapon " + targetWeapon + " range " + minRange + "-" + maxRange);
    }
    
    // Check positions at each distance in priority order
    var distancePriorities = [];
    
    if (targetWeapon == WEAPON_RHINO) {
        // RHINO: Prioritize distance 3 (middle of range) for flexibility
        push(distancePriorities, 3);
        push(distancePriorities, 2);
        push(distancePriorities, 4);
    } else if (targetWeapon == WEAPON_ELECTRISOR) {
        // ELECTRISOR: Must be exactly distance 7
        push(distancePriorities, 7);
    } else if (targetWeapon == WEAPON_GRENADE_LAUNCHER) {
        // GRENADE: Prefer distance 5-6 for good AoE coverage
        push(distancePriorities, 5);
        push(distancePriorities, 6);
        push(distancePriorities, 4);
        push(distancePriorities, 7);
    } else if (targetWeapon == WEAPON_SWORD || targetWeapon == WEAPON_KATANA) {
        // Melee: Must be distance 1
        push(distancePriorities, 1);
    } else {
        // Other weapons: Try middle of range first
        var midRange = floor((minRange + maxRange) / 2);
        for (var d = midRange; d >= minRange; d--) {
            push(distancePriorities, d);
        }
        for (var d = midRange + 1; d <= maxRange; d++) {
            push(distancePriorities, d);
        }
    }
    
    // Find best position at priority distances
    for (var dp = 0; dp < count(distancePriorities); dp++) {
        var targetDistance = distancePriorities[dp];
        var positions = getCellsAtExactDistance(enemyCell, targetDistance);
        
        for (var i = 0; i < count(positions); i++) {
            var cell = positions[i];
            
            // Must be walkable
            if (getCellContent(cell) == CELL_OBSTACLE) continue;
            
            // Calculate reachability score
            var moveDistance = getCellDistance(currentCell, cell);
            var reachableThisTurn = (moveDistance <= myMP);
            
            var score = 100 - moveDistance; // Closer is better
            
            if (reachableThisTurn) {
                score += 50; // Bonus for immediate reach
            }
            
            // Line of sight bonus
            if (lineOfSight(cell, enemyCell)) {
                score += 20;
            }
            
            // Cover bonus
            var coverBonus = countAdjacentObstacles(cell) * 3;
            score += min(coverBonus, 10); // Cap cover bonus
            
            if (score > bestScore) {
                bestScore = score;
                bestPosition = {
                    cell: cell,
                    distance: targetDistance,
                    weapon: targetWeapon,
                    reachable: reachableThisTurn
                };
                
                if (debugEnabled) {
                    debugW("SMART POSITION: New best position " + cell + " distance=" + targetDistance + " score=" + score);
                }
            }
        }
        
        // If we found a good position at this distance, use it
        if (bestPosition != null && bestScore > 50) {
            break;
        }
    }
    
    return bestPosition;
}

// === WEAPON-SPECIFIC POSITIONING ===
function findWeaponSpecificPosition(currentCell, weapons, enemyCell) {
    if (weapons == null || count(weapons) == 0 || enemyCell == null) {
        return null;
    }
    
    var bestResult = null;
    var bestScore = 0;
    
    if (debugEnabled) {
        debugW("WEAPON-SPECIFIC: Finding position for " + count(weapons) + " weapons, enemy at " + enemyCell);
    }
    
    // Check each weapon for optimal positioning
    for (var w = 0; w < count(weapons); w++) {
        var weapon = weapons[w];
        var cost = getWeaponCost(weapon);
        
        // Skip if we can't afford this weapon
        if (myTP < cost) {
            continue;
        }
        
        var minRange = getWeaponMinRange(weapon);
        var maxRange = getWeaponMaxRange(weapon);
        
        // Determine optimal distance based on weapon type
        var optimalDistance = minRange;
        if (weapon == WEAPON_RHINO) {
            optimalDistance = 3; // Middle of 2-4 range for flexibility
        } else if (weapon == WEAPON_ELECTRISOR) {
            optimalDistance = 7; // Exact range required
        } else if (weapon == WEAPON_GRENADE_LAUNCHER) {
            optimalDistance = 5; // Good AoE range
        } else if (weapon == WEAPON_SWORD || weapon == WEAPON_KATANA) {
            optimalDistance = 1; // Melee
        } else if (maxRange > minRange) {
            optimalDistance = floor((minRange + maxRange) / 2); // Middle of range
        }
        
        if (debugEnabled) {
            debugW("WEAPON-SPECIFIC: Checking " + weapon + " optimal distance " + optimalDistance);
        }
        
        // Find cells at optimal distance from enemy
        var targetCells = getCellsAtExactDistance(enemyCell, optimalDistance);
        
        for (var t = 0; t < count(targetCells) && t < 10; t++) {
            var cell = targetCells[t];
            
            // Must be walkable
            if (getCellContent(cell) != CELL_EMPTY) {
                continue;
            }
            
            // Calculate score based on reachability and weapon priority
            var moveDistance = getCellDistance(currentCell, cell);
            var score = 100 - moveDistance; // Closer is better
            
            // Weapon priority bonuses based on build type
            if (isMagicBuild) {
                // MAGIC BUILD: DoT weapons as main DPS, DESTROYER for tactical debuffing
                if (weapon == WEAPON_FLAME_THROWER) {
                    score += 60; // Top priority for main DoT DPS
                } else if (weapon == WEAPON_RHINO) {
                    score += 50; // High DPS backup
                } else if (weapon == WEAPON_ELECTRISOR) {
                    score += 45; // AoE backup
                } else if (weapon == WEAPON_DESTROYER) {
                    score += 40; // Tactical debuff (lower than main DPS)
                } else if (weapon == WEAPON_GRENADE_LAUNCHER) {
                    score += 35; // AoE backup
                } else if (weapon == WEAPON_SWORD) {
                    score += 30; // Melee backup
                } else if (weapon == WEAPON_KATANA) {
                    score += 25; // Melee backup
                }
            } else {
                // STRENGTH BUILD: Standard priorities
                if (weapon == WEAPON_RHINO) {
                    score += 50; // Highest DPS
                } else if (weapon == WEAPON_ELECTRISOR) {
                    score += 40; // High DPS + AoE
                } else if (weapon == WEAPON_GRENADE_LAUNCHER) {
                    score += 35; // Good DPS + AoE
                } else if (weapon == WEAPON_SWORD) {
                    score += 30; // Good melee
                } else if (weapon == WEAPON_KATANA) {
                    score += 25; // Standard melee
                } else if (weapon == WEAPON_DESTROYER) {
                    score += 22; // Lower priority for strength
                } else if (weapon == WEAPON_FLAME_THROWER) {
                    score += 21; // Lower priority for strength
                }
            }
            
            // Bonus for reachable this turn
            if (moveDistance <= myMP) {
                score += 25;
            }
            
            // Line of sight bonus
            if (checkLineOfSight(cell, enemyCell)) {
                score += 15;
            }
            
            if (score > bestScore) {
                bestScore = score;
                bestResult = {
                    cell: cell,
                    weapon: weapon,
                    distance: optimalDistance,
                    reachable: moveDistance <= myMP
                };
                
                if (debugEnabled) {
                    debugW("WEAPON-SPECIFIC: New best " + weapon + " position " + cell + " (score=" + score + ")");
                }
            }
        }
    }
    
    return bestResult;
}

// === WEAPON PRIORITY SCORING ===
function getWeaponSortScore(entry) {
    var damage = entry[1];
    var weaponId = (count(entry) > 2) ? entry[2] : null;
    
    // Base score is damage
    var score = damage;
    
    // Add weapon priority bonuses based on build type
    if (weaponId != null) {
        if (isMagicBuild) {
            // MAGIC BUILD: DoT weapons as main DPS, DESTROYER for tactical debuffing
            if (weaponId == WEAPON_FLAME_THROWER) {
                score += 1200; // Highest priority - main DoT DPS
            } else if (weaponId == WEAPON_RHINO) {
                score += 1100; // High DPS backup
            } else if (weaponId == WEAPON_ELECTRISOR) {
                score += 1000; // Good DPS + AoE
            } else if (weaponId == WEAPON_DESTROYER) {
                score += 900; // Tactical debuff (lower than main DPS)
            } else if (weaponId == WEAPON_GRENADE_LAUNCHER) {
                score += 800; // Decent DPS + AoE
            } else if (weaponId == WEAPON_B_LASER) {
                score += 700; // Multi-use backup
            } else if (weaponId == WEAPON_ENHANCED_LIGHTNINGER) {
                score += 600; // Healing capability
            } else if (weaponId == WEAPON_M_LASER) {
                score += 500; // Alignment required
            } else if (weaponId == WEAPON_RIFLE) {
                score += 400; // Standard weapon
            } else if (weaponId == WEAPON_KATANA) {
                score += 300; // Melee backup
            } else if (weaponId == WEAPON_SWORD) {
                score += 200; // Basic melee
            }
        } else {
            // STRENGTH BUILD: Standard priorities
            if (weaponId == WEAPON_RHINO) {
                score += 1000; // Highest priority - excellent DPS, low cost
            } else if (weaponId == WEAPON_ELECTRISOR) {
                score += 900; // High priority - good DPS, AoE
            } else if (weaponId == WEAPON_GRENADE_LAUNCHER) {
                score += 800; // Good priority - decent DPS, AoE
            } else if (weaponId == WEAPON_B_LASER) {
                score += 700; // Good priority - multi-use
            } else if (weaponId == WEAPON_ENHANCED_LIGHTNINGER) {
                score += 600; // Moderate priority - healing capability
            } else if (weaponId == WEAPON_M_LASER) {
                score += 500; // Moderate priority - high damage but alignment required
            } else if (weaponId == WEAPON_RIFLE) {
                score += 400; // Lower priority - standard weapon
            } else if (weaponId == WEAPON_DESTROYER) {
                score += 350; // Lower priority for strength builds
            } else if (weaponId == WEAPON_FLAME_THROWER) {
                score += 340; // Lower priority for strength builds
            } else if (weaponId == WEAPON_KATANA) {
                score += 300; // Low priority - melee, bonus damage
            } else if (weaponId == WEAPON_SWORD) {
                score += 100; // Lowest priority - basic melee
            }
        }
    }
    
    // DISTANCE BONUS: For magic builds using FLAME_THROWER, prefer longer distances to stay out of enemy TOXIN range
    if (isMagicBuild && weaponId == WEAPON_FLAME_THROWER && count(entry) > 0) {
        var cellId = entry[0];
        if (primaryTarget != null) {
            var targetCell = getCell(primaryTarget);
            if (targetCell != null) {
                var dist = getDistance(cellId, targetCell);
                // Bonus for distances 6-8 (max FLAME_THROWER range), penalty for close range
                if (dist >= 6 && dist <= 8) {
                    score += 50; // Prefer max range for safety
                } else if (dist >= 4 && dist <= 5) {
                    score += 25; // Moderate range is acceptable
                } else if (dist <= 3) {
                    score -= 25; // Penalty for being too close to enemy TOXIN range
                }
            }
        }
    }
    
    return score;
}