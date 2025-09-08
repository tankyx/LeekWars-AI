// V6 Module: combat/grenade_tactics.ls
// Grenade targeting
// Auto-generated from V5.0 script

// Function: findBestGrenadeTarget
function findBestGrenadeTarget(fromCell) {
    if (!inArray(getWeapons(), WEAPON_GRENADE_LAUNCHER)) return null;
    
    var minRange = 4;
    var maxRange = 7;
    var bestResult = null;
    var bestDamage = 0;
    
    // Get all potential target cells in Grenade range
    var targetCells = getCellsInRange(fromCell, maxRange);
    
    for (var i = 0; i < min(50, count(targetCells)); i++) {
        var targetCell = targetCells[i];
        var dist = getCellDistance(fromCell, targetCell);
        
        // Check range and LOS
        if (dist < minRange || dist > maxRange) continue;
        if (!hasLOS(fromCell, targetCell)) continue;
        
        // Calculate AoE damage at this target position
        var totalDamage = 0;
        var enemiesHit = 0;
        
        // Check all cells in AoE radius (2 cells from impact)
        var aoeCells = getCellsInRange(targetCell, 2);
        
        // Multi-enemy support: check all enemies in AoE
        if (count(allEnemies) > 0) {
            for (var e = 0; e < count(allEnemies); e++) {
                var enemyData = allEnemies[e];
                var eCell = enemyData["cell"];
                var aoeDist = getCellDistance(targetCell, eCell);
                
                // Check if enemy is in AoE radius (2 cells)
                if (aoeDist <= 2) {
                    // Damage falloff: 100% at center, -20% per cell
                    var damagePercent = max(0, 1 - 0.2 * aoeDist);
                    var baseDamage = 70 * (1 + myStrength / 100.0);  // Grenade base damage
                    var damage = baseDamage * damagePercent;
                    totalDamage += damage;
                    enemiesHit++;
                }
            }
        } else {
            // Single enemy fallback
            for (var j = 0; j < count(aoeCells); j++) {
                var aoeCell = aoeCells[j];
                var aoeDist = getCellDistance(targetCell, aoeCell);
                
                // Check if enemy is in this cell
                if (aoeCell == enemyCell) {
                    // Damage falloff: 100% at center, -20% per cell
                    var damagePercent = max(0, 1 - 0.2 * aoeDist);
                    var baseDamage = 70 * (1 + myStrength / 100.0);  // Grenade base damage
                    var damage = baseDamage * damagePercent;
                    totalDamage += damage;
                    enemiesHit++;
                }
            }
        }
        
        // Prefer positions that hit the enemy
        if (enemiesHit > 0 && totalDamage > bestDamage) {
            bestDamage = totalDamage;
            bestResult = [:];;
            bestResult["targetCell"] = targetCell;
            bestResult["damage"] = totalDamage;
            bestResult["directHit"] = (targetCell == enemyCell);
            bestResult["range"] = dist;
        }
    }
    
    if (bestResult != null && debugEnabled) {
        debugLog("👣 Grenade target: cell " + bestResult["targetCell"] + 
                 " dmg=" + round(bestResult["damage"]) +
                 " direct=" + bestResult["directHit"] +
                 " range=" + bestResult["range"]);
    }
    
    return bestResult;
}

// === EHP CALCULATION ===
