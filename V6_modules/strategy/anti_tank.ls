// V6 Module: strategy/anti_tank.ls
// Anti-tank strategy
// Auto-generated from V5.0 script

// Function: useAntiTankStrategy
function useAntiTankStrategy() {
    // Anti-tank strategy using Liberation chip
    if (enemy == null) return false;
    
    if (getCooldown(CHIP_LIBERATION) == 0 && myTP >= 5) {
        var enemyShields = getAbsoluteShield(enemy) + getRelativeShield(enemy);
        var enemyEffects = getEffects(enemy);
        var numEffects = count(enemyEffects);
        var dist = getCellDistance(myCell, enemyCell);
        var hasLine = hasLOS(myCell, enemyCell);
        
        // Use Liberation aggressively against buffed enemies
        // Liberation removes 40% of ALL effects (shields, buffs, everything)
        // Check for high-value buffs like Steroid, Warm Up, Solidification
        var hasHighValueBuff = false;
        for (var i = 0; i < count(enemyEffects); i++) {
            var effectType = enemyEffects[i][0];
            // Check for STR, AGI, RES, or shield buffs
            if (effectType == EFFECT_BUFF_STRENGTH ||
                effectType == EFFECT_BUFF_AGILITY ||
                effectType == EFFECT_BUFF_RESISTANCE ||
                effectType == EFFECT_ABSOLUTE_SHIELD ||
                effectType == EFFECT_RELATIVE_SHIELD) {
                hasHighValueBuff = true;
                break;
            }
        }
        
        // Use Liberation if: shields > 50, or 3+ effects, or any high-value buff
        if (enemyShields > 50 || numEffects >= 3 || hasHighValueBuff) {
            if (dist <= 6 && hasLine) {
                var result = useChip(CHIP_LIBERATION, enemy);
                if (result == USE_SUCCESS || result == USE_CRITICAL) {
                    myTP = getTP();  // Update TP
                    var critText = result == USE_CRITICAL ? " (CRITICAL!)" : "";
                    debugLog("Used Liberation" + critText + "! Stripped " + round(enemyShields * 0.4) + " shields + 40% of " + numEffects + " effects");
                    return true;
                }
            }
        }
    }
    return false;
}

