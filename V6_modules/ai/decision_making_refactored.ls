// V6 Module: ai/decision_making_refactored.ls
// Refactored main decision making - orchestrates the specialized modules
// Replaces the monolithic 963-line decision_making.ls

// Include required modules
include("emergency_decisions");
include("tactical_decisions_ai");
include("combat_decisions");

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

// Function: makeDecision
// Main decision making orchestrator - now much cleaner and modular

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

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
        debugLog("makeDecision called - enemy=" + enemy + " (" + count(allEnemies) + " total enemies)");
    }
    
    if (enemy == null) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("No enemy found");
        }
        return;
    }
    
    // PHASE 1: Emergency Decisions
    // Handle panic mode, emergency timeouts, and aggressive openings
    if (handleEmergencyDecisions()) {
        return; // Emergency action taken, exit early
    }
    
    // Check for aggressive opening (turns 1-2)
    if (handleAggressiveOpening()) {
        return; // Aggressive opening executed, exit early
    }
    
    // Handle panic mode ultra-basic decisions
    if (handlePanicModeDecisions()) {
        return; // Panic mode action taken, exit early
    }
    
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Not in panic mode, continuing...");
    }
    
    // PHASE 2: Tactical Decisions
    // Strategic positioning, teleportation, pattern learning, influence mapping

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var tacticalAction = makeTacticalDecision();
    
    if (tacticalAction == "teleport_executed") {
        return; // Teleportation handled everything
    } else if (tacticalAction == "standard_positioning") {
        // Continue to positioning evaluation with deep analysis

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

        // Try deep tactical analysis first - much more aggressive trigger
        var deepAnalysis = null;
        if (canSpendOps(1500000)) {
            deepAnalysis = performDeepTacticalAnalysis();
            if (deepAnalysis != null && count(deepAnalysis["bestPositions"]) > 0) {
                var bestPos = deepAnalysis["bestPositions"][0][0];
                if (bestPos != myCell) {
                    debugLog("🎯 Deep analysis found superior position");
                    if (moveToCell(bestPos)) {
                        executeAttack();
                        if (myTP >= 4) executeDefensive();
                        return;
                    }
                }
            }
        }

        var positionResult = evaluatePositioning();
        if (positionResult == "position_improved") {
            // Position was improved, now attack from new position
            executeAttack();
            if (myTP >= 4) executeDefensive();
            return;
        }
    }
    
    // PHASE 3: Combat Decisions  
    // Attack commitment, kill setup, combat strategies

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var combatAction = makeCombatDecision();
    
    if (combatAction != null) {
        // Combat action was taken
        return;
    }
    
    // PHASE 4: Fallback Logic
    // Final positioning and attack attempts
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

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

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

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

            var moved = false;

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

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