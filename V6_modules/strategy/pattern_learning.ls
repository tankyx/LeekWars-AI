// V6 Module: strategy/pattern_learning.ls
// Enemy pattern recognition
// Auto-generated from V5.0 script

// Function: initializePatternLearning
function initializePatternLearning() {
    if (!PATTERN_INITIALIZED) {
        ENEMY_PATTERNS["healThreshold"] = [];
        ENEMY_PATTERNS["positionPreference"] = [];
        ENEMY_PATTERNS["weaponSequence"] = [];
        ENEMY_PATTERNS["buffSequence"] = [];
        ENEMY_PATTERNS["retreatThreshold"] = [];
        ENEMY_PATTERNS["aggressionLevel"] = [];
        ENEMY_PATTERNS["averageMP"] = [];
        ENEMY_PATTERNS["turnData"] = [];
        ENEMY_PATTERNS["preferredRange"] = [];
        PATTERN_INITIALIZED = true;
    }
}


// Function: updatePatternLearning
function updatePatternLearning() {
    if (enemy == null) return null;
    
    initializePatternLearning();
    
    var turnInfo = [:];
    turnInfo["turn"] = turn;
    turnInfo["enemyHP"] = enemyHP / enemyMaxHP;
    turnInfo["enemyPos"] = enemyCell;
    turnInfo["enemyQuadrant"] = getQuadrant(enemyCell);
    turnInfo["enemyDistance"] = enemyDistance;
    turnInfo["enemyUsedHeal"] = false;
    turnInfo["enemyUsedBuff"] = false;
    turnInfo["enemyDamageDealt"] = 0;
    turnInfo["enemyMPUsed"] = 0;
    turnInfo["enemyWeapon"] = getWeapon(enemy);
    
    // Detect healing pattern
    if (turn > 1 && enemyLastHP > 0) {
        var expectedHP = enemyLastHP - myLastTurnDamage;
        if (enemyHP > expectedHP + 50) {
            turnInfo["enemyUsedHeal"] = true;
            push(ENEMY_PATTERNS["healThreshold"], enemyLastHP / enemyMaxHP);
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("PATTERN: Enemy healed at " + round((enemyLastHP/enemyMaxHP)*100) + "% HP");
            }
        }
    }


    
    // Track damage dealt to us
    if (turn > 1 && myLastHP > 0) {
        var damageToUs = max(0, myLastHP - myHP);
        turnInfo["enemyDamageDealt"] = damageToUs;
        push(ENEMY_PATTERNS["aggressionLevel"], damageToUs);
    }

    
    // Track movement patterns
    if (turn > 1 && enemyLastCell != -1) {
        var mpUsed = getCellDistance(enemyLastCell, enemyCell);
        turnInfo["enemyMPUsed"] = mpUsed;
        push(ENEMY_PATTERNS["averageMP"], mpUsed);
    }

    
    // Track position preference
    push(ENEMY_PATTERNS["positionPreference"], turnInfo["enemyQuadrant"]);
    
    // Track preferred combat range
    push(ENEMY_PATTERNS["preferredRange"], enemyDistance);
    
    // Track weapon usage
    if (turnInfo["enemyWeapon"] != null) {
        push(ENEMY_PATTERNS["weaponSequence"], turnInfo["enemyWeapon"]);
    }

    
    // Store turn data
    push(ENEMY_PATTERNS["turnData"], turnInfo);
    
    // Update tracking variables for next turn
    enemyLastHP = enemyHP;
    enemyLastCell = enemyCell;
    myLastHP = myHP;
    
    // Make predictions after 3 turns
    if (turn >= 3) {
        return predictEnemyBehavior();
    }

    return null;
}



