// V6 Module: combat/b_laser_tactics.ls
// B-Laser weapon tactics using generic laser implementation
// Note: This module is always included but functions only execute when B-Laser is equipped

// Include generic laser tactics
include("laser_tactics_generic");

// Function: findBestBLaserTarget
// Wrapper for generic laser function with B-Laser specifics
function findBestBLaserTarget() {
    var enemiesArray = getAliveEnemies();
    var result = findBestLaserTargetGeneric(WEAPON_B_LASER, getCell(), B_LASER_MIN_RANGE, B_LASER_MAX_RANGE, enemiesArray);
    
    // Add healing value to the result if we need it
    if (result != null) {
        myHP = getLife();
        myMaxHP = getTotalLife();
        var needHealing = myHP < myMaxHP * B_LASER_HEAL_THRESHOLD;
        
        if (needHealing) {
            // B-Laser heals for 50-60 base, scaled by wisdom
            var healAmount = 55 * (1 + getWisdom() / 100);
            result["healValue"] = healAmount;
            result["totalValue"] = result["totalDamage"] + healAmount * 0.5; // Healing worth half of damage
        } else {
            result["healValue"] = 0;
            result["totalValue"] = result["totalDamage"];
        }
    }
    
    return result;
}

// Function: evaluateBLaserPosition
// B-Laser specific position evaluation
function evaluateBLaserPosition(fromCell) {
    var enemiesArray = getAliveEnemies();
    var score = evaluateLaserPosition(WEAPON_B_LASER, B_LASER_MIN_RANGE, B_LASER_MAX_RANGE, fromCell, enemiesArray);
    
    // Add bonus for positions that allow healing when needed
    myHP = getLife();
    myMaxHP = getTotalLife();
    if (myHP < myMaxHP * B_LASER_HEAL_THRESHOLD) {
        score += 200; // Bonus for being able to heal while attacking
    }
    
    return score;
}

// Function: shouldRepositionForBLaser
// Check if we should move for better B-Laser shot
function shouldRepositionForBLaser() {
    var enemiesArray = getAliveEnemies();
    return shouldRepositionForLaser(WEAPON_B_LASER, B_LASER_MIN_RANGE, B_LASER_MAX_RANGE, getCell(), getMP(), enemiesArray);
}

// Function: countBLaserHits
// Count how many enemies would be hit by B-Laser
function countBLaserHits(fromCell, targetCell) {
    var enemiesArray = getAliveEnemies();
    var hitData = countLaserHitsGeneric(fromCell, targetCell, B_LASER_MIN_RANGE, B_LASER_MAX_RANGE, enemiesArray);
    return hitData["count"];
}

// Function: getBLaserDamage
// Calculate total damage for a B-Laser shot
function getBLaserDamage(fromCell, targetCell) {
    var enemiesArray = getAliveEnemies();
    return calculateLaserTotalDamage(WEAPON_B_LASER, fromCell, targetCell, B_LASER_MIN_RANGE, B_LASER_MAX_RANGE, enemiesArray, getEntity());
}

// Function: executeBLaserShot
// Execute B-Laser shot on best target
function executeBLaserShot() {
    if (!inArray(getWeapons(), WEAPON_B_LASER)) return false;
    if (getTP() < B_LASER_COST) return false;
    if (bLaserUsesRemaining <= 0) return false;
    
    var bestTarget = findBestBLaserTarget();
    if (bestTarget == null) return false;
    
    setWeapon(WEAPON_B_LASER);
    var result = useWeaponOnCell(bestTarget["targetCell"]);
    
    if (result == USE_SUCCESS) {
        bLaserUsesRemaining--;
        debugLog("B-Laser fired! Hits: " + bestTarget["hits"] + ", Damage: " + bestTarget["totalDamage"]);
        if (bestTarget["healValue"] > 0) {
            debugLog("B-Laser heal: " + bestTarget["healValue"]);
        }
        return true;
    }
    
    return false;
}

// Only log if we actually have B-Laser equipped
if (inArray(getWeapons(), WEAPON_B_LASER)) {
    debugLog("B-Laser tactics module loaded");
}