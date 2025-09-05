// V6 Module: combat/execute_combat.ls
// Combat execution
// Auto-generated from V5.0 script

// Function: executeAttack
function executeAttack() {
    // say("executeAttack - TP=" + myTP); // Removed - costs 1 TP
    debug("executeAttack called - enemy=" + enemy + ", myTP=" + myTP);
    if (enemy == null || myTP < 1) {
        debug("executeAttack early return - enemy null or no TP");
        return;
    }
    
    var dist = getCellDistance(myCell, enemyCell);
    var hasLine = hasLOS(myCell, enemyCell);
    // say("Range=" + dist + " LOS=" + hasLine); // Removed - costs 1 TP
    debug("Combat range=" + dist + ", hasLOS=" + hasLine);
    
    // SMART ATTACK: Use damage calculation to find best weapon/chip combo!
    // Commented out to prevent log spam: debugLog("Smart attack at range " + dist + ", TP=" + myTP);
    
    // POSITIONING CHECK: Only reposition if we're COMPLETELY out of attack range
    // Don't waste MP repositioning if we can already attack!
    var canAttackFromHere = false;
    var myWeapons = getWeapons();
    var myChips = getChips();
    
    // Check if any weapon can hit from current position
    for (var i = 0; i < count(myWeapons); i++) {
        var w = myWeapons[i];
        if (dist >= getWeaponMinRange(w) && dist <= getWeaponMaxRange(w) && 
            canUseWeapon(w, enemy) && (!weaponNeedLos(w) || hasLine)) {
            canAttackFromHere = true;
            break;
        }
    }
    
    // Also check damage chips
    if (!canAttackFromHere) {
        for (var i = 0; i < count(myChips); i++) {
            var ch = myChips[i];
            if (chipHasDamage(ch) && getCooldown(ch) <= 0 &&
                dist >= getChipMinRange(ch) && dist <= getChipMaxRange(ch) && 
                canUseChip(ch, enemy) && (!chipNeedLos(ch) || hasLine)) {
                canAttackFromHere = true;
                break;
            }
        }
    }
    
    // Only reposition if we CAN'T attack from current position
    if (myMP > 0 && !canAttackFromHere) {
        debugLog("Can't attack from range " + dist + ", repositioning...");
        // Try to get to optimal range 6-7
        var targetRange = 7;
        var reachable = getReachableCells(myCell, myMP);
        var bestCell = myCell;
        var bestScore = -999999;
        
        for (var i = 0; i < min(20, count(reachable)); i++) {
            var cell = reachable[i];
            var newDist = getCellDistance(cell, enemyCell);
            var score = 0;
            
            // Heavily favor dynamically calculated optimal range
            if (newDist == optimalAttackRange) score = 5000;
            else if (abs(newDist - optimalAttackRange) == 1) score = 4000;
            else if (newDist >= 6 && newDist <= 10) score = 2000;  // Lightninger range
            else if (newDist >= 4 && newDist <= 7) score = 1500;   // Grenade range
            else score = -abs(newDist - optimalAttackRange) * 500;
            
            // Check LoS
            if (hasLOS(cell, enemyCell)) score += 1000;
            
            if (score > bestScore) {
                bestScore = score;
                bestCell = cell;
            }
        }
        
        if (bestCell != myCell) {
            var newDist = getCellDistance(bestCell, enemyCell);
            if (newDist >= 6 && newDist <= 7) {
                debugLog("Repositioning from range " + dist + " to optimal range " + newDist);
                if (moveToCell(bestCell) > 0) {
                    dist = getCellDistance(myCell, enemyCell);
                    hasLine = hasLOS(myCell, enemyCell);
                    enemyDistance = dist;
                }
            }
        }
    }
    
    // Build attack options list (3x faster with fold!)
    var weapons = getWeapons();
    debugLog("Building attack options - Weapons available: " + count(weapons));
    debugLog("  Range=" + dist + ", TP=" + myTP + ", LOS=" + hasLine);
    
    var attackOptions = arrayFoldLeft(weapons, function(acc, w) {
        var minR = getWeaponMinRange(w);
        var maxR = getWeaponMaxRange(w);
        var cost = getWeaponCost(w);
        
        // Can we use this weapon?
        debugLog("  Checking weapon " + getWeaponName(w) + ": range[" + minR + "-" + maxR + "] cost=" + cost);
        if (dist >= minR && dist <= maxR && myTP >= cost) {
            // Check LOS separately for better debugging
            if (!weaponNeedLos(w) || hasLine) {
                debugLog("    ✓ Added weapon: " + getWeaponName(w));
                var damage = getWeaponDamage(w, myLeek);
                var dptp = damage / cost;  // Damage per TP
                var maxUses = getWeaponMaxUses(w);
                var possibleUses = floor(myTP / cost);
                // Handle unlimited uses (-1) and ensure at least 1 use if we have TP
                if (maxUses == -1 || maxUses == 0) {
                    // Unlimited uses or unspecified - use TP-based calculation
                    possibleUses = max(1, possibleUses);  // At least 1 use if we can afford it
                } else if (maxUses > 0) {
                    possibleUses = min(possibleUses, maxUses);
                }
                
                // Bonus for AOE weapons
                if (w == WEAPON_LIGHTNINGER) {
                    // Check if enemy is positioned for diagonal hits
                    var lightResult = evaluateLightningerPosition(myCell, enemyCell);
                    if (lightResult != null && lightResult["numHits"] > 0) {
                        // Bonus for diagonal pattern potential
                        dptp = dptp * 1.3; // 30% bonus for diagonal pattern
                    } else {
                        dptp = dptp * 1.2; // 20% standard AOE bonus
                    }
                } else if (w == WEAPON_GRENADE_LAUNCHER) {
                    // Use enhanced grenade targeting
                    var grenadeTarget = findBestGrenadeTarget(myCell);
                    if (grenadeTarget != null) {
                        // Calculate actual damage potential with AoE
                        var actualDamage = grenadeTarget["damage"];
                        dptp = actualDamage / cost;
                        
                        // Bonus for splash damage opportunity
                        if (!grenadeTarget["directHit"]) {
                            dptp = dptp * 1.3; // 30% bonus for clever splash positioning
                        }
                    } else {
                        dptp = dptp * 1.2; // 20% standard AOE bonus
                    }
                }
                
                // Fix 8: Rhino has 3 uses - HIGHEST DPS at close range!
                if (w == WEAPON_RHINO && maxUses == 3) {
                    if (dist >= 2 && dist <= 3) {
                        dptp = dptp * 1.5; // 50% bonus - best close-range DPS
                    } else {
                        dptp = dptp * 1.2; // 20% bonus for multiple uses
                    }
                }
                
                // Katana bonus for AGI debuff
                if (w == WEAPON_KATANA && enemyAgility > 200) {
                    dptp = dptp * 1.15; // 15% bonus vs high AGI
                }
                
                // Build option array
                var option = [];
                push(option, "weapon");  // type at index 0
                push(option, w);          // item at index 1
                push(option, damage);     // damage at index 2
                push(option, cost);       // cost at index 3
                push(option, dptp);       // dptp at index 4
                push(option, possibleUses); // maxUses at index 5
                push(option, getWeaponName(w)); // name at index 6
                push(acc, option);
            } else {
                debugLog("    ✗ No LOS for weapon");
            }
        } else {
            if (dist < minR || dist > maxR) {
                debugLog("    ✗ Out of range");
            }
            if (myTP < cost) {
                debugLog("    ✗ Not enough TP");
            }
        }
        return acc;
    }, []);
    
    // Check damage chips (3x faster with fold!)
    var chips = getChips();
    if (debugEnabled && turn <= 3) {
        debugLog("Checking " + count(chips) + " chips for damage options");
    }
    attackOptions = arrayFoldLeft(chips, function(acc, ch) {
        if (!chipHasDamage(ch)) return acc;
        if (getCooldown(ch) > 0) return acc;
        
        var minR = getChipMinRange(ch);
        var maxR = getChipMaxRange(ch);
        var cost = getChipCost(ch);
        
        // Can we use this chip?
        if (dist >= minR && dist <= maxR && myTP >= cost) {
            // Check cooldown and LOS separately for better debugging
            if (getCooldown(ch) == 0 && (!chipNeedLos(ch) || hasLine)) {
                var damage = getChipDamage(ch, myLeek);
                var dptp = damage / cost;
                var maxUses = getChipMaxUses(ch);
                var possibleUses = floor(myTP / cost);
                if (maxUses > 0) possibleUses = min(possibleUses, maxUses);
                
                // Build option array
                var option = [];
                push(option, "chip");     // type at index 0
                push(option, ch);         // item at index 1
                push(option, damage);     // damage at index 2
                push(option, cost);       // cost at index 3
                push(option, dptp);       // dptp at index 4
                push(option, possibleUses); // maxUses at index 5
                push(option, getChipName(ch)); // name at index 6
                push(acc, option);
            }
        }
        return acc;
    }, attackOptions);
    
    // Sort by damage per TP (highest first) - Using arraySort for better performance
    // Create sortable array with dptp as first element for natural sorting
    var sortable = arrayMap(attackOptions, function(option) {
        // Negate dptp for descending sort (LeekScript sorts ascending)
        return [-option[4], option];  // [negated dptp, original option]
    });
    
    // Use built-in sort which is much faster than O(n²) manual sorting
    sort(sortable);
    
    // Extract the sorted options
    attackOptions = arrayMap(sortable, function(item) {
        return item[1];  // Get the original option
    });
    
    // Always log attack options for debugging
    // say("Attack options: " + count(attackOptions)); // Removed - costs 1 TP
    debug("Attack options available: " + count(attackOptions) + " at range " + dist + " with TP=" + myTP);
    if (count(attackOptions) == 0) {
        // say("WARNING: No attack options!"); // Removed - costs 1 TP
        debug("WARNING: No attack options - checking weapons: " + count(getWeapons()));
    }
    
    // FALLBACK: If no options but we have TP and are in range, force basic attack
    if (count(attackOptions) == 0 && myTP >= 3 && dist <= 10 && hasLine) {
        debugLog("FALLBACK: Forcing attack attempt");
        
        // Try each weapon directly (use existing weapons array from line 5589)
        for (var w = 0; w < count(weapons); w++) {
            var weapon = weapons[w];
            var minR = getWeaponMinRange(weapon);
            var maxR = getWeaponMaxRange(weapon);
            var cost = getWeaponCost(weapon);
            
            if (dist >= minR && dist <= maxR && myTP >= cost) {
                setWeaponIfNeeded(weapon);
                var result = useWeapon(enemy);
                if (result == USE_SUCCESS || result == USE_CRITICAL) {
                    debugLog("Fallback attack succeeded with " + getWeaponName(weapon));
                    myTP = getTP();
                } else {
                    debugLog("Fallback failed: " + result + " for " + getWeaponName(weapon));
                }
            }
        }
    }
    
    // Execute attacks in order of efficiency
    var tpLeft = myTP;
    var totalDamage = 0;
    
    // say("Executing " + count(attackOptions) + " attacks"); // Removed - costs 1 TP
    debug("Starting attack execution - " + count(attackOptions) + " options, TP=" + tpLeft);
    
    for (var i = 0; i < count(attackOptions); i++) {
        var option = attackOptions[i];
        // Array indices: 0=type, 1=item, 2=damage, 3=cost, 4=dptp, 5=maxUses, 6=name
        
        if (tpLeft < option[3]) continue;  // cost
        
        // Ensure we try to use the weapon at least once if we have TP
        var uses = option[5];  // Start with possibleUses
        if (uses <= 0 && tpLeft >= option[3]) {
            uses = floor(tpLeft / option[3]);  // Fallback calculation
        }
        uses = min(uses, floor(tpLeft / option[3]));  // Don't exceed current TP
        uses = max(0, uses);  // Ensure non-negative
        
        if (uses > 0) {
            debugLog("Executing: " + option[6] + " (type=" + option[0] + ", uses=" + uses + ", cost=" + option[3] + ")");
        } else {
            debugLog("Skipping " + option[6] + " - uses=" + uses);
            continue;
        }
        
        if (option[0] == "weapon") {  // type
            debugLog("  Processing weapon: " + option[6]);
            // Check if we need to swap weapon (costs 1 TP!)
            if (getWeapon() != option[1]) {
                setWeaponIfNeeded(option[1]);  // This costs 1 TP
                myTP = getTP();  // Update TP after swap
                tpLeft = myTP;
                // Recalculate uses after weapon swap!
                uses = min(floor(tpLeft / option[3]), option[5]);
                if (uses <= 0) continue;  // Skip if no TP left after swap
            }
            for (var j = 0; j < uses; j++) {
                debugLog("    Use #" + (j+1) + " of weapon " + option[6]);
                var result;
                var weaponId = option[1];
                
                // Check if this is an AoE weapon that might need cell targeting
                if (weaponId == WEAPON_GRENADE_LAUNCHER || weaponId == WEAPON_LIGHTNINGER) {
                    // Try direct first
                    debugLog("    Attempting useWeapon on enemy...");
                    result = useWeapon(enemy);
                    if (result == USE_INVALID_TARGET || result == USE_INVALID_POSITION) {
                        // Can't hit directly, use AoE on cell
                        enemyCell = getCell(enemy);
                        result = useWeaponOnCell(enemyCell);
                        if (debugEnabled && turn <= 5) {
                            debugLog("  Using " + option[6] + " on cell " + enemyCell + " (AoE)");
                        }
                    }
                } else {
                    debugLog("    Attempting useWeapon on enemy (direct)...");
                    result = useWeapon(enemy);
                }
                
                debugLog("    Result: " + result);
                
                if (result == USE_SUCCESS) {
                    totalDamage += option[2];  // damage
                    updateErosion(option[2], false);  // Track erosion
                    tpLeft -= option[3];  // cost
                } else if (result == USE_CRITICAL) {
                    var critDamage = option[2] * (1 + CRITICAL_FACTOR);  // Correct crit damage
                    totalDamage += critDamage;
                    updateErosion(critDamage, true);  // Track critical erosion
                    tpLeft -= option[3];  // cost
                    debugLog("CRITICAL HIT with " + option[6] + "!");
                } else {
                    if (debugEnabled && turn <= 5) {
                        debugLog("  Failed to use " + option[6] + ": result=" + result);
                    }
                    break;
                }
            }
        } else {  // chip
            for (var j = 0; j < uses; j++) {
                // Check if this is an AoE chip that needs cell targeting
                var chipId = option[1];
                var result;
                
                // AoE chips that should target cells when not aligned
                if (chipId == CHIP_LIGHTNING || chipId == CHIP_METEORITE || 
                    chipId == CHIP_BURNING || chipId == CHIP_ROCKFALL ||
                    chipId == CHIP_ICE || chipId == CHIP_STALACTITE) {
                    // Try direct first, fallback to cell targeting
                    result = useChip(chipId, enemy);
                    if (result == USE_INVALID_TARGET || result == USE_INVALID_POSITION) {
                        // Can't hit directly, use AoE on cell
                        enemyCell = getCell(enemy);
                        result = useChipOnCell(chipId, enemyCell);
                        if (debugEnabled && turn <= 5) {
                            debugLog("  Using " + option[6] + " on cell " + enemyCell + " (AoE)");
                        }
                    }
                } else {
                    // Non-AoE chip, use directly
                    result = useChip(chipId, enemy);
                }
                
                if (result == USE_SUCCESS) {
                    totalDamage += option[2];  // damage
                    updateErosion(option[2], false);  // Track erosion
                    tpLeft -= option[3];  // cost
                } else if (result == USE_CRITICAL) {
                    var critDamage = option[2] * (1 + CRITICAL_FACTOR);  // Correct crit damage
                    totalDamage += critDamage;
                    updateErosion(critDamage, true);  // Track critical erosion
                    tpLeft -= option[3];  // cost
                    debugLog("CRITICAL HIT with " + option[6] + "!");
                } else {
                    if (debugEnabled && turn <= 5) {
                        debugLog("  Failed to use " + option[6] + ": result=" + result);
                    }
                    break;
                }
            }
        }
        
        // Update TP
        myTP = getTP();
        tpLeft = myTP;
        
        if (tpLeft < 3) break;  // No point continuing with so little TP
    }
    
    if (totalDamage > 0) {
        debugLog("Total damage dealt: " + totalDamage);
        // Track damage for pattern learning
        myLastTurnDamage = totalDamage;
    }
    
    // ENHANCED: Try AoE splash through obstacles with proper patterns!
    if (totalDamage == 0 && myTP >= 5) {
        debugLog("Checking for AoE opportunities (including diagonal patterns)...");
        
        var bestSplash = null;
        var bestDamage = 0;
        
        // Check Grenade Launcher splash positions
        if (inArray(getWeapons(), WEAPON_GRENADE_LAUNCHER)) {
            var splashPositions = findAoESplashPositions(WEAPON_GRENADE_LAUNCHER, myCell, enemyCell);
            
            for (var i = 0; i < count(splashPositions); i++) {
                var splash = splashPositions[i];
                var grenadeBase = 150 + myStrength * 2;
                var damage = grenadeBase * splash["damagePercent"];
                
                if (damage > bestDamage) {
                    bestDamage = damage;
                    bestSplash = splash;
                    bestSplash["weapon"] = WEAPON_GRENADE_LAUNCHER;
                }
            }
        }
        
        // IMPROVED: Check Lightninger diagonal pattern optimization
        if (inArray(getWeapons(), WEAPON_LIGHTNINGER) && myTP >= 5) {
            var lightningerResult = findBestLightningerTarget(myCell);
            
            if (lightningerResult != null && lightningerResult["damage"] > 0) {
                // Compare with standard splash detection
                var standardSplash = findAoESplashPositions(WEAPON_LIGHTNINGER, myCell, enemyCell);
                
                // Use the better of the two methods
                if (lightningerResult["damage"] > bestDamage) {
                    bestDamage = lightningerResult["damage"];
                    bestSplash = [:];
                    bestSplash["target"] = lightningerResult["targetCell"];
                    bestSplash["weapon"] = WEAPON_LIGHTNINGER;
                    bestSplash["damagePercent"] = 1.0;
                    bestSplash["isIndirect"] = (lightningerResult["targetCell"] != enemyCell);
                    bestSplash["patternHits"] = lightningerResult["numHits"];
                    
                    // Log diagonal pattern detection
                    if (count(lightningerResult["cellsHit"]) > 1) {
                        debugLog("Lightninger diagonal pattern: " + count(lightningerResult["cellsHit"]) + " cells hit!");
                    }
                }
            }
        }
        
        // Execute best splash attack
        if (bestSplash != null && bestDamage > 0) {
            var targetCell = bestSplash["target"];
            var weapon = bestSplash["weapon"];
            
            setWeaponIfNeeded(weapon);
            if (useWeaponOnCell(targetCell)) {
                var weaponName = (weapon == WEAPON_GRENADE_LAUNCHER) ? "Grenade" : "Lightninger";
                
                if (bestSplash["isIndirect"]) {
                    debugLog("INDIRECT " + weaponName + " splash through obstacle!");
                    debugLog("Target: " + targetCell + ", Enemy at: " + enemyCell);
                } else {
                    debugLog("Direct " + weaponName + " hit!");
                }
                
                debugLog("Splash distance: " + bestSplash["splashDistance"] + 
                        ", damage: " + round(bestDamage) + 
                        " (" + round(bestSplash["damagePercent"] * 100) + "%)");
                
                totalDamage = bestDamage;
                myLastTurnDamage = bestDamage;
            }
        }
    }
    
    // End of executeAttack function
}


