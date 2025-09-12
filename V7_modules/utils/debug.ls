// V7 Module: utils/debug.ls
// Debug utilities using proper LeekScript debug functions

function debug(message) {
    if (debugEnabled) {
        debugW("[DEBUG] " + message);
    }
}

function debugDamageZones(damageMap) {
    if (!debugEnabled) return;
    
    var count = 0;
    var maxDamage = 0;
    
    for (var cell in damageMap) {
        count++;
        var damage = damageMap[cell] + 0; // Convert to number
        if (damage > maxDamage) {
            maxDamage = damage;
        }
    }
    
    debugW("[DAMAGE] Found " + count + " damage zones, max: " + maxDamage);
}

function debugPath(pathResult) {
    if (!debugEnabled || pathResult == null) return;
    
    debugW("[PATH] Target: " + pathResult.targetCell + 
        ", Damage: " + pathResult.damage + 
        ", Distance: " + pathResult.distance +
        ", Reachable: " + pathResult.reachable);
}

function debugError(message) {
    debugE("[ERROR] " + message);
}