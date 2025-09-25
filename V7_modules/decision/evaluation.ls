// V7 Module: decision/evaluation.ls
// SIMPLIFIED enemy-centric damage zone calculation

// === MAIN MULTI-ENEMY DAMAGE ZONE CALCULATION WITH ENEMY ASSOCIATIONS ===
function calculateMultiEnemyDamageZones() {
    // Custom color definitions for visual marking
    var COLOR_YELLOW = 0xFFFF00;
    var COLOR_ORANGE = 0xFF8000;
    var COLOR_PURPLE = 0x8000FF;
    var COLOR_WHITE = 0xFFFFFF;
    var COLOR_BLACK = 0x000000;
    // === MULTI-ENEMY DAMAGE CALCULATION START ===
    var mergedDamageArray = [];
    
    // Safety checks
    if (allEnemies == null || count(allEnemies) == 0) {
        return mergedDamageArray;
    }
    
    var aliveEnemies = [];
    for (var i = 0; i < count(allEnemies); i++) {
        if (getLife(allEnemies[i]) > 0) {
            push(aliveEnemies, allEnemies[i]);
        }
    }
    
    // Enemies check complete
    
    if (count(aliveEnemies) == 0) {
        debugW("NO ALIVE ENEMIES!");
        return mergedDamageArray;
    }
    
    // Get weapons
    var weapons = getWeapons();
    var hasWeapons = (weapons != null && count(weapons) > 0);

    // OPERATIONS OPTIMIZATION: Use optimized calculation for multiple enemies
    if (count(aliveEnemies) > 1 && hasWeapons) {
        debugW("MULTI-ENEMY OPTIMIZATION: Using corridor-based calculation for " + count(aliveEnemies) + " enemies");
        var maxOperations = 5000000; // Match original limit
        var optimizedZones = calculateOptimizedDamageZones(aliveEnemies, weapons, maxOperations);

        if (optimizedZones != null && count(optimizedZones) > 0) {
            debugW("OPTIMIZATION SUCCESS: Generated " + count(optimizedZones) + " optimized damage zones");
            return optimizedZones;
        } else {
            debugW("OPTIMIZATION FALLBACK: Using original calculation");
            // Continue with original method below
        }
    }

    // Original single-enemy focused calculation (preserved for compatibility)
    // Weapon availability checked

    // NEW ENEMY-CENTRIC APPROACH: Generate zones around enemies at weapon ranges
    var enemyDamageZones = []; // Combined: [cell, damage, weaponId, enemyEntity]
    var weaponDamageZones = []; // Weapon-only
    var chipDamageZones = [];   // Chip-only
    var operationsUsed = 0;
    var maxOperations = 5000000; // 5M operations - utilize our full budget
    
    // Processing enemies with available weapons
    
    // For each weapon, create zones around each enemy at that weapon's optimal range
    for (var w = 0; w < count(weapons) && operationsUsed < maxOperations; w++) {
        var weapon = weapons[w];
        var weaponCost = getWeaponCost(weapon);
        
        // Skip weapons we can't afford
        if (weaponCost > myTP) {
            continue;
        }
        
        var minRange = getWeaponMinRange(weapon);
        var maxRange = getWeaponMaxRange(weapon);
        var optimalRange = floor((minRange + maxRange) / 2);
        
        // Show weapon color mapping using built-in constants
        var weaponColorName = "Yellow"; // Default
        if (weapon == WEAPON_M_LASER) weaponColorName = "Red";
        else if (weapon == WEAPON_RIFLE) weaponColorName = "Orange";
        else if (weapon == WEAPON_ENHANCED_LIGHTNINGER) weaponColorName = "Purple";
        else if (weapon == WEAPON_KATANA) weaponColorName = "Blue";
        else if (weapon == WEAPON_B_LASER) weaponColorName = "Deep Pink";
        else if (weapon == WEAPON_GRENADE_LAUNCHER) weaponColorName = "Dark Orange";
        else if (weapon == WEAPON_ELECTRISOR) weaponColorName = "Cyan";
        else if (weapon == WEAPON_RHINO) weaponColorName = "Brown";
        else if (weapon == WEAPON_SWORD) weaponColorName = "Lime Green";
        else if (weapon == WEAPON_NEUTRINO) weaponColorName = "Pink";
        else if (weapon == WEAPON_DESTROYER) weaponColorName = "Indigo";
        else if (weapon == WEAPON_FLAME_THROWER) weaponColorName = "Red Orange";
        else if (weapon == WEAPON_LASER) weaponColorName = "Crimson";
        
        // Processing weapon zones for all ranges
        
        // For each enemy, create zones at ALL weapon ranges (not just optimal)
        for (var e = 0; e < count(aliveEnemies) && operationsUsed < maxOperations; e++) {
            var currentEnemy = aliveEnemies[e];
            
            // Use validated enemy cell from enemyData instead of calling getCell() again
            var currentEnemyCell = null;
            if (enemyData[currentEnemy] != null) {
                currentEnemyCell = enemyData[currentEnemy].cell;
                
                // CRITICAL DEBUG: Verify we're using enemy position, not our position
                if (currentEnemyCell == myCell) {
                    debugW("BUG DETECTED: Enemy cell " + currentEnemyCell + " equals our cell " + myCell + " - this should NEVER happen!");
                    debugW("BUG DEBUG: Enemy entity=" + currentEnemy + ", enemyData exists=" + (enemyData[currentEnemy] != null));
                    continue; // Skip this enemy to avoid calculating zones around ourselves
                }
                
                // Enemy position validated
            } else {
                // Missing enemy data, skipping
                continue;
            }
            
            // Generate zones for ALL ranges within weapon's capability
            for (var range = minRange; range <= maxRange && operationsUsed < maxOperations; range++) {
                var zoneCells = getCellsAtExactDistance(currentEnemyCell, range);
                
                // Calculate ALL cells - no limits

                // Zone search for all cells at this range

                for (var c = 0; c < count(zoneCells) && operationsUsed < maxOperations; c++) {
                var attackPosition = zoneCells[c];
                operationsUsed++;
                
                // Safety check: ensure attackPosition is valid
                attackPosition = floor(attackPosition + 0.5);
                if (attackPosition < 0 || attackPosition > 612) continue;
                
                // Always calculate damage - let pathfinding handle reachability
                var distanceToPosition = getCellDistance(myCell, attackPosition);
                
                // For enemy-centric zones, calculate damage from this position to enemy
                var damage = calculateBaseWeaponDamage(weapon, attackPosition, currentEnemyCell);
                
                // Damage calculated for position
                
                // Check Line of Sight for this position
                var hasLoS = lineOfSight(attackPosition, currentEnemyCell);
                
                // Store zone if it provides significant damage or movement incentive
                // Priority: LoS zones with real damage > non-LoS zones with incentive
                if (damage > 0) {
                    // Only store non-LoS zones if they have significant incentive (> 50 damage)
                    // or if we have very few LoS zones
                    if (hasLoS || damage > 50) {
                        // Require axis alignment for line weapons to avoid infeasible MLASER/BLASER zones
                        var lt = getWeaponLaunchType(weapon);
                        var requiresAxisAlignment = (lt == LAUNCH_TYPE_LINE || lt == LAUNCH_TYPE_LINE_INVERTED);
                        if (requiresAxisAlignment && !isOnSameLine(attackPosition, currentEnemyCell)) {
                            // Skip non-aligned line-weapon zones
                        } else {
                            push(enemyDamageZones, [attackPosition, damage, weapon, currentEnemy]);
                        }
                    }
                    
                    // Mark damage zones visually on the map with weapon-specific colors
                    // Show for entire fight for tactical advantage
                        var markColor = 0; // Default black
                        
                        // Color by weapon type (using RGB values)
                        // Distinct color per weapon type
                        if (weapon == WEAPON_M_LASER) markColor = getColor(255, 0, 0);         // M-Laser - Red
                        else if (weapon == WEAPON_RIFLE) markColor = getColor(255, 165, 0); // Rifle - Orange  
                        else if (weapon == WEAPON_ENHANCED_LIGHTNINGER) markColor = getColor(128, 0, 128); // Enhanced Lightninger - Purple
                        else if (weapon == WEAPON_KATANA) markColor = getColor(0, 0, 255);   // Katana - Blue
                        else if (weapon == WEAPON_B_LASER) markColor = getColor(255, 20, 147); // B-Laser - Deep Pink
                        else if (weapon == WEAPON_GRENADE_LAUNCHER) markColor = getColor(255, 140, 0);  // Grenade Launcher - Dark Orange
                        else if (weapon == WEAPON_ELECTRISOR) markColor = getColor(0, 255, 255);  // Electrisor - Cyan
                        else if (weapon == WEAPON_RHINO) markColor = getColor(139, 69, 19);  // Rhino - Saddle Brown
                        else if (weapon == WEAPON_SWORD) markColor = getColor(50, 205, 50);  // Sword - Lime Green
                        else if (weapon == WEAPON_NEUTRINO) markColor = getColor(255, 192, 203); // Neutrino - Pink
                        else if (weapon == WEAPON_DESTROYER) markColor = getColor(75, 0, 130);   // Destroyer - Indigo
                        else if (weapon == WEAPON_FLAME_THROWER) markColor = getColor(255, 69, 0);   // Flame Thrower - Red Orange
                        else if (weapon == WEAPON_LASER) markColor = getColor(220, 20, 60);  // Laser - Crimson
                        else markColor = getColor(255, 255, 0); // Unknown weapons - Yellow
                        
                        // Dim color if no Line of Sight (make it gray)
                        if (!hasLoS) {
                            markColor = getColor(128, 128, 128); // All non-LoS zones are gray
                        }
                        
                        mark(attackPosition, markColor);
                    
                    if (getTurn() <= 3) {
                        // Zone created (debug log removed to reduce output pollution)
                    }
                }
                }
            }
        }
    }
    
    debugW("ENEMY-CENTRIC: Created " + count(enemyDamageZones) + " weapon damage zones around enemies");
    
    // ADD CHIP DAMAGE ZONES TO MAIN CALCULATION
    var chips = getChips();
    // Equipped chips checked
    if (chips != null && count(chips) > 0 && operationsUsed < maxOperations) {
        // Adding chip damage zones
        
        // Define all available damage chips with their properties
        var chipData = [
            {id: CHIP_LIGHTNING, cost: 4, range: 10, minDmg: 35, maxDmg: 45},
            {id: CHIP_METEORITE, cost: 5, range: 8, minDmg: 45, maxDmg: 55},
            {id: CHIP_TOXIN, cost: 5, range: 7, minDmg: 25, maxDmg: 35},
            {id: CHIP_VENOM, cost: 4, range: 10, minDmg: 20, maxDmg: 28},
            {id: CHIP_BURNING, cost: 2, range: 8, minDmg: 12, maxDmg: 18},
            {id: CHIP_ROCKFALL, cost: 4, range: 6, minDmg: 40, maxDmg: 50},
            {id: CHIP_ICEBERG, cost: 3, range: 8, minDmg: 30, maxDmg: 40}
        ];
        
        // Chip constants verified
        
        // Check each equipped chip
        for (var c = 0; c < count(chipData) && operationsUsed < maxOperations; c++) {
            var chip = chipData[c];
            if (!inArray(chips, chip.id)) {
                continue;
            }
            if (chip.cost > myTP) {
                // Chip too expensive
                continue;
            }
            
            // Processing chip zones
            
            // Calculate chip zones around each enemy
            for (var e = 0; e < count(aliveEnemies) && operationsUsed < maxOperations; e++) {
                var currentEnemy = aliveEnemies[e];
                var currentEnemyCell = null;
                
                if (enemyData[currentEnemy] != null) {
                    currentEnemyCell = enemyData[currentEnemy].cell;
                } else {
                    continue;
                }
                
                // Find positions where we can use this chip against this enemy
                var maxSearchDistance = min(myMP + chip.range, 15);
                for (var d = 1; d <= maxSearchDistance && operationsUsed < maxOperations; d++) {
                    var candidateCells = getCellsAtExactDistance(myCell, d);

                    for (var i = 0; i < count(candidateCells) && operationsUsed < maxOperations; i++) {
                        var attackCell = candidateCells[i];
                        operationsUsed++;
                        
                        var distanceToEnemy = getCellDistance(attackCell, currentEnemyCell);
                        
                        if (distanceToEnemy <= chip.range) {
                            // Check line of sight (SPARK doesn't need LoS)
                            var needsLOS = (chip.id != CHIP_SPARK);
                            var hasLoSCheck = true;
                            
                            if (needsLOS) {
                                hasLoSCheck = lineOfSight(attackCell, currentEnemyCell);
                            }
                            
                            if (hasLoSCheck) {
                                // Calculate chip damage (use average)
                                var chipDamage = (chip.minDmg + chip.maxDmg) / 2;
                                
                                // Apply magic scaling for magic builds
                                if (isMagicBuild && myMagic != null) {
                                    chipDamage = chipDamage * (1 + myMagic / 100.0);
                                }
                                
                                // Calculate uses (chips have no max uses limit usually)
                                var tpUses = floor(myTP / chip.cost);
                                var totalChipDamage = chipDamage * tpUses;
                                
                                var entry = [attackCell, totalChipDamage, chip.id, currentEnemy];
                                push(enemyDamageZones, entry);
                                push(chipDamageZones, entry);
                                
                                if (getTurn() <= 2) {
                                    // Chip zone created
                                }
                            }
                        }
                    }
                }
            }
        }
        
        debugW("CHIP INTEGRATION: Complete, total zones=" + count(enemyDamageZones));
    }
    
    debugW("ENEMY-CENTRIC: Total " + count(enemyDamageZones) + " weapon+chip damage zones around enemies");
    
    // Mark current position and enemies for reference
    if (getTurn() <= 5) {
        mark(myCell, getColor(0, 0, 255)); // Mark AI position in blue
        for (var e = 0; e < count(aliveEnemies); e++) {
            var enemyPosition = getCell(aliveEnemies[e]);
            // Validate enemy cell before marking
            if (enemyPosition >= 0 && enemyPosition <= 612) {
                mark(enemyPosition, getColor(0, 255, 0)); // Mark enemies in bright green for visibility
            }
        }
    }
    
    // Convert enemy-specific zones to cell-based aggregation for compatibility
    var damageByCell = [:];
    var weaponByCell = [:]; // Track which weapon provides max damage for each cell
    for (var i = 0; i < count(enemyDamageZones); i++) {
        var zone = enemyDamageZones[i];
        
        // DEFENSIVE: Check if zone is valid before accessing
        if (zone == null || count(zone) < 2) {
            if (debugEnabled) {
                debugW("AGGREGATION SKIP: Invalid zone at index " + i);
            }
            continue;
        }
        
        var cell = zone[0];
        var damage = zone[1];
        var weaponId = (count(zone) >= 3) ? zone[2] : 0;
        
        // DEBUG: Show every zone during aggregation (DEFENSIVE)
        if (debugEnabled && i < 5 && count(zone) >= 3) {
            debugW("AGGREGATION[" + i + "]: zone=[" + zone[0] + ", " + zone[1] + ", " + zone[2] + "] cell=" + cell + ", damage=" + damage);
        }
        
        // Ensure cell is integer and damage is valid
        if (cell != null && damage != null && damage > 0) {
            var cellId = floor(cell + 0.5); // Ensure integer cell ID
            
            // Take MAXIMUM damage instead of adding - proper weapon priority
            if (damageByCell[cellId] == null || damage > damageByCell[cellId]) {
                damageByCell[cellId] = damage;
                weaponByCell[cellId] = weaponId;
                
                // Debug weapon override for M_LASER vs ENHANCED_LIGHTNINGER
                if (debugEnabled && (weaponId == WEAPON_M_LASER || weaponId == WEAPON_ENHANCED_LIGHTNINGER)) {
                    debugW("WEAPON OVERRIDE: Cell " + cellId + " now uses weapon " + weaponId + " with damage " + damage);
                }
            }
        } else if (debugEnabled) {
            debugW("AGGREGATION SKIP: cell=" + cell + ", damage=" + damage);
        }
    }
    
    // Enemy-centric calculation complete - let main handle empty zones if needed
    
    // Store separated maps globally for pathfinding (weapon-first, chip-second)
    // Partition enemyDamageZones by weapon/chip id
    for (var i2 = 0; i2 < count(enemyDamageZones); i2++) {
        var e = enemyDamageZones[i2];
        if (e == null || count(e) < 3) continue;
        var wid = e[2];
        if (wid != null && wid >= CHIP_LIGHTNING) {
            // chip
            // already pushed above for chip entries from chip loops; weapon-generated chips shouldn't exist
        } else {
            push(weaponDamageZones, e);
        }
    }
    currentWeaponDamageArray = weaponDamageZones;
    currentChipDamageArray = chipDamageZones;

    // PRIORITY 1: Return enemy-specific damage zones
    if (count(enemyDamageZones) > 0) {
        return enemyDamageZones;
    }
    
    // PRIORITY 2: Convert to array format for chip fallback compatibility
    for (var cell in damageByCell) {
        var damage = damageByCell[cell];
        if (damage > 0) {
            var cellId = floor(cell + 0.5); // Ensure integer cell ID
            var bestWeapon = (weaponByCell[cellId] != null) ? weaponByCell[cellId] : WEAPON_RIFLE;
            push(mergedDamageArray, [cellId, damage, bestWeapon]); // Use the actual best weapon
        }
    }
    
    debugW("=== MULTI-ENEMY DAMAGE CALCULATION COMPLETE: " + count(mergedDamageArray) + " zones ===");
    return mergedDamageArray;
}

