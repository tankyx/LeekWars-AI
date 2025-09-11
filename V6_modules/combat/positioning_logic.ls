// V6 Module: combat/positioning_logic.ls
// Combat positioning and movement logic
// Refactored from execute_combat.ls for better modularity
// Fixed: All field access using bracket notation for associative arrays

// Include required modules


// Function: evaluateCombatPositioning
// Evaluate if we should reposition before attacking


function evaluateCombatPositioning(currentDistance, hasLineOfSight, availableMP, availableWeapons) {
    if (availableMP == 0) {
        return null; // Can't move
    }
    
    var currentDamage = calculatePositionDamage(myCell, availableWeapons);


    var shouldReposition = false;


    var repositionReason = "";
    
    // Check for optimal weapon positioning


    var positioningNeeds = analyzePositioningNeeds(currentDistance, hasLineOfSight, availableWeapons);
    
    if (positioningNeeds["needsRepositioning"]) {
        shouldReposition = true;
        repositionReason = positioningNeeds["reason"];
        
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Positioning needed: " + repositionReason);
        }
    }
    // Find best position within movement range
    if (shouldReposition) {
        // Looking for better position - debug removed to reduce spam


        var bestPosition = findOptimalAttackPosition(availableMP, availableWeapons);
        if (bestPosition != null && bestPosition != myCell) {
            // Found position - debug removed to reduce spam


            var newDamage = calculatePositionDamage(bestPosition, availableWeapons);
            // Special handling for line weapons - they need alignment more than damage improvement
            var hasLineWeapons = inArray(availableWeapons, WEAPON_B_LASER) || inArray(availableWeapons, WEAPON_M_LASER) || inArray(availableWeapons, WEAPON_LASER) || inArray(availableWeapons, WEAPON_FLAME_THROWER);
            var improvementThreshold = hasLineWeapons ? 1.01 : 1.05; // 1% for line weapons, 5% for others
            
            if (newDamage > currentDamage * improvementThreshold || currentDamage == 0) { // Line weapons: 1%, others: 5% improvement


                var result = [:];
                result["cell"] = bestPosition;
                result["reason"] = repositionReason;
                result["damageImprovement"] = newDamage - currentDamage;
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Moving to position " + bestPosition + " for +" + (newDamage - currentDamage) + " damage");
                }
                return result;
            } else {
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Position improvement insufficient - staying put");
                }
            }
        } else {
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("No valid position found within MP range");
            }
        }
    } else {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("No repositioning needed");
        }
    }
    // CRITICAL FIX: If desperately out of range, force movement towards enemy
    if (shouldReposition && availableMP > 0 && currentDistance > 12) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("EMERGENCY: Forcing movement towards enemy - distance " + currentDistance + " > 12");
        }
        // Find a cell closer to the enemy, even if not optimal
        var reachableCells = getReachableCells(myCell, availableMP);
        var closestCell = null;
        var closestDistance = currentDistance;
        
        for (var i = 0; i < min(20, count(reachableCells)); i++) {
            var cell = reachableCells[i];
            var distToEnemy = getCellDistance(cell, enemyCell);
            if (distToEnemy < closestDistance) {
                closestDistance = distToEnemy;
                closestCell = cell;
            }
        }
        if (closestCell != null && closestCell != myCell) {
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("Emergency movement to " + closestCell + " (distance " + closestDistance + " vs " + currentDistance + ")");
            }
            
            var result = [:];
            result["cell"] = closestCell;
            result["reason"] = "Emergency movement - out of attack range";
            result["damageImprovement"] = 0;
            return result;
        }
    }
    return null;
}

// Function: analyzePositioningNeeds
// Analyze what positioning improvements are needed


