// V6 Module: ai/tactical_decisions_ai.ls
// Strategic and tactical decision making
// Refactored from decision_making.ls for better modularity

// NOTE: Global variables are defined in core/globals.ls when included via V6_main.ls
// For standalone testing only, uncomment the lines below:
// global debugEnabled = true;
// global myTP = 0;
// global myHP = 0;
// global myMaxHP = 100;
// global myMP = 0;
// global myCell = 0;
// global enemy = null;
// global enemyCell = 0;
// global enemyHP = 100;
// global myAbsShield = 0;
// global myRelShield = 0;
// global myResistance = 0;
// global turn = 1;
// global TELEPORT_AVAILABLE = false;
// global CHIP_TELEPORTATION = 401;
// global PATTERN_INITIALIZED = false;
// global GAME_PHASE = "OPENING";
// global combatState = 0;
// global WEIGHT_DAMAGE = 1.0;
// global WEIGHT_SAFETY = 0.8;

// State flags
// global STATE_CAN_MOVE = 1;
// global STATE_CAN_ATTACK = 2;
// global STATE_HAS_LOS = 4;
// global STATE_IN_RANGE = 8;
// global STATE_IS_BUFFED = 16;
// global STATE_IS_SHIELDED = 32;
// global STATE_PKILL_READY = 8192;
// global STATE_PANIC_MODE = 32768;

// Functions from debug system
// debugLog is provided by utils/debug.ls when included via V6_main.ls
// canSpendOps is provided by core/operations.ls when included via V6_main.ls

// Functions from movement system
// getReachableCells is provided by movement/reachability.ls when included via V6_main.ls
// moveToCell is provided by movement/positioning.ls when included via V6_main.ls
// moveToward is provided by movement/positioning.ls when included via V6_main.ls

// Functions from core system
// getOperationLevel is provided by core/operations.ls when included via V6_main.ls

// Functions from teleportation system
// findBestTeleportTarget is provided by movement/teleportation.ls when included via V6_main.ls
// useChipOnCell is provided by combat/chip_management.ls when included via V6_main.ls

// Functions from pattern learning
// updatePatternLearning is provided by strategy/pattern_learning.ls when included via V6_main.ls
// applyPatternPredictions is provided by strategy/pattern_learning.ls when included via V6_main.ls

// Functions from influence map
// buildInfluenceMap is provided by ai/influence_map.ls when included via V6_main.ls
// visualizeInfluenceMap is provided by ai/visualization.ls when included via V6_main.ls
// precomputeEID is provided by ai/eid_system.ls when included via V6_main.ls

// Functions from damage calculation
// calculateEHP is provided by ai/evaluation.ls when included via V6_main.ls
// calculateEID is provided by ai/eid_system.ls when included via V6_main.ls
// calculateMaxDamage is provided by combat/damage_calculation.ls when included via V6_main.ls
// calculateLifeSteal is provided by combat/damage_calculation.ls when included via V6_main.ls
// calculatePkill is provided by strategy/kill_calculations.ls when included via V6_main.ls

// Functions from strategy system
// determineGamePhase is provided by strategy/phase_management.ls when included via V6_main.ls
// adjustKnobs is provided by core/operations.ls when included via V6_main.ls
// quickCombatDecision is provided by ai/decision_making.ls when included via V6_main.ls
// ensembleDecision is provided by strategy/ensemble_system.ls when included via V6_main.ls
// makeQuickEmergencyDecision is provided by ai/emergency_decisions.ls when included via V6_main.ls

// LeekScript constants (defined by LeekScript engine)
// global USE_SUCCESS = 1;
// global USE_CRITICAL = 2;

// Include required modules


// Function: makeTacticalDecision
// Main tactical decision logic - returns action to take


