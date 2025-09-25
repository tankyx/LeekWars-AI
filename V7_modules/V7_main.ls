// ===================================================================
// VIRUS LEEK V7.0 - STREAMLINED AI WITH DAMAGE-ZONE OPTIMIZATION
// Version 7.0.1 - Runtime Error Fixes (Jan 2025)
// ===================================================================
// Core Philosophy: Calculate damage zones from enemy position, A* to optimal cell
// Architecture: 12 modules, ~1,180 lines (91% reduction from V6)
// Performance: Enemy-centric damage calculation + scenario-based combat

// === INCLUDE MODULES ===
include("core/globals");
include("config/weapons");
include("decision/evaluation");
include("decision/targeting");
include("decision/emergency");
include("decision/buffs");
include("combat/execution");
include("movement/pathfinding");
include("utils/debug");
include("utils/cache");
include("decision/optimization");

// === MAIN GAME LOOP ===
function main() {
    // CRITICAL: Verify main() is being called
    // Main function called - turn start
    
    // Clear caches at start of turn
    clearCaches();
    // Caches cleared
    
    // Update game state
    updateGameState();
    // Game state updated
    
    // Update target priorities
    updatePrimaryTarget();
    
    // Ensure backward compatibility variables are set
    if (primaryTarget != null) {
        enemy = primaryTarget;
        enemyCell = getCell(primaryTarget);
    } else {
        enemy = null;
        enemyCell = null;
    }
    
    if (debugEnabled) {
        // Turn status logged
        if (primaryTarget != null && enemyData[primaryTarget] != null) {
            var data = enemyData[primaryTarget];
            // Primary enemy status logged
        }
    }
    
    // No enemy - end turn
    if (primaryTarget == null) {
        // Early exit - no enemies
        return;
    }
    
    // Checking emergency mode
    
    // Check for emergency mode
    if (isEmergencyMode()) {
        debug("EMERGENCY MODE ACTIVATED");
        executeEmergencyMode();
        // Continue with normal combat if we still have TP/MP after emergency actions
        if (myTP > 0 || myMP > 0) {
            debug("CONTINUING COMBAT AFTER EMERGENCY ACTIONS: TP=" + myTP + ", MP=" + myMP);
        } else {
            debug("MAIN: No resources after emergency, ending turn");
            return; // No resources left, end turn
        }
    }
    
    debug("MAIN: About to call executeNormalTurn()");
    
    // Normal combat flow
    executeNormalTurn();
    
    debug("MAIN: executeNormalTurn() completed");
    
    if (debugEnabled) {
        debug("=== TURN END ===");
    }
}

