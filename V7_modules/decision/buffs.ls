// V7 Module: decision/buffs.ls
// Buff chip management for strength/agility focused build

// === CHIP_MIRROR LOGIC - REMOVED ===
// Function removed to avoid compilation issues

// === MAIN BUFF APPLICATION ===
function applyTurnBuffs() {
    if (debugEnabled) {
        debugW("=== BUFF APPLICATION START ===");
        debugW("Turn: " + getTurn() + ", TP: " + myTP);
    }
    
    // Check if we should skip buffs to reserve TP for weapons
    if (shouldSkipBuffsInEmergency()) {
        return 0; // No TP used
    }
    
    var turn = getTurn();
    var tpUsed = 0;
    var chips = getChips();

    // Priority 0: CHIP_MIRROR - temporarily removed for debugging
    // All CHIP_MIRROR logic has been disabled to isolate compilation issues

    // Priority 1: Motivation (+2 TP) - use early for compound benefit
    // Apply on turns 1, 4, 7, etc. (every 3 turns due to 6 turn cooldown)
    if ((turn == 1 || (turn - 1) % 6 == 0) && inArray(chips, CHIP_MOTIVATION)) {
        if (canUseChip(CHIP_MOTIVATION, getEntity()) && myTP >= 4) {
            useChip(CHIP_MOTIVATION, getEntity());
            tpUsed += 4;
            myTP = getTP(); // Update TP after buff
            if (debugEnabled) {
                debugW("BUFF: Applied MOTIVATION (+2 TP for 3 turns)");
            }
        }
    }
    
    // Priority 2: Protein (+strength) on turn 1 and when expired
    // Apply on turns 1, 4, 7, etc. (every 3 turns due to 3 turn cooldown)
    if ((turn == 1 || (turn - 1) % 3 == 0) && inArray(chips, CHIP_PROTEIN)) {
        if (canUseChip(CHIP_PROTEIN, getEntity()) && myTP >= 3) {
            useChip(CHIP_PROTEIN, getEntity());
            tpUsed += 3;
            myTP = getTP();
            myStrength = getStrength(); // Update strength
            if (debugEnabled) {
                debugW("BUFF: Applied PROTEIN (+80-100 strength for 2 turns)");
            }
        }
    }
    
    // Priority 3: Stretching (+agility) for crit chance
    // Apply on turns 2, 5, 8, etc. (offset from Protein to avoid conflicts)
    if ((turn == 2 || (turn - 2) % 3 == 0) && inArray(chips, CHIP_STRETCHING)) {
        if (canUseChip(CHIP_STRETCHING, getEntity()) && myTP >= 3) {
            useChip(CHIP_STRETCHING, getEntity());
            tpUsed += 3;
            myTP = getTP();
            myAgility = getAgility(); // Update agility
            if (debugEnabled) {
                debugW("BUFF: Applied STRETCHING (+80-100 agility for 2 turns)");
            }
        }
    }
    
    // Priority 4: Leather Boots (+MP) when positioning is critical
    // Only use when MP is low and we need to move
    if (myMP <= 2 && inArray(chips, CHIP_LEATHER_BOOTS)) {
        if (canUseChip(CHIP_LEATHER_BOOTS, getEntity()) && myTP >= 3) {
            useChip(CHIP_LEATHER_BOOTS, getEntity());
            tpUsed += 3;
            myTP = getTP();
            myMP = getMP(); // Update MP
            if (debugEnabled) {
                debugW("BUFF: Applied LEATHER_BOOTS (+2 MP for 2 turns)");
            }
        }
    }
    
    if (debugEnabled) {
        debugW("BUFF APPLICATION COMPLETE: Used " + tpUsed + " TP, Remaining: " + myTP);
    }
    
    return tpUsed;
}

