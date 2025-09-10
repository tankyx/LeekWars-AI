// V6 Module: combat/weapon_selection.ls
// Weapon selection and prioritization logic
// Refactored from execute_combat.ls for better modularity

// Include required modules


// Function: buildAttackOptions
// Build and prioritize attack options based on current situation


function buildAttackOptions(currentTP, currentDistance, hasLineOfSight) {


    var attackOptions = [];


    var myWeapons = getWeapons();
    
    // Debug weapon detection
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Detected weapons: " + count(myWeapons));
        for (var i = 0; i < count(myWeapons); i++) {
            debugLog("  Weapon " + i + ": " + myWeapons[i] + " (" + getWeaponName(myWeapons[i]) + ")");
        }
    }
    
    // Add null check for weapons
    if (myWeapons == null) {
        debugLog("ERROR: getWeapons() returned null");
        return [];
    }

    var myChips = getChips();

    var mySTR = getStrength();
    
    // === WEAPON OPTIONS ===
    for (var w = 0; w < count(myWeapons); w++) {
        var weaponId = myWeapons[w];
        
        if (debugEnabled && canSpendOps(500)) {
            debugLog("Processing weapon: " + weaponId + " (" + getWeaponName(weaponId) + ")");
        }

        var minRange = getWeaponMinRange(weaponId);
        var maxRange = getWeaponMaxRange(weaponId);
        var cost = getWeaponCost(weaponId);
        var name = getWeaponName(weaponId);
        
        // Check if weapon is in range and we have TP
        if (currentDistance >= minRange && currentDistance <= maxRange && currentTP >= cost) {
            // Calculate base damage and scale with strength
            var baseDamage = getWeaponBaseDamage(weaponId);
            
            if (debugEnabled && canSpendOps(500)) {
                debugLog("Weapon " + weaponId + " - baseDamage: " + baseDamage + ", range: " + minRange + "-" + maxRange + ", cost: " + cost);
            }

            var scaledDamage = baseDamage * (1 + mySTR / 100);
            
            // Calculate uses possible with current TP
            var maxUses = getWeaponMaxUses(weaponId);
            var possibleUses = min(maxUses, floor(currentTP / cost));
            
            // Special weapon handling
            if (weaponId == WEAPON_M_LASER && !isOnSameLine(myCell, enemyCell)) {
                continue; // Skip M-Laser if not aligned
            }
            
            if (weaponId == WEAPON_DARK_KATANA) {
                var selfDamage = 44 * (1 + mySTR / 100);
                if (myHP <= selfDamage * 2) {
                    continue; // Skip if too dangerous
                }
            }
            
            // Laser weapon line alignment check
            if (weaponId == WEAPON_LASER && !isOnSameLine(myCell, enemyCell)) {
                continue; // Skip Laser if not aligned (line weapon)
            }
            
            // B-Laser line alignment check (if B-Laser system is active)
            if (weaponId == WEAPON_B_LASER && !isOnSameLine(myCell, enemyCell)) {
                continue; // Skip B-Laser if not aligned (line weapon)
            }
            
            // Flame Thrower line alignment check
            if (weaponId == WEAPON_FLAME_THROWER && !isOnSameLine(myCell, enemyCell)) {
                continue; // Skip Flame Thrower if not aligned (line weapon)
            }
            
            // Calculate damage per TP


            var totalDamage = scaledDamage * possibleUses;
            
            // Add poison damage for Flame Thrower
            if (weaponId == WEAPON_FLAME_THROWER) {
                // Poison damage scales with magic: 24-30 base, 27 average
                var poisonDamage = 27 * (1 + myMagic / 100) * possibleUses;
                totalDamage += poisonDamage; // Add poison DoT value
            }

            var totalCost = cost * possibleUses;


            var dptp = (totalCost > 0) ? totalDamage / totalCost : 0;
            
            // Apply weapon-specific bonuses and penalties
            dptp = applyWeaponPriorities(weaponId, dptp, currentDistance, myWeapons);
            
            // Add to options
            push(attackOptions, ["weapon", weaponId, totalDamage, cost, dptp, possibleUses, name]);
        }
    }
    
    // === AoE INDIRECT ATTACKS ===
    // Check for Grenade AoE opportunities when no direct LOS
    if (!hasLineOfSight && count(attackOptions) == 0) {
        var grenadeAoE = checkGrenadeAoEOptions(currentTP, currentDistance, myWeapons, mySTR);
        if (grenadeAoE != null && count(grenadeAoE) > 0) {
            attackOptions = arrayConcat(attackOptions, grenadeAoE);
        }
    }
    
    // === CHIP OPTIONS ===


    var chipOptions = buildChipOptions(currentTP, currentDistance, hasLineOfSight, myChips, mySTR);
    if (chipOptions != null) {
        attackOptions = arrayConcat(attackOptions, chipOptions);
    }
    
    // Sort by damage per TP (highest first)
    
    // Add null check for attackOptions
    if (attackOptions == null) {
        return [];
    }
    
    var sortable = [];
    for (var i = 0; i < count(attackOptions); i++) {
        var option = attackOptions[i];
        push(sortable, [option[4], option]); // [dptp, option] - push modifies in-place
    }
    
    arraySort(sortable, function(a, b) {
        return b[0] - a[0]; // Sort by dptp descending
    });
    
    // Extract the sorted options
    var sortedOptions = [];
    for (var i = 0; i < count(sortable); i++) {
        push(sortedOptions, sortable[i][1]); // push modifies in-place
    }
    
    return sortedOptions;
}

