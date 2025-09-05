// V6 Module: strategy/ensemble_system.ls
// Ensemble decision making
// Auto-generated from V5.0 script

// Function: initializeEnsemble
function initializeEnsemble() {
    if (!ENSEMBLE_INITIALIZED) {
        ENSEMBLE_STRATEGIES["aggressive"] = [:];
        ENSEMBLE_STRATEGIES["aggressive"]["weight"] = 0.3;
        ENSEMBLE_STRATEGIES["aggressive"]["function"] = evaluateAggressive;
        
        ENSEMBLE_STRATEGIES["defensive"] = [:];
        ENSEMBLE_STRATEGIES["defensive"]["weight"] = 0.3;
        ENSEMBLE_STRATEGIES["defensive"]["function"] = evaluateDefensive;
        
        ENSEMBLE_STRATEGIES["balanced"] = [:];
        ENSEMBLE_STRATEGIES["balanced"]["weight"] = 0.4;
        ENSEMBLE_STRATEGIES["balanced"]["function"] = evaluateBalanced;
        
        ENSEMBLE_INITIALIZED = true;
    }
}


// Function: ensembleDecision
function ensembleDecision() {
    initializeEnsemble();
    
    var votes = [:];
    var explanations = [];
    var totalWeight = 0;
    
    // Collect votes from each strategy
    for (var name in ENSEMBLE_STRATEGIES) {
        var strategy = ENSEMBLE_STRATEGIES[name];
        if (strategy == null || strategy["function"] == null) continue;
        
        var result = strategy["function"]();
        
        if (result == null) continue;
        
        var voteWeight = strategy["weight"] * result["confidence"];
        var action = result["action"];
        
        if (!mapGet(votes, action, false)) {
            votes[action] = 0;
        }
        votes[action] += voteWeight;
        totalWeight += voteWeight;
        
        push(explanations, name + " suggests " + action + 
             " (conf: " + round(result["confidence"] * 100) + "%)");
    }
    
    // Find winning action
    var bestAction = null;
    var bestVotes = 0;
    
    for (var action in votes) {
        if (votes[action] > bestVotes) {
            bestVotes = votes[action];
            bestAction = action;
        }
    }
    
    // Log ensemble decision
    if (count(explanations) > 0 && turn <= 5) {
        // Join explanations manually (LeekScript may not have arrayJoin)
        var explainText = "";
        for (var i = 0; i < count(explanations); i++) {
            if (i > 0) explainText += ", ";
            explainText += explanations[i];
        }
        debugLog("Ensemble: " + explainText);
        
        if (bestAction != null && totalWeight > 0) {
            var support = round(bestVotes / totalWeight * 100);
            debugLog("Decision: " + bestAction + " with " + support + "% support");
        }
    }
    
    return bestAction;
}

// Lightweight ensemble for EFFICIENT mode - fewer strategies

// Function: ensembleDecisionLight
function ensembleDecisionLight() {
    var myDamage = calculateDamageFrom(myCell);
    var enemyEID = calculateEID(myCell);
    
    // Simple two-strategy vote
    var aggressiveVote = 0;
    var defensiveVote = 0;
    
    // Quick aggressive evaluation
    if (myDamage > enemyHP * 0.4) {
        aggressiveVote = 0.8;
    } else if (myDamage > enemyHP * 0.25) {
        aggressiveVote = 0.5;
    } else {
        aggressiveVote = 0.2;
    }
    
    // Quick defensive evaluation  
    if (enemyEID > myHP * 0.6) {
        defensiveVote = 0.9;
    } else if (enemyEID > myHP * 0.4) {
        defensiveVote = 0.5;
    } else {
        defensiveVote = 0.2;
    }
    
    // Determine action based on votes
    if (aggressiveVote > defensiveVote) {
        if (myDamage >= enemyHP) {
            return "KILLSHOT";
        } else if (enemyDistance <= 7) {
            return "ATTACK";
        } else {
            return "APPROACH";
        }
    } else {
        if (enemyEID >= myHP) {
            return "ESCAPE";
        } else if (enemyDistance <= 5) {
            return "KITE";
        } else {
            return "POSITION";
        }
    }
}

