// ===================================================================
// VIRUS LEEK V7.0 - STREAMLINED AI WITH DAMAGE-ZONE OPTIMIZATION
// ===================================================================
// Core Philosophy: Calculate damage zones from enemy position, A* to optimal cell
// Architecture: 12 modules, ~1,180 lines (91% reduction from V6)
// Performance: Enemy-centric damage calculation + scenario-based combat

// === INCLUDE MODULES ===
include("core/globals");
include("config/weapons");
include("decision/evaluation");
include("decision/emergency");
include("decision/buffs");
include("combat/execution");
include("movement/pathfinding");
include("utils/debug");
include("utils/cache");

// === MAIN GAME LOOP ===
function main() {
    // Clear caches at start of turn
    clearCaches();
    
    // Update game state
    updateGameState();
    
    if (debugEnabled) {
        debug("=== TURN START ===");
        debug("HP: " + myHP + "/" + myMaxHP + ", TP: " + myTP + ", MP: " + myMP);
        if (enemy != null) {
            debug("Enemy HP: " + enemyHP + "/" + enemyMaxHP + ", Distance: " + getCellDistance(myCell, enemyCell));
        }
    }
    
    // No enemy - end turn
    if (enemy == null) {
        debug("No enemies found");
        return;
    }
    
    // Check for emergency mode
    if (isEmergencyMode()) {
        debug("EMERGENCY MODE ACTIVATED");
        executeEmergencyMode();
        return;
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
    
    // Step 1: Calculate damage zones as array to avoid LeekScript map corruption
    var damageArray = calculateDamageZonesArray(enemyCell);
    
    
    if (debugEnabled) {
        // Mark key positions for reference
        markText(myCell, "ME", getColor(0, 255, 0), 15);      // My position - bright green
        markText(enemyCell, "ENEMY", getColor(255, 0, 255), 15); // Enemy position - bright magenta
        
        // Mark damage zones from array with text values
        for (var i = 0; i < count(damageArray); i++) {
            var entry = damageArray[i];
            var cellId = entry[0];
            var damage = entry[1];
            
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
    
    // Step 2: Consider teleportation (skip for now due to map dependency)
    // var teleportOption = considerTeleportation(damageArray);
    
    // Step 3: Find optimal path using A* with damage array
    var pathResult = findOptimalPathFromArray(myCell, damageArray);
    
    if (debugEnabled) {
        debugPath(pathResult);
    }
    
    // Step 4: Execute movement
    if (pathResult != null) {
        executeMovement(pathResult);
    }
    
    // Step 5: Execute combat from final position
    executeCombat(myCell);
    
    // Step 6: Seek cover after attacking (if MP remaining)
    if (myMP > 1) {
        var movedToCover = seekCoverAfterCombat();
        if (debugEnabled && movedToCover) {
            debug("Moved to cover after combat");
        }
    }
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
        
        var chips = getChips();
        
        // ALWAYS use this exact sequence on turn 1:
        // 1. CHIP_KNOWLEDGE for wisdom boost
        if (inArray(chips, CHIP_KNOWLEDGE) && canUseChip(CHIP_KNOWLEDGE, getEntity())) {
            useChip(CHIP_KNOWLEDGE, getEntity());
            myTP -= getChipCost(CHIP_KNOWLEDGE);
            debug("Applied CHIP_KNOWLEDGE");
        }
        
        // 2. CHIP_ARMORING for damage reduction
        if (inArray(chips, CHIP_ARMORING) && canUseChip(CHIP_ARMORING, getEntity())) {
            useChip(CHIP_ARMORING, getEntity());
            myTP -= getChipCost(CHIP_ARMORING);
            debug("Applied CHIP_ARMORING");
        }
        
        // 3. CHIP_ELEVATION for agility boost
        if (inArray(chips, CHIP_ELEVATION) && canUseChip(CHIP_ELEVATION, getEntity())) {
            useChip(CHIP_ELEVATION, getEntity());
            myTP -= getChipCost(CHIP_ELEVATION);
            debug("Applied CHIP_ELEVATION");
        }
    }
}

// === EXECUTION ENTRY POINT ===
// Initialize on first run
if (getTurn() == 1) {
    initializeTurn();
    handleFirstTurn();
}

// Execute main game logic
main();