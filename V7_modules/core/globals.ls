// V7 Module: core/globals.ls
// Minimal global state - streamlined for maximum performance

// === MAP CONSTANTS ===
global MAP_WIDTH = 17;   // LeekWars map width in cells
global MAP_HEIGHT = 17;  // LeekWars map height in cells

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

// === BUILD TYPE DETECTION ===
global isMagicBuild = false;         // True when magic > strength
global isHighMagicBuild = false;     // True when magic > strength * 2
global isAgilityBuild = false;       // True when agility > strength && agility > magic
global isStrengthBuild = false;      // True when strength > magic && strength > agility
global isWisdomBuild = false;        // True when wisdom > strength && wisdom > magic
global isBalancedBuild = false;      // True when no stat is clearly dominant

// === CHIP_MIRROR TRACKING ===
global mirrorActive = false;         // True when CHIP_MIRROR effect is active
global mirrorRemainingTurns = 0;     // Remaining turns for CHIP_MIRROR effect
global mirrorMinTPReserve = 0;       // Build-specific TP reserve for core strategies

// === WEAPON USAGE TRACKING ===
global weaponUsesThisTurn = [:];     // Map[weaponId -> usesCount] tracks uses per turn

// === HEALING CHIP TRACKING ===
global regenerationUsed = false;     // Once per fight flag for CHIP_REGENERATION
global vaccineHoTTurnsLeft = 0;     // Remaining turns for VACCINE heal over time

// === DoT CYCLE TRACKING ===
global lastDoTApplicationTurn = 0;   // Turn when we last applied DoT
global enemyDoTRemainingTurns = 0;   // Enemy's remaining DoT turns
global shouldReturnForDoT = false;   // Flag to return and reapply DoT

// === PROGRESS TRACKING ===

// === MULTI-ENEMY TRACKING ===
global allEnemies = [];             // Array of all alive enemy entities
global enemyData = [:];             // Map[enemyId -> {cell, hp, maxHp, ttk, priority, threat}]

// === STALEMATE DETECTION ===
global lastDistanceToEnemy = -1;    // Distance to primary enemy last turn
global lastTurnAttacked = 0;        // Last turn we successfully attacked
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
global currentWeaponDamageArray = []; // Separated: weapon-only damage zones
global currentChipDamageArray = [];   // Separated: chip-only damage zones
global damageArrayTurn = -1;        // Turn number when currentDamageArray was computed
global currentTarget = null;        // Current enemy target (legacy)
global emergencyMode = false;       // Panic mode flag
global debugEnabled = false;        // Debug output control - DISABLED for production (only errors/issues)
global sparkUsesThisTurn = 0;       // Limit SPARK spam per turn

// === CONSTANTS ===
global EMERGENCY_HP_THRESHOLD = 0.25;  // Enter emergency mode below 25% HP
global PEEK_COVER_BONUS = 0.1;         // 10% damage bonus per adjacent cover
global MAX_PATHFIND_CELLS = 20;        // Limit A* search to top 20 damage cells

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
// Note: Using built-in LeekScript constants - no need to redefine
// WEAPON_ENHANCED_LIGHTNINGER, WEAPON_RIFLE, WEAPON_M_LASER, WEAPON_KATANA, etc.
// are already available as built-in constants

// === CACHING ===
global pathCache = [:];             // Simple path caching
global losCache = [:];              // Line of sight cache
// Removed weapon tracking to avoid LeekScript variable conflicts
global weaponSwitchCache = [:];     // Cache weapon compatibility checks
global eidCache = [:];              // Cache EID per cell for this turn

// === TERRAIN LOS (PERSISTENT ACROSS TURNS) ===
global terrainLOS = [:];            // Map[start -> Map[end -> 0/1]]; upper-triangle storage
global terrainLOSDone = false;      // True when full precompute finished
global terrainLOSI = 0;             // Progress pointer (row)
global terrainLOSJ = 1;             // Progress pointer (col)
global LOS_PRECOMP_PAIRS_PER_TURN = 65000; // Process all pairs within ~3 turns (~2.0M ops/turn)

