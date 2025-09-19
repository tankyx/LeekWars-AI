// V7 Module: combat/execution.ls
// Scenario-based combat execution

// === ENHANCED MULTI-ENEMY COMBAT EXECUTION WITH ENEMY ASSOCIATIONS ===
function executeCombat(fromCell, recommendedWeapon) {
    if (count(enemies) == 0) {
        debugW("COMBAT: No enemies found");
        return;
    }
    
    var tpRemaining = myTP;
    
    if (debugEnabled) {
        debugW("=== ENHANCED COMBAT START ===");
        debugW("TP Available: " + tpRemaining + ", Enemies: " + count(enemies));
    }
    
    // Execute enhanced combat strategy with enemy associations
    var combatAttempts = 0;
    var maxCombatAttempts = 3;
    var lastTP = tpRemaining;
    var consecutiveFailures = 0;
    
    while (tpRemaining >= 3 && count(getEnemies()) > 0 && combatAttempts < maxCombatAttempts) {
        combatAttempts++;
        
        // Update targets and priorities
        updatePrimaryTarget();
        
        if (primaryTarget == null || getLife(primaryTarget) <= 0) {
            if (debugEnabled) {
                debugW("No valid primary target, combat ending");
            }
            break;
        }
        
        // NEW: Try to use enemy associations from current cell's damage zones
        var targetToAttack = primaryTarget;
        var associatedWeapon = recommendedWeapon;
        
        // Check if current cell has enemy associations from damage zones
        var currentCellAssociation = findEnemyAssociationForCell(myCell);
        if (currentCellAssociation != null) {
            targetToAttack = currentCellAssociation[0];   // enemy
            associatedWeapon = currentCellAssociation[1]; // weapon
            
            if (debugEnabled) {
                debugW("ENEMY ASSOCIATION: Using associated target " + targetToAttack + " with weapon " + associatedWeapon);
            }
        }
        
        // If we don't have a recommended weapon, check what we can attack from current cell
        if (recommendedWeapon == null) {
            var bestAttackOption = findBestAttackFromCurrentCell();
            if (bestAttackOption != null) {
                targetToAttack = bestAttackOption.target;
                recommendedWeapon = bestAttackOption.weapon;
                if (debugEnabled) {
                    debugW("FROM CURRENT CELL: Best target " + targetToAttack + " with weapon " + recommendedWeapon);
                }
            }
        }
        
        // If still no recommended weapon, try ALL available weapons systematically
        if (recommendedWeapon == null) {
            var weapons = getWeapons();
            if (weapons != null && count(weapons) > 0) {
                if (debugEnabled) {
                    debugW("WEAPON DETECTION: Trying all " + count(weapons) + " available weapons from current position");
                }
                
                // Try each weapon to see what can hit from current position
                for (var w = 0; w < count(weapons); w++) {
                    var weapon = weapons[w];
                    var weaponCost = getWeaponCost(weapon);
                    
                    if (tpRemaining < weaponCost + 1) continue; // Not enough TP (include weapon switch cost)
                    
                    // Check each enemy
                    for (var e = 0; e < count(enemies); e++) {
                        var currentEnemy = enemies[e];
                        if (getLife(currentEnemy) <= 0) continue;
                        
                        var currentEnemyCell = getCell(currentEnemy);
                        var distance = getCellDistance(myCell, currentEnemyCell);
                        
                        // Check if weapon can reach this enemy
                        if (canWeaponReachTarget(weapon, myCell, currentEnemyCell)) {
                            recommendedWeapon = weapon;
                            targetToAttack = currentEnemy;
                            if (debugEnabled) {
                                debugW("WEAPON DETECTION: Found " + weapon + " can hit " + currentEnemy + " at distance " + distance);
                            }
                            break;
                        }
                    }
                    
                    if (recommendedWeapon != null) break;
                }
                
                if (debugEnabled && recommendedWeapon == null) {
                    debugW("WEAPON DETECTION: No weapons can hit any enemy from current position");
                }
            }
        }
        
        // Check for AoE opportunities first
        var aoeOption = findBestAoETarget();
        if (aoeOption != null && aoeOption.enemyCount >= 2 && tpRemaining >= getWeaponCost(aoeOption.weapon)) {
            if (debugEnabled) {
                debugW("AOE OPPORTUNITY: " + aoeOption.weapon + " can hit " + aoeOption.enemyCount + " enemies");
            }
            tpRemaining = executeAoEAttack(aoeOption, tpRemaining);
        } else {
            // Single-target attack on primary target
            var tpBefore = tpRemaining;
            
            // Use pre-calculated weapon (this should always be available from pathfinding)
            if (recommendedWeapon != null) {
                tpRemaining = executePreCalculatedWeapon(recommendedWeapon, targetToAttack, tpRemaining);
            } else {
                // No recommended weapon - handle "no cells in reach" scenario
                if (debugEnabled) {
                    debugW("NO RECOMMENDED WEAPON: Handling unreachable enemies scenario");
                }
                
                // Try to find any attack from current position
                var bestCurrentAttack = findBestAttackFromCurrentCell();
                if (bestCurrentAttack != null) {
                    // We found something to attack from current cell
                    tpRemaining = executePreCalculatedWeapon(bestCurrentAttack.weapon, bestCurrentAttack.target, tpRemaining);
                    if (debugEnabled) {
                        debugW("CURRENT CELL ATTACK: Used " + bestCurrentAttack.weapon + " on " + bestCurrentAttack.target);
                    }
                } else {
                    // Truly no attacks possible - try emergency options
                    tpRemaining = handleNoAttacksPossible(tpRemaining);
                }
            }
            
            // Track consecutive failures
            if (tpBefore - tpRemaining <= 1) {
                consecutiveFailures++;
                if (debugEnabled) {
                    debugW("CONSECUTIVE FAILURE: " + consecutiveFailures + " (used " + (tpBefore - tpRemaining) + " TP)");
                }
                if (consecutiveFailures >= 2) {
                    if (debugEnabled) {
                        debugW("BREAKING: 2 consecutive combat failures, ending combat");
                    }
                    break;
                }
            } else {
                consecutiveFailures = 0;
            }
        }
        
        // Check if we made progress (damaged or killed enemies)
        var aliveEnemies = getEnemies();
        if (count(aliveEnemies) == 0) {
            if (debugEnabled) {
                debugW("All enemies defeated!");
            }
            break;
        }
        
        // Prevent infinite loops - check both TP usage and attempts
        var tpUsed = lastTP - tpRemaining;
        if (debugEnabled) {
            debugW("LOOP PREVENTION CHECK: TP used this iteration: " + tpUsed + ", attempt " + combatAttempts + "/" + maxCombatAttempts);
        }
        
        if (tpUsed <= 2) {
            if (debugEnabled) {
                debugW("LOOP PREVENTION: Minimal TP progress (used: " + tpUsed + "), attempt " + combatAttempts + "/" + maxCombatAttempts);
            }
            if (combatAttempts >= 2) {
                if (debugEnabled) {
                    debugW("LOOP PREVENTION: Breaking combat loop - no meaningful progress after 2 attempts");
                }
                break;
            }
        } else {
            // Reset attempt counter if we made real progress (used >2 TP)
            combatAttempts = 0;
            if (debugEnabled) {
                debugW("LOOP PREVENTION: Good progress, resetting attempt counter");
            }
        }
        
        lastTP = tpRemaining;
    }
    
    if (debugEnabled) {
        debugW("=== COMBAT COMPLETE ===");
        debugW("TP Used: " + (myTP - tpRemaining) + ", Enemies Remaining: " + count(getEnemies()));
    }
    
    // Update our position after combat
    myCell = getCell();
    myMP = getMP();
}

