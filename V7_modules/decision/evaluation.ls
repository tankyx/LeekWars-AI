// V7 Module: decision/evaluation.ls
// Enemy-centric damage zone calculation

// === MAIN DAMAGE ZONE CALCULATION (ARRAY-ONLY VERSION) ===
function calculateDamageZonesArray(enemyCell) {
    // Direct array return - no map conversion to avoid LeekScript bug
    var damageArray = []; // Array of [cellId, damage] pairs
    
    if (debugEnabled) {
        debugW("ARRAY-ONLY: Created damage array for enemy at " + enemyCell);
    }
    
    var weapons = getWeapons();
    
    if (debugEnabled) {
        debugW("=== DAMAGE ZONE CALCULATION (ARRAY-ONLY) ===");
        for (var i = 0; i < count(weapons); i++) {
            var w = weapons[i];
            debugW("Weapon " + i + ": " + w + " (range " + getWeaponMinRange(w) + "-" + getWeaponMaxRange(w) + ", cost " + getWeaponCost(w) + ")");
        }
    }
    
    // Calculate weapon damage zones from enemy perspective 
    for (var i = 0; i < count(weapons); i++) {
        var weapon = weapons[i];
        calculateWeaponDamageZone(weapon, enemyCell, damageArray);
    }
    
    // Add chip damage zones
    var chips = getDamageChips();
    if (debugEnabled) {
        debugW("Available chips: " + count(chips));
    }
    for (var j = 0; j < count(chips); j++) {
        var chip = chips[j];
        if (canUseChip(chip, getEntity())) {
            calculateChipDamageZone(chip, enemyCell, damageArray);
        }
    }
    
    if (debugEnabled) {
        debugW("ARRAY-ONLY COMPLETE: " + count(damageArray) + " damage entries");
    }
    
    return damageArray; // Return array directly
}

// === MAIN DAMAGE ZONE CALCULATION (MAP VERSION - LEGACY) ===
function calculateDamageZones(enemyCell) {
    // WORKAROUND: Use array instead of map due to LeekScript map corruption bug
    var damageArray = []; // Array of [cellId, damage] pairs
    
    if (debugEnabled) {
        debugW("INIT: Created empty damage array (workaround for map bug)");
    }
    var weapons = getWeapons();
    
    if (debugEnabled) {
        debugW("=== DAMAGE ZONE CALCULATION ===");
        for (var i = 0; i < count(weapons); i++) {
            var w = weapons[i];
            debugW("Weapon " + i + ": " + w + " (range " + getWeaponMinRange(w) + "-" + getWeaponMaxRange(w) + ", cost " + getWeaponCost(w) + ")");
        }
    }
    
    // Calculate weapon damage zones from enemy perspective 
    for (var i = 0; i < count(weapons); i++) {
        var weapon = weapons[i];
        calculateWeaponDamageZone(weapon, enemyCell, damageArray);
    }
    
    // Add chip damage zones
    var chips = getDamageChips();
    if (debugEnabled) {
        debugW("Available chips: " + count(chips));
    }
    for (var j = 0; j < count(chips); j++) {
        var chip = chips[j];
        if (canUseChip(chip, getEntity())) {
            calculateChipDamageZone(chip, enemyCell, damageArray);
        }
    }
    
    // Apply tactical bonuses (temporarily disabled for debugging)
    // applyTacticalBonuses(localDamageMap, enemyCell);
    
    // Convert array back to map for compatibility
    var resultMap = [:];
    var cellCount = count(damageArray);
    var maxDamage = 0;
    
    if (debugEnabled) {
        debugW("ARRAY TO MAP: Converting " + cellCount + " array entries");
    }
    
    for (var i = 0; i < cellCount; i++) {
        var entry = damageArray[i];
        var cellId = entry[0];
        var damage = entry[1];
        
        resultMap[cellId] = damage;
        
        if (damage > maxDamage) {
            maxDamage = damage;
        }
        
        if (debugEnabled && i < 3) {
            debugW("ARRAY CONVERT: [" + cellId + ", " + damage + "] -> resultMap[" + cellId + "]=" + resultMap[cellId]);
        }
    }
    
    if (debugEnabled) {
        debugW("CONVERSION COMPLETE: " + cellCount + " cells, max damage: " + maxDamage);
        debug("Damage zones: " + cellCount + " cells, max: " + maxDamage + ", top zones: 0");
    }
    
    return resultMap;
}

