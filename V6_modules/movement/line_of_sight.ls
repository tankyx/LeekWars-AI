// V6 Module: movement/line_of_sight.ls
// Line of sight checks
// Auto-generated from V5.0 script

// Function: hasLOS
function hasLOS(from, to) {
    var k1 = from + "_" + to;
    var k2 = to + "_" + from;
    var cached = mapGet(CACHE_LOS, k1, null);
    if (cached != null) return cached;
    
    var result = lineOfSight(from, to);
    CACHE_LOS[k1] = result;
    CACHE_LOS[k2] = result; // Both directions
    return result;
}

// === PATTERN LEARNING SYSTEM ===

// Function: canAttackFromPosition
function canAttackFromPosition(cell) {
    if (enemy == null) return false;
    
    var dist = getCellDistance(cell, enemyCell);
    var hasLine = hasLOS(cell, enemyCell);
    
    // Check weapons
    var weapons = getWeapons();
    for (var i = 0; i < count(weapons); i++) {
        var w = weapons[i];
        if (dist >= getWeaponMinRange(w) && dist <= getWeaponMaxRange(w)) {
            if (!weaponNeedLos(w) || hasLine) {
                return true;
            }
        }
    }
    
    // Check damage chips
    var chips = getChips();
    for (var i = 0; i < count(chips); i++) {
        var ch = chips[i];
        if (chipHasDamage(ch) && getCooldown(ch) == 0) {
            if (dist >= getChipMinRange(ch) && dist <= getChipMaxRange(ch)) {
                if (!chipNeedLos(ch) || hasLine) {
                    return true;
                }
            }
        }
    }
    
    return false;
}