// === AOE ATTACK EXECUTION ===
function executeAoEAttack(aoeOption, tpRemaining) {
    var weapon = aoeOption.weapon;
    var weaponCost = getWeaponCost(weapon);
    
    if (tpRemaining < weaponCost) {
        if (debugEnabled) {
            debugW("AOE SKIP: Insufficient TP for " + weapon);
        }
        return tpRemaining;
    }
    
    // Switch to AoE weapon if needed
    if (getWeapon() != weapon) {
        setWeapon(weapon);
        tpRemaining -= 1; // Cost of weapon switch
        if (debugEnabled) {
            debugW("AOE: Switched to weapon " + weapon);
        }
    }
    
    // Execute AoE attack on primary target (will hit multiple enemies in AoE)
    if (canUseWeapon(primaryTarget)) {
        if (debugEnabled) {
            debugW("AOE ATTACK: Using " + weapon + " targeting " + primaryTarget + " (affects " + aoeOption.enemyCount + " enemies)");
        }
        
        useWeapon(primaryTarget);
        tpRemaining -= weaponCost;
        
        if (debugEnabled) {
            debugW("AOE SUCCESS: Used " + weapon + ", TP remaining: " + tpRemaining);
        }
    } else {
        if (debugEnabled) {
            debugW("AOE FAIL: Cannot use " + weapon + " on " + primaryTarget);
        }
    }
    
    return tpRemaining;
}