// === SIMPLE DAMAGE ZONE CALCULATION ===
function calculateDamageZones(enemyCell) {
    var damageMap = [:];
    
    if (enemyCell == null) return damageMap;
    
    var weapons = getWeapons();
    var hasWeapons = (weapons != null && count(weapons) > 0);
    
    // Check positions within movement + weapon range
    var maxDistance = min(myMP + 15, 20);
    
    for (var distance = 0; distance <= maxDistance; distance++) {
        var cells = getCellsAtExactDistance(myCell, distance);

        for (var i = 0; i < count(cells); i++) {
            var cell = cells[i];
            
            // Safety check: ensure cell is an integer
            if (cell != floor(cell)) {
                // Cell coordinate normalized
                cell = floor(cell);
            }
            var totalDamage = 0;
            
            // Check all weapons from this position
            for (var w = 0; w < count(weapons); w++) {
                var weapon = weapons[w];
                var damage = 0;
                
                if (isAreaWeapon(weapon)) {
                    // Calculate AoE damage opportunities (splash damage)
                    damage = calculateAoEDamageZones(weapon, cell, enemyCell);
                } else {
                    // Direct damage calculation for single-target weapons
                    damage = calculateWeaponDamageFromCell(weapon, cell, enemyCell);
                }
                
                totalDamage += damage;
            }
            
            if (totalDamage > 0) {
                damageMap[cell] = totalDamage;
            }
        }
    }
    
    // NO CHIP FALLBACK: If no weapon zones, the AI should move to get into weapon range
    // instead of falling back to weak chips like SPARK
    
    var mapHasEntries = false;
    for (var cell in damageMap) {
        mapHasEntries = true;
        break;
    }
    
    // Map entries checked
    
    return damageMap;
}