function makeTacticalDecision() {
    // Check teleportation opportunities first
    var teleportAction = evaluateTeleportation();
    if (teleportAction != null) {
        return teleportAction;
    }
    
    // Update pattern learning and apply predictions
    updatePatternLearning();
    if (PATTERN_INITIALIZED) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Applying pattern predictions");
        }
        var predictions = null; // Would come from updatePatternLearning() 
        applyPatternPredictions(predictions);
    }
    
    // Get current operational mode and build influence map if needed
    var currentMode = getOperationLevel();
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Current mode: " + currentMode);
    }
    
    if (currentMode != "PANIC" && canSpendOps(3000000)) {
        if (debugEnabled && canSpendOps(2000)) {
            debugLog("Building influence map...");
        }
        buildInfluenceMap();
        
        // Visualize in debug mode for early turns
        if (debugEnabled && turn <= 5 && canSpendOps(50000)) {
            visualizeInfluenceMap();
        }
    }
    
    // Precompute EID for candidate cells
    var candidateCells = getReachableCells(myCell, myMP + 3);
    var eidCap = (currentMode == "PANIC") ? 5 : min(10, count(candidateCells));
    
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Precomputing EID for " + min(eidCap, count(candidateCells)) + " cells...");
    }
    
    precomputeEID(candidateCells, eidCap);
    
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("EID precomputation complete");
    }
    
    return evaluateStrategicOptions();
}


// Function: evaluateTeleportation
// Check for teleportation opportunities


function evaluateTeleportation() {
    // AGGRESSIVE TELEPORTATION: Check if we can teleport for tactical advantage!
    if (TELEPORT_AVAILABLE && turn >= 3 && myTP >= 12 && canSpendOps(500000)) {
        var bestTeleportCell = findBestTeleportTarget();
        
        if (bestTeleportCell != null && bestTeleportCell != myCell) {
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("AGGRESSIVE TELEPORT OPPORTUNITY!");
                debugLog("Best teleport target: " + bestTeleportCell + " (current: " + getCell() + ")");
            }
            
            var teleportResult = useChipOnCell(CHIP_TELEPORTATION, bestTeleportCell);
            if (teleportResult == USE_SUCCESS || teleportResult == USE_CRITICAL) {
                myCell = getCell();
                myMP = getMP();
                myTP = getTP();
                enemyCell = getCell(enemy);

                var currentDist = getCellDistance(myCell, enemyCell);
                
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("After teleport distance: " + currentDist);
                }
                
                // Move after teleporting if needed to get into attack range
                if (currentDist > 9 && myMP > 0) {
                    if (debugEnabled && canSpendOps(1000)) {
                        debugLog("Need to move after teleport to attack!");
                    }

                    var moveSteps = min(myMP, currentDist - 7);
                    moveToward(enemy, moveSteps);
                    if (debugEnabled && canSpendOps(1000)) {
                        debugLog("Moved to range " + getCellDistance(getCell(), getCell(enemy)) + " after teleport");
                    }
                }
                
                return "teleport_executed";
            } else {
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Failed to execute teleport!");
                }
            }
        } else {
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("No valid teleport target found!");
            }
        }
    }
    
    return null;
}


// Function: evaluateStrategicOptions
// Evaluate strategic options based on current state