// Quick tactical decision for SURVIVAL mode

// Function: evaluateAggressive
function evaluateAggressive() {
    var result = [:];
    var confidence = 0.5;  // Base confidence
    
    // Aggressive strategy focuses on maximizing damage
    var myDamage = calculateDamageFrom(myCell);
    var enemyEID = calculateEID(myCell);
    var pkill = calculatePkill(enemyHP, myTP);
    
    // High confidence if we can deal significant damage
    if (myDamage > enemyHP * 0.5) {
        confidence = 0.9;
        result["action"] = "ATTACK";
    } else if (pkill >= 0.7) {
        confidence = 0.85;
        result["action"] = "COMMIT";
    } else if (myDamage > enemyHP * 0.3 && enemyEID < myHP * 0.5) {
        confidence = 0.7;
        result["action"] = "ATTACK";
    } else if (enemyDistance > 10) {
        confidence = 0.6;
        result["action"] = "APPROACH";
    } else {
        confidence = 0.4;
        result["action"] = "POSITION";
    }
    
    // Boost confidence if enemy is low HP
    if (enemyHP < enemyMaxHP * 0.3) {
        confidence = min(1.0, confidence + 0.2);
        result["action"] = "COMMIT";  // Override to commit
    }
    
    result["confidence"] = confidence;
    return result;
}


// Function: evaluateDefensive
function evaluateDefensive() {
    var result = [:];
    var confidence = 0.5;
    
    // Defensive strategy focuses on survival
    var myEHP = calculateEHP(myHP, myAbsShield, myRelShield, 0, myResistance);
    var enemyEID = calculateEID(myCell);
    var threatRatio = myEHP > 0 ? enemyEID / myEHP : 1.0;
    
    // High confidence if we're in danger
    if (threatRatio >= 0.7) {
        confidence = 0.95;
        result["action"] = "RETREAT";
    } else if (threatRatio >= 0.5) {
        confidence = 0.8;
        result["action"] = "DEFEND";
    } else if (myHP < myMaxHP * 0.3) {
        confidence = 0.85;
        result["action"] = "HEAL";
    } else if (myHP < myMaxHP * 0.5 && threatRatio >= 0.3) {
        confidence = 0.7;
        result["action"] = "KITE";
    } else if (enemyDistance <= 3) {
        confidence = 0.6;
        result["action"] = "KITE";
    } else {
        confidence = 0.4;
        result["action"] = "POSITION";
    }
    
    // Boost confidence if we have good shields available
    if (myTP >= 6 && getCooldown(CHIP_FORTRESS) == 0) {
        confidence = min(1.0, confidence + 0.1);
    }
    
    result["confidence"] = confidence;
    return result;
}


