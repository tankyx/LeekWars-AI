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

// === MULTI-ENEMY TRACKING ===
global enemies = [];                // Array of all alive enemy entities
global enemyData = [:];             // Map[enemyId -> {cell, hp, maxHp, ttk, priority, threat}]
global primaryTarget = null;        // Current primary target (entity)
global damageZonesPerEnemy = [:];   // Map[enemyId -> damageArray]

// Legacy single-enemy variables (for backward compatibility)
global enemy = null;
global enemyCell = null;
global enemyHP = 0;
global enemyMaxHP = 0;
global enemyTP = 0;
global enemyMP = 0;

// === TACTICAL STATE ===
global damageZones = [:];           // Map[cell -> damage_potential] (legacy)
global currentDamageArray = [];     // NEW: Enhanced damage zones with enemy associations [cell, damage, weaponId, enemyEntity]
global currentTarget = null;        // Current enemy target (legacy)
global emergencyMode = false;       // Panic mode flag
global debugEnabled = false;        // Debug output control - DISABLED to avoid operation timeout

// === CONSTANTS ===
global EMERGENCY_HP_THRESHOLD = 0.25;  // Enter emergency mode below 25% HP
global PEEK_COVER_BONUS = 0.1;         // 10% damage bonus per adjacent cover
global MAX_PATHFIND_CELLS = 10;        // Limit A* search to top 10 damage cells

// === DANGEROUS ENEMY TARGETING CONSTANTS ===
global THREAT_WEIGHT = 3;              // Weight for enemy threat in priority calculation
global TTK_WEIGHT = 50;                // Weight for time-to-kill in priority calculation
global DISTANCE_WEIGHT = 10;           // Weight for distance in priority calculation
global REACHABILITY_BONUS = 1000;      // Priority bonus for reachable enemies
global BURST_KILL_BONUS = 500;         // Priority bonus for enemies we can kill this turn
global LOW_HP_DANGER_THRESHOLD = 0.5;  // HP threshold for dangerous low-HP enemies
global LOW_HP_DANGER_BONUS = 300;      // Threat bonus for dangerous low-HP enemies
global TEAM_FOCUS_HP_THRESHOLD = 0.4;  // HP threshold for team focus targeting
global TEAM_FOCUS_BONUS = 200;         // Priority bonus for low-HP team focus targets
global PRIMARY_TARGET_DAMAGE_BONUS = 0.5; // Damage zone bonus for attacking primary target

// === WEAPON CONSTANTS ===
global WEAPON_ENHANCED_LIGHTNINGER = 225;  // Enhanced Lightninger (range 5-12, cost 8, AoE)
global WEAPON_RIFLE = 151;                 // Rifle (range 7-9, cost 7)  
global WEAPON_M_LASER = 47;                // M-Laser (range 6-10, cost 9, line weapon)
global WEAPON_KATANA = 107;                // Katana (range 1, cost 7, melee)

// === CACHING ===
global pathCache = [:];             // Simple path caching
global losCache = [:];              // Line of sight cache
// Removed weapon tracking to avoid LeekScript variable conflicts
global weaponSwitchCache = [:];     // Cache weapon compatibility checks

