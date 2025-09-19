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

// === MAIN GAME LOOP ===
function main() {
    // CRITICAL: Verify main() is being called
    if (debugEnabled) {
        debug("=== MAIN FUNCTION CALLED - TURN " + getTurn() + " ===");
    }
    
    // Clear caches at start of turn
    clearCaches();
    
    // Update game state
    updateGameState();
    
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
        debug("=== TURN START ===");
        debug("HP: " + myHP + "/" + myMaxHP + ", TP: " + myTP + ", MP: " + myMP);
        debug("Enemies: " + count(enemies) + ", Primary Target: " + primaryTarget);
        if (primaryTarget != null && enemyData[primaryTarget] != null) {
            var data = enemyData[primaryTarget];
            debug("Primary Enemy HP: " + data.hp + "/" + data.maxHp + ", Distance: " + data.distance + ", TTK: " + data.ttk);
        }
    }
    
    // No enemy - end turn
    if (primaryTarget == null) {
        debug("EARLY EXIT: No enemies found");
        return;
    }
    
    // Check for emergency mode
    if (isEmergencyMode()) {
        debug("EMERGENCY MODE ACTIVATED");
        executeEmergencyMode();
        // Continue with normal combat if we still have TP/MP after emergency actions
        if (myTP > 0 || myMP > 0) {
            debug("CONTINUING COMBAT AFTER EMERGENCY ACTIONS: TP=" + myTP + ", MP=" + myMP);
        } else {
            return; // No resources left, end turn
        }
    }
    
    // Normal combat flow
    executeNormalTurn();
    
    if (debugEnabled) {
        debug("=== TURN END ===");
    }
}

// === NORMAL TURN EXECUTION ===
function executeNormalTurn() {
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
    
    // Step 1: Calculate multi-enemy damage zones with enemy associations
    var damageArray;
    if (enemies == null || count(enemies) == 0) {
        // No enemies - return empty damage array
        damageArray = [];
        if (debugEnabled) {
            debug("No enemies found - empty damage array");
        }
    } else if (count(enemies) >= 1) {
        // Multi-enemy mode: calculate merged damage zones with enemy associations
        // Use this for single enemies too since it handles line weapons better
        damageArray = calculateMultiEnemyDamageZones();
        
        if (debugEnabled) {
            // DEBUG: Show actual weapon IDs and their built-in constants
            var weapons = getWeapons();
            debugW("WEAPON DEBUG: Equipped weapons: [" + join(weapons, ", ") + "]");
            debugW("BUILT-IN CONSTANTS: WEAPON_RHINO=" + WEAPON_RHINO + ", WEAPON_B_LASER=" + WEAPON_B_LASER + ", WEAPON_GRENADE_LAUNCHER=" + WEAPON_GRENADE_LAUNCHER);
        }
    } else {
        // Legacy single-enemy mode - DISABLED, using multi-enemy for all cases
        damageArray = [];
        if (debugEnabled) {
            debug("ERROR: Should not reach legacy single-enemy mode - using multi-enemy instead");
        }
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
    }
    
    if (debugEnabled) {
        // Mark key positions for reference
        markText(myCell, "ME", getColor(0, 255, 0), 15);      // My position - bright green
        
        // Mark all enemies with different colors
        for (var i = 0; i < count(enemies); i++) {
            var enemyEntity = enemies[i];
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
    var immediateAttack = checkImmediateCombatOpportunity();
    if (immediateAttack != null && count(immediateAttack) > 0 && immediateAttack[0] != null) {
        executeCombat(myCell, immediateAttack[0]); // immediateAttack[0] = weaponId
        
        // Step 2b: Seek cover after immediate attack (if MP remaining)
        // Skip cover seeking for simplicity
        return; // Skip movement, we attacked from current position
    }
    
    // Step 3: Consider teleportation (skip for now due to map dependency)
    // var teleportOption = considerTeleportation(damageArray);
    
    // Step 4: Find optimal path using A* with damage array
    if (debugEnabled) {
        debug("PATHFINDING: Starting with " + count(damageArray) + " damage zones");
    }
    var pathResult = findOptimalPathFromArray(myCell, damageArray);
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
    
    if (pathResult == null && !hasValidDamage && count(enemies) > 0) {
        if (debugEnabled) {
            debug("No damage zones available - moving toward closest enemy for weapon positioning");
        }
        
        // Find closest alive enemy
        var closestEnemy = null;
        var closestDistance = 999;
        for (var e = 0; e < count(enemies); e++) {
            if (getLife(enemies[e]) > 0) {
                var distance = getCellDistance(myCell, getCell(enemies[e]));
                if (distance < closestDistance) {
                    closestDistance = distance;
                    closestEnemy = enemies[e];
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
            
            // Set pathResult to indicate movement was handled
            pathResult = null;
        }
    }
    
    // Debug path result with defensive checks
    if (debugEnabled && pathResult != null) {
        debugPath(pathResult);
    }
    
    // Step 5: Execute movement (if pathfinding found a valid path)
    if (pathResult != null) {
        // Check if pathResult has path property and it's not empty
        var hasValidPath = false;
        if (pathResult != null && count(pathResult) >= 7 && pathResult[1] != null && count(pathResult[1]) > 1) {
            hasValidPath = true;
        }
        
        var useTeleport = (pathResult != null && count(pathResult) >= 7 && pathResult[6] == true); // pathResult[6] = useTeleport
        
        if (hasValidPath || useTeleport) {
            if (debugEnabled) {
                debug("MOVEMENT: Executing movement - hasValidPath=" + hasValidPath + ", useTeleport=" + useTeleport);
            }
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
    var recommendedWeapon = null;
    if (pathResult != null && count(pathResult) >= 7 && pathResult[3] != null) {
        recommendedWeapon = pathResult[3]; // pathResult[3] = weaponId
    }
    
    if (debugEnabled) {
        debug("COMBAT PHASE: Position=" + myCell + ", TP=" + myTP + ", MP=" + myMP + ", RecommendedWeapon=" + recommendedWeapon);
        if (primaryTarget != null) {
            debug("Primary target: " + primaryTarget + ", HP=" + getLife(primaryTarget) + ", Distance=" + getCellDistance(myCell, getCell(primaryTarget)));
        }
        var weapons = getWeapons();
        debug("AVAILABLE WEAPONS: Count=" + count(weapons) + ", List=" + weapons);
        debug("DAMAGE ZONES: Available=" + count(currentDamageArray));
    }
    
    executeCombat(myCell, recommendedWeapon);
    
    if (debugEnabled) {
        debug("TURN COMPLETE: Final TP=" + getTP() + ", Final MP=" + getMP());
    }
    
    // Step 7: Seek cover after attacking (if MP remaining)
    // Skip cover seeking for simplicity
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
        if (hasLOS(myCell, targetCell)) {
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

// Execute main game logic
debugW("V7 AI STARTING - Turn " + getTurn());
main();
debugW("V7 AI FINISHED - Turn " + getTurn());