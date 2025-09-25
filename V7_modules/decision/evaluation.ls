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

    // NOTE: Corridor optimization disabled to restore full zone marking and
    // original movement behavior in solo/team fights. Keep the original
    // calculation path so all zones are marked and aggregated consistently.
    // if (count(aliveEnemies) > 1 && hasWeapons) { ... }

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
                
                // Early-turn cone pruning to save ops: only consider cells within a 90° cone
                if (getTurn() <= 3) {
                    if (!isWithinNinetyDegreeCone(myCell, currentEnemyCell, attackPosition)) {
                        continue;
                    }
                }
                
                // Always calculate damage - let pathfinding handle reachability
                var distanceToPosition = getCellDistance(myCell, attackPosition);
                
                // For enemy-centric zones, calculate damage from this position to enemy
                var damage = calculateBaseWeaponDamage(weapon, attackPosition, currentEnemyCell);
                
                // Damage calculated for position
                
                // Check Line of Sight for this position
                var hasLoS = checkLineOfSight(attackPosition, currentEnemyCell);
                
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
                    
                }

                // Always mark computed cells for visualization, even if damage == 0
                // Weapon-specific color, gray if no LoS or zero damage
                var markColor = 0;
                if (weapon == WEAPON_M_LASER) markColor = getColor(255, 0, 0);
                else if (weapon == WEAPON_RIFLE) markColor = getColor(255, 165, 0);
                else if (weapon == WEAPON_ENHANCED_LIGHTNINGER) markColor = getColor(128, 0, 128);
                else if (weapon == WEAPON_KATANA) markColor = getColor(0, 0, 255);
                else if (weapon == WEAPON_B_LASER) markColor = getColor(255, 20, 147);
                else if (weapon == WEAPON_GRENADE_LAUNCHER) markColor = getColor(255, 140, 0);
                else if (weapon == WEAPON_ELECTRISOR) markColor = getColor(0, 255, 255);
                else if (weapon == WEAPON_RHINO) markColor = getColor(139, 69, 19);
                else if (weapon == WEAPON_SWORD) markColor = getColor(50, 205, 50);
                else if (weapon == WEAPON_NEUTRINO) markColor = getColor(255, 192, 203);
                else if (weapon == WEAPON_DESTROYER) markColor = getColor(75, 0, 130);
                else if (weapon == WEAPON_FLAME_THROWER) markColor = getColor(255, 69, 0);
                else if (weapon == WEAPON_LASER) markColor = getColor(220, 20, 60);
                else markColor = getColor(255, 255, 0);
                if (!hasLoS || damage <= 0) {
                    markColor = getColor(128, 128, 128);
                }
                mark(attackPosition, markColor);
                
                if (getTurn() <= 3) {
                    // Cell visualized
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
                        // Respect chip min/max range
                        var cMin = getChipMinRange(chip.id);
                        var cMax = getChipMaxRange(chip.id);
                        if (distanceToEnemy < cMin || distanceToEnemy > cMax) {
                            continue;
                        }
                        
                        // Early-turn cone pruning for chip zones as well
                        if (getTurn() <= 3) {
                            if (!isWithinNinetyDegreeCone(myCell, currentEnemyCell, attackCell)) {
                                continue;
                            }
                        }
                        
                        if (distanceToEnemy <= chip.range) {
                            // Check line of sight (SPARK doesn't need LoS)
                            var needsLOS = (chip.id != CHIP_SPARK);
                            var hasLoSCheck = true;
                            
                            if (needsLOS) {
                            hasLoSCheck = checkLineOfSight(attackCell, currentEnemyCell);
                            }
                            
                            if (hasLoSCheck) {
                                // Calculate chip base damage (use average)
                                var chipDamage = (chip.minDmg + chip.maxDmg) / 2;
                                // Apply magic scaling for magic builds
                                if (isMagicBuild && myMagic != null) {
                                    chipDamage = chipDamage * (1 + myMagic / 100.0);
                                }
                                var areaShape = getChipAreaShapeNormalized(chip.id);
                                var totalPerCast = 0;
                                if (areaShape != null && areaShape != AREA_POINT) {
                                    // AoE chip: aim at enemy cell; sum over all enemies within AoE shape
                                    var multiSum = 0;
                                    for (var ei = 0; ei < count(allEnemies); ei++) {
                                        var ent = allEnemies[ei];
                                        if (getLife(ent) <= 0) continue;
                                        var eCell = getCell(ent);
                                        if (eCell == null) continue;
                                        if (!isCellInAoEShapeForShot(attackCell, currentEnemyCell, eCell, areaShape)) continue;
                                        var percent = getAoEPercentAt(currentEnemyCell, eCell, areaShape);
                                        multiSum += chipDamage * percent;
                                    }
                                    totalPerCast = multiSum;
                                } else {
                                    // Single target chip: damage to current enemy only
                                    totalPerCast = chipDamage;
                                }
                                // Uses
                                var tpUses = floor(myTP / chip.cost);
                                var totalChipDamage = totalPerCast * tpUses;
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
    if (!checkLineOfSight(fromCell, targetCell)) {
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

        // Multi-hit enhancement for line weapons (LASER/FLAME):
        // If multiple enemies are aligned along the same axis and direction, 
        // sum their expected damages (with a light AoE falloff around the targeted cell).
        var multiLineDamage = calculateLineMultiTargetDamageFromCell(weapon, fromCell, targetCell);
        if (multiLineDamage > 0) {
            return multiLineDamage;
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
    var areaShape = getWeaponAreaShapeNormalized(weapon); // AREA_* constant or numeric radius
    
    // AoE damage calculation starting
    
    // Check all cells we can shoot at within weapon range, and sum damage over ALL enemies per AoE shape
    for (var range = minRange; range <= maxRange; range++) {
        var targetCells = getCellsAtExactDistance(fromCell, range);
        
        for (var i = 0; i < count(targetCells); i++) {
            var shootCell = targetCells[i];
            
            // Must have line of sight to the shoot position
            if (!checkLineOfSight(fromCell, shootCell)) {
                continue;
            }
            
            // Base damage per enemy at the center
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
            if (baseDamage == 0) continue;
            var scaledBase = baseDamage * (1 + myStrength / 100.0);

            // Compute total multi-enemy damage at this shot cell per AREA_* shape
            var multiSum = 0;
            for (var ei = 0; ei < count(allEnemies); ei++) {
                var ent = allEnemies[ei];
                if (getLife(ent) <= 0) continue;
                var eCell = getCell(ent);
                if (eCell == null) continue;
                if (!isCellInAoEShapeForShot(fromCell, shootCell, eCell, areaShape)) continue;
                var percent = getAoEPercentAt(shootCell, eCell, areaShape);
                multiSum += scaledBase * percent;
            }

            if (multiSum > 0) {
                var maxUses = getWeaponMaxUses(weapon);
                var tpUses = floor(myTP / weaponCost);
                var actualUses = (maxUses > 0) ? min(tpUses, maxUses) : tpUses;
                var totalAtShot = multiSum * actualUses;
                if (totalAtShot > totalDamage) {
                    totalDamage = totalAtShot;
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
        {id: CHIP_LIGHTNING, damage: 400, cost: 4},
        {id: CHIP_METEORITE, damage: 350, cost: 5}
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
            // Use actual chip max range from API
            var cMax = getChipMaxRange(chipData.id);
            var cMin = getChipMinRange(chipData.id);
            var maxSearchDistance = min(myMP + cMax, 20);
            for (var d = 1; d <= maxSearchDistance; d++) {
                var candidateCells = getCellsAtExactDistance(myCell, d);

                for (var i = 0; i < count(candidateCells); i++) {
                    var attackCell = candidateCells[i];
                    var distanceToEnemy = getCellDistance(attackCell, currentEnemyCell);
                    
                    // Check if chip can reach enemy from this position (respect min/max)
                    if (distanceToEnemy >= cMin && distanceToEnemy <= cMax) {
                        // SPARK doesn't need LOS, others do
                        var needsLOS = (chipData.id != CHIP_SPARK);
                        var hasLOSCheck = true;
                        
                        if (needsLOS) {
                            hasLOSCheck = checkLineOfSight(attackCell, currentEnemyCell);
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
// Lightweight ring cache to avoid recomputing the same Manhattan rings.
// Stored globally; initialize lazily on first use.
global ringCache = null;
function getCellsAtExactDistance(centerCell, distance) {
    var cells = [];

    // Early exit for invalid distance
    if (distance <= 0 || distance > 20) {
        return cells;
    }

    if (ringCache == null) { ringCache = [:]; }
    // Cache hit?
    var key = centerCell + ":" + distance;
    if (ringCache[key] != null) {
        return ringCache[key];
    }

    var cx = getCellX(centerCell);
    var cy = getCellY(centerCell);

    // Generate Manhattan ring: |dx| + |dy| == distance
    for (var dx = -distance; dx <= distance; dx++) {
        var adx = abs(dx);
        var dy = distance - adx;
        var x1 = cx + dx;
        var y1 = cy + dy;
        var c1 = getCellFromXY(x1, y1);
        if (c1 != null && c1 >= 0) { push(cells, c1); }
        if (dy != 0) {
            var y2 = cy - dy;
            var c2 = getCellFromXY(x1, y2);
            if (c2 != null && c2 >= 0) { push(cells, c2); }
        }
    }

    // Store in cache and return
    ringCache[key] = cells;
    return ringCache[key];
}

function checkLineOfSight(fromCell, toCell) {
    // Use cached LOS wrapper for performance.
    return cachedLineOfSight(fromCell, toCell, null);
}

function checkLineOfSightIgnore(fromCell, toCell, ignoreEntities) {
    // Variant that forwards an ignore list (entity or array of entities).
    return cachedLineOfSight(fromCell, toCell, ignoreEntities);
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

// Cone filter utility: returns true if testCell lies within a 90° cone
// centered on the vector from myCell -> axisCell (i.e., towards the enemy).
// Uses a sqrt-free check: 2 * (u·v)^2 >= |u|^2 * |v|^2 (cos^2 45° = 1/2)
function isWithinNinetyDegreeCone(myCell, axisCell, testCell) {
    var mx = getCellX(myCell);
    var my = getCellY(myCell);
    var ax = getCellX(axisCell);
    var ay = getCellY(axisCell);
    var tx = getCellX(testCell);
    var ty = getCellY(testCell);

    var ux = ax - mx;
    var uy = ay - my;
    var vx = tx - mx;
    var vy = ty - my;

    var len2u = ux * ux + uy * uy;
    var len2v = vx * vx + vy * vy;
    if (len2u == 0 || len2v == 0) return true; // degenerate; don't filter
    var dot = ux * vx + uy * vy;
    var dot2 = dot * dot;
    // Inside cone if angle ≤ 45°: 2*dot^2 ≥ |u|^2 * |v|^2
    return (2 * dot2) >= (len2u * len2v);
}

// === AREA_* SHAPE SUPPORT ===
function isCellInAoEShapeForShot(shooterCell, shotCell, testCell, areaVal) {
    // Numeric fallback: treat as Manhattan circle radius
    if (areaVal == null) return false;
    if (areaVal == 0) return false;
    var sx = getCellX(shotCell);
    var sy = getCellY(shotCell);
    var tx = getCellX(testCell);
    var ty = getCellY(testCell);
    var dx = tx - sx;
    var dy = ty - sy;
    var adx = abs(dx);
    var ady = abs(dy);
    
    // Numeric radius (compat with existing wrapper): Circle (Manhattan) radius areaVal
    if (areaVal == 1 || areaVal == 2 || areaVal == 3) {
        return (abs(dx) + abs(dy)) <= areaVal;
    }
    
    // Constants: compare against built-ins if available
    if (areaVal == AREA_POINT) {
        return (shotCell == testCell);
    }
    if (areaVal == AREA_CIRCLE_1 || areaVal == AREA_CIRCLE_2 || areaVal == AREA_CIRCLE_3) {
        var r = (areaVal == AREA_CIRCLE_1) ? 1 : (areaVal == AREA_CIRCLE_2) ? 2 : 3;
        return (abs(dx) + abs(dy)) <= r;
    }
    if (areaVal == AREA_SQUARE_1 || areaVal == AREA_SQUARE_2) {
        var r2 = (areaVal == AREA_SQUARE_1) ? 1 : 2;
        return max(adx, ady) <= r2;
    }
    if (areaVal == AREA_PLUS_1 || areaVal == AREA_PLUS_2 || areaVal == AREA_PLUS_3) {
        var rp = (areaVal == AREA_PLUS_1) ? 1 : (areaVal == AREA_PLUS_2) ? 2 : 3;
        return ((abs(dx) + abs(dy)) <= rp) && (dx == 0 || dy == 0);
    }
    if (areaVal == AREA_X_1 || areaVal == AREA_X_2 || areaVal == AREA_X_3) {
        var rx = (areaVal == AREA_X_1) ? 1 : (areaVal == AREA_X_2) ? 2 : 3;
        return (adx == ady && adx <= rx);
    }
    if (areaVal == AREA_LASER_LINE) {
        // Laser line AoE: along the beam direction from shooter to shot (100% per cell, no falloff)
        if (shooterCell == null) return false; // need direction
        var fx = getCellX(shooterCell);
        var fy = getCellY(shooterCell);
        var dirX = sign(sx - fx);
        var dirY = sign(sy - fy);
        // Must be axis aligned
        // Must be axis-aligned (exactly one axis non-zero direction)
        if (!(((dirX == 0) != (dirY == 0)))) return false;
        if (!isOnSameLine(shotCell, testCell)) return false;
        // Same half-line direction from shot cell
        if (dirX != 0 && sign(tx - sx) != dirX) return false;
        if (dirY != 0 && sign(ty - sy) != dirY) return false;
        return true;
    }
    
    // Unknown constant: be safe and include center only
    return (shotCell == testCell);
}

function getAoEPercentAt(centerCell, cell, areaVal) {
    // Lasers (AREA_LASER_LINE) do not reduce
    if (areaVal == AREA_LASER_LINE) return 1;
    // Default falloff per spec
    var dist = getCellDistance(centerCell, cell);
    return max(0, 1 - 0.2 * dist);
}

// === LINE MULTI-HIT DAMAGE (LASERS/FLAME) ===
// Sums damage over all aligned enemies in the direction from fromCell to targetCell.
function calculateLineMultiTargetDamageFromCell(weapon, fromCell, targetCell) {
    if (!isLineWeapon(weapon)) return 0;
    // Range and LOS already validated by caller; re-check conservative gates
    if (!checkLineOfSight(fromCell, targetCell)) return 0;
    if (!isOnSameLine(fromCell, targetCell)) return 0;

    var minRange = getWeaponMinRange(weapon);
    var maxRange = getWeaponMaxRange(weapon);
    var distance = getCellDistance(fromCell, targetCell);
    if (distance < minRange || distance > maxRange) return 0;

    // Base average damage for this weapon
    var base = 0;
    var eff = getWeaponEffects(weapon);
    for (var i = 0; i < count(eff); i++) {
        if (eff[i][0] == 1) { base = (eff[i][1] + eff[i][2]) / 2; break; }
    }
    if (base == 0) return 0;
    var scaledBase = base * (1 + myStrength / 100.0);

    // Determine shooting direction (toward targetCell)
    var fx = getCellX(fromCell);
    var fy = getCellY(fromCell);
    var tx = getCellX(targetCell);
    var ty = getCellY(targetCell);
    var dirX = sign(tx - fx);
    var dirY = sign(ty - fy);

    // Multi-hit sum. Lasers deal 100% to every cell; non-laser line weapons use falloff from target.
    var sum = 0;
    for (var ei = 0; ei < count(allEnemies); ei++) {
        var ent = allEnemies[ei];
        if (getLife(ent) <= 0) continue;
        var eCell = getCell(ent);
        if (eCell == null) continue;
        // Must be on same axis line
        if (!isOnSameLine(fromCell, eCell)) continue;

        // Ensure enemy lies in the same half-line direction as target
        var ex = getCellX(eCell);
        var ey = getCellY(eCell);
        if (dirX != 0 && sign(ex - fx) != dirX) continue;
        if (dirY != 0 && sign(ey - fy) != dirY) continue;

        // Must be within weapon max range from shooter
        var dFromShooter = getCellDistance(fromCell, eCell);
        if (dFromShooter < minRange || dFromShooter > maxRange) continue;

        // LOS to targetCell was required; for multi-hit line, assume pass-through on aligned enemies
        // Lasers (and FLAME_THROWER): no reduction. Others: apply falloff relative to targeted enemy.
        var percent = 1;
        if (!(weapon == WEAPON_M_LASER || weapon == WEAPON_B_LASER || weapon == WEAPON_LASER || weapon == WEAPON_FLAME_THROWER)) {
            var distCenter = getCellDistance(targetCell, eCell);
            percent = max(0, 1 - 0.2 * distCenter);
        }
        sum += scaledBase * percent;
    }

    if (sum <= 0) return 0;
    var maxUses = getWeaponMaxUses(weapon);
    var wCost = getWeaponCost(weapon);
    var uses = floor(myTP / wCost);
    if (maxUses > 0) uses = min(uses, maxUses);
    if (uses <= 0) return 0;
    return sum * uses;
}

// sign utility for line direction
function sign(v) { if (v > 0) return 1; if (v < 0) return -1; return 0; }
// Map known weapons to proper AREA_* constants when wrapper returns numeric
function getWeaponAreaShapeNormalized(weapon) {
    var a = getWeaponArea(weapon);
    // Enhanced Lightninger is a 3x3 square (AREA_SQUARE_1)
    if (weapon == WEAPON_ENHANCED_LIGHTNINGER) return AREA_SQUARE_1;
    // Lightninger (non-enhanced) is diagonal cross radius 1
    if (weapon == WEAPON_LIGHTNINGER) return AREA_X_1;
    // Grenade launcher is circle radius 2
    if (weapon == WEAPON_GRENADE_LAUNCHER) return AREA_CIRCLE_2;
    // Electrisor is circle radius 1
    if (weapon == WEAPON_ELECTRISOR) return AREA_CIRCLE_1;
    // Default: return raw value (numeric treated as circle radius)
    return a;
}

// Normalize chip AoE shapes to AREA_* constants
function getChipAreaShapeNormalized(chip) {
    var a = getChipArea(chip);
    if (chip == CHIP_TOXIN) return AREA_CIRCLE_2;
    return a;
}
