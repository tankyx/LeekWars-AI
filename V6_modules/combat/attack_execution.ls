// V6 Module: combat/attack_execution.ls
// Core attack execution and combat logic
// Refactored from execute_combat.ls for better modularity

// Include required modules
include("weapon_selection");
include("positioning_logic");
include("damage_sequences");
include("grenade_tactics");
include("m_laser_tactics");


// Function: executeAttackSequence
// Main attack execution - refactored from executeAttack()
function executeAttackSequence() {
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("executeAttackSequence called - enemy=" + enemy + ", myTP=" + myTP);
    }
    
    if (enemy == null || myTP < 1) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("executeAttackSequence early return - enemy null or no TP");
        }
        return;
    }

    var dist = getCellDistance(myCell, enemyCell);
    var hasLine = hasLOS(myCell, enemyCell);
    
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Combat range=" + dist + ", hasLOS=" + hasLine);
    }
    
    // Check for optimal damage sequence first
    var optimalSequence = checkOptimalDamageSequence(dist);
    if (optimalSequence == true) {
        return; // Optimal sequence executed
    }
    
    // Evaluate positioning needs
    var positioningInfo = evaluateCombatPositioning(dist, hasLine, myMP, getWeapons());
    if (positioningInfo != null) {
        var positioned = executePositioning(positioningInfo);
        if (positioned) {
            // Update distance after repositioning
            dist = getCellDistance(myCell, enemyCell);
            hasLine = hasLOS(myCell, enemyCell);
        }
    }
    
    // Build attack options
    var attackOptions = buildAttackOptions(myTP, dist, hasLine);
    
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Attack options available: " + count(attackOptions) + " at range " + dist + " with TP=" + myTP);
    }
    
    // Handle movement if no good attack options
    var movementResult = handleMovementFallback(attackOptions, dist, hasLine);
    if (movementResult) {
        // Rebuild options after movement
        dist = getCellDistance(myCell, enemyCell);
        hasLine = hasLOS(myCell, enemyCell);
        attackOptions = buildAttackOptions(myTP, dist, hasLine);
    }
    
    // Execute attacks
    executeAttackOptions(attackOptions);
}

// Function: checkOptimalDamageSequence
// Check for and execute optimal damage sequences
function checkOptimalDamageSequence(distance) {
    var mySTR = getStrength();
    var darkKatanaSelfDmg = 44 * (1 + mySTR / 100);
    var optimalSequence = getBestDamageSequence(myTP, distance, myHP, mySTR);
    
    if (optimalSequence != null && optimalSequence[2] >= getLife(enemy) * 0.5) {
        // If sequence can deal 50%+ enemy HP, execute it
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Using optimal damage sequence: " + optimalSequence[4]);
        }

        var dmgDealt = executeDamageSequence(optimalSequence, enemy);
        if (dmgDealt > 0) {
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("Sequence executed for " + dmgDealt + " damage");
            }
            return true;
        }
    }
    
    return false;
}

