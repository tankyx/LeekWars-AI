// V7 Module: core/globals.ls
// Minimal global state - streamlined for maximum performance

// === GAME STATE ===
global myLeek;
global myCell;
global myHP;
global myMaxHP;
global myTP;
global myMP;
global myStrength;
global myAgility;
global myScience;
global myMagic;
global myResistance;
global myWisdom;

global enemy;
global enemyCell;
global enemyHP;
global enemyMaxHP;
global enemyTP;
global enemyMP;

// === TACTICAL STATE ===
global damageZones = [:];           // Map[cell -> damage_potential]
global currentTarget = null;        // Current enemy target
global emergencyMode = false;       // Panic mode flag
global debugEnabled = true;         // Debug output control

// === CONSTANTS ===
global EMERGENCY_HP_THRESHOLD = 0.25;  // Enter emergency mode below 25% HP
global PEEK_COVER_BONUS = 0.1;         // 10% damage bonus per adjacent cover
global MAX_PATHFIND_CELLS = 10;        // Limit A* search to top 10 damage cells

// === WEAPON CONSTANTS ===
global WEAPON_ENHANCED_LIGHTNINGER = 225;  // Enhanced Lightninger (range 5-12, cost 8, AoE)
global WEAPON_RIFLE = 151;                 // Rifle (range 7-9, cost 7)  
global WEAPON_M_LASER = 47;                // M-Laser (range 6-10, cost 9, line weapon)
global WEAPON_KATANA = 107;                // Katana (range 1, cost 7, melee)

// === CACHING ===
global pathCache = [:];             // Simple path caching
global losCache = [:];              // Line of sight cache

// === INITIALIZATION ===
function updateGameState() {
    myLeek = getEntity();
    myCell = getCell();
    myHP = getLife();
    myMaxHP = getTotalLife();
    myTP = getTP();
    myMP = getMP();
    myStrength = getStrength();
    myAgility = getAgility();
    myScience = getScience();
    myMagic = getMagic();
    myResistance = getResistance();
    myWisdom = getWisdom();
    
    // Find closest enemy
    var enemies = getAliveEnemies();
    if (count(enemies) > 0) {
        enemy = enemies[0];
        enemyCell = getCell(enemy);
        enemyHP = getLife(enemy);
        enemyMaxHP = getTotalLife(enemy);
        enemyTP = getTP(enemy);
        enemyMP = getMP(enemy);
    }
    
    // Check emergency mode
    emergencyMode = (myHP / myMaxHP) < EMERGENCY_HP_THRESHOLD;
}

// === WEAPON UTILITY FUNCTIONS ===
function getWeaponMinRange(weapon) {
    if (weapon == WEAPON_ENHANCED_LIGHTNINGER) return 5;
    if (weapon == WEAPON_RIFLE) return 7;
    if (weapon == WEAPON_M_LASER) return 6;
    if (weapon == WEAPON_KATANA) return 1;
    if (weapon == WEAPON_B_LASER) return 2;
    if (weapon == WEAPON_GRENADE_LAUNCHER) return 4;
    if (weapon == WEAPON_RHINO) return 2;
    return 1; // Default for other weapons
}

function getWeaponMaxRange(weapon) {
    if (weapon == WEAPON_ENHANCED_LIGHTNINGER) return 12;
    if (weapon == WEAPON_RIFLE) return 9;
    if (weapon == WEAPON_M_LASER) return 10;
    if (weapon == WEAPON_KATANA) return 1;
    if (weapon == WEAPON_B_LASER) return 8;
    if (weapon == WEAPON_GRENADE_LAUNCHER) return 7;
    if (weapon == WEAPON_RHINO) return 4;
    return 10; // Default for other weapons
}

function getWeaponCost(weapon) {
    if (weapon == WEAPON_ENHANCED_LIGHTNINGER) return 9;
    if (weapon == WEAPON_RIFLE) return 7;
    if (weapon == WEAPON_M_LASER) return 9;
    if (weapon == WEAPON_KATANA) return 7;
    if (weapon == WEAPON_B_LASER) return 5;
    if (weapon == WEAPON_GRENADE_LAUNCHER) return 6;
    if (weapon == WEAPON_RHINO) return 5;
    return 5; // Default for other weapons
}

function getWeaponMaxUses(weapon) {
    if (weapon == WEAPON_ENHANCED_LIGHTNINGER) return 2;
    if (weapon == WEAPON_RIFLE) return 2;
    if (weapon == WEAPON_M_LASER) return 1;
    if (weapon == WEAPON_KATANA) return 1;
    if (weapon == WEAPON_B_LASER) return 3;
    if (weapon == WEAPON_GRENADE_LAUNCHER) return 2;
    if (weapon == WEAPON_RHINO) return 3;
    return 0; // 0 = unlimited uses
}

function getWeaponArea(weapon) {
    if (weapon == WEAPON_ENHANCED_LIGHTNINGER) return 1; // 3x3 square
    if (weapon == WEAPON_GRENADE_LAUNCHER) return 2; // Circle of radius 2
    return 0; // No area effect
}

function isOnSameLine(cell1, cell2) {
    var x1 = getCellX(cell1);
    var y1 = getCellY(cell1);
    var x2 = getCellX(cell2);
    var y2 = getCellY(cell2);
    
    // Check if on same X or Y axis (for line weapons)
    return (x1 == x2) || (y1 == y2);
}