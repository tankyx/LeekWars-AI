// V6 Module: combat/damage_calculation.ls
// Damage calculations
// Auto-generated from V5.0 script

// Function: calculateActualDamage
function calculateActualDamage(baseDamage, target) {
    if (target == null) return baseDamage;
    
    var relShield = getRelativeShield(target);
    var absShield = getAbsoluteShield(target);
    var targetHP = getLife(target);
    
    // Apply relative shield first (percentage reduction)
    var afterRelative = baseDamage * max(0.1, 1 - relShield / 100.0);
    
    // Then subtract absolute shield
    var finalDamage = max(0, afterRelative - absShield);
    
    // Can't deal more damage than target's current HP
    finalDamage = min(finalDamage, targetHP);
    
    return floor(finalDamage);
}

// Calculate life steal based on actual damage dealt

// Function: calculateLifeSteal
function calculateLifeSteal(damage, target) {
    var actualDamage = calculateActualDamage(damage, target);
    var lifeSteal = floor(actualDamage * myWisdom / 1000.0);
    return lifeSteal;
}

// === INFLUENCE MAP SYSTEM ===

// Function: calculateDamageFrom
function calculateDamageFrom(cell) {
    if (enemy == null) return 0;
    
    var dist = getCellDistance(cell, enemyCell);
    
    // Use pre-computed matrix if available
    if (MATRIX_INITIALIZED) {
        return getOptimalDamage(dist, myTP);
    }
    
    // Fallback to manual calculation if matrix not ready
    var totalDamage = 0;
    var tpLeft = myTP;
    
    // Check each weapon
    var weapons = getWeapons();
    for (var i = 0; i < count(weapons); i++) {
        var w = weapons[i];
        
        if (!canUseWeapon(w, enemy)) continue;
        
        // Check if we can hit directly OR through AoE splash
        var canHitDirect = (dist >= getWeaponMinRange(w) && dist <= getWeaponMaxRange(w) && 
                           hasLOS(cell, enemyCell));
        
        // Check for AoE splash opportunities (even without direct LOS!)
        var canHitSplash = false;
        if (!canHitDirect && getWeaponArea(w) > 0) {
            var splashPositions = findAoESplashPositions(w, cell, enemyCell);
            canHitSplash = count(splashPositions) > 0;
        }
        
        if (!canHitDirect && !canHitSplash) continue;
        
        var cost = getWeaponCost(w);
        if (cost > tpLeft) continue;
        
        var uses = floor(tpLeft / cost);
        var maxUses = getWeaponMaxUses(w);
        if (maxUses > 0) uses = min(uses, maxUses);
        
        var damage = uses * getWeaponDamage(w, myLeek);
        totalDamage += damage;
        tpLeft -= uses * cost;
        
        if (tpLeft < 3) break;
    }
    
    // Check damage chips
    var chips = getChips();
    for (var i = 0; i < count(chips); i++) {
        var ch = chips[i];
        
        if (!chipHasDamage(ch)) continue;
        if (!canUseChip(ch, enemy)) continue;
        if (dist < getChipMinRange(ch) || dist > getChipMaxRange(ch)) continue;
        if (chipNeedLos(ch) && !hasLOS(cell, enemyCell)) continue;
        
        var cost = getChipCost(ch);
        if (cost > tpLeft) continue;
        
        var uses = floor(tpLeft / cost);
        var maxUses = getChipMaxUses(ch);
        if (maxUses > 0) uses = min(uses, maxUses);
        
        var damage = uses * getChipDamage(ch, myLeek);
        totalDamage += damage;
        tpLeft -= uses * cost;
        
        if (tpLeft < 3) break;
    }
    
    // Fix 6: Include AoE damage potential
    var aoeDamage = calculateOptimalAoEDamage(cell, dist, tpLeft);
    return max(totalDamage, aoeDamage);  // Use best of direct or AoE
}

// Fix 6: AoE targeting with CORRECT damage falloff formula
// LeekWars AoE formula: damage = baseDamage * max(0, 1 - 0.2 * distance)