// === PRE-CALCULATED WEAPON EXECUTION ===
function executePreCalculatedWeapon(weaponId, target, tpRemaining) {
    if (target == null || getLife(target) <= 0) {
        return tpRemaining;
    }
    
    if (debugEnabled) {
        debugW("PRE-CALC WEAPON: Using calculated weapon " + weaponId + " on target " + target);
    }
    
    var weaponCost = getWeaponCost(weaponId);
    
    // Check if we have enough TP
    if (tpRemaining < weaponCost) {
        if (debugEnabled) {
            debugW("PRE-CALC FAIL: Not enough TP for weapon " + weaponId + " (need " + weaponCost + ", have " + tpRemaining + ")");
        }
        // Try chip fallback when weapon fails due to insufficient TP
        return tryChipFallback(target, tpRemaining);
    }
    
    // Switch to the pre-calculated weapon if needed
    if (getWeapon() != weaponId) {
        if (tpRemaining < weaponCost + 1) {
            if (debugEnabled) {
                debugW("PRE-CALC FAIL: Not enough TP to switch and use weapon (need " + (weaponCost + 1) + ", have " + tpRemaining + ")");
            }
            // Try chip fallback when can't afford weapon switch
            return tryChipFallback(target, tpRemaining);
        }
        setWeapon(weaponId);
        tpRemaining--;
        if (debugEnabled) {
            debugW("PRE-CALC: Switched to weapon " + weaponId);
        }
    }
    
    // Use the weapon - it should work since it was pre-calculated
    if (debugEnabled) {
        var myPos = getCell();
        var targetPos = getCell(target);
        var distance = getCellDistance(myPos, targetPos);
        var hasLOSCheck = hasLOS(myPos, targetPos);
        var weaponMinRange = getWeaponMinRange(weaponId);
        var weaponMaxRange = getWeaponMaxRange(weaponId);
        debugW("PRE-CALC DEBUG: Weapon " + weaponId + " check - Distance: " + distance + ", Range: " + weaponMinRange + "-" + weaponMaxRange + ", LOS: " + hasLOSCheck + ", MyPos: " + myPos + ", TargetPos: " + targetPos);
    }
    
    // Additional debugging for weapon state
    if (debugEnabled) {
        var currentWeapon = getWeapon();
        var currentTP = getTP();
        var targetValid = (target != null && getLife(target) > 0);
        debugW("PRE-CALC STATE: Current weapon=" + currentWeapon + ", Expected=" + weaponId + ", TP=" + currentTP + ", Target=" + target + ", Valid=" + targetValid);
    }
    
    // CRITICAL FIX: Enhanced Lightninger often fails canUseWeapon() at max range
    // Add manual range/LOS check as fallback for Enhanced Lightninger
    var canAttack = canUseWeapon(target);
    
    if (!canAttack && weaponId == 225) { // Enhanced Lightninger
        if (debugEnabled) {
            debugW("PRE-CALC LIGHTNINGER FIX: Bypassing canUseWeapon() check for Enhanced Lightninger");
        }
        
        var myPos = getCell();
        var targetPos = getCell(target);
        var distance = getCellDistance(myPos, targetPos);
        var hasLOSCheck = hasLOS(myPos, targetPos);
        var inRange = (distance >= 6 && distance <= 10); // Fixed: Enhanced Lightninger range is 6-10
        
        if (hasLOSCheck && inRange && getTP() >= 9) { // Enhanced Lightninger costs 9 TP
            canAttack = true;
            if (debugEnabled) {
                debugW("PRE-CALC LIGHTNINGER FIX: Manual check passed - Distance:" + distance + ", LOS:" + hasLOSCheck + ", TP:" + getTP());
            }
        }
    }
    
    if (canAttack) {
        if (debugEnabled) {
            debugW("PRE-CALC ATTACK: Using " + weaponId + " on " + target);
        }
        
        useWeapon(target);
        tpRemaining -= weaponCost;
        
        if (debugEnabled) {
            debugW("PRE-CALC SUCCESS: Used " + weaponId + " on " + target + " (TP left: " + tpRemaining + ")");
        }
        
        // Try to use weapon multiple times if possible
        var maxUses = getWeaponMaxUses(weaponId);
        var remainingUses = maxUses - 1; // Already used once
        
        while (remainingUses > 0 && tpRemaining >= weaponCost && canUseWeapon(target) && getLife(target) > 0) {
            if (debugEnabled) {
                debugW("PRE-CALC MULTI: Using " + weaponId + " again on " + target + " (use " + (maxUses - remainingUses + 1) + "/" + maxUses + ")");
            }
            
            useWeapon(target);
            tpRemaining -= weaponCost;
            remainingUses--;
        }
    } else {
        if (debugEnabled) {
            debugW("PRE-CALC UNEXPECTED FAIL: Cannot use pre-calculated weapon " + weaponId + " on " + target + " - trying cell-based attack");
        }
        
        // Try using weapon on target's cell instead of entity (might be entity reference issue)
        var targetCell = getCell(target);
        if (targetCell != null && canUseWeaponOnCell(targetCell)) {
            if (debugEnabled) {
                debugW("PRE-CALC CELL SUCCESS: Using " + weaponId + " on cell " + targetCell);
            }
            useWeapon(targetCell);
            tpRemaining -= weaponCost;
            
            if (debugEnabled) {
                debugW("PRE-CALC CELL SUCCESS: Used " + weaponId + " on cell " + targetCell + " (TP left: " + tpRemaining + ")");
            }
            
            // Try to use weapon multiple times if possible
            var maxUses = getWeaponMaxUses(weaponId);
            var remainingUses = maxUses - 1; // Already used once
            
            while (remainingUses > 0 && tpRemaining >= weaponCost && canUseWeaponOnCell(targetCell) && getLife(target) > 0) {
                if (debugEnabled) {
                    debugW("PRE-CALC CELL MULTI: Using " + weaponId + " again on cell " + targetCell + " (use " + (maxUses - remainingUses + 1) + "/" + maxUses + ")");
                }
                
                useWeapon(targetCell);
                tpRemaining -= weaponCost;
                remainingUses--;
            }
        } else {
            if (debugEnabled) {
                debugW("PRE-CALC CELL FAIL: Cannot use weapon on cell " + targetCell + " either - trying chip fallback");
            }
            // Both entity and cell approach failed, try chip fallback
            return tryChipFallback(target, tpRemaining);
        }
    }
    
    return tpRemaining;
}

// === SINGLE TARGET COMBAT ===
function executeSingleTargetCombat(target, tpRemaining) {
    if (target == null || getLife(target) <= 0) {
        return tpRemaining;
    }
    
    var weapons = getWeapons();
    var distance = getCellDistance(myCell, getCell(target));
    
    // Get appropriate scenario for current weapon loadout
    var scenario = getScenarioForLoadout(weapons, tpRemaining);
    
    // Ensure scenario is always an array
    if (scenario == null) {
        scenario = [CHIP_LIGHTNING];
        debugW("COMBAT: Using fallback scenario");
    }
    
    if (debugEnabled) {
        debugW("SINGLE TARGET: [" + join(scenario, ", ") + "] against " + target + " at distance " + distance);
    }
    
    // Execute scenario actions
    for (var i = 0; i < count(scenario) && tpRemaining >= 3; i++) {
        var action = scenario[i];
        
        if (debugEnabled) {
            debugW("ACTION: " + action + " (isWeapon=" + isWeapon(action) + ", isChip=" + isChip(action) + ")");
        }
        
        if (isWeapon(action)) {
            tpRemaining = executeWeaponActionOnTarget(action, target, tpRemaining);
        } else if (isChip(action)) {
            tpRemaining = executeChipActionOnTarget(action, target, tpRemaining);
        }
        
        // Stop if target is defeated
        if (getLife(target) <= 0) {
            if (debugEnabled) {
                debugW("Target " + target + " defeated!");
            }
            break;
        }
    }
    
    return tpRemaining;
}

// === LEGACY SINGLE-ENEMY COMBAT (for backward compatibility) ===
function executeLegacyCombat(fromCell) {
    if (enemy == null) {
        debugW("COMBAT: No enemy found");
        return;
    }
    
    var weapons = getWeapons();
    var tpRemaining = myTP;
    var distance = getCellDistance(myCell, enemyCell);
    
    
    // Get appropriate scenario for current weapon loadout
    var scenario = getScenarioForLoadout(weapons, tpRemaining);
    
    // Ensure scenario is always an array
    if (scenario == null) {
        scenario = [CHIP_LIGHTNING];
        debugW("COMBAT: Using fallback scenario");
    }
    
    if (debugEnabled) {
        debugW("COMBAT SCENARIO: [" + join(scenario, ", ") + "] for distance=" + distance + ", TP=" + tpRemaining);
    }
    
    // Execute scenario actions in sequence
    for (var i = 0; i < count(scenario) && tpRemaining >= 3; i++) {
        var action = scenario[i];
        
        if (debugEnabled) {
            debugW("COMBAT ACTION: " + action + " (isWeapon=" + isWeapon(action) + ", isChip=" + isChip(action) + ")");
        }
        
        if (isWeapon(action)) {
            tpRemaining = executeWeaponAction(action, tpRemaining);
        } else if (isChip(action)) {
            tpRemaining = executeChipAction(action, tpRemaining);
        }
        
        // Stop if enemy is defeated
        if (getLife(enemy) <= 0) {
            if (debugEnabled) {
                debugW("Enemy defeated!");
            }
            break;
        }
    }
    
    // After all combat actions, update our position
    myCell = getCell();
    myMP = getMP();
}

