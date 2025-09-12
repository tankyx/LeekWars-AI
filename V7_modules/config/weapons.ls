// V7 Module: config/weapons.ls
// Pre-defined weapon and chip scenarios by TP amount

// === RIFLE SCENARIOS (Cost: 7 TP, Max 2 uses/turn, Range 7-9, Damage 76) ===
global RIFLE_SCENARIOS = [
    14: [WEAPON_RIFLE, WEAPON_RIFLE],  // 2 uses = 14 TP
    7: [WEAPON_RIFLE],                 // 1 use = 7 TP
    5: [CHIP_METEORITE],
    4: [CHIP_LIGHTNING],
    3: [CHIP_SPARK]
];

// === M-LASER SCENARIOS (Cost: 9 TP, Max 1 use/turn, Range 6-10, Damage 91) ===
global MLASER_SCENARIOS = [
    18: [WEAPON_M_LASER, CHIP_LIGHTNING], // 1 use + chip = 18 TP
    9: [WEAPON_M_LASER],                  // 1 use = 9 TP
    5: [CHIP_METEORITE],
    4: [CHIP_LIGHTNING],
    3: [CHIP_SPARK]
];

// === FLAME THROWER SCENARIOS ===
global FLAME_SCENARIOS = [
    18: [WEAPON_FLAME_THROWER, WEAPON_FLAME_THROWER, WEAPON_FLAME_THROWER],
    12: [WEAPON_FLAME_THROWER, WEAPON_FLAME_THROWER],
    8: [WEAPON_FLAME_THROWER, CHIP_BURNING],
    6: [WEAPON_FLAME_THROWER],
    5: [CHIP_BURNING],
    4: [CHIP_BURNING]
];

// === GRENADE LAUNCHER SCENARIOS ===
global GRENADE_SCENARIOS = [
    14: [WEAPON_GRENADE_LAUNCHER, WEAPON_GRENADE_LAUNCHER],
    10: [WEAPON_GRENADE_LAUNCHER, CHIP_METEORITE],
    7: [WEAPON_GRENADE_LAUNCHER],
    5: [CHIP_METEORITE],
    4: [CHIP_ROCKFALL]
];

// === B-LASER SCENARIOS (Cost: 5 TP, Max 3 uses/turn, Range 2-8, Line weapon) ===
global BLASER_SCENARIOS = [
    15: [WEAPON_B_LASER, WEAPON_B_LASER, WEAPON_B_LASER], // 3 uses = 15 TP
    10: [WEAPON_B_LASER, WEAPON_B_LASER],                 // 2 uses = 10 TP
    8: [WEAPON_B_LASER, CHIP_LIGHTNING],                  // 1 use + chip = 8 TP
    5: [WEAPON_B_LASER],                                  // 1 use = 5 TP
    4: [CHIP_LIGHTNING],
    3: [CHIP_SPARK]
];

// === RHINO SCENARIOS (Cost: 5 TP, Max 3 uses/turn, Range 2-4, Single target) ===
global RHINO_SCENARIOS = [
    15: [WEAPON_RHINO, WEAPON_RHINO, WEAPON_RHINO], // 3 uses = 15 TP (optimal)
    10: [WEAPON_RHINO, WEAPON_RHINO],               // 2 uses = 10 TP
    8: [WEAPON_RHINO, CHIP_LIGHTNING],              // 1 use + chip = 8 TP
    5: [WEAPON_RHINO],                              // 1 use = 5 TP
    4: [CHIP_LIGHTNING],
    3: [CHIP_SPARK]
];

// === GRENADE LAUNCHER SCENARIOS (Cost: 6 TP, Max 2 uses/turn, Range 4-7, Circle AoE) ===
global GRENADE_LAUNCHER_SCENARIOS = [
    12: [WEAPON_GRENADE_LAUNCHER, WEAPON_GRENADE_LAUNCHER], // 2 uses = 12 TP
    10: [WEAPON_GRENADE_LAUNCHER, CHIP_LIGHTNING],          // 1 use + chip = 10 TP
    6: [WEAPON_GRENADE_LAUNCHER],                           // 1 use = 6 TP
    5: [CHIP_METEORITE],
    4: [CHIP_LIGHTNING]
];

