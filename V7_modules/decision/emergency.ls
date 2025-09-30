// V7 Module: decision/emergency.ls
// Panic mode and emergency decisions

// === MULTI-ENEMY EMERGENCY MODE DETECTION ===
function isEmergencyMode() {
    if (count(allEnemies) == 0) return false;
    
    // Low HP threshold
    if ((myHP / myMaxHP) < EMERGENCY_HP_THRESHOLD) return true;
    
    // Calculate combined threat from all enemies
    var totalEnemyThreat = 0;
    var immediateKillPossible = false;
    
    for (var i = 0; i < count(allEnemies); i++) {
        var enemyEntity = allEnemies[i];
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
            // Emergency override - staying aggressive to finish target
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
                // Emergency override - target critical, staying aggressive
            }
            return false;
        }
    }
    
    // Check if we actually have healing options before triggering emergency mode
    var hasRegenChip = inArray(getChips(), CHIP_REGENERATION);
    var regenAlreadyUsed = (lastChipUse[CHIP_REGENERATION] != null);
    var canUseRegen = hasRegenChip && !regenAlreadyUsed && canUseChip(CHIP_REGENERATION, getEntity());
    
    var hasLightninger = inArray(getWeapons(), WEAPON_ENHANCED_LIGHTNINGER);
    var distanceToEnemy = getCellDistance(myCell, enemyCell);
    var inLightningerRange = distanceToEnemy >= 6 && distanceToEnemy <= 10;
    var hasTPForLightninger = myTP >= 9;
    var canUseLightninger = hasLightninger && inLightningerRange && hasTPForLightninger && checkLineOfSight(myCell, enemyCell);
    
    var hasHealingOptions = canUseRegen || canUseLightninger;
    
    // Combined enemies can kill us next turn
    if (totalEnemyThreat >= myHP) {
        if (debugEnabled) {
            // Emergency threat detected - high damage potential
            if (!hasHealingOptions) {
                // No healing options, switching to aggressive combat
                return false; // No healing available, stay aggressive
            }
        }
        return hasHealingOptions; // Only go emergency if we can actually heal
    }
    
    // Outnumbered significantly (3+ enemies vs 1)
    if (count(allEnemies) >= 3 && (myHP / myMaxHP) < 0.5) {
        if (debugEnabled) {
            // Emergency - outnumbered with low HP
            if (!hasHealingOptions) {
                // No healing options, switching to aggressive combat
                return false; // No healing available, stay aggressive
            }
        }
        return hasHealingOptions; // Only go emergency if we can actually heal
    }
    
    return false;
}