// Function: handleMovementFallback
// Handle movement when no good attack options are available
function handleMovementFallback(attackOptions, distance, hasLine) {
    // Check if we only have chip options but could move to weapon range
    var hasWeaponOptions = false;
    var hasOnlyChipOptions = false;
    
    for (var i = 0; i < count(attackOptions); i++) {
        if (attackOptions[i][0] == "weapon") {
            hasWeaponOptions = true;
            break;
        }
    }
    
    if (count(attackOptions) > 0 && !hasWeaponOptions) {
        hasOnlyChipOptions = true;
    }
    
    if (count(attackOptions) == 0 || (hasOnlyChipOptions && getMP() > 0 && distance > 12)) {
        if (count(attackOptions) == 0) {
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("WARNING: No attack options - checking weapons: " + count(getWeapons()));
            }
        } else {
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("Only chip options available, but can move to weapon range - prioritizing movement");
            }
        }
        
        // Move for better positioning  
        if (getMP() > 0) {
            var shouldReposition = false;
            var repositionReason = "";
            
            if (distance > 12) {
                shouldReposition = true;
                repositionReason = "Out of attack range - moving closer";
            } else if (!hasLine) {
                shouldReposition = true;
                repositionReason = "No line of sight - repositioning for better angle";
            } else if (distance >= 10 && distance <= 12 && hasLine && !isOnSameLine(myCell, enemyCell)) {
                // AGGRESSIVE REPOSITIONING: In M-Laser range but no line alignment
                // Move to Rifle range (7-9) for guaranteed weapon availability
                shouldReposition = true;
                repositionReason = "M-Laser range without alignment - moving to Rifle range 7-9";
            }
            
            if (shouldReposition) {
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog(repositionReason);
                }
                
                // Smart target distance based on situation  
                var targetDist = 8; // Default optimal range
                if (distance > 15) {
                    targetDist = 10; // Conservative approach from very far
                } else {
                    targetDist = 8; // Center of Rifle range (7-9)
                }
                
                moveToward(enemy, min(getMP(), distance - targetDist));
                updatePositionAfterMovement();
            }
            
            // Clear chip-only options since we moved
            if (hasOnlyChipOptions) {
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Clearing chip options after movement - will reevaluate weapons next turn");
                }
            }
            
            return true;
        }
    }
    
    return false;
}

// Function: executeAttackOptions
// Execute the selected attack options
function executeAttackOptions(attackOptions) {
    if (count(attackOptions) == 0) {
        // Fallback attack attempt
        executeFallbackAttack();
        return;
    }

    var tpLeft = myTP;
    var totalDamage = 0;
    var currentWeapon = getWeapon();
    
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Starting attack execution - " + count(attackOptions) + " options, TP=" + tpLeft);
    }
    
    for (var i = 0; i < count(attackOptions); i++) {
        var option = attackOptions[i];
        // Array indices: 0=type, 1=item, 2=damage, 3=cost, 4=dptp, 5=maxUses, 6=name
        
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Processing attack option " + i + ": " + option[6] + " (dptp: " + option[4] + ", damage: " + option[2] + ")");
        }
        
        if (tpLeft < option[3]) continue; // Not enough TP
        
        var uses = min(option[5], floor(tpLeft / option[3]));
        if (uses <= 0) continue;
        
        // Check weapon switching efficiency and pre-validate
        if (option[0] == "weapon") {
            var weaponId = option[1];
            var needsSwap = (currentWeapon != weaponId);
            
            // Pre-switch validation to prevent wasting TP
            var canFire = true;
            var skipReason = "";
            
            // Check if weapon can actually fire before switching
            if (weaponId == WEAPON_MAGNUM || weaponId == WEAPON_B_LASER || weaponId == WEAPON_LASER || weaponId == WEAPON_FLAME_THROWER) {
                // Direct fire weapons need LOS
                if (!hasLOS(myCell, enemyCell)) {
                    canFire = false;
                    skipReason = "no line of sight";
                }
            } else if (weaponId == WEAPON_GRENADE_LAUNCHER) {
                // Grenade Launcher can always fire (direct or indirect)
                canFire = true;
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Grenade Launcher pre-validation: can fire (direct/indirect)");
                }
            }
            
            // Check alignment for line weapons
            if (canFire && (weaponId == WEAPON_B_LASER || weaponId == WEAPON_M_LASER || weaponId == WEAPON_LASER || weaponId == WEAPON_FLAME_THROWER)) {
                if (!isOnSameLine(myCell, enemyCell)) {
                    canFire = false;
                    skipReason = "not aligned for line weapon";
                }
            }
            
            if (!canFire) {
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Skipping " + option[6] + " - " + skipReason);
                }
                continue;
            }
            
            if (needsSwap && totalDamage > 0 && tpLeft < (option[3] + 1)) {
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Skipping " + option[6] + " - would require weapon switch with insufficient TP");
                }
                continue;
            }

            var damageDealt = executeWeaponAttacks(option, uses);
            totalDamage += damageDealt;
            tpLeft = getTP();
            currentWeapon = option[1];
            
        } else if (option[0] == "chip") {
            var chipResult = executeChipAttack(option[1]);
            if (chipResult > 0) {
                totalDamage += chipResult;
                tpLeft = getTP();
            }
        }
        
        // Check if enemy is dead
        if (getLife(enemy) <= 0) {
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("Enemy eliminated with " + totalDamage + " total damage");
            }
            
            // Enhanced Lightninger passive: +1 TP per entity killed
            var weapons = getWeapons();
            if (inArray(weapons, WEAPON_ENHANCED_LIGHTNINGER)) {
                // Add 1 TP for the kill (LeekScript doesn't have direct setTP, but the passive works automatically)
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Enhanced Lightninger passive: +1 TP for kill");
                }
            }
            
            break;
        }
        
        // Operation limit check
        if (!canSpendOps(10000)) {
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("Operation limit reached, ending attack sequence");
            }
            break;
        }
    }
    
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Attack execution complete - " + totalDamage + " total damage dealt");
    }
}

