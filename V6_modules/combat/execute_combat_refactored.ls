// V6 Module: combat/execute_combat_refactored.ls
// Refactored combat execution using modular components
// Replaces the monolithic 1,952-line execute_combat.ls

// Include required modules
include("attack_execution");
include("positioning_logic");
include("weapon_selection");

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

// Function: executeAttack
// Main attack function - now much cleaner and modular

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

function executeAttack() {
    executeAttackSequence();
}

// Function: executeDefensive
// Defensive actions (shields, heals, buffs)

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

function executeDefensive() {
    if (myTP < 1) return;
    
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("executeDefensive called - TP=" + myTP);
    }
    

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var threatRatio = calculateEID(myCell) / calculateEHP(myHP, myAbsShield, myRelShield, 0, myResistance);
    
    // Priority 1: Emergency healing if HP is critically low
    if (myHP < myMaxHP * 0.25 && myTP >= 4) {
        executeEmergencyHealing();
        return;
    }
    
    // Priority 2: Shields if under high threat and attacking
    if (threatRatio >= TP_DEFENSIVE_RATIO && myTP >= 4) {
        executeShielding();
    }
    
    // Priority 3: Healing if moderately damaged and safe
    if (myHP < myMaxHP * 0.7 && threatRatio < THREAT_HIGH_RATIO && myTP >= 4) {
        executeHealing();
    }
    
    // Priority 4: Buffs if early game and safe
    if (turn <= 3 && threatRatio < THREAT_SAFE_RATIO && myTP >= 4) {
        executeBuffs();
    }
}

// Function: executeEmergencyHealing
// Emergency healing when HP is critically low

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

function executeEmergencyHealing() {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var chips = getChips();
    
    // Try Regeneration first (most powerful heal)
    if (inArray(chips, CHIP_REGENERATION) && getCooldown(CHIP_REGENERATION) == 0) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

        var result = useChip(CHIP_REGENERATION);
        if (result == USE_SUCCESS || result == USE_CRITICAL) {
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("Emergency Regeneration used!");
            }
            return;
        }
    }
    
    // Try Cure
    if (inArray(chips, CHIP_CURE) && myTP >= getChipCost(CHIP_CURE)) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

        var result = useChip(CHIP_CURE);
        if (result == USE_SUCCESS || result == USE_CRITICAL) {
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("Emergency Cure used!");
            }
            return;
        }
    }
    
    // Try Bandage as last resort
    if (inArray(chips, CHIP_BANDAGE) && myTP >= getChipCost(CHIP_BANDAGE)) {
        useChip(CHIP_BANDAGE);
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Emergency Bandage used!");
        }
    }
}

// Function: executeShielding
// Apply shields when under threat

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

function executeShielding() {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var chips = getChips();

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var usedShield = false;
    
    // Try Armor first
    if (inArray(chips, CHIP_ARMOR) && myTP >= getChipCost(CHIP_ARMOR)) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

        var result = useChip(CHIP_ARMOR);
        if (result == USE_SUCCESS || result == USE_CRITICAL) {
            usedShield = true;
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("Armor shield applied (high threat)");
            }
        }
    }
    
    // Try Shield if Armor failed or unavailable
    if (!usedShield && inArray(chips, CHIP_SHIELD) && myTP >= getChipCost(CHIP_SHIELD)) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

        var result = useChip(CHIP_SHIELD);
        if (result == USE_SUCCESS || result == USE_CRITICAL) {
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("Shield applied (high threat)");
            }
        }
    }
}

// Function: executeHealing
// Regular healing when moderately damaged

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

function executeHealing() {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var chips = getChips();
    
    // Try Cure chip  
    if (inArray(chips, CHIP_CURE) && myTP >= getChipCost(CHIP_CURE)) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

        var result = useChip(CHIP_CURE);
        if (result == USE_SUCCESS || result == USE_CRITICAL) {
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("Cure used (moderate damage)");
            }
            return;
        }
    }
    
    // Try Cure if poisoned and need healing
    if (inArray(chips, CHIP_CURE) && myTP >= getChipCost(CHIP_CURE)) {
        if (hasNegativeEffects()) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

            var result = useChip(CHIP_CURE);
            if (result == USE_SUCCESS || result == USE_CRITICAL) {
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Cure used (healing + cleanse)");
                }
            }
        }
    }
}

