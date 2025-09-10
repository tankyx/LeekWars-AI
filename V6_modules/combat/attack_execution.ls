// V6 Module: combat/attack_execution.ls
// Core attack execution and combat logic
// Refactored from execute_combat.ls for better modularity

// Include required modules
include("weapon_selection");
include("positioning_logic");
include("damage_sequences");
include("grenade_tactics");
include("m_laser_tactics");

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

// Function: executeAttackSequence
// Main attack execution - refactored from executeAttack()

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

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
    

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var dist = getCellDistance(myCell, enemyCell);

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var hasLine = hasLOS(myCell, enemyCell);
    
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Combat range=" + dist + ", hasLOS=" + hasLine);
    }
    
    // Check for optimal damage sequence first

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var optimalSequence = checkOptimalDamageSequence(dist);
    if (optimalSequence == true) {
        return; // Optimal sequence executed
    }
    
    // Evaluate positioning needs

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var positioningInfo = evaluateCombatPositioning(dist, hasLine, myMP, getWeapons());
    if (positioningInfo != null) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

        var positioned = executePositioning(positioningInfo);
        if (positioned) {
            // Update distance after repositioning
            dist = getCellDistance(myCell, enemyCell);
            hasLine = hasLOS(myCell, enemyCell);
        }
    }
    
    // Build attack options

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var attackOptions = buildAttackOptions(myTP, dist, hasLine);
    
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Attack options available: " + count(attackOptions) + " at range " + dist + " with TP=" + myTP);
    }
    
    // Handle movement if no good attack options

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

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

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

function checkOptimalDamageSequence(distance) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var mySTR = getStrength();

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var darkKatanaSelfDmg = 44 * (1 + mySTR / 100);

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var optimalSequence = getBestDamageSequence(myTP, distance, myHP, mySTR);
    
    if (optimalSequence != null && optimalSequence[2] >= getLife(enemy) * 0.5) {
        // If sequence can deal 50%+ enemy HP, execute it
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Using optimal damage sequence: " + optimalSequence[4]);
        }

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

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

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

function handleMovementFallback(attackOptions, distance, hasLine) {
    // Check if we only have chip options but could move to weapon range

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var hasWeaponOptions = false;

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

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

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

function executeAttackOptions(attackOptions) {
    if (count(attackOptions) == 0) {
        // Fallback attack attempt
        executeFallbackAttack();
        return;
    }
    

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var tpLeft = myTP;

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var totalDamage = 0;

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var currentWeapon = getWeapon();
    
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Starting attack execution - " + count(attackOptions) + " options, TP=" + tpLeft);
    }
    
    for (var i = 0; i < count(attackOptions); i++) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

        var option = attackOptions[i];
        // Array indices: 0=type, 1=item, 2=damage, 3=cost, 4=dptp, 5=maxUses, 6=name
        
        if (tpLeft < option[3]) continue; // Not enough TP
        

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

        var uses = min(option[5], floor(tpLeft / option[3]));
        if (uses <= 0) continue;
        
        // Check weapon switching efficiency
        if (option[0] == "weapon") {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

            var needsSwap = (currentWeapon != option[1]);
            if (needsSwap && totalDamage > 0 && tpLeft < (option[3] + 1)) {
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Skipping " + option[6] + " - would require weapon switch with insufficient TP");
                }
                continue;
            }
            

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

            var damageDealt = executeWeaponAttacks(option, uses);
            totalDamage += damageDealt;
            tpLeft = getTP();
            currentWeapon = option[1];
            
        } else if (option[0] == "chip") {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

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

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

function executeWeaponAttacks(weaponOption, uses) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var weaponId = weaponOption[1];

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var weaponName = weaponOption[6];

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var totalDamage = 0;
    
    switchToWeaponIfNeeded(weaponId);
    
    // Special handling for AoE weapons
    if (isAoEWeapon(weaponId)) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

        var targetCell = findBestAoETarget(weaponId);
        if (targetCell != null) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

            var result = useWeaponOnCell(targetCell);
            if (result == USE_SUCCESS || result == USE_CRITICAL) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

                var estimatedDamage = weaponOption[2] / uses;
                totalDamage += estimatedDamage;
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("AoE " + weaponName + " fired at cell " + targetCell);
                }
            }
        }
    } else {
        // Direct targeting
        for (var u = 0; u < uses && myTP >= getWeaponCost(weaponId); u++) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

            var result = useWeapon(enemy);
            if (result == USE_SUCCESS) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

                var estimatedDamage = weaponOption[2] / uses;
                totalDamage += estimatedDamage;
            } else if (result == USE_CRITICAL) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

                var estimatedDamage = weaponOption[2] / uses * 1.3; // Critical bonus
                totalDamage += estimatedDamage;
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("CRITICAL " + weaponName + " hit!");
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

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

function executeChipAttack(chipId) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var result = 0;

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var chipName = getChipName(chipId);
    
    if (chipId == CHIP_SPARK || chipId == CHIP_LIGHTNING) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

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

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

function isAoEWeapon(weaponId) {
    return (weaponId == WEAPON_GRENADE_LAUNCHER || weaponId == WEAPON_M_LASER);
}

// Function: findBestAoETarget
// Find best cell for AoE weapon

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

function findBestAoETarget(weaponId) {
    if (weaponId == WEAPON_GRENADE_LAUNCHER) {
        return findBestGrenadeTarget(myCell);
    } else if (weaponId == WEAPON_M_LASER) {
        return findBestMLaserTarget();
    }
    
    return enemyCell; // Fallback to direct targeting
}

// Function: executeFallbackAttack
// Fallback attack when no options are available

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

function executeFallbackAttack() {
    if (myTP < 3) return;
    

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var dist = getCellDistance(myCell, enemyCell);

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var hasLine = hasLOS(myCell, enemyCell);
    
    if (dist > 10 || !hasLine) return; // Can't attack
    
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("FALLBACK: Forcing attack attempt");
    }
    

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var weapons = getWeapons();
    for (var w = 0; w < count(weapons); w++) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

        var weapon = weapons[w];

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

        var minR = getWeaponMinRange(weapon);

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

        var maxR = getWeaponMaxRange(weapon);

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

        var cost = getWeaponCost(weapon);
        
        if (dist >= minR && dist <= maxR && myTP >= cost) {
            setWeaponIfNeeded(weapon);

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

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

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

function updatePositionAfterMovement() {
    myCell = getCell();
    myMP = getMP();
    enemyCell = getCell(enemy);
    enemyDistance = getCellDistance(myCell, enemyCell);

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var newLOS = hasLOS(myCell, enemyCell);
    
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Repositioned - new distance: " + enemyDistance + ", new LOS: " + newLOS);
    }
}