// === BASE WEAPON DAMAGE FOR ENEMY-CENTRIC ZONES ===
function calculateBaseWeaponDamage(weapon, fromCell, targetCell) {
    // Use the existing weapon damage calculation function
    return calculateWeaponDamageFromCell(weapon, fromCell, targetCell);
}

// === WEAPON DAMAGE CALCULATION ===
function calculateWeaponDamageFromCell(weapon, fromCell, targetCell) {
    // Damage calculation starting
    
    if (myTP == null || myStrength == null) {
        return 0;
    }
    
    // Check weapon cost - RELAXED for movement planning
    var weaponCost = getWeaponCost(weapon);
    if (weaponCost > myTP && myTP < 15) { // Only fail if we're very low on TP
        return 0;
    }
    
    // Check range
    var distance = getCellDistance(fromCell, targetCell);
    var minRange = getWeaponMinRange(weapon);
    var maxRange = getWeaponMaxRange(weapon);
    
    // Check range - enhanced for AoE weapons
    if (isAreaWeapon(weapon)) {
        var aoeRadius = getWeaponArea(weapon);
        var effectiveMinRange = max(1, minRange - aoeRadius);
        var effectiveMaxRange = maxRange + aoeRadius;
        
        if (distance < effectiveMinRange || distance > effectiveMaxRange) {
            // Too far even for splash damage
            return 0;
        } else if (distance < minRange || distance > maxRange) {
            // Can't direct shot, and can't hit with splash - no damage possible
            return 0;
        }
        // Else: within direct range, continue with normal damage calculation
    } else {
        // Standard range check for single-target weapons
        if (distance < minRange || distance > maxRange) {
            // Out of range - no damage possible
            return 0;
        }
    }
    
    // Check line of sight - no damage without LOS
    if (!lineOfSight(fromCell, targetCell)) {
        return 0;
    }
    
    // M-Laser specific alignment check - requires X OR Y axis alignment only (no diagonal)
    if (weapon == WEAPON_M_LASER) {
        var fromX = getCellX(fromCell);
        var fromY = getCellY(fromCell);
        var targetX = getCellX(targetCell);
        var targetY = getCellY(targetCell);
        
        var dx = targetX - fromX;
        var dy = targetY - fromY;
        
        // M-Laser requires X OR Y axis alignment only (same row or column, NOT diagonal)
        var isAligned = (dx == 0) || (dy == 0);
        
        if (!isAligned) {
            return 0;
        }
    }
    
    // Check alignment for line weapons (other lasers and flame thrower) - X/Y axis only
    if (isLineWeapon(weapon) && weapon != WEAPON_M_LASER) { // M-LASER already checked above
        var fromX = getCellX(fromCell);
        var fromY = getCellY(fromCell);
        var targetX = getCellX(targetCell);
        var targetY = getCellY(targetCell);
        
        var dx = targetX - fromX;
        var dy = targetY - fromY;
        
        // Line weapons require X OR Y axis alignment only (same row or column, NOT diagonal)
        var isAligned = (dx == 0) || (dy == 0);
        
        if (!isAligned) {
            return 0;
        }
    }
    
    // Get base damage
    var effects = getWeaponEffects(weapon);
    // Minimal weapon debugging for M-Laser vs Enhanced Lightninger only
    var baseDamage = 0;
    
    for (var i = 0; i < count(effects); i++) {
        if (effects[i][0] == 1) { // EFFECT_DAMAGE
            var minDmg = effects[i][1];
            var maxDmg = effects[i][2];
            baseDamage = (minDmg + maxDmg) / 2;
            break;
        }
    }
    
    if (baseDamage == 0) {
        return 0;
    }
    
    // Apply strength scaling
    var scaledDamage = baseDamage * (1 + myStrength / 100.0);
    
    // Calculate uses
    var maxUses = getWeaponMaxUses(weapon);
    var tpUses = floor(myTP / weaponCost);
    var actualUses = (maxUses > 0) ? min(tpUses, maxUses) : tpUses;
    
    var totalDamage = scaledDamage * actualUses;

    // Add estimated DoT contribution if weapon applies poison (e.g., DOUBLE_GUN)
    var wEffects = getWeaponEffects(weapon);
    for (var i = 0; i < count(wEffects); i++) {
        var eff = wEffects[i];
        var effType = eff[0];
        var minVal = eff[1];
        var maxVal = eff[2];
        // EFFECT_POISON
        if (effType == EFFECT_POISON) {
            var avgPoison = (minVal + maxVal) / 2;
            // Poison scales with magic per user design
            var scaledPoison = avgPoison * (1 + myMagic / 100.0);
            // Stack per use; assume 2 turns of effect as per weapon description
            var perUseDoT = scaledPoison * 2;
            totalDamage += perUseDoT * actualUses;
        }
    }
    
    // Natural weapon stats used without artificial bonuses
    
    // Weapon-specific bonuses
    if (weapon == WEAPON_KATANA && distance == 1) {
        totalDamage *= 1.2; // Melee bonus
    }
    if (weapon == WEAPON_SWORD && distance == 1) {
        totalDamage *= 1.1; // Melee bonus for sword
    }
    
    return totalDamage;
}

