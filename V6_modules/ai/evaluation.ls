// V6 Module: ai/evaluation.ls
// Position evaluation
// Auto-generated from V5.0 script

// Function: evaluateCandidates
function evaluateCandidates(candidates) {
    var bestCell = myCell;
    var bestScore = evaluatePosition(myCell);
    
    for (var i = 0; i < count(candidates); i++) {
        var cell = candidates[i];
        var score = evaluatePosition(cell);
        
        if (score > bestScore) {
            bestScore = score;
            bestCell = cell;
        }
    }
    
    return bestCell;
}


// Function: evaluatePosition
function evaluatePosition(cell) {
    var damage = calculateDamageFrom(cell);
    var eid = eidOf(cell);  // Use cached version
    var myEHP = calculateEHP(myHP, myAbsShield, myRelShield, 0, myResistance);
    var dist = getCellDistance(cell, enemyCell);  // Calculate distance for range checks
    
    // Use influence map data if available for better tactical awareness
    var influenceBonus = 0;
    if (INFLUENCE_TURN == turn) {
        var influence = mapGet(INFLUENCE_MAP, cell, null);
        if (influence != null) {
            // Use influence map data to enhance position evaluation
            influenceBonus += influence["control"] * 0.5;  // Territory control value
            influenceBonus += influence["safety"] * 200;   // Safety score bonus
            
            // Bonus for AoE coverage potential
            if (count(influence["myAoE"]) > 0) {
                influenceBonus += count(influence["myAoE"]) * 20;
            }
            
            // Penalty for being in enemy AoE zones
            if (count(influence["enemyAoE"]) > 0) {
                influenceBonus -= count(influence["enemyAoE"]) * 50;
            }
        }
    }
    
    // LIFE STEAL CALCULATION - With 260 wisdom, this is MASSIVE!
    // Life steal is based on ACTUAL damage dealt after enemy shields
    // At 260 wisdom = 26% life steal of actual damage!
    var lifeSteal = calculateLifeSteal(damage, enemy);
    var netDamage = max(0, eid - lifeSteal);  // Net damage after life steal healing
    
    // Calculate threat ratio with life steal considered
    var threatRatio = myEHP > 0 ? netDamage / myEHP : 1.0;
    
    // Base score from damage
    var score = damage * WEIGHT_DAMAGE;
    
    // Add life steal bonus - CONSERVATIVE to prevent suicidal rushes
    // Consider enemy burst damage potential when valuing life steal
    var enemyBurstPotential = eid * 1.5;  // Assume enemy can burst 1.5x avg damage
    var effectiveLifeSteal = lifeSteal;
    
    // If enemy can burst us down, life steal won't save us
    if (enemyBurstPotential >= myHP) {
        effectiveLifeSteal = lifeSteal * 0.2;  // Heavily reduce value if we can be one-shot
    } else if (enemyBurstPotential >= myHP * 0.7) {
        effectiveLifeSteal = lifeSteal * 0.4;  // Reduce value if enemy can nearly kill us
    }
    
    // Cap life steal contribution to max 15% of EHP (reduced from 20%)
    var lifeStealBonus = min(effectiveLifeSteal * 0.4, myEHP * 0.15);  
    score += lifeStealBonus;
    
    if (debugEnabled && lifeStealBonus > 0) {
        debugLog("Life steal bonus: " + round(lifeStealBonus) + " (capped from " + round(lifeSteal) + ")");
    }
    
    // Penalize by NET damage (after life steal), not raw EID
    score -= netDamage * WEIGHT_SAFETY;
    
    // When buffed with agility OR high wisdom, be moderately more aggressive
    // Base AGI is 310, with Warm Up it's 480+ (48% crit!)
    // Base WIS is 260 (26% life steal!)
    if (myAgility > 400) {  // If we have high agility (likely buffed)
        score += damage * 0.3;  // 30% bonus score when crit-buffed (reduced from 50%)
    }
    if (myWisdom > 200 && threatRatio < 0.5) {  // Only be aggressive with lifesteal when somewhat safe
        score += damage * 0.4;  // 40% bonus (reduced from 80%, and only when not in danger)
    }
    
    // Bonus for Electrisor/Lightninger range
    if (dist >= 6 && dist <= 10) {
        score += 100;  // Prefer our optimal attack range
    }
    if (dist == 7) {
        score += 100;  // Long range option
    }
    
    // TACTICAL POSITIONING vs enemy weapons
    if (ENEMY_HAS_BAZOOKA) {
        if (dist <= 3) {
            // Inside Bazooka min range - HUGE bonus!
            score += 500;
        } else if (dist >= 4 && dist <= 7) {
            // Prime Bazooka kill zone - HUGE penalty
            score -= 400;
        } else if (dist == 8 || dist == 9) {
            // Edge of Bazooka range - risky
            score -= 200;
        }
    }
    
    // General min-range exploitation
    if (ENEMY_MIN_RANGE >= 4 && dist < ENEMY_MIN_RANGE) {
        // They can't shoot us - massive bonus!
        score += 300 * (ENEMY_MIN_RANGE - dist);
    }
    
    // Bonus for safe positions when healthy
    if (threatRatio < THREAT_SAFE_RATIO && myHP > myMaxHP * 0.5) {
        score += 100;
    }
    
    // With 26% life steal, we can be much more aggressive
    if (threatRatio > THREAT_HIGH_RATIO) {
        var penalty = 500;
        if (lifeSteal > eid * 0.25) {  // We heal back 26% of damage dealt
            penalty = 100;  // Minimal penalty - we're healing machines!
        } else if (lifeSteal > eid * 0.15) {
            penalty = 250;
        }
        score -= penalty;
    }
    
    // Distance factor - prefer optimal range
    var rangeDiff = abs(dist - optimalAttackRange);
    score -= rangeDiff * 20;  // Penalty for being off optimal range
    
    // With 26% life steal, melee is much safer
    if (dist <= 1 && damage < enemyHP) {
        var penalty = 300;
        // With high life steal, melee becomes viable
        if (lifeSteal > 100) {  // Healing 100+ per turn
            penalty = 50;  // Almost no penalty!
        } else if (lifeSteal > 50) {
            penalty = 100;  
        }
        // Or if we can nearly kill (80%+ of enemy HP)
        if (damage >= enemyHP * 0.8) {
            penalty = 50;
        }
        score -= penalty;
    }
    
    // Bonus for maintaining good range
    if (dist >= optimalAttackRange - 1 && dist <= optimalAttackRange + 1) {
        score += 100;
    }
    
    // Apply influence map bonus
    score += influenceBonus;
    
    return score;
}