// Function: applyWeaponPriorities
// Apply weapon-specific priority adjustments


function applyWeaponPriorities(weaponId, baseDptp, distance, availableWeapons) {


    var adjustedDptp = baseDptp;
    
    // Weapon priority adjustments
    if (weaponId == WEAPON_RIFLE) {
        // Rifle is excellent in its range
        if (distance >= 7 && distance <= 9) {
            adjustedDptp *= 1.2; // 20% bonus in optimal range
        }
    } else if (weaponId == WEAPON_M_LASER) {
        // M-Laser is superior - highest damage, longest range, line piercing
        adjustedDptp *= 1.4; // 40% bonus - highest priority line weapon
        
        // Multi-enemy bonus if applicable
        if (count(allEnemies) > 1) {
            adjustedDptp *= 1.3; // 30% bonus for multi-hit potential
        }
    } else if (weaponId == WEAPON_DARK_KATANA) {
        // Dark Katana prioritized in close range
        if (distance >= 2 && distance <= 4) {
            adjustedDptp *= 1.5; // 50% bonus for close range positioning
        }
    } else if (weaponId == WEAPON_GRENADE_LAUNCHER) {
        // Grenade penalties when better options available


        var hasBetterOptions = false;
        if (inArray(availableWeapons, WEAPON_RIFLE) && distance >= 7 && distance <= 9) {
            hasBetterOptions = true;
        }
        if (inArray(availableWeapons, WEAPON_M_LASER) && distance >= 5 && distance <= 12) {
            hasBetterOptions = true;
        }
        
        if (hasBetterOptions) {
            adjustedDptp *= 0.7; // 30% penalty when better options exist
        }
        
        // Multi-enemy bonus for AoE
        if (count(allEnemies) > 1) {
            adjustedDptp *= 1.4; // 40% bonus for AoE multi-hit
        }
    } else if (weaponId == WEAPON_NEUTRINO) {
        // Neutrino prioritized for its vulnerability effect
        if (distance >= 2 && distance <= 6) {
            adjustedDptp *= 1.3; // 30% bonus for vulnerability debuff utility
        }
        // Bonus against high-HP enemies where vulnerability helps
        if (getLife(enemy) > 1500) {
            adjustedDptp *= 1.2; // 20% bonus vs tanks
        }
    } else if (weaponId == WEAPON_DESTROYER) {
        // Destroyer prioritized for its strength debuff
        if (distance >= 1 && distance <= 6) {
            adjustedDptp *= 1.25; // 25% bonus for strength debuff utility
        }
        // Bonus against high-STR enemies where debuff is most valuable
        if (getStrength(enemy) > 300) {
            adjustedDptp *= 1.3; // 30% bonus vs high STR enemies
        }
        
        // Penalty when Flame Thrower is available at better range
        if (inArray(availableWeapons, WEAPON_FLAME_THROWER) && distance >= 2) {
            adjustedDptp *= 0.7; // 30% penalty - prefer Flame Thrower for its DoT
        }
    } else if (weaponId == WEAPON_LASER) {
        // Laser is good line weapon, similar to M-Laser but shorter range
        adjustedDptp *= 1.1; // 10% bonus for line piercing
        
        // Multi-enemy bonus if applicable
        if (count(allEnemies) > 1) {
            adjustedDptp *= 1.25; // 25% bonus for multi-hit potential
        }
        
        // Preference in mid-range where it excels
        if (distance >= 4 && distance <= 7) {
            adjustedDptp *= 1.15; // 15% bonus in sweet spot
        }
    } else if (weaponId == WEAPON_FLAME_THROWER) {
        // Flame Thrower is excellent line weapon with poison DoT
        adjustedDptp *= 1.6; // 60% bonus for line piercing + poison damage
        
        // Multi-enemy bonus for line piercing
        if (count(allEnemies) > 1) {
            adjustedDptp *= 1.3; // 30% bonus for multi-hit potential
        }
        
        // Optimal range bonus (2-8 range)
        if (distance >= 2 && distance <= 6) {
            adjustedDptp *= 1.2; // 20% bonus in sweet spot
        }
    }
    
    return adjustedDptp;
}

