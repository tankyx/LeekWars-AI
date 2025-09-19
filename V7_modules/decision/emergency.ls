// V7 Module: decision/emergency.ls
// Panic mode and emergency decisions

// === MULTI-ENEMY EMERGENCY MODE DETECTION ===
function isEmergencyMode() {
    if (count(enemies) == 0) return false;
    
    // Low HP threshold
    if ((myHP / myMaxHP) < EMERGENCY_HP_THRESHOLD) return true;
    
    // Calculate combined threat from all enemies
    var totalEnemyThreat = 0;
    var immediateKillPossible = false;
    
    for (var i = 0; i < count(enemies); i++) {
        var enemyEntity = enemies[i];
        if (getLife(enemyEntity) <= 0) continue;
        
        // Enemy threat assessment
        var enemyDamage = estimateEnemyDamageNextTurn(enemyEntity);
        totalEnemyThreat += enemyDamage;
        
        // Check if we can kill any enemy this turn (aggressive override)
        if (primaryTarget == enemyEntity) {
            var myDamageToTarget = estimateMyDamageThisTurn(enemyEntity);
            if (myDamageToTarget >= getLife(enemyEntity) && myDamageToTarget > 0) {
                immediateKillPossible = true;
            }
        }
    }
    
    // Don't go emergency if we can kill primary target this turn (PRIORITY CHECK)
    if (immediateKillPossible) {
        if (debugEnabled) {
            debugW("EMERGENCY OVERRIDE: Can kill primary target, staying aggressive");
        }
        return false;
    }
    
    // CRITICAL: Never flee if primary enemy is extremely low HP (< 25%)
    if (primaryTarget != null && getLife(primaryTarget) > 0) {
        var primaryHP = getLife(primaryTarget);
        var primaryMaxHP = getTotalLife(primaryTarget);
        var primaryHPPercent = primaryHP / primaryMaxHP;
        
        if (primaryHPPercent < 0.25) {
            if (debugEnabled) {
                debugW("EMERGENCY OVERRIDE: Primary target critical HP (" + floor(primaryHPPercent * 100) + "%), staying aggressive");
            }
            return false;
        }
    }
    
    // Combined enemies can kill us next turn
    if (totalEnemyThreat >= myHP) {
        if (debugEnabled) {
            debugW("EMERGENCY THREAT: Combined enemy damage " + totalEnemyThreat + " >= our HP " + myHP);
        }
        return true;
    }
    
    // Outnumbered significantly (3+ enemies vs 1)
    if (count(enemies) >= 3 && (myHP / myMaxHP) < 0.5) {
        if (debugEnabled) {
            debugW("EMERGENCY OUTNUMBERED: " + count(enemies) + " enemies, HP < 50%");
        }
        return true;
    }
    
    return false;
}

// === SIMPLIFIED EMERGENCY MODE ===
function executeEmergencyMode() {
    // Priority 1: Try to heal with REGENERATION if available
    if (canUseChip(CHIP_REGENERATION, getEntity())) {
        useChip(CHIP_REGENERATION, getEntity());
        myHP = getLife(); // Update HP after healing
        myTP = getTP();   // Update TP after healing
        // DON'T RETURN - continue with movement and attacks!
    }
    
    // Priority 2: Tactical repositioning - find safe position that maintains weapon range
    if (myMP > 0) {
        var weapons = getWeapons();
        var bestCell = null;
        var bestScore = -999;
        
        // Find tactically optimal cell within movement range
        for (var dist = 1; dist <= myMP; dist++) {
            var cells = getCellsAtExactDistance(myCell, dist);
            for (var i = 0; i < count(cells); i++) {
                var cell = cells[i];
                
                // Must be walkable
                if (getCellContent(cell) != CELL_EMPTY) continue;
                
                var score = 0;
                var enemyDist = getCellDistance(cell, enemyCell);
                
                // PRIORITY 1: Stay within Enhanced Lightninger range (6-10) for healing + damage
                if (inArray(weapons, WEAPON_ENHANCED_LIGHTNINGER) && enemyDist >= 6 && enemyDist <= 10) {
                    score += 50; // High priority for Enhanced Lightninger range
                    if (hasLOS(cell, enemyCell)) {
                        score += 20; // LOS bonus
                    }
                }
                
                // PRIORITY 2: Stay within M-Laser range (5-12) if aligned
                if (inArray(weapons, WEAPON_M_LASER) && enemyDist >= 5 && enemyDist <= 12) {
                    var cellX = getCellX(cell);
                    var cellY = getCellY(cell);
                    var enemyX = getCellX(enemyCell);  
                    var enemyY = getCellY(enemyCell);
                    var xAligned = (cellX == enemyX);
                    var yAligned = (cellY == enemyY);
                    
                    if ((xAligned || yAligned) && !(xAligned && yAligned)) {
                        score += 40; // M-Laser alignment bonus
                    }
                }
                
                // PRIORITY 3: Stay within Rifle range (7-9) 
                if (inArray(weapons, WEAPON_RIFLE) && enemyDist >= 7 && enemyDist <= 9) {
                    score += 30; // Rifle range bonus
                    if (hasLOS(cell, enemyCell)) {
                        score += 15; // LOS bonus  
                    }
                }
                
                // Distance bonus: prefer farther cells for safety (but within weapon range)
                score += min(enemyDist, 12); // Cap distance bonus
                
                if (score > bestScore) {
                    bestScore = score;
                    bestCell = cell;
                }
            }
        }
        
        // Move to tactically optimal position
        if (bestCell != null && bestScore > 0) {
            moveTowardCells([bestCell], myMP);
            myCell = getCell();
            myMP = getMP();
            if (debugEnabled) {
                debugW("TACTICAL EMERGENCY: Moved to weapon-ready position " + bestCell + " (score: " + bestScore + ")");
            }
        }
    }
    
    // Priority 3: Attack with any available weapon if in range
    if (myTP > 0 && enemy != null) {
        var weapons = getWeapons();
        var currentWeapon = getWeapon();
        
        // First, try current weapon without switching (saves 1 TP)
        if (currentWeapon != null) {
            var cost = getWeaponCost(currentWeapon);
            if (myTP >= cost && canWeaponReachTarget(currentWeapon, myCell, enemyCell)) {
                if (canUseWeapon(enemy)) {
                    useWeapon(enemy);
                    myTP = getTP(); // Update TP after attack
                    return; // Exit after successful attack
                }
            }
        }
        
        // Only switch if current weapon doesn't work
        for (var i = 0; i < count(weapons) && i < 3; i++) { // Limit to prevent timeout
            var weapon = weapons[i];
            if (weapon == currentWeapon) continue; // Skip current weapon
            
            var cost = getWeaponCost(weapon);
            // Check if we have TP for switch (1) + attack (cost)
            if (myTP >= cost + 1) {
                // Pre-validate BEFORE switching to avoid wasting TP
                if (canWeaponReachTarget(weapon, myCell, enemyCell)) {
                    setWeapon(weapon);
                    myTP--; // Deduct switch cost immediately
                    if (canUseWeapon(enemy)) {
                        useWeapon(enemy);
                        myTP = getTP(); // Update TP after attack
                        break;
                    }
                }
            }
        }
    }
}

// Note: getCellsAtExactDistance() is defined in evaluation.ls