function analyzePositioningNeeds(distance, hasLOS, weapons) {


    var needs = [:];
    needs["needsRepositioning"] = false;
    needs["reason"] = "";
    
    // Dark Katana close-range opportunity
    if (distance >= 2 && distance <= 4 && inArray(weapons, WEAPON_DARK_KATANA)) {


        var mySTR = getStrength();


        var darkKatanaSelfDmg = 44 * (1 + mySTR / 100);
        if (myHP > darkKatanaSelfDmg * 2) {


            var meleeReachable = canReachDistance(1, myMP);
            if (meleeReachable) {
                needs["needsRepositioning"] = true;
                needs["reason"] = "Close range - move to melee for Dark Katana";
                return needs;
            }
        }
    }
    
    // Rifle range optimization
    if (inArray(weapons, WEAPON_RIFLE) && hasLOS) {
        if (distance < 7) {
            needs["needsRepositioning"] = true;
            needs["reason"] = "Too close for rifle - move to range 7-9";
            return needs;
        } else if (distance > 9) {
            needs["needsRepositioning"] = true;
            needs["reason"] = "Too far for rifle - move to range 7-9";
            return needs;
        }
    }
    // M-Laser alignment
    if (inArray(weapons, WEAPON_M_LASER) && distance >= 5 && distance <= 12) {
        if (!isOnSameLine(myCell, enemyCell)) {
            needs["needsRepositioning"] = true;
            if (distance >= 10) {
                // At longer ranges, prefer moving to Rifle range over seeking line alignment
                needs["reason"] = "M-Laser not aligned at range " + distance + " - prefer Rifle range";
            } else {
                needs["reason"] = "M-Laser not aligned - seek line positioning";
            }
            return needs;
        }
    }
    // B-Laser alignment
    if (inArray(weapons, WEAPON_B_LASER) && distance >= 2 && distance <= 8) {
        if (!isOnSameLine(myCell, enemyCell)) {
            needs["needsRepositioning"] = true;
            needs["reason"] = "B-Laser not aligned - seek line positioning";
            return needs;
        }
    }
    // Flame Thrower alignment
    if (inArray(weapons, WEAPON_FLAME_THROWER) && distance >= 2 && distance <= 8) {
        if (!isOnSameLine(myCell, enemyCell)) {
            needs["needsRepositioning"] = true;
            needs["reason"] = "Flame Thrower not aligned - seek line positioning";
            return needs;
        }
    }
    
    // Enhanced Lightninger range check
    if (inArray(weapons, WEAPON_ENHANCED_LIGHTNINGER)) {
        if (distance < 6) {
            needs["needsRepositioning"] = true;
            needs["reason"] = "Enhanced Lightninger too close - need range 6-10";
            return needs;
        } else if (distance > 10) {
            needs["needsRepositioning"] = true;
            needs["reason"] = "Enhanced Lightninger too far - need range 6-10";
            return needs;
        }
    }
    
    // Katana range check - must be at range 1
    if (inArray(weapons, WEAPON_KATANA)) {
        if (distance != 1) {
            needs["needsRepositioning"] = true;
            needs["reason"] = "Katana requires melee range - need range 1";
            return needs;
        }
    }
    // Grenade launcher accessibility
    if (distance == 8 && inArray(weapons, WEAPON_GRENADE_LAUNCHER) && !hasLOS) {
        // We're at range 8 but no LOS - move to range 7 for grenade access
        needs["needsRepositioning"] = true;
        needs["reason"] = "Range 8 without LOS - move to grenade range";
        return needs;
    }
    // Line of sight issues
    if (!hasLOS && distance <= 10) {
        needs["needsRepositioning"] = true;
        needs["reason"] = "No line of sight - repositioning for better angle";
        return needs;
    }
    // Out of all weapon ranges - check actual max weapon range
    var maxWeaponRange = getMaxWeaponRange(weapons);
    if (distance > maxWeaponRange) {
        needs["needsRepositioning"] = true;
        needs["reason"] = "Out of weapon range - moving closer";
        return needs;
    }
    return needs;
}