// Function: executeDefensive
function executeDefensive() {
    var hpRatio = myHP / myMaxHP;
    debugLog("Defensive: HP=" + myHP + "/" + myMaxHP + " (" + round(hpRatio*100) + "%), TP=" + myTP);
    
    // Priority 0: ALWAYS check for Liberation opportunity first!
    // Much more aggressive Liberation usage
    if (enemy != null) {
        if (useAntiTankStrategy()) {
            debugLog("Liberation successful - enemy buffs/shields stripped!");
        }
    }
    
    // Priority 1: Check for poison and remove it immediately!
    var myEffects = getEffects(myLeek);
    var hasPoisonEffect = false;
    
    // Check if we have any poison effects (EFFECT_POISON type = 13)
    for (var i = 0; i < count(myEffects); i++) {
        if (myEffects[i][0] == 13) {  // EFFECT_POISON
            hasPoisonEffect = true;
            break;
        }
    }
    
    if (hasPoisonEffect && getCooldown(CHIP_ANTIDOTE) == 0 && myTP >= 3) {
        debugLog("POISON DETECTED! Using Antidote!");
        if (tryUseChip(CHIP_ANTIDOTE, myLeek)) {
            debugLog("Antidote applied - all poisons removed!");
        }
    }
    
    // Priority 2: Smart healing with phase-aware thresholds
    var tactics = getPhaseSpecificTactics();
    var healThreshold = tactics["healThreshold"];
    
    if (hpRatio < healThreshold) {  // Phase-based healing threshold
        debugLog("HEALING TRIGGERED - HP below " + round(healThreshold * 100) + "% (" + GAME_PHASE + " phase)");
        
        // Prioritize multi-turn heals for kiting efficiency
        // HoT allows us to heal WHILE maintaining distance and attacking
        var healChips = [
            CHIP_SERUM,      // 8 TP, 50-55 heal/turn x4 - AOE HoT with 290 WIS!
            CHIP_VACCINE,    // 6 TP, 38-42 heal/turn x3 - Strong HoT
            CHIP_CURE,       // 4 TP, 38-46 instant - ~180 HP with WIS!
            CHIP_ARMORING    // 5 TP, 25-30 max life + heal
        ];
        for (var i = 0; i < count(healChips); i++) {
            var chip = healChips[i];
            tryUseChip(chip, myLeek);  // tryUseChip handles TP and logging
        }
    }
    
    // Priority 3: Shield if expecting damage (2.5x effectiveness with 150 resistance!)
    if (myTP >= 3) {
        // Shield chips are VERY effective with resistance multiplier!
        // Base 150 RES = 2.5x multiplier (shield * 2.5)
        // With Solidification: 330-350 RES = 4.3-4.5x multiplier!
        var shieldChips = [
            CHIP_FORTRESS,   // 6 TP, 7.5% rel shield -> 18.75% with 150 RES, 32% with Solidification!
            CHIP_ARMOR,      // 6 TP, 25 abs shield -> 62.5 with 150 RES, 107 with Solidification!
            CHIP_SHIELD      // 4 TP, 20 abs shield -> 50 with 150 RES, 86 with Solidification!
        ];
        for (var i = 0; i < count(shieldChips); i++) {
            var chip = shieldChips[i];
            tryUseChip(chip, myLeek);  // tryUseChip handles TP and logging
        }
    }
    
    // Priority 3: Buffs if have TP left
    if (myTP >= 3) {
        executeBuffs();
    }
}