// === NORMAL TURN EXECUTION ===
function executeNormalTurn() {
    debug("EXECUTE NORMAL TURN: Starting");
    
    // Apply buffs at start of turn (before combat calculations)
    if (!emergencyMode && getTurn() <= 10) {
        var tpUsed = applyTurnBuffs();
        myTP -= tpUsed;
        if (debugEnabled && tpUsed > 0) {
            debug("Applied buffs: Used " + tpUsed + " TP, Remaining: " + myTP);
        }
    }
    
    // Clear previous turn's marks
    clearMarks();
    
    // Step 1: Calculate multi-enemy damage zones with enemy associations (compute once per turn)
    var damageArray = [];
    
    // SAFE: Damage calculation with defensive checks
    debug("ENEMY STATE: allEnemies=" + (allEnemies == null ? "NULL" : "NOT_NULL"));
    if (allEnemies != null) {
        debug("ENEMY COUNT: " + count(allEnemies));
    }
    
    if (allEnemies != null && count(allEnemies) > 0) {
        debug("DAMAGE CALC: Starting with " + count(allEnemies) + " enemies");
        if (damageArrayTurn != getTurn() || currentDamageArray == null || count(currentDamageArray) == 0) {
            damageArray = calculateMultiEnemyDamageZones();
            damageArrayTurn = getTurn();
        } else {
            damageArray = currentDamageArray; // reuse cached zones for this turn
        }
        debug("DAMAGE CALC: Completed with " + count(damageArray) + " zones");
        
        // FALLBACK: If calculation returned empty, create basic zones
        if (damageArray == null || count(damageArray) == 0) {
            debugW("FALLBACK TRIGGERED: Empty damage zones, creating movement zones");
            damageArray = [];
            
            // Smart fallback: create movement zones toward enemy
            var weapons = getWeapons();
            debugW("FALLBACK: weapons=" + (weapons == null ? "NULL" : count(weapons)));
            if (weapons != null && count(weapons) > 0) {
                // Use validated enemy cell from enemyData instead of calling getCell() again
                var firstEnemy = allEnemies[0];
                var firstEnemyCell = enemyData[firstEnemy] != null ? enemyData[firstEnemy].cell : 161; // Default to center if no data
                debugW("FALLBACK: Moving toward enemy at cell " + firstEnemyCell);
                
                if (firstEnemyCell != null) {
                    // ULTRA SIMPLE: Just move closer to enemy
                    debugW("FALLBACK: Creating movement zone toward enemy at " + firstEnemyCell);
                    
                    // Calculate direction toward enemy
                    var currentDistance = getCellDistance(myCell, firstEnemyCell);
                    var targetCell = firstEnemyCell;
                    
                    // Try to get to range 8 (good for most weapons)
                    if (currentDistance > 8) {
                        // Find a cell roughly 8 distance from enemy, in our direction
                        var cells8 = getCellsAtExactDistance(firstEnemyCell, 8);
                        var bestCell = myCell;
                        var bestDistance = 999;
                        
                        for (var i = 0; i < count(cells8) && i < 10; i++) {
                            var cell = cells8[i];
                            if (getCellContent(cell) == CELL_EMPTY) {
                                var distanceFromUs = getCellDistance(myCell, cell);
                                if (distanceFromUs < bestDistance) {
                                    bestDistance = distanceFromUs;
                                    bestCell = cell;
                                }
                            }
                        }
                        targetCell = bestCell;
                    } else {
                        // We're close enough, just use current position  
                        targetCell = myCell;
                    }
                    
                    push(damageArray, [targetCell, 50, weapons[0]]);
                    debugW("FALLBACK: Added movement zone [" + targetCell + ", 50, " + weapons[0] + "] distance=" + getCellDistance(targetCell, firstEnemyCell));
                }
            } else {
                debugW("FALLBACK: No weapons available for fallback");
            }
        }
    } else {
        debug("DAMAGE CALC: No enemies found");
    }
    
    // Store damage array globally for combat execution
    currentDamageArray = damageArray;
    
    if (debugEnabled) {
        debug("DAMAGE ZONES: Generated " + count(damageArray) + " total damage zones");
        if (count(damageArray) > 0) {
            debug("SAMPLE ZONES: First zone cell=" + damageArray[0][0] + ", damage=" + damageArray[0][1] + ", weapon=" + damageArray[0][2]);
            var weapons = getWeapons();
            debug("MY WEAPONS: Count=" + count(weapons) + ", Available=" + weapons);
        } else {
            debug("WARNING: No damage zones generated - AI will not attack");
        }
        debug("PROCEEDING TO: Immediate combat check");
    }
    
    // TEMPORARY: Force debug output regardless of setting
    debug("FORCE DEBUG: About to check immediate combat");
    
    if (debugEnabled) {
        // Mark key positions for reference
        markText(myCell, "ME", getColor(0, 255, 0), 15);      // My position - bright green
        
        // Mark all enemies with different colors
        for (var i = 0; i < count(allEnemies); i++) {
            var enemyEntity = allEnemies[i];
            if (getLife(enemyEntity) > 0) {
                var currentEnemyCell = getCell(enemyEntity);
                var color = (enemyEntity == primaryTarget) ? getColor(255, 0, 255) : getColor(255, 128, 0);
                var label = (enemyEntity == primaryTarget) ? "PRIMARY" : "E" + i;
                markText(currentEnemyCell, label, color, 15);
            }
        }
        
        // Mark damage zones from array with text values
        for (var i = 0; i < count(damageArray); i++) {
            var entry = damageArray[i];
            
            // Safety check: ensure entry has at least 2 elements
            if (entry == null || count(entry) < 2) {
                continue;
            }
            
            var cellId = entry[0];
            var damage = entry[1];
            
            // Safety check: ensure damage is a valid number
            if (damage == null || isNaN(damage)) {
                continue;
            }
            
            // Round damage for cleaner display
            var displayDamage = floor(damage + 0.5);
            
            if (damage > 1000) {
                markText(cellId, "" + displayDamage, getColor(255, 0, 0), 10); // High damage - red
            } else if (damage > 500) {
                markText(cellId, "" + displayDamage, getColor(255, 165, 0), 10); // Medium damage - orange
            } else if (damage > 0) {
                markText(cellId, "" + displayDamage, getColor(255, 255, 255), 10); // Low damage - white
            }
        }
    }
    
    // Step 2: Check for immediate close-range combat (KATANA priority)
    debugW("STEP 2: Checking immediate combat opportunity");
    var immediateAttack = checkImmediateCombatOpportunity();
    var immediateWeapon = null;
    var immediateDamage = 0;
    if (immediateAttack != null && count(immediateAttack) > 0 && immediateAttack[0] != null) {
        immediateWeapon = immediateAttack[0];
        debugW("IMMEDIATE ATTACK: Found weapon " + immediateWeapon + " for immediate use");
        // Estimate simple damage from current cell for comparison against path/tele plans
        var tgt = (primaryTarget != null) ? getCell(primaryTarget) : null;
        if (tgt != null) {
            var effects = getWeaponEffects(immediateWeapon);
            var base = 0;
            for (var e = 0; e < count(effects); e++) {
                if (effects[e][0] == 1) { base = (effects[e][1] + effects[e][2]) / 2; break; }
            }
            if (base == 0) { base = getWeaponCost(immediateWeapon) * 10; }
            var switchCost = (getWeapon() != immediateWeapon) ? 1 : 0;
            var tpAvail = max(0, getTP() - switchCost);
            var uses = floor(tpAvail / getWeaponCost(immediateWeapon));
            var maxUses = getWeaponMaxUses(immediateWeapon);
            if (maxUses > 0) uses = min(uses, maxUses);
            immediateDamage = floor(base * (1 + myStrength / 100.0) * uses + 0.5);
        }
    } else {
        debugW("IMMEDIATE ATTACK: None found, proceeding to pathfinding");
    }
    
    // Step 3: Smart teleportation when movement fails or enemy needs finishing
    debugW("STEP 3: Checking teleportation options");
    var shouldConsiderTeleport = false;
    var enemyNeedsFinishing = false;
    
    // Check if any enemy has low HP (below 30% or less than 500 HP)
    var currentEnemies = getEnemies();
    for (var i = 0; i < count(currentEnemies); i++) {
        var currentEnemyHP = getLife(currentEnemies[i]);
        var currentEnemyMaxHP = getTotalLife(currentEnemies[i]);
        if (currentEnemyHP > 0 && (currentEnemyHP < 500 || (currentEnemyHP / currentEnemyMaxHP) < 0.3)) {
            enemyNeedsFinishing = true;
            break;
        }
    }
    
    // Consider teleport if pathfinding will likely fail or enemy needs finishing
    if (enemyNeedsFinishing || count(damageArray) < 3) {
        shouldConsiderTeleport = true;
    }
    // Do not consider teleport in the first two turns
    if (getTurn() <= 2) {
        shouldConsiderTeleport = false;
    }
    
    // Step 4: Find optimal path using A* with damage array
    debugW("STEP 4: Starting pathfinding with " + count(damageArray) + " damage zones");
    // Use dual-map pathfinding when available (weapon-first, then chips)
    var pathResult = null;
    if (currentWeaponDamageArray != null && currentChipDamageArray != null && (count(currentWeaponDamageArray) + count(currentChipDamageArray)) > 0) {
        pathResult = findOptimalPathFromDualArrays(myCell, currentWeaponDamageArray, currentChipDamageArray);
    } else {
        pathResult = findOptimalPathFromArray(myCell, damageArray);
    }
    debugW("STEP 4: Pathfinding completed, result=" + (pathResult == null ? "NULL" : "SUCCESS"));
    if (debugEnabled) {
        if (pathResult == null) {
            debug("PATHFINDING FAILED: No path found from " + count(damageArray) + " damage zones");
        } else if (count(pathResult) < 7) {
            debug("PATHFINDING ERROR: Returned array size " + count(pathResult) + " instead of 7");
        } else {
            debug("PATHFINDING SUCCESS: Found path to cell " + pathResult[0] + " with damage " + pathResult[2]);
        }
    }
    
    // Step 4b: If no damage zones available, move toward closest enemy to get into weapon range
    // Check if all damage zones are invalid (null or 0 damage)
    var hasValidDamage = false;
    for (var i = 0; i < count(damageArray); i++) {
        if (damageArray[i][1] != null && damageArray[i][1] > 0) {
            hasValidDamage = true;
            break;
        }
    }
    
    // Step 4b: Smart teleportation when pathfinding fails or enemy needs finishing
    if ((pathResult == null || shouldConsiderTeleport) && count(allEnemies) > 0) {
        var teleportExecuted = false;
        var originalPathResult = pathResult; // Preserve original pathfinding result
        
        // Try teleportation if we have enough TP and good damage zones exist
        if (myTP >= 15 && count(damageArray) > 0) { // 9 TP for teleport + 6+ for weapon
            var bestTeleportTarget = null;
            var bestTeleportDamage = 0;
            var bestTeleportWeapon = null;
            
            if (debugEnabled) {
                debug("TELEPORT EVAL: " + myTP + " TP available, " + count(damageArray) + " damage zones, enemyNeedsFinishing=" + enemyNeedsFinishing);
            }
            
            // Find best teleport target from damage zones
            for (var i = 0; i < count(damageArray); i++) {
                var zoneCell = damageArray[i][0];
                var zoneDamage = damageArray[i][1];
                var zoneWeapon = (count(damageArray[i]) > 2) ? damageArray[i][2] : null;
                
                // For finishing blows, accept lower damage thresholds
                var damageThreshold = enemyNeedsFinishing ? 100 : 400;
                
                if (zoneDamage > bestTeleportDamage && zoneDamage > damageThreshold) {
                    // Check if we can teleport to this position (range 1-12)
                    var teleportDistance = getCellDistance(myCell, zoneCell);
                    if (getCellContent(zoneCell) == CELL_EMPTY && teleportDistance >= 1 && teleportDistance <= 12) {
                        bestTeleportTarget = zoneCell;
                        bestTeleportDamage = zoneDamage;
                        bestTeleportWeapon = zoneWeapon;
                    }
                }
            }
            
            // Execute teleportation if we found a good target
            if (bestTeleportTarget != null) {
                if (debugEnabled) {
                    debug("SMART TELEPORT: To cell " + bestTeleportTarget + " for " + bestTeleportDamage + " damage (weapon " + bestTeleportWeapon + ")");
                }
                
                // Use teleport chip if available
                if (canUseChip(CHIP_TELEPORTATION, bestTeleportTarget)) {
                    useChip(CHIP_TELEPORTATION, bestTeleportTarget);
                    
                    // Update position after teleport
                    myCell = getCell();
                    myMP = getMP();
                    myTP = getTP();
                    teleportExecuted = true;
                    
                    if (debugEnabled) {
                        debug("TELEPORT SUCCESS: New position=" + myCell + ", TP remaining=" + myTP);
                    }
                    
                    // Set pathResult with teleport info for combat execution
                    pathResult = [bestTeleportTarget, [], bestTeleportDamage, bestTeleportWeapon, 0, 0, true];
                } else {
                    if (debugEnabled) {
                        debug("TELEPORT FAILED: Chip not available or on cooldown");
                    }
                }
            } else {
                if (debugEnabled) {
                    debug("TELEPORT SKIPPED: No suitable target found");
                }
            }
        }
        
        // Fallback movement if teleport didn't work and no valid damage
        if (!teleportExecuted && !hasValidDamage) {
            if (debugEnabled) {
                debug("PATHFINDING FALLBACK: Moving toward closest enemy");
            }
            
            // Find closest alive enemy
            var closestEnemy = null;
            var closestDistance = 999;
            for (var e = 0; e < count(allEnemies); e++) {
                if (getLife(allEnemies[e]) > 0) {
                    var distance = getCellDistance(myCell, getCell(allEnemies[e]));
                    if (distance < closestDistance) {
                        closestDistance = distance;
                        closestEnemy = allEnemies[e];
                    }
                }
            }
            
            // Move toward closest enemy
            if (closestEnemy != null) {
                var targetCell = getCell(closestEnemy);
                
                // Simple movement toward enemy
                var mpUsed = moveTowardCells([targetCell], myMP);
                if (mpUsed > 0) {
                    myCell = getCell();
                    myMP = getMP();
                    if (debugEnabled) {
                        debug("Moved " + mpUsed + " MP toward enemy at " + targetCell);
                    }
                }
                
                // Set pathResult to indicate fallback movement was handled (no weapon recommendation)
                // Keep pathResult as null for fallback movement since no specific weapon was calculated
            }
        }
        
        // If neither teleport nor fallback movement occurred, restore original pathfinding result
        if (!teleportExecuted && originalPathResult != null) {
            pathResult = originalPathResult;
            if (debugEnabled) {
                debug("PATHFINDING RESTORED: Using original path result since no teleport/fallback occurred");
            }
        }
        
        if (debugEnabled) {
            debug("TELEPORT BLOCK END: teleportExecuted=" + teleportExecuted + ", pathResult=" + (pathResult != null ? "NOT_NULL" : "NULL"));
        }
    }
    
    // Debug path result with defensive checks
    if (debugEnabled) {
        if (pathResult != null) {
            debug("PATHRESULT DEBUG: Found valid path result");
            debugPath(pathResult);
        } else {
            debug("PATHRESULT DEBUG: pathResult is NULL - no movement/combat will occur");
        }
    }
    
    // Step 5: Execute movement (if pathfinding found a valid path)
    debugW("STEP 5: Checking movement execution, pathResult=" + (pathResult == null ? "NULL" : "EXISTS"));
    if (pathResult != null) {
        // Consider teleport+movement alternative if it yields immediate damage
        if (getTurn() > 2) {
            var teleAlt = tryTeleportMovementFallback(myCell, currentDamageArray);
            if (teleAlt != null) {
                var moveDamage = (count(pathResult) >= 3) ? pathResult[2] : 0;
                var teleDamage = (count(teleAlt) >= 3) ? teleAlt[2] : 0;
                if (teleDamage > moveDamage) {
                    pathResult = teleAlt;
                }
            }
        }
        // Compare against immediate attack option; prefer whichever yields higher damage this turn
        if (immediateWeapon != null) {
            var planDamage = (count(pathResult) >= 3) ? pathResult[2] : 0;
            if (immediateDamage >= planDamage) {
                // Stick to immediate attack: build a no-move pathResult carrying the weapon
                pathResult = [myCell, [myCell], immediateDamage, immediateWeapon, true, 0, false];
            }
        }
        // Check if pathResult has path property and it's not empty
        var hasValidPath = false;
        if (pathResult != null && count(pathResult) >= 7 && pathResult[1] != null && count(pathResult[1]) >= 1) {
            hasValidPath = true;
        }
        
        var useTeleport = (pathResult != null && count(pathResult) >= 7 && pathResult[6] == true); // pathResult[6] = useTeleport
        
        debugW("STEP 5: hasValidPath=" + hasValidPath + ", useTeleport=" + useTeleport);
        debugW("STEP 5: pathResult details - count=" + count(pathResult) + ", pathResult[1]=" + (pathResult[1] == null ? "NULL" : "count=" + count(pathResult[1])));
        
        if (hasValidPath || useTeleport) {
            debugW("STEP 5: Executing movement");
            executeMovement(pathResult);
            
            // Update global state after movement to ensure correct position for combat
            myCell = getCell();
            myMP = getMP();
            myTP = getTP();
            if (debugEnabled) {
                debug("MOVEMENT COMPLETE: New position=" + myCell + ", MP=" + myMP + ", TP=" + myTP);
            }
        } else {
            if (debugEnabled) {
                debug("MOVEMENT SKIPPED: No valid path or teleport available");
            }
        }
    }
    
    // Step 6: Execute combat from final position
    debugW("STEP 6: Starting combat phase");
    var recommendedWeapon = null;
    if (pathResult != null && count(pathResult) >= 7 && pathResult[3] != null) {
        recommendedWeapon = pathResult[3]; // pathResult[3] = weaponId
    }
    
    // If no weapon recommended by pathfinding, try to find a weapon that can attack NOW
    if (recommendedWeapon == null) {
        var bestW = null;
        var bestScore = -1;
        var weaponsNow = getWeapons();
        var tgt = (primaryTarget != null) ? primaryTarget : ((count(allEnemies)>0)? allEnemies[0] : null);
        var tgtCell = (tgt != null) ? getCell(tgt) : null;
        if (weaponsNow != null && tgtCell != null) {
            for (var wi = 0; wi < count(weaponsNow); wi++) {
                var w = weaponsNow[wi];
                var switchCost = (getWeapon() != w) ? 1 : 0;
                var tpAvail = getTP() - switchCost;
                if (tpAvail < getWeaponCost(w)) continue;
                if (!canWeaponReachTarget(w, myCell, tgtCell)) continue;
                var score = getWeaponCost(w); // simple proxy for damage, avoids heavy calc
                if (score > bestScore) { bestScore = score; bestW = w; }
            }
        }
        recommendedWeapon = bestW;
    }
    
    debugW("STEP 6: recommendedWeapon=" + recommendedWeapon);
    
    if (debugEnabled) {
        debug("COMBAT PHASE: Position=" + myCell + ", TP=" + myTP + ", MP=" + myMP + ", RecommendedWeapon=" + recommendedWeapon);
        if (primaryTarget != null) {
            debug("Primary target: " + primaryTarget + ", HP=" + getLife(primaryTarget) + ", Distance=" + getCellDistance(myCell, getCell(primaryTarget)));
        }
        var weapons = getWeapons();
        debug("AVAILABLE WEAPONS: Count=" + count(weapons) + ", List=" + weapons);
        debug("DAMAGE ZONES: Available=" + count(currentDamageArray));
    }
    
    // Step 6: Combat
    if (debugEnabled) { debug("EXECUTING COMBAT: weapon=" + recommendedWeapon + ", fromCell=" + myCell); }
    
    // GUARANTEED COMBAT: Engage only if we have an actual shot; otherwise try offensive teleport
    myTP = getTP();
    debugW("STEP 6: Combat check - enemies=" + count(allEnemies) + ", TP=" + getTP() + ", myTP=" + myTP);
    if (count(allEnemies) > 0 && getTP() >= 3) {
        if (recommendedWeapon == null && inArray(getChips(), CHIP_TELEPORTATION)) {
            var teleAttempt = attemptOffensiveTeleport(getTP());
            if (teleAttempt[1]) {
                // Teleport + attack executed by combat layer
                myCell = getCell();
                myTP = getTP();
                if (debugEnabled) { debugW("COMBAT: Offensive teleport executed"); }
            } else {
                debugW("COMBAT: Skipping combat (no immediate shot and teleport not viable)");
            }
        } else {
            // Execute combat once; scenario builder will pick viable actions
            debugW("COMBAT: Calling executeCombat with weapon=" + recommendedWeapon);
            executeCombat(myCell, recommendedWeapon);
            debugW("COMBAT: executeCombat completed");
        }
    } else {
        debugW("COMBAT IMPOSSIBLE: enemies=" + count(allEnemies) + ", TP=" + getTP());
    }
    
    // Step 7: No extra hide; movement and combat already completed.
    
    if (debugEnabled) {
        debug("TURN COMPLETE: Final TP=" + getTP() + ", Final MP=" + getMP());
    }
}

