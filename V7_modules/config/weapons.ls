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

// === M-LASER SCENARIOS (Cost: 8 TP, Max 2 uses/turn, Range 5-12, Damage 90-100) ===
global MLASER_SCENARIOS = [
    16: [WEAPON_M_LASER, WEAPON_M_LASER], // 2 uses = 16 TP
    12: [WEAPON_M_LASER, CHIP_LIGHTNING], // 1 use + chip = 12 TP  
    8: [WEAPON_M_LASER],                  // 1 use = 8 TP
    5: [CHIP_METEORITE],
    4: [CHIP_LIGHTNING],
    3: [CHIP_SPARK]
];

// === FLAME THROWER SCENARIOS (with poison chip synergy) ===
global FLAME_SCENARIOS = [
    18: [WEAPON_FLAME_THROWER, WEAPON_FLAME_THROWER, WEAPON_FLAME_THROWER],
    17: [WEAPON_FLAME_THROWER, WEAPON_FLAME_THROWER, CHIP_TOXIN],  // KEY COMBO!
    16: [WEAPON_FLAME_THROWER, WEAPON_FLAME_THROWER, CHIP_VENOM],  // Alternative combo
    15: [WEAPON_FLAME_THROWER, WEAPON_FLAME_THROWER, CHIP_SPARK],  // 15 TP combo with SPARK!
    12: [WEAPON_FLAME_THROWER, WEAPON_FLAME_THROWER],
    11: [WEAPON_FLAME_THROWER, CHIP_TOXIN],  // Single flame + AoE poison
    10: [WEAPON_FLAME_THROWER, CHIP_VENOM],  // Single flame + poison (unchanged)
    8: [WEAPON_FLAME_THROWER, CHIP_BURNING],
    6: [WEAPON_FLAME_THROWER],
    5: [CHIP_TOXIN],  // Fallback to AoE poison
    4: [CHIP_VENOM],  // Fallback to single poison
    3: [CHIP_SPARK]   // Final fallback
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

// === ENHANCED LIGHTNINGER SCENARIOS (Cost: 9 TP, Max 2 uses/turn, Range 6-10, Damage 89-93 + 100 HP heal) ===
global LIGHTNINGER_SCENARIOS = [
    18: [WEAPON_ENHANCED_LIGHTNINGER, WEAPON_ENHANCED_LIGHTNINGER], // 2 uses = 18 TP
    9: [WEAPON_ENHANCED_LIGHTNINGER],                               // 1 use = 9 TP  
    5: [CHIP_METEORITE],
    4: [CHIP_LIGHTNING],
    3: [CHIP_SPARK]
];

// === SWORD SCENARIOS (Cost: 6 TP, Max 2 uses/turn, Range 1, Damage 50-60) ===
global SWORD_SCENARIOS = [
    16: [WEAPON_SWORD, WEAPON_SWORD, CHIP_LIGHTNING], // 2 uses + chip = 16 TP
    12: [WEAPON_SWORD, WEAPON_SWORD],                 // 2 uses = 12 TP
    10: [WEAPON_SWORD, CHIP_LIGHTNING],               // 1 use + chip = 10 TP
    9: [WEAPON_SWORD, CHIP_SPARK],                    // 1 use + spark = 9 TP
    6: [WEAPON_SWORD],                                // 1 use = 6 TP
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

// === NEUTRINO SCENARIOS (Cost: 4 TP, Max 3 uses/turn, Range 2-6 diagonal) ===
global NEUTRINO_SCENARIOS = [
    12: [WEAPON_NEUTRINO, WEAPON_NEUTRINO, WEAPON_NEUTRINO], // 3 uses = 12 TP
    8: [WEAPON_NEUTRINO, WEAPON_NEUTRINO],                   // 2 uses = 8 TP
    7: [WEAPON_NEUTRINO, CHIP_SPARK],                        // 1 use + chip = 7 TP
    4: [WEAPON_NEUTRINO],                                    // 1 use = 4 TP
    3: [CHIP_SPARK]
];

// === DESTROYER SCENARIOS (Cost: 6 TP, Max 2 uses/turn, Range 1-6) ===
global DESTROYER_SCENARIOS = [
    12: [WEAPON_DESTROYER, WEAPON_DESTROYER], // 2 uses = 12 TP
    10: [WEAPON_DESTROYER, CHIP_LIGHTNING],   // 1 use + chip = 10 TP
    6: [WEAPON_DESTROYER],                    // 1 use = 6 TP
    4: [CHIP_LIGHTNING],
    3: [CHIP_SPARK]
];

// === POISON CHIP SCENARIOS (High magic builds) ===
global POISON_SCENARIOS = [
    17: [CHIP_TOXIN, CHIP_TOXIN, CHIP_TOXIN],  // Triple toxin (if cooldown allows)
    12: [CHIP_TOXIN, CHIP_TOXIN],              // Double toxin
    9: [CHIP_TOXIN, CHIP_VENOM],               // AoE + single poison
    8: [CHIP_VENOM, CHIP_VENOM],               // Double venom
    5: [CHIP_TOXIN],                           // Single AoE poison
    4: [CHIP_VENOM],                           // Single target poison
    3: [CHIP_SPARK]                            // Fallback
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
    
    // Sword - highest priority if in melee range (cheaper than Katana, 2x attacks)
    if (inArray(weapons, WEAPON_SWORD) && distance <= 1) {
        return SWORD_SCENARIOS[tp] != null ? SWORD_SCENARIOS[tp] : SWORD_SCENARIOS[6];
    }
    
    // Katana - fallback melee weapon if no sword
    if (inArray(weapons, WEAPON_KATANA) && distance <= 1) {
        return KATANA_SCENARIOS[tp] != null ? KATANA_SCENARIOS[tp] : KATANA_SCENARIOS[7];
    }
    
    // POISON BUILD PRIORITY (high magic + poison weapons/chips)
    var allChips = getChips();
    if (myMagic > myStrength * 1.5) { // Strong magic build
        
        // FLAME_THROWER + TOXIN combo (best at range 2-7 for both)
        if (inArray(weapons, WEAPON_FLAME_THROWER) && inArray(allChips, CHIP_TOXIN)) {
            if (distance >= 2 && distance <= 7 && lineOfSight(myCell, enemyCell)) {
                // Prioritize the 17 TP combo
                if (tp >= 17) {
                    return [WEAPON_FLAME_THROWER, WEAPON_FLAME_THROWER, CHIP_TOXIN];
                } else if (tp >= 11) {
                    return [WEAPON_FLAME_THROWER, CHIP_TOXIN];
                }
            }
        }
        
        // Pure chip poison if no line to enemy but in range
        if (inArray(allChips, CHIP_TOXIN) && distance <= 7) {
            return POISON_SCENARIOS[tp] != null ? POISON_SCENARIOS[tp] : POISON_SCENARIOS[5];
        }
        
        if (inArray(allChips, CHIP_VENOM) && distance <= 10) {
            return POISON_SCENARIOS[tp] != null ? POISON_SCENARIOS[tp] : POISON_SCENARIOS[4];
        }
    }
    
    // Rhino - high priority at 2-4 range (3x attacks for maximum DPS)
    if (inArray(weapons, WEAPON_RHINO) && distance >= 2 && distance <= 4 && lineOfSight(myCell, enemyCell)) {
        return RHINO_SCENARIOS[tp] != null ? RHINO_SCENARIOS[tp] : RHINO_SCENARIOS[5];
    }
    
    // Neutrino - high priority at diagonal positions (3x attacks, low cost)
    if (inArray(weapons, WEAPON_NEUTRINO) && distance >= 2 && distance <= 6) {
        // Check diagonal alignment
        var myX = getCellX(myCell);
        var myY = getCellY(myCell);
        var enemyX = getCellX(enemyCell);
        var enemyY = getCellY(enemyCell);
        
        var dx = abs(enemyX - myX);
        var dy = abs(enemyY - myY);
        
        // Prioritize Neutrino when diagonally aligned - cheap and effective!
        if (dx == dy && dx != 0 && lineOfSight(myCell, enemyCell)) {
            return NEUTRINO_SCENARIOS[tp] != null ? NEUTRINO_SCENARIOS[tp] : NEUTRINO_SCENARIOS[4];
        }
    }
    
    // M-LASER PRIORITY: Always check M-Laser first for better damage efficiency
    // Prioritize M-Laser when available - 8 TP cost vs 9 TP, 5-12 range vs 6-10 range
    if (inArray(weapons, WEAPON_M_LASER) && distance >= 5 && distance <= 12) {
        // M-Laser needs X or Y axis alignment
        var myX = getCellX(myCell);
        var myY = getCellY(myCell);
        var enemyX = getCellX(enemyCell);
        var enemyY = getCellY(enemyCell);
        
        var xAligned = (myX == enemyX);
        var yAligned = (myY == enemyY);
        
        // M-Laser aligned: IMMEDIATE priority - better TP efficiency than Enhanced Lightninger
        if ((xAligned || yAligned) && !(xAligned && yAligned)) {
            return MLASER_SCENARIOS[tp] != null ? MLASER_SCENARIOS[tp] : MLASER_SCENARIOS[8];
        }
        // Note: If M-Laser not aligned, we should consider moving to alignment rather than using Enhanced Lightninger
    }
    
    // HEALTH-BASED ENHANCED LIGHTNINGER: Only prioritize when critically low HP
    var currentHPPercent = myHP / myMaxHP;
    var criticalHP = (currentHPPercent < 0.35); // Only below 35% HP (was 60%)
    
    // Enhanced Lightninger for CRITICAL healing - reduced threshold to favor M-Laser movement
    if (criticalHP && inArray(weapons, WEAPON_ENHANCED_LIGHTNINGER) && distance >= 6 && distance <= 10 && lineOfSight(myCell, enemyCell)) {
        // CRITICAL HEALING: Enhanced Lightninger when desperately need +100 HP
        debugW("CRITICAL HP: Using Enhanced Lightninger for emergency healing (" + floor(currentHPPercent * 100) + "% HP)");
        return LIGHTNINGER_SCENARIOS[tp] != null ? LIGHTNINGER_SCENARIOS[tp] : LIGHTNINGER_SCENARIOS[9];
    }
    
    // Enhanced Lightninger - use only when M-Laser unavailable OR as pure fallback
    // Significantly reduced priority to encourage M-Laser positioning
    if (inArray(weapons, WEAPON_ENHANCED_LIGHTNINGER) && distance >= 6 && distance <= 10 && lineOfSight(myCell, enemyCell)) {
        // Check if M-Laser could work with movement - prefer moving to M-Laser alignment
        var hasMlaser = inArray(weapons, WEAPON_M_LASER);
        if (!hasMlaser) {
            // No M-Laser available, Enhanced Lightninger is fine
            return LIGHTNINGER_SCENARIOS[tp] != null ? LIGHTNINGER_SCENARIOS[tp] : LIGHTNINGER_SCENARIOS[9];
        } else {
            // M-Laser available but not aligned - prefer Enhanced Lightninger only if MP too low to move
            if (myMP < 3) {
                // Not enough MP to move for M-Laser alignment, use Enhanced Lightninger
                debugW("LOW MP: Using Enhanced Lightninger, insufficient MP for M-Laser alignment");
                return LIGHTNINGER_SCENARIOS[tp] != null ? LIGHTNINGER_SCENARIOS[tp] : LIGHTNINGER_SCENARIOS[9];
            }
            // Has MP to move for M-Laser alignment - skip Enhanced Lightninger to encourage movement
            debugW("M-LASER MOVEMENT: Skipping Enhanced Lightninger to encourage M-Laser alignment movement");
        }
    }
    
    // Destroyer - debuff weapon, good at close-mid range
    if (inArray(weapons, WEAPON_DESTROYER) && distance >= 1 && distance <= 6 && lineOfSight(myCell, enemyCell)) {
        return DESTROYER_SCENARIOS[tp] != null ? DESTROYER_SCENARIOS[tp] : DESTROYER_SCENARIOS[6];
    }
    
    // Rifle - reliable mid-range damage
    if (inArray(weapons, WEAPON_RIFLE) && distance >= 7 && distance <= 9 && lineOfSight(myCell, enemyCell)) {
        return RIFLE_SCENARIOS[tp] != null ? RIFLE_SCENARIOS[tp] : RIFLE_SCENARIOS[7];
    }
    
    // Grenade Launcher - AoE damage at mid range
    if (inArray(weapons, WEAPON_GRENADE_LAUNCHER) && distance >= 4 && distance <= 7 && lineOfSight(myCell, enemyCell)) {
        return GRENADE_LAUNCHER_SCENARIOS[tp] != null ? GRENADE_LAUNCHER_SCENARIOS[tp] : GRENADE_LAUNCHER_SCENARIOS[6];
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
    var canUseSword = inArray(weapons, WEAPON_SWORD) && distance <= 1;
    var canUseKatana = inArray(weapons, WEAPON_KATANA) && distance <= 1;
    var canUseRhino = inArray(weapons, WEAPON_RHINO) && distance >= 2 && distance <= 4;
    var canUseBlaser = inArray(weapons, WEAPON_B_LASER) && distance >= 2 && distance <= 8;
    var canUseGrenadeLauncher = inArray(weapons, WEAPON_GRENADE_LAUNCHER) && distance >= 4 && distance <= 7;
    var canUseNeutrino = inArray(weapons, WEAPON_NEUTRINO) && distance >= 2 && distance <= 6;
    var canUseDestroyer = inArray(weapons, WEAPON_DESTROYER) && distance >= 1 && distance <= 6;
    var canUseFlamethrower = inArray(weapons, WEAPON_FLAME_THROWER) && distance >= 2 && distance <= 8;
    
    // Prioritize weapons that are definitely in range
    if (canUseRhino) {
        return RHINO_SCENARIOS[tp] != null ? RHINO_SCENARIOS[tp] : RHINO_SCENARIOS[5];
    }
    
    if (canUseNeutrino) {
        return NEUTRINO_SCENARIOS[tp] != null ? NEUTRINO_SCENARIOS[tp] : NEUTRINO_SCENARIOS[4];
    }
    
    if (canUseDestroyer) {
        return DESTROYER_SCENARIOS[tp] != null ? DESTROYER_SCENARIOS[tp] : DESTROYER_SCENARIOS[6];
    }
    
    if (canUseFlamethrower) {
        return FLAME_SCENARIOS[tp] != null ? FLAME_SCENARIOS[tp] : FLAME_SCENARIOS[6];
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
    
    if (canUseSword) {
        return SWORD_SCENARIOS[tp] != null ? SWORD_SCENARIOS[tp] : SWORD_SCENARIOS[6];
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
    
    if (inArray(weapons, WEAPON_SWORD)) {
        return SWORD_SCENARIOS[tp] != null ? SWORD_SCENARIOS[tp] : SWORD_SCENARIOS[6];
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
    
    // LOW-TP STRATEGY: When TP < 7, encourage movement instead of weak chip attacks
    if (tp < 7) {
        // Find the cheapest available weapon for next turn positioning
        var cheapestWeapon = null;
        var cheapestCost = 999;
        
        for (var i = 0; i < count(weapons); i++) {
            var weapon = weapons[i];
            var cost = getWeaponCost(weapon);
            if (cost < cheapestCost) {
                cheapestCost = cost;
                cheapestWeapon = weapon;
            }
        }
        
        if (cheapestWeapon != null) {
            // Use weak chip and save TP for next turn
            debugW("LOW-TP STRATEGY: Using LIGHTNING to save TP for " + cheapestWeapon + " (costs " + cheapestCost + ")");
            return [CHIP_LIGHTNING]; // Use LIGHTNING (4 TP) instead of SPARK (3 TP) for better damage
        }
    }
    
    // Fallback to chip-only combat - return array not single value
    return CHIP_SCENARIOS[tp] != null ? CHIP_SCENARIOS[tp] : [CHIP_LIGHTNING];
}

// === WEAPON TYPE DETECTION ===
function isLineWeapon(weapon) {
    return weapon == WEAPON_M_LASER || weapon == WEAPON_B_LASER || 
           weapon == WEAPON_LASER || weapon == WEAPON_FLAME_THROWER;
}

function isNeutrinoWeapon(weapon) {
    return weapon == WEAPON_NEUTRINO;
}

function isAreaWeapon(weapon) {
    return weapon == WEAPON_GRENADE_LAUNCHER || 
           weapon == WEAPON_ENHANCED_LIGHTNINGER;  // Enhanced Lightninger has 3x3 AoE
}

function getAllDamageChips() {
    var allChips = getChips();
    var damageChips = [];
    
    var chipList = [CHIP_LIGHTNING, CHIP_METEORITE, CHIP_ICEBERG, 
                   CHIP_BURNING, CHIP_ROCKFALL, CHIP_SPARK,
                   CHIP_VENOM, CHIP_TOXIN];  // Add poison chips
    
    for (var i = 0; i < count(chipList); i++) {
        if (inArray(allChips, chipList[i])) {
            push(damageChips, chipList[i]);
        }
    }
    
    return damageChips;
}