// === EMERGENCY HEALING ===
function tryEmergencyHealing() {
    var healed = false;
    var myCurrentTP = getTP();
    var currentCell = getCell();
    var distanceToEnemy = getCellDistance(currentCell, enemyCell);
    
    if (debugEnabled) {
        debugW("EMERGENCY HEAL: TP=" + myCurrentTP + ", Distance=" + distanceToEnemy);
    }
    
    // PRIORITY 1: Enhanced Lightninger if positioned correctly (range 6-10) and has TP
    var weapons = getWeapons();
    var hasLightninger = inArray(weapons, WEAPON_ENHANCED_LIGHTNINGER);
    var inRange = distanceToEnemy >= 6 && distanceToEnemy <= 10;
    var hasTP = myCurrentTP >= 9;
    var hasLineOfSight = hasLOS(currentCell, enemyCell);
    
    if (debugEnabled) {
        debugW("LIGHTNINGER CHECK: hasWeapon=" + hasLightninger + ", inRange=" + inRange + " (d=" + distanceToEnemy + "), hasTP=" + hasTP + ", hasLOS=" + hasLineOfSight);
    }
    
    if (hasLightninger && inRange && hasTP && hasLineOfSight) {
        if (debugEnabled) {
            debugW("EMERGENCY: Using Enhanced Lightninger for healing + damage at distance " + distanceToEnemy);
        }
        
        // Use Enhanced Lightninger for healing + damage
        useWeapon(primaryTarget);
        healed = true;
        myCurrentTP -= 9;
        
        // Follow up with REGENERATION if available and enough TP
        if (myCurrentTP >= 3 && canUseChip(CHIP_REGENERATION, getEntity())) {
            useChip(CHIP_REGENERATION, getEntity());
            if (debugEnabled) {
                debugW("EMERGENCY: Added REGENERATION for extra healing");
            }
        }
        
        return healed;
    }
    
    // PRIORITY 2: Regeneration chip (guaranteed percentage healing) - ONE USE PER FIGHT
    var regenAlreadyUsed = (lastChipUse[CHIP_REGENERATION] != null);
    var canUseRegen = canUseChip(CHIP_REGENERATION, getEntity());
    
    if (debugEnabled) {
        debugW("REGEN CHECK: alreadyUsed=" + regenAlreadyUsed + ", canUse=" + canUseRegen);
    }
    
    if (!regenAlreadyUsed && canUseRegen) {
        useChip(CHIP_REGENERATION, getEntity());
        lastChipUse[CHIP_REGENERATION] = getTurn(); // Track usage
        healed = true;
        if (debugEnabled) {
            debugW("EMERGENCY: Used REGENERATION chip (first use this fight)");
        }
    } else {
        if (debugEnabled) {
            if (regenAlreadyUsed) {
                debugW("EMERGENCY: REGENERATION already used on turn " + lastChipUse[CHIP_REGENERATION]);
            } else {
                debugW("EMERGENCY: REGENERATION chip not available (not equipped or other issue)");
            }
        }
    }
    
    // PRIORITY 3: If no healing available, try to attack with healing weapons
    if (!healed && hasLightninger && inRange && hasTP) {
        if (debugEnabled) {
            debugW("EMERGENCY FALLBACK: No healing chips available, trying Enhanced Lightninger anyway (LOS=" + hasLineOfSight + ")");
        }
        
        // Try Enhanced Lightninger even without perfect LOS - it might work
        if (hasLineOfSight) {
            useWeapon(primaryTarget);
            healed = true;
            if (debugEnabled) {
                debugW("EMERGENCY FALLBACK: Used Enhanced Lightninger without healing chips");
            }
        }
    }
    
    if (debugEnabled && !healed) {
        debugW("EMERGENCY HEAL: No healing options available - REGENERATION used and Enhanced Lightninger unavailable");
    }
    
    return healed;
}

// === EMERGENCY HEALING WITH ENHANCED LIGHTNINGER ===
function tryEmergencyHealingWithAttack() {
    // Try Enhanced Lightninger first for bonus healing (100 HP flat + lifesteal)
    var hasLightninger = inArray(getWeapons(), WEAPON_ENHANCED_LIGHTNINGER);
    var currentDistance = getCellDistance(myCell, enemyCell);
    
    // Calculate minimum TP needed for at least 1 attack + switching + regen
    var switchCost = (getWeapon() != WEAPON_ENHANCED_LIGHTNINGER) ? 1 : 0;
    var weaponCost = getWeaponCost(WEAPON_ENHANCED_LIGHTNINGER);
    var tpReservedForRegen = canUseChip(CHIP_REGENERATION, getEntity()) ? getChipCost(CHIP_REGENERATION) : 0;
    var minTpNeeded = switchCost + weaponCost + tpReservedForRegen; // Minimum for 1 attack
    
    if (debugEnabled) {
        debugW("COMBAT HEAL CHECK: hasLightninger=" + hasLightninger + ", distance=" + currentDistance + ", TP=" + myTP + "/" + minTpNeeded);
    }
    
    if (hasLightninger && myTP >= minTpNeeded) {
        // Check if Enhanced Lightninger is in range (5-12) AND has LOS
        if (currentDistance >= 5 && currentDistance <= 12) {
            if (debugEnabled) {
                debugW("COMBAT HEAL: In range at distance " + currentDistance + ", checking LOS");
            }
            
            // Check LOS before switching weapons (avoid wasting TP)
            if (hasLOS(myCell, enemyCell)) {
                // Switch to Enhanced Lightninger if needed
                if (getWeapon() != WEAPON_ENHANCED_LIGHTNINGER) {
                    setWeapon(WEAPON_ENHANCED_LIGHTNINGER);
                    if (debugEnabled) {
                        debugW("COMBAT HEAL: Switched to Enhanced Lightninger");
                    }
                }
                
                // Double-check if we can use the weapon now
                if (canUseWeapon(enemy)) {
                if (debugEnabled) {
                    debugW("EMERGENCY: Using Enhanced Lightninger for bonus healing at distance " + currentDistance);
                }
                
                if (debugEnabled) {
                    debugW("MULTI-SHOT CALCULATION: Starting Enhanced Lightninger multi-shot logic");
                }
                
                // Attack multiple times for maximum lifesteal healing
                var lightningCost = getWeaponCost(WEAPON_ENHANCED_LIGHTNINGER);
                var maxUses = getWeaponMaxUses(WEAPON_ENHANCED_LIGHTNINGER);
                
                if (debugEnabled) {
                    debugW("MULTI-SHOT CALCULATION: weaponCost=" + weaponCost + ", maxUses=" + maxUses);
                }
                
                // Step 1: Always fire Enhanced Lightninger first
                if (debugEnabled) {
                    debugW("SMART HEALING: Step 1 - Firing first Enhanced Lightninger shot");
                }
                
                var hpBeforeShot = getLife();
                useWeapon(enemy);
                var hpAfterShot = getLife();
                
                if (debugEnabled) {
                    debugW("ENHANCED LIGHTNINGER: First shot - HP: " + hpBeforeShot + " → " + hpAfterShot + ", TP after: " + getTP());
                }
                
                // Step 2: Check HP after first shot to decide next action
                var hpPercent = hpAfterShot / getTotalLife();
                var currentTP = getTP();
                
                if (hpPercent > 0.5) {
                    // HP > 50%: Fire Enhanced Lightninger again if we have TP
                    if (currentTP >= lightningCost && canUseWeapon(enemy)) {
                        if (debugEnabled) {
                            debugW("SMART HEALING: HP > 50% (" + floor(hpPercent * 100) + "%), firing second Enhanced Lightninger");
                        }
                        
                        var hpBeforeSecond = getLife();
                        useWeapon(enemy);
                        var hpAfterSecond = getLife();
                        
                        if (debugEnabled) {
                            debugW("ENHANCED LIGHTNINGER: Second shot - HP: " + hpBeforeSecond + " → " + hpAfterSecond + ", TP after: " + getTP());
                        }
                    } else {
                        if (debugEnabled) {
                            debugW("SMART HEALING: HP > 50% but insufficient TP (" + currentTP + "/" + lightningCost + ") for second shot");
                        }
                    }
                } else {
                    // HP ≤ 50%: Use REGENERATION if available, otherwise fire second Enhanced Lightninger
                    if (canUseChip(CHIP_REGENERATION, getEntity()) && currentTP >= getChipCost(CHIP_REGENERATION)) {
                        if (debugEnabled) {
                            debugW("SMART HEALING: HP ≤ 50% (" + floor(hpPercent * 100) + "%), using REGENERATION instead");
                        }
                        
                        var hpBeforeRegen = getLife();
                        useChip(CHIP_REGENERATION, getEntity());
                        var hpAfterRegen = getLife();
                        
                        if (debugEnabled) {
                            debugW("REGENERATION: Used chip - HP: " + hpBeforeRegen + " → " + hpAfterRegen + ", TP after: " + getTP());
                        }
                    } else {
                        // REGENERATION not available, fire second Enhanced Lightninger if we have TP
                        if (currentTP >= lightningCost && canUseWeapon(enemy)) {
                            if (debugEnabled) {
                                debugW("SMART HEALING: HP ≤ 50% but REGENERATION not available, firing second Enhanced Lightninger");
                            }
                            
                            var hpBeforeSecond = getLife();
                            useWeapon(enemy);
                            var hpAfterSecond = getLife();
                            
                            if (debugEnabled) {
                                debugW("ENHANCED LIGHTNINGER: Second shot (fallback) - HP: " + hpBeforeSecond + " → " + hpAfterSecond + ", TP after: " + getTP());
                            }
                        } else {
                            if (debugEnabled) {
                                debugW("SMART HEALING: HP ≤ 50%, no REGENERATION, and insufficient TP (" + currentTP + "/" + lightningCost + ") for second shot");
                            }
                        }
                    }
                }
                
                return true;
                } else {
                    if (debugEnabled) {
                        debugW("COMBAT HEAL FAIL: canUseWeapon() failed - target may be dead/invalid");
                    }
                }
            } else {
                if (debugEnabled) {
                    debugW("COMBAT HEAL FAIL: No LOS from " + myCell + " to " + enemyCell + " at distance " + currentDistance);
                }
            }
        } else {
            if (debugEnabled) {
                debugW("COMBAT HEAL FAIL: Enhanced Lightninger out of range (" + currentDistance + " not in 5-12)");
            }
        }
    } else {
        if (debugEnabled) {
            debugW("HEAL FAIL: No Enhanced Lightninger or insufficient TP");
        }
    }
    
    return false;
}