// === OPTIMAL WEAPON RANGE MOVEMENT ===
function findOptimalWeaponRange(enemyCell, weapons) {
    debugW("WEAPON RANGE: Finding optimal position to attack enemy at " + enemyCell);
    
    var bestCell = null;
    var bestScore = -1;
    var maxSearchDistance = min(myMP, 6); // Conservative search to prevent timeout
    
    // For each weapon, find the optimal range
    for (var w = 0; w < count(weapons) && w < 3; w++) {
        var weapon = weapons[w];
        var minRange = getWeaponMinRange(weapon);
        var maxRange = getWeaponMaxRange(weapon);
        var weaponCost = getWeaponCost(weapon);
        
        debugW("WEAPON RANGE: Checking weapon " + weapon + " (range " + minRange + "-" + maxRange + ", cost " + weaponCost + ")");
        
        // Check if we have enough TP for this weapon
        if (myTP < weaponCost) {
            debugW("WEAPON RANGE: Skipping weapon " + weapon + " - not enough TP");
            continue;
        }
        
        // Find cells within weapon range of the enemy
        for (var range = minRange; range <= maxRange; range++) {
            var candidates = getCellsAtExactDistance(enemyCell, range);
            
            for (var i = 0; i < count(candidates) && i < 15; i++) { // Limit candidates
                var candidate = candidates[i];
                
                if (getCellContent(candidate) == CELL_EMPTY) {
                    var moveDistance = getCellDistance(myCell, candidate);
                    
                    // Can we reach this cell?
                    if (moveDistance <= maxSearchDistance) {
                        // Score based on weapon effectiveness and movement efficiency
                        var score = 100 - weaponCost - moveDistance;
                        
                        if (score > bestScore) {
                            bestScore = score;
                            bestCell = candidate;
                            debugW("WEAPON RANGE: Better position " + candidate + " for weapon " + weapon + " at range " + range + " (score " + score + ")");
                        }
                    }
                }
            }
        }
    }
    
    if (bestCell != null) {
        var distance = getCellDistance(bestCell, enemyCell);
        debugW("WEAPON RANGE: Selected cell " + bestCell + " at distance " + distance + " from enemy (score " + bestScore + ")");
        return bestCell;
    } else {
        debugW("WEAPON RANGE: No optimal weapon range found, using simple movement");
        return findSimpleMovementTowardEnemy(enemyCell);
    }
}

