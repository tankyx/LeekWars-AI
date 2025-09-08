include("../core/globals");
include("../core/operations");

// Calculate actual damage with STR scaling
// FinalDamage = BaseDamage * (1 + Strength / 100)
function calculateDamageWithSTR(baseDamage, strength) {
    return baseDamage * (1 + strength / 100);
}

// Get weapon's average damage
function getWeaponAvgDamage(weapon) {
    if (weapon == WEAPON_RIFLE) return 76;  // (73+79)/2
    if (weapon == WEAPON_DARK_KATANA) return 99;
    if (weapon == WEAPON_M_LASER) return 95;  // (90+100)/2
    if (weapon == WEAPON_GRENADE_LAUNCHER) return 65;  // Approx for single target
    return 0;
}

// Calculate sequence damage with STR
function calculateSequenceDamage(weapons, mySTR) {
    var totalDamage = 0;
    for (var weapon in weapons) {
        var baseDmg = getWeaponAvgDamage(weapon);
        totalDamage += calculateDamageWithSTR(baseDmg, mySTR);
    }
    return totalDamage;
}

// Get best damage sequence for current TP and range
function getBestDamageSequence(availableTP, targetDistance, myHP, mySTR) {
    var sequences = [];
    var equippedWeapons = getWeapons();
    
    // Melee sequences (distance 1)
    if (targetDistance == 1) {
        // Double Dark Katana - 14 TP, self-damage 88
        if (availableTP >= 14 && myHP > 100 && inArray(equippedWeapons, WEAPON_DARK_KATANA)) {
            var dmg = calculateSequenceDamage([WEAPON_DARK_KATANA, WEAPON_DARK_KATANA], mySTR);
            push(sequences, [
                [WEAPON_DARK_KATANA, WEAPON_DARK_KATANA],
                14, dmg, 88, "melee_kill"
            ]);
        }
        // Single Dark Katana - 7 TP, self-damage 44
        if (availableTP >= 7 && myHP > 60 && inArray(equippedWeapons, WEAPON_DARK_KATANA)) {
            var dmg = calculateSequenceDamage([WEAPON_DARK_KATANA], mySTR);
            push(sequences, [
                [WEAPON_DARK_KATANA],
                7, dmg, 44, "melee_burst"
            ]);
        }
    }
    
    // Mid-range sequences (7-9 cells for Rifle)
    if (targetDistance >= 7 && targetDistance <= 9 && inArray(equippedWeapons, WEAPON_RIFLE)) {
        // M-Laser + Rifle combo - 15 TP
        if (availableTP >= 15 && targetDistance <= 12 && inArray(equippedWeapons, WEAPON_M_LASER)) {
            var dmg = calculateSequenceDamage([WEAPON_M_LASER, WEAPON_RIFLE], mySTR);
            push(sequences, [
                [WEAPON_M_LASER, WEAPON_RIFLE],
                15, dmg, 0, "mid_combo"
            ]);
        }
        // Double Rifle - 14 TP
        if (availableTP >= 14 && inArray(equippedWeapons, WEAPON_RIFLE)) {
            var dmg = calculateSequenceDamage([WEAPON_RIFLE, WEAPON_RIFLE], mySTR);
            push(sequences, [
                [WEAPON_RIFLE, WEAPON_RIFLE],
                14, dmg, 0, "mid_burst"
            ]);
        }
        // Single Rifle - 7 TP
        if (availableTP >= 7 && inArray(equippedWeapons, WEAPON_RIFLE)) {
            var dmg = calculateSequenceDamage([WEAPON_RIFLE], mySTR);
            push(sequences, [
                [WEAPON_RIFLE],
                7, dmg, 0, "mid_single"
            ]);
        }
    }
    
    // Long-range sequences (5-12 cells for M-Laser)
    if (targetDistance >= 5 && targetDistance <= 12) {
        // Double M-Laser - 16 TP
        if (availableTP >= 16 && inArray(equippedWeapons, WEAPON_M_LASER)) {
            var dmg = calculateSequenceDamage([WEAPON_M_LASER, WEAPON_M_LASER], mySTR);
            push(sequences, [
                [WEAPON_M_LASER, WEAPON_M_LASER],
                16, dmg, 0, "long_burst"
            ]);
        }
        // Single M-Laser - 8 TP
        if (availableTP >= 8 && inArray(equippedWeapons, WEAPON_M_LASER)) {
            var dmg = calculateSequenceDamage([WEAPON_M_LASER], mySTR);
            push(sequences, [
                [WEAPON_M_LASER],
                8, dmg, 0, "long_single"
            ]);
        }
    }
    
    // AoE sequences (4-7 cells for Grenade)
    if (targetDistance >= 4 && targetDistance <= 7 && inArray(equippedWeapons, WEAPON_GRENADE_LAUNCHER)) {
        // Single Grenade - 6 TP (can hit multiple enemies)
        if (availableTP >= 6) {
            var dmg = calculateSequenceDamage([WEAPON_GRENADE_LAUNCHER], mySTR);
            push(sequences, [
                [WEAPON_GRENADE_LAUNCHER],
                6, dmg, 0, "aoe_single"
            ]);
        }
    }
    
    // Find best sequence by damage/TP ratio considering self-damage
    var bestSequence = null;
    var bestScore = 0;
    
    for (var seq in sequences) {
        var tpCost = seq[1];
        var damage = seq[2];
        var selfDamage = seq[3];
        
        // Score = damage - (self-damage * 2) to penalize self-damage
        var score = damage - (selfDamage * 2);
        
        // Bonus for using all TP efficiently
        if (tpCost == availableTP) score *= 1.1;
        
        if (score > bestScore) {
            bestScore = score;
            bestSequence = seq;
        }
    }
    
    return bestSequence;
}