// Function: executeBuffs
function executeBuffs() {
    if (myTP < 1) return;
    
    // OPTIMAL BUFF STACKING ORDER
    var buffChips = [];
    
    // Turn 1: Already used Adrenaline, focus on defense + damage
    if (turn == 1) {
        // Fix 7: Steroid before Solidification for better turn 1 damage
        buffChips = [
            CHIP_STEROID,        // 7 TP, +150-170 STR - 570 total STR!
            CHIP_SOLIDIFICATION, // 6 TP, +180-200 RES - shields become 5.5x effective!
            CHIP_MOTIVATION      // 4 TP, +2 TP/turn x3
        ];
    }
    // Turn 2+: We have 23 TP from Adrenaline, go all out!
    else if (turn == 2) {
        buffChips = [
            CHIP_WARM_UP,        // 7 TP, +170-190 AGI - 39% crit chance!
            CHIP_PROTEIN,        // 3 TP, +80-100 STR if Steroid not active
            CHIP_WINGED_BOOTS,   // 6 TP, +3 MP instant
            CHIP_MOTIVATION      // 4 TP, +2 TP/turn if not active
        ];
    }
    // Later turns: maintain buffs
    else {
        buffChips = [
            CHIP_ADRENALINE,     // 1 TP, +5 TP if available again
            CHIP_SOLIDIFICATION, // Re-apply if expired
            CHIP_STEROID,        // Re-apply if expired
            CHIP_WARM_UP,        // Re-apply if expired
            CHIP_MOTIVATION,     // Keep TP flowing
            CHIP_WINGED_BOOTS,   // Movement if needed
            CHIP_LEATHER_BOOTS   // More movement
        ];
    }
    
    for (var i = 0; i < count(buffChips); i++) {
        var chip = buffChips[i];
        if (getCooldown(chip) <= 0) {
            tryUseChip(chip, myLeek);
        }
        if (myTP < 1) break;
    }
}