// === SIMPLIFIED EMERGENCY MODE ===
function executeEmergencyMode() {
    // Priority 1: Try to heal with REGENERATION if available and not already used
    var hasRegenChip = inArray(getChips(), CHIP_REGENERATION);
    var regenAlreadyUsed = (lastChipUse[CHIP_REGENERATION] != null);
    var canUseRegen = hasRegenChip && !regenAlreadyUsed && canUseChip(CHIP_REGENERATION, getEntity());
    
    if (canUseRegen) {
        useChip(CHIP_REGENERATION, getEntity());
        lastChipUse[CHIP_REGENERATION] = getTurn(); // Mark as used
        myHP = getLife(); // Update HP after healing
        myTP = getTP();   // Update TP after healing
        if (debugEnabled) {
            // Used REGENERATION for emergency healing
        }
        // DON'T RETURN - continue with movement and attacks!
    } else if (debugEnabled) {
        // REGENERATION not available for emergency healing
    }

    // Priority 2: Apply CHIP_MIRROR for agility builds for defensive benefit
    if (isAgilityBuild && inArray(getChips(), CHIP_MIRROR)) {
        if (getCooldown(CHIP_MIRROR) == 0 && canUseChip(CHIP_MIRROR, getEntity()) && myTP >= 5) {
            useChip(CHIP_MIRROR, getEntity());
            myTP = getTP(); // Update TP after buff
            mirrorActive = true;
            mirrorRemainingTurns = 3;

            var reflectPercent = floor(5 + min(34, myAgility * 0.06));
            if (debugEnabled) {
                debugW("EMERGENCY: Applied MIRROR for defense (" + reflectPercent + "% reflection, AGI=" + myAgility + ")");
            }
        } else if (debugEnabled) {
            debugW("EMERGENCY: MIRROR not available - cooldown=" + getCooldown(CHIP_MIRROR) + ", TP=" + myTP);
        }
    }

    // Priority 3: REMOVED INDEPENDENT MOVEMENT - Let main pathfinding handle all movement
    // Emergency mode now focuses only on healing and combat decisions, not movement
    // This prevents position desync with the main pathfinding system
    if (debugEnabled) {
        debugW("EMERGENCY: Skipping independent movement, letting main pathfinding handle positioning");
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

// === UNIFIED EMERGENCY HEALING ===
function tryUnifiedEmergencyHealing(mode) {
    var healed = false;
    var myCurrentTP = getTP();
    var currentCell = getCell();
    var distanceToEnemy = getCellDistance(currentCell, enemyCell);
    var weapons = getWeapons();
    
    if (debugEnabled) {
        debugW("EMERGENCY HEAL (" + mode + "): TP=" + myCurrentTP + ", Distance=" + distanceToEnemy);
    }
    
    // Check if healing is actually available before attempting
    var hasRegenChip = inArray(getChips(), CHIP_REGENERATION);
    var regenAlreadyUsed = (lastChipUse[CHIP_REGENERATION] != null);
    var canUseRegen = hasRegenChip && !regenAlreadyUsed && canUseChip(CHIP_REGENERATION, getEntity());
    
    // Enhanced Lightninger healing + damage priority
    var hasLightninger = inArray(weapons, WEAPON_ENHANCED_LIGHTNINGER);
    var inRange = distanceToEnemy >= 6 && distanceToEnemy <= 10;
    var hasTP = myCurrentTP >= 9;
    var hasLineOfSight = checkLineOfSight(currentCell, enemyCell);
    var canUseLightninger = hasLightninger && inRange && hasTP && hasLineOfSight;
    
    // CRITICAL CHECK: Don't attempt healing if no healing options are available
    if (!canUseRegen && !canUseLightninger) {
        if (debugEnabled) {
            debugW("EMERGENCY HEAL FAIL: No healing options available");
            debugW("  - REGENERATION: hasChip=" + hasRegenChip + ", alreadyUsed=" + regenAlreadyUsed + ", canUse=" + canUseRegen);
            debugW("  - LIGHTNINGER: hasWeapon=" + hasLightninger + ", inRange=" + inRange + ", hasTP=" + hasTP + ", hasLOS=" + hasLineOfSight);
        }
        return false; // No healing available, don't waste time in emergency mode
    }
    
    if (canUseLightninger) {
        if (debugEnabled) {
            debugW("EMERGENCY: Using Enhanced Lightninger for healing + damage at distance " + distanceToEnemy);
        }
        
        if (mode == "simple") {
            // Simple single use
            useWeapon(primaryTarget);
            healed = true;
            myCurrentTP -= 9;
        } else if (mode == "smart") {
            // Smart multi-shot logic
            var hpBeforeShot = getLife();
            useWeapon(primaryTarget);
            var hpAfterShot = getLife();
            var hpPercent = hpAfterShot / getTotalLife();
            var currentTP = getTP();
            var lightningCost = 9;
            
            if (debugEnabled) {
                debugW("ENHANCED LIGHTNINGER: First shot - HP: " + hpBeforeShot + " → " + hpAfterShot + ", TP after: " + currentTP);
            }
            
            if (hpPercent > 0.5) {
                // HP > 50%: Fire again if we have TP
                if (currentTP >= lightningCost && canUseWeapon(primaryTarget)) {
                    useWeapon(primaryTarget);
                    if (debugEnabled) {
                        debugW("SMART HEALING: Second shot - HP > 50%");
                    }
                }
            } else {
                // HP ≤ 50%: Use REGENERATION if available
                if (canUseChip(CHIP_REGENERATION, getEntity()) && currentTP >= getChipCost(CHIP_REGENERATION)) {
                    useChip(CHIP_REGENERATION, getEntity());
                    if (debugEnabled) {
                        debugW("SMART HEALING: Used REGENERATION - HP ≤ 50%");
                    }
                } else if (currentTP >= lightningCost && canUseWeapon(primaryTarget)) {
                    useWeapon(primaryTarget);
                    if (debugEnabled) {
                        debugW("SMART HEALING: Second shot fallback - no REGENERATION");
                    }
                }
            }
            healed = true;
        }
        
        // Follow up with REGENERATION if in simple mode and available
        if (mode == "simple" && myCurrentTP >= 3 && canUseChip(CHIP_REGENERATION, getEntity())) {
            useChip(CHIP_REGENERATION, getEntity());
            if (debugEnabled) {
                debugW("EMERGENCY: Added REGENERATION for extra healing");
            }
        }
        
        return healed;
    }
    
    // REGENERATION chip fallback (re-declare variables locally)
    var regenAlreadyUsedLocal = (lastChipUse[CHIP_REGENERATION] != null);
    var canUseRegenLocal = canUseChip(CHIP_REGENERATION, getEntity());
    
    if (!regenAlreadyUsedLocal && canUseRegenLocal) {
        useChip(CHIP_REGENERATION, getEntity());
        lastChipUse[CHIP_REGENERATION] = getTurn();
        healed = true;
        if (debugEnabled) {
            debugW("EMERGENCY: Used REGENERATION chip (first use this fight)");
        }
    }
    
    // Final Enhanced Lightninger fallback
    if (!healed && hasLightninger && inRange && hasTP && hasLineOfSight) {
        useWeapon(primaryTarget);
        healed = true;
        if (debugEnabled) {
            debugW("EMERGENCY FALLBACK: Used Enhanced Lightninger without healing chips");
        }
    }
    
    if (debugEnabled && !healed) {
        debugW("EMERGENCY HEAL: No healing options available");
    }
    
    return healed;
}

// === WRAPPER FUNCTIONS FOR COMPATIBILITY ===
function tryEmergencyHealing() {
    return tryUnifiedEmergencyHealing("simple");
}

function tryEmergencyHealingWithAttack() {
    return tryUnifiedEmergencyHealing("smart");
}

// === TACTICAL EMERGENCY MOVEMENT ===
function tryEmergencyMovement() {
    if (myMP <= 0) return false;
    
    var currentDistance = getCellDistance(myCell, enemyCell);
    var weapons = getWeapons();
    
    if (debugEnabled) {
        debugW("TACTICAL EMERGENCY MOVE: Finding weapon-ready position from distance " + currentDistance);
    }
    
    // Define weapon priorities with special position finders
    var weaponPriorities = [
        {weapon: WEAPON_FLAME_THROWER, priority: 11, name: "Flame Thrower", special: "tactical"},
        {weapon: WEAPON_ENHANCED_LIGHTNINGER, priority: 10, name: "Enhanced Lightninger", special: "tactical"},
        {weapon: WEAPON_NEUTRINO, priority: 9, name: "Neutrino", special: "diagonal"},
        {weapon: WEAPON_DESTROYER, priority: 8, name: "Destroyer", special: "tactical"},
        {weapon: WEAPON_RIFLE, priority: 7, name: "Rifle", special: "tactical"},
        {weapon: WEAPON_M_LASER, priority: 6, name: "M-Laser", special: "alignment"},
        {weapon: WEAPON_LASER, priority: 5, name: "Laser", special: "alignment"},
        {weapon: WEAPON_B_LASER, priority: 4, name: "B-Laser", special: "alignment"},
        {weapon: WEAPON_MAGNUM, priority: 3, name: "Magnum", special: "tactical"},
        {weapon: WEAPON_PISTOL, priority: 2, name: "Pistol", special: "tactical"},
        {weapon: WEAPON_RHINO, priority: 1, name: "Rhino", special: "tactical"},
        {weapon: WEAPON_GRENADE_LAUNCHER, priority: 1, name: "Grenade Launcher", special: "tactical"},
        {weapon: WEAPON_SWORD, priority: 0, name: "Sword", special: "tactical"},
        {weapon: WEAPON_KATANA, priority: -1, name: "Katana", special: "tactical"}
    ];
    
    // Try weapons in priority order
    for (var p = 0; p < count(weaponPriorities); p++) {
        var wpn = weaponPriorities[p];
        if (!inArray(weapons, wpn.weapon)) continue;
        
        var bestCell = null;
        if (wpn.special == "diagonal") {
            bestCell = findNeutrinoDiagonalPosition();
        } else if (wpn.special == "alignment") {
            bestCell = findAlignmentPosition(wpn.weapon);
        } else {
            bestCell = findTacticalPosition(wpn.weapon, wpn.name);
        }
        
        if (bestCell != null) {
            var oldCell = myCell;
            var mpUsed = moveTowardCells([bestCell], myMP);
            myCell = getCell();
            myMP = getMP();
            
            if (debugEnabled) {
                debugW("TACTICAL MOVE (" + wpn.name + "): From " + oldCell + " to " + myCell + " (MP used: " + mpUsed + ")");
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
                    if (weapon != WEAPON_SWORD && weapon != WEAPON_KATANA && !checkLineOfSight(cell, enemyCell)) {
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

// === UNIFIED ALIGNMENT POSITION FINDER ===
function findAlignmentPosition(weapon) {
    var bestCell = null;
    var bestScore = 0;
    var minRange = getWeaponMinRange(weapon);
    var maxRange = getWeaponMaxRange(weapon);
    var weaponName = (weapon == WEAPON_B_LASER) ? "B-Laser" : 
                     (weapon == WEAPON_M_LASER) ? "M-Laser" :
                     (weapon == WEAPON_LASER) ? "Laser" : "Alignment";
    
    if (debugEnabled) {
        debugW("Finding " + weaponName + " alignment position (range " + minRange + "-" + maxRange + ")");
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
                    // Check for X or Y axis alignment
                    var cellX = getCellX(cell);
                    var cellY = getCellY(cell);
                    var enemyX = getCellX(enemyCell);
                    var enemyY = getCellY(enemyCell);
                    
                    var xAligned = (cellX == enemyX);
                    var yAligned = (cellY == enemyY);
                    
                    // Must be aligned on exactly one axis (XOR)
                    if (xAligned != yAligned) {
                        // Score based on distance (closer for emergency, farther for M-Laser)
                        var score = (weapon == WEAPON_B_LASER) ? (100 - enemyDistance) : enemyDistance;
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
        debugW("Found " + weaponName + " alignment position " + bestCell + " at distance " + distance);
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
                        if (!checkLineOfSight(cell, enemyCell)) {
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
        var losBreak = !checkLineOfSight(cell, enemyCell);
        
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
    executeCombat(myCell, null, null); // No pre-calculated weapon/package in emergency mode
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

// === UNIFIED KITING FUNCTIONS ===
function tryKiting(mode) {
    if (mode == "movement") {
        return tryKitingMovement();
    } else if (mode == "attack") {
        return tryKitingAttack();
    }
    return false;
}

function tryKitingMovement() {
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
    if (maxWeaponRange == 0) maxWeaponRange = 8; // Fallback chip range
    
    // Find cells within movement range that are farther from enemy
    for (var range = 1; range <= myMP; range++) {
        var cells = getCellsAtExactDistance(myCell, range);
        for (var i = 0; i < count(cells); i++) {
            var cell = cells[i];
            var distance = getCellDistance(cell, enemyCell);
            if (distance > currentDistance && distance <= maxWeaponRange && checkLineOfSight(cell, enemyCell)) {
                push(kiteCells, cell);
            }
        }
    }
    
    if (count(kiteCells) == 0) return false;
    
    // Select best kiting position
    var bestKite = null;
    var bestScore = 0;
    for (var i = 0; i < count(kiteCells); i++) {
        var cell = kiteCells[i];
        var distance = getCellDistance(cell, enemyCell);
        var score = distance; // Base score on distance
        
        // Weapon range bonus
        for (var j = 0; j < count(weapons); j++) {
            var weapon = weapons[j];
            var minRange = getWeaponMinRange(weapon);
            var maxRange = getWeaponMaxRange(weapon);
            if (distance >= minRange && distance <= maxRange) {
                score += 100;
                var optimalRange = (minRange + maxRange) / 2;
                score += max(0, 50 - abs(distance - optimalRange) * 5);
            }
        }
        
        if (score > bestScore) {
            bestScore = score;
            bestKite = cell;
        }
    }
    
    if (bestKite != null) {
        var path = aStar(myCell, bestKite, myMP);
        if (path != null) {
            executeMovement({path: path, targetCell: bestKite});
            return true;
        }
    }
    return false;
}

function tryKitingAttack() {
    if (myTP < 3) return false;
    
    var distance = getCellDistance(myCell, enemyCell);
    var weapons = getWeapons();
    
    // Priority weapons with special handling
    var priorityWeapons = [
        {weapon: WEAPON_FLAME_THROWER, priority: 6, special: "line"},
        {weapon: WEAPON_M_LASER, priority: 5, special: "line"},
        {weapon: WEAPON_LASER, priority: 4, special: "line"},
        {weapon: WEAPON_B_LASER, priority: 3, special: "line"},
        {weapon: WEAPON_ENHANCED_LIGHTNINGER, priority: 2, special: "multi"},
        {weapon: WEAPON_NEUTRINO, priority: 1, special: "diagonal"},
        {weapon: WEAPON_DESTROYER, priority: 0, special: "normal"},
        {weapon: WEAPON_MAGNUM, priority: -1, special: "normal"},
        {weapon: WEAPON_PISTOL, priority: -2, special: "normal"},
        {weapon: WEAPON_RHINO, priority: -3, special: "normal"}
    ];
    
    // Try priority weapons first
    for (var p = 0; p < count(priorityWeapons); p++) {
        var wpn = priorityWeapons[p];
        if (!inArray(weapons, wpn.weapon)) continue;
        
        var minRange = getWeaponMinRange(wpn.weapon);
        var maxRange = getWeaponMaxRange(wpn.weapon);
        var cost = getWeaponCost(wpn.weapon);
        
        if (distance < minRange || distance > maxRange || myTP < cost) continue;
        
        // Special alignment checks
        var aligned = true;
        if (wpn.special == "line") {
            aligned = isOnSameLine(myCell, enemyCell);
        } else if (wpn.special == "diagonal") {
            var dx = abs(getCellX(myCell) - getCellX(enemyCell));
            var dy = abs(getCellY(myCell) - getCellY(enemyCell));
            aligned = (dx == dy && dx > 0);
        }
        
        if (!aligned) continue;
        
        if (tryKitingWeaponAttack(wpn.weapon, wpn.special, cost)) {
            return true;
        }
    }
    
    // Fallback: try remaining weapons
    for (var i = 0; i < count(weapons); i++) {
        var weapon = weapons[i];
        var cost = getWeaponCost(weapon);
        var minRange = getWeaponMinRange(weapon);
        var maxRange = getWeaponMaxRange(weapon);
        
        if (distance >= minRange && distance <= maxRange && myTP >= cost) {
            if (tryKitingWeaponAttack(weapon, "normal", cost)) {
                return true;
            }
        }
    }
    
    // Final fallback to chips
    var chips = getAvailableDamageChips();
    for (var i = 0; i < count(chips); i++) {
        var chip = chips[i];
        var chipCost = getChipCost(chip);
        if (myTP >= chipCost && canUseChip(chip, enemy)) {
            useChip(chip, enemy);
            myTP -= chipCost;
            if (debugEnabled) {
                debugW("Kiting attack: Used chip " + chip);
            }
            return true;
        }
    }
    
    return false;
}

function tryKitingWeaponAttack(weapon, special, cost) {
    // Switch weapon if needed
    if (getWeapon() != weapon) {
        if (myTP < cost + 1) return false;
        setWeapon(weapon);
        myTP--;
    }
    
    if (!canUseWeapon(enemy)) return false;
    
    if (special == "multi" && weapon == WEAPON_ENHANCED_LIGHTNINGER) {
        // Enhanced Lightninger multi-shot logic
        var currentTP = getTP();
        var maxUses = getWeaponMaxUses(weapon);
        var tpReservedForRegen = canUseChip(CHIP_REGENERATION, getEntity()) ? getChipCost(CHIP_REGENERATION) : 0;
        var availableUses = floor((currentTP - tpReservedForRegen) / cost);
        var actualUses = (maxUses > 0) ? min(availableUses, maxUses) : availableUses;
        
        var successfulUses = 0;
        for (var use = 0; use < actualUses && canUseWeapon(enemy); use++) {
            useWeapon(enemy);
            successfulUses++;
        }
        
        // Use REGENERATION if reserved
        if (tpReservedForRegen > 0 && canUseChip(CHIP_REGENERATION, getEntity()) && getTP() >= tpReservedForRegen) {
            useChip(CHIP_REGENERATION, getEntity());
        }
        
        return successfulUses > 0;
    } else {
        // Normal single weapon use
        useWeapon(enemy);
        myTP -= cost;
        if (debugEnabled) {
            debugW("Kiting attack: Used " + weapon);
        }
        return true;
    }
}

// === UTILITY FUNCTIONS ===
function findCellsWithoutLOS(enemyCell, maxDistance) {
    var hideCells = [];
    
    for (var range = 1; range <= maxDistance; range++) {
        var cells = getCellsAtExactDistance(myCell, range);
        
        for (var i = 0; i < count(cells); i++) {
            var cell = cells[i];
            if (!checkLineOfSight(cell, enemyCell)) {
                push(hideCells, cell);
            }
        }
    }
    
    return hideCells;
}

// === UNIFIED DAMAGE ESTIMATION ===
function estimateDamage(entity, isEnemyDamage) {
    if (entity == null || getLife(entity) <= 0) return 0;
    
    if (isEnemyDamage) {
        // Enemy damage estimation
        var enemyWeapons = getWeapons(entity);
        var distance = getCellDistance(myCell, getCell(entity));
        var totalDamage = 0;
        
        for (var i = 0; i < count(enemyWeapons); i++) {
            var weapon = enemyWeapons[i];
            var minRange = getWeaponMinRange(weapon);
            var maxRange = getWeaponMaxRange(weapon);
            
            if (distance >= minRange && distance <= maxRange) {
                var baseDamage = getWeaponBaseDamage(weapon);
                var strengthMultiplier = 1 + (getStrength(entity) / 100.0);
                totalDamage += baseDamage * strengthMultiplier;
            }
        }
        
        // Add chip damage potential
        if (getTP(entity) >= 4) {
            totalDamage += 50; // Lightning chip estimation
        }
        
        return floor(totalDamage);
    } else {
        // My damage estimation
        var targetCell = getCell(entity);
        var weapons = getWeapons();
        var maxDamage = 0;
        
        // Current position damage
        var currentDamage = 0;
        for (var i = 0; i < count(weapons); i++) {
            currentDamage += calculateWeaponDamageFromCell(weapons[i], myCell, targetCell);
        }
        maxDamage = currentDamage;
        
        // Check movement options if we have MP
        if (myMP > 0) {
            var bestMoveDamage = 0;
            for (var i = 0; i < count(weapons); i++) {
                var weapon = weapons[i];
                if (getWeaponCost(weapon) > myTP) continue;
                
                var minRange = getWeaponMinRange(weapon);
                var maxRange = getWeaponMaxRange(weapon);
                
                for (var range = minRange; range <= min(maxRange, minRange + 3); range++) {
                    var positions = getCellsAtExactDistance(targetCell, range);
                    for (var j = 0; j < min(count(positions), 8); j++) {
                        var testCell = positions[j];
                        var moveDistance = getCellDistance(myCell, testCell);
                        
                        if (moveDistance <= myMP && getCellContent(testCell) == CELL_EMPTY) {
                            var positionDamage = 0;
                            for (var k = 0; k < count(weapons); k++) {
                                positionDamage += calculateWeaponDamageFromCell(weapons[k], testCell, targetCell);
                            }
                            bestMoveDamage = max(bestMoveDamage, positionDamage);
                        }
                    }
                }
            }
            maxDamage = max(maxDamage, bestMoveDamage);
        }
        
        // Add chip damage potential
        if (myTP >= 4) maxDamage += 50;
        
        if (debugEnabled) {
            debugW("DAMAGE ESTIMATE: Current=" + floor(currentDamage) + ", Best=" + floor(maxDamage) + " vs Enemy HP=" + getLife(entity));
        }
        
        return floor(maxDamage);
    }
}

// === COMPATIBILITY WRAPPER FUNCTIONS ===
function estimateEnemyDamageNextTurn(enemyEntity) {
    return estimateDamage(enemyEntity, true);
}

function estimateMyDamageThisTurn(targetEntity) {
    return estimateDamage(targetEntity, false);
}

function estimatePrimaryEnemyDamage() {
    return (primaryTarget != null) ? estimateEnemyDamageNextTurn(primaryTarget) : 0;
}

function estimateMyDamageOnPrimary() {
    return (primaryTarget != null) ? estimateMyDamageThisTurn(primaryTarget) : 0;
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