// Function: buildChipOptions
// Build chip attack options


function buildChipOptions(currentTP, distance, hasLOS, chips, strength) {


    var chipOptions = [];
    
    for (var c = 0; c < count(chips); c++) {


        var chipId = chips[c];


        var chipCost = getChipCost(chipId);


        var chipName = getChipName(chipId);
        
        if (currentTP >= chipCost && isAttackChip(chipId)) {


            var damage = calculateChipDamage(chipId, strength);


            var dptp = damage / chipCost;
            
            // Apply chip-specific range checks
            if (chipId == CHIP_SPARK && distance <= 12) {
                // Spark chip penalty at longer ranges
                if (distance > 8) {
                    dptp *= 0.6; // 40% penalty for long range spark
                }
                push(chipOptions, ["chip", chipId, damage, chipCost, dptp, 1, chipName]);
            } else if (chipId == CHIP_LIGHTNING && distance <= 8 && hasLOS) {
                push(chipOptions, ["chip", chipId, damage, chipCost, dptp, 1, chipName]);
            }
        }
    }
    
    return chipOptions;
}

// Function: isAttackChip
// Check if chip is an attack chip


function isAttackChip(chipId) {


    var attackChips = [CHIP_SPARK, CHIP_LIGHTNING, CHIP_ROCK, CHIP_ICE];
    return inArray(attackChips, chipId);
}

// Function: calculateChipDamage
// Calculate chip damage with strength scaling


function calculateChipDamage(chipId, strength) {


    var baseDamage = 0;
    
    if (chipId == CHIP_SPARK) {
        baseDamage = 30; // Base spark damage
    } else if (chipId == CHIP_LIGHTNING) {
        baseDamage = 55; // Base lightning damage
    } else if (chipId == CHIP_ROCK) {
        baseDamage = 50; // Base rock damage
    } else if (chipId == CHIP_ICE) {
        baseDamage = 45; // Base ice damage
    }
    
    // Scale with strength
    return baseDamage * (1 + strength / 100);
}

// Function: getWeaponBaseDamage
// Get base damage for weapons