// === TACTICAL EMERGENCY MOVEMENT ===
function tryEmergencyMovement() {
    if (myMP <= 0) return false;
    
    var currentDistance = getCellDistance(myCell, enemyCell);
    var weapons = getWeapons();
    
    if (debugEnabled) {
        debugW("TACTICAL EMERGENCY MOVE: Finding weapon-ready position from distance " + currentDistance);
    }
    
    // Priority 1: Move to FLAME_THROWER range (2-8) with LOS - POISON HEALING!
    if (inArray(weapons, WEAPON_FLAME_THROWER)) {
        var bestCell = findTacticalPosition(WEAPON_FLAME_THROWER, "Flame Thrower");
        if (bestCell != null) {
            var oldCell = myCell;
            var mpUsed = moveTowardCells([bestCell], myMP);
            myCell = getCell();
            myMP = getMP();
            
            if (debugEnabled) {
                debugW("TACTICAL MOVE (Flame): From " + oldCell + " to " + myCell + " (MP used: " + mpUsed + ")");
            }
            return mpUsed > 0;
        }
    }
    
    // Priority 2: Move to Enhanced Lightninger range (5-12) with LOS
    if (inArray(weapons, WEAPON_ENHANCED_LIGHTNINGER)) {
        var bestCell = findTacticalPosition(WEAPON_ENHANCED_LIGHTNINGER, "Enhanced Lightninger");
        if (bestCell != null) {
            var oldCell = myCell;
            var mpUsed = moveTowardCells([bestCell], myMP);
            myCell = getCell();
            myMP = getMP();
            
            if (debugEnabled) {
                debugW("TACTICAL MOVE: From " + oldCell + " to " + myCell + " (MP used: " + mpUsed + ")");
            }
            return mpUsed > 0;
        }
    }
    
    // Priority 3: Move to NEUTRINO range (2-6) with diagonal alignment - VULNERABILITY!
    if (inArray(weapons, WEAPON_NEUTRINO)) {
        var bestCell = findNeutrinoDiagonalPosition();
        if (bestCell != null) {
            var oldCell = myCell;
            var mpUsed = moveTowardCells([bestCell], myMP);
            myCell = getCell();
            myMP = getMP();
            
            if (debugEnabled) {
                debugW("TACTICAL MOVE (Neutrino): From " + oldCell + " to " + myCell + " (MP used: " + mpUsed + ")");
            }
            return mpUsed > 0;
        }
    }
    
    // Priority 4: Move to DESTROYER range (1-6) with LOS - DEBUFF!
    if (inArray(weapons, WEAPON_DESTROYER)) {
        var bestCell = findTacticalPosition(WEAPON_DESTROYER, "Destroyer");
        if (bestCell != null) {
            var oldCell = myCell;
            var mpUsed = moveTowardCells([bestCell], myMP);
            myCell = getCell();
            myMP = getMP();
            
            if (debugEnabled) {
                debugW("TACTICAL MOVE (Destroyer): From " + oldCell + " to " + myCell + " (MP used: " + mpUsed + ")");
            }
            return mpUsed > 0;
        }
    }
    
    // Priority 5: Move to Rifle range (7-9) with LOS
    if (inArray(weapons, WEAPON_RIFLE)) {
        var bestCell = findTacticalPosition(WEAPON_RIFLE, "Rifle");
        if (bestCell != null) {
            var oldCell = myCell;
            var mpUsed = moveTowardCells([bestCell], myMP);
            myCell = getCell();
            myMP = getMP();
            
            if (debugEnabled) {
                debugW("TACTICAL MOVE: From " + oldCell + " to " + myCell + " (MP used: " + mpUsed + ")");
            }
            return mpUsed > 0;
        }
    }
    
    // Priority 6: Move to M-Laser range (6-10) with alignment
    if (inArray(weapons, WEAPON_M_LASER)) {
        var bestCell = findMLaserAlignmentPosition();
        if (bestCell != null) {
            var oldCell = myCell;
            var mpUsed = moveTowardCells([bestCell], myMP);
            myCell = getCell();
            myMP = getMP();
            
            if (debugEnabled) {
                debugW("TACTICAL MOVE (M-Laser): From " + oldCell + " to " + myCell + " (MP used: " + mpUsed + ")");
            }
            return mpUsed > 0;
        }
    }
    
    // Priority 4: Move to B-Laser range (2-8) with alignment - HEALING + DAMAGE!
    if (inArray(weapons, WEAPON_B_LASER)) {
        var bestCell = findBLaserAlignmentPosition();
        if (bestCell != null) {
            var oldCell = myCell;
            var mpUsed = moveTowardCells([bestCell], myMP);
            myCell = getCell();
            myMP = getMP();
            
            if (debugEnabled) {
                debugW("TACTICAL MOVE (B-Laser): From " + oldCell + " to " + myCell + " (MP used: " + mpUsed + ")");
            }
            return mpUsed > 0;
        }
    }
    
    // Priority 5: Move to Rhino range (2-4) for high DPS close combat
    if (inArray(weapons, WEAPON_RHINO)) {
        var bestCell = findTacticalPosition(WEAPON_RHINO, "Rhino");
        if (bestCell != null) {
            var oldCell = myCell;
            var mpUsed = moveTowardCells([bestCell], myMP);
            myCell = getCell();
            myMP = getMP();
            
            if (debugEnabled) {
                debugW("TACTICAL MOVE: From " + oldCell + " to " + myCell + " (MP used: " + mpUsed + ")");
            }
            return mpUsed > 0;
        }
    }
    
    // Priority 6: Move to Grenade Launcher range (4-7) for AoE damage
    if (inArray(weapons, WEAPON_GRENADE_LAUNCHER)) {
        var bestCell = findTacticalPosition(WEAPON_GRENADE_LAUNCHER, "Grenade Launcher");
        if (bestCell != null) {
            var oldCell = myCell;
            var mpUsed = moveTowardCells([bestCell], myMP);
            myCell = getCell();
            myMP = getMP();
            
            if (debugEnabled) {
                debugW("TACTICAL MOVE: From " + oldCell + " to " + myCell + " (MP used: " + mpUsed + ")");
            }
            return mpUsed > 0;
        }
    }
    
    // Priority 6: Move to Sword range (1) - prioritize sword over katana due to lower cost
    if (inArray(weapons, WEAPON_SWORD)) {
        var bestCell = findTacticalPosition(WEAPON_SWORD, "Sword");
        if (bestCell != null) {
            var oldCell = myCell;
            var mpUsed = moveTowardCells([bestCell], myMP);
            myCell = getCell();
            myMP = getMP();
            
            if (debugEnabled) {
                debugW("TACTICAL MOVE: From " + oldCell + " to " + myCell + " (MP used: " + mpUsed + ")");
            }
            
            return mpUsed > 0; // Return true if we moved
        }
    }
    
    // Priority 7: Move to Katana range (1) as last resort
    if (inArray(weapons, WEAPON_KATANA)) {
        var bestCell = findTacticalPosition(WEAPON_KATANA, "Katana");
        if (bestCell != null) {
            var oldCell = myCell;
            var mpUsed = moveTowardCells([bestCell], myMP);
            myCell = getCell();
            myMP = getMP();
            
            if (debugEnabled) {
                debugW("TACTICAL MOVE: From " + oldCell + " to " + myCell + " (MP used: " + mpUsed + ")");
            }
            return mpUsed > 0;
        }
    }
    
    // Fallback: Move away without weapon consideration
    var bestCell = findEscapePosition();
    if (bestCell != null) {
        var oldCell = myCell;
        var mpUsed = moveTowardCells([bestCell], myMP);
        myCell = getCell();
        myMP = getMP();
        
        if (debugEnabled) {
            debugW("EMERGENCY ESCAPE: From " + oldCell + " to " + myCell + " (MP used: " + mpUsed + ")");
        }
        return mpUsed > 0;
    }
    
    if (debugEnabled) {
        debugW("EMERGENCY MOVE: No escape cells found");
    }
    return false;
}