// === TARGET-SPECIFIC WEAPON EXECUTION ===
function executeWeaponActionOnTarget(weapon, target, tpRemaining) {
    if (target == null || getLife(target) <= 0) {
        return tpRemaining;
    }
    
    if (debugEnabled) {
        debugW("WEAPON ON TARGET: Trying weapon " + weapon + " on " + target + " with " + tpRemaining + " TP");
    }
    
    var weaponCost = getWeaponCost(weapon);
    
    // Switch weapon if needed (with caching)
    if (getWeapon() != weapon) {
        if (tpRemaining < weaponCost + 1) {
            if (debugEnabled) {
                debugW("WEAPON FAIL: Not enough TP to switch weapons (need " + (weaponCost + 1) + ", have " + tpRemaining + ")");
            }
            return tpRemaining;
        }
        setWeapon(weapon);
        // Removed invalid assignment: getWeapon() = weapon; // Update cache
        tpRemaining--;
        if (debugEnabled) {
            debugW("Switched to weapon " + weapon + " (cached)");
        }
    } else {
        if (debugEnabled) {
            debugW("WEAPON READY: Already equipped " + weapon + " (no switch needed)");
        }
    }
    
    // Check range to target
    var distance = getCellDistance(myCell, getCell(target));
    var minRange = getWeaponMinRange(weapon);
    var maxRange = getWeaponMaxRange(weapon);
    
    if (distance < minRange || distance > maxRange) {
        if (debugEnabled) {
            debugW("TARGET WEAPON FAIL: Out of range - distance=" + distance + ", range=" + minRange + "-" + maxRange);
        }
        return tryFallbackWeaponsOnTarget(target, tpRemaining, distance);
    }
    
    // Check if we can use weapon on target
    if (!canUseWeapon(target)) {
        if (debugEnabled) {
            var myPos = getCell();
            var targetPos = getCell(target);
            var myX = getCellX(myPos);
            var myY = getCellY(myPos);
            var targetX = getCellX(targetPos);
            var targetY = getCellY(targetPos);
            var dx = abs(targetX - myX);
            var dy = abs(targetY - myY);
            var hasLOSCheck = hasLOS(myPos, targetPos);
            
            debugW("TARGET WEAPON FAIL: Cannot use weapon " + weapon + " on " + target);
            debugW("  Position: Me=" + myPos + "(" + myX + "," + myY + ") → Target=" + targetPos + "(" + targetX + "," + targetY + ")");
            debugW("  Distance=" + distance + ", dx=" + dx + ", dy=" + dy + ", LOS=" + hasLOSCheck);
            
            // Special debugging for NEUTRINO diagonal check
            if (weapon == WEAPON_NEUTRINO) {
                var isDiagonal = (dx == dy && dx > 0);
                debugW("  NEUTRINO: diagonal=" + isDiagonal + " (dx=" + dx + " == dy=" + dy + " && dx>0)");
            }
        }
        return tryFallbackWeaponsOnTarget(target, tpRemaining, distance);
    }
    
    // Execute the attack
    if (debugEnabled) {
        debugW("TARGET WEAPON ATTACK: Using " + weapon + " on " + target);
    }
    
    useWeapon(target);
    tpRemaining -= weaponCost;
    
    if (debugEnabled) {
        debugW("TARGET WEAPON SUCCESS: Used " + weapon + " on " + target + " (TP left: " + tpRemaining + ")");
    }
    
    return tpRemaining;
}

// === TARGET-SPECIFIC CHIP EXECUTION ===
function executeChipActionOnTarget(chip, target, tpRemaining) {
    if (target == null || getLife(target) <= 0) {
        return tpRemaining;
    }
    
    // Check cooldown first
    if (chip == CHIP_TOXIN && chipCooldowns[CHIP_TOXIN] > 0) {
        if (debugEnabled) {
            debugW("TOXIN on cooldown for " + chipCooldowns[CHIP_TOXIN] + " turns");
        }
        // Try VENOM as fallback
        if (canUseChip(CHIP_VENOM, target)) {
            return executeChipActionOnTarget(CHIP_VENOM, target, tpRemaining);
        }
        return tpRemaining;
    }
    
    if (chip == CHIP_VENOM && chipCooldowns[CHIP_VENOM] > 0) {
        if (debugEnabled) {
            debugW("VENOM on cooldown for " + chipCooldowns[CHIP_VENOM] + " turn");
        }
        return tpRemaining;
    }
    
    var chipCost = getChipCost(chip);
    
    if (tpRemaining < chipCost) {
        if (debugEnabled) {
            debugW("CHIP FAIL: Not enough TP for " + chip + " (need " + chipCost + ", have " + tpRemaining + ")");
        }
        return tpRemaining;
    }
    
    if (!canUseChip(chip, target)) {
        if (debugEnabled) {
            debugW("CHIP FAIL: Cannot use " + chip + " on " + target);
        }
        return tpRemaining;
    }
    
    if (debugEnabled) {
        debugW("CHIP ATTACK: Using " + chip + " on " + target);
    }
    
    useChip(chip, target);
    tpRemaining -= chipCost;
    
    // Set cooldown after successful use
    if (chip == CHIP_TOXIN) {
        chipCooldowns[CHIP_TOXIN] = 2; // 2 turn cooldown
        if (debugEnabled) {
            debugW("TOXIN cooldown set: 2 turns");
        }
    } else if (chip == CHIP_VENOM) {
        chipCooldowns[CHIP_VENOM] = 1; // 1 turn cooldown
        if (debugEnabled) {
            debugW("VENOM cooldown set: 1 turn");
        }
    }
    
    if (debugEnabled) {
        debugW("CHIP SUCCESS: Used " + chip + " on " + target + " (TP left: " + tpRemaining + ")");
    }
    
    return tpRemaining;
}

