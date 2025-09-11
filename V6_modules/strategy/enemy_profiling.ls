// V6 Module: strategy/enemy_profiling.ls
// Enemy analysis and strategy selection
// Auto-generated from V5.0 script

// Function: profileEnemy
function profileEnemy() {
    if (enemy == null) return;
    
    var maxStat = max(enemyStrength, max(enemyMagic, max(enemyAgility, enemyScience)));
    var enemyResistance = getResistance(enemy);
    
    // Classify enemy based on their primary stat
    if (enemyMaxHP > 4500) {
        ENEMY_TYPE = "TANK";
    } else if (enemyStrength == maxStat && enemyStrength > 500) {
        ENEMY_TYPE = "STR";
    } else if (enemyMagic == maxStat && enemyMagic > 500) {
        ENEMY_TYPE = "MAG";
    } else if (enemyAgility == maxStat && enemyAgility > 500) {
        ENEMY_TYPE = "AGI";
    } else if (enemyScience == maxStat && enemyScience > 500) {
        ENEMY_TYPE = "WIS";
    } else if (enemyResistance > 500) {
        ENEMY_TYPE = "DEFENSIVE";
    } else {
        ENEMY_TYPE = "BALANCED";
    }
    
    if (debugEnabled && canSpendOps(1000)) {
		debugLog("Enemy Profile: " + ENEMY_TYPE + " (STR:" + enemyStrength + " MAG:" + enemyMagic + " AGI:" + enemyAgility + ")");
    }
}

// Function: selectCombatStrategy
function selectCombatStrategy() {
    // WIS-TANK BUILD: Adjust strategies based on our sustain focus
    if (ENEMY_TYPE == "STR") {
        // vs STR: OUTLAST - Tank their damage with shields and heals
        COMBAT_STRATEGY = "OUTLAST";
        optimalAttackRange = 8;  // Stay at safe distance
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Strategy: OUTLAST - Tank and sustain vs high STR enemy");
        }
    } else if (ENEMY_TYPE == "MAG") {
        // vs MAG: PRESSURE - Get in their face to disrupt
        COMBAT_STRATEGY = "PRESSURE";
        optimalAttackRange = 4;
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Strategy: PRESSURE - Close combat vs magic user");
        }
    } else if (ENEMY_TYPE == "TANK") {
        // vs TANK: ENDURANCE - Long fight, maximize efficiency
        COMBAT_STRATEGY = "ENDURANCE";
        optimalAttackRange = 6;
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Strategy: ENDURANCE - Efficient DPS vs tank");
        }
    } else if (ENEMY_TYPE == "WIS") {
        // vs WIS: SUSTAIN DUEL - Out-sustain them
        COMBAT_STRATEGY = "SUSTAIN";
        optimalAttackRange = 7;
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Strategy: SUSTAIN - Out-heal and outlast vs WIS");
        }
    } else if (ENEMY_TYPE == "DEFENSIVE") {
        // vs DEFENSIVE: SUSTAIN - Consistent pressure
        COMBAT_STRATEGY = "SUSTAIN";
        optimalAttackRange = 6;
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Strategy: SUSTAIN - Consistent damage vs defensive");
        }
    } else {
        // Default: SUSTAIN - Our core strategy
        COMBAT_STRATEGY = "SUSTAIN";
        optimalAttackRange = 7;
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Strategy: SUSTAIN - Tank and outlast");
        }
    }

    if (debugEnabled && canSpendOps(1000)) {
		debugLog("Optimal attack range: " + optimalAttackRange);
    }
    if (debugEnabled && canSpendOps(1000)) {
		debugLog("Enemy weapon ranges: " + ENEMY_MIN_RANGE + "-" + ENEMY_MAX_RANGE + ", max AoE=" + ENEMY_MAX_AOE_SIZE);
    }
}

// Analyze our weapons to find optimal engagement range (3x faster with fold!)