// Function: executeWeaponAttacks
// Execute weapon attacks
function executeWeaponAttacks(weaponOption, uses) {
    var weaponId = weaponOption[1];
    var weaponName = weaponOption[6];
    var totalDamage = 0;
    
    switchToWeaponIfNeeded(weaponId);
    
    // Special handling for AoE weapons - but prefer direct fire for Grenade Launcher when possible
    var useDirectFire = true;
    if (weaponId == WEAPON_GRENADE_LAUNCHER) {
        // Use direct fire if in LOS, AoE if not
        useDirectFire = hasLOS(myCell, enemyCell);
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Grenade Launcher: using " + (useDirectFire ? "direct" : "AoE") + " fire");
        }
    } else if (weaponId == WEAPON_M_LASER) {
        // M-Laser always uses direct fire when aligned
        useDirectFire = true;
    }
    
    if (!useDirectFire && isAoEWeapon(weaponId)) {
        var targetInfo = findBestAoETarget(weaponId);
        if (targetInfo != null) {
            var targetCell = (weaponId == WEAPON_GRENADE_LAUNCHER) ? targetInfo["targetCell"] : targetInfo;
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("Attempting AoE fire at cell " + targetCell + " with " + weaponName);
            }
            var result = useWeaponOnCell(targetCell);
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("AoE fire result: " + result + " for " + weaponName);
            }
            if (result == USE_SUCCESS || result == USE_CRITICAL) {
                var estimatedDamage = weaponOption[2] / uses;
                totalDamage += estimatedDamage;
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("AoE " + weaponName + " fired at cell " + targetCell + " for " + estimatedDamage + " damage");
                }
            }
        }
    } else {
        // Direct targeting
        for (var u = 0; u < uses && myTP >= getWeaponCost(weaponId); u++) {
            var result;
            if (weaponId == WEAPON_GRENADE_LAUNCHER) {
                // Grenade Launcher always targets cells, even in direct fire
                result = useWeaponOnCell(enemyCell);
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Direct Grenade fire at enemy cell " + enemyCell);
                }
            } else if (weaponId == WEAPON_ENHANCED_LIGHTNINGER) {
                // Enhanced Lightninger always targets cells for AoE + healing
                result = useWeaponOnCell(enemyCell);
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Enhanced Lightninger AoE at enemy cell " + enemyCell);
                }
            } else {
                result = useWeapon(enemy);
            }
            if (result == USE_SUCCESS) {
                var estimatedDamage = weaponOption[2] / uses;
                totalDamage += estimatedDamage;
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Used weapon " + weaponName + " for " + getWeaponCost(weaponId) + " TP");
                }
                
                // Track weapon usage for max uses per turn management
                if (weaponId == WEAPON_MAGNUM) {
                    magnumUsesRemaining--;
                    if (debugEnabled && canSpendOps(1000)) {
                        debugLog("Magnum uses remaining: " + magnumUsesRemaining);
                    }
                } else if (weaponId == WEAPON_B_LASER) {
                    bLaserUsesRemaining--;
                    if (debugEnabled && canSpendOps(1000)) {
                        debugLog("B-Laser uses remaining: " + bLaserUsesRemaining);
                    }
                } else if (weaponId == WEAPON_ENHANCED_LIGHTNINGER) {
                    enhancedLightningerUsesRemaining--;
                    if (debugEnabled && canSpendOps(1000)) {
                        debugLog("Enhanced Lightninger uses remaining: " + enhancedLightningerUsesRemaining);
                    }
                } else if (weaponId == WEAPON_KATANA) {
                    katanaUsesRemaining--;
                    if (debugEnabled && canSpendOps(1000)) {
                        debugLog("Katana uses remaining: " + katanaUsesRemaining);
                    }
                }
                
            } else if (result == USE_CRITICAL) {
                var estimatedDamage = weaponOption[2] / uses * 1.3; // Critical bonus
                totalDamage += estimatedDamage;
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Used weapon " + weaponName + " for " + getWeaponCost(weaponId) + " TP (CRIT!)");
                }
                
                // Track weapon usage for max uses per turn management
                if (weaponId == WEAPON_MAGNUM) {
                    magnumUsesRemaining--;
                    if (debugEnabled && canSpendOps(1000)) {
                        debugLog("Magnum uses remaining: " + magnumUsesRemaining);
                    }
                } else if (weaponId == WEAPON_B_LASER) {
                    bLaserUsesRemaining--;
                    if (debugEnabled && canSpendOps(1000)) {
                        debugLog("B-Laser uses remaining: " + bLaserUsesRemaining);
                    }
                } else if (weaponId == WEAPON_ENHANCED_LIGHTNINGER) {
                    enhancedLightningerUsesRemaining--;
                    if (debugEnabled && canSpendOps(1000)) {
                        debugLog("Enhanced Lightninger uses remaining: " + enhancedLightningerUsesRemaining);
                    }
                } else if (weaponId == WEAPON_KATANA) {
                    katanaUsesRemaining--;
                    if (debugEnabled && canSpendOps(1000)) {
                        debugLog("Katana uses remaining: " + katanaUsesRemaining);
                    }
                }
                
            } else {
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Weapon attack failed: " + result + " for " + weaponName);
                }
                break;
            }
        }
    }
    
    return totalDamage;
}