// === WEAPON DAMAGE ZONE CALCULATION ===
function calculateWeaponDamageZone(weapon, enemyCell, damageArray) {
    var minRange = getWeaponMinRange(weapon);
    var maxRange = getWeaponMaxRange(weapon);
    
    // Safety bounds: limit maximum range to prevent infinite loops
    maxRange = min(maxRange, 20);
    
    // Calculate damage zones by range rings
    for (var range = minRange; range <= maxRange; range++) {
        var cells = getCellsAtDistance(enemyCell, range);
        
        // Safety limit: don't process more than 100 cells per weapon
        var cellLimit = min(count(cells), 100);
        
        for (var i = 0; i < cellLimit; i++) {
            var cell = cells[i];
            
            // All weapons need LOS
            if (!hasLOS(cell, enemyCell)) continue;
            
            
            // Laser weapons need X or Y axis alignment
            if (isLaserWeapon(weapon)) {
                var fromX = getCellX(cell);
                var fromY = getCellY(cell);
                var toX = getCellX(enemyCell);
                var toY = getCellY(enemyCell);
                
                var xAligned = (fromX == toX);
                var yAligned = (fromY == toY);
                
                // Must be aligned on exactly one axis (XOR)
                if (!(xAligned != yAligned)) continue;
            }
            
            // Calculate weapon damage from this cell (including AoE)
            var damage = calculateWeaponDamageFromCell(weapon, cell, enemyCell);
            
            // Add AoE damage bonus for area weapons
            if (weapon == WEAPON_ENHANCED_LIGHTNINGER || weapon == WEAPON_GRENADE_LAUNCHER) {
                var aoeDamage = calculateAoEDamage(weapon, cell, enemyCell);
                damage += aoeDamage;
                
                if (debugEnabled && aoeDamage > 0) {
                    debugW("AoE BONUS: " + weapon + " at " + cell + " gets +" + aoeDamage + " AoE damage");
                }
            }
            
            // M-Laser alignment bonus - prioritize alignment positions
            if (weapon == WEAPON_M_LASER && damage > 0) {
                var fromX = getCellX(cell);
                var fromY = getCellY(cell);
                var toX = getCellX(enemyCell);
                var toY = getCellY(enemyCell);
                
                var xAligned = (fromX == toX);
                var yAligned = (fromY == toY);
                
                if (xAligned || yAligned) {
                    damage *= 1.3; // 30% bonus for M-Laser alignment
                }
            }
            
            // Add to damage array (accumulate multiple weapons)
            if (damage > 0 && cell >= 0 && cell <= 612) {
                // Find existing entry for this cell
                var existingIndex = -1;
                for (var k = 0; k < count(damageArray); k++) {
                    if (damageArray[k][0] == cell) {
                        existingIndex = k;
                        break;
                    }
                }
                
                if (existingIndex >= 0) {
                    // Update existing entry
                    var oldValue = damageArray[existingIndex][1];
                    var newValue = oldValue + damage;
                    damageArray[existingIndex][1] = newValue;
                    
                } else {
                    // Add new entry
                    push(damageArray, [cell, damage]);
                    
                }
                
                // Mark cells on map with weapon damage text for visual debugging
                if (debugEnabled && damage > 0) {
                    var weaponColor = getWeaponColor(weapon);
                    var displayDamage = floor(damage + 0.5);
                    markText(cell, "" + displayDamage, weaponColor, 8);
                }
            }
        }
    }
}

// === CHIP DAMAGE ZONE CALCULATION ===
function calculateChipDamageZone(chip, enemyCell, damageArray) {
    var minRange = getChipMinRange(chip);
    var maxRange = getChipMaxRange(chip);
    var needsLOS = chipNeedLos(chip);
    
    for (var range = minRange; range <= maxRange; range++) {
        var cells = getCellsAtDistance(enemyCell, range);
        
        for (var i = 0; i < count(cells); i++) {
            var cell = cells[i];
            
            // Skip if chip needs LOS but doesn't have it
            if (needsLOS && !hasLOS(cell, enemyCell)) continue;
            
            // Get chip damage from effects
            var effects = getChipEffects(chip);
            var baseDamage = 0;
            
            // Find damage effect - EFFECT_DAMAGE = 1
            for (var j = 0; j < count(effects); j++) {
                if (effects[j][0] == 1) { // EFFECT_DAMAGE constant
                    var minDamage = effects[j][1];
                    var maxDamage = effects[j][2];
                    baseDamage = (minDamage + maxDamage) / 2; // Average chip damage
                    break;
                }
            }
            
            if (baseDamage == 0) continue;
            
            // Apply strength/magic scaling
            var damage;
            if (chip == CHIP_LIGHTNING || chip == CHIP_SPARK) {
                damage = baseDamage * (1 + myStrength / 100.0);
            } else {
                damage = baseDamage * (1 + myMagic / 100.0);
            }
            
            // Add to damage array (same approach as weapons)
            if (damage > 0 && cell >= 0 && cell <= 612) {
                // Find existing entry for this cell
                var existingIndex = -1;
                for (var k = 0; k < count(damageArray); k++) {
                    if (damageArray[k][0] == cell) {
                        existingIndex = k;
                        break;
                    }
                }
                
                if (existingIndex >= 0) {
                    // Update existing entry
                    var oldValue = damageArray[existingIndex][1];
                    var newValue = oldValue + damage;
                    damageArray[existingIndex][1] = newValue;
                    
                } else {
                    // Add new entry
                    push(damageArray, [cell, damage]);
                    
                }
            }
        }
    }
}

