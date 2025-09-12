// V7 Module: decision/emergency.ls
// Panic mode and emergency decisions

// === EMERGENCY MODE DETECTION ===
function isEmergencyMode() {
    if (enemy == null) return false;
    
    // Low HP threshold
    if ((myHP / myMaxHP) < EMERGENCY_HP_THRESHOLD) return true;
    
    // Enemy can kill us next turn
    var estimatedEnemyDamage = estimateEnemyDamageNextTurn();
    if (estimatedEnemyDamage >= myHP) return true;
    
    // We can kill enemy this turn (go for it!)
    var estimatedMyDamage = estimateMyDamageThisTurn();
    if (estimatedMyDamage >= enemyHP && estimatedMyDamage > 0) return false;
    
    return false;
}

// === EMERGENCY MODE EXECUTION ===
function executeEmergencyMode() {
    if (debugEnabled) {
        debugE("EMERGENCY MODE ACTIVATED! HP: " + myHP + "/" + myMaxHP);
    }
    
    // Check if we need healing (and haven't used it this turn)
    var needsHealing = (canUseChip(CHIP_REGENERATION, getEntity()) || canUseChip(CHIP_CURE, getEntity()));
    
    if (needsHealing) {
        // Priority 1: Teleport to safety FIRST (before healing)
        if (tryEmergencyTeleport()) {
            if (debugEnabled) {
                debugW("Emergency teleport executed, will heal after");
            }
            // Now heal in safety
            tryEmergencyHealing();
            return;
        } else {
            if (debugEnabled) {
                debugW("Emergency teleport FAILED - checking why");
            }
        }
        
        // Priority 2: Move away from enemy if teleport failed
        if (tryEmergencyMovement()) {
            if (debugEnabled) {
                debugW("Moved to safety, will try Enhanced Lightninger healing");
            }
            // Now try Enhanced Lightninger for healing bonus, fallback to regular healing
            if (!tryEmergencyHealingWithAttack()) {
                tryEmergencyHealing();
            }
            return;
        }
        
        // Priority 3: Heal immediately if we can't escape, but try Enhanced Lightninger for bonus healing
        if (tryEmergencyHealingWithAttack()) {
            if (debugEnabled) {
                debugW("Emergency healing + Enhanced Lightninger attack applied");
            }
            return;
        }
        
        // Priority 4: Just heal if Enhanced Lightninger isn't available
        if (tryEmergencyHealing()) {
            if (debugEnabled) {
                debugW("Emergency healing applied (couldn't escape)");
            }
        }
    } else {
        // No healing available - use kiting strategy
        if (debugEnabled) {
            debugW("No healing available, initiating kiting strategy");
        }
        
        // Priority 1: Try to escape first (teleport or movement)
        if (tryEmergencyTeleport()) {
            if (debugEnabled) {
                debugW("Kiting: teleported to safety");
            }
            return;
        } else if (tryEmergencyMovement()) {
            if (debugEnabled) {
                debugW("Kiting: moved to tactical position - now trying to attack");
            }
            // Don't return - continue to attack after positioning
        }
        
        // Priority 2: If can't escape, attack with Enhanced Lightninger for healing
        if (tryKitingAttack()) {
            if (debugEnabled) {
                debugW("Kiting attack executed (couldn't escape)");
            }
            return;
        }
        
        // Priority 3: Break line of sight as last resort
        if (tryHideAndSeek()) {
            if (debugEnabled) {
                debugW("Attempting hide-and-seek");
            }
            return;
        }
    }
    
    // Priority 4: Go for kill if we can
    if (tryDesperationAttack()) {
        if (debugEnabled) {
            debugW("Desperation attack mode");
        }
        return;
    }
    
    // Priority 5: Move away and use any remaining TP for defense
    tryDefensiveRetreat();
}

