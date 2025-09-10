
// Calculate actual damage with STR scaling
// FinalDamage = BaseDamage * (1 + Strength / 100)

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

function calculateDamageWithSTR(baseDamage, strength) {
    return baseDamage * (1 + strength / 100);
}

// Get weapon's average damage

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

function getWeaponAvgDamage(weapon) {
    if (weapon == WEAPON_RIFLE) return 76;  // (73+79)/2
    if (weapon == WEAPON_DARK_KATANA) return 99;
    if (weapon == WEAPON_M_LASER) return 95;  // (90+100)/2
    if (weapon == WEAPON_GRENADE_LAUNCHER) return 65;  // Approx for single target
    if (weapon == WEAPON_FLAME_THROWER) return 37.5;  // (35+40)/2 direct damage only
    return 0;
}

// Calculate total Flame Thrower damage including poison DoT
function getFlameThrowerTotalDamage(mySTR, myMAG) {
    // Direct damage (scales with STR): 35-40 base, 37.5 average
    var directDamage = 37.5 * (1 + mySTR / 100);
    
    // Poison damage (scales with MAG): 24-30 base, 27 average over 2 turns
    var poisonDamage = 27 * (1 + myMAG / 100);
    
    return directDamage + poisonDamage;
}

// Calculate sequence damage with STR

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

function calculateSequenceDamage(weapons, mySTR) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var totalDamage = 0;
    for (var weapon in weapons) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

        var baseDmg = getWeaponAvgDamage(weapon);
        totalDamage += calculateDamageWithSTR(baseDmg, mySTR);
    }
    return totalDamage;
}

// Get best damage sequence for current TP and range

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

function getBestDamageSequence(availableTP, targetDistance, myHP, mySTR) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var sequences = [];

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var equippedWeapons = getWeapons();
    
    // Melee sequences (distance 1)
    if (targetDistance == 1) {
        // Double Dark Katana - 14 TP, self-damage 88
        if (availableTP >= 14 && myHP > 100 && inArray(equippedWeapons, WEAPON_DARK_KATANA)) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

            var dmg = calculateSequenceDamage([WEAPON_DARK_KATANA, WEAPON_DARK_KATANA], mySTR);
            push(sequences, [
                [WEAPON_DARK_KATANA, WEAPON_DARK_KATANA],
                14, dmg, 88, "melee_kill"
            ]);
        }
        // Single Dark Katana - 7 TP, self-damage 44
        if (availableTP >= 7 && myHP > 60 && inArray(equippedWeapons, WEAPON_DARK_KATANA)) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

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

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

            var dmg = calculateSequenceDamage([WEAPON_M_LASER, WEAPON_RIFLE], mySTR);
            push(sequences, [
                [WEAPON_M_LASER, WEAPON_RIFLE],
                15, dmg, 0, "mid_combo"
            ]);
        }
        // Double Rifle - 14 TP
        if (availableTP >= 14 && inArray(equippedWeapons, WEAPON_RIFLE)) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

            var dmg = calculateSequenceDamage([WEAPON_RIFLE, WEAPON_RIFLE], mySTR);
            push(sequences, [
                [WEAPON_RIFLE, WEAPON_RIFLE],
                14, dmg, 0, "mid_burst"
            ]);
        }
        // Single Rifle - 7 TP
        if (availableTP >= 7 && inArray(equippedWeapons, WEAPON_RIFLE)) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

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

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

            var dmg = calculateSequenceDamage([WEAPON_M_LASER, WEAPON_M_LASER], mySTR);
            push(sequences, [
                [WEAPON_M_LASER, WEAPON_M_LASER],
                16, dmg, 0, "long_burst"
            ]);
        }
        // Single M-Laser - 8 TP
        if (availableTP >= 8 && inArray(equippedWeapons, WEAPON_M_LASER)) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

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

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

            var dmg = calculateSequenceDamage([WEAPON_GRENADE_LAUNCHER], mySTR);
            push(sequences, [
                [WEAPON_GRENADE_LAUNCHER],
                6, dmg, 0, "aoe_single"
            ]);
        }
    }
    
    // Flame Thrower sequences (range 2-8)
    if (targetDistance >= 2 && targetDistance <= 8 && inArray(equippedWeapons, WEAPON_FLAME_THROWER)) {
        // Double Flame Thrower - 12 TP (maximum damage with poison DoT)
        if (availableTP >= 12) {
            var flameDamage = getFlameThrowerTotalDamage(mySTR, myMagic) * 2; // 2 uses
            push(sequences, [
                [WEAPON_FLAME_THROWER, WEAPON_FLAME_THROWER],
                12, flameDamage, 0, "flame_double"
            ]);
        }
        // Single Flame Thrower - 6 TP
        if (availableTP >= 6) {
            var flameDamage = getFlameThrowerTotalDamage(mySTR, myMagic);
            push(sequences, [
                [WEAPON_FLAME_THROWER],
                6, flameDamage, 0, "flame_single"
            ]);
        }
        // Flame Thrower + other weapons combos
        if (availableTP >= 13 && inArray(equippedWeapons, WEAPON_RIFLE)) {
            // Flame Thrower + Rifle combo - 13 TP
            var totalDamage = getFlameThrowerTotalDamage(mySTR, myMagic) + calculateSequenceDamage([WEAPON_RIFLE], mySTR);
            push(sequences, [
                [WEAPON_FLAME_THROWER, WEAPON_RIFLE],
                13, totalDamage, 0, "flame_rifle_combo"
            ]);
        }
    }
    
    // Find best sequence by damage/TP ratio considering self-damage

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var bestSequence = null;

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var bestScore = 0;
    
    for (var seq in sequences) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

        var tpCost = seq[1];

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

        var damage = seq[2];

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

        var selfDamage = seq[3];
        
        // Score = damage - (self-damage * 2) to penalize self-damage

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

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

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