// === WEAPON DAMAGE CALCULATION ===
function calculateWeaponDamageFromCell(weapon, fromCell, targetCell) {
    // Ensure global variables are initialized
    if (myTP == null || myStrength == null) {
        if (debugEnabled) {
            debugE("Global variables not initialized: myTP=" + myTP + ", myStrength=" + myStrength);
        }
        return 0;
    }
    
    // Don't check canUseWeapon(weapon, enemy) here since we're calculating from different positions
    // Instead, check the weapon's basic availability
    var weaponCost = getWeaponCost(weapon);
    if (weaponCost > myTP) {
        return 0;
    }
    
    var distance = getCellDistance(fromCell, targetCell);
    var minRange = getWeaponMinRange(weapon);
    var maxRange = getWeaponMaxRange(weapon);
    
    // Check if in range
    if (distance < minRange || distance > maxRange) {
        return 0;
    }
    
    // Check LOS for all weapons
    if (!hasLOS(fromCell, targetCell)) {
        return 0;
    }
    
    // Check laser alignment (X or Y axis only, not diagonal)
    if (isLaserWeapon(weapon)) {
        var fromX = getCellX(fromCell);
        var fromY = getCellY(fromCell);
        var toX = getCellX(targetCell);
        var toY = getCellY(targetCell);
        
        // Must be aligned on X-axis XOR Y-axis (not both, not neither)
        var xAligned = (fromX == toX);
        var yAligned = (fromY == toY);
        
        if (!(xAligned != yAligned)) { // XOR: one true, one false
            return 0;
        }
    }
    
    // Get base weapon damage using proper method
    var effects = getWeaponEffects(weapon);
    var baseDamage = 0;
    
    
    // Find damage effect - EFFECT_DAMAGE = 1
    for (var i = 0; i < count(effects); i++) {
        if (effects[i][0] == 1) { // EFFECT_DAMAGE constant
            // Effects format: [type, min, max, turns, targets, stackable]
            var minDamage = effects[i][1];
            var maxDamage = effects[i][2];
            
            if (minDamage == maxDamage) {
                baseDamage = minDamage; // Fixed damage (like Katana: 77)
            } else {
                baseDamage = (minDamage + maxDamage) / 2; // Average damage
            }
            
            break;
        }
    }
    
    
    if (baseDamage == 0) return 0;
    
    // Apply strength scaling
    var scaledDamage = baseDamage * (1 + myStrength / 100.0);
    
    // Calculate maximum uses with available TP (reuse weaponCost from above)
    var maxUses = getWeaponMaxUses(weapon);
    
    
    if (weaponCost <= 0 || myTP <= 0) {
        return 0;
    }
    
    var tpUses = floor(myTP / weaponCost);
    
    var actualUses = (maxUses > 0) ? min(tpUses, maxUses) : tpUses;
    
    // Calculate total damage potential
    var totalDamage = scaledDamage * actualUses;
    
    // Apply weapon-specific bonuses
    if (weapon == WEAPON_KATANA && distance == 1) {
        totalDamage *= 1.2; // 20% melee bonus
    }
    
    
    
    return totalDamage;
}

