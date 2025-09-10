// V6 Module: strategy/kill_calculations.ls
// Kill probability calculations
// Auto-generated from V5.0 script

// Function: calculatePkill
function calculatePkill(targetHP, availableTP) {
    var minD = 0;
    var maxD = 0;
    var tp = availableTP;
    var weapons = getWeapons();
    
    // Check range and LOS for weapons
    var dist = getCellDistance(myCell, enemyCell);
    var hasLos = hasLOS(myCell, enemyCell);

    // Sort weapons by DPTP (3x faster with fold!)
    var wlist = arrayFoldLeft(weapons, function(acc, w) {
        var cost = getWeaponCost(w);
        if (cost <= 0) return acc;
        
        // Check range and LOS requirements
        if (dist < getWeaponMinRange(w) || dist > getWeaponMaxRange(w)) return acc;
        if (weaponNeedLos(w) && !hasLos) return acc;
        
        var dptp = getWeaponDamage(w, getEntity()) / cost;
        push(acc, [-dptp, w]);
        return acc;
    }, []);
    sort(wlist);
    
    // Process weapons (optimized with fold)
    var damageData = arrayFoldLeft(wlist, function(acc, item) {
        var w = item[1];
        if (!canUseWeapon(w, enemy)) return acc;
        
        var cost = getWeaponCost(w);
        var uses = min(floor(acc.tp/cost), (getWeaponMaxUses(w) > 0 ? getWeaponMaxUses(w) : 99));
        if (uses <= 0) return acc;

        var effects = getWeaponEffects(w);
        for (var e = 0; e < count(effects); e++) {
            if (effects[e][0] == EFFECT_DAMAGE) {
                var mn = effects[e][1] * (1 + myStrength/100.0);
                var mx = effects[e][2] * (1 + myStrength/100.0);
                acc.minD += uses * mn;
                acc.maxD += uses * mx;
                acc.tp -= uses * cost;
                break;
            }
        }
        return acc;
    }, {minD: minD, maxD: maxD, tp: tp});
    
    minD = damageData.minD;
    maxD = damageData.maxD;
    tp = damageData.tp;
    
    // Add damage chips
    var chips = getChips();
    for (var i = 0; i < count(chips); i++) {
        var ch = chips[i];
        if (!chipHasDamage(ch)) continue;
        
        var cost = getChipCost(ch);
        if (cost <= 0) continue;
        
        var uses = min(floor(tp/cost), (getChipMaxUses(ch) > 0 ? getChipMaxUses(ch) : 99));
        if (uses <= 0) continue;
        
        // Check cooldown
        if (getCooldown(ch) > 0) continue;
        
        // Check range and LOS from current position (dist already declared above)
        if (dist < getChipMinRange(ch) || dist > getChipMaxRange(ch)) continue;
        if (chipNeedLos(ch) && !hasLos) continue;  // Use hasLos already computed above
        
        var eff = getChipEffects(ch);
        for (var e = 0; e < count(eff); e++) {
            if (eff[e][0] == EFFECT_DAMAGE) {
                var mn = eff[e][1] * (1 + myStrength/100.0);
                var mx = eff[e][2] * (1 + myStrength/100.0);
                minD += uses * mn;
                maxD += uses * mx;
                tp -= uses * cost;
                break;
            }
        }
    }

    // Apply enemy mitigation (resistance only affects shields, not damage reduction)
    var rel = max(0, getRelativeShield(enemy)) / 100.0;
    var mult = max(0.01, (1 - rel));  // Only relative shield reduces damage
    minD *= mult;
    maxD *= mult;

    if (maxD < targetHP) return 0;
    if (minD >= targetHP) return 1;
    return (maxD - targetHP) / max(1, (maxD - minD));
}

// FIX: canSetupKill to be EV-based

// Function: canSetupKill
function canSetupKill() {
    // Calculate damage this turn
    var evNow = calculateDamageFrom(myCell);
    var hpNext = enemyHP - evNow;
    
    // Estimate next turn damage
    var evNext = estimateNextTurnEV();
    
    return hpNext <= evNext;
}

// Estimate next turn expected value

// Function: estimateNextTurnEV
function estimateNextTurnEV() {
    var nextTP = getTotalTP();
    var bestDamage = 0;
    
    // Check from current position
    bestDamage = calculateDamageFromWithTP(myCell, nextTP);
    
    // Check nearby cells (1 move)
    if (!canSpendOps(100)) {
        return bestDamage;
    }
    
    var neighbors = [
        getCellFromXY(getCellX(myCell)+1, getCellY(myCell)),
        getCellFromXY(getCellX(myCell)-1, getCellY(myCell)),
        getCellFromXY(getCellX(myCell), getCellY(myCell)+1),
        getCellFromXY(getCellX(myCell), getCellY(myCell)-1)
    ];
    
    for (var i = 0; i < count(neighbors); i++) {
        var n = neighbors[i];
        if (n != -1 && !isObstacle(n) && n != enemyCell) {
            var damage = calculateDamageFromWithTP(n, nextTP);
            if (damage > bestDamage) {
                bestDamage = damage;
            }
        }
    }
    
    return bestDamage;
}