// Function: findOptimalAttackPosition
// Find the best position for attacking within movement range


function findOptimalAttackPosition(maxMovement, weapons) {


    var reachableCells = getReachableCells(myCell, maxMovement);
    
    // Removed verbose cell searching logs


    var bestCell = null;
    var bestScore = -999999;
    var bestLOSCell = null;
    var bestLOSScore = -999999;
    var bestMLaserCell = null;
    var bestMLaserScore = -999999;
    var bestLaserCell = null;
    var bestLaserScore = -999999;
    var bestBLaserCell = null;
    var bestBLaserScore = -999999;
    var bestRifleCell = null;  
    var bestRifleScore = -999999;
    var bestNeutrinoCell = null;
    var bestNeutrinoScore = -999999;
    var bestDestroyerCell = null;
    var bestDestroyerScore = -999999;
    var bestFlameThrowerCell = null;
    var bestFlameThrowerScore = -999999;
    var bestKatanaCell = null;
    var bestKatanaScore = -999999;
    var bestAoECell = null;
    var bestAoEScore = -999999;
    
    // Evaluate all reachable positions
    for (var i = 0; i < min(50, count(reachableCells)); i++) { // Limit for performance
        var cell = reachableCells[i];
        var score = scoreAttackPosition(cell, weapons);
        
        // Track overall best
        if (score > bestScore) {
            bestScore = score;
            bestCell = cell;
        }
        // Track best LOS position separately
        if (hasLOS(cell, enemyCell) && score > bestLOSScore) {
            bestLOSScore = score;
            bestLOSCell = cell;
        }
        var distance = getCellDistance(cell, enemyCell);
        
        // Track best M-Laser aligned position (range 5-12, line aligned)
        if (inArray(weapons, WEAPON_M_LASER) && 
            distance >= 5 && distance <= 12 && 
            hasLOS(cell, enemyCell) && 
            isOnSameLine(cell, enemyCell) && 
            score > bestMLaserScore) {
            bestMLaserScore = score;
            bestMLaserCell = cell;
        }
        // Track best Laser aligned position (range 2-9, line aligned)
        if (inArray(weapons, WEAPON_LASER) && 
            distance >= 2 && distance <= 9 && 
            hasLOS(cell, enemyCell) && 
            isOnSameLine(cell, enemyCell) && 
            score > bestLaserScore) {
            bestLaserScore = score;
            bestLaserCell = cell;
        }
        // Track best B-Laser aligned position (range 2-8, line aligned)
        if (inArray(weapons, WEAPON_B_LASER) && 
            distance >= 2 && distance <= 8 && 
            hasLOS(cell, enemyCell) && 
            isOnSameLine(cell, enemyCell) && 
            score > bestBLaserScore) {
            bestBLaserScore = score;
            bestBLaserCell = cell;
        }
        // Track best Rifle position (range 7-9, LOS required)
        if (inArray(weapons, WEAPON_RIFLE) && 
            distance >= 7 && distance <= 9 && 
            hasLOS(cell, enemyCell) && 
            score > bestRifleScore) {
            bestRifleScore = score;
            bestRifleCell = cell;
        }
        // Track best Neutrino position (range 2-6, LOS required)
        if (inArray(weapons, WEAPON_NEUTRINO) && 
            distance >= 2 && distance <= 6 && 
            hasLOS(cell, enemyCell) && 
            score > bestNeutrinoScore) {
            bestNeutrinoScore = score;
            bestNeutrinoCell = cell;
        }
        // Track best Destroyer position (range 1-6, LOS required)
        if (inArray(weapons, WEAPON_DESTROYER) && 
            distance >= 1 && distance <= 6 && 
            hasLOS(cell, enemyCell) && 
            score > bestDestroyerScore) {
            bestDestroyerScore = score;
            bestDestroyerCell = cell;
        }
        // Track best Flame Thrower position (range 2-8, line alignment required)
        if (inArray(weapons, WEAPON_FLAME_THROWER) && 
            distance >= 2 && distance <= 8 && 
            hasLOS(cell, enemyCell) && 
            isOnSameLine(cell, enemyCell) &&
            score > bestFlameThrowerScore) {
            bestFlameThrowerScore = score;
            bestFlameThrowerCell = cell;
        }
        
        // Track best Enhanced Lightninger position (range 6-10, LOS required for AoE)
        if (inArray(weapons, WEAPON_ENHANCED_LIGHTNINGER) && 
            distance >= 6 && distance <= 10 && 
            hasLOS(cell, enemyCell) && 
            score > bestFlameThrowerScore) {  // Reuse variable or add new one
            bestFlameThrowerScore = score;
            bestFlameThrowerCell = cell;
        }
        
        // Track best Katana position (range 1, melee combat)
        if (inArray(weapons, WEAPON_KATANA) && 
            distance == 1 && 
            hasLOS(cell, enemyCell) && 
            score > bestKatanaScore) {
            bestKatanaScore = score;
            bestKatanaCell = cell;
        }
        // Track best AoE position (for Grenade range 4-7)
        if (distance >= 4 && distance <= 7 && score > bestAoEScore) {
            bestAoEScore = score;
            bestAoECell = cell;
        }
    }
    // PRIORITY 1: M-Laser aligned position (best weapon when aligned)
    if (bestMLaserCell != null && bestMLaserScore > -5000) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("🎯 M-Laser aligned position: " + bestMLaserCell + " (score: " + bestMLaserScore + ")");
        }
        return bestMLaserCell;
    }
    // PRIORITY 2: Enhanced Lightninger position (excellent AoE weapon with healing)
    if (inArray(weapons, WEAPON_ENHANCED_LIGHTNINGER) && bestFlameThrowerCell != null && bestFlameThrowerScore > -5000) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("🎯 Enhanced Lightninger position: " + bestFlameThrowerCell + " (score: " + bestFlameThrowerScore + ")");
        }
        return bestFlameThrowerCell;
    }
    
    // PRIORITY 2.5: Flame Thrower aligned position (excellent line weapon with poison DoT)
    if (bestFlameThrowerCell != null && bestFlameThrowerScore > -5000) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("🎯 Flame Thrower aligned position: " + bestFlameThrowerCell + " (score: " + bestFlameThrowerScore + ")");
        }
        return bestFlameThrowerCell;
    }
    // PRIORITY 2.5: B-Laser aligned position (healing line weapon, high DPT)
    if (bestBLaserCell != null && bestBLaserScore > -5000) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("🎯 B-Laser aligned position: " + bestBLaserCell + " (score: " + bestBLaserScore + ")");
        }
        return bestBLaserCell;
    }
    // PRIORITY 3: Laser aligned position (good line weapon, shorter range than M-Laser)
    if (bestLaserCell != null && bestLaserScore > -5000) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("🎯 Laser aligned position: " + bestLaserCell + " (score: " + bestLaserScore + ")");
        }
        return bestLaserCell;
    }
    // PRIORITY 4: Rifle position (consistent reliable weapon)
    if (bestRifleCell != null && bestRifleScore > -5000) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("🎯 Rifle position: " + bestRifleCell + " (score: " + bestRifleScore + ")");
        }
        return bestRifleCell;
    }
    
    // PRIORITY 4.5: Katana position (high damage melee with TP debuff)
    if (bestKatanaCell != null && bestKatanaScore > -5000) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("🎯 Katana position: " + bestKatanaCell + " (score: " + bestKatanaScore + ")");
        }
        return bestKatanaCell;
    }
    // PRIORITY 6: Destroyer position (debuff weapon, fallback to close range)
    if (bestDestroyerCell != null && bestDestroyerScore > -5000) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("🎯 Destroyer position: " + bestDestroyerCell + " (score: " + bestDestroyerScore + ")");
        }
        return bestDestroyerCell;
    }
    // PRIORITY 5: Neutrino position (vulnerability debuff utility)
    if (bestNeutrinoCell != null && bestNeutrinoScore > -5000) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("🎯 Neutrino position: " + bestNeutrinoCell + " (score: " + bestNeutrinoScore + ")");
        }
        return bestNeutrinoCell;
    }
    // PRIORITY 6: General LOS positions (fallback)
    if (bestLOSCell != null && bestLOSScore > -5000) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("General LOS position: " + bestLOSCell + " (score: " + bestLOSScore + ")");
        }
        return bestLOSCell;
    }
    // PRIORITY 7: AoE position for indirect attacks
    if (bestAoECell != null && bestAoEScore > -8000) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("AoE position: " + bestAoECell + " (score: " + bestAoEScore + ") - No direct LOS available");
        }
        return bestAoECell;
    }
    // Multi-turn LOS pathfinding as last resort
    if (bestScore < -8000) {
        var futurePosition = findFutureLOSPosition(maxMovement * 2); // Look 2 turns ahead
        if (futurePosition != null) {
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("Planning multi-turn move toward LOS position: " + futurePosition);
            }
            // Move toward the future LOS position
            return planMovementToward(futurePosition, maxMovement);
        }
    }
    // Last resort: return best overall position
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Best attack position: " + bestCell + " (score: " + bestScore + ") - Emergency fallback");
    }
    return bestCell;
}