// === FIND TACTICAL POSITION FOR SPECIFIC WEAPON ===
function findTacticalPosition(weapon, weaponName) {
    var minRange = getWeaponMinRange(weapon);
    var maxRange = getWeaponMaxRange(weapon);
    var bestCell = null;
    var bestScore = 0;
    
    if (debugEnabled) {
        debugW("TACTICAL: Finding " + weaponName + " position (range " + minRange + "-" + maxRange + ")");
    }
    
    // Check cells within MP range
    for (var x = getCellX(myCell) - myMP; x <= getCellX(myCell) + myMP; x++) {
        for (var y = getCellY(myCell) - myMP; y <= getCellY(myCell) + myMP; y++) {
            var cell = getCellFromXY(x, y);
            
            if (cell != null && cell != -1 && cell != myCell) {
                var moveDistance = getCellDistance(myCell, cell);
                var enemyDistance = getCellDistance(cell, enemyCell);
                
                // Must be reachable and in weapon range
                if (moveDistance <= myMP && enemyDistance >= minRange && enemyDistance <= maxRange) {
                    // Check LOS for ranged weapons (not Sword or Katana)
                    if (weapon != WEAPON_SWORD && weapon != WEAPON_KATANA && !lineOfSight(cell, enemyCell)) {
                        continue; // Need LOS for ranged weapons
                    }
                    
                    // Score: prefer safer distances (farther from enemy) but within weapon range
                    var score = enemyDistance;
                    
                    // Bonus for staying within optimal range
                    var optimalRange = (minRange + maxRange) / 2;
                    var rangeScore = 10 - abs(enemyDistance - optimalRange);
                    score += rangeScore;
                    
                    if (score > bestScore) {
                        bestScore = score;
                        bestCell = cell;
                    }
                }
            }
        }
    }
    
    if (bestCell != null && debugEnabled) {
        var distance = getCellDistance(bestCell, enemyCell);
        debugW("TACTICAL: Found " + weaponName + " position " + bestCell + " at distance " + distance);
    }
    
    return bestCell;
}

// === B-LASER ALIGNMENT POSITION FINDER ===
function findBLaserAlignmentPosition() {
    var bestCell = null;
    var bestScore = 0;
    var minRange = getWeaponMinRange(WEAPON_B_LASER);
    var maxRange = getWeaponMaxRange(WEAPON_B_LASER);
    
    if (debugEnabled) {
        debugW("Finding B-Laser alignment position (range " + minRange + "-" + maxRange + ")");
    }
    
    // Check cells within MP range for X or Y axis alignment with enemy
    for (var x = getCellX(myCell) - myMP; x <= getCellX(myCell) + myMP; x++) {
        for (var y = getCellY(myCell) - myMP; y <= getCellY(myCell) + myMP; y++) {
            var cell = getCellFromXY(x, y);
            
            if (cell != null && cell != -1 && cell != myCell) {
                var moveDistance = getCellDistance(myCell, cell);
                var enemyDistance = getCellDistance(cell, enemyCell);
                
                // Check if within movement range and weapon range
                if (moveDistance <= myMP && enemyDistance >= minRange && enemyDistance <= maxRange) {
                    // Check for X or Y axis alignment (like M-Laser)
                    var cellX = getCellX(cell);
                    var cellY = getCellY(cell);
                    var enemyX = getCellX(enemyCell);
                    var enemyY = getCellY(enemyCell);
                    
                    var xAligned = (cellX == enemyX);
                    var yAligned = (cellY == enemyY);
                    
                    // Must be aligned on exactly one axis (XOR)
                    if (xAligned != yAligned) {
                        // Score based on distance (closer is better for emergency)
                        var score = 100 - enemyDistance;
                        if (score > bestScore) {
                            bestScore = score;
                            bestCell = cell;
                        }
                    }
                }
            }
        }
    }
    
    if (debugEnabled && bestCell != null) {
        var distance = getCellDistance(bestCell, enemyCell);
        debugW("Found B-Laser alignment position " + bestCell + " at distance " + distance);
    }
    
    return bestCell;
}