// === EMERGENCY HEALING ===
function tryEmergencyHealing() {
    var healed = false;
    
    // Try Regeneration chip
    if (canUseChip(CHIP_REGENERATION, getEntity())) {
        useChip(CHIP_REGENERATION, getEntity());
        healed = true;
    }
    
    // Try any other healing chips
    if (canUseChip(CHIP_CURE, getEntity())) {
        useChip(CHIP_CURE, getEntity());
        healed = true;
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
        debugW("HEAL WITH ATTACK: hasLightninger=" + hasLightninger + ", distance=" + currentDistance + ", TP=" + myTP + "/" + minTpNeeded);
    }
    
    if (hasLightninger && myTP >= minTpNeeded) {
        // Check if Enhanced Lightninger is in range (5-12)
        if (currentDistance >= 5 && currentDistance <= 12) {
            // Switch to Enhanced Lightninger if needed
            if (getWeapon() != WEAPON_ENHANCED_LIGHTNINGER) {
                setWeapon(WEAPON_ENHANCED_LIGHTNINGER);
                if (debugEnabled) {
                    debugW("EMERGENCY: Switched to Enhanced Lightninger");
                }
            }
            
            // Check if we can use the weapon now
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
                    // HP ≤ 50%: Use REGENERATION instead
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
                        if (debugEnabled) {
                            debugW("SMART HEALING: HP ≤ 50% but REGENERATION not available");
                        }
                    }
                }
                
                return true;
            } else {
                if (debugEnabled) {
                    debugW("HEAL FAIL: Cannot use Enhanced Lightninger (LOS issue?)");
                }
            }
        } else {
            if (debugEnabled) {
                debugW("HEAL FAIL: Enhanced Lightninger out of range (" + currentDistance + " not in 5-12)");
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
    
    // Priority 1: Move to Enhanced Lightninger range (5-12) with LOS
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
    
    // Priority 2: Move to Rifle range (7-9) with LOS
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
    
    // Priority 3: Move to M-Laser range (6-10) with alignment
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
                    // Check LOS for ranged weapons (not Katana)
                    if (weapon != WEAPON_KATANA && !lineOfSight(cell, enemyCell)) {
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

// Note: findMLaserAlignmentPosition is defined in movement/pathfinding.ls

// === FALLBACK ESCAPE POSITION ===
function findEscapePosition() {
    var currentDistance = getCellDistance(myCell, enemyCell);
    var bestCell = null;
    var maxDistance = 0;
    
    // Find cells within MP range that are farther from enemy
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
    var estimatedDamage = estimateMyDamageThisTurn();
    
    // Only go for desperation attack if we can potentially kill enemy
    if (estimatedDamage < enemyHP * 0.8) return false;
    
    if (debugEnabled) {
        debugW("Desperation attack: estimated damage " + estimatedDamage + " vs enemy HP " + enemyHP);
    }
    
    // Execute combat with all remaining TP
    executeCombat(myCell);
    return true;
}

// === DEFENSIVE RETREAT ===
function tryDefensiveRetreat() {
    // Move away from enemy using all MP
    var retreatCells = [];
    var currentDistance = getCellDistance(myCell, enemyCell);
    
    // Find cells that are farther from enemy
    for (var range = 1; range <= myMP; range++) {
        var cells = getCellsAtDistance(myCell, range);
        
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
        var cells = getCellsAtDistance(myCell, range);
        
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
    
    // PRIORITY 1: Try B-Laser first - HEALING + DAMAGE + cheaper cost (5 TP vs 8 TP)
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
    
    // PRIORITY 3: Try Rhino for close-range high DPS
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
        if (weapon == WEAPON_ENHANCED_LIGHTNINGER || weapon == WEAPON_B_LASER || weapon == WEAPON_RHINO) continue; // Already tried above
        
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
    var chips = getDamageChips();
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
        var cells = getCellsAtDistance(myCell, range);
        
        for (var i = 0; i < count(cells); i++) {
            var cell = cells[i];
            if (!hasLOS(cell, enemyCell)) {
                push(hideCells, cell);
            }
        }
    }
    
    return hideCells;
}

function estimateEnemyDamageNextTurn() {
    if (enemy == null) return 0;
    
    // Simple damage estimation based on enemy weapons
    var enemyWeapons = getWeapons(enemy);
    var distance = getCellDistance(myCell, enemyCell);
    var totalDamage = 0;
    
    for (var i = 0; i < count(enemyWeapons); i++) {
        var weapon = enemyWeapons[i];
        var minRange = getWeaponMinRange(weapon);
        var maxRange = getWeaponMaxRange(weapon);
        
        if (distance >= minRange && distance <= maxRange) {
            var damage = getWeaponEffects(weapon)[0][1]; // Get base damage from weapon effects
            totalDamage += damage * (1 + getStrength(enemy) / 100.0);
        }
    }
    
    return totalDamage;
}

function estimateMyDamageThisTurn() {
    if (enemy == null) return 0;
    
    var weapons = getWeapons();
    var distance = getCellDistance(myCell, enemyCell);
    var totalDamage = 0;
    
    for (var i = 0; i < count(weapons); i++) {
        var weapon = weapons[i];
        var damage = calculateWeaponDamageFromCell(weapon, myCell, enemyCell);
        totalDamage += damage;
    }
    
    return totalDamage;
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