// ===================================================================
// V6 B-LASER BUILD - COMBAT EXECUTION MODULE
// ===================================================================

// Include generic laser tactics for multi-hit support
include("../combat/laser_tactics_generic");

function executeAttackBLaser() {
    if (enemy == null || myTP <= 0) return;
    
    debugLog("Executing B-Laser combat sequence");
    
    // Update position before combat
    updatePositionBLaser();
    
    // Phase 1: Apply defensive buffs if needed
    if (myHP < myMaxHP * SHIELD_THRESHOLD && myTP >= 4 && !hasSolidification) {
        if (canUseChip(CHIP_SOLIDIFICATION, getEntity())) {
            useChip(CHIP_SOLIDIFICATION, getEntity());
            myTP -= 4;
            hasSolidification = true;
            debugLog("Applied Solidification shield");
        }
    }
    
    // Phase 2: Position optimization
    if (myMP > 0) {
        var optimalCell = findOptimalAttackPosition();
        if (optimalCell != null && optimalCell != myCell) {
            var path = getPath(myCell, optimalCell);
            if (path != null && count(path) <= myMP) {
                moveToward(optimalCell, myMP);
                updatePositionBLaser();
                debugLog("Moved to optimal position");
            }
        }
    }
    
    // Phase 3: Execute weapon attacks
    var attackSequence = calculateBestAttackSequence();
    executeBLaserSequence(attackSequence);
    
    // Phase 4: Use remaining TP for chip damage
    if (myTP >= 2 && enemyDistance <= 6 && canUseChip(CHIP_SPARK, enemy)) {
        useChip(CHIP_SPARK, enemy);
        myTP -= 2;
        debugLog("Spark chip bonus damage");
    }
    
    // Phase 5: Final repositioning
    if (myMP > 0) {
        if (myHP < myMaxHP * 0.4) {
            // Low health - create distance
            moveAwayFrom(enemy, myMP);
            debugLog("Defensive repositioning");
        } else if (enemyDistance > OPTIMAL_RANGE_BLASER) {
            // Close gap for next turn
            moveToward(enemy, min(myMP, enemyDistance - OPTIMAL_RANGE_BLASER));
            debugLog("Aggressive repositioning");
        }
    }
}

function findOptimalAttackPosition() {
    // Find best cell for attack considering all weapons
    var bestCell = myCell;
    var bestScore = evaluateAttackPosition(myCell);
    
    // Check reachable cells
    var reachableCells = getReachableCells(myCell, myMP);
    for (var cell in reachableCells) {
        var score = evaluateAttackPosition(cell);
        if (score > bestScore) {
            bestScore = score;
            bestCell = cell;
        }
    }
    
    return bestCell;
}

function evaluateAttackPosition(cell) {
    if (enemy == null) return 0;
    
    var score = 0;
    var dist = getCellDistance(cell, enemyCell);
    
    // Use generic laser position evaluation for B-Laser
    if (dist >= B_LASER_MIN_RANGE && dist <= B_LASER_MAX_RANGE) {
        var laserScore = evaluateLaserPosition(WEAPON_B_LASER, B_LASER_MIN_RANGE, B_LASER_MAX_RANGE, cell, enemies);
        score += laserScore;
    }
    
    // Destroyer range bonus
    if (dist >= DESTROYER_MIN_RANGE && dist <= DESTROYER_MAX_RANGE) {
        score += 500;
    }
    
    // Magnum range bonus
    if (dist >= MAGNUM_MIN_RANGE && dist <= MAGNUM_MAX_RANGE) {
        score += 300;
    }
    
    // Optimal distance bonus
    var optimalDist = abs(dist - OPTIMAL_RANGE_BLASER);
    score -= optimalDist * 50;
    
    // Safety consideration (use existing EID if available)
    if (getOperations() < maxOperations - 100000) {
        var eid = calculateEID(cell);
        score -= eid * 2;
    }
    
    return score;
}

