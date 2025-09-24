// V7 Module: combat/execution.ls
// Scenario-based combat execution

// === ENHANCED MULTI-ENEMY COMBAT EXECUTION WITH ENEMY ASSOCIATIONS ===
function executeCombat(fromCell, recommendedWeapon) {
    if (count(allEnemies) == 0) {
        return;
    }
    
    var tpRemaining = getTP();
    
    // Enhanced combat starting
    
    // Execute enhanced combat strategy with enemy associations
    var combatAttempts = 0;
    var maxCombatAttempts = 2; // REDUCED from 3 to 2
    var lastTP = tpRemaining;
    var consecutiveFailures = 0;
    var weaponSwitches = 0;
    var maxWeaponSwitches = 3; // PREVENT infinite weapon switching
    
    // Limit to single combat attempt when called from peek-a-boo to prevent weapon switching loops
    var maxLoops = (fromCell == getCell()) ? 1 : maxCombatAttempts;
    
    while (tpRemaining >= 3 && count(getEnemies()) > 0 && combatAttempts < maxLoops) {
        combatAttempts++;
        
        // Update targets and priorities
        updatePrimaryTarget();
        
        if (primaryTarget == null || getLife(primaryTarget) <= 0) {
            break;
        }
        
        // Try to use enemy associations from current cell's damage zones
        var targetToAttack = primaryTarget;
        var associatedWeapon = recommendedWeapon;
        
        // Check if current cell has enemy associations from damage zones
        // Checking enemy associations
        var currentCellAssociation = findEnemyAssociationForCell(myCell);
        if (currentCellAssociation != null) {
            targetToAttack = currentCellAssociation[0];   // enemy
            associatedWeapon = currentCellAssociation[1]; // weapon
            debugW("ENEMY ASSOCIATION: Using associated target " + targetToAttack + " with weapon " + associatedWeapon);
        } else {
            // No enemy associations found
        }
        
        // If we don't have a recommended weapon, get scenario for current TP
        if (recommendedWeapon == null) {
            var scenario = getBestScenarioForTP(tpRemaining, true);

            // If no valid scenario, we should stop combat
            if (scenario == null || count(scenario) == 0) {
                break;
            }
            
            // Use the first weapon from the scenario as recommended weapon
            for (var i = 0; i < count(scenario); i++) {
                var action = scenario[i];
                if (isWeapon(action)) {
                    recommendedWeapon = action;
                    break;
                }
            }
            
            if (recommendedWeapon == null) {
                break;
            }
        }
        
        // Check for AoE opportunities first
        var aoeOption = findBestAoETarget();
        if (aoeOption != null && aoeOption.enemyCount >= 2 && tpRemaining >= getWeaponCost(aoeOption.weapon)) {
            // AoE opportunity found
            tpRemaining = executeAoEAttack(aoeOption, tpRemaining);
        } else {
            // Single-target attack on primary target
            var tpBefore = tpRemaining;
            
            // Scenario-based attack: recalculating optimal combinations
            
            // For strength builds: First check what weapons work at current distance
            if (!isMagicBuild && primaryTarget != null) {
                var currentDistance = getCellDistance(getCell(), getCell(primaryTarget));
                // Checking best weapon for current distance
                
                // Find best weapon for current distance using equipped weapons
                var bestWeaponForRange = null;
                var bestWeaponDamage = 0;
                var equippedWeapons = getWeapons();
                for (var w = 0; w < count(equippedWeapons); w++) {
                    var testWeapon = equippedWeapons[w];
                    var minRange = getWeaponMinRange(testWeapon);
                    var maxRange = getWeaponMaxRange(testWeapon);
                    if (currentDistance >= minRange && currentDistance <= maxRange) {
                        // Check alignment for M-Laser and line weapons
                        var alignmentOK = true;
                        var launchType = getWeaponLaunchType(testWeapon);
                        if (launchType == LAUNCH_TYPE_LINE || launchType == LAUNCH_TYPE_LINE_INVERTED) {
                            var myX = getCellX(getCell());
                            var myY = getCellY(getCell());
                            var targetX = getCellX(getCell(primaryTarget));
                            var targetY = getCellY(getCell(primaryTarget));
                            var dx = targetX - myX;
                            var dy = targetY - myY;
                            alignmentOK = (dx == 0) || (dy == 0); // Line weapons require X OR Y axis alignment
                            // Line weapon alignment checked
                        } else if (launchType == LAUNCH_TYPE_DIAGONAL || launchType == LAUNCH_TYPE_DIAGONAL_INVERTED) {
                            var myX = getCellX(getCell());
                            var myY = getCellY(getCell());
                            var targetX = getCellX(getCell(primaryTarget));
                            var targetY = getCellY(getCell(primaryTarget));
                            var dx = abs(targetX - myX);
                            var dy = abs(targetY - myY);
                            alignmentOK = (dx == dy && dx > 0); // Diagonal weapons require perfect diagonal alignment
                            if (!alignmentOK) {
                                // Diagonal weapon lacks alignment
                            }
                        } else if (launchType == LAUNCH_TYPE_STAR || launchType == LAUNCH_TYPE_STAR_INVERTED) {
                            var myX = getCellX(getCell());
                            var myY = getCellY(getCell());
                            var targetX = getCellX(getCell(primaryTarget));
                            var targetY = getCellY(getCell(primaryTarget));
                            var dx = targetX - myX;
                            var dy = targetY - myY;
                            var lineAligned = (dx == 0) || (dy == 0);
                            var diagAligned = (abs(dx) == abs(dy) && dx != 0);
                            alignmentOK = lineAligned || diagAligned; // Star pattern: line OR diagonal
                            if (!alignmentOK) {
                                // Star weapon lacks alignment
                            }
                        }
                        
                        if (alignmentOK) {
                            // Use weapon cost as damage proxy (higher cost usually = higher damage)
                            var damage = getWeaponCost(testWeapon) * 10;
                            // Weapon range and cost checked
                            if (damage > bestWeaponDamage) {
                                bestWeaponDamage = damage;
                                bestWeaponForRange = testWeapon;
                            }
                        }
                    }
                }
                
                if (bestWeaponForRange != null) {
                    // Using range-optimized weapon
                    recommendedWeapon = bestWeaponForRange;
                }
            }
            
            // Get fresh scenario based on current position (after movement)
            var scenario = getBestScenarioForTP(tpRemaining, true);
            
            var actualTPUsed = 0;
            var newTPRemaining = tpRemaining;
            
            if (scenario != null && count(scenario) > 0) {
                // Only log scenario selection if debug enabled
                if (debugEnabled) {
                    // Scenario selected for execution
                }
                newTPRemaining = executeScenario(scenario, targetToAttack, tpRemaining);
                actualTPUsed = tpRemaining - newTPRemaining;
            } else {
                // ERROR: No scenario available - always log this issue
                debugW("ERROR: No combat scenario available for magic build with " + tpRemaining + " TP");
            }
            
            if (actualTPUsed > 0) {
                // Success - only log if debug enabled
                if (debugEnabled) {
                    // Scenario executed successfully
                }
                tpRemaining = newTPRemaining;
                consecutiveFailures = 0; // Reset failure counter
            } else {
                // ERROR: No TP used - always log this issue
                debugW("ERROR: Scenario execution failed - no TP used, falling back to single weapon");
                // Fallback to single weapon attack if scenario fails
                if (recommendedWeapon != null) {
                    // First check if it's a valid weapon before getting cost
                    var validWeapon = recommendedWeapon;

                    // Check if recommendedWeapon is actually a chip ID before using setWeapon
                    if (recommendedWeapon != null && isChip(recommendedWeapon)) {
                        // Recommended action is chip, clearing for fallback
                        validWeapon = null;
                    } else if (recommendedWeapon != null && !isWeapon(recommendedWeapon)) {
                        // Invalid recommended weapon ID
                        validWeapon = null;
                    }

                    if (validWeapon != null) {
                        var weaponCost = getWeaponCost(validWeapon);
                        if (tpRemaining >= weaponCost) {
                            // Ensure correct weapon is equipped for fallback
                            if (getWeapon() != validWeapon) {
                                setWeapon(validWeapon);
                                tpRemaining -= 1; // Account for weapon switch cost
                            }

                            // Use the valid weapon
                            if (canUseWeapon(targetToAttack)) {
                                useWeapon(targetToAttack);
                                recordWeaponUse(validWeapon);
                                tpRemaining -= weaponCost;
                                // Fallback weapon used successfully
                                consecutiveFailures = 0;
                            } else {
                                // Fallback weapon failed - range/LOS issue
                                consecutiveFailures++;
                            }
                        } else {
                            // Insufficient TP for fallback weapon
                            consecutiveFailures++;
                        }
                    } else {
                        // No valid fallback weapon available
                        consecutiveFailures++;
                    }
                } else {
                    // No fallback weapon available
                    consecutiveFailures++;
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
        // Combat phase complete
        debugW("TP Used: " + (myTP - tpRemaining) + ", Enemies Remaining: " + count(getEnemies()));
    }
    
    // MAGIC BUILD HIDE-AND-SEEK TACTICS
    if (isMagicBuild && count(getEnemies()) > 0) {
        var mpRemaining = getMP();
        var currentCell = getCell();
        
        // Check if we successfully applied DoT this turn
        var dotApplied = (myTP - tpRemaining) >= 12; // FLAME_THROWER + FLAME_THROWER costs 12 TP
        
        if (dotApplied && mpRemaining >= 3) {
            debugW("MAGIC TACTICS: DoT applied, attempting to flee from " + count(getEnemies()) + " enemies");
            
            // Find safest position away from all enemies
            var bestFleeCell = null;
            var bestFleeScore = -1;
            var searchRadius = min(mpRemaining, 4); // Don't search too far
            
            for (var dx = -searchRadius; dx <= searchRadius; dx++) {
                for (var dy = -searchRadius; dy <= searchRadius; dy++) {
                    var testCell = currentCell + dx + dy * MAP_WIDTH;
                    var distance = abs(dx) + abs(dy); // Manhattan distance
                    
                    if (distance == 0 || distance > mpRemaining) continue;
                    if (getCellContent(testCell) != CELL_EMPTY) continue;
                    
                    // Calculate safety score - farther from enemies is better
                    var totalEnemyDistance = 0;
                    var hasLoS = false;
                    
                    for (var e = 0; e < count(allEnemies); e++) {
                        var targetEnemyCell = getCell(allEnemies[e]);
                        var enemyDistance = getCellDistance(testCell, targetEnemyCell);
                        totalEnemyDistance += enemyDistance;
                        
                        // Check if enemies have line of sight to this position
                        if (lineOfSight(testCell, targetEnemyCell, targetEnemyCell)) {
                            hasLoS = true;
                        }
                    }
                    
                    // Prefer positions without LoS, but prioritize distance
                    var fleeScore = totalEnemyDistance * 10;
                    if (!hasLoS) fleeScore += 50; // Bonus for breaking LoS
                    
                    if (fleeScore > bestFleeScore) {
                        bestFleeScore = fleeScore;
                        bestFleeCell = testCell;
                    }
                }
            }
            
            // Execute flee movement
            if (bestFleeCell != null && bestFleeCell != currentCell) {
                var moveResult = moveToward(bestFleeCell);
                if (moveResult > 0) {
                    debugW("MAGIC FLEE: Moved toward cell " + bestFleeCell + " (score: " + bestFleeScore + ")");
                } else {
                    debugW("MAGIC FLEE: Failed to move toward " + bestFleeCell);
                }
            }
        }

        // HEALING PHASE: After fleeing, use remaining TP for healing if needed
        var remainingTPAfterFlee = getTP();
        var hpPercent = myHP / myMaxHP;
        var safeDistance = getAverageEnemyDistance() >= 8; // Safe if average distance 8+

        if (remainingTPAfterFlee >= 5 && safeDistance) {
            var healingPriority = getHealingPriority();
            debugW("MAGIC HEALING: HP=" + floor(hpPercent * 100) + "%, TP=" + remainingTPAfterFlee + ", Priority=" + healingPriority);

            // Critical: Use REGENERATION if available and HP very low
            if (shouldUseHealingChip(CHIP_REGENERATION, 0.3) && remainingTPAfterFlee >= 8) {
                debugW("MAGIC HEAL: Using REGENERATION (once per fight) at " + floor(hpPercent * 100) + "% HP");
                if (canUseChip(CHIP_REGENERATION, getEntity())) {
                    useChip(CHIP_REGENERATION, getEntity());
                    regenerationUsed = true;
                    tpRemaining -= 8;
                    debugW("MAGIC HEAL: REGENERATION successful, TP remaining: " + tpRemaining);
                }
            }
            // Moderate: Use REMISSION for reliable healing
            else if (shouldUseHealingChip(CHIP_REMISSION, 0.5) && remainingTPAfterFlee >= 5) {
                debugW("MAGIC HEAL: Using REMISSION at " + floor(hpPercent * 100) + "% HP");
                if (canUseChip(CHIP_REMISSION, getEntity())) {
                    useChip(CHIP_REMISSION, getEntity());
                    chipCooldowns[CHIP_REMISSION] = 1;
                    tpRemaining -= 5;
                    debugW("MAGIC HEAL: REMISSION successful, TP remaining: " + tpRemaining);
                }
            }
            // Sustain: Use VACCINE for heal over time
            else if (shouldUseHealingChip(CHIP_VACCINE, 0.7) && remainingTPAfterFlee >= 6) {
                debugW("MAGIC HEAL: Using VACCINE for HoT at " + floor(hpPercent * 100) + "% HP");
                if (canUseChip(CHIP_VACCINE, getEntity())) {
                    useChip(CHIP_VACCINE, getEntity());
                    chipCooldowns[CHIP_VACCINE] = 4;
                    vaccineHoTTurnsLeft = 3;
                    tpRemaining -= 6;
                    debugW("MAGIC HEAL: VACCINE successful, HoT for 3 turns, TP remaining: " + tpRemaining);
                }
            }
        }
        
        // If we can't flee effectively, use DESTROYER for strength debuffing
        var remainingTP = getTP();
        if (remainingTP >= 6 && getWeapon() != WEAPON_DESTROYER) { // DESTROYER costs 6 TP
            var nearbyEnemies = [];
            for (var e = 0; e < count(allEnemies); e++) {
                var enemyDistance = getCellDistance(getCell(), getCell(allEnemies[e]));
                if (enemyDistance <= 6) { // DESTROYER max range
                    push(nearbyEnemies, allEnemies[e]);
                }
            }
            
            if (count(nearbyEnemies) > 0) {
                debugW("MAGIC TACTICS: Cannot flee effectively, using DESTROYER to debuff enemies");
                // Target strongest enemy first
                var targetEnemy = nearbyEnemies[0];
                var maxStrength = getStrength(targetEnemy);
                for (var e = 1; e < count(nearbyEnemies); e++) {
                    var enemyStrength = getStrength(nearbyEnemies[e]);
                    if (enemyStrength > maxStrength) {
                        maxStrength = enemyStrength;
                        targetEnemy = nearbyEnemies[e];
                    }
                }
                
                if (setWeapon(WEAPON_DESTROYER)) {
                    useWeapon(getCell(targetEnemy));
                    debugW("MAGIC DEBUFF: Used DESTROYER on strongest enemy (strength: " + maxStrength + ")");
                }
            }
        }
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
        recordWeaponUse(weapon);
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

// Old executePreCalculatedWeapon function removed - now uses executeUnifiedWeaponAction with "precalc" mode

// === UNIFIED SCENARIO-BASED COMBAT ===
function executeUnifiedScenarioCombat(target, tpRemaining, mode) {
    var actualTarget = (mode == "legacy") ? enemy : target;
    
    if (actualTarget == null || getLife(actualTarget) <= 0) {
        if (mode == "legacy") {
            debugW("COMBAT: No enemy found");
        }
        return tpRemaining;
    }
    
    var weapons = getWeapons();
    var distance = getCellDistance(myCell, getCell(actualTarget));
    
    // Get appropriate scenario for current weapon loadout
    var scenario = getScenarioForLoadout(weapons, tpRemaining);
    
    // Ensure scenario is always an array
    if (scenario == null) {
        scenario = [CHIP_LIGHTNING];
        debugW("COMBAT: Using fallback scenario");
    }
    
    if (debugEnabled) {
        var targetDesc = (mode == "legacy") ? ("enemy at distance=" + distance) : ("target " + actualTarget + " at distance " + distance);
        debugW("UNIFIED COMBAT: [" + join(scenario, ", ") + "] against " + targetDesc + ", TP=" + tpRemaining);
    }
    
    // Execute scenario actions in sequence
    var lastTPBefore = tpRemaining;
    var successfulActions = 0;
    
    for (var i = 0; i < count(scenario) && tpRemaining >= 3; i++) {
        var action = scenario[i];
        var tpBefore = tpRemaining;
        
        if (debugEnabled) {
            debugW("COMBAT ACTION: " + action + " (isWeapon=" + isWeapon(action) + ", isChip=" + isChip(action) + ")");
        }
        
        if (isWeapon(action)) {
            if (mode == "legacy") {
                tpRemaining = executeWeaponAction(action, tpRemaining);
            } else {
                tpRemaining = executeWeaponActionOnTarget(action, actualTarget, tpRemaining);
            }
        } else if (isChip(action)) {
            if (mode == "legacy") {
                tpRemaining = executeChipAction(action, tpRemaining);
            } else {
                tpRemaining = executeChipActionOnTarget(action, actualTarget, tpRemaining);
            }
        }
        
        // Check if action was successful (TP was consumed)
        var actionSuccess = (tpRemaining < tpBefore);
        if (actionSuccess) {
            successfulActions++;
            if (debugEnabled) {
                debugW("COMBAT SUCCESS: Action " + action + " completed, TP: " + tpBefore + " -> " + tpRemaining);
            }
        } else {
            if (debugEnabled) {
                debugW("COMBAT FAIL: Action " + action + " failed, TP unchanged: " + tpRemaining);
            }
            // Stop executing more weapons if this one failed
            if (isWeapon(action)) {
                // Weapon failed, aborting scenario
                break;
            }
        }
        
        // Stop if target is defeated
        if (getLife(actualTarget) <= 0) {
            if (debugEnabled) {
                var targetName = (mode == "legacy") ? "Enemy" : ("Target " + actualTarget);
                debugW(targetName + " defeated!");
            }
            break;
        }
    }
    
    // Update position for legacy mode
    if (mode == "legacy") {
        myCell = getCell();
        myMP = getMP();
    }
    
    return tpRemaining;
}

// === COMPATIBILITY WRAPPER FUNCTIONS ===
function executeSingleTargetCombat(target, tpRemaining) {
    return executeUnifiedScenarioCombat(target, tpRemaining, "target");
}

function executeLegacyCombat(fromCell) {
    executeUnifiedScenarioCombat(null, myTP, "legacy");
}

// === SCENARIO EXECUTION ===
function executeScenario(scenario, target, tpRemaining) {
    // Executing scenario on target
    
    if (target == null || getLife(target) <= 0) {
        // Scenario aborted - invalid target
        return tpRemaining;
    }
    
    var successfulActions = 0;
    var originalTP = tpRemaining;
    
    for (var i = 0; i < count(scenario) && tpRemaining >= 1; i++) {
        var action = scenario[i];
        var tpBefore = tpRemaining;
        
        // Only log individual actions if debug enabled
        if (debugEnabled) {
            debugW("SCENARIO ACTION " + (i+1) + "/" + count(scenario) + ": " + action + " (TP=" + tpRemaining + ")");
        }
        
        // Debug action type detection
        debugW("ACTION DEBUG: action=" + action + ", isWeapon=" + isWeapon(action) + ", isChip=" + isChip(action));
        
        if (isWeapon(action)) {
            // Execute weapon action
            var weaponCost = getWeaponCost(action);
            if (tpRemaining >= weaponCost) {
                // Switch weapon if needed
                if (getWeapon() != action) {
                    if (tpRemaining >= weaponCost + 1) {
                        setWeapon(action);
                        tpRemaining--;
                        debugW("SCENARIO: Switched to weapon " + action + " (-1 TP)");
                    } else {
                        debugW("SCENARIO: Not enough TP to switch to weapon " + action);
                        break;
                    }
                }
                
                // Use weapon on target
                if (canUseWeapon(target)) {
                    useWeapon(target);
                    recordWeaponUse(action);
                    tpRemaining -= weaponCost;
                    successfulActions++;
                    // Success - only log if debug enabled
                    if (debugEnabled) {
                        debugW("SCENARIO: Used weapon " + action + " (-" + weaponCost + " TP, remaining: " + tpRemaining + ")");
                    }
                } else {
                    // Enhanced debug for weapon failures
                    var myPos = getCell();
                    var targetPos = getCell(target);
                    var myX = getCellX(myPos);
                    var myY = getCellY(myPos);
                    var targetX = getCellX(targetPos);
                    var targetY = getCellY(targetPos);
                    var dx = targetX - myX;
                    var dy = targetY - myY;
                    var distance = getCellDistance(myPos, targetPos);
                    
                    debugW("WEAPON FAIL: " + action + " from " + myPos + "(" + myX + "," + myY + ") to " + targetPos + "(" + targetX + "," + targetY + ")");
                    debugW("WEAPON FAIL: Distance=" + distance + ", dx=" + dx + ", dy=" + dy + ", aligned=" + ((dx == 0) || (dy == 0)));
                    debugW("WEAPON FAIL: LineOfSight=" + lineOfSight(myPos, targetPos, targetPos));
                    
                    break;
                }
            } else {
                // ERROR: Always log insufficient TP
                debugW("ERROR: Not enough TP for weapon " + action + " (need " + weaponCost + ", have " + tpRemaining + ")");
                break;
            }
        } else if (isChip(action)) {
            // Execute chip action
            var chipCost = getChipCost(action);
            // Attempting chip usage
            if (tpRemaining >= chipCost) {
                // Check cooldown status for debug
                if (action == CHIP_TOXIN && chipCooldowns[CHIP_TOXIN] > 0) {
                    debugW("SCENARIO CHIP: CHIP_TOXIN on cooldown for " + chipCooldowns[CHIP_TOXIN] + " turns");
                } else if (action == CHIP_VENOM && chipCooldowns[CHIP_VENOM] > 0) {
                    debugW("SCENARIO CHIP: CHIP_VENOM on cooldown for " + chipCooldowns[CHIP_VENOM] + " turns");
                } else if (action == CHIP_LIBERATION && chipCooldowns[CHIP_LIBERATION] > 0) {
                    debugW("SCENARIO CHIP: CHIP_LIBERATION on cooldown for " + chipCooldowns[CHIP_LIBERATION] + " turns");
                } else if (action == CHIP_ANTIDOTE && chipCooldowns[CHIP_ANTIDOTE] > 0) {
                    debugW("SCENARIO CHIP: CHIP_ANTIDOTE on cooldown for " + chipCooldowns[CHIP_ANTIDOTE] + " turns");
                }

                // DEFENSIVE CHIP TARGETING: Determine correct target for the chip
                var chipTarget = target; // Default to attacking target

                // For defensive chips, determine if we should target self or enemy
                if (action == CHIP_ANTIDOTE) {
                    chipTarget = getEntity(); // Always target self for antidote
                    debugW("DEFENSIVE CHIP: ANTIDOTE targets self for poison removal/healing");
                } else if (action == CHIP_LIBERATION) {
                    // LIBERATION can target self (remove debuffs) or enemy (remove buffs)
                    var shouldTargetSelf = (hasNegativeEffects() || getDefensivePriority() > 40);
                    var shouldTargetEnemy = false;

                    // Check if current target has removable buffs
                    if (target != null && getLife(target) > 0) {
                        shouldTargetEnemy = hasRemovableBuffs(target);
                    }

                    // Prioritize self-targeting if we have critical effects
                    if (shouldTargetSelf && getDefensivePriority() >= 50) {
                        chipTarget = getEntity();
                        debugW("DEFENSIVE CHIP: LIBERATION targets self for debuff removal (priority=" + getDefensivePriority() + ")");
                    } else if (shouldTargetEnemy) {
                        chipTarget = target; // Keep enemy target for buff removal
                        debugW("OFFENSIVE CHIP: LIBERATION targets enemy " + target + " for buff removal");
                    } else if (shouldTargetSelf) {
                        chipTarget = getEntity();
                        debugW("DEFENSIVE CHIP: LIBERATION targets self for effect reduction");
                    }
                }
                
                // Enhanced debugging for chip usage validation using built-in functions
                var canUse = canUseChip(action, chipTarget);
                debugW("CHIP VALIDATION: canUseChip(" + action + ", " + chipTarget + ") = " + canUse);
                if (!canUse) {
                    debugW("CHIP DEBUG: Chip " + action + " failed validation - checking reasons");
                    var minRange = getChipMinRange(action);
                    var maxRange = getChipMaxRange(action);
                    var cooldown = getChipCooldown(action);
                    var maxUses = getChipMaxUses(action);
                    var launchType = getChipLaunchType(action);
                    var area = getChipArea(action);
                    var distance = getCellDistance(getCell(), getCell(chipTarget));
                    var hasLOS = lineOfSight(getCell(), getCell(chipTarget));

                    debugW("CHIP DEBUG: Range=" + minRange + "-" + maxRange + ", Distance=" + distance + ", HasLOS=" + hasLOS);
                    debugW("CHIP DEBUG: Cooldown=" + cooldown + ", MaxUses=" + maxUses + ", LaunchType=" + launchType + ", Area=" + area);
                }

                if (canUse) {
                    useChip(action, chipTarget);
                    tpRemaining -= chipCost;
                    successfulActions++;

                    // Set cooldowns for chips after successful use
                    if (action == CHIP_LIBERATION) {
                        chipCooldowns[CHIP_LIBERATION] = 5; // 5 turn cooldown
                        debugW("COOLDOWN SET: CHIP_LIBERATION cooldown set to 5 turns");
                    } else if (action == CHIP_ANTIDOTE) {
                        chipCooldowns[CHIP_ANTIDOTE] = 4; // 4 turn cooldown
                        debugW("COOLDOWN SET: CHIP_ANTIDOTE cooldown set to 4 turns");
                    } else if (action == CHIP_REGENERATION) {
                        regenerationUsed = true; // Mark as used once per fight
                        debugW("HEALING USED: CHIP_REGENERATION marked as used (once per fight)");
                    } else if (action == CHIP_VACCINE) {
                        chipCooldowns[CHIP_VACCINE] = 4; // 4 turn cooldown
                        vaccineHoTTurnsLeft = 3; // 3 turns of healing
                        debugW("COOLDOWN SET: CHIP_VACCINE cooldown set to 4 turns, HoT for 3 turns");
                    } else if (action == CHIP_REMISSION) {
                        chipCooldowns[CHIP_REMISSION] = 1; // 1 turn cooldown
                        debugW("COOLDOWN SET: CHIP_REMISSION cooldown set to 1 turn");
                    }

                    // Success - only log if debug enabled
                    if (debugEnabled) {
                        debugW("SCENARIO: Used chip " + action + " on " + chipTarget + " (-" + chipCost + " TP, remaining: " + tpRemaining + ")");
                    }
                } else {
                    // ERROR: Always log chip usage failures
                    debugW("ERROR: Cannot use chip " + action + " on target " + chipTarget + " (cooldown or other issue)");
                    break;
                }
            } else {
                // ERROR: Always log insufficient TP for chips
                debugW("ERROR: Not enough TP for chip " + action + " (need " + chipCost + ", have " + tpRemaining + ")");
                break;
            }
        } else {
            // Action is neither weapon nor chip
            debugW("ERROR: Unknown action type " + action + " - not weapon or chip");
            break;
        }
        
        // Check if target is defeated
        if (getLife(target) <= 0) {
            debugW("SCENARIO: Target " + target + " defeated after action " + (i+1) + "!");
            break;
        }
    }
    
    var totalTPUsed = originalTP - tpRemaining;
    debugW("SCENARIO COMPLETE: " + successfulActions + "/" + count(scenario) + " actions completed, " + totalTPUsed + " TP used");
    
    return tpRemaining;
}

// === UNIFIED WEAPON EXECUTION ===
function executeUnifiedWeaponAction(weapon, target, tpRemaining, mode) {
    debugW("UNIFIED WEAPON ENTRY: weapon=" + weapon + ", target=" + target + ", TP=" + tpRemaining + ", mode=" + mode);
    
    if ((target != null && getLife(target) <= 0) || (target == null && mode != "legacy")) {
        debugW("UNIFIED WEAPON EXIT: Invalid target (target=" + target + ", life=" + (target != null ? getLife(target) : "null") + ")");
        return tpRemaining;
    }
    
    // For legacy mode, use global enemy variable
    var actualTarget = (mode == "legacy") ? enemy : target;
    if (actualTarget == null || getLife(actualTarget) <= 0) {
        return tpRemaining;
    }
    
    if (debugEnabled) {
        debugW("UNIFIED WEAPON: Trying " + weapon + " on " + actualTarget + " with " + tpRemaining + " TP (mode: " + mode + ")");
    }
    
    var weaponCost = getWeaponCost(weapon);
    
    // Switch weapon if needed (avoid redundant switches)
    var currentWeapon = getWeapon();
    if (currentWeapon != weapon) {
        if (tpRemaining < weaponCost + 1) {
            if (debugEnabled) {
                debugW("WEAPON FAIL: Not enough TP to switch weapons (need " + (weaponCost + 1) + ", have " + tpRemaining + ")");
            }
            return tpRemaining;
        }
        setWeapon(weapon);
        tpRemaining--;
        
        // Track weapon switches in debug output
        if (debugEnabled) {
            debug("WEAPON SWITCHES: Incremented");
        }
        
        if (debugEnabled) {
            debug("WEAPON SWITCH: " + currentWeapon + " -> " + weapon + " (-1 TP)");
        }
    } else {
        if (debugEnabled) {
            debug("WEAPON OK: Already equipped " + weapon);
        }
    }
    
    // Get target cell
    var targetCell = getCell(actualTarget);
    var distance = getCellDistance(myCell, targetCell);
    var minRange = getWeaponMinRange(weapon);
    var maxRange = getWeaponMaxRange(weapon);
    
    // Range check
    if (distance < minRange || distance > maxRange) {
        if (debugEnabled) {
            debugW("WEAPON FAIL: Out of range - distance=" + distance + ", range=" + minRange + "-" + maxRange);
        }
        
        // FIXED: Don't call fallback weapons during scenario execution to prevent weapon switching loops
        if (mode == "target") {
            debugW("RANGE FAIL: Skipping fallback to prevent weapon switching loop");
            return tpRemaining; // Return unchanged TP to indicate failure
        }
        
        return tryFallbackWeapons(tpRemaining, distance);
    }
    
    // Enhanced Lightninger special handling for precalculated mode
    var canAttack = canUseWeapon(actualTarget);
    if (!canAttack && mode == "precalc" && weapon == 225) { // Enhanced Lightninger
        var hasLOSCheck = checkLineOfSight(myCell, targetCell);
        var inRange = (distance >= 6 && distance <= 10);
        if (hasLOSCheck && inRange && getTP() >= 9) {
            canAttack = true;
            if (debugEnabled) {
                debugW("LIGHTNINGER FIX: Manual check passed");
            }
        }
    }
    
    if (!canAttack) {
        if (debugEnabled) {
            debugW("WEAPON FAIL: Cannot use weapon " + weapon + " on " + actualTarget);
        }
        if (mode == "precalc") {
            // Try cell-based attack
            if (getCellContent(targetCell) != CELL_OBSTACLE) {
                return executeWeaponOnCell(weapon, targetCell, tpRemaining);
            } else {
                return tryChipFallback(actualTarget, tpRemaining);
            }
        }
        
        // FIXED: Don't call fallback weapons during scenario execution to prevent weapon switching loops
        if (mode == "target") {
            debugW("WEAPON FAIL: Skipping fallback to prevent weapon switching loop");
            return tpRemaining; // Return unchanged TP to indicate failure
        }
        
        return tryFallbackWeapons(tpRemaining, distance);
    }
    
    // Execute weapon attack(s)
    var maxUses = getWeaponMaxUses(weapon);
    var tpUses = floor(tpRemaining / weaponCost);
    var actualUses = (maxUses > 0) ? min(tpUses, maxUses) : tpUses;
    
    if (mode == "legacy") {
        actualUses = min(actualUses, 3); // Legacy mode limits
    }
    
    for (var use = 0; use < actualUses; use++) {
        if (tpRemaining < weaponCost || getLife(actualTarget) <= 0) break;
        
        if (debugEnabled) {
            debugW("WEAPON ATTACK: Using " + weapon + " on " + actualTarget + " (use " + (use + 1) + "/" + actualUses + ")");
        }
        
        useWeapon(actualTarget);
        recordWeaponUse(weapon);
        tpRemaining -= weaponCost;
        
        if (debugEnabled) {
            debugW("WEAPON SUCCESS: Used " + weapon + " (TP left: " + tpRemaining + ")");
        }
    }
    
    return tpRemaining;
}

function executeWeaponOnCell(weapon, targetCell, tpRemaining) {
    var weaponCost = getWeaponCost(weapon);
    var maxUses = getWeaponMaxUses(weapon);
    var actualUses = (maxUses > 0) ? min(floor(tpRemaining / weaponCost), maxUses) : floor(tpRemaining / weaponCost);
    
    for (var use = 0; use < actualUses; use++) {
        if (tpRemaining < weaponCost) break;
        
        if (debugEnabled) {
            debugW("CELL ATTACK: Using " + weapon + " on cell " + targetCell);
        }
        
        useWeapon(targetCell);
        recordWeaponUse(weapon);
        tpRemaining -= weaponCost;
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
        lastDoTApplicationTurn = getTurn(); // Track DoT application for cycle timing
        if (debugEnabled) {
            debugW("TOXIN cooldown set: 2 turns");
        }
    } else if (chip == CHIP_VENOM) {
        chipCooldowns[CHIP_VENOM] = 1; // 1 turn cooldown
        lastDoTApplicationTurn = getTurn(); // Track DoT application for cycle timing
        if (debugEnabled) {
            debugW("VENOM cooldown set: 1 turn");
        }
    }
    
    if (debugEnabled) {
        debugW("CHIP SUCCESS: Used " + chip + " on " + target + " (TP left: " + tpRemaining + ")");
    }
    
    return tpRemaining;
}

// === UNIFIED FALLBACK WEAPONS ===
function tryUnifiedFallbackWeapons(target, tpRemaining, distance, useTarget) {
    var weapons = getWeapons();
    
    if (debugEnabled) {
        var targetDesc = useTarget ? ("target " + target) : "enemies";
        debugW("FALLBACK: Checking " + count(weapons) + " weapons for " + targetDesc + " at distance " + distance);
    }
    
    // Create cache key
    var cacheKey = (useTarget ? target : "legacy") + "_" + distance;
    
    // Check cache
    if (weaponSwitchCache[cacheKey] != null) {
        var cachedWeapon = weaponSwitchCache[cacheKey];
        if (debugEnabled) {
            debugW("FALLBACK CACHE: Using cached weapon " + cachedWeapon + " for " + cacheKey);
        }
        
        var currentWeap = getWeapon();
        if (currentWeap != cachedWeapon) {
            setWeapon(cachedWeapon);
            tpRemaining--;
        }
        
        var testTarget = useTarget ? target : enemy;
        if (canUseWeapon(testTarget)) {
            useWeapon(testTarget);
            recordWeaponUse(cachedWeapon);
            tpRemaining -= getWeaponCost(cachedWeapon);
            if (debugEnabled) {
                debugW("FALLBACK CACHE SUCCESS: Used cached weapon " + cachedWeapon);
            }
            return tpRemaining;
        }
    }
    
    // Create weapon priority list
    var weaponPriority = [];
    var currentWeap = getWeapon();
    
    var weaponPriorityMap = [
        {weapon: WEAPON_ENHANCED_LIGHTNINGER, priority: 800},
        {weapon: WEAPON_RIFLE, priority: 600},
        {weapon: WEAPON_M_LASER, priority: 400},
        {weapon: WEAPON_SWORD, priority: 300},
        {weapon: WEAPON_KATANA, priority: 200}
    ];
    
    for (var i = 0; i < count(weapons); i++) {
        var weapon = weapons[i];
        var minRange = getWeaponMinRange(weapon);
        var maxRange = getWeaponMaxRange(weapon);
        var weaponCost = getWeaponCost(weapon);
        
        // Skip if weapon is not viable
        if (distance < minRange || distance > maxRange || tpRemaining < weaponCost + 1) {
            continue;
        }
        
        var priority = 100; // Default priority
        
        // Current weapon gets highest priority (no switch cost)
        if (weapon == currentWeap) {
            priority = 1000;
        } else {
            // Look up weapon in priority map
            for (var p = 0; p < count(weaponPriorityMap); p++) {
                if (weaponPriorityMap[p].weapon == weapon) {
                    priority = weaponPriorityMap[p].priority;
                    break;
                }
            }
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
        var needsSwitch = (currentWeap != weapon);
        var testTarget = useTarget ? target : enemy;
        
        if (debugEnabled) {
            debugW("FALLBACK: Testing weapon " + weapon + " (priority " + weaponInfo.priority + ")");
        }
        
        if (!needsSwitch) {
            if (canUseWeapon(testTarget)) {
                useWeapon(testTarget);
                recordWeaponUse(weapon);
                tpRemaining -= weaponCost;
                weaponSwitchCache[cacheKey] = weapon;
                if (debugEnabled) {
                    debugW("FALLBACK SUCCESS: Used equipped " + weapon);
                }
                return tpRemaining;
            }
        } else {
            setWeapon(weapon);
            tpRemaining--;
            
            if (canUseWeapon(testTarget)) {
                useWeapon(testTarget);
                recordWeaponUse(weapon);
                tpRemaining -= weaponCost;
                weaponSwitchCache[cacheKey] = weapon;
                if (debugEnabled) {
                    debugW("FALLBACK SUCCESS: Switched to " + weapon);
                }
                return tpRemaining;
            }
        }
    }
    
    // Try chips as last resort
    if (tpRemaining >= 4) {
        if (useTarget) {
            return executeChipActionOnTarget(CHIP_LIGHTNING, target, tpRemaining);
        } else {
            return executeChipAction(CHIP_LIGHTNING, tpRemaining);
        }
    }
    
    return tpRemaining;
}

// === COMPATIBILITY WRAPPER FUNCTIONS ===
function executeWeaponActionOnTarget(weapon, target, tpRemaining) {
    return executeUnifiedWeaponAction(weapon, target, tpRemaining, "target");
}

function executePreCalculatedWeapon(weaponId, target, tpRemaining) {
    return executeUnifiedWeaponAction(weaponId, target, tpRemaining, "precalc");
}

function executeWeaponAction(weapon, tpRemaining) {
    return executeUnifiedWeaponAction(weapon, null, tpRemaining, "legacy");
}

function tryFallbackWeaponsOnTarget(target, tpRemaining, distance) {
    return tryUnifiedFallbackWeapons(target, tpRemaining, distance, true);
}

function tryFallbackWeapons(tpRemaining, distance) {
    return tryUnifiedFallbackWeapons(null, tpRemaining, distance, false);
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
// Note: isWeapon() and isChip() are LeekScript built-in functions

// === CHIP FALLBACK SYSTEM ===
function tryChipFallback(target, tpRemaining) {
    if (debugEnabled) {
        debugW("CHIP FALLBACK: Trying chips with " + tpRemaining + " TP remaining");
    }
    
    // NO CHIP FALLBACK: AI should move to weapon range instead of using weak chips
    if (debugEnabled) {
        // No chip fallback - should move to weapon range
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

// This duplicate function has been removed - now uses tryUnifiedFallbackWeapons

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
            if (checkLineOfSight(myCell, getCell(enemyEntity))) {
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