// V6 Module: strategy/bait_tactics.ls
// Bait and trap tactics
// Auto-generated from V5.0 script

// Function: executeBaitTactic
function executeBaitTactic() {
    // Don't bait too often
    if (turn - LAST_BAIT_TURN < 3) {
        return null;
    }
    
    // Find best bait position
    var candidates = getReachableCells(myCell, myMP);
    var bestBait = null;
    var bestScore = -999999;
    
    // OPTIMIZATION: Limit operations by checking fewer candidates
    var maxCandidates = 15;  // Reduced from 30
    if (getOperationLevel() != "OPTIMAL") {
        maxCandidates = 8;  // Even fewer if ops are tight
    }
    
    for (var i = 0; i < min(maxCandidates, count(candidates)); i++) {
        var bait = evaluateBaitPosition(candidates[i]);
        
        if (bait["worthRisk"]) {
            // Score based on trap potential vs risk
            var score = bait["trapPotential"] * 3 - bait["apparentWeakness"] * 2;
            
            // Bonus for positions that look especially tempting
            if (bait["apparentWeakness"] > 0.6 && bait["apparentWeakness"] < 0.75) {
                score += 0.5;  // Sweet spot of vulnerability
            }
            
            // Consider success rate history
            if (BAIT_SUCCESS_RATE > 0.5) {
                score *= 1.2;  // Enemy has fallen for baits before
            }
            
            if (score > bestScore) {
                bestScore = score;
                bestBait = bait;
            }
        }
    }
    
    if (bestBait != null) {
        debugLog("BAIT TACTIC: Moving to cell " + bestBait["cell"]);
        debugLog("  Apparent weakness: " + round(bestBait["apparentWeakness"] * 100) + "%");
        debugLog("  Trap potential: " + round(bestBait["trapPotential"] * 100) + "%");
        
        var baitRecord = [:];
        baitRecord["turn"] = turn;
        baitRecord["cell"] = bestBait["cell"];
        baitRecord["prediction"] = predictEnemyResponse(bestBait["cell"]);
        baitRecord["enemyStartCell"] = enemyCell;
        push(BAIT_HISTORY, baitRecord);
        
        LAST_BAIT_TURN = turn;
        return bestBait["cell"];
    }
    
    return null;
}


// Function: evaluateBaitPosition
function evaluateBaitPosition(cell) {
    var bait = [:];
    bait["cell"] = cell;
    bait["apparentWeakness"] = 0;
    bait["actualStrength"] = 0;
    bait["trapPotential"] = 0;
    bait["worthRisk"] = false;
    
    // Calculate apparent weakness (what enemy sees)
    var eid = calculateEID(cell);
    var myEHP = calculateEHP(myHP, myAbsShield, myRelShield, 0, myResistance);
    var threatRatio = myEHP > 0 ? eid / myEHP : 1.0;
    
    // Good bait appears vulnerable but not obviously suicidal
    if (threatRatio > 0.5 && threatRatio < 0.85) {
        bait["apparentWeakness"] = threatRatio;
        
        // Calculate actual strength (what we know)
        // Factor in healing, shields we'll apply, life steal
        var nextTurnHealing = 0;
        var myEffects = getEffects(getEntity());
        if (myEffects != null) {
            for (var i = 0; i < count(myEffects); i++) {
                if (myEffects[i][0] == EFFECT_HEAL) {
                    // Healing over time effect
                    nextTurnHealing += (myEffects[i][1] + myEffects[i][2]) / 2;
                }
            }
        }
        
        var projectedHP = myHP + nextTurnHealing;
        
        // Factor in life steal from damage we'll deal
        var damageFromBait = calculateDamageFrom(cell);
        var lifeStealNext = floor(damageFromBait * myWisdom / 1000.0);
        projectedHP += lifeStealNext;
        
        // Factor in shields we can apply next turn
        if (myTP >= 5) {
            projectedHP += 100;  // Approximate shield value
        }
        
        bait["actualStrength"] = enemyHP > 0 ? projectedHP / enemyHP : 0;
        
        // Calculate trap potential
        // Can we kill enemy if they take the bait?
        var enemyLikelyPosition = predictEnemyResponse(cell);
        if (enemyLikelyPosition != null && enemyLikelyPosition != -1) {
            // Damage we can deal from bait position
            var counterDamage = calculateDamageFromTo(cell, enemyLikelyPosition);
            
            // Factor in AoE splash damage opportunities
            if (inArray(getWeapons(), WEAPON_GRENADE_LAUNCHER)) {
                counterDamage *= 1.2;  // AoE bonus
            }
            
            bait["trapPotential"] = enemyHP > 0 ? counterDamage / enemyHP : 0;
        }
        
        // Is it worth the risk?
        // Consider game phase and health states
        var riskTolerance = 0.5;  // Base risk tolerance
        
        if (GAME_PHASE == "ENDGAME") {
            riskTolerance = 0.3;  // More willing to take risks
        } else if (GAME_PHASE == "OPENING") {
            riskTolerance = 0.7;  // Less willing early game
        }
        
        bait["worthRisk"] = bait["trapPotential"] > 0.7 && 
                           bait["actualStrength"] > riskTolerance &&
                           bait["apparentWeakness"] < 0.8;
    }
    
    return bait;
}


