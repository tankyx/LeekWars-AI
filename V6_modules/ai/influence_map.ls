// V6 Module: ai/influence_map.ls
// Influence mapping
// Auto-generated from V5.0 script

// Function: buildInfluenceMap
function buildInfluenceMap() {
    if (INFLUENCE_TURN == turn) {
        debugLog("Influence map already built for turn " + turn);
        return;  // Already built this turn
    }
    
    debugLog("Building influence map for turn " + turn);
    INFLUENCE_MAP = [:];
    INFLUENCE_TURN = turn;
    
    // Get all cells in reasonable range - increased to 10 for better coverage
    var influenceRange = 10;  // Increased from 5 since we have ops to spare
    var mapCells = getCellsInRange(myCell, influenceRange);
    debugLog("Found " + count(mapCells) + " cells to analyze in range " + influenceRange);
    
    // Increased limit since we're only using 1-19% operations
    var maxCells = 40;  // Process up to 40 cells (increased from 20)
    var cellsToProcess = min(count(mapCells), maxCells);
    debugLog("Processing " + cellsToProcess + " cells (limited)");
    
    for (var i = 0; i < cellsToProcess; i++) {
        var cell = mapCells[i];
        if (i % 10 == 0) {
            debugLog("Processing cell " + i + "/" + cellsToProcess);
        }
        
        var cellInfluence = [:];
        cellInfluence["myDamage"] = 0;      // Damage I can deal from here
        cellInfluence["enemyDamage"] = 0;   // Damage enemy can deal to here
        cellInfluence["myAoE"] = [];        // My AoE coverage from here
        cellInfluence["enemyAoE"] = [];     // Enemy AoE threat to here
        cellInfluence["safety"] = 0;        // Overall safety score
        cellInfluence["control"] = 0;       // Territory control value
        
        // Calculate my damage potential from this cell
        debugLog("  Calculating damage from cell " + i);
        cellInfluence["myDamage"] = calculateDamageFrom(cell);
        
        // Calculate enemy threat to this cell  
        debugLog("  Calculating EID for cell " + i);
        cellInfluence["enemyDamage"] = calculateEID(cell);
        debugLog("  EID complete for cell " + i);
        
        // Calculate AoE zones - RE-ENABLED with limited scope
        // Only calculate AoE for first 20 cells to balance performance
        if (i < 20) {
            debugLog("  Calculating AoE zones for cell " + i);
            cellInfluence["myAoE"] = calculateMyAoEZones(cell);
            cellInfluence["enemyAoE"] = calculateEnemyAoEZones(cell);
        } else {
            cellInfluence["myAoE"] = [];
            cellInfluence["enemyAoE"] = [];
        }
        
        // Calculate safety score
        var myEHP = calculateEHP(myHP, myAbsShield, myRelShield, 0, myResistance);
        cellInfluence["safety"] = myEHP > 0 ? 1 - (cellInfluence["enemyDamage"] / myEHP) : 0;
        
        // Calculate control value (damage dealt vs taken)
        cellInfluence["control"] = cellInfluence["myDamage"] - cellInfluence["enemyDamage"];
        
        INFLUENCE_MAP[cell] = cellInfluence;
    }
}


// Function: calculateMyAoEZones
function calculateMyAoEZones(fromCell) {
    var zones = [];
    
    // Check Grenade Launcher zones - OPTIMIZED
    if (inArray(getWeapons(), WEAPON_GRENADE_LAUNCHER)) {
        // Only check enemy position and nearby cells instead of all cells in range
        var grenadeTargets = [enemyCell];  // Just check if we can hit enemy
        var nearbyEnemy = getCellsAtDistance(enemyCell, 1);  // And cells next to enemy
        for (var i = 0; i < min(4, count(nearbyEnemy)); i++) {
            push(grenadeTargets, nearbyEnemy[i]);
        }
        
        for (var i = 0; i < count(grenadeTargets); i++) {
            var target = grenadeTargets[i];
            var dist = getCellDistance(fromCell, target);
            if (dist > 7 || dist < 4) continue;  // Check range first
            if (!hasLOS(fromCell, target)) continue;
            
            var zone = [:];
            zone["weapon"] = "Grenade";
            zone["center"] = target;
            zone["cells"] = [];
            
            // Calculate all affected cells with damage percentages
            for (var dx = -2; dx <= 2; dx++) {
                for (var dy = -2; dy <= 2; dy++) {
                    var tx = getCellX(target) + dx;
                    var ty = getCellY(target) + dy;
                    var targetCell = getCellFromXY(tx, ty);
                    if (targetCell == null || targetCell == -1) continue;
                    
                    var distToTarget = getCellDistance(target, targetCell);
                    if (distToTarget <= 2) {
                        var damagePercent = max(0, 1 - 0.2 * distToTarget);
                        var cellDamage = [:];
                        cellDamage["cell"] = targetCell;
                        cellDamage["damage"] = damagePercent * 59 * (1 + myStrength/100);
                        push(zone["cells"], cellDamage);
                    }
                }
            }
            
            push(zones, zone);
        }
    }
    
    // Check Lightninger zones - OPTIMIZED
    if (inArray(getWeapons(), WEAPON_LIGHTNINGER)) {
        // Only check enemy position instead of all cells in range
        var lightTargets = [enemyCell];
        
        for (var i = 0; i < count(lightTargets); i++) {
            var target = lightTargets[i];
            var dist = getCellDistance(fromCell, target);
            if (dist > 10 || dist < 6) continue;  // Check range first
            if (!hasLOS(fromCell, target)) continue;
            
            var zone = [:];
            zone["weapon"] = "Lightninger";
            zone["center"] = target;
            zone["cells"] = [];
            
            // Diagonal cross pattern
            var offsets = [[0,0,1], [1,1,0.8], [-1,-1,0.8], [1,-1,0.8], [-1,1,0.8]];
            
            for (var j = 0; j < count(offsets); j++) {
                var offset = offsets[j];
                var tx = getCellX(target) + offset[0];
                var ty = getCellY(target) + offset[1];
                var targetCell = getCellFromXY(tx, ty);
                if (targetCell == null || targetCell == -1) continue;
                
                var cellDamage = [:];
                cellDamage["cell"] = targetCell;
                cellDamage["damage"] = offset[2] * 103 * (1 + myStrength/100);
                push(zone["cells"], cellDamage);
            }
            
            push(zones, zone);
        }
    }
    
    return zones;
}


