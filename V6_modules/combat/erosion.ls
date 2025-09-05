// V6 Module: combat/erosion.ls
// Erosion damage tracking
// Auto-generated from V5.0 script

// Function: updateErosion
function updateErosion(damageDealt, wasCritical) {
    if (damageDealt <= 0) return;
    
    var erosionRate = wasCritical ? EROSION_CRITICAL : EROSION_NORMAL;
    var erosion = damageDealt * erosionRate;
    ENEMY_EROSION += erosion;
    
    // Adjust strategy if erosion is significant
    if (ENEMY_EROSION > ENEMY_ORIGINAL_MAX_HP * 0.2) {
        if (debugEnabled) {
            debugLog("🔥 Significant erosion! Enemy lost " + round(ENEMY_EROSION) + " max HP");
        }
        // Be more aggressive - their healing is less effective
        WEIGHT_DAMAGE = min(1.5, WEIGHT_DAMAGE * 1.1);
    }
    
    return erosion;
}

// Evaluate target priority based on erosion potential

// Function: evaluateErosionPotential
function evaluateErosionPotential(target) {
    var targetMaxHP = getTotalLife(target);
    var myCritChance = min(1.0, myAgility / 1000.0);
    
    // High-HP targets benefit more from erosion
    var erosionValue = 0;
    
    if (myCritChance > 0.4) {  // High crit build
        // Prefer tankier targets for erosion
        erosionValue = targetMaxHP * 0.001 * myCritChance;
    }
    
    return erosionValue;
}

// === FIX 20: GRENADE LAUNCHER RANGE OPTIMIZATION ===
// Analyze optimal range for Grenade Launcher effectiveness