// === FALLBACK WEAPONS FOR TARGET ===
function tryFallbackWeaponsOnTarget(target, tpRemaining, distance) {
    var weapons = getWeapons();
    
    if (debugEnabled) {
        debugW("FALLBACK: Checking " + count(weapons) + " weapons for target " + target + " at distance " + distance);
    }
    
    // Create cache key for this target-distance combination
    var cacheKey = target + "_" + distance;
    
    // Check if we've already tested weapons for this scenario
    if (weaponSwitchCache[cacheKey] != null) {
        var cachedWeapon = weaponSwitchCache[cacheKey];
        if (debugEnabled) {
            debugW("FALLBACK CACHE: Using cached weapon " + cachedWeapon + " for " + cacheKey);
        }
        
        // Try the cached weapon first
        var currentWeap = getWeapon();
        if (currentWeap != cachedWeapon) {
            setWeapon(cachedWeapon);
            // Removed invalid assignment: getWeapon() = cachedWeapon;
            tpRemaining--;
        }
        
        if (canUseWeapon(target)) {
            useWeapon(target);
            tpRemaining -= getWeaponCost(cachedWeapon);
            if (debugEnabled) {
                debugW("FALLBACK CACHE SUCCESS: Used cached weapon " + cachedWeapon);
            }
            return tpRemaining;
        }
    }
    
    // Sort weapons by priority: try current weapon first, then by damage potential
    var weaponPriority = [];
    var currentWeap = getWeapon();
    
    for (var i = 0; i < count(weapons); i++) {
        var weapon = weapons[i];
        var minRange = getWeaponMinRange(weapon);
        var maxRange = getWeaponMaxRange(weapon);
        var weaponCost = getWeaponCost(weapon);
        
        // Skip if weapon is not viable
        if (distance < minRange || distance > maxRange || tpRemaining < weaponCost + 1) {
            continue;
        }
        
        var priority = 0;
        
        // Highest priority: current weapon (no switch cost)
        if (weapon == currentWeap) {
            priority = 1000;
        }
        // Enhanced Lightninger gets high priority
        else if (weapon == WEAPON_ENHANCED_LIGHTNINGER) {
            priority = 800;
        }
        // Rifle gets medium priority
        else if (weapon == WEAPON_RIFLE) {
            priority = 600;
        }
        // M-Laser gets lower priority (requires alignment)
        else if (weapon == WEAPON_M_LASER) {
            priority = 400;
        }
        // Sword gets priority over Katana (less TP cost)
        else if (weapon == WEAPON_SWORD) {
            priority = 300;
        }
        // Katana gets lowest priority (melee range)
        else if (weapon == WEAPON_KATANA) {
            priority = 200;
        }
        
        push(weaponPriority, {weapon: weapon, priority: priority});
    }
    
    // Sort by priority (highest first)
    for (var i = 0; i < count(weaponPriority) - 1; i++) {
        for (var j = i + 1; j < count(weaponPriority); j++) {
            if (weaponPriority[j].priority > weaponPriority[i].priority) {
                var temp = weaponPriority[i];
                weaponPriority[i] = weaponPriority[j];
                weaponPriority[j] = temp;
            }
        }
    }
    
    // Try weapons in priority order
    for (var p = 0; p < count(weaponPriority); p++) {
        var weaponInfo = weaponPriority[p];
        var weapon = weaponInfo.weapon;
        var weaponCost = getWeaponCost(weapon);
        
        if (debugEnabled) {
            debugW("FALLBACK: Testing weapon " + weapon + " (priority " + weaponInfo.priority + ")");
        }
        
        // Test if we can use this weapon WITHOUT switching first (save TP)
        var needsSwitch = (currentWeap != weapon);
        
        if (!needsSwitch) {
            // Already have the right weapon
            if (canUseWeapon(target)) {
                if (debugEnabled) {
                    debugW("FALLBACK SUCCESS: Already equipped " + weapon + ", attacking");
                }
                
                useWeapon(target);
                tpRemaining -= weaponCost;
                
                // Cache this successful weapon
                weaponSwitchCache[cacheKey] = weapon;
                
                return tpRemaining;
            }
        } else {
            // Need to switch - only do it if we're confident it will work
            setWeapon(weapon);
            // Removed invalid assignment: getWeapon() = weapon;
            tpRemaining--;
            
            if (canUseWeapon(target)) {
                if (debugEnabled) {
                    debugW("FALLBACK SUCCESS: Switched to " + weapon + ", attacking");
                }
                
                useWeapon(target);
                tpRemaining -= weaponCost;
                
                // Cache this successful weapon
                weaponSwitchCache[cacheKey] = weapon;
                
                return tpRemaining;
            } else {
                if (debugEnabled) {
                    debugW("FALLBACK FAIL: Cannot use weapon " + weapon + " after switch (LOS/range issue)");
                }
                // We've wasted 1 TP on the switch, continue to try other weapons
            }
        }
    }
    
    if (debugEnabled) {
        debugW("FALLBACK: No weapons in range for target " + target + ", trying chips");
    }
    
    // Try chips as last resort
    if (tpRemaining >= 4) {
        return executeChipActionOnTarget(CHIP_LIGHTNING, target, tpRemaining);
    }
    
    return tpRemaining;
}