// === NEUTRINO DIAGONAL POSITION FINDER ===
function findNeutrinoDiagonalPosition() {
    var bestCell = null;
    var bestScore = 0;
    var minRange = getWeaponMinRange(WEAPON_NEUTRINO);
    var maxRange = getWeaponMaxRange(WEAPON_NEUTRINO);
    
    if (debugEnabled) {
        debugW("Finding Neutrino diagonal position (range " + minRange + "-" + maxRange + ")");
    }
    
    // Check cells within MP range for diagonal alignment with enemy
    for (var x = getCellX(myCell) - myMP; x <= getCellX(myCell) + myMP; x++) {
        for (var y = getCellY(myCell) - myMP; y <= getCellY(myCell) + myMP; y++) {
            var cell = getCellFromXY(x, y);
            
            if (cell != null && cell != -1 && cell != myCell) {
                var moveDistance = getCellDistance(myCell, cell);
                var enemyDistance = getCellDistance(cell, enemyCell);
                
                // Check if within movement range and weapon range
                if (moveDistance <= myMP && enemyDistance >= minRange && enemyDistance <= maxRange) {
                    // Check for diagonal alignment
                    var cellX = getCellX(cell);
                    var cellY = getCellY(cell);
                    var enemyX = getCellX(enemyCell);
                    var enemyY = getCellY(enemyCell);
                    
                    var dx = abs(cellX - enemyX);
                    var dy = abs(cellY - enemyY);
                    
                    // Must be diagonally aligned (dx == dy and not on same cell)
                    if (dx == dy && dx > 0) {
                        // Score based on distance (farther is better for emergency)
                        var score = enemyDistance;
                        if (score > bestScore) {
                            bestScore = score;
                            bestCell = cell;
                        }
                    }
                }
            }
        }
    }
    
    if (debugEnabled && bestCell != null) {
        var distance = getCellDistance(bestCell, enemyCell);
        debugW("Found Neutrino diagonal position " + bestCell + " at distance " + distance);
    }
    
    return bestCell;
}

// Note: findMLaserAlignmentPosition is defined in movement/pathfinding.ls

// === FALLBACK ESCAPE POSITION ===
function findEscapePosition() {
    var currentDistance = getCellDistance(myCell, enemyCell);
    var bestCell = null;
    var maxDistance = 0;
    
    // Phase 1: Find cells that are farther from enemy (ideal)
    for (var x = getCellX(myCell) - myMP; x <= getCellX(myCell) + myMP; x++) {
        for (var y = getCellY(myCell) - myMP; y <= getCellY(myCell) + myMP; y++) {
            var cell = getCellFromXY(x, y);
            
            if (cell != null && cell != -1 && cell != myCell) {
                var moveDistance = getCellDistance(myCell, cell);
                var enemyDistance = getCellDistance(cell, enemyCell);
                
                // Accept cells we can reach that are farther from enemy
                if (moveDistance <= myMP && enemyDistance > currentDistance) {
                    if (enemyDistance > maxDistance) {
                        maxDistance = enemyDistance;
                        bestCell = cell;
                    }
                }
            }
        }
    }
    
    // Phase 2: If no farther cells found, accept same distance (kiting movement)
    if (bestCell == null) {
        if (debugEnabled) {
            debugW("ESCAPE FALLBACK: No farther cells, trying same distance");
        }
        
        for (var x = getCellX(myCell) - myMP; x <= getCellX(myCell) + myMP; x++) {
            for (var y = getCellY(myCell) - myMP; y <= getCellY(myCell) + myMP; y++) {
                var cell = getCellFromXY(x, y);
                
                if (cell != null && cell != -1 && cell != myCell) {
                    var moveDistance = getCellDistance(myCell, cell);
                    var enemyDistance = getCellDistance(cell, enemyCell);
                    
                    // Accept cells at same distance or slightly closer (tactical repositioning)
                    if (moveDistance <= myMP && enemyDistance >= currentDistance - 1) {
                        // Prefer cells that break LOS or provide cover
                        var score = enemyDistance;
                        if (!hasLOS(cell, enemyCell)) {
                            score += 10; // LOS breaking bonus
                        }
                        
                        if (score > maxDistance) {
                            maxDistance = score;
                            bestCell = cell;
                        }
                    }
                }
            }
        }
    }
    
    if (debugEnabled && bestCell != null) {
        var finalDistance = getCellDistance(bestCell, enemyCell);
        debugW("ESCAPE: Found position " + bestCell + " at distance " + finalDistance + " (current: " + currentDistance + ")");
    }
    
    return bestCell;
}

// === HIDE AND SEEK MECHANICS ===
function tryHideAndSeek() {
    // Find cells that break line of sight with enemy
    var hideCells = findCellsWithoutLOS(enemyCell, myMP);
    
    if (count(hideCells) == 0) return false;
    
    // Select best hiding spot (farthest from enemy)
    var bestHide = null;
    var maxDistance = 0;
    
    for (var i = 0; i < count(hideCells); i++) {
        var cell = hideCells[i];
        var distance = getCellDistance(cell, enemyCell);
        
        // Prefer cells that are farther away and have cover
        var score = distance;
        if (countAdjacentObstacles(cell) > 0) {
            score += 2; // Bonus for cover
        }
        
        if (score > maxDistance) {
            maxDistance = score;
            bestHide = cell;
        }
    }
    
    if (bestHide != null) {
        // Move toward hiding spot
        var path = aStar(myCell, bestHide, myMP);
        if (path != null) {
            executeMovement({path: path, targetCell: bestHide});
            return true;
        }
    }
    
    return false;
}

// === EMERGENCY TELEPORTATION ===
function tryEmergencyTeleport() {
    var hasChip = inArray(getChips(), CHIP_TELEPORTATION);
    var chipCooldown = getCooldown(CHIP_TELEPORTATION);
    var chipCost = getChipCost(CHIP_TELEPORTATION);
    var canUse = canUseChip(CHIP_TELEPORTATION, getEntity());
    
    if (debugEnabled) {
        debugW("TELEPORT CHECK: hasChip=" + hasChip + ", cooldown=" + chipCooldown + 
               ", cost=" + chipCost + ", TP=" + myTP + ", canUse=" + canUse);
    }
    
    if (!canUse) {
        if (debugEnabled) {
            if (!hasChip) {
                debugW("TELEPORT FAIL: Chip not equipped");
            } else if (chipCooldown > 0) {
                debugW("TELEPORT FAIL: On cooldown (" + chipCooldown + " turns)");
            } else if (myTP < chipCost) {
                debugW("TELEPORT FAIL: Not enough TP (" + myTP + "/" + chipCost + ")");
            } else {
                debugW("TELEPORT FAIL: Unknown reason");
            }
        }
        return false;
    }
    
    var teleportRange = 12;
    var safeCells = [];
    
    var currentEnemyDistance = getCellDistance(myCell, enemyCell);
    
    // Find all cells within teleport range that are farther from enemy
    for (var x = getCellX(myCell) - teleportRange; x <= getCellX(myCell) + teleportRange; x++) {
        for (var y = getCellY(myCell) - teleportRange; y <= getCellY(myCell) + teleportRange; y++) {
            var cell = getCellFromXY(x, y);
            
            if (cell != null && cell != -1) {
                var teleportDistance = getCellDistance(myCell, cell);
                var enemyDistance = getCellDistance(cell, enemyCell);
                
                // Check if cell is walkable (not an obstacle)
                var isWalkable = (getCellContent(cell) == CELL_EMPTY);
                
                // Accept cells that are farther from enemy and walkable
                if (teleportDistance <= teleportRange && enemyDistance > currentEnemyDistance && isWalkable) {
                    push(safeCells, cell);
                }
            }
        }
    }
    
    if (count(safeCells) == 0) {
        if (debugEnabled) {
            debugW("TELEPORT FAIL: No cells farther from enemy within range " + teleportRange + " (current distance: " + currentEnemyDistance + ")");
        }
        return false;
    }
    
    if (debugEnabled) {
        debugW("TELEPORT: Found " + count(safeCells) + " safe teleport cells");
    }
    
    // Select best teleport target (prioritize LOS break, then distance, then cover)
    var bestTeleport = null;
    var bestScore = 0;
    
    for (var i = 0; i < count(safeCells); i++) {
        var cell = safeCells[i];
        var distance = getCellDistance(cell, enemyCell);
        var cover = countAdjacentObstacles(cell);
        var losBreak = !hasLOS(cell, enemyCell);
        
        // Score: LOS break bonus (100) + distance + cover bonus
        var score = distance + cover * 2;
        if (losBreak) {
            score += 100; // Huge bonus for breaking LOS
        }
        
        if (score > bestScore) {
            bestScore = score;
            bestTeleport = cell;
        }
    }
    
    if (bestTeleport != null) {
        if (debugEnabled) {
            debugW("TELEPORT: Attempting teleport to cell " + bestTeleport);
        }
        var result = useChipOnCell(CHIP_TELEPORTATION, bestTeleport);
        if (debugEnabled) {
            debugW("TELEPORT RESULT: " + result);
        }
        return result;
    }
    
    if (debugEnabled) {
        debugW("TELEPORT FAIL: No best teleport target found");
    }
    return false;
}