// Function: executeChipAttack
// Execute chip attack
function executeChipAttack(chipId) {
    var result = 0;
    var chipName = getChipName(chipId);
    
    if (chipId == CHIP_SPARK || chipId == CHIP_LIGHTNING) {
        var useResult = useChip(chipId, enemy);
        if (useResult == USE_SUCCESS || useResult == USE_CRITICAL) {
            result = calculateChipDamage(chipId, getStrength());
            if (debugEnabled && canSpendOps(1000)) {
                debugLog(chipName + " chip used successfully");
            }
        }
    }
    
    return result;
}

// Function: isAoEWeapon
// Check if weapon is Area of Effect
function isAoEWeapon(weaponId) {
    return (weaponId == WEAPON_GRENADE_LAUNCHER || weaponId == WEAPON_M_LASER || weaponId == WEAPON_ENHANCED_LIGHTNINGER);
}

// Function: findBestAoETarget
// Find best cell for AoE weapon
function findBestAoETarget(weaponId) {
    if (weaponId == WEAPON_GRENADE_LAUNCHER) {
        return findBestGrenadeTarget(myCell);
    } else if (weaponId == WEAPON_M_LASER) {
        return findBestMLaserTarget();
    } else if (weaponId == WEAPON_ENHANCED_LIGHTNINGER) {
        return findBestEnhancedLightningerTarget();
    }
    
    return enemyCell; // Fallback to direct targeting
}