// Function: scoreAttackPosition
// Score a position for attack effectiveness


function scoreAttackPosition(cell, weapons) {


    var score = 0;


    var distance = getCellDistance(cell, enemyCell);
    
    var hasDirectLOS = hasLOS(cell, enemyCell);
    if (!hasDirectLOS) {
        // Check if this could be useful for AoE attacks (distance already declared above)
        if (distance >= 4 && distance <= 7) {
            // Potential AoE position - reduced penalty
            score -= 5000; // Less harsh penalty for AoE range
        } else {
            return -10000; // Heavily penalize no line of sight outside AoE range
        }
    }
    // Score based on weapon effectiveness
    for (var w = 0; w < count(weapons); w++) {


        var weaponId = weapons[w];


        var weaponScore = scoreWeaponAtPosition(weaponId, cell, distance);
        score = max(score, weaponScore); // Take best weapon score
    }
    // Distance penalties for being too close to dangerous enemies
    if (ENEMY_HAS_BAZOOKA && distance >= 2 && distance <= 4) {
        score -= 2000; // Heavy penalty for bazooka range
    }
    // Small bonus for optimal range (7-8)
    if (distance >= 7 && distance <= 8) {
        score += 100;
    }
    // EID penalty (Expected Incoming Damage)


    var eid = calculateEID(cell);
    score -= eid * 0.5;
    
    return score;
}