function calculateBestAttackSequence() {
    var sequence = [];
    var remainingTP = myTP;
    
    // Calculate damage potential for each weapon
    var weapons = [];
    
    // B-Laser evaluation - find best target line for multi-hits
    if (bLaserUsesRemaining > 0 && remainingTP >= B_LASER_COST) {
        var bestLaserTarget = findBestBLaserTarget();
        if (bestLaserTarget != null) {
            var bLaserDmg = getWeaponDamage(WEAPON_B_LASER, bestLaserTarget["target"]);
            var bLaserHeal = 55 * (1 + myWisdom / 100);
            var needHeal = (myHP < myMaxHP * HEAL_THRESHOLD) ? bLaserHeal : 0;
            var multiHit = bestLaserTarget["hits"];
            
            var weaponData = [:];
            weaponData["weapon"] = WEAPON_B_LASER;
            weaponData["priority"] = (bLaserDmg * multiHit) + needHeal;
            weaponData["cost"] = B_LASER_COST;
            weaponData["uses"] = bLaserUsesRemaining;
            weaponData["target"] = bestLaserTarget["target"];
            weaponData["targetCell"] = bestLaserTarget["targetCell"];
            push(weapons, weaponData);
        }
    }
    
    // Destroyer evaluation
    if (destroyerUsesRemaining > 0 && remainingTP >= DESTROYER_COST) {
        if (enemyDistance >= DESTROYER_MIN_RANGE && enemyDistance <= DESTROYER_MAX_RANGE) {
            var destroyerDmg = getWeaponDamage(WEAPON_DESTROYER, enemy);
            var weaponData = [:];
            weaponData["weapon"] = WEAPON_DESTROYER;
            weaponData["priority"] = destroyerDmg;
            weaponData["cost"] = DESTROYER_COST;
            weaponData["uses"] = destroyerUsesRemaining;
            push(weapons, weaponData);
        }
    }
    
    // Magnum evaluation
    if (magnumUsesRemaining > 0 && remainingTP >= MAGNUM_COST) {
        if (enemyDistance >= MAGNUM_MIN_RANGE && enemyDistance <= MAGNUM_MAX_RANGE) {
            var magnumDmg = getWeaponDamage(WEAPON_MAGNUM, enemy);
            var weaponData = [:];
            weaponData["weapon"] = WEAPON_MAGNUM;
            weaponData["priority"] = magnumDmg;
            weaponData["cost"] = MAGNUM_COST;
            weaponData["uses"] = magnumUsesRemaining;
            push(weapons, weaponData);
        }
    }
    
    // Sort by priority (manual sort since LeekScript doesn't support lambdas)
    for (var i = 0; i < count(weapons) - 1; i++) {
        for (var j = i + 1; j < count(weapons); j++) {
            if (weapons[j]["priority"] > weapons[i]["priority"]) {
                var temp = weapons[i];
                weapons[i] = weapons[j];
                weapons[j] = temp;
            }
        }
    }
    
    // Build sequence
    for (var w in weapons) {
        var uses = 0;
        while (remainingTP >= w["cost"] && uses < w["uses"]) {
            push(sequence, w["weapon"]);
            remainingTP -= w["cost"];
            uses++;
        }
    }
    
    return sequence;
}

function executeBLaserSequence(sequence) {
    for (var weaponData in sequence) {
        if (enemy == null || getLife(enemy) <= 0) break;
        
        var weapon = weaponData;
        var targetCell = enemyCell;
        
        // Handle weapon data objects for B-Laser with custom targets
        if (typeOf(weaponData) == TYPE_ARRAY) {
            weapon = weaponData["weapon"];
            if (weaponData["targetCell"] != null) {
                targetCell = weaponData["targetCell"];
            }
        }
        
        if (weapon == WEAPON_B_LASER) {
            setWeapon(WEAPON_B_LASER);
            if (useWeaponOnCell(targetCell) == USE_SUCCESS) {
                myTP -= B_LASER_COST;
                bLaserUsesRemaining--;
                debugLog("B-Laser fired (heal + damage) - multi-hit!");
            }
        } else if (weapon == WEAPON_DESTROYER) {
            setWeapon(WEAPON_DESTROYER);
            if (useWeapon(enemy) == USE_SUCCESS) {
                myTP -= DESTROYER_COST;
                destroyerUsesRemaining--;
                debugLog("Destroyer fired");
            }
        } else if (weapon == WEAPON_MAGNUM) {
            setWeapon(WEAPON_MAGNUM);
            if (useWeapon(enemy) == USE_SUCCESS) {
                myTP -= MAGNUM_COST;
                magnumUsesRemaining--;
                debugLog("Magnum fired");
            }
        }
        
        // Update TP after each shot
        myTP = getTP();
    }
}

function findBestBLaserTarget() {
    // Use generic laser function for B-Laser
    return findBestLaserTargetGeneric(WEAPON_B_LASER, myCell, B_LASER_MIN_RANGE, B_LASER_MAX_RANGE, enemies);
}

function countLaserHits(fromCell, targetCell) {
    // Use generic laser hit counting
    var hitData = countLaserHitsGeneric(fromCell, targetCell, B_LASER_MIN_RANGE, B_LASER_MAX_RANGE, enemies);
    return hitData["count"];
}

function shouldRepositionForBLaser() {
    // Check if we should move for better B-Laser positioning
    return shouldRepositionForLaser(WEAPON_B_LASER, B_LASER_MIN_RANGE, B_LASER_MAX_RANGE, myCell, myMP, enemies);
}

debugLog("B-Laser combat execution module loaded");