// Function: calculateEHP
function calculateEHP(hp, absShield, relShield, armor, resistance) {
    // CORRECTED: Resistance MULTIPLIES shield effectiveness!
    // Shield effectiveness = base_shield * (1 + resistance/100)
    // With 150 resistance: shields are 2.5x effective
    // With 330 resistance (Solidification): shields are 4.3x effective
    
    // Apply resistance multiplier to both shield types
    var resistanceMultiplier = 1 + resistance / 100.0;
    var finalAbsShield = absShield * resistanceMultiplier;
    var finalRelShield = relShield * resistanceMultiplier;
    
    // Cap relative shield at 90% (after resistance boost)
    finalRelShield = min(90, finalRelShield);
    
    // Calculate damage reduction from relative shield
    // Damage formula: FinalDamage = BaseDamage * (1 - RelShield/100) - AbsShield
    var damageMultiplier = max(0.1, 1.0 - finalRelShield / 100.0);
    
    // Calculate effective HP
    // EHP = (HP + AbsoluteShield) / DamageMultiplier
    var effectiveHP = (hp + finalAbsShield) / damageMultiplier;
    
    return floor(effectiveHP);
}

// Helper function to calculate actual shield value with resistance

// Function: calculateEffectiveShieldValue
function calculateEffectiveShieldValue(baseAbsShield, baseRelShield, resistance) {
    // Shield effectiveness = base_shield * (1 + resistance/100)
    var resistanceMultiplier = 1 + resistance / 100.0;
    
    var effectiveAbsShield = baseAbsShield * resistanceMultiplier;
    var effectiveRelShield = min(90, baseRelShield * resistanceMultiplier);
    
    return {
        absShield: effectiveAbsShield,
        relShield: effectiveRelShield,
        totalValue: effectiveAbsShield + (effectiveRelShield * 10)  // Rough HP equivalence
    };
}

// === EID CALCULATION ===