// === PATHFINDING BUDGETS ===
global PATH_ASTAR_BUDGET_DEFAULT = 60;     // Max A* calls per turn after LOS precompute
global PATH_ASTAR_BUDGET_DURING_LOS = 20;  // Max A* calls per turn while LOS is building
global aStarCallsThisTurn = 0;             // Counter reset each turn

// === CHIP COOLDOWN TRACKING ===
global chipCooldowns = [:];         // Map[chipId -> turnsRemaining]
global lastChipUse = [:];          // Map[chipId -> turnUsed]

// === INITIALIZATION ===
function updateGameState() {
    myLeek = getEntity();
    myCell = getCell();

    // Reset terrain LOS precompute at the start of each fight
    if (getTurn() == 1) {
        terrainLOS = [:];
        terrainLOSDone = false;
        terrainLOSI = 0;
        terrainLOSJ = 1;

    }
    
    // CRITICAL FIX: Validate our own position is within bounds
    if (myCell < 0 || myCell > 612) {
        debugW("CRITICAL BUG: Our position " + myCell + " is invalid (out of bounds 0-612)");
        debugW("CRITICAL BUG: This suggests fundamental LeekScript API issue");
        // Use a safe fallback position 
        myCell = 300; // Safe position near center
        debugW("CRITICAL FIX: Corrected our position to " + myCell);
    }
    
    // Initialize weapon usage tracking for new turn
    initWeaponUsageTracking();
    sparkUsesThisTurn = 0; // reset SPARK usage counter
    
    // CRITICAL DEBUG: Verify we got our own position
    debugW("GAME STATE: Our entity=" + myLeek + ", our cell=" + myCell);
    
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
    
    // Update comprehensive build detection
    isMagicBuild = myMagic > myStrength;
    isHighMagicBuild = myMagic > myStrength * 2.0;
    isAgilityBuild = myAgility > myStrength && myAgility > myMagic;
    isStrengthBuild = myStrength > myMagic && myStrength > myAgility;
    isWisdomBuild = myWisdom > myStrength && myWisdom > myMagic;
    isBalancedBuild = !isMagicBuild && !isAgilityBuild && !isStrengthBuild && !isWisdomBuild;

    // Set minimum TP reserve based on build type for CHIP_MIRROR decisions
    if (isMagicBuild) {
        mirrorMinTPReserve = 17;  // Reserve for FLAME+FLAME+TOXIN combo
    } else if (isStrengthBuild) {
        mirrorMinTPReserve = 7;   // Reserve for weapon attack
    } else if (isWisdomBuild) {
        mirrorMinTPReserve = 5;   // Reserve for healing chips
    } else if (isAgilityBuild) {
        mirrorMinTPReserve = 0;   // No reserve, mirror is highest priority
    } else {
        mirrorMinTPReserve = 6;   // Balanced builds reserve for basic attack
    }

    // CRITICAL DEBUG: Always log build status
    debugW("BUILD DETECTION: STR=" + myStrength + ", MAG=" + myMagic + ", AGI=" + myAgility + ", WIS=" + myWisdom);
    var buildType = isAgilityBuild ? "AGILITY" : isMagicBuild ? "MAGIC" : isStrengthBuild ? "STRENGTH" : isWisdomBuild ? "WISDOM" : "BALANCED";
    debugW("BUILD TYPE: " + buildType + " (TP reserve for MIRROR: " + mirrorMinTPReserve + ")");
    if (isMagicBuild) {
        debugW("MAGIC BUILD: Will prioritize DoT/debuff weapons");
    } else if (isAgilityBuild) {
        // Agility build - prioritizing CHIP_MIRROR
    } else if (isStrengthBuild) {
        debugW("STRENGTH BUILD: Will prioritize damage weapons");
    } else if (isWisdomBuild) {
        debugW("WISDOM BUILD: Will prioritize healing and support");
    } else {
        debugW("BALANCED BUILD: Using standard priorities");
    }
    
    // Update all enemies data
    allEnemies = getAliveEnemies();
    enemyData = [:]; // Clear previous data
    
    if (count(allEnemies) > 0) {
        // Track all enemies
        for (var i = 0; i < count(allEnemies); i++) {
            var enemyEntity = allEnemies[i];
            debugW("ENEMY RETRIEVAL: Getting position for enemy entity " + enemyEntity);
            var enemyEntityCell = getCell(enemyEntity);
            debugW("ENEMY POSITION: Enemy " + enemyEntity + " is at cell " + enemyEntityCell);
            
            // CRITICAL DEBUG: Check if enemy position equals our position
            if (enemyEntityCell == myCell) {
                debugW("CRITICAL BUG: Enemy " + enemyEntity + " position " + enemyEntityCell + " equals our position " + myCell);
                debugW("BUG DEBUG: This suggests getCell() is returning wrong data or there's a variable mix-up");
                debugW("BUG DEBUG: Our entity=" + myLeek + ", enemy entity=" + enemyEntity);
                debugW("BUG DEBUG: Re-checking positions - myCell=getCell()=" + getCell() + ", enemyCell=getCell(" + enemyEntity + ")=" + getCell(enemyEntity));
                
                // SAFETY FIX: Skip this enemy to prevent calculating zones around ourselves
                debugW("SAFETY FIX: Skipping enemy " + enemyEntity + " to prevent zone calculation around our position");
                continue;
            }
            
            // Validate enemy cell is within map bounds
            if (enemyEntityCell < 0 || enemyEntityCell > 612) {
                debugW("WARNING: Enemy " + enemyEntity + " has invalid cell " + enemyEntityCell + " (out of bounds 0-612)");
                // Use a safe default cell that is DIFFERENT from our position
                var fallbackCell = 306; // Center of larger map
                if (fallbackCell == myCell) {
                    fallbackCell = 400; // Alternative safe position 
                }
                enemyEntityCell = fallbackCell;
                debugW("WARNING: Corrected enemy cell to safe position " + enemyEntityCell + " (avoiding our position " + myCell + ")");
            }
            
            debugW("ENEMY SETUP: Entity " + enemyEntity + " at cell " + enemyEntityCell + " (we are at " + myCell + ")");
            
            enemyData[enemyEntity] = {
                entity: enemyEntity,
                cell: enemyEntityCell,
                hp: getLife(enemyEntity),
                maxHp: getTotalLife(enemyEntity),
                tp: getTP(enemyEntity),
                mp: getMP(enemyEntity),
                strength: getStrength(enemyEntity),
                agility: getAgility(enemyEntity),
                resistance: getResistance(enemyEntity),
                distance: getCellDistance(myCell, enemyEntityCell),
                ttk: 0, // Will be calculated by targeting system
                priority: 0, // Will be calculated by targeting system
                threat: 0 // Will be calculated by targeting system
            };
        }
        
        // Maintain backward compatibility with single-enemy variables
        if (primaryTarget == null || getLife(primaryTarget) <= 0) {
            primaryTarget = allEnemies[0]; // Default to first enemy
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
    if (chipCooldowns[CHIP_STALACTITE] != null && chipCooldowns[CHIP_STALACTITE] > 0) {
        chipCooldowns[CHIP_STALACTITE]--;
    }

    // Update healing chip cooldowns
    if (chipCooldowns[CHIP_VACCINE] != null && chipCooldowns[CHIP_VACCINE] > 0) {
        chipCooldowns[CHIP_VACCINE]--;
    }
    if (chipCooldowns[CHIP_REMISSION] != null && chipCooldowns[CHIP_REMISSION] > 0) {
        chipCooldowns[CHIP_REMISSION]--;
    }

    // Update VACCINE heal over time
    if (vaccineHoTTurnsLeft > 0) {
        vaccineHoTTurnsLeft--;
        if (vaccineHoTTurnsLeft > 0) {
            debugW("VACCINE HoT: " + vaccineHoTTurnsLeft + " turns remaining");
        }
    }

    // Update DoT cycle tracking
    updateDoTTracking();


    // Reset per-turn pathfinding budget
    aStarCallsThisTurn = 0;
    if (chipCooldowns[CHIP_LIBERATION] != null && chipCooldowns[CHIP_LIBERATION] > 0) {
        chipCooldowns[CHIP_LIBERATION]--;
    }
    if (chipCooldowns[CHIP_ANTIDOTE] != null && chipCooldowns[CHIP_ANTIDOTE] > 0) {
        chipCooldowns[CHIP_ANTIDOTE]--;
    }
    
    // Check emergency mode
    emergencyMode = (myHP / myMaxHP) < EMERGENCY_HP_THRESHOLD;
}

// === WEAPON UTILITY FUNCTIONS ===
// NOTE: Using LeekScript built-in APIs for dynamic weapon adaptation
// These functions now work with ANY weapon without hardcoded values

function getWeaponMaxUses(weapon) {
    // Hardcoded values for known weapons using built-in constants
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
    if (weapon == WEAPON_ELECTRISOR) return 2;
    if (weapon == WEAPON_PISTOL) return 4;
    if (weapon == WEAPON_DOUBLE_GUN) return 3; // New: Double Gun has 3 uses/turn
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
    
    // Check line of sight (cached)
    if (!checkLineOfSight(fromCell, targetCell)) {
        if (debugEnabled) {
            debugW("WEAPON REACH FAIL: No line of sight from " + fromCell + " to " + targetCell);
        }
        return false;
    }
    
    // Check alignment by launch type
    var lt = getWeaponLaunchType(weapon);
    if (lt == LAUNCH_TYPE_LINE || lt == LAUNCH_TYPE_LINE_INVERTED) {
        if (!isOnSameLine(fromCell, targetCell)) { return false; }
    } else if (lt == LAUNCH_TYPE_STAR || lt == LAUNCH_TYPE_STAR_INVERTED) {
        // Enhanced Lightninger is NOT star pattern; only enforce for regular Lightninger
        if (weapon != WEAPON_ENHANCED_LIGHTNINGER) {
            if (!isValidStarPattern(fromCell, targetCell)) { return false; }
        }
    }
    
    return true;
}

// === WEAPON USAGE TRACKING FUNCTIONS ===

// Initialize weapon usage tracking at start of turn
function initWeaponUsageTracking() {
    weaponUsesThisTurn = [:];
}

// Record a weapon use
function recordWeaponUse(weapon) {
    if (weaponUsesThisTurn[weapon] == null) {
        weaponUsesThisTurn[weapon] = 0;
    }
    weaponUsesThisTurn[weapon]++;
}

// Get remaining uses for a weapon this turn
function getRemainingWeaponUses(weapon) {
    var maxUses = getWeaponMaxUses(weapon);
    var usedThisTurn = (weaponUsesThisTurn[weapon] != null) ? weaponUsesThisTurn[weapon] : 0;
    return max(0, maxUses - usedThisTurn);
}

// === EFFECT TRACKING FUNCTIONS ===

// Check if enemy has DoT effects (poison, burning, etc)
function hasDoTEffect(enemyEntity) {
    var effects = getEffects(enemyEntity);
    for (var i = 0; i < count(effects); i++) {
        var effect = effects[i];
        var effectType = effect[0];
        // Check for damage over time effects
        if (effectType == EFFECT_POISON) {
            return true;
        }
    }
    return false;
}

// Check if enemy has strength debuff
function hasStrengthDebuff(enemyEntity) {
    var effects = getEffects(enemyEntity);
    for (var i = 0; i < count(effects); i++) {
        var effect = effects[i];
        var effectType = effect[0];
        var effectValue = effect[1];
        // Check for negative strength effects (debuffs have negative values)
        if (effectType == EFFECT_BUFF_STRENGTH && effectValue < 0) {
            return true;
        }
    }
    return false;
}

// Get remaining turns of DoT effects
function getDoTRemainingTurns(enemyEntity) {
    var effects = getEffects(enemyEntity);
    var maxTurns = 0;
    for (var i = 0; i < count(effects); i++) {
        var effect = effects[i];
        var effectType = effect[0];
        var turns = effect[3];
        if (effectType == EFFECT_POISON) {
            maxTurns = max(maxTurns, turns);
        }
    }
    return maxTurns;
}

// Get remaining turns of strength debuff
function getStrengthDebuffRemainingTurns(enemyEntity) {
    var effects = getEffects(enemyEntity);
    for (var i = 0; i < count(effects); i++) {
        var effect = effects[i];
        var effectType = effect[0];
        var effectValue = effect[1];
        var turns = effect[3];
        if (effectType == EFFECT_BUFF_STRENGTH && effectValue < 0) {
            return turns;
        }
    }
    return 0;
}

// === DEFENSIVE CHIP ANALYSIS FUNCTIONS ===

// Check if our leek has significant negative effects worth removing
function hasNegativeEffects() {
    var myEffects = getEffects();
    for (var i = 0; i < count(myEffects); i++) {
        var effect = myEffects[i];
        var effectType = effect[0];
        var effectValue = effect[1];
        var turns = effect[3];

        // Check for poison (immediate threat)
        if (effectType == EFFECT_POISON && turns > 1) {
            return true;
        }

        // Check for significant debuffs (>10 reduction)
        if ((effectType == EFFECT_SHACKLE_STRENGTH || effectType == EFFECT_SHACKLE_TP ||
             effectType == EFFECT_SHACKLE_MP || effectType == EFFECT_SHACKLE_MAGIC) &&
            abs(effectValue) > 10 && turns > 1) {
            return true;
        }

        // Check for vulnerability effects
        if ((effectType == EFFECT_VULNERABILITY || effectType == EFFECT_ABSOLUTE_VULNERABILITY) &&
            effectValue > 20 && turns > 1) {
            return true;
        }
    }
    return false;
}

// Calculate total poison damage we'll take over remaining turns
function calculatePoisonDamage() {
    var myEffects = getEffects();
    var totalDamage = 0;
    for (var i = 0; i < count(myEffects); i++) {
        var effect = myEffects[i];
        var effectType = effect[0];
        var effectValue = effect[1];
        var turns = effect[3];

        if (effectType == EFFECT_POISON) {
            totalDamage += effectValue * turns;
        }
    }
    return totalDamage;
}

// Calculate impact of debuffs on our combat effectiveness
function calculateDebuffImpact() {
    var myEffects = getEffects();
    var strengthReduction = 0;
    var tpReduction = 0;
    var mpReduction = 0;

    for (var i = 0; i < count(myEffects); i++) {
        var effect = myEffects[i];
        var effectType = effect[0];
        var effectValue = effect[1];
        var turns = effect[3];

        if (turns > 0) {
            if (effectType == EFFECT_SHACKLE_STRENGTH) {
                strengthReduction += abs(effectValue);
            } else if (effectType == EFFECT_SHACKLE_TP) {
                tpReduction += abs(effectValue);
            } else if (effectType == EFFECT_SHACKLE_MP) {
                mpReduction += abs(effectValue);
            }
        }
    }

    // Calculate combat impact: damage reduction + mobility reduction + action reduction
    var damageImpact = strengthReduction * 2; // Each strength point affects damage significantly
    var actionImpact = tpReduction * 10; // TP is very valuable
    var mobilityImpact = mpReduction * 5; // MP affects positioning

    return damageImpact + actionImpact + mobilityImpact;
}

// Check if enemy has significant buffs worth removing with LIBERATION
function hasRemovableBuffs(enemyEntity) {
    var effects = getEffects(enemyEntity);
    for (var i = 0; i < count(effects); i++) {
        var effect = effects[i];
        var effectType = effect[0];
        var effectValue = effect[1];
        var turns = effect[3];

        // Check for significant buffs (>50 shield, >15 stat buffs)
        if (turns > 1) {
            if ((effectType == EFFECT_ABSOLUTE_SHIELD || effectType == EFFECT_RELATIVE_SHIELD) &&
                effectValue > 50) {
                return true;
            }

            if ((effectType == EFFECT_BUFF_STRENGTH || effectType == EFFECT_BUFF_AGILITY ||
                 effectType == EFFECT_BUFF_TP || effectType == EFFECT_BUFF_MP) &&
                effectValue > 15) {
                return true;
            }
        }
    }
    return false;
}

// Calculate defensive priority: higher = more urgent defensive action needed
function getDefensivePriority() {
    var priority = 0;
    var hpPercent = myHP / myMaxHP;

    // Critical HP with poison = highest priority
    var poisonDamage = calculatePoisonDamage();
    if (hpPercent < 0.3 && poisonDamage > 0) {
        priority += 100; // Critical - poison will kill us
    }

    // High poison damage relative to HP
    if (poisonDamage > myHP * 0.4) {
        priority += 60; // High - significant poison threat
    }

    // Significant debuff impact
    var debuffImpact = calculateDebuffImpact();
    if (debuffImpact > 40) {
        priority += 50; // High - debuffs severely limiting combat
    }

    // Multiple effects
    if (hasNegativeEffects()) {
        priority += 20; // Medium - general negative effects
    }

    return priority;
}

// Check if defensive chip is on cooldown
function isDefensiveChipAvailable(chip) {
    return (chipCooldowns[chip] == null || chipCooldowns[chip] <= 0);
}

// === HEALING SYSTEM FUNCTIONS ===

// Calculate healing priority: higher = more urgent healing needed
function getHealingPriority() {
    var priority = 0;
    var hpPercent = myHP / myMaxHP;

    // Critical HP threshold
    if (hpPercent < 0.3) {
        priority += 100; // Critical - immediate healing needed
    } else if (hpPercent < 0.5) {
        priority += 50; // High - healing strongly recommended
    } else if (hpPercent < 0.7) {
        priority += 20; // Medium - healing beneficial
    }

    // Poison damage consideration
    var poisonDamage = calculatePoisonDamage();
    if (poisonDamage > 0) {
        if (poisonDamage > myHP * 0.3) {
            priority += 60; // Poison will kill us without healing
        } else if (poisonDamage > myHP * 0.15) {
            priority += 30; // Significant poison threat
        } else {
            priority += 10; // Minor poison damage
        }
    }

    // Distance from enemies (safer = can afford to heal)
    var avgEnemyDistance = getAverageEnemyDistance();
    if (avgEnemyDistance > 10) {
        priority += 10; // Safe to heal
    } else if (avgEnemyDistance < 5) {
        priority -= 20; // Too dangerous, might need combat instead
    }

    return priority;
}

// Get average distance to all enemies
function getAverageEnemyDistance() {
    if (count(allEnemies) == 0) return 99;

    var totalDistance = 0;
    var enemyCount = 0;

    for (var i = 0; i < count(allEnemies); i++) {
        if (getLife(allEnemies[i]) > 0) {
            var distance = getCellDistance(myCell, getCell(allEnemies[i]));
            totalDistance += distance;
            enemyCount++;
        }
    }

    return (enemyCount > 0) ? (totalDistance / enemyCount) : 99;
}

// === DoT CYCLE TRACKING FUNCTIONS ===

// Update DoT cycle tracking each turn
function updateDoTTracking() {
    if (primaryTarget != null && getLife(primaryTarget) > 0) {
        // Check enemy DoT status
        var dotTurns = getDoTRemainingTurns(primaryTarget);
        enemyDoTRemainingTurns = dotTurns;

        // Determine if we should return to apply DoT
        if (dotTurns <= 1 && dotTurns >= 0) {
            shouldReturnForDoT = true;
            if (debugEnabled) {
                debugW("DOT CYCLE: Enemy DoT expiring in " + dotTurns + " turn(s), should return to reapply");
            }
        } else if (dotTurns > 3) {
            shouldReturnForDoT = false;
            if (debugEnabled) {
                debugW("DOT CYCLE: Enemy DoT strong (" + dotTurns + " turns), can stay at distance");
            }
        }
    } else {
        shouldReturnForDoT = false;
        enemyDoTRemainingTurns = 0;
    }
}

// Check if we should use healing chip based on current situation
function shouldUseHealingChip(chip, hpThreshold) {
    var hpPercent = myHP / myMaxHP;

    // Basic HP check
    if (hpPercent > hpThreshold) return false;

    // Chip availability check
    if (chip == CHIP_REGENERATION && regenerationUsed) {
        return false; // Already used once per fight
    }

    if (chipCooldowns[chip] != null && chipCooldowns[chip] > 0) {
        return false; // On cooldown
    }

    // Safety check - don't heal if enemies very close (emergency combat needed)
    var minEnemyDistance = 99;
    for (var i = 0; i < count(allEnemies); i++) {
        if (getLife(allEnemies[i]) > 0) {
            var distance = getCellDistance(myCell, getCell(allEnemies[i]));
            if (distance < minEnemyDistance) {
                minEnemyDistance = distance;
            }
        }
    }

    // Don't heal if enemy is very close unless HP is critical
    if (minEnemyDistance < 3 && hpPercent > 0.2) {
        return false; // Too dangerous to heal
    }

    return true; // All checks passed
}

