// V6 Module: combat/execute_combat_refactored.ls
// Refactored combat execution using modular components
// Replaces the monolithic 1,952-line execute_combat.ls

// Include required modules
include("attack_execution");
include("positioning_logic");
include("weapon_selection");


// Function: executeAttack
// Main attack function - now much cleaner and modular


function executeAttack() {
    executeAttackSequence();
}


// Function: executeDefensive
// Defensive actions (shields, heals, buffs)


function executeDefensive() {
    if (myTP < 1) return;
    
    if (debugEnabled && canSpendOps(1000)) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("executeDefensive called - TP=" + myTP);
        }
    }

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


function executeEmergencyHealing() {
    var chips = getChips();
    
    // Try Regeneration first (most powerful heal)
    if (inArray(chips, CHIP_REGENERATION) && getCooldown(CHIP_REGENERATION) == 0) {
        var result = useChip(CHIP_REGENERATION);
        if (result == USE_SUCCESS || result == USE_CRITICAL) {
            if (debugEnabled && canSpendOps(1000)) {
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Emergency Regeneration used!");
                }
            }
            return;
        }
    }
    
    // Try Cure
    if (inArray(chips, CHIP_CURE) && myTP >= getChipCost(CHIP_CURE)) {
        var result = useChip(CHIP_CURE);
        if (result == USE_SUCCESS || result == USE_CRITICAL) {
            if (debugEnabled && canSpendOps(1000)) {
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Emergency Cure used!");
                }
            }
            return;
        }
    }
    
    // Try Bandage as last resort
    if (inArray(chips, CHIP_BANDAGE) && myTP >= getChipCost(CHIP_BANDAGE)) {
        useChip(CHIP_BANDAGE);
        if (debugEnabled && canSpendOps(1000)) {
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("Emergency Bandage used!");
            }
        }
    }
}


// Function: executeShielding
// Apply shields when under threat


function executeShielding() {
    var chips = getChips();
    var usedShield = false;
    
    // Try Armor first
    if (inArray(chips, CHIP_ARMOR) && myTP >= getChipCost(CHIP_ARMOR)) {
        var result = useChip(CHIP_ARMOR);
        if (result == USE_SUCCESS || result == USE_CRITICAL) {
            usedShield = true;
            if (debugEnabled && canSpendOps(1000)) {
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Armor shield applied (high threat)");
                }
            }
        }
    }
    
    // Try Shield if Armor failed or unavailable
    if (!usedShield && inArray(chips, CHIP_SHIELD) && myTP >= getChipCost(CHIP_SHIELD)) {
        var result = useChip(CHIP_SHIELD);
        if (result == USE_SUCCESS || result == USE_CRITICAL) {
            if (debugEnabled && canSpendOps(1000)) {
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Shield applied (high threat)");
                }
            }
        }
    }
}


// Function: executeHealing
// Regular healing when moderately damaged


function executeHealing() {
    var chips = getChips();
    
    // Try Cure chip  
    if (inArray(chips, CHIP_CURE) && myTP >= getChipCost(CHIP_CURE)) {
        var result = useChip(CHIP_CURE);
        if (result == USE_SUCCESS || result == USE_CRITICAL) {
            if (debugEnabled && canSpendOps(1000)) {
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Cure used (moderate damage)");
                }
            }
            return;
        }
    }
    
    // Try Cure if poisoned and need healing
    if (inArray(chips, CHIP_CURE) && myTP >= getChipCost(CHIP_CURE)) {
        if (hasNegativeEffects()) {
            var result = useChip(CHIP_CURE);
            if (result == USE_SUCCESS || result == USE_CRITICAL) {
                if (debugEnabled && canSpendOps(1000)) {
                    if (debugEnabled && canSpendOps(1000)) {
                        debugLog("Cure used (healing + cleanse)");
                    }
                }
            }
        }
    }
}


// Function: executeBuffs
// Apply buffs in early game


function executeBuffs() {
    if (debugEnabled && canSpendOps(1000)) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("executeBuffs called - TP=" + myTP + ", turn=" + turn);
        }
    }

    var chips = getChips();
    var usedBuff = false;
    
    // Turn 1 priority buffs
    if (turn == 1) {
        // Knowledge for wisdom boost
        if (!usedBuff && inArray(chips, CHIP_KNOWLEDGE) && myTP >= getChipCost(CHIP_KNOWLEDGE)) {
            var result = useChip(CHIP_KNOWLEDGE);
            if (result == USE_SUCCESS || result == USE_CRITICAL) {
                usedBuff = true;
                if (debugEnabled && canSpendOps(1000)) {
                    if (debugEnabled && canSpendOps(1000)) {
                        debugLog("Knowledge applied (Turn 1)");
                    }
                }
            }
        }
        
        // Armoring for HP boost
        if (!usedBuff && inArray(chips, CHIP_ARMORING) && myTP >= getChipCost(CHIP_ARMORING)) {
            var result = useChip(CHIP_ARMORING);
            if (result == USE_SUCCESS || result == USE_CRITICAL) {
                usedBuff = true;
                if (debugEnabled && canSpendOps(1000)) {
                    if (debugEnabled && canSpendOps(1000)) {
                        debugLog("Armoring applied (Turn 1)");
                    }
                }
            }
        }
    }
    
    // Turn 2-3 situational buffs
    if (turn >= 2 && turn <= 3 && !usedBuff) {
        // Motivation if we need more TP
        if (myTP < 6 && inArray(chips, CHIP_MOTIVATION) && myTP >= getChipCost(CHIP_MOTIVATION)) {
            var result = useChip(CHIP_MOTIVATION);
            if (result == USE_SUCCESS || result == USE_CRITICAL) {
                if (debugEnabled && canSpendOps(1000)) {
                    if (debugEnabled && canSpendOps(1000)) {
                        debugLog("Motivation applied (low TP)");
                    }
                }
            }
        }
    }
}