// === SIMPLE MOVEMENT TOWARD ENEMY (FALLBACK) ===
function findSimpleMovementTowardEnemy(enemyCell) {
    debugW("SIMPLE MOVE: Finding movement from " + myCell + " toward " + enemyCell);
    
    var originalDistance = getCellDistance(myCell, enemyCell);
    var bestCell = null;
    var bestDistance = originalDistance;
    var maxSearchDistance = min(myMP, 6); // Conservative limit
    
    // Simple radial search for better positions
    for (var distance = 1; distance <= maxSearchDistance; distance++) {
        var candidateCells = getCellsAtExactDistance(myCell, distance);
        for (var i = 0; i < count(candidateCells) && i < 15; i++) { // Limit candidates
            var candidate = candidateCells[i];
            
            if (getCellContent(candidate) == CELL_EMPTY) {
                var candidateDistance = getCellDistance(candidate, enemyCell);
                
                // Simple distance-based improvement
                if (candidateDistance < bestDistance) {
                    bestDistance = candidateDistance;
                    bestCell = candidate;
                    debugW("SIMPLE MOVE: Better cell " + candidate + " at distance " + candidateDistance);
                }
            }
        }
        
        // Early exit if we found a significant improvement
        if (bestDistance < originalDistance - 3) {
            break;
        }
    }
    
    return bestCell;
}

