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
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Detected weapons: " + count(myWeapons));
        for (var i = 0; i < count(myWeapons); i++) {
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("  Weapon " + i + ": " + myWeapons[i] + " (" + getWeaponName(myWeapons[i]) + ")");
            }
        }
        }
    }


    
    // Add null check for weapons
    if (myWeapons == null) {
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("ERROR: getWeapons() returned null");
        }
        return [];
    }


    var myChips = getChips();

    var mySTR = getStrength();
    
    // === WEAPON OPTIONS ===
    for (var w = 0; w < count(myWeapons); w++) {
        var weaponId = myWeapons[w];
        
        if (debugEnabled && canSpendOps(500)) {
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("Processing weapon: " + weaponId + " (" + getWeaponName(weaponId) + ")");
            }
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
                if (debugEnabled && canSpendOps(1000)) {
		debugLog("Weapon " + weaponId + " - baseDamage: " + baseDamage + ", range: " + minRange + "-" + maxRange + ", cost: " + cost);
                }
            }


            var scaledDamage = baseDamage * (1 + mySTR / 100);
            
            // Calculate uses possible with current TP
            var maxUses = getWeaponMaxUses(weaponId);
            
            // Special tracking for weapons with custom usage limits
            if (weaponId == WEAPON_MAGNUM) {
                if (magnumUsesRemaining <= 0) {
                    if (debugEnabled && canSpendOps(500)) {
                        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Skipping Magnum - no uses remaining (" + magnumUsesRemaining + ")");
                        }
                    }
                    continue; // Skip if no uses left
                }

                maxUses = magnumUsesRemaining; // Use custom tracking for Magnum
            } else if (weaponId == WEAPON_B_LASER) {
                if (bLaserUsesRemaining <= 0) {
                    if (debugEnabled && canSpendOps(500)) {
                        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Skipping B-Laser - no uses remaining (" + bLaserUsesRemaining + ")");
                        }
                    }
                    continue; // Skip if no uses left
                }

                maxUses = bLaserUsesRemaining; // Use custom tracking for B-Laser
            } else if (weaponId == WEAPON_ENHANCED_LIGHTNINGER) {
                if (enhancedLightningerUsesRemaining <= 0) {
                    if (debugEnabled && canSpendOps(500)) {
                        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Skipping Enhanced Lightninger - no uses remaining (" + enhancedLightningerUsesRemaining + ")");
                        }
                    }
                    continue; // Skip if no uses left
                }

                maxUses = enhancedLightningerUsesRemaining; // Use custom tracking for Enhanced Lightninger
            } else if (weaponId == WEAPON_KATANA) {
                if (katanaUsesRemaining <= 0) {
                    if (debugEnabled && canSpendOps(500)) {
                        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Skipping Katana - no uses remaining (" + katanaUsesRemaining + ")");
                        }
                    }
                    continue; // Skip if no uses left
                }

                maxUses = katanaUsesRemaining; // Use custom tracking for Katana
            }

            
            var possibleUses = min(maxUses, floor(currentTP / cost));
            
            // Special weapon handling
            if (weaponId == WEAPON_M_LASER && !isOnSameLine(myCell, enemyCell)) {
                if (debugEnabled && canSpendOps(500)) {
                    if (debugEnabled && canSpendOps(1000)) {
		debugLog("Skipping M-Laser - not aligned");
                    }
                }
                continue; // Skip M-Laser if not aligned
            }

            
            if (weaponId == WEAPON_DARK_KATANA) {
                var selfDamage = 44 * (1 + mySTR / 100);
                if (myHP <= selfDamage * 2) {
                    if (debugEnabled && canSpendOps(500)) {
                        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Skipping Dark Katana - too dangerous (HP: " + myHP + ", selfDmg: " + selfDamage + ")");
                        }
                    }
                    continue; // Skip if too dangerous
                }
            }


            
            // Laser weapon line alignment check
            if (weaponId == WEAPON_LASER && !isOnSameLine(myCell, enemyCell)) {
                if (debugEnabled && canSpendOps(500)) {
                    if (debugEnabled && canSpendOps(1000)) {
		debugLog("Skipping Laser - not aligned");
                    }
                }
                continue; // Skip Laser if not aligned (line weapon)
            }

            
            // B-Laser line alignment check (if B-Laser system is active)
            if (weaponId == WEAPON_B_LASER && !isOnSameLine(myCell, enemyCell)) {
                if (debugEnabled && canSpendOps(500)) {
                    if (debugEnabled && canSpendOps(1000)) {
		debugLog("Skipping B-Laser - not aligned");
                    }
                }
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
            
            // Add healing value for Enhanced Lightninger
            if (weaponId == WEAPON_ENHANCED_LIGHTNINGER) {
                // 100 HP flat heal per use (not affected by magic/wisdom)
                var healValue = 100 * possibleUses;
                // Convert heal to damage equivalent for comparison
                totalDamage += healValue * 0.8; // 80% damage equivalent for healing
            }
            
            // Add TP debuff value for Katana
            if (weaponId == WEAPON_KATANA) {
                // TP debuff scales with magic: -30-40% TP for 1 turn, 35% average
                var tpDebuffPercent = 0.35 * (1 + myMagic / 100); // Scale with magic
                var tpDebuffValue = enemyTP * tpDebuffPercent * possibleUses;
                // Convert TP denial to damage equivalent (1 TP ≈ 3 damage equivalent)
                totalDamage += tpDebuffValue * 3; // TP denial is very valuable
            }


            var totalCost = cost * possibleUses;


            var dptp = (totalCost > 0) ? totalDamage / totalCost : 0;
            
            // Apply weapon-specific bonuses and penalties
            dptp = applyWeaponPriorities(weaponId, dptp, currentDistance, myWeapons);
            
            // Add to options
            push(attackOptions, ["weapon", weaponId, totalDamage, cost, dptp, possibleUses, name]);
            
            if (debugEnabled && canSpendOps(500)) {
                if (debugEnabled && canSpendOps(1000)) {
		debugLog("Added weapon option: " + name + " (damage: " + totalDamage + ", dptp: " + dptp + ", uses: " + possibleUses + ")");
                }
            }

        } else {
            if (debugEnabled && canSpendOps(500)) {
                var reason = "";
                if (currentDistance < minRange) reason = "too close (" + currentDistance + " < " + minRange + ")";
                else if (currentDistance > maxRange) reason = "too far (" + currentDistance + " > " + maxRange + ")";
                else if (currentTP < cost) reason = "insufficient TP (" + currentTP + " < " + cost + ")";
                if (debugEnabled && canSpendOps(1000)) {
		debugLog("Skipping " + name + " - " + reason);
                }
            }
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

    
    // Debug pre-sort order
    if (debugEnabled) {
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("PRE-SORT weapon order:");
        }
        for (var i = 0; i < min(5, count(attackOptions)); i++) {
            var option = attackOptions[i];
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("  " + i + ": " + option[6] + " (dptp: " + option[4] + ")");
            }
        }
    }


    
    var sortable = [];
    for (var i = 0; i < count(attackOptions); i++) {
        var option = attackOptions[i];
        push(sortable, [option[4], option]); // [dptp, option] - push modifies in-place
    }

    
    // Debug pre-sort order
    if (debugEnabled) {
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Before arraySort:");
        }
        for (var j = 0; j < count(sortable); j++) {
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("  " + j + ": dptp=" + sortable[j][0] + " weapon=" + sortable[j][1][6]);
            }
        }
    }


    
    // Use simple bubble sort for reliable descending order (highest dptp first)
    for (var i = 0; i < count(sortable) - 1; i++) {
        for (var j = 0; j < count(sortable) - 1 - i; j++) {
            if (sortable[j][0] < sortable[j + 1][0]) { // If current < next, swap them
                var temp = sortable[j];
                sortable[j] = sortable[j + 1];
                sortable[j + 1] = temp;
                if (debugEnabled && canSpendOps(500)) {
                    if (debugEnabled && canSpendOps(1000)) {
		debugLog("Swapped: " + sortable[j + 1][1][6] + "(" + sortable[j + 1][0] + ") with " + sortable[j][1][6] + "(" + sortable[j][0] + ")");
                    }
                }
            }
        }
    }




    
    // Debug post-sort order
    if (debugEnabled) {
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("After arraySort:");
        }
        for (var j = 0; j < count(sortable); j++) {
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("  " + j + ": dptp=" + sortable[j][0] + " weapon=" + sortable[j][1][6]);
            }
        }
    }


    
    // Extract the sorted options
    var sortedOptions = [];
    for (var i = 0; i < count(sortable); i++) {
        push(sortedOptions, sortable[i][1]); // push modifies in-place
    }

    
    // Debug the final sorted order - ALWAYS show this critical info
    if (debugEnabled) {
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Sorting " + count(attackOptions) + " options into " + count(sortedOptions) + " sorted");
        }
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Final weapon order after sorting:");
        }
        for (var i = 0; i < min(5, count(sortedOptions)); i++) {
            var option = sortedOptions[i];
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("  " + i + ": " + option[6] + " (dptp: " + option[4] + ")");
            }
        }
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
        // Grenade Launcher should compete based on its high damage, no artificial penalties
        // Let dptp comparison handle priority naturally
        
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

        
        // Apply penalty only when Flame Thrower is equipped and viable
        // (This leek has B-Laser + Magnum + Grenade, no Flame Thrower, so no penalty should apply)
        if (inArray(availableWeapons, WEAPON_FLAME_THROWER) && distance >= 2 && distance <= 8) {
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

    } else if (weaponId == WEAPON_ENHANCED_LIGHTNINGER) {
        // Enhanced Lightninger is excellent AoE weapon with healing
        adjustedDptp *= 1.8; // 80% bonus for AoE damage + healing utility
        
        // Multi-enemy bonus for 3x3 AoE
        if (count(allEnemies) > 1) {
            adjustedDptp *= 1.5; // 50% bonus for multi-hit AoE potential
        }
        
        // Bonus when at low health (healing value)
        if (myHP < myMaxHP * 0.7) {
            adjustedDptp *= 1.3; // 30% bonus when healing is valuable
        }
        
        // Optimal range bonus (6-10 range)
        if (distance >= 6 && distance <= 8) {
            adjustedDptp *= 1.2; // 20% bonus in sweet spot
        }

    } else if (weaponId == WEAPON_KATANA) {
        // Katana is excellent melee weapon with TP debuff
        adjustedDptp *= 1.7; // 70% bonus for TP debuff utility + high damage
        
        // Bonus against high-TP enemies where debuff is most valuable
        if (enemyTP > 10) {
            adjustedDptp *= 1.4; // 40% bonus vs high TP enemies
        }
        
        // Bonus in melee range (range 1 only)
        if (distance == 1) {
            adjustedDptp *= 1.3; // 30% bonus at optimal range
        }

    } else if (weaponId == WEAPON_MAGNUM) {
        // Magnum competes on raw dptp - no artificial bonuses
        // Life steal is factored into damage calculation already
    }

    
    if (debugEnabled && canSpendOps(500)) {
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Priority adjustment for " + getWeaponName(weaponId) + ": " + baseDptp + " -> " + adjustedDptp);
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
    } else if (weaponId == WEAPON_ENHANCED_LIGHTNINGER) {
        return 91; // Enhanced Lightninger base damage (89-93 average)
    } else if (weaponId == WEAPON_KATANA) {
        return 77; // Katana base damage
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