// === MAIN EXECUTION ===
// NOTE: initialize() is called from V6_main.ls, not here!

// Function to handle early game sequences and special tactics
function executeEarlyGameSequence() {
    // This function should ONLY handle turn 1
    // Turn 2+ should use makeDecision() from V6_main.ls
    
    if (turn != 1) {
        debugLog("executeEarlyGameSequence called on turn " + turn + " - delegating to makeDecision");
        makeDecision();
        return;
    }
    
    // Track bait success from previous turn
    updateBaitSuccess();

    // PRIORITY 1: Liberation if enemy has ANY buffs or shields (turn 1+)
    if (enemy != null && myTP >= 5) {
        var dist = getCellDistance(myCell, enemyCell);
        if (dist <= 6 && hasLOS(myCell, enemyCell)) {
            if (useAntiTankStrategy()) {
                debugLog("=== TURN " + turn + " LIBERATION STRIKE! ===");
            }
        }
    }

    // TURN 1 EXECUTION
    if (turn == 1) {
    // TURN 1: BALANCED OPENING - Defense, ONE buff, then attack
    debugLog("=== TURN 1: BALANCED OPENING ===");
    debugLog("TP: " + myTP + ", Enemy at distance " + enemyDistance);
    
    // PRIORITY 1: SHIELDS if enemy can hit us
    if (enemyDistance <= 10) {
        // Enemy can potentially attack - shield first!
        if (getCooldown(CHIP_SHIELD) == 0 && myTP >= 3) {
            if (tryUseChip(CHIP_SHIELD, myLeek)) {
                myAbsShield = getAbsoluteShield(myLeek);
                debugLog("🛡️ SHIELD: +" + myAbsShield + " absolute shield");
                myTP = getTP();
            }
        }
        
        // Use relative shield too if we have TP
        if (getCooldown(CHIP_FORTRESS) == 0 && myTP >= 4) {
            if (tryUseChip(CHIP_FORTRESS, myLeek)) {
                myRelShield = getRelativeShield(myLeek);
                debugLog("🏰 FORTRESS: +" + myRelShield + "% damage reduction");
                myTP = getTP();
            }
        }
    }
    
    // PRIORITY 2: ONE key buff (not all three!)
    // Choose based on enemy type
    var buffUsed = false;
    
    // If enemy is magic/science based, prioritize resistance
    if (enemyMagic > 400 || enemyScience > 400) {
        if (getCooldown(CHIP_SOLIDIFICATION) == 0 && myTP >= 6 && !buffUsed) {
            if (tryUseChip(CHIP_SOLIDIFICATION, myLeek)) {
                myResistance = getResistance();
                debugLog("💎 SOLIDIFICATION: Resistance now " + myResistance);
                myTP = getTP();
                buffUsed = true;
            }
        }
    }
    
    // Otherwise use Knowledge for wisdom boost
    if (!buffUsed && getCooldown(CHIP_KNOWLEDGE) == 0 && myTP >= 5) {
        if (tryUseChip(CHIP_KNOWLEDGE, myLeek)) {
            var oldWisdom = myWisdom;
            myWisdom = getWisdom();
            var wisBoost = myWisdom - oldWisdom;
            debugLog("📚 KNOWLEDGE: +" + wisBoost + " Wisdom (now " + myWisdom + ")");
            myTP = getTP();
            buffUsed = true;
        }
    }
    
    // PRIORITY 3: POSITION for optimal attack range
    if (myMP > 0) {
        var targetDist = 7;  // Optimal for both Grenade and Lightninger
        
        if (enemyDistance > targetDist + 2) {
            // Too far - approach
            var step = bestApproachStep(enemyCell);
            if (moveToCell(step) > 0) {
                enemyDistance = getCellDistance(myCell, enemyCell);
                debugLog("→ Approached to distance " + enemyDistance);
            }
        } else if (enemyDistance < 4 && enemyDistance > 0) {
            // Too close for Grenade - back up slightly
            var reachable = getReachableCells(myCell, myMP);
            var bestCell = myCell;
            var bestScore = -999;
            
            for (var i = 0; i < min(20, count(reachable)); i++) {
                var cell = reachable[i];
                var dist = getCellDistance(cell, enemyCell);
                if (dist >= 5 && dist <= 8 && hasLOS(cell, enemyCell)) {
                    var score = 100 - abs(dist - 7) * 20;
                    if (score > bestScore) {
                        bestScore = score;
                        bestCell = cell;
                    }
                }
            }
            
            if (bestCell != myCell) {
                if (moveToCell(bestCell) > 0) {
                    enemyDistance = getCellDistance(myCell, enemyCell);
                    debugLog("→ Repositioned to distance " + enemyDistance);
                }
            }
        }
    }
    
    // PRIORITY 4: ATTACK with remaining TP!
    if (myTP >= 5 && enemyDistance <= 10 && hasLOS(myCell, enemyCell)) {
        debugLog("Turn 1 attack with " + myTP + " TP");
        executeAttack();
    }
    
    debugLog("Turn 1 complete. HP: " + myHP + "/" + myMaxHP + ", Shields: " + myAbsShield + "+" + myRelShield + "%, Position: " + enemyDistance);
    } // End of turn 1 block
}  // End of executeEarlyGameSequence