// Function: calculateDamageFromTo
function calculateDamageFromTo(fromCell, toCell) {
    // Calculate damage we can deal from one cell to another
    var dist = getCellDistance(fromCell, toCell);
    var totalDamage = 0;
    
    // Use pre-computed weapon matrix if available
    if (MATRIX_INITIALIZED) {
        return getOptimalDamage(dist, myTP);
    }
    
    // Fallback calculation
    var myWeapons = getWeapons();
    if (myWeapons != null) {
        for (var i = 0; i < count(myWeapons); i++) {
            var w = myWeapons[i];
            var minR = getWeaponMinRange(w);
            var maxR = getWeaponMaxRange(w);
            
            if (dist >= minR && dist <= maxR && lineOfSight(fromCell, toCell, enemy)) {
                var effects = getWeaponEffects(w);
                if (effects != null) {
                    for (var j = 0; j < count(effects); j++) {
                        if (effects[j][0] == EFFECT_DAMAGE) {
                            totalDamage += (effects[j][1] + effects[j][2]) / 2;
                            break;
                        }
                    }
                }
            }
        }
    }
    
    return totalDamage * (1 + myStrength / 100.0);
}


// Function: calculateEnemyDamageFrom
function calculateEnemyDamageFrom(fromCell, toCell) {
    // Estimate enemy damage from position
    var dist = getCellDistance(fromCell, toCell);
    var totalDamage = 0;
    
    var enemyWeapons = getWeapons(enemy);
    if (enemyWeapons != null) {
        for (var i = 0; i < count(enemyWeapons); i++) {
            var w = enemyWeapons[i];
            var minR = getWeaponMinRange(w);
            var maxR = getWeaponMaxRange(w);
            
            if (dist >= minR && dist <= maxR) {
                var effects = getWeaponEffects(w);
                if (effects != null) {
                    for (var j = 0; j < count(effects); j++) {
                        if (effects[j][0] == EFFECT_DAMAGE) {
                            totalDamage += (effects[j][1] + effects[j][2]) / 2;
                            break;
                        }
                    }
                }
            }
        }
    }
    
    return totalDamage * (1 + getStrength(enemy) / 100.0);
}


// Function: calculateDamageFromWithTP
function calculateDamageFromWithTP(cell, availableTP) {
    if (enemy == null) return 0;
    
    var dist = getCellDistance(cell, enemyCell);
    var totalDamage = 0;
    var tpLeft = availableTP;
    
    // Check weapons
    var weapons = getWeapons();
    for (var i = 0; i < count(weapons); i++) {
        var w = weapons[i];
        
        if (!canUseWeapon(w, enemy)) continue;
        if (dist < getWeaponMinRange(w) || dist > getWeaponMaxRange(w)) continue;
        
        var cost = getWeaponCost(w);
        if (cost > tpLeft) continue;
        
        var uses = floor(tpLeft / cost);
        var maxUses = getWeaponMaxUses(w);
        if (maxUses > 0) uses = min(uses, maxUses);
        
        var damage = uses * getWeaponDamage(w, myLeek);
        totalDamage += damage;
        tpLeft -= uses * cost;
        
        if (tpLeft < 3) break;
    }
    
    // Check damage chips
    var damageChips = [
        [CHIP_LIGHTNING, 4, 41, 2, 5, true, 3],     // Avg 41 dmg, 4 TP, 3 uses
        [CHIP_BURNING, 5, 82, 4, 6, false, 1],      // Avg 82 base + poison AOE!
        [CHIP_METEORITE, 8, 75, 5, 9, false, 1],    // Avg 75 dmg, 8 TP AOE
        [CHIP_ROCKFALL, 5, 54, 5, 7, false, 1],     // Avg 54 dmg, 5 TP
        [CHIP_ICEBERG, 7, 86, 3, 5, true, 1]        // Avg 86 dmg, 7 TP
    ];
    
    for (var i = 0; i < count(damageChips); i++) {
        if (tpLeft < 4) break;  // Min chip cost is 4
        
        var chipData = damageChips[i];
        var ch = chipData[0];
        var cost = chipData[1];
        var avgDmg = chipData[2];
        var minRange = chipData[3];
        var maxRange = chipData[4];
        var needsLine = chipData[5];
        var maxPerTurn = chipData[6];
        
        if (getCooldown(ch) > 0) continue;
        if (cost > tpLeft) continue;
        if (dist < minRange || dist > maxRange) continue;
        if (needsLine && !hasLOS(cell, enemyCell)) continue;  // Use hasLOS for consistency
        
        var uses = min(floor(tpLeft / cost), maxPerTurn);
        var chipDmg = uses * avgDmg * (1 + myStrength / 100.0);
        totalDamage += chipDmg;
        tpLeft -= uses * cost;
    }
    
    return totalDamage;
}

// === ATTACK ACTIONS ===
// Fix 12: Cache cooldown checks to avoid redundant calls