// === AOE WEAPON DAMAGE CALCULATION ===
function calculateAoEDamageZones(weapon, fromCell, targetCell) {
    if (myTP == null || myStrength == null) {
        return 0;
    }
    
    // Check weapon cost
    var weaponCost = getWeaponCost(weapon);
    if (weaponCost > myTP && myTP < 15) {
        return 0;
    }
    
    var totalDamage = 0;
    var minRange = getWeaponMinRange(weapon);
    var maxRange = getWeaponMaxRange(weapon);
    var aoeRadius = getWeaponArea(weapon);
    
    // AoE damage calculation starting
    
    // Check all cells we can shoot at within weapon range
    for (var range = minRange; range <= maxRange; range++) {
        var targetCells = getCellsAtExactDistance(fromCell, range);
        
        for (var i = 0; i < count(targetCells); i++) {
            var shootCell = targetCells[i];
            
            // Must have line of sight to the shoot position
            if (!lineOfSight(fromCell, shootCell)) {
                continue;
            }
            
            // Check if target enemy is within AoE radius of this shoot position
            var splashDistance = getCellDistance(shootCell, targetCell);
            
            if (splashDistance <= aoeRadius) {
                // Enemy will be hit by splash damage!
                var baseDamage = 0;
                var effects = getWeaponEffects(weapon);
                
                for (var e = 0; e < count(effects); e++) {
                    if (effects[e][0] == 1) { // EFFECT_DAMAGE
                        var minDmg = effects[e][1];
                        var maxDmg = effects[e][2];
                        baseDamage = (minDmg + maxDmg) / 2;
                        break;
                    }
                }
                
                if (baseDamage > 0) {
                    // Apply strength scaling
                    var scaledDamage = baseDamage * (1 + myStrength / 100.0);
                    
                    // Calculate multiple uses
                    var maxUses = getWeaponMaxUses(weapon);
                    var tpUses = floor(myTP / weaponCost);
                    var actualUses = (maxUses > 0) ? min(tpUses, maxUses) : tpUses;
                    
                    var weaponDamage = scaledDamage * actualUses;
                    
                    // Take the best position (closest splash for maximum accuracy)
                    if (weaponDamage > totalDamage) {
                        totalDamage = weaponDamage;
                        
                        // AoE hit position found
                    }
                }
            }
        }
    }
    
    return totalDamage;
}