// OLD CODE BELOW - NOT USED ANYMORE
/*
// CRITICAL: Check for teleportation on turn 2+ (high priority) 
} else if (turn >= 2 && shouldUseTeleport()) {
    debugLog("🌀 TELEPORT NEEDED!");
    var bestTeleportCell = findBestTeleportTarget();
    if (executeTeleport(bestTeleportCell)) {
        // Successfully teleported - now attack from new position
        executeAttack();
    }
// Check if we should use bait tactics on turn 2+
} else if (turn >= 2 && shouldUseBaitTactic()) {
    debugLog("🎯 BAIT TACTIC: Setting trap for predictable enemy");
    var baitCell = executeBaitTactic();
    if (baitCell != null) {
        // Actually move to the bait position
        if (moveToCell(baitCell) > 0) {
            debugLog("Moved to bait position");
        }
        // After baiting, still perform combat actions
        executeAttack();
        if (myTP >= 4) executeDefensive();
    }
} else if (turn <= 3 && enemyDistance > 12) {
    // Turns 2-3: Continue setup if enemy is very far
    debugLog("=== EARLY GAME CONTINUED SETUP ===");
    
    if (turn == 2) {
        // Turn 2: Get remaining key buffs
        debugLog("Turn 2: Additional buffs");
        
        // Elevation for max HP
        if (getCooldown(CHIP_ELEVATION) == 0 && myTP >= 6) {
            if (tryUseChip(CHIP_ELEVATION, myLeek)) {
                var oldMaxHP = myMaxHP;
                myMaxHP = getTotalLife();
                myHP = getLife();
                var hpGain = myMaxHP - oldMaxHP;
                MAX_HP_BUFFED = true;
                debugLog("📈 ELEVATION: +" + hpGain + " max HP (now " + myMaxHP + ")");
                myTP = getTP();
            }
        }
        
        // Armoring for more HP
        if (getCooldown(CHIP_ARMORING) == 0 && myTP >= 5) {
            if (tryUseChip(CHIP_ARMORING, myLeek)) {
                var oldMaxHP = myMaxHP;
                myMaxHP = getTotalLife();
                myHP = getLife();
                var armorHP = myMaxHP - oldMaxHP;
                debugLog("🛡️ ARMORING: +" + armorHP + " max HP (total " + myMaxHP + ")");
                myTP = getTP();
            }
        }
        
        // Move closer and try to attack
        if (myMP > 0) {
            var step = bestApproachStep(enemyCell);
            if (moveToCell(step) > 0) {
                enemyDistance = getCellDistance(myCell, enemyCell);
            }
        }
        
        if (myTP >= 5 && enemyDistance <= 10) {
            executeAttack();
        }
    } else if (turn == 3) {
        // Turn 3: Full engagement
        debugLog("=== TURN 2: ASSESSMENT & ENGAGEMENT ===");
        debugLog("HP: " + myHP + "/" + myMaxHP + ", TP: " + myTP + ", Enemy HP: " + enemyHP);
        
        // ASSESSMENT: Check threat level
        var myEHP = calculateEHP(myHP, myAbsShield, myRelShield, 0, myResistance);
        var enemyEID = calculateEID(myCell);
        var threatRatio = myEHP > 0 ? enemyEID / myEHP : 1.0;
        
        debugLog("Threat: EID=" + enemyEID + ", EHP=" + myEHP + ", ratio=" + round(threatRatio * 100) + "%");
        
        if (threatRatio > 0.5) {
            // HIGH THREAT - Defensive sequence
            debugLog("⚠️ High threat - defensive stance");
            
            // Priority 1: SOLIDIFICATION for massive resistance
            if (getCooldown(CHIP_SOLIDIFICATION) == 0 && myTP >= 6) {
                if (tryUseChip(CHIP_SOLIDIFICATION, myLeek)) {
                    var oldResistance = myResistance;
                    myResistance = getResistance();
                    var resBoost = myResistance - oldResistance;
                    debugLog("💪 SOLIDIFICATION: +" + resBoost + " Resistance (now " + myResistance + ")");
                    myTP = getTP();
                }
            }
            
            // Priority 2: Shields
            if (myTP >= 4 && getCooldown(CHIP_SHIELD) == 0) {
                tryUseChip(CHIP_SHIELD, myLeek);
                myAbsShield = getAbsoluteShield(myLeek);
                myTP = getTP();
            }
            
            // Priority 3: Attack with remaining TP
            executeAttack();
            
        } else {
            // LOW THREAT - Consider offensive buffs
            debugLog("✅ Low threat - checking if STEROID helps");
            
            // Only use STEROID if it significantly improves damage
            var currentDamage = calculateDamageFrom(myCell);
            // STEROID adds flat strength (250-270), not percentage
            var simStrength = myStrength + 260;  // Approximate flat boost
            var weaponBoost = floor((simStrength - myStrength) * 2);  // Rough weapon damage increase
            
            if (weaponBoost > 100 && getCooldown(CHIP_STEROID) == 0 && myTP >= 7) {
                if (tryUseChip(CHIP_STEROID, myLeek)) {
                    myStrength = getStrength();
                    debugLog("💉 STEROID: Damage boost ~" + weaponBoost + " (STR: " + myStrength + ")");
                    myTP = getTP();
                }
            }
            
            // Maximum attacks
            executeAttack();
            
            // Shield with leftover TP
            if (myTP >= 4 && getCooldown(CHIP_SHIELD) == 0) {
                tryUseChip(CHIP_SHIELD, myLeek);
                myTP = getTP();
            }
        }
    } else {
        // Turn 3+: Continue with adaptive combat
        debugLog("Turn " + turn + " - Adaptive combat");
        
        // Check for critical health and use REGENERATION if available
        if (myHP < myMaxHP * 0.3 && !EMERGENCY_HEAL_USED && getCooldown(CHIP_REGENERATION) == 0 && myTP >= 8) {
            if (tryUseChip(CHIP_REGENERATION, myLeek)) {
                var oldHP = myHP;
                myHP = getLife();
                var healAmount = myHP - oldHP;  // Actual heal amount (scales with Wisdom)
                EMERGENCY_HEAL_USED = true;
                debugLog("💚 REGENERATION: +" + healAmount + " HP (emergency heal)");
                myTP = getTP();
            }
        }
        
        // Check for teleport opportunity FIRST (before other actions)
        if (shouldUseTeleport()) {
            var bestTeleportCell = findBestTeleportTarget();
            if (executeTeleport(bestTeleportCell)) {
                // Successfully teleported - now attack from new position
                executeAttack();
            }
        }
        
        // Continue with adaptive combat
        var myEHP = calculateEHP(myHP, myAbsShield, myRelShield, 0, myResistance);
        var threatRatio = calculateEID(myCell) / max(1, myEHP);
        
        if (threatRatio > 0.6) {
            // High threat - defensive priority
            executeDefensive();
            if (myTP >= 3) executeAttack();
        } else {
            // Low threat - offensive priority
            executeAttack();
            if (myTP >= 4) executeDefensive();
        }
        
        // Original buff maintenance logic
        if (getCooldown(CHIP_WARM_UP) == 0 && myTP >= 7) {
            if (tryUseChip(CHIP_WARM_UP, myLeek)) {
                debugLog("→ Warm Up: " + round(getAgility()/10) + "% crit");
                myAgility = getAgility();
                myTP = getTP();
            }
        }
        if (getCooldown(CHIP_PROTEIN) == 0 && myTP >= 3) {
            tryUseChip(CHIP_PROTEIN, myLeek);
            myStrength = getStrength();
            myTP = getTP();
        }
        
        // SEQUENCE 2: Movement buffs for positioning
        if (getCooldown(CHIP_WINGED_BOOTS) == 0 && myTP >= 6) {
            tryUseChip(CHIP_WINGED_BOOTS, myLeek);
            myMP = getMP();
            myTP = getTP();
        }
        
        // SEQUENCE 3: Positioning based on weapon range
        if (enemyDistance > 10 && myMP > 0) {
            var step = bestApproachStep(enemyCell);
            moveToCell(step);
            enemyDistance = getCellDistance(myCell, enemyCell);
            debugLog("→ Moved to distance " + enemyDistance);
        } else if (enemyDistance < 6 && myMP > 0) {
            // Try to get to Lightninger range
            var cells = getCellsInRange(myCell, myMP);
            for (var i = 0; i < count(cells); i++) {
                var cell = cells[i];
                var dist = getCellDistance(cell, enemyCell);
                if (dist >= 6 && dist <= 8 && hasLOS(cell, enemyCell)) {
                    moveToCell(cell);
                    enemyDistance = dist;
                    debugLog("→ Repositioned to optimal range " + dist);
                    break;
                }
            }
        }
        
        // SEQUENCE 4: Attack round 1
        debugLog("→ Attack sequence starting with " + myTP + " TP at range " + enemyDistance);
        
        // FORCE ATTACK at range 10 with Lightninger if available
        if (enemyDistance >= 6 && enemyDistance <= 10 && myTP >= 5) {
            if (inArray(getWeapons(), WEAPON_LIGHTNINGER)) {
                setWeaponIfNeeded(WEAPON_LIGHTNINGER);
                var shots = 0;
                while (myTP >= 5 && shots < 2) {
                    var result = useWeapon(enemy);
                    if (result == USE_SUCCESS || result == USE_CRITICAL) {
                        shots++;
                        myTP = getTP();
                        if (result == USE_CRITICAL) {
                            debugLog("CRITICAL Lightninger!");
                        }
                    } else {
                        debugLog("Failed to use Lightninger: " + result);
                        break;
                    }
                }
                debugLog("→ Lightninger: " + shots + " shots fired");
            }
        } else {
            executeAttack();
        }
        myTP = getTP();
        
        // SEQUENCE 5: EID check - continue or defend?
        var currentEID = eidOf(myCell);
        myEHP = calculateEHP(myHP, myAbsShield, myRelShield, 0, myResistance);
        var eidRatio = currentEID / myEHP;
        
        if (eidRatio < 0.5) {
            // Safe - attack again
            debugLog("→ EID safe (" + round(eidRatio*100) + "%), continuing attacks");
            if (myTP >= 3) {
                executeAttack();
                myTP = getTP();
            }
        } else {
            // Dangerous - shield up
            debugLog("→ EID dangerous (" + round(eidRatio*100) + "%), applying shields");
            if (getCooldown(CHIP_FORTRESS) == 0 && myTP >= 6) tryUseChip(CHIP_FORTRESS, myLeek);
            if (getCooldown(CHIP_ARMOR) == 0 && myTP >= 6) tryUseChip(CHIP_ARMOR, myLeek);
            if (getCooldown(CHIP_SHIELD) == 0 && myTP >= 4) tryUseChip(CHIP_SHIELD, myLeek);
        }
    }
    
} else if (!shouldUseBaitTactic()) {
    // SEQUENCED COMBAT STRATEGY WITH EID DECISION MAKING
    debugLog("=== TURN " + turn + " SEQUENCED COMBAT ===");
    
    // PHASE 1: BUFF SEQUENCE (Prioritize TP → STR → AGI → WIS buffs)
    debugLog("PHASE 1: Buff sequence");
    
    // 1A: Adrenaline for TP boost (highest priority)
    if (getCooldown(CHIP_ADRENALINE) == 0 && myTP >= 1) {
        if (tryUseChip(CHIP_ADRENALINE, myLeek)) {
            debugLog("→ Adrenaline: +5 TP next turn");
            myTP = getTP();
        }
    }
    
    // 1B: Motivation for sustained TP
    if (getCooldown(CHIP_MOTIVATION) == 0 && myTP >= 4) {
        if (tryUseChip(CHIP_MOTIVATION, myLeek)) {
            debugLog("→ Motivation: +2 TP/turn");
            myTP = getTP();
        }
    }
    
    // 1C: Combat buffs in priority order
    if (myTP >= 6) {
        // Solidification for defense multiplier (shields become 5.3x effective)
        if (getResistance() < 300 && getCooldown(CHIP_SOLIDIFICATION) == 0) {
            if (tryUseChip(CHIP_SOLIDIFICATION, myLeek)) {
                debugLog("→ Solidification: Shields 5.3x effective");
                myResistance = getResistance();
                myTP = getTP();
            }
        }
        
        // Steroid for damage (570+ STR)
        if (getStrength() < 500 && getCooldown(CHIP_STEROID) == 0 && myTP >= 7) {
            if (tryUseChip(CHIP_STEROID, myLeek)) {
                debugLog("→ Steroid: " + getStrength() + " STR");
                myStrength = getStrength();
                myTP = getTP();
            }
        }
        
        // Warm Up for crits (39% crit chance)
        if (getAgility() < 350 && getCooldown(CHIP_WARM_UP) == 0 && myTP >= 7) {
            if (tryUseChip(CHIP_WARM_UP, myLeek)) {
                debugLog("→ Warm Up: " + round(getAgility()/10) + "% crit");
                myAgility = getAgility();
                myTP = getTP();
            }
        }
        
        // Protein as backup STR buff
        if (getStrength() < 500 && getCooldown(CHIP_PROTEIN) == 0 && myTP >= 3) {
            tryUseChip(CHIP_PROTEIN, myLeek);
            myStrength = getStrength();
            myTP = getTP();
        }
    }
    
    // PHASE 2: POSITIONING (Strategy-based positioning)
    debugLog("PHASE 2: " + COMBAT_STRATEGY + " positioning (EID=" + round(eidOf(myCell)) + ")");
    
    var myEHP = calculateEHP(myHP, myAbsShield, myRelShield, 0, myResistance);
    var currentEID = eidOf(myCell);
    var eidRatio = currentEID / myEHP;
    
    if (COMBAT_STRATEGY == "KITE") {
        // KITE: Hit and run - attack then retreat
        debugLog("→ Kiting strategy - hit and run");
        
        // CRITICAL FIX: Approach if too far (beyond weapon range of 12)
        if (enemyDistance > 12 && myMP > 0) {
            // Use A* to get closer efficiently
            var targetCell = enemyCell;
            var path = getPath(myCell, targetCell);
            if (path != null && count(path) > 0) {
                // Move as close as we can, aiming for range 8-10
                var steps = min(myMP, count(path));
                for (var s = 0; s < steps; s++) {
                    var nextCell = path[s];
                    var newDist = getCellDistance(nextCell, enemyCell);
                    if (newDist <= 10) {
                        // Stop when we reach good attack range
                        moveToCell(nextCell);
                        enemyDistance = newDist;
                        debugLog("→ Approached to attack range " + newDist);
                        break;
                    } else if (s == steps - 1) {
                        // Use all MP if still too far
                        moveToCell(nextCell);
                        enemyDistance = newDist;
                        debugLog("→ Moved closer to " + newDist);
                    }
                }
            }
        } else if (enemyDistance > 10 && myMP > 0) {
            // Fine-tune positioning for optimal range 8-10
            var approachCells = getCellsInRange(myCell, myMP);
            for (var i = 0; i < count(approachCells); i++) {
                var cell = approachCells[i];
                var dist = getCellDistance(cell, enemyCell);
                if (dist >= 8 && dist <= 10 && hasLOS(cell, enemyCell)) {
                    moveToCell(cell);
                    enemyDistance = dist;
                    debugLog("→ Positioned at kiting distance " + dist);
                    break;
                }
            }
        }
        // Attacks happen in PHASE 3
        // Retreat happens in PHASE 4
        
    } else if (COMBAT_STRATEGY == "RUSH") {
        // RUSH: Close distance aggressively
        debugLog("→ Rush strategy - closing distance");
        
        if (enemyDistance > 3 && myMP > 0) {
            var targetCells = getCellsInRange(myCell, myMP);
            var bestCell = myCell;
            var minDist = enemyDistance;
            
            for (var i = 0; i < min(30, count(targetCells)); i++) {
                var cell = targetCells[i];
                var dist = getCellDistance(cell, enemyCell);
                if (dist < minDist && dist >= 1 && hasLOS(cell, enemyCell)) {
                    minDist = dist;
                    bestCell = cell;
                }
            }
            
            if (bestCell != myCell) {
                moveToCell(bestCell);
                enemyDistance = getCellDistance(myCell, enemyCell);
                debugLog("→ Rushed to distance " + enemyDistance);
            }
        }
        
    } else if (COMBAT_STRATEGY == "SUSTAINED") {
        // SUSTAINED: Maintain optimal DPS range
        debugLog("→ Sustained DPS strategy");
        
        // Stay at range 6-7 for consistent damage
        if ((enemyDistance < 6 || enemyDistance > 7) && myMP > 0) {
            var targetCells = getCellsInRange(myCell, myMP);
            for (var i = 0; i < count(targetCells); i++) {
                var cell = targetCells[i];
                var dist = getCellDistance(cell, enemyCell);
                if (dist >= 6 && dist <= 7 && hasLOS(cell, enemyCell)) {
                    moveToCell(cell);
                    enemyDistance = dist;
                    debugLog("→ Positioned for sustained DPS at range " + dist);
                    break;
                }
            }
        }
        
    } else {
        // ADAPTIVE: Standard EID-based positioning
        if (eidRatio < 0.3) {
            debugLog("→ Safe position, attacking aggressively");
            // FIX: Don't call expensive makeDecision() - just attack
            executeAttack();
        } else if (eidRatio < 0.6) {
            debugLog("→ Moderate danger, balanced approach");
            // FIX: Don't call expensive makeDecision() - use simpler logic
            if (myMP > 0) {
                if (enemyDistance > optimalAttackRange + 2) {
                    var step = bestApproachStep(enemyCell);
                    moveToCell(step);
                } else if (enemyDistance < optimalAttackRange - 2) {
                    repositionDefensive();
                }
            }
        } else {
            debugLog("→ HIGH DANGER, repositioning!");
            if (myMP > 0) {
                repositionDefensive();
            }
        }
    }
    
    // PHASE 3: ATTACK SEQUENCE - Use ALL available TP for maximum damage!
    if (enemy != null && myTP >= 3) {
        debugLog("PHASE 3: Attack sequence");
        
        // Keep attacking until we run out of TP or weapons
        var attackRounds = 0;
        while (myTP >= 3 && attackRounds < 5) {  // Max 5 rounds to prevent infinite loops
            var tpBefore = myTP;
            executeAttack();
            myTP = getTP();
            attackRounds++;
            
            // If TP didn't change, we couldn't attack - stop trying
            if (myTP == tpBefore) break;
        }
        
        debugLog("→ Completed " + attackRounds + " attack rounds, TP remaining: " + myTP);
    }
    
    // PHASE 4: EID DECISION - Continue aggression or defend/heal?
    if (enemy != null) {
        debugLog("PHASE 4: EID Decision");
        
        // Recalculate EID after attacks
        currentEID = eidOf(myCell);
        myEHP = calculateEHP(myHP, myAbsShield, myRelShield, 0, myResistance);
        eidRatio = currentEID / myEHP;
        var hpRatio = myHP / myMaxHP;
        
        debugLog("→ Current state: HP=" + round(hpRatio*100) + "%, EID ratio=" + round(eidRatio*100) + "%");
        
        // Special handling for KITE strategy - only retreat if in danger OR have MP to spare
        if (COMBAT_STRATEGY == "KITE" && myMP > 0 && (eidRatio > 0.4 || myMP >= 3)) {
            debugLog("→ Kiting retreat phase");
            enemyDistance = getCellDistance(myCell, enemyCell);
            
            // Only retreat if enemy is too close or we're taking too much damage
            if (enemyDistance <= 7 || eidRatio > 0.4) {
                // Try to retreat to max range
                var retreatCells = getCellsInRange(myCell, myMP);
                var bestRetreat = null;
                var maxDist = enemyDistance;
                
                for (var i = 0; i < count(retreatCells); i++) {
                    var cell = retreatCells[i];
                    if (!isObstacle(cell) && cell != myCell) {
                        var newDist = getCellDistance(cell, enemyCell);
                        if (newDist >= 9 && newDist <= 10 && hasLOS(cell, enemyCell)) {
                            if (newDist > maxDist) {
                                maxDist = newDist;
                                bestRetreat = cell;
                            }
                        }
                    }
                }
                
                if (bestRetreat != null) {
                    moveToCell(bestRetreat);
                    debugLog("→ Retreated to distance " + getCellDistance(myCell, enemyCell));
                }
            } else {
                debugLog("→ Already at safe distance " + enemyDistance + ", saving MP");
            }
        } else if (eidRatio > 0.7 || hpRatio < 0.4) {
            // CRITICAL: Must defend/heal immediately
            debugLog("→ CRITICAL! Defending and healing");
            
            // Apply shields first (5.3x effective with Solidification!)
            if (myTP >= 4) {
                if (getCooldown(CHIP_FORTRESS) == 0 && myTP >= 6) tryUseChip(CHIP_FORTRESS, myLeek);
                if (getCooldown(CHIP_ARMOR) == 0 && myTP >= 6) tryUseChip(CHIP_ARMOR, myLeek);
                if (getCooldown(CHIP_SHIELD) == 0 && myTP >= 4) tryUseChip(CHIP_SHIELD, myLeek);
            }
            
            // Heal if very low
            if (hpRatio < 0.4 && myTP >= 4) {
                if (getCooldown(CHIP_CURE) == 0) tryUseChip(CHIP_CURE, myLeek);
                if (getCooldown(CHIP_SERUM) == 0 && myTP >= 8) tryUseChip(CHIP_SERUM, myLeek);
                if (getCooldown(CHIP_VACCINE) == 0 && myTP >= 6) tryUseChip(CHIP_VACCINE, myLeek);
            }
            
            // Reposition if we have MP
            if (myMP > 0) {
                repositionDefensive();
            }
            
        } else if (eidRatio > 0.4) {
            // Moderate danger - apply shields while continuing to attack
            debugLog("→ Moderate danger, shielding while attacking");
            
            if (myTP >= 4) {
                if (getCooldown(CHIP_SHIELD) == 0) tryUseChip(CHIP_SHIELD, myLeek);
                myTP = getTP();
            }
            
            // One more attack if possible
            if (myTP >= 3) {
                executeAttack();
            }
            
        } else {
            // Safe - continue maximum aggression
            debugLog("→ Safe position, continuing aggression");
            
            // Use all remaining TP for attacks (max 3 iterations to prevent infinite loop)
            var attackCount = 0;
            var prevTP = myTP;
            while (myTP >= 3 && enemy != null && attackCount < 3) {
                executeAttack();
                myTP = getTP();
                attackCount++;
                // If TP didn't change, we can't attack, so break
                if (myTP == prevTP) break;
                prevTP = myTP;
            }
        }
    }
    
    // PHASE 5: Use any remaining TP efficiently
    if (myTP >= 3) {
        // Apply any remaining buffs or shields
        if (getCooldown(CHIP_SHIELD) == 0 && myTP >= 4) tryUseChip(CHIP_SHIELD, myLeek);
        if (getCooldown(CHIP_LEATHER_BOOTS) == 0 && myTP >= 3) tryUseChip(CHIP_LEATHER_BOOTS, myLeek);
    }
}

if (myMP > 0 && canSpendOps(10000)) {
    // Final repositioning if we have MP left
    var currentEID = eidOf(myCell);
    var myEHP = calculateEHP(myHP, myAbsShield, myRelShield, 0, myResistance);
    
    if (currentEID > myEHP * 0.5) {
        repositionDefensive();
    }
}

    var opsUsed = getOperations() - opsStartTurn;
    debugLog("Turn " + turn + " complete. Ops used: " + opsUsed);
}  // End of executeEarlyGameSequence function
*/

// Function: simplifiedCombat
function simplifiedCombat() {
    // Ultra-simple combat for panic mode
    if (enemyDistance <= 10 && hasLOS(myCell, enemyCell)) {
        // Just attack with best available weapon
        if (enemyDistance <= 4) {
            setWeaponIfNeeded(WEAPON_RHINO);
        } else if (enemyDistance <= 7) {
            setWeaponIfNeeded(WEAPON_GRENADE_LAUNCHER);
        } else {
            setWeaponIfNeeded(WEAPON_LIGHTNINGER);
        }
        useWeapon(enemy);
    } else if (myMP > 0) {
        // Simple move toward enemy
        var step = bestApproachStep(enemyCell);
        if (step != myCell) {
            moveToCell(step);
        }
    }
}

