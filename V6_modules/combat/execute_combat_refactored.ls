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
// Apply buffs according to new strategy


function executeBuffs() {
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("executeBuffs called - TP=" + myTP + ", turn=" + turn);
    }

    var chips = getChips();
    
    // Turn 1: Execute mandatory buff sequence - KNOWLEDGE -> ELEVATION -> ARMORING
    if (turn == 1 && !TURN_1_BUFFS_COMPLETE) {
        executeTurn1BuffSequence(chips);
        return;
    }
    
    // Turn 2+: Only use STEROID if available and on cooldown cycle
    if (turn >= 2) {
        executeSTEROIDCycle(chips);
    }
}


// Function: executeTurn1BuffSequence
// Execute the mandatory turn 1 sequence: KNOWLEDGE -> ELEVATION -> ARMORING -> LEATHER_BOOTS
function executeTurn1BuffSequence(chips) {
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("=== TURN 1 BUFF SEQUENCE ===");
        debugLog("Starting TP: " + myTP);
    }
    
    // Sequence: KNOWLEDGE (5 TP) -> ELEVATION (5 TP) -> ARMORING (6 TP) -> LEATHER_BOOTS (3 TP) = 19 TP
    // With 22 TP total, leaves 3 TP for weapon equip
    
    var chipOrder = [CHIP_KNOWLEDGE, CHIP_ELEVATION, CHIP_ARMORING];
    var totalUsed = 0;
    
    for (var i = 0; i < count(chipOrder); i++) {
        var chip = chipOrder[i];
        
        if (inArray(chips, chip) && myTP >= getChipCost(chip)) {
            var cost = getChipCost(chip);
            var result = useChip(chip);
            
            if (result == USE_SUCCESS || result == USE_CRITICAL) {
                myTP -= cost;
                totalUsed += cost;
                
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Applied " + getChipName(chip) + " (-" + cost + " TP, remaining: " + myTP + ")");
                }
            } else {
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("FAILED to apply " + getChipName(chip));
                }
            }
        } else {
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("Cannot use " + getChipName(chip) + " - not available or insufficient TP");
            }
        }
    }
    
    // Now use LEATHER_BOOTS if we have enough TP (need 6 TP total: 3 for boots + 3 for weapon equip)
    if (inArray(chips, CHIP_LEATHER_BOOTS) && myTP >= 6) {
        var result = useChip(CHIP_LEATHER_BOOTS);
        if (result == USE_SUCCESS || result == USE_CRITICAL) {
            myTP -= 3;
            totalUsed += 3;
            LEATHER_BOOTS_LAST_USED = turn;
            hasLeatherBoots = true;
            
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("Applied LEATHER_BOOTS (-3 TP, remaining: " + myTP + ")");
            }
        }
    }
    
    TURN_1_BUFFS_COMPLETE = true;
    
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Turn 1 buffs complete - Used " + totalUsed + " TP, remaining: " + myTP);
    }
}


// Function: executeSTEROIDCycle  
// Handle STEROID usage on its cooldown cycle
function executeSTEROIDCycle(chips) {
    // Check if STEROID is off cooldown (5-turn cooldown)
    var steroidAvailable = (turn - STEROID_LAST_USED) >= STEROID_COOLDOWN;
    
    if (steroidAvailable && inArray(chips, CHIP_STEROID) && myTP >= getChipCost(CHIP_STEROID)) {
        var result = useChip(CHIP_STEROID);
        if (result == USE_SUCCESS || result == USE_CRITICAL) {
            myTP -= getChipCost(CHIP_STEROID);
            STEROID_LAST_USED = turn;
            
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("Applied STEROID for damage boost (next available: turn " + (turn + STEROID_COOLDOWN) + ")");
            }
        }
    } else if (!steroidAvailable && debugEnabled && canSpendOps(1000)) {
        var turnsUntilReady = STEROID_COOLDOWN - (turn - STEROID_LAST_USED);
        debugLog("STEROID on cooldown - available in " + turnsUntilReady + " turns");
    }
}


// Function: executeEarlyGameSequence
// Turn 1 sequence: KNOWLEDGE -> ELEVATION -> ARMORING -> LEATHER_BOOTS -> equip RIFLE


function executeEarlyGameSequence() {
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("=== TURN 1 NEW STRATEGY SEQUENCE ===");
        debugLog("HP: " + myHP + "/" + myMaxHP + " | TP: " + myTP + " | MP: " + myMP);
        debugLog("Enemy: " + getName(enemy) + " | Distance: " + enemyDistance);
    }
    
    // PHASE 1: MANDATORY BUFF SEQUENCE (16-19 TP)
    var initialTP = myTP;
    executeBuffs(); // This will execute the turn 1 buff sequence
    
    var buffsTP = initialTP - myTP;
    if (debugEnabled && canSpendOps(1000)) {
        debugLog("Phase 1 complete - Used " + buffsTP + " TP on buffs, remaining: " + myTP);
    }
    
    // PHASE 2: EQUIP RIFLE (3 TP) - Only if we have enough TP
    if (myTP >= 3) {
        var weapons = getWeapons();
        if (inArray(weapons, WEAPON_RIFLE)) {
            var result = setWeapon(WEAPON_RIFLE);
            if (result == USE_SUCCESS) {
                myTP -= 3;
                RIFLE_USES_REMAINING = getWeaponMaxUses(WEAPON_RIFLE);
                
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Equipped RIFLE (-3 TP, remaining: " + myTP + ", uses: " + RIFLE_USES_REMAINING + ")");
                }
            }
        } else {
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("RIFLE not available - checking other weapons");
            }
        }
    }
    
    // PHASE 3: POSITIONING (if MP available and needed)
    if (myMP > 0) {
        var currentDistance = getCellDistance(myCell, enemyCell);
        var hasLine = hasLOS(myCell, enemyCell);
        
        // Only move if we're out of RIFLE range (7-9) or don't have line of sight
        if (currentDistance > 9 || currentDistance < 7 || !hasLine) {
            var positioningInfo = evaluateCombatPositioning(currentDistance, hasLine, myMP, getWeapons());
            if (positioningInfo != null) {
                executePositioning(positioningInfo);
                
                if (debugEnabled && canSpendOps(1000)) {
                    debugLog("Phase 3 positioning complete - Final distance: " + getCellDistance(myCell, enemyCell));
                }
            }
        } else {
            if (debugEnabled && canSpendOps(1000)) {
                debugLog("Phase 3 - Already in RIFLE range, no positioning needed");
            }
        }
    }
    
    // PHASE 4: REMAINING ACTIONS (should have 0-3 TP left)
    if (myTP > 0) {
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Phase 4 - " + myTP + " TP remaining after turn 1 setup");
        }
        
        // Skip attacking on turn 1 - save TP for turn 2 STEROID combo
        if (debugEnabled && canSpendOps(1000)) {
            debugLog("Turn 1 complete - saving remaining TP for turn 2 STEROID combo");
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