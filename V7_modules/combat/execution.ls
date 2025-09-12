// V7 Module: combat/execution.ls
// Scenario-based combat execution

// === MAIN COMBAT EXECUTION ===
function executeCombat(fromCell) {
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

// === WEAPON EXECUTION ===
function executeWeaponAction(weapon, tpRemaining) {
    if (debugEnabled) {
        debugW("WEAPON EXEC: Trying weapon " + weapon + " with " + tpRemaining + " TP, enemy " + enemy);
    }
    
    var weaponCost = getWeaponCost(weapon);
    
    // Switch weapon if needed
    if (getWeapon() != weapon) {
        if (tpRemaining < weaponCost + 1) {
            if (debugEnabled) {
                debugW("WEAPON FAIL: Not enough TP to switch weapons (need " + (weaponCost + 1) + ", have " + tpRemaining + ")");
            }
            return tpRemaining;
        }
        setWeapon(weapon);
        tpRemaining--;
        if (debugEnabled) {
            debugW("Switched to weapon " + weapon);
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
            var cells = getCellsAtDistance(enemyCell, r);
            
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
    var affectedCells = getCellsAtDistance(targetCell, area);
    
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
           action == WEAPON_FLAME_THROWER || action == WEAPON_GRENADE_LAUNCHER || 
           action == WEAPON_B_LASER || action == WEAPON_LASER ||
           action == WEAPON_RHINO;
}

function isChip(action) {
    return action >= 400; // Chip constants are 400+
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
    var currentWeapon = getWeapon();
    var tpCost = 0;
    
    for (var i = 0; i < count(scenario); i++) {
        var action = scenario[i];
        
        if (isWeapon(action)) {
            if (currentWeapon != action) {
                tpCost += 1; // Weapon switch cost
                currentWeapon = action;
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