// === GET AVAILABLE DAMAGE CHIPS ===
function getAvailableDamageChips() {
    var chips = getChips();
    var damageChips = [];
    
    for (var i = 0; i < count(chips); i++) {
        var chip = chips[i];
        if (chip == CHIP_LIGHTNING) {
            push(damageChips, chip);
        }
    }
    
    return damageChips;
}

// === CALCULATE CHIP-BASED DAMAGE ZONES ===
function calculateChipDamageZones() {
    var chipDamageArray = [];
    var chips = getChips();
    
    if (chips == null || count(chips) == 0) {
        return chipDamageArray;
    }
    
    // Prioritize high-damage chips over SPARK
    var damageChips = [
        {id: CHIP_LIGHTNING, range: 10, damage: 400, cost: 4},
        {id: CHIP_METEORITE, range: 8, damage: 350, cost: 5}
    ];
    
    // Calculating chip damage zones
    
    for (var c = 0; c < count(damageChips); c++) {
        var chipData = damageChips[c];
        if (!inArray(chips, chipData.id)) continue;
        if (chipData.cost > myTP) continue; // Can't afford this chip
        
        // Processing chip zones
        
        // Calculate zones for this chip against all enemies
        for (var e = 0; e < count(allEnemies); e++) {
            var currentEnemy = allEnemies[e];
            if (getLife(currentEnemy) <= 0) continue;
            
            var currentEnemyCell = getCell(currentEnemy);
            
            // Check cells within movement + chip range
            var maxSearchDistance = min(myMP + chipData.range, 20);
            for (var d = 1; d <= maxSearchDistance; d++) {
                var candidateCells = getCellsAtExactDistance(myCell, d);

                for (var i = 0; i < count(candidateCells); i++) {
                    var attackCell = candidateCells[i];
                    var distanceToEnemy = getCellDistance(attackCell, currentEnemyCell);
                    
                    // Check if chip can reach enemy from this position
                    if (distanceToEnemy <= chipData.range) {
                        // SPARK doesn't need LOS, others do
                        var needsLOS = (chipData.id != CHIP_SPARK);
                        var hasLOSCheck = true;
                        
                        if (needsLOS) {
                            hasLOSCheck = lineOfSight(attackCell, currentEnemyCell);
                        }
                        
                        if (hasLOSCheck) {
                            push(chipDamageArray, [attackCell, chipData.damage, chipData.id]);
                        }
                    }
                }
            }
        }
        
        // Only use the best chip for zones to avoid duplicate calculations
        if (count(chipDamageArray) > 0) {
            break;
        }
    }
    
    // Chip damage zones generated
    
    return chipDamageArray;
}