// Function: scoreWeaponAtPosition
// Score a specific weapon at a position


function scoreWeaponAtPosition(weaponId, cell, distance) {


    var minRange = getWeaponMinRange(weaponId);


    var maxRange = getWeaponMaxRange(weaponId);
    
    if (distance < minRange || distance > maxRange) {
        return -5000; // Can't use weapon
    }


    var baseScore = 1000; // Base score for usable weapon
    
    // Weapon-specific scoring
    if (weaponId == WEAPON_RIFLE && distance >= 7 && distance <= 9) {
        baseScore = 8000; // Excellent rifle range
    } else if (weaponId == WEAPON_M_LASER && distance >= 5 && distance <= 12) {
        if (isOnSameLine(cell, enemyCell)) {
            baseScore = 7500; // Excellent M-Laser position
        } else {
            baseScore = 3000; // M-Laser without alignment
        }
    } else if (weaponId == WEAPON_DARK_KATANA && distance == 1) {
        baseScore = 6000; // Good melee position
    } else if (weaponId == WEAPON_FLAME_THROWER && distance >= 2 && distance <= 8) {
        if (isOnSameLine(cell, enemyCell)) {
            baseScore = 8000; // Excellent Flame Thrower position with line alignment - HIGHER than Destroyer
        } else {
            baseScore = 3500; // Flame Thrower without alignment
        }
    } else if (weaponId == WEAPON_DESTROYER && distance >= 1 && distance <= 6) {
        baseScore = 5500; // Good Destroyer position - LOWER than Flame Thrower
    } else if (weaponId == WEAPON_GRENADE_LAUNCHER && distance >= 4 && distance <= 7) {
        baseScore = 5000; // Good grenade range
    }
    return baseScore;
}

