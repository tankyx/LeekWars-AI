// V6 Module: movement/range_finding.ls
// Range and cell finding
// Auto-generated from V5.0 script

// Function: getCellsInRange
function getCellsInRange(center, range) {
    // Full hit-cell detection as promised - no early-turn pruning!
    var allCells = [];
    
    // Use sampling only when very low on ops
    if (!canSpendOps(3000000)) {
        // Emergency mode - sample every 2nd cell
        var cx = getCellX(center);
        var cy = getCellY(center);
        var step = 2;
        
        for (var dx = -range; dx <= range; dx += step) {
            for (var dy = -range; dy <= range; dy += step) {
                var x = cx + dx;
                var y = cy + dy;
                var cell = getCellFromXY(x, y);
                
                if (cell != -1 && !isObstacle(cell)) {
                    var dist = getCellDistance(center, cell);
                    if (dist <= range) {
                        push(allCells, cell);
                    }
                }
            }
        }
        return allCells;
    }
    
    // Normal FULL thorough search
    
    // Get bounds to limit search
    var cx = getCellX(center);
    var cy = getCellY(center);
    
    for (var dx = -range; dx <= range; dx++) {
        for (var dy = -range; dy <= range; dy++) {
            var x = cx + dx;
            var y = cy + dy;
            var cell = getCellFromXY(x, y);
            
            if (cell != -1 && !isObstacle(cell)) {
                var dist = getCellDistance(center, cell);
                if (dist <= range) {
                    push(allCells, cell);
                }
            }
        }
    }
    
    return allCells;
}

// Find which hit cells we can actually reach this turn - O(N) version

// Function: getCellsAtDistance
function getCellsAtDistance(fromCell, distance) {
    var cells = [];
    var x = getCellX(fromCell);
    var y = getCellY(fromCell);
    
    // Get all cells at exact Manhattan distance
    for (var dx = -distance; dx <= distance; dx++) {
        var dy = distance - abs(dx);
        var c1 = getCellFromXY(x + dx, y + dy);
        var c2 = getCellFromXY(x + dx, y - dy);
        if (c1 != -1) push(cells, c1);
        if (c2 != -1 && dy != 0) push(cells, c2);  // Avoid duplicates when dy=0
    }
    
    return cells;
}

// === A* PATHFINDING IMPLEMENTATION ===

