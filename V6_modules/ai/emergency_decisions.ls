// V6 Module: ai/emergency_decisions.ls
// Emergency decision making and panic mode handling
// Refactored from decision_making.ls for better modularity

// === STANDALONE COMPILATION SUPPORT ===
// These variables/functions are defined in other modules when included via V6_main.ls
// For standalone compilation, provide stub implementations

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
// global enemyDistance = 5;
// global turn = 1;

// Functions from debug system
// debugLog is provided by utils/debug.ls when included via V6_main.ls
// canSpendOps is provided by core/operations.ls when included via V6_main.ls

// Functions from movement system
// getReachableCells is provided by movement/reachability.ls when included via V6_main.ls
// moveToCell is provided by movement/positioning.ls when included via V6_main.ls
// bestApproachStep is provided by movement/pathfinding.ls when included via V6_main.ls

// Functions from combat system
// executeAttack is provided by combat/attack_execution.ls when included via V6_main.ls
// executeDefensive is provided by combat/execute_combat_refactored.ls when included via V6_main.ls
// executeDamageSequence is provided by combat/damage_sequences.ls when included via V6_main.ls

// Functions from core system
// isInPanicMode is provided by core/state_management.ls when included via V6_main.ls
// simplifiedCombat is provided by combat/execute_combat_refactored.ls when included via V6_main.ls
// getOperationLevel is provided by core/operations.ls when included via V6_main.ls

// Functions from strategy system
// getAliveEnemies is provided by strategy/multi_enemy.ls when included via V6_main.ls
// getTurn1Strategy is provided by strategy/phase_management.ls when included via V6_main.ls  
// getBestDamageSequence is provided by combat/damage_sequences.ls when included via V6_main.ls

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

// Function: bestFleeStep
function bestFleeStep() {
    // Find the best cell to flee to (maximize distance from enemies)
    var reachable = getReachableCells(myCell, myMP);
    var bestCell = myCell;
    var bestScore = -1;
    
    for (var i = 0; i < count(reachable); i++) {
        var cell = reachable[i];
        var score = 0;
        
        // Calculate total distance to all enemies
        var localEnemies = getAliveEnemies();
        for (var j = 0; j < count(localEnemies); j++) {
            var currentEnemy = localEnemies[j];
            var dist = getCellDistance(cell, getCell(currentEnemy));
            score += dist;
        }
        
        // Prefer cells that maximize distance to enemies
        if (score > bestScore) {
            bestScore = score;
            bestCell = cell;
        }
    }
    
    return bestCell;
}

// Function: handleEmergencyDecisions
// Returns true if emergency action was taken, false to continue normal processing
function handleEmergencyDecisions() {
    // Check for panic mode first
    if (isInPanicMode()) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("PANIC MODE - Using simplified tactics");
        }
        simplifiedCombat();
        return true;
    }
    
    // Emergency check for mid-game turns to avoid timeout
    if (turn >= 5 && !canSpendOps(4000000)) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Turn 5+ emergency mode - simplified logic");
        }
        // Just find a decent position and attack
        var step = bestApproachStep(enemyCell);
        if (step != myCell) {
            moveToCell(step);
            myCell = getCell();
            myMP = getMP();
            enemyDistance = getCellDistance(myCell, enemyCell);
        }
        executeAttack();
        if (myTP >= 4) executeDefensive();
        return true;
    }
    
    // Emergency check for late turns to avoid timeout
    if (turn >= 9 && !canSpendOps(2000000)) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Turn 9+ emergency mode - direct attack");
        }
        executeAttack();
        if (myTP >= 4) executeDefensive();
        return true;
    }
    
    return false; // No emergency action taken
}

// Function: handleAggressiveOpening
// Returns true if aggressive opening was executed, false to continue
function handleAggressiveOpening() {
    // NEW: Check for aggressive opening with damage sequences (Turn 1-2)
    if (turn <= 2) {
        var strategy = getTurn1Strategy(enemy);
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Turn " + turn + " strategy: " + strategy);
        }
        
        if (strategy == "all_damage") {
            // Skip ALL buffs, maximum damage
            var mySTR = getStrength();
            var sequence = getBestDamageSequence(myTP, enemyDistance, myHP, mySTR);
            if (sequence != null) {
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Aggressive opening! Sequence: " + sequence[4] + " for " + sequence[2] + " damage");
                }
                var dmgDealt = executeDamageSequence(sequence, enemy);
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Damage dealt: " + dmgDealt);
                }
                return true;
            }
        }
    }
    
    return false; // No aggressive opening executed
}

// Function: handlePanicModeDecisions
// Ultra-basic decisions when in panic mode
function handlePanicModeDecisions() {
    if (getOperationLevel() == "PANIC") {
        // Emergency mode - just attack or flee
        if (debugEnabled && canSpendOps(500)) {
            debugLog("⚠️ PANIC MODE - Emergency only!");
        }
        
        if (myTP >= 5 && enemyDistance <= 10) {
            executeAttack();
        } else if (myMP > 0 && enemyDistance < 6) {
            // Flee if too close
            var step = bestFleeStep();
            if (step != myCell) {
                moveToCell(step);
            }
        }
        
        if (myTP >= 4) {
            executeDefensive();
        }
        return true;
    }
    
    return false;
}

// Function: makeQuickEmergencyDecision
// Quick tactical decision for when operations are limited
function makeQuickEmergencyDecision() {
    // Simple heuristics for quick decisions
    var currentMode = getOperationLevel();
    
    if (enemyDistance <= 3 && myTP >= 7) {
        return "close_combat";
    } else if (enemyDistance >= 10 && myMP > 2) {
        return "approach";
    } else if (myHP < myMaxHP * 0.3 && myTP >= 4) {
        return "defensive";
    } else if (myTP >= 5) {
        return "attack";
    }
    
    return "default";
}