// === FIND CELL AT SPECIFIC RANGE ===
function findCellAtRange(fromCell, toCell, targetRange) {
    // Simple approach: find a cell approximately at targetRange from toCell
    // in the direction of fromCell
    var currentDistance = getCellDistance(fromCell, toCell);
    
    if (currentDistance <= targetRange) {
        return fromCell; // Already close enough
    }
    
    // Try cells at targetRange distance from toCell
    var candidates = getCellsAtExactDistance(toCell, targetRange);
    var bestCell = null;
    var bestDistanceToFrom = 999;
    
    for (var i = 0; i < count(candidates) && i < 10; i++) { // Limit to prevent timeout
        var candidate = candidates[i];
        if (getCellContent(candidate) == CELL_EMPTY) {
            var distanceToFrom = getCellDistance(candidate, fromCell);
            if (distanceToFrom < bestDistanceToFrom) {
                bestDistanceToFrom = distanceToFrom;
                bestCell = candidate;
            }
        }
    }
    
    return bestCell;
}

// === TURN INITIALIZATION ===
function initializeTurn() {
    // Initialize combat systems
    initializeCombatTurn();
    
    if (debugEnabled) {
        debug("V7 AI initialized - " + getCacheStats());
    }
}

// === TURN 1 SPECIAL HANDLING ===
function handleFirstTurn() {
    if (getTurn() == 1) {
        debug("First turn initialization");
        
        // Ensure myTP is updated for first turn buff calculations
        myTP = getTP();
        
        var chips = getChips();
        
        // CONSERVATIVE TURN 1 BUFFS: Reserve TP for weapons (cheapest weapon costs 7 TP)
        var reservedTP = 7; // Reserve enough TP for at least one weapon use
        var availableTP = myTP - reservedTP;
        
        debug("TURN 1 BUFFS: Total TP=" + myTP + ", Reserved=" + reservedTP + ", Available=" + availableTP);
        
        // Only apply buffs if we have enough TP left for weapons
        if (availableTP >= 6 && inArray(chips, CHIP_KNOWLEDGE) && canUseChip(CHIP_KNOWLEDGE, getEntity())) {
            useChip(CHIP_KNOWLEDGE, getEntity());
            myTP -= getChipCost(CHIP_KNOWLEDGE);
            availableTP -= getChipCost(CHIP_KNOWLEDGE);
            debug("Applied CHIP_KNOWLEDGE");
        }
        
        if (availableTP >= 3 && inArray(chips, CHIP_ARMORING) && canUseChip(CHIP_ARMORING, getEntity())) {
            useChip(CHIP_ARMORING, getEntity());
            myTP -= getChipCost(CHIP_ARMORING);
            availableTP -= getChipCost(CHIP_ARMORING);
            debug("Applied CHIP_ARMORING");
        }
        
        if (availableTP >= 3 && inArray(chips, CHIP_ELEVATION) && canUseChip(CHIP_ELEVATION, getEntity())) {
            useChip(CHIP_ELEVATION, getEntity());
            myTP -= getChipCost(CHIP_ELEVATION);
            debug("Applied CHIP_ELEVATION");
        }
        
        debug("TURN 1 COMPLETE: Remaining TP=" + myTP);
    }
}