// Function: executeEarlyGameSequence
// Early game sequence with minimal buffs and quick attack


function executeEarlyGameSequence() {
    if (debugEnabled && canSpendOps(1000)) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("=== TURN 1 EARLY GAME SEQUENCE ===");
        }
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("HP: " + myHP + "/" + myMaxHP + " | TP: " + myTP + " | MP: " + myMP);
        }
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Enemy: " + getName(enemy) + " | Distance: " + enemyDistance);
        }
    }
    
    // PHASE 1: MINIMAL BUFFS - Reserve TP for attacks
    var initialTP = myTP;
    if (myTP >= 8) { // Only buff if we have sufficient TP
        executeBuffs();
    }
    
    var buffsTP = initialTP - myTP;
    if (debugEnabled && canSpendOps(1000)) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Phase 1 complete - Used " + buffsTP + " TP on buffs");
        }
    }
    
    // PHASE 2: POSITIONING
    if (myMP > 0) {
        var positioningInfo = evaluateCombatPositioning(enemyDistance, hasLOS(myCell, enemyCell), myMP, getWeapons());
        if (positioningInfo != null) {
            executePositioning(positioningInfo);
        }
    }
    
    if (debugEnabled && canSpendOps(1000)) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Phase 2 complete - Final distance: " + getCellDistance(myCell, enemyCell));
        }
    }
    
    // PHASE 3: ATTACK SEQUENCE
    if (myTP >= 5) {
        if (debugEnabled && canSpendOps(1000)) {
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("Phase 3 - Attack sequence with " + myTP + " TP remaining");
            }
        }
        executeAttackSequence();
    }
    
    // PHASE 4: DEFENSIVE ACTIONS
    if (myTP >= 4) {
        if (debugEnabled && canSpendOps(1000)) {
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("Phase 4 - Defensive actions with " + myTP + " TP remaining");
            }
        }
        executeDefensive();
    }
    
    if (debugEnabled && canSpendOps(1000)) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("=== EARLY GAME SEQUENCE COMPLETE ===");
        }
    }
}


// Function: simplifiedCombat
// Simplified combat for panic mode


function simplifiedCombat() {
    if (debugEnabled && canSpendOps(500)) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("SIMPLIFIED COMBAT - Panic mode active");
        }
    }
    
    // Priority 1: Enhanced Lightninger in panic mode (attack + heal combo)
    if (myHP < myMaxHP * 0.4 && myTP >= 9 && enhancedLightningerUsesRemaining > 0) {
        if (enemyDistance >= 6 && enemyDistance <= 10 && hasLOS(myCell, enemyCell)) {
            if (debugEnabled && canSpendOps(500)) {
                debugLog("PANIC: Using Enhanced Lightninger (attack+heal combo)");
            }
            var weapons = getWeapons();
            if (inArray(weapons, WEAPON_ENHANCED_LIGHTNINGER)) {
                var result = useWeaponOnCell(enemyCell);
                if (result == USE_SUCCESS || result == USE_CRITICAL) {
                    enhancedLightningerUsesRemaining--;
                    return; // Done with turn
                }
            }
        }
    }
    
    // Priority 2: Emergency healing if critically low HP (only if Enhanced Lightninger failed)
    if (myHP < myMaxHP * 0.2 && myTP >= 4) {
        executeEmergencyHealing();
    }
    
    // Priority 3: Attack if we can
    if (myTP >= 5 && enemyDistance <= 10 && hasLOS(myCell, enemyCell)) {
        executeAttackSequence();
    }
    
    // Priority 4: Move closer if out of range
    if (enemyDistance > 10 && myMP > 0) {
        moveToward(enemy, min(myMP, 3));
    }
    
    // Priority 5: Shield if we have TP left
    if (myTP >= 4) {
        executeShielding();
    }
}


// Function: hasNegativeEffects
// Check if we have negative effects that Cure can remove


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
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("🎯 Found optimal teleport target at range 8 with LOS: " + testCell);
            }
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
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("🎯 Found teleport target at range " + range + ": " + testCell);
                }
                return testCell;
            }
        }
    }
    
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("⚠️ No optimal teleport target found - staying current position");
    }
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
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("=== TURN 2: COMBO SEQUENCE - " + COMBO_STRATEGY + " ===");
    }
    
    var currentDist = getCellDistance(myCell, enemyCell);
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Turn 2: Distance " + currentDist + ", TP: " + myTP);
    }
    
    // PHASE 1: Aggressive positioning (teleport if needed)
    var inCombatRange = false;
    if (currentDist > 12 && TELEPORT_AVAILABLE && myTP >= 8) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("🚀 TELEPORT ASSAULT: Closing distance immediately");
        }
        var teleportTarget = findOptimalTeleportTarget();
        if (teleportTarget != myCell) {
            if (executeTeleport(teleportTarget)) {
                currentDist = getCellDistance(getCell(), getCell(enemy));
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("✅ Teleported - new distance: " + currentDist);
                }
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
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("⚔️ PHASE 2: Immediate combat engagement");
        }
        executeAttack();
        myTP = getTP();
    }
    
    // PHASE 3: Defensive preparation for Turn 3
    if (myTP >= 4) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("🛡️ PHASE 3: Defensive prep for sustained combat");
        }
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
    
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Turn 2 combo sequence complete");
    }
}