// === DESPERATION ATTACK ===
function tryDesperationAttack() {
    var estimatedDamage = estimateMyDamageOnPrimary();
    
    // Only go for desperation attack if we can potentially kill enemy
    if (estimatedDamage < enemyHP * 0.8) return false;
    
    if (debugEnabled) {
        debugW("Desperation attack: estimated damage " + estimatedDamage + " vs enemy HP " + enemyHP);
    }
    
    // Execute combat with all remaining TP
    executeCombat(myCell, null); // No pre-calculated weapon in emergency mode
    return true;
}

// === DEFENSIVE RETREAT ===
function tryDefensiveRetreat() {
    // Move away from enemy using all MP
    var retreatCells = [];
    var currentDistance = getCellDistance(myCell, enemyCell);
    
    // Find cells that are farther from enemy
    for (var range = 1; range <= myMP; range++) {
        var cells = getCellsAtExactDistance(myCell, range);
        
        for (var i = 0; i < count(cells); i++) {
            var cell = cells[i];
            var distance = getCellDistance(cell, enemyCell);
            
            if (distance > currentDistance) {
                push(retreatCells, cell);
            }
        }
    }
    
    if (count(retreatCells) > 0) {
        // Pick cell that's farthest from enemy
        var bestRetreat = retreatCells[0];
        var maxDistance = getCellDistance(bestRetreat, enemyCell);
        
        for (var i = 1; i < count(retreatCells); i++) {
            var cell = retreatCells[i];
            var distance = getCellDistance(cell, enemyCell);
            
            if (distance > maxDistance) {
                maxDistance = distance;
                bestRetreat = cell;
            }
        }
        
        // Move to retreat position
        var path = aStar(myCell, bestRetreat, myMP);
        if (path != null) {
            executeMovement({path: path, targetCell: bestRetreat});
        }
    }
    
    // Use any remaining TP for defensive actions
    tryDefensiveChips();
}

// === KITING FUNCTIONS ===
function tryKitingMovement() {
    // Find cells that are farther from enemy and allow ranged attacks
    var currentDistance = getCellDistance(myCell, enemyCell);
    var kiteCells = [];
    var weapons = getWeapons();
    
    // Find the longest range weapon we have
    var maxWeaponRange = 0;
    for (var i = 0; i < count(weapons); i++) {
        var weaponRange = getWeaponMaxRange(weapons[i]);
        if (weaponRange > maxWeaponRange) {
            maxWeaponRange = weaponRange;
        }
    }
    
    // If no weapons, use chip range
    if (maxWeaponRange == 0) {
        maxWeaponRange = 8; // Typical chip range
    }
    
    // Find cells within our movement range that are farther from enemy
    for (var range = 1; range <= myMP; range++) {
        var cells = getCellsAtExactDistance(myCell, range);
        
        for (var i = 0; i < count(cells); i++) {
            var cell = cells[i];
            var distance = getCellDistance(cell, enemyCell);
            
            // Must be farther from enemy and within weapon range
            if (distance > currentDistance && distance <= maxWeaponRange) {
                // Prefer cells with LOS for attacking
                if (hasLOS(cell, enemyCell)) {
                    push(kiteCells, cell);
                }
            }
        }
    }
    
    if (count(kiteCells) == 0) return false;
    
    // Select best kiting position (optimal range for our best weapon)
    var bestKite = null;
    var bestScore = 0;
    
    for (var i = 0; i < count(kiteCells); i++) {
        var cell = kiteCells[i];
        var distance = getCellDistance(cell, enemyCell);
        
        // Score based on optimal weapon range
        var score = 0;
        for (var j = 0; j < count(weapons); j++) {
            var weapon = weapons[j];
            var minRange = getWeaponMinRange(weapon);
            var maxRange = getWeaponMaxRange(weapon);
            
            if (distance >= minRange && distance <= maxRange) {
                score += 100; // Can use weapon from here
                
                // Bonus for being at optimal range (mid-range for most weapons)
                var optimalRange = (minRange + maxRange) / 2;
                var rangeDiff = abs(distance - optimalRange);
                score += max(0, 50 - rangeDiff * 5);
            }
        }
        
        // Bonus for distance from enemy (safer)
        score += distance;
        
        if (score > bestScore) {
            bestScore = score;
            bestKite = cell;
        }
    }
    
    if (bestKite != null) {
        // Move to kiting position
        var path = aStar(myCell, bestKite, myMP);
        if (path != null) {
            executeMovement({path: path, targetCell: bestKite});
            return true;
        }
    }
    
    return false;
}