// Function: executePositioning
// Execute the positioning move


function executePositioning(positionInfo) {
    if (positionInfo == null || positionInfo["cell"] == myCell) {
        return false;
    }
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Repositioning: " + positionInfo["reason"] + 
                " (damage improvement: +" + positionInfo["damageImprovement"] + ")");
    }
    moveToCell(positionInfo["cell"]);
    
    // Update position variables
    myCell = getCell();
    myMP = getMP();
    enemyCell = getCell(enemy);
    enemyDistance = getCellDistance(myCell, enemyCell);
    
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Repositioned - new distance: " + enemyDistance + ", new LOS: " + hasLOS(myCell, enemyCell));
    }
    return true;
}

// Function: calculatePositionDamage
// Calculate potential damage from a position


function calculatePositionDamage(cell, weapons) {


    var maxDamage = 0;


    var distance = getCellDistance(cell, enemyCell);


    var mySTR = getStrength();
    
    if (!hasLOS(cell, enemyCell)) {
        return 0;
    }
    for (var w = 0; w < count(weapons); w++) {


        var weaponId = weapons[w];


        var minRange = getWeaponMinRange(weaponId);


        var maxRange = getWeaponMaxRange(weaponId);
        
        if (distance >= minRange && distance <= maxRange) {


            var damage = 0;
            
            if (weaponId == WEAPON_RIFLE && distance >= 7 && distance <= 9) {
                damage = 76 * (1 + mySTR / 100) * 2; // 2 uses
            } else if (weaponId == WEAPON_M_LASER && distance >= 5 && distance <= 12) {
                if (isOnSameLine(cell, enemyCell)) {
                    damage = 95 * (1 + mySTR / 100);
                }
            } else if (weaponId == WEAPON_DARK_KATANA && distance == 1) {
                damage = 99 * (1 + mySTR / 100) * 2; // 2 uses
            } else if (weaponId == WEAPON_GRENADE_LAUNCHER && distance >= 4 && distance <= 7) {
                damage = 150 * (1 + mySTR / 100);
            }
            maxDamage = max(maxDamage, damage);
        }
    }
    return maxDamage;
}

// Function: canReachDistance
// Check if we can reach a specific distance from enemy


function canReachDistance(targetDistance, movementPoints) {


    var reachable = getReachableCells(myCell, movementPoints);
    
    for (var i = 0; i < count(reachable); i++) {


        var cell = reachable[i];
        if (getCellDistance(cell, enemyCell) == targetDistance) {
            return true;
        }
    }
    return false;
}

// Function: findBestAttackPosition
// Find the best position for attacking (used in fallback logic)


function findBestAttackPosition(availableWeapons) {


    var reachable = getReachableCells(myCell, myMP);


    var bestCell = null;


    var bestScore = -999999;
    
    for (var i = 0; i < min(30, count(reachable)); i++) {


        var cell = reachable[i];


        var distance = getCellDistance(cell, enemyCell);
        
        if (!hasLOS(cell, enemyCell)) {
            continue; // Skip positions without LOS
        }
        // Allow positions up to max weapon range + movement buffer
        var maxRange = getMaxWeaponRange(availableWeapons) + 3;
        if (distance > maxRange) {
            continue; // Skip positions too far from any weapon range
        }


        var score = 1000 - distance * 10; // Prefer closer positions
        
        // Bonus for optimal ranges
        if (distance >= 7 && distance <= 9) {
            score += 500; // Rifle range bonus
        } else if (distance >= 5 && distance <= 8) {
            score += 300; // Good general range
        }
        if (score > bestScore) {
            bestScore = score;
            bestCell = cell;
        }
    }
    return bestCell;
}