// === WEAPON EXECUTION ===
function executeWeaponAction(weapon, tpRemaining) {
    if (debugEnabled) {
        debugW("WEAPON EXEC: Trying weapon " + weapon + " with " + tpRemaining + " TP, enemy " + enemy);
    }
    
    var weaponCost = getWeaponCost(weapon);
    
    // Switch weapon if needed (with caching)
    if (getWeapon() != weapon) {
        if (tpRemaining < weaponCost + 1) {
            if (debugEnabled) {
                debugW("WEAPON FAIL: Not enough TP to switch weapons (need " + (weaponCost + 1) + ", have " + tpRemaining + ")");
            }
            return tpRemaining;
        }
        setWeapon(weapon);
        // Removed invalid assignment: getWeapon() = weapon; // Update cache
        tpRemaining--;
        if (debugEnabled) {
            debugW("Switched to weapon " + weapon + " (cached)");
        }
    } else {
        if (debugEnabled) {
            debugW("WEAPON READY: Already equipped " + weapon + " (no switch needed)");
        }
    }
    
    // Check range manually first
    var distance = getCellDistance(myCell, enemyCell);
    var minRange = getWeaponMinRange(weapon);
    var maxRange = getWeaponMaxRange(weapon);
    
    if (distance < minRange || distance > maxRange) {
        if (debugEnabled) {
            debugW("WEAPON FAIL: Out of range - distance=" + distance + ", range=" + minRange + "-" + maxRange + 
                   ". Trying fallback weapons...");
        }
        // Try other weapons that might be in range
        return tryFallbackWeapons(tpRemaining, distance);
    }
    
    // Now check if we can use the equipped weapon on the enemy
    if (!canUseWeapon(enemy)) {
        if (debugEnabled) {
            debugW("WEAPON FAIL: Cannot use weapon " + weapon + " on enemy " + enemy + 
                   " (distance=" + distance + ", range=" + minRange + "-" + maxRange + 
                   ", LOS=" + lineOfSight(myCell, enemyCell) + "). Trying fallback weapons...");
        }
        // Try other weapons that might work at this distance
        return tryFallbackWeapons(tpRemaining, distance);
    }
    
    // Calculate number of uses
    var maxUses = getWeaponMaxUses(weapon);
    var tpUses = floor(tpRemaining / weaponCost);
    var actualUses = (maxUses > 0) ? min(tpUses, maxUses) : tpUses;
    
    // Execute weapon attacks
    for (var use = 0; use < actualUses; use++) {
        if (tpRemaining < weaponCost) break;
        
        var target = selectBestTarget(weapon);
        if (target != null) {
            if (debugEnabled) {
                debugW("WEAPON ATTACK: Using " + weapon + " on target " + target);
            }
            var result = useWeapon(target);
            tpRemaining -= weaponCost;
            
            if (debugEnabled) {
                debugW("WEAPON SUCCESS: Used " + weapon + " on " + target + " (TP left: " + tpRemaining + ")");
            }
            
            
            // Special handling for area weapons
            if (isAreaWeapon(weapon)) {
                var splashTarget = findBestAreaTarget(weapon);
                if (splashTarget != null) {
                    useWeapon(splashTarget);
                }
            }
        } else {
            break;
        }
    }
    
    return tpRemaining;
}

// === CHIP EXECUTION ===
function executeChipAction(chip, tpRemaining) {
    if (!canUseChip(chip, enemy)) {
        if (debugEnabled) {
            debugW("Cannot use chip " + chip);
        }
        return tpRemaining;
    }
    
    var chipCost = getChipCost(chip);
    if (tpRemaining < chipCost) return tpRemaining;
    
    // Execute chip
    var result = useChip(chip, enemy);
    tpRemaining -= chipCost;
    
    if (debugEnabled) {
        debugW("Used " + chip + " on " + enemy + " (TP left: " + tpRemaining + ")");
    }
    
    return tpRemaining;
}

// === TARGET SELECTION ===
function selectBestTarget(weapon) {
    // For single-target weapons, always target main enemy
    if (!isAreaWeapon(weapon)) {
        // Check basic requirements
        var distance = getCellDistance(myCell, enemyCell);
        var minRange = getWeaponMinRange(weapon);
        var maxRange = getWeaponMaxRange(weapon);
        
        
        if (distance < minRange || distance > maxRange) {
            if (debugEnabled) {
                debugW("TARGET RANGE FAIL: Distance " + distance + " not in range " + minRange + "-" + maxRange);
            }
            return null;
        }
        
        // Check alignment for line weapons (X or Y axis)
        if (isLineWeapon(weapon) && !isOnSameLine(myCell, enemyCell)) {
            return null;
        }
        
        return enemy;
    }
    
    // For area weapons, find best splash target
    return findBestAreaTarget(weapon);
}

function findBestAreaTarget(weapon) {
    if (!isAreaWeapon(weapon)) return enemy;
    
    var bestTarget = null;
    var bestScore = 0;
    var range = getWeaponMaxRange(weapon);
    var area = getWeaponArea(weapon);
    
    // For Grenade Launcher, check cells around enemy for best area effect
    if (weapon == WEAPON_GRENADE_LAUNCHER) {
        // Circle of radius 2 = 13 cells affected
        for (var r = 1; r <= area; r++) {
            var cells = getCellsAtExactDistance(enemyCell, r);
            
            for (var i = 0; i < count(cells); i++) {
                var cell = cells[i];
                var distance = getCellDistance(myCell, cell);
                
                if (distance >= getWeaponMinRange(weapon) && distance <= range) {
                    var score = calculateAreaEffectScore(cell, weapon);
                    if (score > bestScore) {
                        bestScore = score;
                        bestTarget = cell;
                    }
                }
            }
        }
    }
    // For Enhanced Lightninger, direct target is usually best
    else if (weapon == WEAPON_ENHANCED_LIGHTNINGER) {
        bestTarget = enemyCell;
    }
    
    return bestTarget || enemyCell;
}