// === ENHANCED LIGHTNINGER SCENARIOS (Cost: 8 TP, Max 2 uses/turn, Range 5-12, Damage 95) ===
global LIGHTNINGER_SCENARIOS = [
    16: [WEAPON_ENHANCED_LIGHTNINGER, WEAPON_ENHANCED_LIGHTNINGER], // 2 uses = 16 TP
    8: [WEAPON_ENHANCED_LIGHTNINGER],                               // 1 use = 8 TP  
    5: [CHIP_METEORITE],
    4: [CHIP_LIGHTNING],
    3: [CHIP_SPARK]
];

// === KATANA SCENARIOS (Cost: 7 TP, Max 1 use/turn, Range 1, Damage 77) ===
global KATANA_SCENARIOS = [
    14: [WEAPON_KATANA, CHIP_LIGHTNING], // 1 use + chip = 14 TP
    7: [WEAPON_KATANA],                  // 1 use = 7 TP
    4: [CHIP_LIGHTNING],
    3: [CHIP_SPARK]
];

// === FALLBACK CHIP-ONLY SCENARIOS ===
global CHIP_SCENARIOS = [
    8: [CHIP_METEORITE, CHIP_LIGHTNING],
    7: [CHIP_ICEBERG, CHIP_LIGHTNING],
    6: [CHIP_BURNING, CHIP_SPARK],
    5: [CHIP_METEORITE],
    4: [CHIP_LIGHTNING],
    3: [CHIP_LIGHTNING]
];

