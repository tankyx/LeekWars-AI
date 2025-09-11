// V6 Module: combat/weapon_management.ls
// Weapon usage and switching
// Auto-generated from V5.0 script

// Function: tryUseWeapon
function tryUseWeapon(target) {
    var w = getWeapon();
    if (w == null || !canUseWeapon(w, target)) return false;
    
    var cost = getWeaponCost(w);
    if (cost > myTP) return false;
    
    var result = useWeaponOnCell(getCell(target));
    
    // Check for explicit success or critical
    if (result == USE_SUCCESS || result == USE_CRITICAL) {
        myTP -= cost;
        var critText = (result == USE_CRITICAL) ? " (CRIT!)" : "";
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Used weapon " + getWeaponName(w) + " for " + cost + " TP" + critText);
        }
        return true;
    }
    return false;
}

// Function: setWeaponIfNeeded
function setWeaponIfNeeded(weapon) {
    if (getWeapon() != weapon) {
        setWeapon(weapon);
        myTP = getTP();  // Update TP after weapon switch (costs 1 TP)
    }
}

// === MOVEMENT ===

// Function: weaponNeedLos
function weaponNeedLos(weapon) {
    // All our current weapons need LOS
    return true;
}

// Function: getWeaponDamage
function getWeaponDamage(weapon, leek) {
    var effects = getWeaponEffects(weapon);
    var strength = getStrength(leek);
    var agility = getAgility(leek);
    
    // Standard weapon damage with crit consideration
    for (var i = 0; i < count(effects); i++) {
        if (effects[i][0] == EFFECT_DAMAGE) {
            var avg = (effects[i][1] + effects[i][2]) / 2;
            var baseDmg = avg * (1 + strength / 100.0);
            var critChance = min(1.0, agility / 1000.0);  // AGI/1000 = crit rate
            var expectedDmg = baseDmg * (1 + critChance * CRITICAL_FACTOR);  // 30% more on crit
            return expectedDmg;
        }
    }
    return 0;
}