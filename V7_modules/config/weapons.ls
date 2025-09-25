// V7 Module: config/weapons.ls
// Pre-defined weapon and chip scenarios by TP amount

// === RIFLE SCENARIOS (using built-in constants) ===
global RIFLE_SCENARIOS = [
    18: [WEAPON_RIFLE, WEAPON_RIFLE, CHIP_LIGHTNING], // 2 uses + chip = 18 TP
    14: [WEAPON_RIFLE, WEAPON_RIFLE],                 // 2 uses = 14 TP
    11: [WEAPON_RIFLE, CHIP_LIGHTNING],               // 1 use + chip = 11 TP
    7: [WEAPON_RIFLE],                                // 1 use = 7 TP
    5: [CHIP_METEORITE],
    4: [CHIP_LIGHTNING],
    3: [CHIP_SPARK]
];

// === M-LASER SCENARIOS (Cost: 8 TP, Max 2 uses/turn, Range 5-12, Damage 90-100) ===
global MLASER_SCENARIOS = [
    23: [WEAPON_M_LASER, WEAPON_M_LASER, CHIP_LIGHTNING, CHIP_SPARK], // 2 uses + 2 chips = 23 TP
    21: [WEAPON_M_LASER, WEAPON_M_LASER, CHIP_VENOM],                 // 2 uses + venom = 21 TP
    20: [WEAPON_M_LASER, WEAPON_M_LASER, CHIP_LIGHTNING],             // 2 uses + lightning = 20 TP
    16: [WEAPON_M_LASER, WEAPON_M_LASER],                             // 2 uses = 16 TP
    12: [WEAPON_M_LASER, CHIP_LIGHTNING],                             // 1 use + lightning = 12 TP  
    8: [WEAPON_M_LASER],                                              // 1 use = 8 TP
    5: [CHIP_METEORITE],
    4: [CHIP_LIGHTNING],
    3: [CHIP_SPARK]
];