function tryKitingAttack() {
    // Use remaining TP to attack from safe distance
    if (myTP < 3) return false; // Need at least some TP
    
    var distance = getCellDistance(myCell, enemyCell);
    var weapons = getWeapons();
    
    // PRIORITY 1: Try FLAME_THROWER first - POISON HEALING + LINE WEAPON
    if (inArray(weapons, WEAPON_FLAME_THROWER)) {
        var minRange = getWeaponMinRange(WEAPON_FLAME_THROWER);
        var maxRange = getWeaponMaxRange(WEAPON_FLAME_THROWER);
        var cost = getWeaponCost(WEAPON_FLAME_THROWER);
        
        if (distance >= minRange && distance <= maxRange && isOnSameLine(myCell, enemyCell) && myTP >= cost) {
            if (debugEnabled) {
                debugW("KITING ATTACK: Using Flame Thrower for poison healing at distance " + distance);
            }
            
            // Switch to Flame Thrower if needed
            if (getWeapon() != WEAPON_FLAME_THROWER) {
                if (myTP >= cost + 1) {
                    setWeapon(WEAPON_FLAME_THROWER);
                    myTP--;
                    if (debugEnabled) {
                        debugW("EMERGENCY: Switched to Flame Thrower");
                    }
                } else {
                    return false; // Not enough TP
                }
            }
            
            // Attack with Flame Thrower (poison + lifesteal healing)
            if (canUseWeapon(enemy)) {
                useWeapon(enemy);
                if (debugEnabled) {
                    debugW("EMERGENCY: Used Flame Thrower for poison healing");
                }
                return true;
            }
        }
    }
    
    // PRIORITY 2: Try B-Laser - HEALING + DAMAGE + cheaper cost (5 TP vs 8 TP)
    if (inArray(weapons, WEAPON_B_LASER)) {
        var minRange = getWeaponMinRange(WEAPON_B_LASER);
        var maxRange = getWeaponMaxRange(WEAPON_B_LASER);
        
        if (distance >= minRange && distance <= maxRange && isOnSameLine(myCell, enemyCell)) {
            if (debugEnabled) {
                debugW("KITING ATTACK: Using B-Laser for healing + damage at distance " + distance);
            }
            
            // Switch to B-Laser if needed
            if (getWeapon() != WEAPON_B_LASER) {
                if (myTP >= 6) { // 1 TP to switch + 5 TP to attack
                    setWeapon(WEAPON_B_LASER);
                    if (debugEnabled) {
                        debugW("EMERGENCY: Switched to B-Laser");
                    }
                } else {
                    return false; // Not enough TP
                }
            }
            
            // Attack with B-Laser (heals + damages)
            if (canUseWeapon(enemy)) {
                useWeapon(enemy);
                if (debugEnabled) {
                    debugW("EMERGENCY: Used B-Laser for healing + damage");
                }
                return true;
            }
        }
    }
    
    // PRIORITY 2: Try Enhanced Lightninger for healing bonus (100 HP flat + lifesteal)
    if (inArray(weapons, WEAPON_ENHANCED_LIGHTNINGER)) {
        var minRange = getWeaponMinRange(WEAPON_ENHANCED_LIGHTNINGER);
        var maxRange = getWeaponMaxRange(WEAPON_ENHANCED_LIGHTNINGER);
        var cost = getWeaponCost(WEAPON_ENHANCED_LIGHTNINGER);
        
        if (distance >= minRange && distance <= maxRange && myTP >= cost) {
            if (canUseWeapon(enemy)) {
                // Switch weapon if needed
                if (getWeapon() != WEAPON_ENHANCED_LIGHTNINGER) {
                    if (myTP >= cost + 1) {
                        setWeapon(WEAPON_ENHANCED_LIGHTNINGER);
                        myTP--;
                        if (debugEnabled) {
                            debugW("EMERGENCY: Switched to Enhanced Lightninger for healing");
                        }
                    } else {
                        return false; // Not enough TP
                    }
                }
                
                // Use Enhanced Lightninger multiple times for maximum healing (KITING VERSION)
                var maxUses = getWeaponMaxUses(WEAPON_ENHANCED_LIGHTNINGER);
                
                // Smart REGENERATION reservation logic for kiting
                var tpReservedForRegen = 0;
                var currentTP = getTP();
                var maxPossibleUses = floor(currentTP / cost);
                var possibleWithRegen = canUseChip(CHIP_REGENERATION, getEntity()) ? 
                    floor((currentTP - getChipCost(CHIP_REGENERATION)) / cost) : 0;
                
                // Only reserve TP for REGENERATION if it doesn't prevent multiple weapon uses
                if (canUseChip(CHIP_REGENERATION, getEntity()) && (maxPossibleUses <= 1 || possibleWithRegen >= 1)) {
                    tpReservedForRegen = getChipCost(CHIP_REGENERATION);
                }
                
                var availableUses = floor((currentTP - tpReservedForRegen) / cost);
                var actualUses = (maxUses > 0) ? min(availableUses, maxUses) : availableUses;
                
                if (debugEnabled) {
                    debugW("ENHANCED LIGHTNINGER KITING: Using " + actualUses + " times (max=" + maxUses + ", available=" + availableUses + ")");
                    debugW("KITING: currentTP=" + currentTP + ", weaponCost=" + cost + ", tpReservedForRegen=" + tpReservedForRegen);
                    debugW("KITING: maxPossible=" + maxPossibleUses + ", possibleWithRegen=" + possibleWithRegen);
                }
                
                var successfulUses = 0;
                for (var use = 0; use < actualUses && canUseWeapon(enemy); use++) {
                    if (debugEnabled) {
                        debugW("KITING: Attempt " + (use + 1) + "/" + actualUses + " - TP before: " + getTP());
                    }
                    var result = useWeapon(enemy);
                    successfulUses++;
                    if (debugEnabled) {
                        debugW("ENHANCED LIGHTNINGER KITING: Attack " + (use + 1) + "/" + actualUses + " - TP after: " + getTP());
                    }
                }
                
                if (debugEnabled) {
                    debugW("KITING COMPLETE: Enhanced Lightninger attack sequence finished");
                }
                
                // Then heal with regeneration if it was reserved (and we have TP)
                if (tpReservedForRegen > 0 && canUseChip(CHIP_REGENERATION, getEntity()) && getTP() >= tpReservedForRegen) {
                    useChip(CHIP_REGENERATION, getEntity());
                    if (debugEnabled) {
                        debugW("KITING: Used REGENERATION after Enhanced Lightninger (reserved)");
                    }
                } else if (tpReservedForRegen == 0 && canUseChip(CHIP_REGENERATION, getEntity())) {
                    // Try to use REGENERATION if we didn't reserve it but still have TP
                    if (getTP() >= getChipCost(CHIP_REGENERATION)) {
                        useChip(CHIP_REGENERATION, getEntity());
                        if (debugEnabled) {
                            debugW("KITING: Used REGENERATION after Enhanced Lightninger (opportunistic)");
                        }
                    }
                }
                
                return successfulUses > 0;
            }
        }
    }
    
    // PRIORITY 3: Try NEUTRINO for diagonal vulnerability attacks
    if (inArray(weapons, WEAPON_NEUTRINO)) {
        var minRange = getWeaponMinRange(WEAPON_NEUTRINO);
        var maxRange = getWeaponMaxRange(WEAPON_NEUTRINO);
        var cost = getWeaponCost(WEAPON_NEUTRINO);
        
        // Check diagonal alignment
        var cellX = getCellX(myCell);
        var cellY = getCellY(myCell);
        var enemyX = getCellX(enemyCell);
        var enemyY = getCellY(enemyCell);
        var dx = abs(cellX - enemyX);
        var dy = abs(cellY - enemyY);
        var isDiagonal = (dx == dy && dx > 0);
        
        if (distance >= minRange && distance <= maxRange && isDiagonal && myTP >= cost) {
            if (debugEnabled) {
                debugW("KITING ATTACK: Using Neutrino for vulnerability at distance " + distance);
            }
            
            // Switch to Neutrino if needed
            if (getWeapon() != WEAPON_NEUTRINO) {
                if (myTP >= cost + 1) {
                    setWeapon(WEAPON_NEUTRINO);
                    myTP--;
                    if (debugEnabled) {
                        debugW("EMERGENCY: Switched to Neutrino");
                    }
                } else {
                    return false; // Not enough TP
                }
            }
            
            // Attack with Neutrino (vulnerability debuff)
            if (canUseWeapon(enemy)) {
                useWeapon(enemy);
                if (debugEnabled) {
                    debugW("EMERGENCY: Used Neutrino for vulnerability");
                }
                return true;
            }
        }
    }
    
    // PRIORITY 4: Try DESTROYER for debuff attacks
    if (inArray(weapons, WEAPON_DESTROYER)) {
        var minRange = getWeaponMinRange(WEAPON_DESTROYER);
        var maxRange = getWeaponMaxRange(WEAPON_DESTROYER);
        var cost = getWeaponCost(WEAPON_DESTROYER);
        
        if (distance >= minRange && distance <= maxRange && myTP >= cost) {
            if (debugEnabled) {
                debugW("KITING ATTACK: Using Destroyer for debuff at distance " + distance);
            }
            
            // Switch to Destroyer if needed
            if (getWeapon() != WEAPON_DESTROYER) {
                if (myTP >= cost + 1) {
                    setWeapon(WEAPON_DESTROYER);
                    myTP--;
                    if (debugEnabled) {
                        debugW("EMERGENCY: Switched to Destroyer");
                    }
                } else {
                    return false; // Not enough TP
                }
            }
            
            // Attack with Destroyer (strength debuff)
            if (canUseWeapon(enemy)) {
                useWeapon(enemy);
                if (debugEnabled) {
                    debugW("EMERGENCY: Used Destroyer for debuff");
                }
                return true;
            }
        }
    }
    
    // PRIORITY 5: Try Rhino for close-range high DPS
    if (inArray(weapons, WEAPON_RHINO)) {
        var minRange = getWeaponMinRange(WEAPON_RHINO);
        var maxRange = getWeaponMaxRange(WEAPON_RHINO);
        
        if (distance >= minRange && distance <= maxRange) {
            if (debugEnabled) {
                debugW("KITING ATTACK: Using Rhino for high DPS at distance " + distance);
            }
            
            // Switch to Rhino if needed
            if (getWeapon() != WEAPON_RHINO) {
                if (myTP >= 6) { // 1 TP to switch + 5 TP to attack
                    setWeapon(WEAPON_RHINO);
                    if (debugEnabled) {
                        debugW("EMERGENCY: Switched to Rhino");
                    }
                } else {
                    return false; // Not enough TP
                }
            }
            
            // Attack with Rhino for maximum damage
            if (canUseWeapon(enemy)) {
                useWeapon(enemy);
                if (debugEnabled) {
                    debugW("EMERGENCY: Used Rhino for high damage");
                }
                return true;
            }
        }
    }
    
    // Fallback: Try other weapons at current range
    for (var i = 0; i < count(weapons); i++) {
        var weapon = weapons[i];
        if (weapon == WEAPON_FLAME_THROWER || weapon == WEAPON_ENHANCED_LIGHTNINGER || 
            weapon == WEAPON_B_LASER || weapon == WEAPON_NEUTRINO || 
            weapon == WEAPON_DESTROYER || weapon == WEAPON_RHINO) continue; // Already tried above
        
        var minRange = getWeaponMinRange(weapon);
        var maxRange = getWeaponMaxRange(weapon);
        var cost = getWeaponCost(weapon);
        
        if (distance >= minRange && distance <= maxRange && myTP >= cost) {
            if (canUseWeapon(enemy)) {
                // Switch weapon if needed
                if (getWeapon() != weapon) {
                    if (myTP >= cost + 1) {
                        setWeapon(weapon);
                        myTP--;
                    } else {
                        continue; // Not enough TP to switch and use
                    }
                }
                
                // Use weapon
                var result = useWeapon(enemy);
                myTP -= cost;
                
                if (debugEnabled) {
                    debugW("Kiting attack: Used " + weapon + " at range " + distance);
                }
                return true;
            }
        }
    }
    
    // Fallback to chips if no weapons available
    var chips = getAvailableDamageChips();
    for (var i = 0; i < count(chips); i++) {
        var chip = chips[i];
        if (canUseChip(chip, enemy)) {
            var chipCost = getChipCost(chip);
            if (myTP >= chipCost) {
                useChip(chip, enemy);
                myTP -= chipCost;
                
                if (debugEnabled) {
                    debugW("Kiting attack: Used chip " + chip);
                }
                return true;
            }
        }
    }
    
    return false;
}