// Function: executeBuffs
// Apply buffs in early game

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

function executeBuffs() {
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("executeBuffs called - TP=" + myTP + ", turn=" + turn);
    }
    

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var chips = getChips();

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var usedBuff = false;
    
    // Turn 1 priority buffs
    if (turn == 1) {
        // Knowledge for wisdom boost
        if (!usedBuff && inArray(chips, CHIP_KNOWLEDGE) && myTP >= getChipCost(CHIP_KNOWLEDGE)) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

            var result = useChip(CHIP_KNOWLEDGE);
            if (result == USE_SUCCESS || result == USE_CRITICAL) {
                usedBuff = true;
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Knowledge applied (Turn 1)");
                }
            }
        }
        
        // Armoring for HP boost
        if (!usedBuff && inArray(chips, CHIP_ARMORING) && myTP >= getChipCost(CHIP_ARMORING)) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

            var result = useChip(CHIP_ARMORING);
            if (result == USE_SUCCESS || result == USE_CRITICAL) {
                usedBuff = true;
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Armoring applied (Turn 1)");
                }
            }
        }
    }
    
    // Turn 2-3 situational buffs
    if (turn >= 2 && turn <= 3 && !usedBuff) {
        // Motivation if we need more TP
        if (myTP < 6 && inArray(chips, CHIP_MOTIVATION) && myTP >= getChipCost(CHIP_MOTIVATION)) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

            var result = useChip(CHIP_MOTIVATION);
            if (result == USE_SUCCESS || result == USE_CRITICAL) {
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Motivation applied (low TP)");
                }
            }
        }
    }
}

// Function: executeEarlyGameSequence
// Early game sequence with minimal buffs and quick attack

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

function executeEarlyGameSequence() {
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("=== TURN 1 EARLY GAME SEQUENCE ===");
        debugLog("HP: " + myHP + "/" + myMaxHP + " | TP: " + myTP + " | MP: " + myMP);
        debugLog("Enemy: " + getName(enemy) + " | Distance: " + enemyDistance);
    }
    
    // PHASE 1: MINIMAL BUFFS - Reserve TP for attacks

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var initialTP = myTP;
    if (myTP >= 8) { // Only buff if we have sufficient TP
        executeBuffs();
    }
    

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

    var buffsTP = initialTP - myTP;
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Phase 1 complete - Used " + buffsTP + " TP on buffs");
    }
    
    // PHASE 2: POSITIONING
    if (myMP > 0) {

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

        var positioningInfo = evaluateCombatPositioning(enemyDistance, hasLOS(myCell, enemyCell), myMP, getWeapons());
        if (positioningInfo != null) {
            executePositioning(positioningInfo);
        }
    }
    
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Phase 2 complete - Final distance: " + getCellDistance(myCell, enemyCell));
    }
    
    // PHASE 3: ATTACK SEQUENCE
    if (myTP >= 5) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Phase 3 - Attack sequence with " + myTP + " TP remaining");
        }
        executeAttackSequence();
    }
    
    // PHASE 4: DEFENSIVE ACTIONS
    if (myTP >= 4) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Phase 4 - Defensive actions with " + myTP + " TP remaining");
        }
        executeDefensive();
    }
    
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("=== EARLY GAME SEQUENCE COMPLETE ===");
    }
}

// Function: simplifiedCombat
// Simplified combat for panic mode

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

function simplifiedCombat() {
    if (debugEnabled && canSpendOps(500)) {
        debugLog("SIMPLIFIED COMBAT - Panic mode active");
    }
    
    // Priority 1: Emergency healing if critically low HP
    if (myHP < myMaxHP * 0.2 && myTP >= 4) {
        executeEmergencyHealing();
    }
    
    // Priority 2: Attack if we can
    if (myTP >= 5 && enemyDistance <= 10 && hasLOS(myCell, enemyCell)) {
        executeAttackSequence();
    }
    
    // Priority 3: Move closer if out of range
    if (enemyDistance > 10 && myMP > 0) {
        moveToward(enemy, min(myMP, 3));
    }
    
    // Priority 4: Shield if we have TP left
    if (myTP >= 4) {
        executeShielding();
    }
}

