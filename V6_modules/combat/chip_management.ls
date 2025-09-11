// V6 Module: combat/chip_management.ls
// Chip usage and management
// Auto-generated from V5.0 script

// Function: tryUseChip
function tryUseChip(chip, target) {
    if (!canUseChip(chip, target)) return false;
    
    // Fix 12: Use cached cooldown check
    if (getCachedCooldown(chip) > 0) return false;
    
    var cost = getChipCost(chip);
    if (cost > myTP) return false;
    
    var result = useChipOnCell(chip, getCell(target));
    if (result == USE_SUCCESS || result == USE_CRITICAL) {  // Both indicate successful use
        myTP -= cost;
        var critText = (result == USE_CRITICAL) ? " (CRIT!)" : "";
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Used chip " + getChipName(chip) + " for " + cost + " TP" + critText);
        }
        return true;
    }

    return false;
}



// Function: getCachedCooldown
function getCachedCooldown(chip) {
    if (COOLDOWN_CACHE_TURN != turn) {
        COOLDOWN_CACHE = [:];
        COOLDOWN_CACHE_TURN = turn;
    }
    
    var cached = mapGet(COOLDOWN_CACHE, chip, -999);
    if (cached != -999) return cached;
    
    var cd = getCooldown(chip);
    COOLDOWN_CACHE[chip] = cd;
    return cd;
}



// Function: chipHasDamage
function chipHasDamage(chip) {
    var effects = getChipEffects(chip);
    for (var i = 0; i < count(effects); i++) {
        if (effects[i][0] == EFFECT_DAMAGE) {
            return true;
        }
    }
    return false;
}



// Function: getChipDamage
function getChipDamage(chip, leek) {
    var effects = getChipEffects(chip);
    // Fixed: Use max of all stats since chips can scale with magic/science
    var stat = max(getStrength(leek), max(getMagic(leek), getScience(leek)));
    
    for (var i = 0; i < count(effects); i++) {
        if (effects[i][0] == EFFECT_DAMAGE) {
            var avg = (effects[i][1] + effects[i][2]) / 2;
            return avg * (1 + stat / 100.0);
        }
    }
    return 0;
}



// Function: chipNeedLos
function chipNeedLos(chip) {
    // Most chips need LOS except specific ones
    // You can add exceptions here based on your chip loadout
    return true;
}

// Function to execute buff chips