// V6 Module: ai/decision_making_refactored.ls
// Refactored main decision making - orchestrates the specialized modules
// Replaces the monolithic 963-line decision_making.ls

// Include required modules
include("emergency_decisions");
include("tactical_decisions_ai");
include("combat_decisions");


// Function: makeDecision
// Main decision making orchestrator - prioritizes new strategy


function makeDecision() {
    // Update enemy tracking for multi-enemy support
    initializeEnemies();
    
    // Check if we should switch targets in multi-enemy scenarios
    if (count(allEnemies) > 1 && shouldSwitchTarget()) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Target switched to: " + enemy);
        }
    }
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("makeDecision called - Turn " + turn + ", enemy=" + enemy + " (" + count(allEnemies) + " total enemies)");
    }
    if (enemy == null) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("No enemy found");
        }
        return;
    }
    
    // === NEW STRATEGY DECISION FLOW ===
    // Turns 2+ use the new STEROID + RIFLE strategy prioritized over legacy logic
    
    // PHASE 1: Emergency Decisions (always first priority)
    if (handleEmergencyDecisions()) {
        return; // Emergency action taken, exit early
    }
    
    // PHASE 2: NEW STRATEGY EXECUTION (turn 2+)
    if (turn >= 2) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("=== NEW STRATEGY DECISION MAKING ===");
        }
        
        // Execute the new strategy attack system
        executeNewStrategyAttack();
        
        // Post-combat defensive actions if TP remains
        if (myTP >= 4) {
            executeDefensive();
        }
        
        // Conservative repositioning if MP remains (no TP usage)
        if (getMP() > 0 && enemy != null && getLife(enemy) > 0) {
            repositionDefensiveMP(); // MP-only repositioning
        }
        
        return; // New strategy handled everything
    }
    
    // === LEGACY FALLBACK FOR EDGE CASES ===
    // Only used if new strategy doesn't apply (turn 1 has its own sequence)
    
    // Handle panic mode ultra-basic decisions
    if (handlePanicModeDecisions()) {
        return; // Panic mode action taken, exit early
    }
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Using legacy decision flow...");
    }
    
    // Legacy tactical decisions
    var tacticalAction = makeTacticalDecision();
    
    if (tacticalAction == "teleport_executed") {
        return; // Teleportation handled everything
    } else if (tacticalAction == "standard_positioning") {
        var positionResult = evaluatePositioning();
        if (positionResult == "position_improved") {
            executeAttack();
            if (myTP >= 4) executeDefensive();
            return;
        }
    }
    
    // Legacy combat decisions
    var combatAction = makeCombatDecision();
    if (combatAction != null) {
        return;
    }
    
    // Legacy fallback
    executeFallbackLogic();
    
    // PHASE 5: Burn Remaining Operations
    // Use any leftover operations for additional analysis
    burnRemainingOperations();
    
    // PHASE 5: Visualization and Cleanup
    if (debugEnabled && canSpendOps(50000)) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Checking visualization...");
        }
        if (debugEnabled) {
            visualizeEID();
        }
    }
    
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("makeDecision() complete - exiting");
    }
}
// Function: executeFallbackLogic
// Final fallback positioning and attack logic


function executeFallbackLogic() {
    // Final positioning check - can we hit from current position?
    if (enemyDistance <= 10 && hasLOS(myCell, enemyCell)) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Can hit from current position at range " + enemyDistance);
        }
        executeAttack();
        if (myTP >= 4) executeDefensive();
    } else {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Can't hit from distance " + enemyDistance + ", need to approach");
        }
        
        if (myMP > 0) {
            var moved = false;
            var targetDist = min(8, enemyDistance - 1);
            
            if (targetDist > 0) {
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Moving closer to enemy");
                }
                moveToward(enemy, min(myMP, enemyDistance - targetDist));
                moved = true;
                
                // Update distance after movement
                myCell = getCell();
                myMP = getMP();
                enemyCell = getCell(enemy);
                enemyDistance = getCellDistance(myCell, enemyCell);
                
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("New distance: " + enemyDistance);
                }
            }
        }
        
        // Try to attack after movement
        if (enemyDistance <= 10) {
            executeAttack();
            if (myTP >= 4) executeDefensive();
        }
    }
    
    // REPOSITION after combat if we have MP left
    if (getMP() > 0 && enemy != null && getLife(enemy) > 0) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Post-combat repositioning with " + getMP() + " MP");
        }
        repositionDefensive();
    }
}