// === FLAME THROWER SCENARIOS (max 2 uses/turn, with poison chip synergy) ===
global FLAME_SCENARIOS = [
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

// === DOUBLE GUN SCENARIOS (Cost: 4 TP, Max 3 uses/turn, Range 2-7, Damage + Poison stack) ===
global DOUBLE_GUN_SCENARIOS = [
    12: [WEAPON_DOUBLE_GUN, WEAPON_DOUBLE_GUN, WEAPON_DOUBLE_GUN], // 3 uses = 12 TP
    8:  [WEAPON_DOUBLE_GUN, WEAPON_DOUBLE_GUN],                    // 2 uses = 8 TP
    4:  [WEAPON_DOUBLE_GUN]                                        // 1 use = 4 TP
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
    16: [WEAPON_GRENADE_LAUNCHER, WEAPON_GRENADE_LAUNCHER, CHIP_LIGHTNING], // 2 uses + chip = 16 TP
    12: [WEAPON_GRENADE_LAUNCHER, WEAPON_GRENADE_LAUNCHER],                 // 2 uses = 12 TP
    10: [WEAPON_GRENADE_LAUNCHER, CHIP_LIGHTNING],                          // 1 use + chip = 10 TP
    6: [WEAPON_GRENADE_LAUNCHER],                                           // 1 use = 6 TP
    5: [CHIP_METEORITE],
    4: [CHIP_LIGHTNING]
];

// === ENHANCED LIGHTNINGER SCENARIOS (Cost: 9 TP, Max 2 uses/turn, Range 6-10, Damage 89-93 + 100 HP heal) ===
global LIGHTNINGER_SCENARIOS = [
    23: [WEAPON_ENHANCED_LIGHTNINGER, WEAPON_ENHANCED_LIGHTNINGER, CHIP_TOXIN],     // 2 uses + toxin = 23 TP
    22: [WEAPON_ENHANCED_LIGHTNINGER, WEAPON_ENHANCED_LIGHTNINGER, CHIP_LIGHTNING], // 2 uses + lightning = 22 TP
    21: [WEAPON_ENHANCED_LIGHTNINGER, WEAPON_ENHANCED_LIGHTNINGER, CHIP_SPARK],     // 2 uses + spark = 21 TP
    18: [WEAPON_ENHANCED_LIGHTNINGER, WEAPON_ENHANCED_LIGHTNINGER],                 // 2 uses = 18 TP
    13: [WEAPON_ENHANCED_LIGHTNINGER, CHIP_LIGHTNING],                              // 1 use + lightning = 13 TP
    9: [WEAPON_ENHANCED_LIGHTNINGER],                                               // 1 use = 9 TP  
    5: [CHIP_METEORITE],
    4: [CHIP_LIGHTNING],
    3: [CHIP_SPARK]
];

// === LIGHTNINGER SCENARIOS (Cost: 9 TP, Max 2 uses/turn, Range 6-10 star pattern, Diagonal cross AoE) ===
global REGULAR_LIGHTNINGER_SCENARIOS = [
    22: [WEAPON_LIGHTNINGER, WEAPON_LIGHTNINGER, CHIP_LIGHTNING], // 2 uses + chip = 22 TP  
    18: [WEAPON_LIGHTNINGER, WEAPON_LIGHTNINGER],                 // 2 uses = 18 TP
    13: [WEAPON_LIGHTNINGER, CHIP_LIGHTNING],                     // 1 use + chip = 13 TP
    9: [WEAPON_LIGHTNINGER],                                      // 1 use = 9 TP
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

// === ELECTRISOR SCENARIOS (Cost: 7 TP, Max 2 uses/turn, Range 7, Damage 70-80, Circle 1 AoE) ===
global ELECTRISOR_SCENARIOS = [
    18: [WEAPON_ELECTRISOR, WEAPON_ELECTRISOR, CHIP_LIGHTNING], // 2 uses + chip = 18 TP
    14: [WEAPON_ELECTRISOR, WEAPON_ELECTRISOR],                 // 2 uses = 14 TP
    11: [WEAPON_ELECTRISOR, CHIP_LIGHTNING],                    // 1 use + chip = 11 TP
    7: [WEAPON_ELECTRISOR],                                     // 1 use = 7 TP
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
    16: [WEAPON_DESTROYER, WEAPON_DESTROYER, CHIP_LIGHTNING], // 2 uses + chip = 16 TP
    12: [WEAPON_DESTROYER, WEAPON_DESTROYER],                 // 2 uses = 12 TP
    10: [WEAPON_DESTROYER, CHIP_LIGHTNING],                   // 1 use + chip = 10 TP
    6: [WEAPON_DESTROYER],                                    // 1 use = 6 TP
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

// === DEFENSIVE CHIP SCENARIOS ===
global LIBERATION_SCENARIOS = [
    8: [CHIP_LIBERATION, CHIP_SPARK],    // Liberation + damage (8 TP)
    5: [CHIP_LIBERATION],                // Liberation only (5 TP)
    3: [CHIP_SPARK]                      // Fallback damage
];

global ANTIDOTE_SCENARIOS = [
    7: [CHIP_ANTIDOTE, CHIP_LIGHTNING],  // Antidote + damage (7 TP)
    6: [CHIP_ANTIDOTE, CHIP_SPARK],      // Antidote + cheap damage (6 TP)
    3: [CHIP_ANTIDOTE],                  // Antidote only (3 TP)
    2: [CHIP_SPARK]                      // Fallback damage if can't afford antidote
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

// === NEW SIMPLIFIED SCENARIO SELECTION FUNCTION ===
function getScenarioForLoadout(weapons, tp) {
    // Use new dynamic system that works with any loadout
    return getBestScenarioForTP(tp, false);
}

// === OLD HARDCODED SCENARIO SELECTION FUNCTION (KEPT FOR REFERENCE) ===
function getScenarioForLoadout_OLD(weapons, tp) {
    // Define enemy cell for legacy function
    var legacyEnemyCell = (primaryTarget != null) ? getCell(primaryTarget) : null;
    if (legacyEnemyCell == null && count(allEnemies) > 0) {
        legacyEnemyCell = getCell(allEnemies[0]);
    }
    
    var distance = getCellDistance(myCell, legacyEnemyCell);
    
    // Get chips for scenario building
    var allChips = getChips();
    
    // Debug magic build detection
    // Weapon selection based on build type and range
    
    // Weapon priority order (most effective first by range)
    
    // Sword - highest priority if in melee range (cheaper than Katana, 2x attacks)
    if (inArray(weapons, WEAPON_SWORD) && distance <= 1) {
        return SWORD_SCENARIOS[tp] != null ? SWORD_SCENARIOS[tp] : SWORD_SCENARIOS[6];
    }
    
    // Katana - fallback melee weapon if no sword
    if (inArray(weapons, WEAPON_KATANA) && distance <= 1) {
        return KATANA_SCENARIOS[tp] != null ? KATANA_SCENARIOS[tp] : KATANA_SCENARIOS[7];
    }
    
    // MAGIC BUILD PRIORITY (DoT weapons as main DPS, DESTROYER for tactical debuffing)
    if (isMagicBuild) {
        // Magic build detected - prioritizing DoT weapons
        
        // FLAME_THROWER + TOXIN combo (DoT synergy - HIGHEST PRIORITY for magic builds)
        if (inArray(weapons, WEAPON_FLAME_THROWER) && inArray(allChips, CHIP_TOXIN)) {
            if (distance >= 2 && distance <= 8 && lineOfSight(myCell, legacyEnemyCell)) {
                // Using FLAME_THROWER + TOXIN DoT combo
                // Enhanced combos for magic builds (FLAME_THROWER max 2 uses/turn)
                // Check AoE safety for TOXIN combinations
                if (tp >= 17 && isChipSafeToUse(CHIP_TOXIN, legacyEnemyCell)) {
                    return [WEAPON_FLAME_THROWER, WEAPON_FLAME_THROWER, CHIP_TOXIN]; // KEY COMBO!
                } else if (tp >= 16) {
                    return [WEAPON_FLAME_THROWER, WEAPON_FLAME_THROWER, CHIP_VENOM]; // Alternative combo
                } else if (tp >= 11 && isChipSafeToUse(CHIP_TOXIN, legacyEnemyCell)) {
                    return [WEAPON_FLAME_THROWER, CHIP_TOXIN]; // Single flame + AoE poison
                } else if (tp >= 10) {
                    return [WEAPON_FLAME_THROWER, CHIP_VENOM]; // Single flame + poison
                }
            }
        }
        
        // FLAME_THROWER priority for magic builds (main DoT DPS weapon)
        if (inArray(weapons, WEAPON_FLAME_THROWER) && distance >= 2 && distance <= 8 && lineOfSight(myCell, legacyEnemyCell)) {
            // Using FLAME_THROWER as main DoT DPS
            // Enhanced flame thrower scenarios for magic builds (max 2 uses/turn)
            if (tp >= 12) {
                return [WEAPON_FLAME_THROWER, WEAPON_FLAME_THROWER]; // Double flame (max uses)
            } else if (tp >= 10) {
                return [WEAPON_FLAME_THROWER, CHIP_LIGHTNING]; // Single flame + chip
            } else if (tp >= 6) {
                return [WEAPON_FLAME_THROWER]; // Single flame
            }
        }
        
        // DESTROYER priority for magic builds (tactical debuff weapon - secondary)
        if (inArray(weapons, WEAPON_DESTROYER) && distance >= 1 && distance <= 6 && lineOfSight(myCell, legacyEnemyCell)) {
            // Using DESTROYER for tactical debuffing
            // DESTROYER scenarios for tactical debuffing
            if (tp >= 16) {
                return [WEAPON_DESTROYER, WEAPON_DESTROYER, CHIP_LIGHTNING]; // Double destroyer + chip
            } else if (tp >= 12) {
                return [WEAPON_DESTROYER, WEAPON_DESTROYER]; // Double destroyer
            } else if (tp >= 10) {
                return [WEAPON_DESTROYER, CHIP_LIGHTNING]; // Single destroyer + chip
            } else if (tp >= 6) {
                return [WEAPON_DESTROYER]; // Single destroyer
            }
        }
        
        // FLAME_THROWER solo priority for magic builds (DoT weapon)
        if (inArray(weapons, WEAPON_FLAME_THROWER) && distance >= 2 && distance <= 8 && lineOfSight(myCell, legacyEnemyCell)) {
            // Using FLAME_THROWER for DoT damage
            return FLAME_SCENARIOS[tp] != null ? FLAME_SCENARIOS[tp] : FLAME_SCENARIOS[6];
        }
        
        // Pure poison chip priority (DoT chips without line of sight requirement)
        if (inArray(allChips, CHIP_TOXIN) && distance <= 7 && isChipSafeToUse(CHIP_TOXIN, legacyEnemyCell)) {
            // Using TOXIN for AoE DoT
            if (isHighMagicBuild && tp >= 17) {
                return [CHIP_TOXIN, CHIP_TOXIN, CHIP_TOXIN]; // Triple toxin for very high magic
            }
            return POISON_SCENARIOS[tp] != null ? POISON_SCENARIOS[tp] : POISON_SCENARIOS[5];
        }
        
        if (inArray(allChips, CHIP_VENOM) && distance <= 10) {
            // Using VENOM for single-target DoT
            if (isHighMagicBuild && tp >= 12) {
                return [CHIP_VENOM, CHIP_VENOM, CHIP_VENOM]; // Triple venom for very high magic
            }
            return POISON_SCENARIOS[tp] != null ? POISON_SCENARIOS[tp] : POISON_SCENARIOS[4];
        }
    }
    
    // Rhino - high priority at 2-4 range (3x attacks for maximum DPS)
    if (inArray(weapons, WEAPON_RHINO) && distance >= 2 && distance <= 4 && lineOfSight(myCell, legacyEnemyCell)) {
        return RHINO_SCENARIOS[tp] != null ? RHINO_SCENARIOS[tp] : RHINO_SCENARIOS[5];
    }
    
    // Neutrino - high priority at diagonal positions (3x attacks, low cost)
    if (inArray(weapons, WEAPON_NEUTRINO) && distance >= 2 && distance <= 6) {
        // Check diagonal alignment
        var myX = getCellX(myCell);
        var myY = getCellY(myCell);
        var enemyX = getCellX(legacyEnemyCell);
        var enemyY = getCellY(legacyEnemyCell);
        
        var dx = abs(enemyX - myX);
        var dy = abs(enemyY - myY);
        
        // Prioritize Neutrino when diagonally aligned - cheap and effective!
        if (dx == dy && dx != 0 && lineOfSight(myCell, legacyEnemyCell)) {
            return NEUTRINO_SCENARIOS[tp] != null ? NEUTRINO_SCENARIOS[tp] : NEUTRINO_SCENARIOS[4];
        }
    }
    
    // M-LASER PRIORITY: Always check M-Laser first for better damage efficiency
    // Prioritize M-Laser when available - 8 TP cost vs 9 TP, 5-12 range vs 6-10 range
    if (inArray(weapons, WEAPON_M_LASER) && distance >= 5 && distance <= 12) {
        // M-Laser needs X or Y axis alignment
        var myX = getCellX(myCell);
        var myY = getCellY(myCell);
        var enemyX = getCellX(legacyEnemyCell);
        var enemyY = getCellY(legacyEnemyCell);
        
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
    if (criticalHP && inArray(weapons, WEAPON_ENHANCED_LIGHTNINGER) && distance >= 6 && distance <= 10 && lineOfSight(myCell, legacyEnemyCell)) {
        // CRITICAL HEALING: Enhanced Lightninger when desperately need +100 HP
        // Critical HP - using Enhanced Lightninger for healing
        return LIGHTNINGER_SCENARIOS[tp] != null ? LIGHTNINGER_SCENARIOS[tp] : LIGHTNINGER_SCENARIOS[9];
    }
    
    // Enhanced Lightninger - use only when M-Laser unavailable OR as pure fallback
    // Significantly reduced priority to encourage M-Laser positioning
    if (inArray(weapons, WEAPON_ENHANCED_LIGHTNINGER) && distance >= 6 && distance <= 10 && lineOfSight(myCell, legacyEnemyCell)) {
        // Check if M-Laser could work with movement - prefer moving to M-Laser alignment
        var hasMlaser = inArray(weapons, WEAPON_M_LASER);
        if (!hasMlaser) {
            // No M-Laser available, Enhanced Lightninger is fine
            return LIGHTNINGER_SCENARIOS[tp] != null ? LIGHTNINGER_SCENARIOS[tp] : LIGHTNINGER_SCENARIOS[9];
        } else {
            // M-Laser available but not aligned - prefer Enhanced Lightninger only if MP too low to move
            if (myMP < 3) {
                // Not enough MP to move for M-Laser alignment, use Enhanced Lightninger
                // Low MP - using Enhanced Lightninger
                return LIGHTNINGER_SCENARIOS[tp] != null ? LIGHTNINGER_SCENARIOS[tp] : LIGHTNINGER_SCENARIOS[9];
            }
            // Has MP to move for M-Laser alignment - skip Enhanced Lightninger to encourage movement
            // Encouraging M-Laser alignment movement
        }
    }
    
    // NON-MAGIC BUILD WEAPON PRIORITIZATION
    // Skip these for magic builds to prioritize DoT/debuff weapons
    if (!isMagicBuild) {
        // Destroyer - debuff weapon, good at close-mid range (normal priority for non-magic)
        if (inArray(weapons, WEAPON_DESTROYER) && distance >= 1 && distance <= 6 && lineOfSight(myCell, legacyEnemyCell)) {
            return DESTROYER_SCENARIOS[tp] != null ? DESTROYER_SCENARIOS[tp] : DESTROYER_SCENARIOS[6];
        }
        
        // Electrisor - AoE damage at range 7 (prioritize over single-target weapons)
        if (inArray(weapons, WEAPON_ELECTRISOR) && distance == 7 && lineOfSight(myCell, legacyEnemyCell)) {
            return ELECTRISOR_SCENARIOS[tp] != null ? ELECTRISOR_SCENARIOS[tp] : ELECTRISOR_SCENARIOS[7];
        }
        
        // Rifle - reliable mid-range damage
        if (inArray(weapons, WEAPON_RIFLE) && distance >= 7 && distance <= 9 && lineOfSight(myCell, legacyEnemyCell)) {
            return RIFLE_SCENARIOS[tp] != null ? RIFLE_SCENARIOS[tp] : RIFLE_SCENARIOS[7];
        }
        
        // Grenade Launcher - AoE damage at mid range
        if (inArray(weapons, WEAPON_GRENADE_LAUNCHER) && distance >= 4 && distance <= 7 && lineOfSight(myCell, legacyEnemyCell)) {
            return GRENADE_LAUNCHER_SCENARIOS[tp] != null ? GRENADE_LAUNCHER_SCENARIOS[tp] : GRENADE_LAUNCHER_SCENARIOS[6];
        }
    } else {
        // For MAGIC builds, prioritize DoT weapons in this section too
        // Magic build - prioritizing DoT weapons over non-DoT
        
        // FLAME_THROWER gets priority over Grenade Launcher for magic builds
        if (inArray(weapons, WEAPON_FLAME_THROWER) && distance >= 2 && distance <= 8 && lineOfSight(myCell, legacyEnemyCell)) {
            // Using FLAME_THROWER over Grenade Launcher
            return FLAME_SCENARIOS[tp] != null ? FLAME_SCENARIOS[tp] : FLAME_SCENARIOS[6];
        }
        
        // DESTROYER gets priority for magic builds
        if (inArray(weapons, WEAPON_DESTROYER) && distance >= 1 && distance <= 6 && lineOfSight(myCell, legacyEnemyCell)) {
            // Using DESTROYER for debuff over other weapons
            return DESTROYER_SCENARIOS[tp] != null ? DESTROYER_SCENARIOS[tp] : DESTROYER_SCENARIOS[6];
        }
        
        // Electrisor still useful for magic builds (AoE)
        if (inArray(weapons, WEAPON_ELECTRISOR) && distance == 7 && lineOfSight(myCell, legacyEnemyCell)) {
            return ELECTRISOR_SCENARIOS[tp] != null ? ELECTRISOR_SCENARIOS[tp] : ELECTRISOR_SCENARIOS[7];
        }
    }
    
    // B-Laser - cheaper line weapon alternative (5 TP vs M-Laser's 9 TP)
    if (inArray(weapons, WEAPON_B_LASER) && distance >= 2 && distance <= 8) {
        // B-Laser needs X or Y axis alignment (like M-Laser)
        var myX = getCellX(myCell);
        var myY = getCellY(myCell);
        var enemyX = getCellX(legacyEnemyCell);
        var enemyY = getCellY(legacyEnemyCell);
        
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
    var canUseRegularLightninger = inArray(weapons, WEAPON_LIGHTNINGER) && distance >= 6 && distance <= 10;
    var canUseSword = inArray(weapons, WEAPON_SWORD) && distance <= 1;
    var canUseKatana = inArray(weapons, WEAPON_KATANA) && distance <= 1;
    var canUseRhino = inArray(weapons, WEAPON_RHINO) && distance >= 2 && distance <= 4;
    var canUseBlaser = inArray(weapons, WEAPON_B_LASER) && distance >= 2 && distance <= 8;
    var canUseGrenadeLauncher = inArray(weapons, WEAPON_GRENADE_LAUNCHER) && distance >= 4 && distance <= 7;
    var canUseNeutrino = inArray(weapons, WEAPON_NEUTRINO) && distance >= 2 && distance <= 6;
    var canUseDestroyer = inArray(weapons, WEAPON_DESTROYER) && distance >= 1 && distance <= 6;
    var canUseFlamethrower = inArray(weapons, WEAPON_FLAME_THROWER) && distance >= 2 && distance <= 8;
    var canUseElectrisor = inArray(weapons, WEAPON_ELECTRISOR) && distance == 7;
    
    // Prioritize weapons that are definitely in range
    // For magic builds, prioritize DoT and debuff weapons first
    if (isMagicBuild) {
        // Prioritize DESTROYER for magic builds (debuff weapon)
        if (canUseDestroyer) {
            // Magic fallback - DESTROYER for debuff
            return DESTROYER_SCENARIOS[tp] != null ? DESTROYER_SCENARIOS[tp] : DESTROYER_SCENARIOS[6];
        }
        
        // Prioritize FLAME_THROWER for magic builds (DoT weapon)
        if (canUseFlamethrower) {
            // Magic fallback - FLAME_THROWER for DoT
            return FLAME_SCENARIOS[tp] != null ? FLAME_SCENARIOS[tp] : FLAME_SCENARIOS[6];
        }
    }
    
    // Standard weapon prioritization - but respect magic build preferences
    if (!isMagicBuild) {
        // Non-magic builds use standard order
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
        
        if (canUseElectrisor) {
            return ELECTRISOR_SCENARIOS[tp] != null ? ELECTRISOR_SCENARIOS[tp] : ELECTRISOR_SCENARIOS[7];
        }
        
        if (canUseRifle) {
            return RIFLE_SCENARIOS[tp] != null ? RIFLE_SCENARIOS[tp] : RIFLE_SCENARIOS[7];
        }
        
        if (canUseGrenadeLauncher) {
            return GRENADE_LAUNCHER_SCENARIOS[tp] != null ? GRENADE_LAUNCHER_SCENARIOS[tp] : GRENADE_LAUNCHER_SCENARIOS[6];
        }
    } else {
        // Magic builds: prioritize DoT and debuff weapons even in fallback
        // Re-checking DoT/debuff weapons before other options
        
        if (canUseFlamethrower) {
            // Magic fallback - FLAME_THROWER for DoT
            return FLAME_SCENARIOS[tp] != null ? FLAME_SCENARIOS[tp] : FLAME_SCENARIOS[6];
        }
        
        if (canUseDestroyer) {
            // Magic fallback - DESTROYER for debuff
            return DESTROYER_SCENARIOS[tp] != null ? DESTROYER_SCENARIOS[tp] : DESTROYER_SCENARIOS[6];
        }
        
        // Other weapons as secondary fallback for magic builds
        if (canUseElectrisor) {
            return ELECTRISOR_SCENARIOS[tp] != null ? ELECTRISOR_SCENARIOS[tp] : ELECTRISOR_SCENARIOS[7];
        }
        
        if (canUseRhino) {
            return RHINO_SCENARIOS[tp] != null ? RHINO_SCENARIOS[tp] : RHINO_SCENARIOS[5];
        }
        
        // Regular Lightninger - check star pattern requirement
        if (canUseRegularLightninger && isValidStarPattern(myCell, legacyEnemyCell)) {
            // Magic backup - using regular LIGHTNINGER
            return REGULAR_LIGHTNINGER_SCENARIOS[tp] != null ? REGULAR_LIGHTNINGER_SCENARIOS[tp] : REGULAR_LIGHTNINGER_SCENARIOS[9];
        }
        
        if (canUseNeutrino) {
            return NEUTRINO_SCENARIOS[tp] != null ? NEUTRINO_SCENARIOS[tp] : NEUTRINO_SCENARIOS[4];
        }
        
        // Non-DoT weapons as last resort for magic builds
        if (canUseRifle) {
            return RIFLE_SCENARIOS[tp] != null ? RIFLE_SCENARIOS[tp] : RIFLE_SCENARIOS[7];
        }
        
        if (canUseGrenadeLauncher) {
            return GRENADE_LAUNCHER_SCENARIOS[tp] != null ? GRENADE_LAUNCHER_SCENARIOS[tp] : GRENADE_LAUNCHER_SCENARIOS[6];
        }
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
    
    if (inArray(weapons, WEAPON_ELECTRISOR)) {
        return ELECTRISOR_SCENARIOS[tp] != null ? ELECTRISOR_SCENARIOS[tp] : ELECTRISOR_SCENARIOS[7];
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
            // Low-TP strategy - saving TP for weapon usage
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
           weapon == WEAPON_ENHANCED_LIGHTNINGER ||  // Enhanced Lightninger has 3x3 AoE
           weapon == WEAPON_LIGHTNINGER ||           // Lightninger has diagonal cross AoE
           weapon == WEAPON_ELECTRISOR;              // Electrisor has Circle 1 AoE
}

function isStarPatternWeapon(weapon) {
    return weapon == WEAPON_LIGHTNINGER;
}

function isValidStarPattern(fromCell, targetCell) {
    // Star pattern: same line OR 45-degree diagonal, distance 6-10
    var distance = getCellDistance(fromCell, targetCell);
    if (distance < 6 || distance > 10) return false;
    
    // Calculate dx and dy
    var fromX = getCellX(fromCell);
    var fromY = getCellY(fromCell);
    var targetX = getCellX(targetCell);
    var targetY = getCellY(targetCell);
    
    var dx = targetX - fromX;
    var dy = targetY - fromY;
    
    // LIGHTNINGER star pattern allows:
    // 1. Same horizontal line (dy = 0)
    // 2. Same vertical line (dx = 0)  
    // 3. 45-degree diagonal (abs(dx) = abs(dy)) - ONLY for LIGHTNINGER
    return (dy == 0) || (dx == 0) || (abs(dx) == abs(dy));
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

// === NEW DYNAMIC WEAPON SELECTION SYSTEM ===

// Get the best scenario based on currently equipped weapons and chips
function getBestScenarioForTP(tp, forCombat) {
    var weapons = getWeapons();
    var chips = getChips();
    
    // Define targetEnemyCell for scenario building
    var targetEnemyCell = (primaryTarget != null) ? getCell(primaryTarget) : null;
    if (targetEnemyCell == null && count(allEnemies) > 0) {
        targetEnemyCell = getCell(allEnemies[0]);
    }
    
    if (weapons == null || count(weapons) == 0) {
        // No weapons - use chip-only scenario (use medium range as default)
        return getChipOnlyScenario(chips, tp, 8);
    }

    // FAST-PATH: Prefer M-LASER if aligned, in range, and LOS clear (efficient 8 TP weapon)
    if (inArray(weapons, WEAPON_M_LASER) && targetEnemyCell != null) {
        var dist = getCellDistance(getCell(), targetEnemyCell);
        var minR = getWeaponMinRange(WEAPON_M_LASER);
        var maxR = getWeaponMaxRange(WEAPON_M_LASER);
        if (dist >= minR && dist <= maxR && lineOfSight(getCell(), targetEnemyCell) && isOnSameLine(getCell(), targetEnemyCell)) {
            var ml = MLASER_SCENARIOS[tp];
            if (ml != null) return ml;
            return MLASER_SCENARIOS[8]; // fallback single use
        }
    }
    
    var bestScenario = null;
    var bestValue = 0;
    
    // Scenario function called
    
    // For magic builds, prioritize optimal mixed scenarios
    // Magic build check
    if (isMagicBuild) {
        // Building magic scenario
        var magicScenario = buildMagicScenario(weapons, chips, tp, forCombat);
        // Magic scenario result obtained
        if (magicScenario != null) {
            // Built optimal magic scenario
            var magicValue = calculateScenarioValue(magicScenario, WEAPON_FLAME_THROWER);
            if (magicValue > bestValue) {
                bestValue = magicValue;
                bestScenario = magicScenario;
                // Magic scenario selected as best
            }
        }
    }
    
    // For strength builds: check what weapons work at current distance first
    var weaponPriorityOrder = weapons;
    if (!isMagicBuild && targetEnemyCell != null) {
        var currentDistance = getCellDistance(getCell(), targetEnemyCell);
        var optimalWeapon = null;
        
        // Find best weapon for current distance
        for (var i = 0; i < count(weapons); i++) {
            var weapon = weapons[i];
            var minRange = getWeaponMinRange(weapon);
            var maxRange = getWeaponMaxRange(weapon);
            
            if (currentDistance >= minRange && currentDistance <= maxRange) {
                optimalWeapon = weapon;
                break;  // Use first valid weapon
            }
        }
        
        // If we found an optimal weapon, prioritize it
        if (optimalWeapon != null) {
            weaponPriorityOrder = [optimalWeapon];
            for (var i = 0; i < count(weapons); i++) {
                if (weapons[i] != optimalWeapon) {
                    push(weaponPriorityOrder, weapons[i]);
                }
            }
            // Strength priority - using optimal weapon for distance
        }
    }
    
    // Check each equipped weapon in priority order
    for (var i = 0; i < count(weaponPriorityOrder); i++) {
        var weapon = weaponPriorityOrder[i];
        
        // Skip weapons that have reached their usage limit this turn
        var remainingUses = getRemainingWeaponUses(weapon);
        if (remainingUses <= 0) {
            // Weapon has no remaining uses this turn
            continue;
        }
        
        // Testing weapon scenario
        var scenario = buildScenarioForWeapon(weapon, tp, chips, null, forCombat);
        
        if (scenario != null) {
            // Weapon scenario built successfully
            
            // Validate scenario executability before calculating value
            if (forCombat && targetEnemyCell != null) {
                var scenarioValid = validateScenarioExecutability(scenario, targetEnemyCell);
                if (!scenarioValid) {
                    // Scenario failed validation
                    continue; // Skip this scenario
                }
            }
            
            var value = calculateScenarioValue(scenario, weapon);
            
            // For strength builds: prefer weapons that work at current distance AND alignment
            if (!isMagicBuild && targetEnemyCell != null) {
                var currentDistance = getCellDistance(getCell(), targetEnemyCell);
                var minRange = getWeaponMinRange(weapon);
                var maxRange = getWeaponMaxRange(weapon);
                
                if (currentDistance >= minRange && currentDistance <= maxRange) {
                    // Check alignment based on weapon launch type
                    var alignmentOK = true;
                    var launchType = getWeaponLaunchType(weapon);
                    
                    if (launchType == LAUNCH_TYPE_LINE || launchType == LAUNCH_TYPE_LINE_INVERTED) {
                        var myX = getCellX(getCell());
                        var myY = getCellY(getCell());
                        var targetX = getCellX(targetEnemyCell);
                        var targetY = getCellY(targetEnemyCell);
                        var dx = targetX - myX;
                        var dy = targetY - myY;
                        alignmentOK = (dx == 0) || (dy == 0); // Line weapons require X OR Y axis alignment
                        if (!alignmentOK) {
                            // Line weapon lacks alignment
                        }
                    } else if (launchType == LAUNCH_TYPE_DIAGONAL || launchType == LAUNCH_TYPE_DIAGONAL_INVERTED) {
                        var myX = getCellX(getCell());
                        var myY = getCellY(getCell());
                        var targetX = getCellX(targetEnemyCell);
                        var targetY = getCellY(targetEnemyCell);
                        var dx = abs(targetX - myX);
                        var dy = abs(targetY - myY);
                        alignmentOK = (dx == dy && dx > 0); // Diagonal weapons require perfect diagonal alignment
                        if (!alignmentOK) {
                            // Diagonal weapon lacks alignment
                        }
                    } else if (launchType == LAUNCH_TYPE_STAR || launchType == LAUNCH_TYPE_STAR_INVERTED) {
                        var myX = getCellX(getCell());
                        var myY = getCellY(getCell());
                        var targetX = getCellX(targetEnemyCell);
                        var targetY = getCellY(targetEnemyCell);
                        var dx = targetX - myX;
                        var dy = targetY - myY;
                        var lineAligned = (dx == 0) || (dy == 0);
                        var diagAligned = (abs(dx) == abs(dy) && dx != 0);
                        alignmentOK = lineAligned || diagAligned; // Star pattern: line OR diagonal
                        if (!alignmentOK) {
                            // Star weapon lacks alignment
                        }
                    }
                    // LAUNCH_TYPE_CIRCLE weapons don't require alignment validation
                    
                    if (alignmentOK) {
                        value = value * 2; // Double the value for range-appropriate weapons
                        // Strength boost applied for range-appropriate weapon
                    } else {
                        // Reduce value significantly for misaligned weapons
                        value = value * 0.1;
                        // Alignment penalty applied
                    }
                }
            }
            
            if (value > bestValue) {
                bestValue = value;
                bestScenario = scenario;
                // New best weapon scenario found
            }
        } else {
            // Weapon scenario failed
        }
    }
    
    // For strength builds: Only consider chip-only scenarios if no weapon scenarios work
    // For magic builds: Always consider chip scenarios competitively
    if (isMagicBuild) {
        var targetDistance = (targetEnemyCell != null) ? getCellDistance(myCell, targetEnemyCell) : 8;
        var chipScenario = getChipOnlyScenario(chips, tp, targetDistance);
        if (chipScenario != null) {
            // Built chip-only scenario
            var chipValue = calculateScenarioValue(chipScenario, chipScenario[0]);
            // Chip scenario evaluated
            if (chipValue > bestValue) {
                bestValue = chipValue;
                bestScenario = chipScenario;
                // Chip scenario selected as best
            }
        }
    } else {
        // STRENGTH BUILD: Only use chips if no weapon scenario was found
        if (bestScenario == null) {
            // Fallback to chip scenarios
            var targetDistance = null;
            if (targetEnemyCell != null) {
                targetDistance = getCellDistance(getCell(), targetEnemyCell);
            }
            var chipScenario = getChipOnlyScenario(chips, tp, targetDistance);
            if (chipScenario != null) {
                // Built chip fallback scenario
                bestScenario = chipScenario;
                bestValue = calculateScenarioValue(chipScenario, chipScenario[0]);
            }
        } else {
            // Using weapon scenario over chips
        }
    }

    // ALWAYS consider defensive scenarios (both strength and magic builds)
    var defensiveScenario = getDefensiveScenario(tp, chips);
    if (defensiveScenario != null) {
        var defensiveValue = calculateDefensiveScenarioValue(defensiveScenario);
        debugW("DEFENSIVE EVALUATION: Scenario [" + join(defensiveScenario, ", ") + "] has value " + defensiveValue + " vs best " + bestValue);

        if (defensiveValue > bestValue) {
            bestValue = defensiveValue;
            bestScenario = defensiveScenario;
            debugW("DEFENSIVE BEST: Defensive scenario is new best with value " + defensiveValue);
        } else {
            debugW("DEFENSIVE SKIP: Defensive scenario value " + defensiveValue + " < best " + bestValue);
        }
    } else {
        debugW("DEFENSIVE NONE: No defensive scenario needed");
    }

    // If still no scenario, use fallback
    if (bestScenario == null) {
        bestScenario = [CHIP_LIGHTNING];
    }

    return bestScenario;
}

// Build optimal mixed scenarios for magic builds
function buildMagicScenario(weapons, chips, availableTP, forCombat) {
    debugW("MAGIC FUNC: buildMagicScenario called with availableTP=" + availableTP);
    debugW("MAGIC FUNC: weapons=[" + join(weapons, ", ") + "], hasFlamethrower=" + inArray(weapons, WEAPON_FLAME_THROWER));
    
    // Define targetEnemyCell for scenario building
    var targetEnemyCell = (primaryTarget != null) ? getCell(primaryTarget) : null;
    if (targetEnemyCell == null && count(allEnemies) > 0) {
        targetEnemyCell = getCell(allEnemies[0]);
    }
    
    // FLAME is optional – we can operate with DESTROYER/poisons alone.
    var hasFlame = inArray(weapons, WEAPON_FLAME_THROWER);
    
    // For FLAME, compute in-range flag; do not abort scenario building if out of range.
    var currentDistance = (targetEnemyCell != null) ? getCellDistance(getCell(), targetEnemyCell) : 99;
    var flameInRange = hasFlame && currentDistance >= 2 && currentDistance <= 8;
    if (forCombat == true) {
        debugW("MAGIC FUNC: Position check - distance=" + currentDistance + ", forCombat=" + forCombat);
        if (!flameInRange) {
            debugW("MAGIC FUNC: FLAME out of range now; will still consider DESTROYER/poisons");
        }
    }
    
    var switchCost = (getWeapon() != WEAPON_FLAME_THROWER) ? 1 : 0;
    var tpLeft = availableTP - switchCost;
    
    // Check remaining FLAME_THROWER uses this turn (max 2 per turn)
    var maxNewFlamethrowerUses = getRemainingWeaponUses(WEAPON_FLAME_THROWER);
    var usedThisTurn = 2 - maxNewFlamethrowerUses;
    debugW("MAGIC FUNC: FLAME_THROWER already used " + usedThisTurn + " times, can use " + maxNewFlamethrowerUses + " more");
    
    // Check enemy effects for intelligent alternation
    var primaryEnemy = primaryTarget;
    if (primaryEnemy == null && count(allEnemies) > 0) {
        primaryEnemy = allEnemies[0];
    }
    
    var enemyHasDoT = false;
    var enemyHasStrengthDebuff = false;
    var dotTurnsLeft = 0;
    var debuffTurnsLeft = 0;
    
    if (primaryEnemy != null) {
        enemyHasDoT = hasDoTEffect(primaryEnemy);
        enemyHasStrengthDebuff = hasStrengthDebuff(primaryEnemy);
        dotTurnsLeft = getDoTRemainingTurns(primaryEnemy);
        debuffTurnsLeft = getStrengthDebuffRemainingTurns(primaryEnemy);
        debugW("MAGIC EFFECTS: enemy=" + primaryEnemy + ", hasDoT=" + enemyHasDoT + " (" + dotTurnsLeft + " turns), hasDebuff=" + enemyHasStrengthDebuff + " (" + debuffTurnsLeft + " turns)");
    }
    
    // Build dynamic scenarios based on enemy effects, in this order:
    // 1) DESTROYER (debuff), 2) DoT (FLAME/poison), 3) Healing (added later), 4) simple backups
    var scenarios = [];

    // 1) DESTROYER-first options (apply strength debuff before DoT)
    if (!enemyHasStrengthDebuff || debuffTurnsLeft <= 1) {
        // High TP: double DESTROYER or DESTROYER + chip
        push(scenarios, {tp: 12, actions: [WEAPON_DESTROYER, WEAPON_DESTROYER]});
        push(scenarios, {tp: 10, actions: [WEAPON_DESTROYER, CHIP_LIGHTNING]});
        push(scenarios, {tp: 6,  actions: [WEAPON_DESTROYER]});
    }

    // 2) DoT options (FLAME + poison)
    if (!enemyHasDoT || dotTurnsLeft <= 1) {
        // High TP: double FLAME + poison
        if (flameInRange) {
            if (isChipSafeToUse(CHIP_TOXIN, targetEnemyCell)) {
                push(scenarios, {tp: 17, actions: [WEAPON_FLAME_THROWER, WEAPON_FLAME_THROWER, CHIP_TOXIN]});
            } else {
                push(scenarios, {tp: 17, actions: [WEAPON_FLAME_THROWER, WEAPON_FLAME_THROWER, CHIP_VENOM]});
            }
            push(scenarios, {tp: 16, actions: [WEAPON_FLAME_THROWER, WEAPON_FLAME_THROWER, CHIP_VENOM]});
        }

        // Medium TP: single FLAME + poison
        if (flameInRange) {
            if (isChipSafeToUse(CHIP_TOXIN, targetEnemyCell)) {
                push(scenarios, {tp: 11, actions: [WEAPON_FLAME_THROWER, CHIP_TOXIN]});
            } else {
                push(scenarios, {tp: 11, actions: [WEAPON_FLAME_THROWER, CHIP_VENOM]});
            }
            push(scenarios, {tp: 10, actions: [WEAPON_FLAME_THROWER, CHIP_VENOM]});
        }

        // Low TP DoT chips
        if (isChipSafeToUse(CHIP_TOXIN, targetEnemyCell)) {
            push(scenarios, {tp: 5, actions: [CHIP_TOXIN]});
        } else {
            push(scenarios, {tp: 5, actions: [CHIP_VENOM]});
        }
        push(scenarios, {tp: 4, actions: [CHIP_VENOM]});
    }

    // 2b) DOUBLE_GUN options (stacking poison, cheap TP)
    if (inArray(weapons, WEAPON_DOUBLE_GUN) && lineOfSight(getCell(), targetEnemyCell)) {
        var dgDist = getCellDistance(getCell(), targetEnemyCell);
        if (dgDist >= 2 && dgDist <= 7) {
            // Prefer triple when TP allows, else double/single
            push(scenarios, {tp: 12, actions: [WEAPON_DOUBLE_GUN, WEAPON_DOUBLE_GUN, WEAPON_DOUBLE_GUN]});
            push(scenarios, {tp: 8,  actions: [WEAPON_DOUBLE_GUN, WEAPON_DOUBLE_GUN]});
            push(scenarios, {tp: 4,  actions: [WEAPON_DOUBLE_GUN]});
        }
    }

    // Backup FLAME-only shots (only when FLAME is in range)
    if (flameInRange) {
        push(scenarios, {tp: 15, actions: [WEAPON_FLAME_THROWER, WEAPON_FLAME_THROWER, CHIP_SPARK]});
        push(scenarios, {tp: 12, actions: [WEAPON_FLAME_THROWER, WEAPON_FLAME_THROWER]});
        push(scenarios, {tp: 9,  actions: [WEAPON_FLAME_THROWER, CHIP_SPARK]});
        push(scenarios, {tp: 6,  actions: [WEAPON_FLAME_THROWER]});
    }
    
    // Final cheap fallback
    push(scenarios, {tp: 3, actions: [CHIP_SPARK]});

    // HEALING SCENARIOS: Gate strictly — only when truly needed or no offense possible
    var safeDistance = (targetEnemyCell != null) ? (getCellDistance(getCell(), targetEnemyCell) >= 9) : true;
    var hpPercent = myHP / myMaxHP;
    var healingPriority = getHealingPriority();

    // Determine if an offensive action is possible from current cell
    var offenseAvailable = false;
    var curCell = getCell();
    if (targetEnemyCell != null) {
        var distNow = getCellDistance(curCell, targetEnemyCell);
        var weapsNow = getWeapons();
        // FLAME/DESTROYER checks (alignment + LoS for line)
        if (!offenseAvailable && inArray(weapsNow, WEAPON_FLAME_THROWER)) {
            if (distNow >= 2 && distNow <= 8 && lineOfSight(curCell, targetEnemyCell) && isOnSameLine(curCell, targetEnemyCell)) {
                offenseAvailable = true;
            }
        }
        if (!offenseAvailable && inArray(weapsNow, WEAPON_DESTROYER)) {
            if (distNow >= 1 && distNow <= 6 && lineOfSight(curCell, targetEnemyCell)) {
                offenseAvailable = true;
            }
        }
        // Poison chips as fallback offense
        var chipsNow = chips;
        if (!offenseAvailable && inArray(chipsNow, CHIP_TOXIN) && chipCooldowns[CHIP_TOXIN] <= 0) {
            if (distNow <= 7 && isChipSafeToUse(CHIP_TOXIN, targetEnemyCell)) {
                offenseAvailable = true;
            }
        }
        if (!offenseAvailable && inArray(chipsNow, CHIP_VENOM) && chipCooldowns[CHIP_VENOM] <= 0) {
            if (distNow <= 10) {
                offenseAvailable = true;
            }
        }
    }

    // Only add healing if: critically low HP OR (no offense available and safe)
    if ((hpPercent < 0.35) || (!offenseAvailable && safeDistance && healingPriority >= 20 && hpPercent < 0.60)) {
        debugW("MAGIC HEALING SCENARIOS: Adding healing options, HP=" + floor(hpPercent * 100) + "%, Priority=" + healingPriority + ", offenseAvailable=" + offenseAvailable);

        // Critical healing: REGENERATION (once per fight)
        if (hpPercent < 0.35 && !regenerationUsed && inArray(chips, CHIP_REGENERATION)) {
            push(scenarios, {tp: 8, actions: [CHIP_REGENERATION]});
            debugW("MAGIC HEALING: Added REGENERATION scenario for critical HP");
        }

        // Moderate healing: REMISSION (repeatable, 1 turn CD)
        if (hpPercent < 0.50 && isDefensiveChipAvailable(CHIP_REMISSION) && inArray(chips, CHIP_REMISSION)) {
            push(scenarios, {tp: 5, actions: [CHIP_REMISSION]});
            debugW("MAGIC HEALING: Added REMISSION scenario for moderate HP");
        }

        // Sustained healing: VACCINE (HoT, 4 turn CD) — only below 45%
        if (hpPercent < 0.45 && isDefensiveChipAvailable(CHIP_VACCINE) && inArray(chips, CHIP_VACCINE)) {
            push(scenarios, {tp: 6, actions: [CHIP_VACCINE]});
            debugW("MAGIC HEALING: Added VACCINE scenario for sustained healing");
        }

        // Combo healing scenarios for high TP situations
        if (hpPercent < 0.40) {
            // Critical combo: REGENERATION + REMISSION (once per fight)
            if (!regenerationUsed && isDefensiveChipAvailable(CHIP_REMISSION) &&
                inArray(chips, CHIP_REGENERATION) && inArray(chips, CHIP_REMISSION)) {
                push(scenarios, {tp: 13, actions: [CHIP_REGENERATION, CHIP_REMISSION]});
                debugW("MAGIC HEALING: Added REGENERATION + REMISSION combo for critical HP");
            }

            // Sustain combo: REMISSION + VACCINE combo for sustained healing
            if (isDefensiveChipAvailable(CHIP_REMISSION) && isDefensiveChipAvailable(CHIP_VACCINE) &&
                inArray(chips, CHIP_REMISSION) && inArray(chips, CHIP_VACCINE)) {
                push(scenarios, {tp: 11, actions: [CHIP_REMISSION, CHIP_VACCINE]});
                debugW("MAGIC HEALING: Added REMISSION + VACCINE combo for sustained healing");
            }
        }
    }

    debugW("MAGIC SCENARIOS: Built " + count(scenarios) + " dynamic scenarios (combat + healing)");
    
    // Find first scenario that fits available TP and has required items equipped
    for (var i = 0; i < count(scenarios); i++) {
        var scenario = scenarios[i];
        if (scenario.tp <= tpLeft + switchCost) {
            // Count FLAME_THROWER uses in this scenario
            var flamethrowerUsesInScenario = 0;
            for (var j = 0; j < count(scenario.actions); j++) {
                if (scenario.actions[j] == WEAPON_FLAME_THROWER) {
                    flamethrowerUsesInScenario++;
                }
            }
            
            // Skip scenario if it would exceed FLAME_THROWER use limit
            if (flamethrowerUsesInScenario > maxNewFlamethrowerUses) {
                debugW("MAGIC FUNC: Skipping scenario " + join(scenario.actions, "+") + " - needs " + flamethrowerUsesInScenario + " FLAME_THROWER uses, only " + maxNewFlamethrowerUses + " remaining");
                continue;
            }
            
            // Check if all required items are available
            var canExecute = true;
            for (var j = 0; j < count(scenario.actions); j++) {
                var action = scenario.actions[j];
                if (action >= CHIP_LIGHTNING) { // It's a chip
                    if (!inArray(chips, action)) {
                        canExecute = false;
                        break;
                    }
                } else { // It's a weapon
                    if (!inArray(weapons, action)) {
                        canExecute = false;
                        break;
                    }
                }
            }
            
            if (canExecute) {
                if (debugEnabled) {
                    var head = (count(scenario.actions) > 0) ? scenario.actions[0] : -1;
                    debugW("MAGIC BUILD: Selected scenario [" + join(scenario.actions, ", ") + "] (head=" + head + ", TP=" + scenario.tp + ")");
                }
                return scenario.actions;
            }
        }
    }
    
    return null;
}

// Build a scenario for a specific weapon with available TP and chips
function buildScenarioForWeapon(weapon, availableTP, chips, distance, forCombat) {
    var cost = getWeaponCost(weapon);
    var minRange = getWeaponMinRange(weapon);
    var maxRange = getWeaponMaxRange(weapon);
    
    // Check basic validity
    if (cost > availableTP) return null;
    
    // Account for weapon switching cost if needed
    var switchCost = (getWeapon() != weapon) ? 1 : 0;
    if (cost + switchCost > availableTP) return null;
    
    // If building scenario for immediate combat, validate weapon availability
    if (forCombat == true) {
        // Only validate that we have a target - range validation happens during movement
        var targetCell = (primaryTarget != null) ? getCell(primaryTarget) : null;
        if (targetCell == null) return null;
    }
    
    // Build scenario
    var scenario = [];
    var tpLeft = availableTP - switchCost; // Reserve TP for weapon switch
    var maxUses = getWeaponMaxUses(weapon);
    var uses = 0;
    
    // Add weapon uses
    while (tpLeft >= cost && (maxUses == 0 || uses < maxUses)) {
        push(scenario, weapon);
        tpLeft -= cost;
        uses++;
    }
    
    // Add best chip if TP remaining
    if (tpLeft >= 3) {
        var bestChip = selectBestChip(chips, tpLeft, weapon, distance);
        if (bestChip != null) {
            push(scenario, bestChip);
        }
    }
    
    return count(scenario) > 0 ? scenario : null;
}

// Calculate relative value of a scenario for comparison
function calculateScenarioValue(scenario, primaryWeapon) {
    var value = 0;
    
    // Base value on weapon type and count
    for (var i = 0; i < count(scenario); i++) {
        var action = scenario[i];
        
        if (action == primaryWeapon) {
            // Weapon use - base value on damage potential
            if (action == WEAPON_RHINO) value += 150; // High DPS, low cost
            else if (action == WEAPON_M_LASER) value += 140; // Efficient damage
            else if (action == WEAPON_ENHANCED_LIGHTNINGER) value += 120; // Damage + heal
            else if (action == WEAPON_RIFLE) value += 110; // Reliable mid-range
            else if (action == WEAPON_FLAME_THROWER) value += 130; // DoT potential
            else if (action == WEAPON_DESTROYER) value += 100; // Debuff value
            else if (action == WEAPON_ELECTRISOR) value += 115; // AoE damage
            else if (action == WEAPON_KATANA) value += 125; // High single damage
            else if (action == WEAPON_SWORD) value += 90; // Cheap melee
            else if (action == WEAPON_B_LASER) value += 85; // Cheap line weapon
            else if (action == WEAPON_GRENADE_LAUNCHER) value += 95; // AoE
            else if (action == WEAPON_NEUTRINO) value += 80; // Diagonal specialist
            else value += 70; // Unknown weapon
        } else {
            // Chip use - add chip value
            if (action == CHIP_TOXIN) value += 60; // AoE poison
            else if (action == CHIP_LIGHTNING) value += 50; // High damage
            else if (action == CHIP_METEORITE) value += 55; // Good damage
            else if (action == CHIP_VENOM) value += 40; // Single poison
            else if (action == CHIP_SPARK) value += 30; // Cheap damage
            else value += 25; // Other chips
        }
    }
    
    // Magic build bonuses
    if (isMagicBuild) {
        if (primaryWeapon == WEAPON_FLAME_THROWER) value += 50; // DoT priority
        if (primaryWeapon == WEAPON_DESTROYER) value += 30; // Debuff priority
        // Bonus for poison chips in magic builds
        for (var i = 0; i < count(scenario); i++) {
            if (scenario[i] == CHIP_TOXIN || scenario[i] == CHIP_VENOM) {
                value += 20;
            }
        }
    }
    
    return value;
}

// Select the best chip for remaining TP
function selectBestChip(chips, tpLeft, primaryWeapon, targetDistance) {
    if (chips == null || count(chips) == 0) return null;
    
    // Chip priority list with costs
    var chipPriority = [
        {id: CHIP_TOXIN, cost: 5, priority: isMagicBuild ? 100 : 70},
        {id: CHIP_LIGHTNING, cost: 4, priority: 80},
        {id: CHIP_METEORITE, cost: 5, priority: 75},
        {id: CHIP_VENOM, cost: 4, priority: isMagicBuild ? 85 : 60},
        {id: CHIP_ICEBERG, cost: 3, priority: 50},
        {id: CHIP_SPARK, cost: 3, priority: 40},
        {id: CHIP_BURNING, cost: 2, priority: 30},
        {id: CHIP_ROCKFALL, cost: 4, priority: 65}
    ];
    
    // Special synergies
    if (primaryWeapon == WEAPON_FLAME_THROWER) {
        // FLAME_THROWER + poison synergy
        for (var i = 0; i < count(chipPriority); i++) {
            if (chipPriority[i].id == CHIP_TOXIN || chipPriority[i].id == CHIP_VENOM) {
                chipPriority[i].priority += 30;
            }
        }
    }
    
    // Find best affordable chip
    var bestChip = null;
    var bestPriority = 0;
    
    for (var i = 0; i < count(chipPriority); i++) {
        var chip = chipPriority[i];
        if (inArray(chips, chip.id) && chip.cost <= tpLeft && chip.priority > bestPriority) {
            // Validate chip range if targetDistance provided
            if (targetDistance != null) {
                var chipMinRange = getChipMinRange(chip.id);
                var chipMaxRange = getChipMaxRange(chip.id);
                if (targetDistance < chipMinRange || targetDistance > chipMaxRange) {
                    // Chip range invalid for distance
                    continue; // Skip this chip
                }
            }
            
            bestPriority = chip.priority;
            bestChip = chip.id;
        }
    }
    
    return bestChip;
}

// Chip-only scenario when no weapons work
function getChipOnlyScenario(chips, tp, targetDistance) {
    if (chips == null || count(chips) == 0) return [CHIP_LIGHTNING];
    
    var scenario = [];
    var tpLeft = tp;
    var usedChips = []; // Track chips already used in this scenario
    
    // Try to use multiple chips if possible, but only once each per scenario
    var bestChip = selectBestChip(chips, tpLeft, null, targetDistance);
    while (bestChip != null && tpLeft >= 3) {
        // Check if we've already used this chip in this scenario
        var alreadyUsed = false;
        for (var i = 0; i < count(usedChips); i++) {
            if (usedChips[i] == bestChip) {
                alreadyUsed = true;
                break;
            }
        }
        
        if (alreadyUsed) {
            // Find next best chip that hasn't been used
            var foundDifferentChip = false;
            for (var j = 0; j < count(chips); j++) {
                var candidateChip = chips[j];
                var candidateCost = getChipCost(candidateChip);
                if (candidateCost <= tpLeft) {
                    var candidateUsed = false;
                    for (var k = 0; k < count(usedChips); k++) {
                        if (usedChips[k] == candidateChip) {
                            candidateUsed = true;
                            break;
                        }
                    }
                    if (!candidateUsed) {
                        bestChip = candidateChip;
                        foundDifferentChip = true;
                        break;
                    }
                }
            }
            if (!foundDifferentChip) {
                break; // No more unique chips available
            }
        }
        
        push(scenario, bestChip);
        push(usedChips, bestChip);
        var chipCost = getChipCost(bestChip);
        tpLeft -= chipCost;
        
        // Try to add another chip
        if (tpLeft >= 3) {
            bestChip = selectBestChip(chips, tpLeft, null, targetDistance);
        } else {
            break;
        }
    }
    
    return count(scenario) > 0 ? scenario : [CHIP_LIGHTNING];
}

// Helper functions
function checkLineAlignment(fromCell, toCell) {
    var fromX = getCellX(fromCell);
    var fromY = getCellY(fromCell);
    var toX = getCellX(toCell);
    var toY = getCellY(toCell);
    
    return (fromX == toX) != (fromY == toY); // Exactly one axis aligned
}

function checkDiagonalAlignment(fromCell, toCell) {
    var fromX = getCellX(fromCell);
    var fromY = getCellY(fromCell);
    var toX = getCellX(toCell);
    var toY = getCellY(toCell);
    
    var dx = abs(toX - fromX);
    var dy = abs(toY - fromY);
    
    return dx == dy && dx > 0; // Perfect diagonal
}

function getChipCost(chip) {
    if (chip == CHIP_LIGHTNING) return 4;
    if (chip == CHIP_SPARK) return 3;
    if (chip == CHIP_METEORITE) return 5;
    if (chip == CHIP_TOXIN) return 5;
    if (chip == CHIP_VENOM) return 4;
    if (chip == CHIP_BURNING) return 2;
    if (chip == CHIP_ROCKFALL) return 4;
    if (chip == CHIP_ICEBERG) return 3;
    return 3; // Default cost
}

// === SCENARIO EXECUTABILITY VALIDATION ===
function validateScenarioExecutability(scenario, targetEnemyCell) {
    if (scenario == null || count(scenario) == 0) return false;
    if (targetEnemyCell == null) return false;
    
    var currentCell = getCell();
    var currentDistance = getCellDistance(currentCell, targetEnemyCell);
    var scenarioWeaponUses = [:]; // Track weapon usage in this scenario
    
    for (var i = 0; i < count(scenario); i++) {
        var action = scenario[i];
        
        if (isWeapon(action)) {
            // Check weapon range
            var minRange = getWeaponMinRange(action);
            var maxRange = getWeaponMaxRange(action);
            if (currentDistance < minRange || currentDistance > maxRange) {
                debugW("VALIDATION FAIL: Weapon " + action + " range " + minRange + "-" + maxRange + " invalid for distance " + currentDistance);
                return false;
            }
            
            // Check weapon alignment based on launch type
            var launchType = getWeaponLaunchType(action);
            if (launchType == LAUNCH_TYPE_LINE || launchType == LAUNCH_TYPE_LINE_INVERTED) {
                var fromX = getCellX(currentCell);
                var fromY = getCellY(currentCell);
                var targetX = getCellX(targetEnemyCell);
                var targetY = getCellY(targetEnemyCell);
                var dx = targetX - fromX;
                var dy = targetY - fromY;
                var aligned = (dx == 0) || (dy == 0); // Line weapons require X OR Y axis alignment
                if (!aligned) {
                    debugW("VALIDATION FAIL: Line weapon " + action + " not aligned (dx=" + dx + ", dy=" + dy + ")");
                    return false;
                }
            } else if (launchType == LAUNCH_TYPE_DIAGONAL || launchType == LAUNCH_TYPE_DIAGONAL_INVERTED) {
                var fromX = getCellX(currentCell);
                var fromY = getCellY(currentCell);
                var targetX = getCellX(targetEnemyCell);
                var targetY = getCellY(targetEnemyCell);
                var dx = abs(targetX - fromX);
                var dy = abs(targetY - fromY);
                var aligned = (dx == dy && dx > 0); // Diagonal weapons require perfect diagonal alignment
                if (!aligned) {
                    debugW("VALIDATION FAIL: Diagonal weapon " + action + " not aligned (dx=" + dx + ", dy=" + dy + ")");
                    return false;
                }
            } else if (launchType == LAUNCH_TYPE_STAR || launchType == LAUNCH_TYPE_STAR_INVERTED) {
                var fromX = getCellX(currentCell);
                var fromY = getCellY(currentCell);
                var targetX = getCellX(targetEnemyCell);
                var targetY = getCellY(targetEnemyCell);
                var dx = targetX - fromX;
                var dy = targetY - fromY;
                var lineAligned = (dx == 0) || (dy == 0);
                var diagAligned = (abs(dx) == abs(dy) && dx != 0);
                var aligned = lineAligned || diagAligned; // Star pattern: line OR diagonal
                if (!aligned) {
                    debugW("VALIDATION FAIL: Star weapon " + action + " not aligned (dx=" + dx + ", dy=" + dy + ")");
                    return false;
                }
            }
            // LAUNCH_TYPE_CIRCLE weapons don't require alignment validation
            
            // Check weapon usage limits using built-in function
            var maxUses = getWeaponMaxUses(action);
            if (maxUses > 0) { // Only check if there's a limit (-1 means unlimited)
                var currentUses = scenarioWeaponUses[action];
                if (currentUses == null) currentUses = 0;
                currentUses++;
                if (currentUses > maxUses) {
                    debugW("VALIDATION FAIL: Weapon " + action + " exceeds max uses " + maxUses + " (attempt " + currentUses + ")");
                    return false;
                }
                scenarioWeaponUses[action] = currentUses;
            }
            
        } else if (isChip(action)) {
            // Check chip range
            var chipMinRange = getChipMinRange(action);
            var chipMaxRange = getChipMaxRange(action);
            if (currentDistance < chipMinRange || currentDistance > chipMaxRange) {
                debugW("VALIDATION FAIL: Chip " + action + " range " + chipMinRange + "-" + chipMaxRange + " invalid for distance " + currentDistance);
                return false;
            }
            
            // Check chip cooldowns
            if (action == CHIP_TOXIN && chipCooldowns[CHIP_TOXIN] > 0) {
                // CHIP_TOXIN on cooldown
                return false;
            }
            if (action == CHIP_VENOM && chipCooldowns[CHIP_VENOM] > 0) {
                // CHIP_VENOM on cooldown
                return false;
            }
            if (action == CHIP_LIBERATION && chipCooldowns[CHIP_LIBERATION] > 0) {
                // CHIP_LIBERATION on cooldown
                return false;
            }
            if (action == CHIP_ANTIDOTE && chipCooldowns[CHIP_ANTIDOTE] > 0) {
                // CHIP_ANTIDOTE on cooldown
                return false;
            }
        }
    }
    
    return true; // All validations passed
}

// === DEFENSIVE CHIP SELECTION LOGIC ===

// Determine if we should use a defensive chip based on current effects
function shouldUseDefensiveChip() {
    var priority = getDefensivePriority();
    debugW("DEFENSIVE CHECK: Priority=" + priority + ", TP=" + myTP);

    // Critical priority (100+) = immediate defensive action required
    if (priority >= 100) {
        debugW("DEFENSIVE: Critical priority " + priority + " - immediate action needed");
        return true;
    }

    // High priority (50+) = strongly consider defensive action
    if (priority >= 50 && myTP >= 5) {
        debugW("DEFENSIVE: High priority " + priority + " - defensive action recommended");
        return true;
    }

    // Medium priority (20+) = consider if we have spare TP
    if (priority >= 20 && myTP >= 8) {
        debugW("DEFENSIVE: Medium priority " + priority + " - defensive action if TP allows");
        return true;
    }

    debugW("DEFENSIVE: Low priority " + priority + " - no defensive action needed");
    return false;
}

// Get the best defensive scenario based on our current effects and available TP
function getDefensiveScenario(tp, chips) {
    if (!shouldUseDefensiveChip()) {
        return null;
    }

    var poisonDamage = calculatePoisonDamage();
    var hasPoison = (poisonDamage > 0);
    var hasDebuffs = (calculateDebuffImpact() > 20);
    var hasNegative = hasNegativeEffects();

    // Priority 1: ANTIDOTE for poison (especially critical HP situations)
    if (hasPoison && isDefensiveChipAvailable(CHIP_ANTIDOTE) && inArray(chips, CHIP_ANTIDOTE)) {
        debugW("DEFENSIVE SCENARIO: Poison detected, trying ANTIDOTE scenarios");
        for (var tpAmount = tp; tpAmount >= 3; tpAmount--) {
            if (ANTIDOTE_SCENARIOS[tpAmount] != null) {
                debugW("DEFENSIVE SCENARIO: Selected ANTIDOTE scenario for " + tpAmount + " TP: [" + join(ANTIDOTE_SCENARIOS[tpAmount], ", ") + "]");
                return ANTIDOTE_SCENARIOS[tpAmount];
            }
        }
    }

    // Priority 2: LIBERATION for debuffs or when ANTIDOTE not available
    if ((hasDebuffs || hasNegative) && isDefensiveChipAvailable(CHIP_LIBERATION) && inArray(chips, CHIP_LIBERATION)) {
        debugW("DEFENSIVE SCENARIO: Debuffs detected, trying LIBERATION scenarios");
        for (var tpAmount = tp; tpAmount >= 5; tpAmount--) {
            if (LIBERATION_SCENARIOS[tpAmount] != null) {
                debugW("DEFENSIVE SCENARIO: Selected LIBERATION scenario for " + tpAmount + " TP: [" + join(LIBERATION_SCENARIOS[tpAmount], ", ") + "]");
                return LIBERATION_SCENARIOS[tpAmount];
            }
        }
    }

    // Priority 3: Offensive LIBERATION against enemy buffs (if we have spare TP)
    if (tp >= 8 && isDefensiveChipAvailable(CHIP_LIBERATION) && inArray(chips, CHIP_LIBERATION)) {
        var enemies = getEnemies();
        for (var i = 0; i < count(enemies); i++) {
            var currentEnemy = enemies[i];
            if (getLife(currentEnemy) > 0 && hasRemovableBuffs(currentEnemy)) {
                debugW("DEFENSIVE SCENARIO: Enemy " + currentEnemy + " has removable buffs, using offensive LIBERATION");
                return LIBERATION_SCENARIOS[tp >= 8 ? 8 : 5];
            }
        }
    }

    debugW("DEFENSIVE SCENARIO: No appropriate defensive scenario found");
    return null;
}

// Calculate value of defensive scenario for comparison with offensive scenarios
function calculateDefensiveScenarioValue(scenario) {
    if (scenario == null) return 0;

    var value = 0;
    var priority = getDefensivePriority();

    // Base value from priority
    value += priority * 2; // High priority defensive actions are very valuable

    // Bonus for specific defensive actions
    for (var i = 0; i < count(scenario); i++) {
        if (scenario[i] == CHIP_ANTIDOTE) {
            var poisonDamage = calculatePoisonDamage();
            value += poisonDamage; // Preventing poison damage
            value += 30; // Healing bonus
        } else if (scenario[i] == CHIP_LIBERATION) {
            var debuffImpact = calculateDebuffImpact();
            value += debuffImpact; // Restoring combat effectiveness
        } else {
            // Damage chips in defensive scenarios
            value += 50; // Standard damage chip value
        }
    }

    debugW("DEFENSIVE VALUE: Scenario [" + join(scenario, ", ") + "] has value " + value);
    return value;
}

// === AoE SELF-DAMAGE VALIDATION ===

// Check if using an AoE chip would damage ourselves
function isChipSafeToUse(chip, targetEnemyCell) {
    if (targetEnemyCell == null) {
        debugW("AOE SAFETY: No target cell provided, assuming safe");
        return true;
    }

    // Get chip area - this determines the AoE size
    var chipArea = getChipArea(chip);
    if (chipArea == null || chipArea <= 0) {
        debugW("AOE SAFETY: Chip " + chip + " has no AoE (area=" + chipArea + "), safe to use");
        return true; // Non-AoE chip
    }

    var myCurrentCell = getCell();
    var distanceToTarget = getCellDistance(myCurrentCell, targetEnemyCell);

    debugW("AOE SAFETY CHECK: Chip " + chip + " area=" + chipArea + ", distance to target=" + distanceToTarget);

    // CHIP_TOXIN has area effect - check if we'd be caught in the blast
    // AoE area affects cells around the target
    if (chip == CHIP_TOXIN) {
        // TOXIN affects cells within its area around the target
        // If we're too close to the target, we'll poison ourselves
        var safeDistance = chipArea + 1; // Need to be outside the AoE radius

        if (distanceToTarget <= chipArea) {
            debugW("AOE DANGER: TOXIN would hit self - distance " + distanceToTarget + " <= AoE area " + chipArea);
            return false;
        } else {
            debugW("AOE SAFE: TOXIN safe to use - distance " + distanceToTarget + " > AoE area " + chipArea);
            return true;
        }
    }

    // For other AoE chips, add similar logic here
    if (chip == CHIP_METEORITE || chip == CHIP_ICEBERG) {
        // These also have AoE effects, check similarly
        if (distanceToTarget <= chipArea) {
            debugW("AOE DANGER: Chip " + chip + " would hit self - distance " + distanceToTarget + " <= AoE area " + chipArea);
            return false;
        }
    }

    debugW("AOE SAFE: Chip " + chip + " safe to use");
    return true;
}