// Function: predictEnemyBehavior
function predictEnemyBehavior() {
    var predictions = [:];
    predictions["willHeal"] = false;
    predictions["preferredQuadrant"] = null;
    predictions["likelyRetreat"] = false;
    predictions["expectedAggression"] = "NORMAL";
    predictions["preferredRange"] = 7;
    
    // Predict healing
    if (count(ENEMY_PATTERNS["healThreshold"]) > 0) {
        var avgHealThreshold = arrayFoldLeft(ENEMY_PATTERNS["healThreshold"], 
            function(acc, val) { return acc + val; }, 0) / count(ENEMY_PATTERNS["healThreshold"]);
        
        if (enemyHP / enemyMaxHP <= avgHealThreshold + 0.05) {
            predictions["willHeal"] = true;
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("PATTERN: Enemy likely to heal (usually at " + round(avgHealThreshold * 100) + "% HP)");
            }
        }
    }


    
    // Predict positioning
    var quadrantCounts = [:];
    for (var i = 0; i < count(ENEMY_PATTERNS["positionPreference"]); i++) {
        var q = ENEMY_PATTERNS["positionPreference"][i];
        quadrantCounts[q] = mapGet(quadrantCounts, q, 0) + 1;
    }

    
    var maxCount = 0;
    for (var q in quadrantCounts) {
        if (quadrantCounts[q] > maxCount) {
            maxCount = quadrantCounts[q];
            predictions["preferredQuadrant"] = q;
        }
    }


    
    // Predict aggression level
    if (count(ENEMY_PATTERNS["aggressionLevel"]) > 0) {
        var avgDamage = arrayFoldLeft(ENEMY_PATTERNS["aggressionLevel"],
            function(acc, val) { return acc + val; }, 0) / count(ENEMY_PATTERNS["aggressionLevel"]);
        
        if (avgDamage > 300) {
            predictions["expectedAggression"] = "HIGH";
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("PATTERN: High aggression enemy (avg " + round(avgDamage) + " damage/turn)");
            }
        } else if (avgDamage < 150) {
            predictions["expectedAggression"] = "LOW";
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("PATTERN: Low aggression enemy (avg " + round(avgDamage) + " damage/turn)");
            }
        }
    }


    
    // Predict preferred range
    if (count(ENEMY_PATTERNS["preferredRange"]) > 0) {
        var avgRange = arrayFoldLeft(ENEMY_PATTERNS["preferredRange"],
            function(acc, val) { return acc + val; }, 0) / count(ENEMY_PATTERNS["preferredRange"]);
        predictions["preferredRange"] = round(avgRange);
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("PATTERN: Enemy prefers range " + predictions["preferredRange"]);
        }
    }

    
    // Predict retreat behavior
    if (count(ENEMY_PATTERNS["turnData"]) >= 2) {
        var retreats = 0;
        for (var i = 1; i < count(ENEMY_PATTERNS["turnData"]); i++) {
            var prevData = ENEMY_PATTERNS["turnData"][i-1];
            var currData = ENEMY_PATTERNS["turnData"][i];
            // Check if enemy moved away when low HP
            if (prevData["enemyHP"] < 0.3 && currData["enemyDistance"] > prevData["enemyDistance"]) {
                retreats++;
            }
        }


        if (retreats > 0 && enemyHP / enemyMaxHP < 0.3) {
            predictions["likelyRetreat"] = true;
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("PATTERN: Enemy likely to retreat when low HP");
            }
        }
    }


    
    return predictions;
}



// Function: getQuadrant
function getQuadrant(cell) {
    if (cell == null || cell == -1) return "UNKNOWN";
    
    var x = getCellX(cell);
    var y = getCellY(cell);
    var centerX = 17;  // Map center (assuming 35x35 map)
    var centerY = 17;
    
    if (x >= centerX && y >= centerY) return "NE";
    if (x < centerX && y >= centerY) return "NW";
    if (x >= centerX && y < centerY) return "SE";
    return "SW";
}



// Function: applyPatternPredictions
function applyPatternPredictions(predictions) {
    if (predictions == null) return;
    
    // Adjust strategy based on predictions
    if (predictions["willHeal"]) {
        // Enemy about to heal - increase aggression
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Adjusting for predicted heal - increasing damage weight");
        }
        WEIGHT_DAMAGE = WEIGHT_DAMAGE * 1.5;
        WEIGHT_SAFETY = WEIGHT_SAFETY * 0.5;
    }

    
    if (predictions["expectedAggression"] == "HIGH") {
        // High aggression enemy - prioritize safety
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Adjusting for high aggression - increasing safety weight");
        }
        WEIGHT_SAFETY = WEIGHT_SAFETY * 1.3;
    } else if (predictions["expectedAggression"] == "LOW") {
        // Low aggression enemy - be more aggressive
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Adjusting for low aggression - increasing damage weight");
        }
        WEIGHT_DAMAGE = WEIGHT_DAMAGE * 1.2;
    }

    
    if (predictions["likelyRetreat"]) {
        // Enemy will retreat - cut off escape routes
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Enemy likely to retreat - adjusting positioning");
        }
        COMBAT_STRATEGY = "RUSH";  // Chase them down
    }

    
    // Adjust optimal range based on enemy preference
    if (predictions["preferredRange"] > 0) {
        // Try to fight outside their comfort zone
        if (predictions["preferredRange"] <= 5) {
            optimalAttackRange = max(6, optimalAttackRange);  // Stay at range
        } else {
            optimalAttackRange = min(4, optimalAttackRange);  // Get close
        }
    }
}




// === ENSEMBLE DECISION SYSTEM ===

// Function: predictEnemyResponse
function predictEnemyResponse(baitCell) {
    // Based on pattern learning, predict where enemy will move
    // to exploit our "weakness"
    
    if (enemy == null) return -1;
    
    var predictedCell = -1;
    var maxThreat = 0;
    
    // Enemy will likely move to maximize damage while staying safe
    var enemyReachable = getEnemyReachable(enemyCell, getMP(enemy));
    
    if (enemyReachable == null || count(enemyReachable) == 0) {
        return enemyCell;  // Enemy stays put
    }

    
    for (var i = 0; i < min(30, count(enemyReachable)); i++) {
        var cell = enemyReachable[i];
        
        // Estimate damage enemy can deal from this position
        var damage = calculateEnemyDamageFrom(cell, baitCell);
        
        // Factor in enemy's safety at this position
        var enemySafety = 1.0;
        if (lineOfSight(baitCell, cell, enemy)) {
            var counterDamage = calculateDamageFromTo(baitCell, cell);
            enemySafety = enemyHP > 0 ? max(0.1, 1 - counterDamage / enemyHP) : 0.1;
        }

        
        // Enemy likely picks high damage with reasonable safety
        var score = damage * enemySafety;
        
        if (score > maxThreat) {
            maxThreat = score;
            predictedCell = cell;
        }
    }


    
    return predictedCell;
}