// Function: findFutureLOSPosition
// Look ahead multiple turns to find positions with LOS
function findFutureLOSPosition(maxDistance) {
    var enemyX = getCellX(enemyCell);
    var enemyY = getCellY(enemyCell);
    var myX = getCellX(myCell);
    var myY = getCellY(myCell);
    
    // Check positions in expanding rings around current position
    for (var radius = 1; radius <= maxDistance; radius++) {
        for (var dx = -radius; dx <= radius; dx++) {
            for (var dy = -radius; dy <= radius; dy++) {
                if (abs(dx) + abs(dy) > radius) continue; // Skip corners
                
                var testCell = getCellFromXY(myX + dx, myY + dy);
                if (testCell == null || testCell == -1) continue;
                
                // Check if this position has LOS and is in weapon range
                if (hasLOS(testCell, enemyCell)) {
                    var distance = getCellDistance(testCell, enemyCell);
                    if (distance >= 4 && distance <= 12) { // Any weapon range
                        return testCell;
                    }
                }
            }
        }
    }
    return null;
}

// Function: planMovementToward
// Plan movement toward a target position
function planMovementToward(targetCell, availableMP) {
    var targetX = getCellX(targetCell);
    var targetY = getCellY(targetCell);
    var myX = getCellX(myCell);
    var myY = getCellY(myCell);
    
    // Calculate direction vector
    var deltaX = targetX - myX;
    var deltaY = targetY - myY;
    
    // Normalize to movement range
    var distance = sqrt(deltaX * deltaX + deltaY * deltaY);
    if (distance == 0) return myCell;
    
    var stepX = floor(deltaX * availableMP / distance);
    var stepY = floor(deltaY * availableMP / distance);
    
    // Find the best reachable cell in that direction
    var reachableCells = getReachableCells(myCell, availableMP);
    var bestCell = myCell;
    var bestDistance = 999;
    
    for (var i = 0; i < count(reachableCells); i++) {
        var cell = reachableCells[i];
        var cellDistance = getCellDistance(cell, targetCell);
        if (cellDistance < bestDistance) {
            bestDistance = cellDistance;
            bestCell = cell;
        }
    }
    return bestCell;
}

// Function: getMaxWeaponRange
// Get maximum range of available weapons
function getMaxWeaponRange(weapons) {
    var maxRange = 0;
    
    for (var i = 0; i < count(weapons); i++) {
        var weaponId = weapons[i];
        var range = 0;
        
        if (weaponId == WEAPON_GRENADE_LAUNCHER) {
            range = 7;
        } else if (weaponId == WEAPON_RIFLE) {
            range = 9;
        } else if (weaponId == WEAPON_M_LASER) {
            range = 12;
        } else if (weaponId == WEAPON_B_LASER) {
            range = 8;
        } else if (weaponId == WEAPON_MAGNUM) {
            range = 7;
        } else if (weaponId == WEAPON_LASER) {
            range = 8;
        } else if (weaponId == WEAPON_FLAME_THROWER) {
            range = 8;
        } else if (weaponId == WEAPON_DESTROYER) {
            range = 2;
        } else if (weaponId == WEAPON_DARK_KATANA) {
            range = 1;
        } else {
            range = 9; // Default reasonable range
        }
        if (range > maxRange) {
            maxRange = range;
        }
    }
    return maxRange > 0 ? maxRange : 9; // Fallback to 9 if no weapons
}