function calculateAreaEffectScore(targetCell, weapon) {
    var score = 0;
    var area = getWeaponArea(weapon);
    
    // Check all cells within area effect
    var affectedCells = getCellsAtExactDistance(targetCell, area);
    
    for (var i = 0; i < count(affectedCells); i++) {
        var cell = affectedCells[i];
        var distance = getCellDistance(targetCell, cell);
        
        // Check if enemy is in this cell
        if (cell == enemyCell) {
            // Apply area effect damage falloff
            var damageMultiplier = max(0, 1 - 0.2 * distance);
            score += 100 * damageMultiplier;
        }
    }
    
    return score;
}

// === UTILITY FUNCTIONS ===
function isWeapon(action) {
    // Check against known weapon IDs used in V7
    return action == WEAPON_ENHANCED_LIGHTNINGER || action == WEAPON_RIFLE || 
           action == WEAPON_M_LASER || action == WEAPON_KATANA ||
           action == WEAPON_SWORD ||
           action == WEAPON_FLAME_THROWER || action == WEAPON_GRENADE_LAUNCHER || 
           action == WEAPON_B_LASER || action == WEAPON_LASER ||
           action == WEAPON_RHINO || action == WEAPON_NEUTRINO || 
           action == WEAPON_DESTROYER;
}

function isChip(action) {
    return action >= 400; // Chip constants are 400+
}

// === CHIP FALLBACK SYSTEM ===
function tryChipFallback(target, tpRemaining) {
    if (debugEnabled) {
        debugW("CHIP FALLBACK: Trying chips with " + tpRemaining + " TP remaining");
    }
    
    // NO CHIP FALLBACK: AI should move to weapon range instead of using weak chips
    if (debugEnabled) {
        debugW("NO CHIP FALLBACK: Combat ending - AI should move to weapon range next turn");
    }
    
    return false; // No combat action taken - let movement system handle positioning
}

// === TURN INITIALIZATION ===
function initializeCombatTurn() {
    // Reset weapon uses per turn
    var weapons = getWeapons();
    
    // Update weapon usage counters (if needed)
    for (var i = 0; i < count(weapons); i++) {
        var weapon = weapons[i];
        // Most weapons have unlimited uses per turn, 
        // but some may have restrictions
    }
}

// === WEAPON SWITCHING OPTIMIZATION ===
function optimizeWeaponSwitching(scenario, currentTP) {
    // Calculate optimal weapon switch sequence to minimize TP waste
    var optimizedSequence = [];
    // Removed invalid assignment: getWeapon() = getWeapon();
    var tpCost = 0;
    
    for (var i = 0; i < count(scenario); i++) {
        var action = scenario[i];
        
        if (isWeapon(action)) {
            if (getWeapon() != action) {
                tpCost += 1; // Weapon switch cost
                // Removed invalid assignment: getWeapon() = action;
            }
            tpCost += getWeaponCost(action);
        } else if (isChip(action)) {
            tpCost += getChipCost(action);
        }
        
        push(optimizedSequence, action);
        
        // Stop if we exceed available TP
        if (tpCost > currentTP) break;
    }
    
    return optimizedSequence;
}

// === FALLBACK WEAPON SYSTEM ===
function tryFallbackWeapons(tpRemaining, currentDistance) {
    var weapons = getWeapons();
    
    if (debugEnabled) {
        debugW("FALLBACK: Checking " + count(weapons) + " weapons for distance " + currentDistance);
    }
    
    // Try each weapon to see if any are in range
    for (var i = 0; i < count(weapons); i++) {
        var weapon = weapons[i];
        var minRange = getWeaponMinRange(weapon);
        var maxRange = getWeaponMaxRange(weapon);
        var weaponCost = getWeaponCost(weapon);
        
        if (currentDistance >= minRange && currentDistance <= maxRange && 
            tpRemaining >= weaponCost) {
            
            if (debugEnabled) {
                debugW("FALLBACK: Trying weapon " + weapon + " (range " + minRange + "-" + maxRange + ")");
            }
            
            // Switch to this weapon and try using it directly
            if (getWeapon() != weapon) {
                if (tpRemaining < weaponCost + 1) {
                    continue; // Not enough TP to switch, try next weapon
                }
                setWeapon(weapon);
                tpRemaining--;
                if (debugEnabled) {
                    debugW("FALLBACK: Switched to weapon " + weapon);
                }
            }
            
            // Check if we can use this weapon
            if (canUseWeapon(enemy)) {
                if (debugEnabled) {
                    debugW("FALLBACK SUCCESS: Can use weapon " + weapon + " at distance " + currentDistance);
                }
                
                // Execute attacks with this weapon
                var maxUses = getWeaponMaxUses(weapon);
                var tpUses = floor(tpRemaining / weaponCost);
                var actualUses = (maxUses > 0) ? min(tpUses, maxUses) : tpUses;
                
                for (var use = 0; use < actualUses; use++) {
                    if (tpRemaining < weaponCost) break;
                    
                    var target = selectBestTarget(weapon);
                    if (target != null) {
                        if (debugEnabled) {
                            debugW("FALLBACK ATTACK: Using " + weapon + " on target " + target);
                        }
                        useWeapon(target);
                        tpRemaining -= weaponCost;
                    } else {
                        break;
                    }
                }
                
                return tpRemaining;
            } else {
                if (debugEnabled) {
                    debugW("FALLBACK FAIL: Cannot use weapon " + weapon + " at distance " + currentDistance);
                }
            }
        }
    }
    
    if (debugEnabled) {
        debugW("FALLBACK: No weapons in range, trying chips");
    }
    
    // If no weapons work, try chips
    var chips = getChips();
    for (var j = 0; j < count(chips); j++) {
        var chip = chips[j];
        if (canUseChip(chip, enemy)) {
            return executeChipAction(chip, tpRemaining);
        }
    }
    
    return tpRemaining;
}