// Execute a damage sequence
function executeDamageSequence(sequence, target) {
    if (sequence == null) return 0;
    
    var weapons = sequence[0];
    var expectedDamage = sequence[2];
    var totalDamage = 0;
    
    debugLog("Executing sequence: " + sequence[4] + " for " + expectedDamage + " dmg");
    
    for (var weapon in weapons) {
        if (getTP() < getWeaponCost(weapon)) {
            debugLog("Not enough TP for " + weapon);
            break;
        }
        
        // Set weapon only if needed to avoid wasting TP
        setWeaponIfNeeded(weapon);
        var result;
        
        // M-Laser needs to target a cell in line with enemy
        if (weapon == WEAPON_M_LASER) {
            var targetCell = getCell(target);
            result = useWeaponOnCell(targetCell);
        } else {
            result = useWeapon(target);
        }
        
        if (result == USE_SUCCESS) {
            var baseDmg = getWeaponAvgDamage(weapon);
            var actualDmg = calculateDamageWithSTR(baseDmg, getStrength());
            totalDamage += actualDmg;
            debugLog("Used " + weapon + " for ~" + actualDmg + " damage");
        } else {
            debugLog("Failed to use " + weapon + ": " + result);
        }
    }
    
    return totalDamage;
}

// Check if we should use aggressive opening (no buffs, all damage)
function shouldUseAggressiveOpening(enemy) {
    var opponentStrength = getStrength(enemy);
    var enemyName = getName(enemy);
    
    // Always aggressive vs high-damage opponents
    if (opponentStrength >= 500) return true;
    if (enemyName == "Domingo") return true;
    
    // Aggressive if enemy is in range and we can burst
    var distance = getCellDistance(getCell(), getCell(enemy));
    if (distance <= 9 && getTurn() <= 2) {
        // Calculate potential first strike damage
        var mySTR = getStrength();
        var sequence = getBestDamageSequence(getTP(), distance, getLife(), mySTR);
        
        if (sequence != null && sequence[2] > 150) {
            return true;  // Go aggressive if we can deal 150+ damage
        }
    }
    
    return false;
}

// Get turn 1 action plan
function getTurn1Strategy(enemy) {
    var enemyName = getName(enemy);
    var distance = getCellDistance(getCell(), getCell(enemy));
    
    // vs Domingo: Maximum aggression
    if (enemyName == "Domingo") {
        return "all_damage";  // Skip ALL buffs, pure damage
    }
    
    // vs high STR: Early pressure
    if (getStrength(enemy) >= 500) {
        return "one_buff_damage";  // Quick Armoring then damage
    }
    
    // vs Magic users: Need resistance
    if (getMagic(enemy) >= 500) {
        return "defensive_buffs";  // Armoring + Solidification
    }
    
    // Default: Balanced approach
    return "standard_buffs";  // Normal buff sequence
}

// Calculate damage potential for a given TP amount
function getDamagePotential(availableTP, distance, myHP, mySTR) {
    var sequence = getBestDamageSequence(availableTP, distance, myHP, mySTR);
    if (sequence != null) {
        return sequence[2];  // Return expected damage
    }
    return 0;
}