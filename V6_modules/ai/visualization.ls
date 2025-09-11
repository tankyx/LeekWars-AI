// V6 Module: ai/visualization.ls
// Debug visualization
// Auto-generated from V5.0 script

// Function: visualizeHitCells
function visualizeHitCells(hitCells) {
    // Visualize hit cells with weapon-specific colors
    if (!debugEnabled || !canSpendOps(20000)) return;
    
    for (var i = 0; i < min(50, count(hitCells)); i++) {
        var hitData = hitCells[i];
        var cell = hitData[0];
        var bestWeapon = hitData[1];
        var damage = hitData[2];
        
        // Color based on weapon type
        var color;
        var weaponName = "";
        
        if (bestWeapon == null) {
            color = 0x808080;  // Gray - no weapon?
        } else if (bestWeapon < 0) {
            // It's a chip (negative value)
            color = 0xFF00FF;  // Magenta for chips
            weaponName = "C";
        } else {
            // Identify weapon by index in our loadout
            var weapons = getWeapons();
            if (count(weapons) > 0 && bestWeapon == weapons[0]) {
                color = 0xFF0000;  // Red - Katana (melee)
                weaponName = "KAT";
            } else if (count(weapons) > 1 && bestWeapon == weapons[1]) {
                color = 0x9966FF;  // Purple - Neutrino (debuff)
                weaponName = "NT";
            } else if (count(weapons) > 2 && bestWeapon == weapons[2]) {
                color = 0xFF8800;  // Orange - Machine Gun (multi-hit)
                weaponName = "MG";
            } else if (count(weapons) > 3 && bestWeapon == weapons[3]) {
                color = 0x00FF00;  // Green - Grenade Launcher
                weaponName = "GL";
            } else {
                // Default color for unknown weapons
                color = 0x0066FF;  // Medium blue
                weaponName = "W";
            }
        }
        
        mark(cell, color);  // Fixed: removed opacity arg
        
        // Show weapon abbreviation and damage for significant cells
        if (damage >= 100) {
            markText(cell, weaponName + ":" + floor(damage), COLOR_WHITE);
        }
    }
}

// Function: findSafeCells
function findSafeCells() {
    var safeCells = [];
    var myEHP = calculateEHP(myHP, myAbsShield, myRelShield, 0, myResistance);
    
    var reach = getReachableCells(myCell, myMP);
    
    // Coarse filter first to save ops
    var coarse = [];
    for (var i = 0; i < count(reach); i++) {
        if (!canSpendOps(5000)) break;
        
        var cell = reach[i];
        // Simple distance-based estimate
        var dist = getCellDistance(cell, enemyCell);
        var estimatedThreat = dist <= 5 ? 1.0 : (dist <= 10 ? 0.5 : 0.2);
        
        if (estimatedThreat < THREAT_SAFE_RATIO * 1.3) {
            push(coarse, cell);
        }
    }
    // Precise evaluation on subset
    var cap = min(60, count(coarse));
    for (var i = 0; i < cap; i++) {
        if (!canSpendOps(10000)) break;
        
        var cell = coarse[i];
        var eid = eidOf(cell);
        
        if (eid < myEHP * THREAT_SAFE_RATIO) {
            push(safeCells, cell);
        }
    }
    
    return safeCells;
}

// === VISUALIZATION ===