// Function: hasNegativeEffects
// Check if we have negative effects that Cure can remove

// NOTE: When included from V6_main.ls, all dependencies are already loaded
// No include statements needed here

function hasNegativeEffects() {
    // This would need to be implemented based on available game state functions
    // For now, return false as a safe default
    return false;
}

// Function: findOptimalTeleportTarget
function findOptimalTeleportTarget() {
    var currentCell = getCell();
    var currentEnemyCell = getCell(enemy);
    
    // Look for positions at range 8 (optimal rifle range) with LOS
    var optimalCells = getCellsAtDistance(currentEnemyCell, 8);
    
    for (var i = 0; i < count(optimalCells); i++) {
        var testCell = optimalCells[i];
        if (testCell == -1 || isObstacle(testCell)) continue;
        
        // Check if we can attack from this position
        if (hasLOS(testCell, currentEnemyCell)) {
            debugLog("🎯 Found optimal teleport target at range 8 with LOS: " + testCell);
            return testCell;
        }
    }
    
    // Fallback: any position in range 7-9 with LOS
    for (var range = 7; range <= 9; range++) {
        var cells = getCellsAtDistance(currentEnemyCell, range);
        for (var i = 0; i < count(cells); i++) {
            var testCell = cells[i];
            if (testCell == -1 || isObstacle(testCell)) continue;
            
            if (hasLOS(testCell, currentEnemyCell)) {
                debugLog("🎯 Found teleport target at range " + range + ": " + testCell);
                return testCell;
            }
        }
    }
    
    debugLog("⚠️ No optimal teleport target found - staying current position");
    return currentCell;
}

// Function: shouldUseTurn2ComboSequence
function shouldUseTurn2ComboSequence() {
    if (turn != 2) return false;
    if (COMBO_STRATEGY == null) return false;
    
    // Only use combo sequence for high damage opponents
    return (COMBO_STRATEGY == "ANTI_BURST" || COMBO_STRATEGY == "ANTI_MAGIC");
}

// Function: executeTurn2ComboSequence
function executeTurn2ComboSequence() {
    debugLog("=== TURN 2: COMBO SEQUENCE - " + COMBO_STRATEGY + " ===");
    
    var currentDist = getCellDistance(myCell, enemyCell);
    debugLog("Turn 2: Distance " + currentDist + ", TP: " + myTP);
    
    // PHASE 1: Aggressive positioning (teleport if needed)
    var inCombatRange = false;
    if (currentDist > 12 && TELEPORT_AVAILABLE && myTP >= 8) {
        debugLog("🚀 TELEPORT ASSAULT: Closing distance immediately");
        var teleportTarget = findOptimalTeleportTarget();
        if (teleportTarget != myCell) {
            if (executeTeleport(teleportTarget)) {
                currentDist = getCellDistance(getCell(), getCell(enemy));
                debugLog("✅ Teleported - new distance: " + currentDist);
                myTP = getTP();
                
                // Move closer after teleport if needed
                if (currentDist > 9 && getMP() > 0) {
                    moveToward(getCell(enemy), getMP());
                    currentDist = getCellDistance(getCell(), getCell(enemy));
                }
                inCombatRange = (currentDist <= 12);
            }
        }
    }
    
    // PHASE 2: Immediate attack if in range
    if (inCombatRange || currentDist <= 12) {
        debugLog("⚔️ PHASE 2: Immediate combat engagement");
        executeAttack();
        myTP = getTP();
    }
    
    // PHASE 3: Defensive preparation for Turn 3
    if (myTP >= 4) {
        debugLog("🛡️ PHASE 3: Defensive prep for sustained combat");
        if (COMBO_STRATEGY == "ANTI_BURST") {
            // Shield against physical damage
            if (getCooldown(CHIP_SHIELD) == 0 && myTP >= 4) {
                tryUseChip(CHIP_SHIELD, getEntity());
                myTP = getTP();
            }
        } else if (COMBO_STRATEGY == "ANTI_MAGIC") {
            // Resistance against magic damage
            if (getCooldown(CHIP_ARMOR) == 0 && myTP >= 4) {
                tryUseChip(CHIP_ARMOR, getEntity());
                myTP = getTP();
            }
        }
    }
    
    debugLog("Turn 2 combo sequence complete");
}