// === UTILITY FUNCTIONS ===
function findCellsWithoutLOS(enemyCell, maxDistance) {
    var hideCells = [];
    
    for (var range = 1; range <= maxDistance; range++) {
        var cells = getCellsAtExactDistance(myCell, range);
        
        for (var i = 0; i < count(cells); i++) {
            var cell = cells[i];
            if (!hasLOS(cell, enemyCell)) {
                push(hideCells, cell);
            }
        }
    }
    
    return hideCells;
}

// === ENEMY DAMAGE ESTIMATION (TARGET-SPECIFIC) ===
function estimateEnemyDamageNextTurn(enemyEntity) {
    if (enemyEntity == null || getLife(enemyEntity) <= 0) return 0;
    
    // Simple damage estimation based on enemy weapons
    var enemyWeapons = getWeapons(enemyEntity);
    var distance = getCellDistance(myCell, getCell(enemyEntity));
    var totalDamage = 0;
    
    for (var i = 0; i < count(enemyWeapons); i++) {
        var weapon = enemyWeapons[i];
        var minRange = getWeaponMinRange(weapon);
        var maxRange = getWeaponMaxRange(weapon);
        
        if (distance >= minRange && distance <= maxRange) {
            // Use our weapon damage estimation for consistency
            var baseDamage = getWeaponBaseDamage(weapon);
            var strengthMultiplier = 1 + (getStrength(enemyEntity) / 100.0);
            var damage = baseDamage * strengthMultiplier;
            totalDamage += damage;
        }
    }
    
    // Add chip damage potential
    var currentEnemyTP = getTP(enemyEntity);
    if (currentEnemyTP >= 4) {
        totalDamage += 50; // Lightning chip estimation
    }
    
    return floor(totalDamage);
}

// === MY DAMAGE ESTIMATION (TARGET-SPECIFIC) ===
function estimateMyDamageThisTurn(targetEntity) {
    if (targetEntity == null || getLife(targetEntity) <= 0) return 0;
    
    var targetCell = getCell(targetEntity);
    var weapons = getWeapons();
    var maxDamage = 0;
    
    // Check damage from current position
    var currentPositionDamage = 0;
    for (var i = 0; i < count(weapons); i++) {
        var weapon = weapons[i];
        var damage = calculateWeaponDamageFromCell(weapon, myCell, targetCell);
        currentPositionDamage += damage;
    }
    
    maxDamage = currentPositionDamage;
    
    // If we have movement points, check nearby optimal positions
    if (myMP > 0) {
        var bestMoveDamage = 0;
        
        // Check weapon-optimal positions within movement range
        for (var i = 0; i < count(weapons); i++) {
            var weapon = weapons[i];
            var weaponCost = getWeaponCost(weapon);
            if (weaponCost > myTP) continue;
            
            var minRange = getWeaponMinRange(weapon);
            var maxRange = getWeaponMaxRange(weapon);
            
            // Check optimal range positions
            for (var range = minRange; range <= min(maxRange, minRange + 3); range++) {
                var optimalPositions = getCellsAtExactDistance(targetCell, range);
                
                for (var j = 0; j < min(count(optimalPositions), 8); j++) {
                    var testCell = optimalPositions[j];
                    var moveDistance = getCellDistance(myCell, testCell);
                    
                    if (moveDistance <= myMP && getCellContent(testCell) == CELL_EMPTY) {
                        var positionDamage = 0;
                        
                        // Calculate all weapon damage from this position
                        for (var k = 0; k < count(weapons); k++) {
                            var testWeapon = weapons[k];
                            var damage = calculateWeaponDamageFromCell(testWeapon, testCell, targetCell);
                            positionDamage += damage;
                        }
                        
                        if (positionDamage > bestMoveDamage) {
                            bestMoveDamage = positionDamage;
                        }
                    }
                }
            }
        }
        
        maxDamage = max(maxDamage, bestMoveDamage);
    }
    
    // Add potential chip damage
    if (myTP >= 4) {
        maxDamage += 50; // Lightning chip damage
    }
    
    if (debugEnabled) {
        debugW("DAMAGE ESTIMATE: Current=" + floor(currentPositionDamage) + ", Best=" + floor(maxDamage) + " vs Enemy HP=" + getLife(targetEntity));
    }
    
    return floor(maxDamage);
}

// === LEGACY DAMAGE ESTIMATION FUNCTIONS (for backward compatibility) ===
function estimatePrimaryEnemyDamage() {
    if (primaryTarget == null) return 0;
    return estimateEnemyDamageNextTurn(primaryTarget);
}

function estimateMyDamageOnPrimary() {
    if (primaryTarget == null) return 0;
    return estimateMyDamageThisTurn(primaryTarget);
}

function tryDefensiveChips() {
    // Try to use any defensive chips with remaining TP
    if (myTP >= 4 && canUseChip(CHIP_SHIELD, getEntity())) {
        useChip(CHIP_SHIELD, getEntity());
    }
    
    if (myTP >= 3 && canUseChip(CHIP_PROTEIN, getEntity())) {
        useChip(CHIP_PROTEIN, getEntity());
    }
}