// === UTILITY FUNCTIONS ===
function getCellsAtExactDistance(centerCell, distance) {
    var cells = [];

    // Early exit for invalid distance
    if (distance <= 0 || distance > 20) {
        return cells;
    }

    // Use LeekWars built-in coordinate system (-17 to +17 in both X and Y)
    var centerX = getCellX(centerCell);
    var centerY = getCellY(centerCell);

    // Check all cells in a square around center
    for (var dx = -distance; dx <= distance; dx++) {
        for (var dy = -distance; dy <= distance; dy++) {
            var targetX = centerX + dx;
            var targetY = centerY + dy;

            // Get cell from coordinates (LeekWars handles bounds automatically)
            var targetCell = getCellFromXY(targetX, targetY);

            if (targetCell != null && targetCell >= 0) {
                var actualDistance = getCellDistance(centerCell, targetCell);

                if (abs(actualDistance - distance) < 0.01) { // Use tolerance for floating-point comparison
                    push(cells, targetCell);
                }
            }
        }
    }

    return cells;
}

function checkLineOfSight(fromCell, toCell) {
    return lineOfSight(fromCell, toCell);
}

function countAdjacentObstacles(cell) {
    var obstacles = 0;
    var neighbors = [
        getCellFromXY(getCellX(cell) + 1, getCellY(cell)),
        getCellFromXY(getCellX(cell) - 1, getCellY(cell)),
        getCellFromXY(getCellX(cell), getCellY(cell) + 1),
        getCellFromXY(getCellX(cell), getCellY(cell) - 1)
    ];
    
    for (var i = 0; i < count(neighbors); i++) {
        var neighbor = neighbors[i];
        if (neighbor == null || neighbor == -1) {
            obstacles++;
        }
    }
    
    return obstacles;
}
