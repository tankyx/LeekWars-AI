// V6 Module: utils/helpers.ls
// Helper functions
// Auto-generated from V5.0 script

// Function: getAliveEnemies  
function getAliveEnemies() {
    // Returns array of all alive enemies
    var aliveEnemies = [];
    
    // Use LeekScript's getEnemies() function directly - no global dependencies
    var rawEnemies = getEnemies();
    
    if (rawEnemies != null && count(rawEnemies) > 0) {
        // Multi-enemy scenario - filter out dead enemies
        for (var i = 0; i < count(rawEnemies); i++) {
            var e = rawEnemies[i];
            if (e != null && getLife(e) > 0) {
                push(aliveEnemies, e);
            }
        }
    } else {
        // Fallback: try getNearestEnemy() for single enemy scenarios
        var nearestEnemy = getNearestEnemy();
        if (nearestEnemy != null && getLife(nearestEnemy) > 0) {
            push(aliveEnemies, nearestEnemy);
        }
    }
    
    return aliveEnemies;
}

// Function: inRange
function inRange(value, min, max) {
    return value >= min && value <= max;
}

// FIX: Reachable cells for me - blocks enemy cell