// Function: findHitCells
function findHitCells() {
    if (enemy == null) return [];
    
    // Remove early turn optimization - always do full hit cell detection
    // Hit cell detection - debug removed to reduce spam
    
    // Calculate actual weapon damage
    var weapons = getWeapons();
    var bestWeaponDamage = 0;
    
    for (var i = 0; i < count(weapons); i++) {
        var w = weapons[i];
        var effects = getWeaponEffects(w);
        for (var j = 0; j < count(effects); j++) {
            if (effects[j][0] == EFFECT_DAMAGE) {
                var avgDamage = (effects[j][1] + effects[j][2]) / 2;
                var scaledDamage = avgDamage * (1 + myStrength / 100.0);
                if (scaledDamage > bestWeaponDamage) {
                    bestWeaponDamage = scaledDamage;
                }
            }
        }
    }
    
    var allHitCells = [];
    
    // Calculate maximum weapon/chip range we have
    var maxRange = 0;
    // weapons already defined above
    for (var i = 0; i < count(weapons); i++) {
        var range = getWeaponMaxRange(weapons[i]);
        if (range > maxRange) maxRange = range;
    }
    var chips = getChips();
    for (var i = 0; i < count(chips); i++) {
        if (chipHasDamage(chips[i])) {
            var range = getChipMaxRange(chips[i]);
            if (range > maxRange) maxRange = range;
        }
    }
    
    // OPERATION MANAGEMENT: Limit search based on turn and available ops
    if (turn >= 5 && !canSpendOps(6000000)) {
        // Late game or low ops - reduce search
        maxRange = min(maxRange, 8);
    }
    
    // Get cells around enemy within our max weapon range
    var cellsAroundEnemy = getCellsInRange(enemyCell, maxRange);
    
    // MAXIMUM ANALYSIS with full operation budget
    var maxCellsToCheck = 800;  // Use maximum operations for ultimate analysis!
    if (turn >= 5) maxCellsToCheck = 600;  // Still analyze many cells late game
    if (!canSpendOps(5000000)) maxCellsToCheck = 400;  // Emergency limit very high
    
    // Don't filter too aggressively - we need all potential hit cells
    // Just cap the total to avoid operations explosion
    if (count(cellsAroundEnemy) > maxCellsToCheck) {
        // Only if we have too many cells, prioritize by distance
        var ranked = [];
        for (var i = 0; i < count(cellsAroundEnemy); i++) {
            var c = cellsAroundEnemy[i];
            var dEnemy = getCellDistance(c, enemyCell);
            var dMe = getCellDistance(c, myCell);
            push(ranked, [abs(dEnemy - optimalAttackRange) * 100 + dMe, c]);
        }
        sort(ranked);
        
        var capped = [];
        for (var i = 0; i < min(maxCellsToCheck, count(ranked)); i++) {
            push(capped, ranked[i][1]);
        }
        cellsAroundEnemy = capped;
    }
    
    // Check each cell to see if we can hit from there
    for (var i = 0; i < count(cellsAroundEnemy); i++) {
        var cell = cellsAroundEnemy[i];
        if (isObstacle(cell)) continue;
        
        var dist = getCellDistance(cell, enemyCell);
        var canHit = false;
        var damageAtRange = 0;
        var bestWeapon = null;
        var bestDamage = 0;
        
        // Check weapons
        for (var k = 0; k < count(weapons); k++) {
            var w = weapons[k];
            var area = getWeaponArea(w);
            
            // For AoE weapons, we can hit if enemy is within area of our target
            if (area > 1) {
                // Check if we can hit a cell near enemy that would splash to them
                if (dist <= getWeaponMaxRange(w) + area - 1 && dist >= max(0, getWeaponMinRange(w) - area + 1)) {
                    if (hasLOS(cell, enemyCell)) {
                        canHit = true;
                        var dmg = getWeaponDamage(w, getEntity());
                        // Reduce damage estimate for AoE splash
                        if (dist > getWeaponMaxRange(w)) {
                            dmg = dmg * 0.7; // Splash damage estimate
                        }
                        damageAtRange += dmg;
                        if (dmg > bestDamage) {
                            bestDamage = dmg;
                            bestWeapon = w;
                        }
                    }
                }
            } else {
                // Direct hit weapons
                if (dist >= getWeaponMinRange(w) && dist <= getWeaponMaxRange(w)) {
                    if (hasLOS(cell, enemyCell)) {
                        canHit = true;
                        var dmg = getWeaponDamage(w, getEntity());
                        damageAtRange += dmg;
                        if (dmg > bestDamage) {
                            bestDamage = dmg;
                            bestWeapon = w;
                        }
                    }
                }
            }
        }
        
        // Check chips
        for (var k = 0; k < count(chips); k++) {
            var ch = chips[k];
            if (!chipHasDamage(ch)) continue;
            
            var area = getChipArea(ch);
            
            // For AoE chips, we can hit if enemy is within area of our target
            if (area > 1) {
                // Check if we can hit a cell near enemy that would splash to them
                if (dist <= getChipMaxRange(ch) + area - 1 && dist >= max(0, getChipMinRange(ch) - area + 1)) {
                    if (!chipNeedLos(ch) || hasLOS(cell, enemyCell)) {
                        canHit = true;
                        var dmg = getChipDamage(ch, getEntity());
                        // Reduce damage estimate for AoE splash
                        if (dist > getChipMaxRange(ch)) {
                            dmg = dmg * 0.7; // Splash damage estimate
                        }
                        damageAtRange += dmg;
                        if (dmg > bestDamage) {
                            bestDamage = dmg;
                            bestWeapon = -ch; // Negative to indicate chip
                        }
                    }
                }
            } else {
                // Direct hit chips
                if (dist >= getChipMinRange(ch) && dist <= getChipMaxRange(ch)) {
                    if (!chipNeedLos(ch) || hasLOS(cell, enemyCell)) {
                        canHit = true;
                        var dmg = getChipDamage(ch, getEntity());
                        damageAtRange += dmg;
                        if (dmg > bestDamage) {
                            bestDamage = dmg;
                            bestWeapon = -ch; // Negative to indicate chip
                        }
                    }
                }
            }
        }
        
        // Add cells we can hit from (avoid melee unless high damage)
        if (canHit) {
            if (dist > 1 || damageAtRange > 300 || enemyHP < 200) {
                push(allHitCells, [cell, bestWeapon, damageAtRange]);
            }
        }
    }
    
    // Hit cells found - debug removed to reduce spam
    return allHitCells;
}

// Get cells within range of a center cell