// === TACTICAL BONUSES ===
function applyTacticalBonuses(damageMap, enemyCell) {
    if (debugEnabled) {
        debugW("Applying tactical bonuses to damage map");
    }
    
    // Create array of cells to avoid modifying map while iterating
    var cells = [];
    for (var cell in damageMap) {
        push(cells, cell);
    }
    
    // Apply bonuses using separate iteration
    for (var i = 0; i < count(cells); i++) {
        var cell = cells[i];
        var bonus = 1.0;
        
        // Peek-a-boo bonus: favor cells with adjacent cover
        var coverCount = countAdjacentObstacles(cell);
        if (coverCount > 0) {
            bonus += coverCount * PEEK_COVER_BONUS;
        }
        
        // Distance penalty: slightly favor closer positions for movement efficiency
        var distance = getCellDistance(cell, myCell);
        if (distance > myMP) {
            bonus = bonus * 0.8; // 20% penalty for unreachable cells
        }
        
        // Apply bonus
        damageMap[cell] = damageMap[cell] * bonus;
    }
}

// === UTILITY FUNCTIONS ===
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

function getCellsAtDistance(centerCell, distance) {
    var cells = [];
    
    // Simple and reliable: iterate through all 613 cells
    for (var cell = 0; cell < 613; cell++) {
        if (getCellDistance(centerCell, cell) == distance) {
            push(cells, cell);
        }
    }
    
    return cells;
}

// === WEAPON TYPE HELPERS ===
function isLaserWeapon(weapon) {
    // All laser weapons need X or Y axis alignment
    return (weapon == WEAPON_M_LASER ||
            weapon == WEAPON_LASER ||
            weapon == WEAPON_B_LASER);
    // WEAPON_ENHANCED_LIGHTNINGER is NOT a laser - it's a grenade launcher with 3x3 AoE
}

// === VISUAL DEBUG HELPERS ===
function getWeaponColor(weapon) {
    if (weapon == WEAPON_ENHANCED_LIGHTNINGER) return getColor(0, 0, 255);     // Blue
    if (weapon == WEAPON_RIFLE) return getColor(0, 255, 0);                    // Green
    if (weapon == WEAPON_M_LASER) return getColor(255, 255, 0);                // Yellow
    if (weapon == WEAPON_KATANA) return getColor(128, 0, 128);                 // Purple
    if (weapon == WEAPON_B_LASER) return getColor(0, 255, 255);                // Cyan
    if (weapon == WEAPON_GRENADE_LAUNCHER) return getColor(255, 128, 0);       // Orange
    if (weapon == WEAPON_RHINO) return getColor(255, 0, 0);                    // Red
    return getColor(255, 255, 255);                                            // Unknown weapon - White
}

function hasLOS(fromCell, toCell) {
    // Use cached result if available
    var cacheKey = fromCell + "_" + toCell;
    if (losCache[cacheKey] != null) {
        return losCache[cacheKey];
    }
    
    // Calculate and cache result
    var result = lineOfSight(fromCell, toCell);
    losCache[cacheKey] = result;
    
    return result;
}

// === POST-COMBAT COVER SEEKING ===
function findCoverPosition() {
    if (myMP <= 0) return null;
    
    var bestCell = null;
    var bestScore = 0;
    
    if (debugEnabled) {
        debugW("=== SEEKING COVER POSITION ===");
        debugW("Current position: " + myCell + ", MP: " + myMP);
    }
    
    // Check all cells within movement range
    for (var x = getCellX(myCell) - myMP; x <= getCellX(myCell) + myMP; x++) {
        for (var y = getCellY(myCell) - myMP; y <= getCellY(myCell) + myMP; y++) {
            var cell = getCellFromXY(x, y);
            
            if (cell != null && cell != -1 && cell != myCell) {
                var moveDistance = getCellDistance(myCell, cell);
                
                // Only consider cells within movement range
                if (moveDistance <= myMP) {
                    var coverScore = calculateCoverScore(cell);
                    
                    if (coverScore > bestScore) {
                        bestScore = coverScore;
                        bestCell = cell;
                    }
                }
            }
        }
    }
    
    if (debugEnabled && bestCell != null) {
        debugW("COVER: Found position " + bestCell + " with score " + bestScore);
    }
    
    return bestCell;
}