// === BUFF PRIORITY CALCULATION ===
function calculateBuffPriority(chip, turn) {
    // Higher score = higher priority
    var priority = 0;

    // CHIP_MIRROR priority logic temporarily removed for debugging
    /*
    if (chip == CHIP_MIRROR) {
        // Dynamic priority based on build type
        if (isAgilityBuild) {
            priority = 120;  // Highest - maximum benefit (up to 39% reflection)
        } else if (isWisdomBuild) {
            priority = 80;   // High - survivability synergy
        } else if (isStrengthBuild) {
            priority = 60;   // Medium - apply if spare TP available
        } else if (isMagicBuild) {
            priority = 40;   // Low - DoT combos take precedence
        } else {
            priority = 70;   // Balanced builds - medium-high priority
        }

        // Boost priority if taking heavy damage (defensive benefit)
        if (myHP < myMaxHP * 0.5) {
            priority += 20;
        }

        // Extra boost if multiple enemies (more incoming damage to reflect)
        if (count(allEnemies) >= 3) {
            priority += 30;
        }
    } else
    */
    if (chip == CHIP_MOTIVATION) {
        // Very high priority early in fight for compound TP benefit
        priority = (turn <= 3) ? 100 : 50;
    } else if (chip == CHIP_PROTEIN) {
        // High priority for strength builds
        priority = 80;
    } else if (chip == CHIP_STRETCHING) {
        // Medium priority for crit chance
        priority = 60;
    } else if (chip == CHIP_LEATHER_BOOTS) {
        // Low priority unless MP is critical
        priority = (myMP <= 2) ? 70 : 20;
    }
    
    return priority;
}

// === BUFF STATUS CHECKING ===
function shouldApplyBuff(chip, turn) {
    var cooldown = getCooldown(chip);
    var cost = getChipCost(chip);
    
    // Check if we have enough TP
    if (myTP < cost) {
        if (debugEnabled) {
            debugW("BUFF SKIP: " + chip + " - Not enough TP (need " + cost + ", have " + myTP + ")");
        }
        return false;
    }
    
    // Check if chip is on cooldown
    if (cooldown > 0) {
        if (debugEnabled) {
            debugW("BUFF SKIP: " + chip + " - On cooldown (" + cooldown + " turns)");
        }
        return false;
    }
    
    // Check if we can actually use the chip
    if (!canUseChip(chip, getEntity())) {
        if (debugEnabled) {
            debugW("BUFF SKIP: " + chip + " - Cannot use chip");
        }
        return false;
    }
    
    return true;
}

// === BUFF OPTIMIZATION ===
function optimizeBuffSequence(availableChips, availableTP) {
    // Calculate optimal buff sequence based on available TP
    var sequence = [];
    var remainingTP = availableTP;
    var turn = getTurn();
    
    // Sort chips by priority
    var chipPriorities = [];
    for (var i = 0; i < count(availableChips); i++) {
        var chip = availableChips[i];
        var priority = calculateBuffPriority(chip, turn);
        push(chipPriorities, [chip, priority]);
    }
    
    // Simple bubble sort by priority (descending)
    for (var i = 0; i < count(chipPriorities) - 1; i++) {
        for (var j = 0; j < count(chipPriorities) - i - 1; j++) {
            if (chipPriorities[j][1] < chipPriorities[j + 1][1]) {
                var temp = chipPriorities[j];
                chipPriorities[j] = chipPriorities[j + 1];
                chipPriorities[j + 1] = temp;
            }
        }
    }
    
    // Apply buffs in priority order
    for (var i = 0; i < count(chipPriorities); i++) {
        var chip = chipPriorities[i][0];
        var cost = getChipCost(chip);
        
        if (remainingTP >= cost && shouldApplyBuff(chip, turn)) {
            push(sequence, chip);
            remainingTP -= cost;
        }
    }
    
    if (debugEnabled && count(sequence) > 0) {
        debugW("BUFF SEQUENCE: [" + join(sequence, ", ") + "] - Cost: " + (availableTP - remainingTP) + " TP");
    }
    
    return sequence;
}

// === EMERGENCY BUFF HANDLING ===
function shouldSkipBuffsInEmergency() {
    // Skip buffs when in emergency mode EXCEPT defensive buffs like MIRROR
    if (emergencyMode) {
        // Check if we have CHIP_MIRROR available and not on cooldown
        var chips = getChips();
        if (inArray(chips, CHIP_MIRROR) && getCooldown(CHIP_MIRROR) == 0 && myTP >= 5) {
            // Don't skip buffs if we can apply mirror for defense
            if (debugEnabled) {
                debugW("BUFF ALLOW: Emergency mode but MIRROR available for defense");
            }
            return false;
        }

        if (debugEnabled) {
            debugW("BUFF SKIP: Emergency mode active - saving TP for survival (MIRROR not available)");
        }
        return true;
    }
    
    // Skip buffs if we're very low on TP and need it for combat
    // Reserve at least 6 TP for weapon attacks (B_LASER costs 5 TP)
    if (myTP < 12) {
        if (debugEnabled) {
            debugW("BUFF SKIP: Low TP (" + myTP + ") - saving for weapons (need 6+ TP reserved)");
        }
        return true;
    }
    
    return false;
}