// Function: executeFallbackAttack
// Fallback attack when no options are available
function executeFallbackAttack() {
    if (myTP < 3) return;
    
    var dist = getCellDistance(myCell, enemyCell);
    var hasLine = hasLOS(myCell, enemyCell);
    
    if (dist > 10 || !hasLine) return; // Can't attack
    
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("FALLBACK: Forcing attack attempt");
    }
    
    var weapons = getWeapons();
    for (var w = 0; w < count(weapons); w++) {
        var weapon = weapons[w];
        var minR = getWeaponMinRange(weapon);
        var maxR = getWeaponMaxRange(weapon);
        var cost = getWeaponCost(weapon);
        
        if (dist >= minR && dist <= maxR && myTP >= cost) {
            setWeaponIfNeeded(weapon);
            var result = useWeapon(enemy);
            if (result == USE_SUCCESS || result == USE_CRITICAL) {
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Fallback attack succeeded with " + getWeaponName(weapon));
                }
                break;
            } else {
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Fallback failed: " + result + " for " + getWeaponName(weapon));
                }
            }
        }
    }
}

// Function: updatePositionAfterMovement
// Update position variables after movement
function updatePositionAfterMovement() {
    myCell = getCell();
    myMP = getMP();
    enemyCell = getCell(enemy);
    enemyDistance = getCellDistance(myCell, enemyCell);
    var newLOS = hasLOS(myCell, enemyCell);
    
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Repositioned - new distance: " + enemyDistance + ", new LOS: " + newLOS);
    }
}

// Function: findBestEnhancedLightningerTarget
// Find best target cell for Enhanced Lightninger 3x3 AoE
function findBestEnhancedLightningerTarget() {
    // Enhanced Lightninger has range 6-10 and 3x3 square area
    var distance = getCellDistance(myCell, enemyCell);
    
    if (distance < 6 || distance > 10) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Enhanced Lightninger out of range: " + distance + " (need 6-10)");
        }
        return null; // Out of range
    }
    
    // Check if we have line of sight to enemy cell
    if (hasLOS(myCell, enemyCell)) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Enhanced Lightninger direct target: enemy at " + enemyCell);
        }
        return enemyCell; // Direct targeting is best
    }
    
    // If no direct LOS, look for cells around enemy that we can target
    var enemyX = getCellX(enemyCell);
    var enemyY = getCellY(enemyCell);
    
    // Check all cells in 3x3 area around enemy for targeting
    var bestTarget = null;
    var bestScore = -1;
    
    for (var dx = -1; dx <= 1; dx++) {
        for (var dy = -1; dy <= 1; dy++) {
            var targetCell = getCellFromXY(enemyX + dx, enemyY + dy);
            if (targetCell == null || targetCell == -1) continue;
            
            var targetDistance = getCellDistance(myCell, targetCell);
            if (targetDistance < 6 || targetDistance > 10) continue;
            
            if (hasLOS(myCell, targetCell)) {
                // Calculate how many enemies this position might hit
                var score = 1; // Base score for hitting primary enemy
                
                // Bonus for hitting multiple enemies if in team battle
                if (count(allEnemies) > 1) {
                    for (var e = 0; e < count(allEnemies); e++) {
                        var enemyEntity = allEnemies[e];
                        var enemyPos = getCell(enemyEntity);
                        var hitDistance = getCellDistance(targetCell, enemyPos);
                        if (hitDistance <= 1) { // Within 3x3 area (distance 1 from center)
                            score += 1;
                        }
                    }
                }
                
                // Prefer closer targets for accuracy
                score += (11 - targetDistance) * 0.1;
                
                if (score > bestScore) {
                    bestScore = score;
                    bestTarget = targetCell;
                }
            }
        }
    }
    
    if (bestTarget != null) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Enhanced Lightninger indirect target: " + bestTarget + " (score: " + bestScore + ")");
        }
        return bestTarget;
    }
    
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Enhanced Lightninger: no valid target found");
    }
    return null;
}