function calculateCoverScore(cell) {
    var score = 0;
    
    // Priority 1: Break line of sight with enemy
    if (!hasLOS(cell, enemyCell)) {
        score += 100; // High bonus for breaking LOS
        if (debugEnabled) {
            debugW("COVER BONUS: Cell " + cell + " breaks LOS with enemy");
        }
    }
    
    // Priority 2: Count adjacent obstacles for defensive positioning
    var adjacentObstacles = countAdjacentObstacles(cell);
    score += adjacentObstacles * 20; // 20 points per adjacent obstacle
    
    // Priority 3: Prefer positions that maintain weapon range options
    var weaponRangeScore = calculateWeaponRangeScore(cell);
    score += weaponRangeScore;
    
    // Priority 4: Distance penalty - don't move too far unless necessary
    var distance = getCellDistance(myCell, cell);
    score -= distance * 2; // Small penalty for distance
    
    // Priority 5: Don't get too close to enemy (unless melee build)
    var enemyDistance = getCellDistance(cell, enemyCell);
    if (enemyDistance < 3) {
        score -= 30; // Penalty for being too close
    }
    
    return score;
}

function calculateWeaponRangeScore(cell) {
    var score = 0;
    var weapons = getWeapons();
    var enemyDistance = getCellDistance(cell, enemyCell);
    
    // Check how many weapons would be in range from this position
    for (var i = 0; i < count(weapons); i++) {
        var weapon = weapons[i];
        var minRange = getWeaponMinRange(weapon);
        var maxRange = getWeaponMaxRange(weapon);
        
        if (enemyDistance >= minRange && enemyDistance <= maxRange) {
            score += 10; // Bonus for each weapon in range
            
            // Extra bonus for high-priority weapons
            if (weapon == WEAPON_RHINO || weapon == WEAPON_B_LASER) {
                score += 5; // Favor positions that keep new weapons in range
            }
        }
    }
    
    return score;
}

function seekCoverAfterCombat() {
    if (myMP <= 1) {
        if (debugEnabled) {
            debugW("COVER: Insufficient MP (" + myMP + ") for cover movement");
        }
        return false;
    }
    
    // Don't seek cover if already in good defensive position
    var currentCoverScore = calculateCoverScore(myCell);
    if (currentCoverScore >= 50) {
        if (debugEnabled) {
            debugW("COVER: Current position already has good cover (score: " + currentCoverScore + ")");
        }
        return false;
    }
    
    var coverCell = findCoverPosition();
    
    if (coverCell != null) {
        var oldCell = myCell;
        var mpUsed = moveTowardCells([coverCell], myMP);
        myCell = getCell();
        myMP = getMP();
        
        if (debugEnabled) {
            debugW("COVER: Moved from " + oldCell + " to " + myCell + " (MP used: " + mpUsed + ")");
        }
        
        // Mark the cover position for visual feedback
        if (debugEnabled) {
            markText(myCell, "COVER", getColor(128, 255, 128), 8);
        }
        
        return mpUsed > 0;
    }
    
    if (debugEnabled) {
        debugW("COVER: No suitable cover position found");
    }
    
    return false;
}

// === AOE DAMAGE CALCULATION ===
function calculateAoEDamage(weapon, attackerCell, targetCell) {
    // Local area weapon check
    var isArea = (weapon == WEAPON_ENHANCED_LIGHTNINGER || weapon == WEAPON_GRENADE_LAUNCHER);
    if (!isArea) return 0;
    
    var aoeDamage = 0;
    var area = getWeaponArea(weapon);
    
    if (weapon == WEAPON_ENHANCED_LIGHTNINGER) {
        // Enhanced Lightninger: 3x3 square around target
        aoeDamage = calculateSquareAoE(attackerCell, targetCell, 1); // 1 = radius for 3x3
    } else if (weapon == WEAPON_GRENADE_LAUNCHER) {
        // Grenade Launcher: Circle radius 2 around target  
        aoeDamage = calculateCircleAoE(attackerCell, targetCell, area); // area = 2
    }
    
    return aoeDamage;
}

function calculateSquareAoE(attackerCell, targetCell, radius) {
    var bonusDamage = 0;
    var enemiesHit = 0;
    
    // Get the center of the explosion (targetCell)
    var centerX = getCellX(targetCell);
    var centerY = getCellY(targetCell);
    
    // Check all cells in the square area
    for (var x = centerX - radius; x <= centerX + radius; x++) {
        for (var y = centerY - radius; y <= centerY + radius; y++) {
            var cell = getCellFromXY(x, y);
            if (cell < 0) continue; // Invalid cell
            
            // Calculate distance from explosion center
            var distanceFromCenter = getCellDistance(targetCell, cell);
            
            // AoE damage formula: max(0, 1 - 0.2 * distance)
            var aoePercentage = max(0, 1 - 0.2 * distanceFromCenter);
            
            if (aoePercentage > 0) {
                // Check if there's an enemy on this cell
                var cellContent = getCellContent(cell);
                if (cellContent == CELL_ENTITY) {
                    bonusDamage += aoePercentage * 100; // Base damage scaled
                    enemiesHit++;
                }
            }
        }
    }
    
    if (debugEnabled && bonusDamage > 0) {
        debugW("Square AoE: " + enemiesHit + " enemies hit, bonus damage: " + bonusDamage);
    }
    
    return bonusDamage;
}