function evaluateStrategicOptions() {
    // Calculate key metrics
    var myEHP = calculateEHP(myHP, myAbsShield, myRelShield, 0, myResistance);
    var enemyEHP = calculateEHP(enemyHP, getAbsoluteShield(enemy), getRelativeShield(enemy), 0, getResistance(enemy));
    var currentEID = calculateEID(myCell);
    var currentDamage = calculateMaxDamage(myCell, enemy, myTP);
    var lifeStealPotential = calculateLifeSteal(currentDamage, enemy);
    var pkillCurrent = calculatePkill(enemyHP, myTP);
    
    if (debugEnabled && canSpendOps(2000)) {
        debugLog("State: MyEHP=" + myEHP + " EnemyEHP=" + enemyEHP + " EID=" + currentEID + 
                " Damage=" + currentDamage + " LifeSteal=" + lifeStealPotential + " Pkill=" + pkillCurrent);
    }
    
    // Determine game phase and adjust strategy
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Calling determineGamePhase...");
    }
    determineGamePhase();
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Current phase: " + GAME_PHASE);
    }
    
    // Adjust tactical parameters
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Calling adjustKnobs...");
    }
    adjustKnobs();
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Knobs adjusted");
    }
    
    // Check for quick combat decision
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Checking quick combat decision...");
    }
    
    var quickDecision = null;
    if (canSpendOps(2000000)) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Calling quickCombatDecision...");
        }
        quickDecision = quickCombatDecision();
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Quick decision result: " + quickDecision);
        }
        
        // Log state for debugging
        if (debugEnabled && turn <= 5 && canSpendOps(3000)) {
            var stateDesc = [];
            if ((combatState & STATE_CAN_MOVE) > 0) push(stateDesc, "CAN_MOVE");
            if ((combatState & STATE_CAN_ATTACK) > 0) push(stateDesc, "CAN_ATTACK");
            if ((combatState & STATE_HAS_LOS) > 0) push(stateDesc, "HAS_LOS");
            if ((combatState & STATE_IN_RANGE) > 0) push(stateDesc, "IN_RANGE");
            if ((combatState & STATE_IS_BUFFED) > 0) push(stateDesc, "IS_BUFFED");
            if ((combatState & STATE_IS_SHIELDED) > 0) push(stateDesc, "IS_SHIELDED");
            if ((combatState & STATE_PKILL_READY) > 0) push(stateDesc, "PKILL_READY");
            if ((combatState & STATE_PANIC_MODE) > 0) push(stateDesc, "PANIC_MODE");
            
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("Combat states: " + join(stateDesc, ", "));
                debugLog("Quick decision: " + quickDecision);
            }
        }
    }
    
    // Check ensemble decision for non-panic modes
    var ensembleAction = null;
    var currentMode = getOperationLevel();
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Checking ensemble decision for mode: " + currentMode);
    }
    
    if (currentMode != "PANIC" && canSpendOps(3000000)) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Calling ensembleDecision...");
        }
        ensembleAction = ensembleDecision();
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Ensemble action: " + ensembleAction);
        }
    }
    
    if (ensembleAction != null && ensembleAction != "default") {
        return ensembleAction;
    }
    
    if (quickDecision != null && quickDecision != "continue") {
        var quickAction = makeQuickEmergencyDecision();
        return quickAction;
    }
    
    return "standard_positioning";
}


// Function: evaluatePositioning
// Evaluate positioning options - Stage B logic


function evaluatePositioning() {
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Stage B: Standard positioning check");
    }
    
    var currentCellDamage = calculateMaxDamage(myCell, enemy, myTP);
    var currentCellEID = calculateEID(myCell);
    var currentScore = currentCellDamage * WEIGHT_DAMAGE - currentCellEID * WEIGHT_SAFETY;
    
    if (debugEnabled && canSpendOps(2000)) {
        debugLog("Current position damage=" + currentCellDamage + " EID=" + currentCellEID + " score=" + currentScore);
    }
    
    var bestCell = myCell;
    var bestScore = currentScore;
    var reachable = getReachableCells(myCell, myMP);
    
    for (var i = 0; i < min(20, count(reachable)); i++) {
        var cell = reachable[i];
        var damage = calculateMaxDamage(cell, enemy, myTP);
        var eid = calculateEID(cell);
        var score = damage * WEIGHT_DAMAGE - eid * WEIGHT_SAFETY;
        
        if (debugEnabled && canSpendOps(1000) && i < 10) {
            debugLog("  Cell " + cell + ": damage=" + damage + " EID=" + eid + " score=" + score);
        }
        
        if (score > bestScore) {
            bestScore = score;
            bestCell = cell;
        }
    }
    
    if (bestCell != myCell && bestScore > currentScore + 50) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Moving to cell " + bestCell + " (score=" + bestScore + " vs current=" + currentScore + ")");
        }
        moveToCell(bestCell);
        return "position_improved";
    }
    
    return "position_optimal";
}