// Function: updateBaitSuccess
function updateBaitSuccess() {
    // Check if our bait worked last turn
    if (count(BAIT_HISTORY) > 0) {
        var lastBait = BAIT_HISTORY[count(BAIT_HISTORY) - 1];
        
        if (lastBait["turn"] == turn - 1) {
            // Check if enemy moved as predicted (within 2 cells)
            var predictionAccuracy = getCellDistance(enemyCell, lastBait["prediction"]);
            
            if (predictionAccuracy <= 2) {
                debugLog("BAIT SUCCESS! Enemy moved close to prediction (off by " + predictionAccuracy + " cells)");
                
                // Update success rate
                var successes = BAIT_SUCCESS_RATE * max(1, count(BAIT_HISTORY) - 1) + 1;
                BAIT_SUCCESS_RATE = successes / count(BAIT_HISTORY);
                
                // Bonus: Did we get a good attack opportunity?
                if (enemyDistance <= 7 && lineOfSight(myCell, enemyCell, enemy)) {
                    debugLog("  Perfect! Enemy in kill range!");
                }
            } else {
                debugLog("Bait failed - enemy didn't take it (off by " + predictionAccuracy + " cells)");
                
                var successes = BAIT_SUCCESS_RATE * max(1, count(BAIT_HISTORY) - 1);
                BAIT_SUCCESS_RATE = successes / count(BAIT_HISTORY);
            }
            
            debugLog("Bait success rate: " + round(BAIT_SUCCESS_RATE * 100) + "%");
        }
    }
}

// Check if we should try a bait tactic

// Function: shouldUseBaitTactic
function shouldUseBaitTactic() {
    // Don't bait in certain situations
    if (GAME_PHASE == "ENDGAME") {
        return false;  // Too risky when low HP
    }
    
    if (myHP < myMaxHP * 0.4) {
        return false;  // Too damaged
    }
    
    if (enemy == null || enemyHP < enemyMaxHP * 0.3) {
        return false;  // Enemy too weak to need baiting
    }
    
    if (BAIT_SUCCESS_RATE > 0 && BAIT_SUCCESS_RATE < 0.2) {
        return false;  // Enemy doesn't fall for baits
    }
    
    // Good situations for baiting
    if (GAME_PHASE == "MID_GAME" && enemyHP > myHP) {
        return true;  // Need tactical advantage
    }
    
    if (hasState(STATE_ENEMY_BUFFED) && !hasState(STATE_PKILL_READY)) {
        return true;  // Enemy is strong, need to outsmart them
    }
    
    // Random chance based on success rate
    var chance = 0.15;  // Base 15% chance
    if (BAIT_SUCCESS_RATE > 0.5) {
        chance = 0.25;  // Higher if it's been working
    }
    
    return rand() < chance;
}

// === EROSION TRACKING SYSTEM ===
// Track cumulative erosion damage to adjust strategy