function calculateCircleAoE(attackerCell, targetCell, radius) {
    var bonusDamage = 0;
    var enemiesHit = 0;
    
    // Get base weapon damage for scaling
    var baseDamage = calculateWeaponDamageFromCell(WEAPON_GRENADE_LAUNCHER, attackerCell, targetCell);
    
    // Check all cells within radius around target (Grenade Launcher)
    for (var range = 1; range <= radius; range++) {
        var cells = getCellsAtDistance(targetCell, range);
        
        for (var i = 0; i < count(cells); i++) {
            var checkCell = cells[i];
            
            // Calculate exact distance from AoE center
            var distanceFromCenter = getCellDistance(targetCell, checkCell);
            
            // Skip if outside AoE radius
            if (distanceFromCenter > radius) continue;
            
            // AoE damage formula: max(0, 1 - 0.2 * distance)
            var aoePercentage = max(0, 1 - 0.2 * distanceFromCenter);
            
            if (aoePercentage > 0) {
                // Check if there's an enemy on this cell
                var leekOnCell = getCellContent(checkCell);
                if (leekOnCell != null && leekOnCell != myLeek && isAlive(leekOnCell)) {
                    enemiesHit++;
                    // Add AoE damage with proper percentage calculation
                    bonusDamage += baseDamage * aoePercentage;
                    
                    if (debugEnabled) {
                        debugW("GRENADE LAUNCHER AoE: Cell " + checkCell + " at distance " + distanceFromCenter + " = " + (aoePercentage * 100) + "% damage");
                    }
                }
            }
        }
    }
    
    if (debugEnabled && enemiesHit > 0) {
        debugW("GRENADE LAUNCHER AoE: Hit " + enemiesHit + " additional enemies for +" + bonusDamage + " total bonus damage");
    }
    
    return bonusDamage;
}

// === OPTIMAL AOE TARGETING ===
function calculateOptimalAoETargeting(weapon, attackerCell) {
    // Only for AoE weapons
    if (!isAoEWeapon(weapon)) return null;
    
    var bestTargetCell = null;
    var bestTotalDamage = 0;
    var weaponMinRange = getWeaponMinRange(weapon);
    var weaponMaxRange = getWeaponMaxRange(weapon);
    
    if (debugEnabled) {
        debugW("=== OPTIMAL AOE TARGET SEARCH ===");
        debugW("Weapon: " + weapon + " (range " + weaponMinRange + "-" + weaponMaxRange + ")");
    }
    
    // Check all possible target cells within weapon range
    for (var range = weaponMinRange; range <= weaponMaxRange; range++) {
        var targetCells = getCellsAtDistance(attackerCell, range);
        
        for (var i = 0; i < count(targetCells); i++) {
            var targetCell = targetCells[i];
            
            // Skip if no LOS for direct weapons
            if (!hasLOS(attackerCell, targetCell)) continue;
            
            // Calculate total damage (direct + AoE)
            var directDamage = calculateWeaponDamageFromCell(weapon, attackerCell, targetCell);
            var aoeDamage = calculateAoEDamage(weapon, attackerCell, targetCell);
            var totalDamage = directDamage + aoeDamage;
            
            if (totalDamage > bestTotalDamage) {
                bestTotalDamage = totalDamage;
                bestTargetCell = targetCell;
                
                if (debugEnabled) {
                    debugW("AOE TARGET: Cell " + targetCell + " = " + directDamage + " direct + " + aoeDamage + " AoE = " + totalDamage + " total");
                }
            }
        }
    }
    
    if (bestTargetCell != null && debugEnabled) {
        debugW("OPTIMAL AOE TARGET: Cell " + bestTargetCell + " with " + bestTotalDamage + " total damage");
        markText(bestTargetCell, "AOE!", getColor(255, 0, 255), 10);
    }
    
    return bestTargetCell;
}

function isAoEWeapon(weapon) {
    return (weapon == WEAPON_ENHANCED_LIGHTNINGER || 
            weapon == WEAPON_GRENADE_LAUNCHER);
}