// === CLOSEST ENEMY FALLBACK FUNCTIONS ===
function canReachEnemyWithWeapons(enemyEntity) {
    if (enemyEntity == null || getLife(enemyEntity) <= 0) {
        return false;
    }
    
    var weapons = getWeapons();
    var distance = getCellDistance(myCell, getCell(enemyEntity));
    
    // Check if any weapon can reach this enemy
    for (var i = 0; i < count(weapons); i++) {
        var weapon = weapons[i];
        var minRange = getWeaponMinRange(weapon);
        var maxRange = getWeaponMaxRange(weapon);
        var weaponCost = getWeaponCost(weapon);
        
        if (distance >= minRange && distance <= maxRange && myTP >= weaponCost + 1) {
            // Check if we have line of sight
            if (hasLOS(myCell, getCell(enemyEntity))) {
                return true;
            }
        }
    }
    
    return false;
}

function findClosestReachableEnemy() {
    // Get current alive enemies
    var currentEnemies = getEnemies();
    if (currentEnemies == null || count(currentEnemies) == 0) {
        return null;
    }
    
    var closestEnemy = null;
    var closestDistance = 999;
    
    for (var i = 0; i < count(currentEnemies); i++) {
        var enemyEntity = currentEnemies[i];
        
        if (getLife(enemyEntity) <= 0) {
            continue; // Skip dead enemies
        }
        
        var distance = getCellDistance(myCell, getCell(enemyEntity));
        
        // Prefer enemies that are reachable with weapons, but also consider close ones
        var isReachable = canReachEnemyWithWeapons(enemyEntity);
        var effectiveDistance = distance;
        
        // Give bonus to reachable enemies
        if (isReachable) {
            effectiveDistance = distance * 0.5; // 50% bonus for reachable
        }
        
        if (effectiveDistance < closestDistance) {
            closestDistance = effectiveDistance;
            closestEnemy = enemyEntity;
        }
    }
    
    if (debugEnabled && closestEnemy != null) {
        var actualDistance = getCellDistance(myCell, getCell(closestEnemy));
        var canReach = canReachEnemyWithWeapons(closestEnemy);
        debugW("CLOSEST ENEMY: " + closestEnemy + " at distance " + actualDistance + " (reachable: " + canReach + ")");
    }
    
    return closestEnemy;
}

// === USE DAMAGE ZONES TO FIND BEST ATTACK FROM CURRENT CELL ===
function findBestAttackFromCurrentCell() {
    if (damageZonesPerEnemy == null) {
        return null;
    }
    
    var bestOption = null;
    var bestDamage = 0;
    
    // Check each enemy's damage zones for our current cell
    for (var enemyId in damageZonesPerEnemy) {
        var enemyZones = damageZonesPerEnemy[enemyId];
        if (enemyZones == null) continue;
        
        // Look for our current cell in this enemy's damage zones
        for (var i = 0; i < count(enemyZones); i++) {
            var zoneData = enemyZones[i];
            var cell = zoneData[0];
            var damage = zoneData[1];
            var weapon = zoneData[2];
            
            if (cell == myCell && damage > bestDamage) {
                bestDamage = damage;
                bestOption = {
                    target: enemyId,
                    weapon: weapon,
                    damage: damage
                };
            }
        }
    }
    
    if (bestOption != null && debugEnabled) {
        debugW("BEST FROM CURRENT: Target " + bestOption.target + ", weapon " + bestOption.weapon + ", damage " + bestOption.damage);
    }
    
    return bestOption;
}

// === HANDLE TRULY NO ATTACKS POSSIBLE SCENARIO ===
function handleNoAttacksPossible(tpRemaining) {
    if (debugEnabled) {
        debugW("NO ATTACKS POSSIBLE: Trying emergency options");
    }
    
    // NO EMERGENCY CHIP ATTACKS: AI should move to weapon range instead
    if (debugEnabled) {
        debugW("NO EMERGENCY CHIP ATTACKS: AI should move toward enemy instead of using chips");
    }
    
    // SKIP CHIP ATTACKS: Move to weapon range instead
    if (debugEnabled) {
        debugW("NO ATTACKS: Emergency phase skipped - AI should reposition next turn");
    }
    
    return tpRemaining;
}

// === NEW: ENEMY ASSOCIATION LOOKUP ===
function findEnemyAssociationForCell(cellId) {
    // Look for enemy association in global damage array
    if (currentDamageArray == null || count(currentDamageArray) == 0) {
        return null;
    }
    
    // Find best association for this cell
    var bestAssociation = null;
    var highestDamage = 0;
    
    for (var i = 0; i < count(currentDamageArray); i++) {
        var entry = currentDamageArray[i];
        var cell = entry[0];
        var damage = entry[1];
        var weaponId = (count(entry) > 2) ? entry[2] : null;
        var enemyEntity = (count(entry) > 3) ? entry[3] : null;
        
        // If this entry matches our cell and has higher damage
        if (cell == cellId && damage > highestDamage && enemyEntity != null && weaponId != null) {
            highestDamage = damage;
            bestAssociation = [];
            push(bestAssociation, enemyEntity);  // enemy
            push(bestAssociation, weaponId);     // weapon
            push(bestAssociation, damage);       // damage
        }
    }
    
    return bestAssociation;
}

// === ENHANCED WEAPON SELECTION WITH ENEMY TARGETING ===
function selectBestWeaponForEnemy(enemyEntity) {
    if (enemyEntity == null || getLife(enemyEntity) <= 0) {
        return null;
    }
    
    var weapons = getWeapons();
    if (weapons == null || count(weapons) == 0) {
        return null;
    }
    
    var targetEnemyCell = getCell(enemyEntity);
    var bestWeapon = null;
    var bestDamage = 0;
    
    // Check each weapon for this specific enemy
    for (var w = 0; w < count(weapons); w++) {
        var weapon = weapons[w];
        var weaponCost = getWeaponCost(weapon);
        
        if (myTP < weaponCost + 1) continue; // Not enough TP
        
        // Check if weapon can reach this enemy
        if (canWeaponReachTarget(weapon, myCell, targetEnemyCell)) {
            var damage = calculateWeaponDamageFromCell(weapon, myCell, targetEnemyCell);
            if (damage > bestDamage) {
                bestDamage = damage;
                bestWeapon = weapon;
            }
        }
    }
    
    return bestWeapon;
}