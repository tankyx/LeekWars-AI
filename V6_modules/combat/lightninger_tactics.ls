// V6 Module: combat/lightninger_tactics.ls
// Lightninger weapon tactics
// Auto-generated from V5.0 script

// Function: evaluateLightningerPosition
function evaluateLightningerPosition(fromCell, targetCell) {
    if (targetCell == null || targetCell == -1) return null;
    
    var pattern = getLightningerPattern(targetCell);
    var totalDamage = 0;
    var enemiesHit = [];
    var cellsHit = [];
    
    // Base damage calculation (Lightninger: 140 base + 1.8x strength)
    var baseDamage = 140 + floor(myStrength * 1.8);
    
    // Check all pattern cells for enemies
    for (var i = 0; i < count(pattern); i++) {
        var patternData = pattern[i];
        var cell = patternData[0];
        var damageMultiplier = patternData[1];
        
        if (cell == null || cell == -1) continue;
        
        // In 1v1, just check if enemy is in this cell
        if (enemy != null && getCell(enemy) == cell) {
            var damage = baseDamage * damageMultiplier;
            totalDamage += damage;
            push(enemiesHit, enemy);
            push(cellsHit, cell);
        }
        
        // For team battles (future support)
        enemies = getAliveEnemies();
        if (count(enemies) > 1) {
            for (var j = 0; j < count(enemies); j++) {
                var e = enemies[j];
                if (e != enemy && getCell(e) == cell) {
                    var damage = baseDamage * damageMultiplier;
                    totalDamage += damage;
                    push(enemiesHit, e);
                    push(cellsHit, cell);
                }
            }
        }
    }
    
    // Calculate efficiency
    var result = [:];
    result["damage"] = totalDamage;
    result["enemies"] = enemiesHit;
    result["cellsHit"] = cellsHit;
    result["efficiency"] = totalDamage / 5;  // 5 TP cost for Lightninger
    result["targetCell"] = targetCell;
    result["numHits"] = count(enemiesHit);
    
    return result;
}


// Function: getLightningerPattern
function getLightningerPattern(targetCell) {
    if (targetCell == null || targetCell == -1) return [];
    
    var cx = getCellX(targetCell);
    var cy = getCellY(targetCell);
    
    // Lightninger X pattern: center + 4 diagonals
    // Damage: Center 100%, Diagonals 80%
    var pattern = [];
    
    // Center - 100% damage
    push(pattern, [targetCell, 1.0]);
    
    // Diagonals - 80% damage each
    var diagonals = [
        [1, 1],   // Northeast
        [-1, -1], // Southwest  
        [1, -1],  // Southeast
        [-1, 1]   // Northwest
    ];
    
    for (var i = 0; i < count(diagonals); i++) {
        var dx = diagonals[i][0];
        var dy = diagonals[i][1];
        var diagonalCell = getCellFromXY(cx + dx, cy + dy);
        if (diagonalCell != null && diagonalCell != -1) {
            push(pattern, [diagonalCell, 0.8]);
        }
    }
    
    return pattern;
}


// Function: findBestLightningerTarget
function findBestLightningerTarget(fromCell) {
    if (!inArray(getWeapons(), WEAPON_LIGHTNINGER)) return null;
    
    var minRange = 6;
    var maxRange = 10;
    var bestResult = null;
    var bestDamage = 0;
    
    // Get all potential target cells in Lightninger range
    var targetCells = getCellsInRange(fromCell, maxRange);
    
    for (var i = 0; i < count(targetCells); i++) {
        var targetCell = targetCells[i];
        var dist = getCellDistance(fromCell, targetCell);
        
        // Check range and LOS
        if (dist < minRange || dist > maxRange) continue;
        if (!hasLOS(fromCell, targetCell)) continue;
        
        // Evaluate this target position
        var result = evaluateLightningerPosition(fromCell, targetCell);
        if (result == null) continue;
        
        // Prefer positions that hit the enemy, even if not centered
        if (result["numHits"] > 0 && result["damage"] > bestDamage) {
            bestDamage = result["damage"];
            bestResult = result;
        }
    }
    
    return bestResult;
}

// Get all cells affected by AoE from center point