// === EXECUTION ENTRY POINT ===
// Initialize on first run
if (getTurn() == 1) {
    // Update game state BEFORE first turn handling so myTP is available
    updateGameState();
    initializeTurn();
    handleFirstTurn();
}

// === IMMEDIATE COMBAT OPPORTUNITY CHECK ===
function checkImmediateCombatOpportunity() {
    // NEW APPROACH: Only allow immediate combat for TRUE immediate opportunities
    // (melee weapons) or critical healing. Otherwise, always consider movement.
    
    if (primaryTarget == null) {
        return null;
    }
    
    // Safety check: ensure primary target is alive
    if (getLife(primaryTarget) <= 0) {
        return null;
    }
    
    var weapons = getWeapons();
    if (weapons == null || count(weapons) == 0) {
        return null;
    }
    
    var targetCell = getCell(primaryTarget);
    if (targetCell == null || targetCell < 0) {
        return null;
    }
    
    var distance = getCellDistance(myCell, targetCell);
    var availableTP = getTP(); // Use direct API call instead of potentially stale global
    
    // MELEE WEAPONS ONLY: These are truly immediate opportunities (can't move closer)
    
    // SWORD priority: If at distance 1 with SWORD and enough TP, attack immediately (prioritized over Katana)
    if (distance == 1 && inArray(weapons, WEAPON_SWORD) && availableTP >= 6) {
        // Simple check - just verify we have the weapon and TP
        var result = [];
        push(result, WEAPON_SWORD);      // [0] weaponId
        push(result, 550);               // [1] damage (55 * 2 uses for 12 TP if available, or 55 * 1)
        push(result, "SWORD_MELEE");     // [2] reason
        return result;
    }
    
    // KATANA priority: If at distance 1 with KATANA and enough TP, attack immediately
    if (distance == 1 && inArray(weapons, WEAPON_KATANA) && availableTP >= 7) {
        // Simple check - just verify we have the weapon and TP
        var result = [];
        push(result, WEAPON_KATANA);     // [0] weaponId
        push(result, 471);               // [1] damage
        push(result, "KATANA_MELEE");    // [2] reason
        return result;
    }
    
    // CRITICAL HEALING ONLY: Only attack immediately if desperately low HP
    var currentHPPercent = myHP / myMaxHP;
    var criticalHP = (currentHPPercent < 0.25); // Only below 25% HP - very critical!
    
    if (criticalHP && distance >= 6 && distance <= 10 && inArray(weapons, WEAPON_ENHANCED_LIGHTNINGER) && availableTP >= 18) {
        if (checkLineOfSight(myCell, targetCell)) {
            var result = [];
            push(result, WEAPON_ENHANCED_LIGHTNINGER);          // [0] weaponId
            push(result, 1100);                                 // [1] damage
            push(result, "CRITICAL_HEALING");                   // [2] reason
            if (debugEnabled) {
                debug("CRITICAL HP: Immediate Enhanced Lightninger healing at " + floor(currentHPPercent * 100) + "% HP");
            }
            return result;
        }
    }
    
    // REMOVED: All other ranged weapon immediate attacks
    // Enhanced Lightninger, M-Laser, etc. should ALWAYS consider movement first
    // This forces the AI to use the pathfinding system and compare movement options
    
    if (debugEnabled) {
        debug("IMMEDIATE COMBAT: No melee or critical healing opportunity - proceeding to pathfinding");
    }
    
    // No immediate opportunity found
    return null;
}

// (Hide and seek removed)

// (Peekaboo removed)

function shouldContinuePeekABoo() {
    // Don't continue if no enemies left
    if (count(getEnemies()) == 0) {
        return false;
    }
    
    // Need at least 3 TP for minimum weapon cost
    if (getTP() < 3) {
        return false;
    }
    
    // Need at least 1 MP for repositioning (optional but helpful)
    // We allow continuing even with 0 MP for stationary attacks
    
    // Check if we have any weapon we can actually use
    var weapons = getWeapons();
    if (weapons == null || count(weapons) == 0) {
        return false;
    }
    
    for (var i = 0; i < count(weapons); i++) {
        var weapon = weapons[i];
        var cost = getWeaponCost(weapon);
        if (cost <= getTP()) {
            // We have at least one usable weapon
            return true;
        }
    }
    
    return false;
}

// (Peekaboo reposition and helpers removed)

// Execute main game logic
debugW("V7 AI STARTING - Turn " + getTurn());
main();
debugW("V7 AI FINISHED - Turn " + getTurn());
