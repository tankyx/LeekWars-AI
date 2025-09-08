// V6 Module: combat/m_laser_tactics.ls
// M-Laser weapon tactics using generic laser implementation

// Include generic laser tactics
include("laser_tactics_generic");

// M-Laser specific constants
global M_LASER_MIN_RANGE = 5;
global M_LASER_MAX_RANGE = 12;

// Function: findBestMLaserTarget
// Wrapper for generic laser function with M-Laser specifics
function findBestMLaserTarget() {
    var enemiesArray = getAliveEnemies();
    return findBestLaserTargetGeneric(WEAPON_M_LASER, getCell(), M_LASER_MIN_RANGE, M_LASER_MAX_RANGE, enemiesArray);
}

// Function: evaluateMLaserPosition
// M-Laser specific position evaluation
function evaluateMLaserPosition(fromCell) {
    var enemiesArray = getAliveEnemies();
    return evaluateLaserPosition(WEAPON_M_LASER, M_LASER_MIN_RANGE, M_LASER_MAX_RANGE, fromCell, enemiesArray);
}

// Function: shouldRepositionForMLaser
// Check if we should move for better M-Laser shot
function shouldRepositionForMLaser() {
    var enemiesArray = getAliveEnemies();
    return shouldRepositionForLaser(WEAPON_M_LASER, M_LASER_MIN_RANGE, M_LASER_MAX_RANGE, getCell(), getMP(), enemiesArray);
}

// Function: countMLaserHits
// Count how many enemies would be hit by M-Laser
function countMLaserHits(fromCell, targetCell) {
    var enemiesArray = getAliveEnemies();
    var hitData = countLaserHitsGeneric(fromCell, targetCell, M_LASER_MIN_RANGE, M_LASER_MAX_RANGE, enemiesArray);
    return hitData["count"];
}

// Function: getMLaserDamage
// Calculate total damage for an M-Laser shot
function getMLaserDamage(fromCell, targetCell) {
    var enemiesArray = getAliveEnemies();
    return calculateLaserTotalDamage(WEAPON_M_LASER, fromCell, targetCell, M_LASER_MIN_RANGE, M_LASER_MAX_RANGE, enemiesArray, getEntity());
}

debugLog("M-Laser tactics module loaded (using generic laser implementation)");