// Function: calculateEnemyAoEZones
function calculateEnemyAoEZones(toCell) {
    var zones = [];
    
    // Check if enemy has AoE weapons
    if (ENEMY_MAX_AOE_SIZE > 1) {
        // Estimate enemy AoE threat zones
        var enemyWeapons = getWeapons(enemy);
        if (enemyWeapons != null) {
            for (var i = 0; i < count(enemyWeapons); i++) {
                var weapon = enemyWeapons[i];
                var area = getWeaponArea(weapon);
                
                if (area > 1) {
                    // Check if this cell could be hit by AoE
                    var maxRange = getWeaponMaxRange(weapon);
                    var minRange = getWeaponMinRange(weapon);
                    var enemyDist = getCellDistance(enemyCell, toCell);
                    
                    if (enemyDist >= minRange && enemyDist <= maxRange && hasLOS(enemyCell, toCell)) {
                        var zone = [:];
                        zone["weapon"] = weapon;
                        zone["center"] = toCell;
                        // Calculate max damage from weapon effects
                        var weaponEffects = getWeaponEffects(weapon);
                        var maxDamage = 0;
                        if (weaponEffects != null) {
                            for (var j = 0; j < count(weaponEffects); j++) {
                                var effect = weaponEffects[j];
                                if (effect[0] == EFFECT_DAMAGE) {  // Damage effect
                                    maxDamage = max(maxDamage, effect[2]);  // Max value
                                }
                            }
                        }
                        zone["threat"] = maxDamage * (1 + getStrength(enemy)/100);
                        push(zones, zone);
                    }
                }
            }
        }
    }
    
    return zones;
}


// Function: visualizeInfluenceMap
function visualizeInfluenceMap() {
    if (!debugEnabled || !canSpendOps(100000)) return;
    
    buildInfluenceMap();
    
    // Find max values for normalization
    var maxDamage = 0;
    var maxSafety = 0;
    
    for (var cell in INFLUENCE_MAP) {
        var inf = INFLUENCE_MAP[cell];
        maxDamage = max(maxDamage, inf["myDamage"]);
        maxSafety = max(maxSafety, inf["safety"]);
    }
    
    // Visualize based on selected mode
    var displayMode = "SAFETY";  // Can be DAMAGE, SAFETY, CONTROL, AOE
    
    for (var cell in INFLUENCE_MAP) {
        var inf = INFLUENCE_MAP[cell];
        var color;
        var text = "";
        
        if (displayMode == "DAMAGE") {
            // Red gradient for damage potential
            var damageRatio = maxDamage > 0 ? inf["myDamage"] / maxDamage : 0;
            var r = floor(255 * damageRatio);
            var g = floor(50 * (1 - damageRatio));
            var b = floor(50 * (1 - damageRatio));
            color = (r << 16) | (g << 8) | b;
            text = floor(inf["myDamage"]);
        } else if (displayMode == "SAFETY") {
            // Green to red for safety
            var safetyRatio = inf["safety"];
            if (safetyRatio >= 0.7) {
                color = 0x00FF00;  // Green - safe
            } else if (safetyRatio >= 0.5) {
                color = 0xFFFF00;  // Yellow - caution
            } else if (safetyRatio >= 0.3) {
                color = 0xFF8800;  // Orange - danger
            } else {
                color = 0xFF0000;  // Red - lethal
            }
            text = round(safetyRatio * 100) + "%";
        } else if (displayMode == "CONTROL") {
            // Blue for our control, purple for contested, red for enemy
            if (inf["control"] > 200) {
                color = 0x0066FF;  // Blue - our control
            } else if (inf["control"] > -200) {
                color = 0x9966FF;  // Purple - contested
            } else {
                color = 0xFF0066;  // Red - enemy control
            }
            text = floor(inf["control"]);
        }
        
        mark(cell, color);
        if (text != "") {
            markText(cell, text, COLOR_WHITE);
        }
    }
}

// === WEAPON EFFECTIVENESS MATRIX ===