// === SCENARIO SELECTION FUNCTION ===
function getScenarioForLoadout(weapons, tp) {
    var distance = getCellDistance(myCell, enemyCell);
    
    // Weapon priority order (most effective first by range)
    
    // Katana - highest priority if in melee range
    if (inArray(weapons, WEAPON_KATANA) && distance <= 1) {
        return KATANA_SCENARIOS[tp] != null ? KATANA_SCENARIOS[tp] : KATANA_SCENARIOS[7];
    }
    
    // Rhino - high priority at 2-4 range (3x attacks for maximum DPS)
    if (inArray(weapons, WEAPON_RHINO) && distance >= 2 && distance <= 4 && lineOfSight(myCell, enemyCell)) {
        return RHINO_SCENARIOS[tp] != null ? RHINO_SCENARIOS[tp] : RHINO_SCENARIOS[5];
    }
    
    // Enhanced Lightninger - area damage at medium range
    // Only prioritize if we have clear LOS
    if (inArray(weapons, WEAPON_ENHANCED_LIGHTNINGER) && distance >= 5 && distance <= 12 && lineOfSight(myCell, enemyCell)) {
        return LIGHTNINGER_SCENARIOS[tp] != null ? LIGHTNINGER_SCENARIOS[tp] : LIGHTNINGER_SCENARIOS[8];
    }
    
    // Rifle - reliable mid-range damage
    if (inArray(weapons, WEAPON_RIFLE) && distance >= 7 && distance <= 9 && lineOfSight(myCell, enemyCell)) {
        return RIFLE_SCENARIOS[tp] != null ? RIFLE_SCENARIOS[tp] : RIFLE_SCENARIOS[7];
    }
    
    // Grenade Launcher - AoE damage at mid range
    if (inArray(weapons, WEAPON_GRENADE_LAUNCHER) && distance >= 4 && distance <= 7 && lineOfSight(myCell, enemyCell)) {
        return GRENADE_LAUNCHER_SCENARIOS[tp] != null ? GRENADE_LAUNCHER_SCENARIOS[tp] : GRENADE_LAUNCHER_SCENARIOS[6];
    }
    
    // M-Laser - pierce multiple enemies at long range
    // Prioritize M-Laser when aligned - it's very strong!
    if (inArray(weapons, WEAPON_M_LASER) && distance >= 6 && distance <= 10) {
        // M-Laser needs X or Y axis alignment
        var myX = getCellX(myCell);
        var myY = getCellY(myCell);
        var enemyX = getCellX(enemyCell);
        var enemyY = getCellY(enemyCell);
        
        var xAligned = (myX == enemyX);
        var yAligned = (myY == enemyY);
        
        // Prioritize M-Laser when properly aligned - high damage weapon!
        if (xAligned != yAligned) {
            return MLASER_SCENARIOS[tp] != null ? MLASER_SCENARIOS[tp] : MLASER_SCENARIOS[9];
        }
        // Note: If not aligned, continue to check other weapons
    }
    
    // B-Laser - cheaper line weapon alternative (5 TP vs M-Laser's 9 TP)
    if (inArray(weapons, WEAPON_B_LASER) && distance >= 2 && distance <= 8) {
        // B-Laser needs X or Y axis alignment (like M-Laser)
        var myX = getCellX(myCell);
        var myY = getCellY(myCell);
        var enemyX = getCellX(enemyCell);
        var enemyY = getCellY(enemyCell);
        
        var xAligned = (myX == enemyX);
        var yAligned = (myY == enemyY);
        
        // Prioritize B-Laser when properly aligned - efficient weapon!
        if (xAligned != yAligned) {
            return BLASER_SCENARIOS[tp] != null ? BLASER_SCENARIOS[tp] : BLASER_SCENARIOS[5];
        }
        // Note: If not aligned, continue to check other weapons
    }
    
    // Fallback weapons - try the most likely to succeed for current distance
    
    // Check which weapons could work at this distance (ignoring alignment/LOS for now)
    var canUseRifle = inArray(weapons, WEAPON_RIFLE) && distance >= 7 && distance <= 9;
    var canUseMlaser = inArray(weapons, WEAPON_M_LASER) && distance >= 6 && distance <= 10;  
    var canUseLightninger = inArray(weapons, WEAPON_ENHANCED_LIGHTNINGER) && distance >= 5 && distance <= 12;
    var canUseKatana = inArray(weapons, WEAPON_KATANA) && distance <= 1;
    var canUseRhino = inArray(weapons, WEAPON_RHINO) && distance >= 2 && distance <= 4;
    var canUseBlaser = inArray(weapons, WEAPON_B_LASER) && distance >= 2 && distance <= 8;
    var canUseGrenadeLauncher = inArray(weapons, WEAPON_GRENADE_LAUNCHER) && distance >= 4 && distance <= 7;
    
    // Prioritize weapons that are definitely in range
    if (canUseRhino) {
        return RHINO_SCENARIOS[tp] != null ? RHINO_SCENARIOS[tp] : RHINO_SCENARIOS[5];
    }
    
    if (canUseRifle) {
        return RIFLE_SCENARIOS[tp] != null ? RIFLE_SCENARIOS[tp] : RIFLE_SCENARIOS[7];
    }
    
    if (canUseGrenadeLauncher) {
        return GRENADE_LAUNCHER_SCENARIOS[tp] != null ? GRENADE_LAUNCHER_SCENARIOS[tp] : GRENADE_LAUNCHER_SCENARIOS[6];
    }
    
    if (canUseBlaser) {
        return BLASER_SCENARIOS[tp] != null ? BLASER_SCENARIOS[tp] : BLASER_SCENARIOS[5];
    }
    
    if (canUseMlaser) {
        return MLASER_SCENARIOS[tp] != null ? MLASER_SCENARIOS[tp] : MLASER_SCENARIOS[9];
    }
    
    if (canUseKatana) {
        return KATANA_SCENARIOS[tp] != null ? KATANA_SCENARIOS[tp] : KATANA_SCENARIOS[7];
    }
    
    if (canUseLightninger) {
        return LIGHTNINGER_SCENARIOS[tp] != null ? LIGHTNINGER_SCENARIOS[tp] : LIGHTNINGER_SCENARIOS[8];
    }
    
    // Last resort - try any weapon regardless of range
    if (inArray(weapons, WEAPON_RHINO)) {
        return RHINO_SCENARIOS[tp] != null ? RHINO_SCENARIOS[tp] : RHINO_SCENARIOS[5];
    }
    
    if (inArray(weapons, WEAPON_B_LASER)) {
        return BLASER_SCENARIOS[tp] != null ? BLASER_SCENARIOS[tp] : BLASER_SCENARIOS[5];
    }
    
    if (inArray(weapons, WEAPON_GRENADE_LAUNCHER)) {
        return GRENADE_LAUNCHER_SCENARIOS[tp] != null ? GRENADE_LAUNCHER_SCENARIOS[tp] : GRENADE_LAUNCHER_SCENARIOS[6];
    }
    
    if (inArray(weapons, WEAPON_RIFLE)) {
        return RIFLE_SCENARIOS[tp] != null ? RIFLE_SCENARIOS[tp] : RIFLE_SCENARIOS[7];
    }
    
    if (inArray(weapons, WEAPON_M_LASER)) {
        return MLASER_SCENARIOS[tp] != null ? MLASER_SCENARIOS[tp] : MLASER_SCENARIOS[9];
    }
    
    if (inArray(weapons, WEAPON_ENHANCED_LIGHTNINGER)) {
        return LIGHTNINGER_SCENARIOS[tp] != null ? LIGHTNINGER_SCENARIOS[tp] : LIGHTNINGER_SCENARIOS[8];
    }
    
    if (inArray(weapons, WEAPON_KATANA)) {
        return KATANA_SCENARIOS[tp] != null ? KATANA_SCENARIOS[tp] : KATANA_SCENARIOS[7];
    }
    
    // Existing weapons (for backward compatibility)
    if (inArray(weapons, WEAPON_FLAME_THROWER)) {
        return FLAME_SCENARIOS[tp] != null ? FLAME_SCENARIOS[tp] : FLAME_SCENARIOS[6];
    }
    if (inArray(weapons, WEAPON_GRENADE_LAUNCHER)) {
        return GRENADE_SCENARIOS[tp] != null ? GRENADE_SCENARIOS[tp] : GRENADE_SCENARIOS[7];
    }
    if (inArray(weapons, WEAPON_B_LASER)) {
        return BLASER_SCENARIOS[tp] != null ? BLASER_SCENARIOS[tp] : BLASER_SCENARIOS[5];
    }
    
    // Fallback to chip-only combat - return array not single value
    return CHIP_SCENARIOS[tp] != null ? CHIP_SCENARIOS[tp] : [CHIP_LIGHTNING];
}

// === WEAPON TYPE DETECTION ===
function isLineWeapon(weapon) {
    return weapon == WEAPON_M_LASER || weapon == WEAPON_B_LASER || 
           weapon == WEAPON_LASER || weapon == WEAPON_FLAME_THROWER;
}

function isAreaWeapon(weapon) {
    return weapon == WEAPON_GRENADE_LAUNCHER || 
           weapon == WEAPON_ENHANCED_LIGHTNINGER;  // Enhanced Lightninger has 3x3 AoE
}

function getDamageChips() {
    var allChips = getChips();
    var damageChips = [];
    
    var chipList = [CHIP_LIGHTNING, CHIP_METEORITE, CHIP_ICEBERG, 
                   CHIP_BURNING, CHIP_ROCKFALL, CHIP_SPARK];
    
    for (var i = 0; i < count(chipList); i++) {
        if (inArray(allChips, chipList[i])) {
            push(damageChips, chipList[i]);
        }
    }
    
    return damageChips;
}