// Function: evaluateBalanced
function evaluateBalanced() {
    var result = [:];
    var confidence = 0.5;
    
    // Balanced strategy considers both offense and defense
    var myEHP = calculateEHP(myHP, myAbsShield, myRelShield, 0, myResistance);
    var enemyEHP = calculateEHP(enemyHP, getAbsoluteShield(enemy), getRelativeShield(enemy), 0, getResistance(enemy));
    var myDamage = calculateDamageFrom(myCell);
    var enemyEID = calculateEID(myCell);
    var pkill = calculatePkill(enemyHP, myTP);
    
    // Calculate advantage ratio
    var offenseRatio = myDamage > 0 ? myDamage / max(1, enemyEHP) : 0;
    var defenseRatio = enemyEID > 0 ? myEHP / max(1, enemyEID) : 999;
    var advantageRatio = offenseRatio * defenseRatio;
    
    if (pkill >= 0.8) {
        confidence = 0.9;
        result["action"] = "COMMIT";
    } else if (advantageRatio >= 2.0) {
        confidence = 0.8;
        result["action"] = "ATTACK";
    } else if (advantageRatio >= 1.0 && enemyDistance <= optimalAttackRange) {
        confidence = 0.7;
        result["action"] = "ATTACK";
    } else if (advantageRatio < 0.5) {
        confidence = 0.75;
        result["action"] = "DEFEND";
    } else if (enemyDistance > optimalAttackRange + 2) {
        confidence = 0.6;
        result["action"] = "APPROACH";
    } else if (enemyDistance < optimalAttackRange - 2) {
        confidence = 0.6;
        result["action"] = "KITE";
    } else {
        confidence = 0.5;
        result["action"] = "POSITION";
    }
    
    // Adjust for turn number
    if (turn <= 2) {
        // Early game - be more aggressive to establish position
        if (result["action"] == "DEFEND") {
            result["action"] = "POSITION";
            confidence *= 0.8;
        }
    } else if (turn >= 50) {
        // Late game - consider time pressure
        if (myHP > enemyHP) {
            result["action"] = "ATTACK";
            confidence = min(1.0, confidence + 0.15);
        }
    }
    
    result["confidence"] = confidence;
    return result;
}


// Function: executeEnsembleAction
function executeEnsembleAction(action) {
    if (action == null) {
        debugLog("No ensemble action - using default behavior");
        executeAttack();
        return;
    }
    
    debugLog("Executing ensemble action: " + action);
    
    if (action == "ATTACK" || action == "COMMIT") {
        executeAttack();
        if (myTP >= 3) executeDefensive();
    } else if (action == "DEFEND" || action == "HEAL") {
        executeDefensive();
        if (myTP >= 4) executeAttack();
    } else if (action == "RETREAT") {
        // Move away from enemy
        var retreatCells = getReachableCells(myCell, myMP);
        var bestRetreat = myCell;
        var bestDist = enemyDistance;
        
        for (var i = 0; i < min(20, count(retreatCells)); i++) {
            var cell = retreatCells[i];
            var dist = getCellDistance(cell, enemyCell);
            if (dist > bestDist) {
                bestDist = dist;
                bestRetreat = cell;
            }
        }
        
        if (bestRetreat != myCell) {
            moveToCell(bestRetreat);
            enemyDistance = getCellDistance(myCell, enemyCell);
        }
        executeDefensive();
    } else if (action == "KITE") {
        // Move to optimal range and attack
        var targetRange = optimalAttackRange;
        var kiteCells = getReachableCells(myCell, myMP);
        var bestKite = myCell;
        var bestScore = -999999;
        
        for (var i = 0; i < min(20, count(kiteCells)); i++) {
            var cell = kiteCells[i];
            var dist = getCellDistance(cell, enemyCell);
            var score = -abs(dist - targetRange) * 100;
            if (hasLOS(cell, enemyCell)) score += 50;
            
            if (score > bestScore) {
                bestScore = score;
                bestKite = cell;
            }
        }
        
        if (bestKite != myCell) {
            moveToCell(bestKite);
            enemyDistance = getCellDistance(myCell, enemyCell);
        }
        executeAttack();
    } else if (action == "APPROACH") {
        var step = bestApproachStep(enemyCell);
        if (step != myCell) {
            moveToCell(step);
            enemyDistance = getCellDistance(myCell, enemyCell);
        }
        executeAttack();
    } else if (action == "POSITION") {
        // Find optimal position
        var candidates = getReachableCells(myCell, myMP);
        var bestPos = evaluateCandidates(candidates);
        if (bestPos != myCell) {
            moveToCell(bestPos);
            enemyDistance = getCellDistance(myCell, enemyCell);
        }
        executeAttack();
    }
}

// === DAMAGE CALCULATION ===