function executeDamageSequence(sequence, target) {
    if (sequence == null) return 0;
    

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var weapons = sequence[0];

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var expectedDamage = sequence[2];

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var totalDamage = 0;
    
    debugLog("Executing sequence: " + sequence[4] + " for " + expectedDamage + " dmg");
    
    for (var weapon in weapons) {
        if (getTP() < getWeaponCost(weapon)) {
            debugLog("Not enough TP for " + weapon);
            break;
        }
        
        // Set weapon only if needed to avoid wasting TP
        switchToWeaponIfNeeded(weapon);

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

        var result;
        
        // M-Laser needs to target a cell in line with enemy
        if (weapon == WEAPON_M_LASER) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

            var targetCell = getCell(target);
            result = useWeaponOnCell(targetCell);
        } else {
            result = useWeapon(target);
        }
        
        if (result == USE_SUCCESS) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

            var baseDmg = getWeaponAvgDamage(weapon);

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

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

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

function shouldUseAggressiveOpening(enemy) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var opponentStrength = getStrength(enemy);

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var enemyName = getName(enemy);
    
    // Always aggressive vs high-damage opponents
    if (opponentStrength >= 500) return true;
    if (enemyName == "Domingo") return true;
    
    // Aggressive if enemy is in range and we can burst

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var distance = getCellDistance(getCell(), getCell(enemy));
    if (distance <= 9 && getTurn() <= 2) {
        // Calculate potential first strike damage

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

        var mySTR = getStrength();

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

        var sequence = getBestDamageSequence(getTP(), distance, getLife(), mySTR);
        
        if (sequence != null && sequence[2] > 150) {
            return true;  // Go aggressive if we can deal 150+ damage
        }
    }
    
    return false;
}

// Get turn 1 action plan

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

function getTurn1Strategy(enemy) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var enemyName = getName(enemy);

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

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

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

function getDamagePotential(availableTP, distance, myHP, mySTR) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var sequence = getBestDamageSequence(availableTP, distance, myHP, mySTR);
    if (sequence != null) {
        return sequence[2];  // Return expected damage
    }
    return 0;
}