function getWeaponBaseDamage(weaponId) {
    if (weaponId == WEAPON_RIFLE) {
        return 76; // Average rifle damage
    } else if (weaponId == WEAPON_M_LASER) {
        return 95; // Average M-Laser damage
    } else if (weaponId == WEAPON_DARK_KATANA) {
        return 99; // Dark Katana base damage
    } else if (weaponId == WEAPON_GRENADE_LAUNCHER) {
        return 150; // Average grenade damage
    } else if (weaponId == WEAPON_B_LASER) {
        return 55; // B-Laser base damage
    } else if (weaponId == WEAPON_MAGNUM) {
        return 65; // Magnum base damage
    } else if (weaponId == WEAPON_DESTROYER) {
        return 50; // Destroyer base damage (40-60 average)
    } else if (weaponId == WEAPON_NEUTRINO) {
        return 27; // Neutrino base damage (25-30 average)  
    } else if (weaponId == WEAPON_LASER) {
        return 51; // Laser base damage (43-59 average)
    } else if (weaponId == WEAPON_FLAME_THROWER) {
        return 37.5; // Flame Thrower base damage (35-40 average)
    }
    
    return 50; // Default fallback
}

// Function: selectBestWeapon
// Select the best weapon for current situation


function selectBestWeapon(attackOptions) {
    // Add null check
    if (attackOptions == null || count(attackOptions) == 0) {
        return null;
    }
    
    // Get the highest priority option


    var bestOption = attackOptions[0];
    
    // Prefer weapons over chips if damage is similar
    for (var i = 0; i < min(3, count(attackOptions)); i++) {


        var option = attackOptions[i];
        if (option[0] == "weapon" && option[4] >= bestOption[4] * 0.9) {
            return option;
        }
    }
    
    return bestOption;
}

// Function: switchToWeaponIfNeeded
// Only switch weapon if different from current


function switchToWeaponIfNeeded(weaponId) {
    if (getWeapon() != weaponId) {
        setWeapon(weaponId);
    }
}

// Function: checkGrenadeAoEOptions
// Look for indirect Grenade attacks using AoE splash damage
function checkGrenadeAoEOptions(currentTP, currentDistance, myWeapons, mySTR) {
    var aoeOptions = [];
    
    // Check if we have Grenade Launcher
    var hasGrenade = false;
    for (var w = 0; w < count(myWeapons); w++) {
        if (myWeapons[w] == WEAPON_GRENADE_LAUNCHER) {
            hasGrenade = true;
            break;
        }
    }
    
    if (!hasGrenade || currentTP < 7) { // Grenade costs 7 TP
        return aoeOptions;
    }
    
    // Get cells around the enemy for AoE targeting
    var enemyX = getCellX(enemyCell);
    var enemyY = getCellY(enemyCell);
    var targetCells = [
        getCellFromXY(enemyX + 1, enemyY),
        getCellFromXY(enemyX - 1, enemyY), 
        getCellFromXY(enemyX, enemyY + 1),
        getCellFromXY(enemyX, enemyY - 1),
        getCellFromXY(enemyX + 1, enemyY + 1),
        getCellFromXY(enemyX - 1, enemyY - 1),
        getCellFromXY(enemyX + 1, enemyY - 1),
        getCellFromXY(enemyX - 1, enemyY + 1)
    ];
    
    // Check each target cell for splash opportunity
    for (var i = 0; i < count(targetCells); i++) {
        var targetCell = targetCells[i];
        if (targetCell == null || targetCell == -1) continue;
        
        var targetDistance = getCellDistance(myCell, targetCell);
        
        // Check if target cell is in grenade range (4-7) and we have LOS to it
        if (targetDistance >= 4 && targetDistance <= 7 && hasLOS(myCell, targetCell)) {
            // Calculate splash damage (reduced from direct hit)
            var baseDamage = 65; // Grenade base damage
            var scaledDamage = baseDamage * (1 + mySTR / 100);
            var splashDamage = scaledDamage * 0.75; // 75% damage from splash
            
            var dptp = splashDamage / 7; // 7 TP cost
            
            // Add AoE attack option
            push(aoeOptions, ["weapon", WEAPON_GRENADE_LAUNCHER, splashDamage, 7, dptp, 1, "Grenade AoE"]);
            
            // Only need one good AoE option
            break;
        }
    }
    
    return aoeOptions;
}