// === CHIP COOLDOWN TRACKING ===
global chipCooldowns = [:];         // Map[chipId -> turnsRemaining]
global lastChipUse = [:];          // Map[chipId -> turnUsed]

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
    
    // Update all enemies data
    enemies = getAliveEnemies();
    enemyData = [:]; // Clear previous data
    
    if (count(enemies) > 0) {
        // Track all enemies
        for (var i = 0; i < count(enemies); i++) {
            var enemyEntity = enemies[i];
            enemyData[enemyEntity] = {
                entity: enemyEntity,
                cell: getCell(enemyEntity),
                hp: getLife(enemyEntity),
                maxHp: getTotalLife(enemyEntity),
                tp: getTP(enemyEntity),
                mp: getMP(enemyEntity),
                strength: getStrength(enemyEntity),
                agility: getAgility(enemyEntity),
                resistance: getResistance(enemyEntity),
                distance: getCellDistance(myCell, getCell(enemyEntity)),
                ttk: 0, // Will be calculated by targeting system
                priority: 0, // Will be calculated by targeting system
                threat: 0 // Will be calculated by targeting system
            };
        }
        
        // Maintain backward compatibility with single-enemy variables
        if (primaryTarget == null || getLife(primaryTarget) <= 0) {
            primaryTarget = enemies[0]; // Default to first enemy
        }
        
        // Update legacy single-enemy variables for backward compatibility
        enemy = primaryTarget;
        if (enemy != null && enemyData[enemy] != null) {
            enemyCell = enemyData[enemy].cell;
            enemyHP = enemyData[enemy].hp;
            enemyMaxHP = enemyData[enemy].maxHp;
            enemyTP = enemyData[enemy].tp;
            enemyMP = enemyData[enemy].mp;
        }
    } else {
        // No enemies found
        primaryTarget = null;
        enemy = null;
    }
    
    // Weapon tracking removed to avoid variable conflicts
    
    // Clear weapon switch cache at turn start to avoid stale data
    weaponSwitchCache = [:];
    
    // Update chip cooldowns
    if (chipCooldowns[CHIP_TOXIN] != null && chipCooldowns[CHIP_TOXIN] > 0) {
        chipCooldowns[CHIP_TOXIN]--;
    }
    if (chipCooldowns[CHIP_VENOM] != null && chipCooldowns[CHIP_VENOM] > 0) {
        chipCooldowns[CHIP_VENOM]--;
    }
    
    // Check emergency mode
    emergencyMode = (myHP / myMaxHP) < EMERGENCY_HP_THRESHOLD;
}

// === WEAPON UTILITY FUNCTIONS ===
// NOTE: Using LeekScript built-in APIs for dynamic weapon adaptation
// These functions now work with ANY weapon without hardcoded values

function getWeaponMaxUses(weapon) {
    if (weapon == WEAPON_ENHANCED_LIGHTNINGER) return 2;
    if (weapon == WEAPON_RIFLE) return 2;
    if (weapon == WEAPON_M_LASER) return 2;
    if (weapon == WEAPON_KATANA) return 1;
    if (weapon == WEAPON_SWORD) return 2;
    if (weapon == WEAPON_B_LASER) return 3;
    if (weapon == WEAPON_GRENADE_LAUNCHER) return 2;
    if (weapon == WEAPON_RHINO) return 3;
    if (weapon == WEAPON_NEUTRINO) return 3;
    if (weapon == WEAPON_DESTROYER) return 2;
    if (weapon == WEAPON_FLAME_THROWER) return 2;
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

function isDiagonallyAligned(fromCell, toCell) {
    var x1 = getCellX(fromCell);
    var y1 = getCellY(fromCell);
    var x2 = getCellX(toCell);
    var y2 = getCellY(toCell);
    
    var dx = abs(x2 - x1);
    var dy = abs(y2 - y1);
    
    // Must be on diagonal (equal x and y distance) and not same cell
    return dx == dy && dx != 0;
}

// === WEAPON VALIDATION FUNCTION ===
function canWeaponReachTarget(weapon, fromCell, targetCell) {
    // Check distance
    var distance = getCellDistance(fromCell, targetCell);
    var minRange = getWeaponMinRange(weapon);
    var maxRange = getWeaponMaxRange(weapon);
    
    if (debugEnabled) {
        debugW("WEAPON REACH DEBUG: Weapon " + weapon + ", distance=" + distance + ", range=" + minRange + "-" + maxRange);
    }
    
    if (distance < minRange || distance > maxRange) {
        if (debugEnabled) {
            debugW("WEAPON REACH FAIL: Distance " + distance + " not in range " + minRange + "-" + maxRange);
        }
        return false;
    }
    
    // Check line of sight
    if (!lineOfSight(fromCell, targetCell)) {
        if (debugEnabled) {
            debugW("WEAPON REACH FAIL: No line of sight from " + fromCell + " to " + targetCell);
        }
        return false;
    }
    
    // Check alignment for laser weapons
    if (weapon == WEAPON_M_LASER || weapon == WEAPON_B_LASER || weapon == WEAPON_LASER) {
        if (!isOnSameLine(fromCell, targetCell)) {
            return false;
        }
    }
    
    return true;
}

