// V6 Module: combat/execute_combat.ls
// Combat execution
// Auto-generated from V5.0 script

// Include M-Laser tactics for laser targeting
include("m_laser_tactics");

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
    
    // NEW: Check for optimal damage sequence first
    var mySTR = getStrength();
    var darkKatanaSelfDmg = 44 * (1 + mySTR / 100);  // Calculate self-damage once at function level
    var optimalSequence = getBestDamageSequence(myTP, dist, myHP, mySTR);
    if (optimalSequence != null && optimalSequence[2] >= getLife(enemy) * 0.5) {
        // If sequence can deal 50%+ enemy HP, execute it
        debugLog("Using optimal damage sequence: " + optimalSequence[4]);
        var dmgDealt = executeDamageSequence(optimalSequence, enemy);
        if (dmgDealt > 0) {
            debugLog("Sequence executed for " + dmgDealt + " damage");
            return;
        }
    }
    
    // SMART ATTACK: Use damage calculation to find best weapon/chip combo!
    // Commented out to prevent log spam: debugLog("Smart attack at range " + dist + ", TP=" + myTP);
    
    // POSITIONING CHECK: Move to OPTIMAL weapon range, not just ANY attack range
    // Calculate damage we can do from current position
    var currentPositionDamage = 0;
    var shouldReposition = false;  // Declare early since we use it in multiple places
    var myWeapons = getWeapons();
    var myChips = getChips();
    
    // Calculate best damage from current position
    if (hasLine) {
        // Rifle check
        if (dist >= 7 && dist <= 9 && inArray(myWeapons, WEAPON_RIFLE)) {
            currentPositionDamage = max(currentPositionDamage, 76 * 2);  // ~76 damage, 2 uses
        }
        // M-Laser check
        if (dist >= 5 && dist <= 12 && inArray(myWeapons, WEAPON_M_LASER) && isOnSameLine(myCell, enemyCell)) {
            currentPositionDamage = max(currentPositionDamage, 95);  // ~95 damage
        }
        // Grenade check (lower priority)
        if (dist >= 4 && dist <= 7 && inArray(myWeapons, WEAPON_GRENADE_LAUNCHER)) {
            currentPositionDamage = max(currentPositionDamage, 150 + mySTR * 2);
        }
    }
    // Dark Katana check
    if (dist == 1 && inArray(myWeapons, WEAPON_DARK_KATANA)) {
        // Dark Katana damage scales with strength: BaseDamage * (1 + Strength/100)
        var darkKatanaDamage = 99 * (1 + mySTR / 100);
        currentPositionDamage = max(currentPositionDamage, darkKatanaDamage * 2);  // 2 uses
    }
    
    // SPECIAL: If we're at close range (2-4) with Dark Katana, we should move to melee!
    // Check if we can survive the self-damage (44 base, scales with strength)
    if (dist >= 2 && dist <= 4 && inArray(myWeapons, WEAPON_DARK_KATANA) && myHP > darkKatanaSelfDmg * 2) {
        // Can we reach melee this turn?
        var meleeReachable = false;
        var reachableCells = getReachableCells(myCell, myMP);
        for (var i = 0; i < count(reachableCells); i++) {
            if (getCellDistance(reachableCells[i], enemyCell) == 1) {
                meleeReachable = true;
                break;
            }
        }
        if (meleeReachable) {
            shouldReposition = true;
            debugLog("Close range (" + dist + ") - should move to melee for Dark Katana!");
        }
    }
    
    // ALWAYS check if we can do MORE damage from a different position
    // Even if we can attack from here, maybe we can do BETTER damage elsewhere!
    // shouldReposition already declared above
    var bestRepositionDamage = currentPositionDamage;
    
    // Quick check: Are we in suboptimal weapon range?
    if (dist >= 4 && dist <= 7 && hasLine) {
        // We're in grenade range - check if we could use better weapons
        if (inArray(myWeapons, WEAPON_RIFLE) && (dist < 7 || dist > 9)) {
            shouldReposition = true;  // Try to get to rifle range (7-9)
            debugLog("Have rifle but not in range - should reposition from grenade range!");
        } else if (inArray(myWeapons, WEAPON_M_LASER) && 
                   (dist < 5 || dist > 12 || !isOnSameLine(myCell, enemyCell))) {
            shouldReposition = true;  // Try to get to M-Laser range/alignment
            debugLog("Have M-Laser but not aligned - should reposition!");
        }
    }
    
    // Also reposition if we're at edge and using grenade
    if (!shouldReposition && dist >= 4 && dist <= 7) {
        // Check if we're near map edge (limits positioning options)
        var cellX = getCellX(myCell);
        var cellY = getCellY(myCell);
        var nearEdge = (cellX <= 2 || cellX >= 15 || cellY <= 2 || cellY >= 15);
        
        if (nearEdge && inArray(myWeapons, WEAPON_RIFLE)) {
            shouldReposition = true;
            debugLog("At map edge with grenade range - repositioning for rifle!");
        }
    }
    
    // Only reposition if we can't attack OR we're in suboptimal range
    if (myMP > 0 && (currentPositionDamage == 0 || shouldReposition)) {
        debugLog("Can't attack from range " + dist + ", repositioning...");
        // Try to get to optimal range for our CURRENT weapons
        // Priority: Rifle (7-9) > M-Laser (5-12) > Grenade (4-7) > Dark Katana (1)
        var reachable = getReachableCells(myCell, myMP);
        var bestCell = myCell;
        var bestScore = -999999;
        
        for (var i = 0; i < min(30, count(reachable)); i++) {
            var cell = reachable[i];
            var newDist = getCellDistance(cell, enemyCell);
            var score = 0;
            
            // Calculate potential damage from this position
            var potentialDamage = 0;
            
            // PRIORITY 1: Dark Katana at melee (highest damage per TP!)
            // Check if we can survive the self-damage
            if (newDist == 1 && inArray(myWeapons, WEAPON_DARK_KATANA) && myHP > darkKatanaSelfDmg) {
                // Dark Katana damage scales with strength: BaseDamage * (1 + Strength/100)
                var darkKatanaDamage = 99 * (1 + mySTR / 100);
                potentialDamage = darkKatanaDamage * 2;  // Can attack immediately, 2 uses
                score = 12000;  // HIGHEST priority when healthy!
                debugLog("  Cell " + cell + ": MELEE position for Dark Katana (" + round(darkKatanaDamage) + " dmg/hit)!");
            }
            // PRIORITY 2: Rifle range (consistent, safe)
            else if (hasLOS(cell, enemyCell)) {
                if (newDist >= 7 && newDist <= 9 && inArray(myWeapons, WEAPON_RIFLE)) {
                    potentialDamage = 76 * 2;  // 2 shots
                    score = 10000;  // High priority
                    if (newDist == 8) score = 11000;  // Perfect range
                }
                // PRIORITY 3: M-Laser range
                else if (newDist >= 5 && newDist <= 12 && inArray(myWeapons, WEAPON_M_LASER) && isOnSameLine(cell, enemyCell)) {
                    potentialDamage = max(potentialDamage, 95);
                    score = max(score, 8000);  // Good alternative
                }
                // Grenade range - prioritize when other weapons unavailable
                else if (newDist >= 4 && newDist <= 7 && inArray(myWeapons, WEAPON_GRENADE_LAUNCHER)) {
                    potentialDamage = max(potentialDamage, 150 + mySTR * 2);
                    // Higher priority when we're currently out of all weapon ranges
                    if (dist > 8 || (dist == 8 && currentPositionDamage == 0)) {
                        score = max(score, 5000);  // Better option when no alternatives
                        debugLog("  Cell " + cell + ": Grenade range (good when out of other ranges)");
                    } else {
                        score = max(score, 2000);  // Lower priority when other options exist
                        debugLog("  Cell " + cell + ": Grenade range (backup option)");
                    }
                }
                
                // BONUS: Moving from grenade range to rifle range
                if (dist >= 4 && dist <= 6 && newDist >= 7 && newDist <= 9) {
                    score += 3000;  // Extra incentive to leave grenade range
                    debugLog("Bonus for moving from grenade to rifle range!");
                }
            }
            // Dark Katana melee range without LOS
            else if (newDist == 1 && inArray(myWeapons, WEAPON_DARK_KATANA)) {
                // Dark Katana damage scales with strength: BaseDamage * (1 + Strength/100)
                var darkKatanaDamage = 99 * (1 + mySTR / 100);
                potentialDamage = darkKatanaDamage * 2;
                score = 6000;  // Good damage even without LOS
            }
            
            // Only consider cells that improve our damage potential OR allow better weapons
            // Exception: At range 8, grenade launcher is out of range, so moving to 7 is beneficial
            if (potentialDamage <= currentPositionDamage && !(dist == 8 && newDist == 7)) {
                // Skip if no improvement, unless we're moving from 8 to 7 to access grenade launcher
                if (dist >= 7 && dist <= 9 && currentPositionDamage > 0) {
                    continue;  // Already in good range with attack options
                }
            }
            
            // Add EID consideration (avoid dangerous positions)
            var eid = calculateEID(cell);
            score -= eid * 0.3;
            
            if (score > bestScore) {
                bestScore = score;
                bestCell = cell;
            }
        }
        
        if (bestCell != myCell && bestScore > 0) {
            var newDist = getCellDistance(bestCell, enemyCell);
            debugLog("Moving from range " + dist + " to range " + newDist);
            if (moveToCell(bestCell) > 0) {
                // Update all position variables after moving
                myCell = getCell();
                dist = getCellDistance(myCell, enemyCell);
                hasLine = hasLOS(myCell, enemyCell);
                enemyDistance = dist;
                myMP = getMP();
            }
        } else if (bestScore <= 0) {
            debugLog("No good attack position reachable this turn");
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
                // Special check for M-Laser - requires straight line alignment
                if (w == WEAPON_M_LASER) {
                    if (!isOnSameLine(myCell, enemyCell)) {
                        debugLog("    ✗ M-Laser requires straight line alignment");
                        return acc;  // Skip this weapon
                    }
                }
                debugLog("    ✓ Added weapon: " + getWeaponName(w));
                var damage = getWeaponDamage(w, myLeek);
                
                // Check for multi-hit potential in multi-enemy battles
                var multiHitBonus = 1.0;
                if (count(getAliveEnemies()) > 1) {
                    if (w == WEAPON_M_LASER) {
                        // Check laser multi-hit
                        var laserTarget = getBestLaserTarget();
                        if (laserTarget != null) {
                            var multiValue = calculateMultiHitValue(w, laserTarget);
                            if (multiValue > damage) {
                                damage = multiValue;  // Use multi-hit damage
                                multiHitBonus = multiValue / getWeaponDamage(w, myLeek);
                                debugLog("    💥 M-Laser multi-hit potential: x" + round(multiHitBonus * 10) / 10);
                            }
                        }
                    } else if (w == WEAPON_GRENADE_LAUNCHER) {
                        // Check grenade AoE multi-hit
                        var aoeTarget = getBestAoETarget(w);
                        if (aoeTarget != null) {
                            var multiValue = calculateMultiHitValue(w, aoeTarget);
                            if (multiValue > damage) {
                                damage = multiValue;  // Use multi-hit damage
                                multiHitBonus = multiValue / getWeaponDamage(w, myLeek);
                                debugLog("    💥 Grenade multi-hit potential: x" + round(multiHitBonus * 10) / 10);
                            }
                        }
                    }
                }
                
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
                
                // Prioritize our best weapons!
                if (w == WEAPON_RIFLE) {
                    // Rifle is reliable, good damage, good range
                    dptp = dptp * 2.0; // 100% bonus - our BEST consistent weapon
                    debugLog("    Rifle strongly prioritized - reliable damage");
                } else if (w == WEAPON_M_LASER) {
                    // M-Laser has excellent damage and range
                    dptp = dptp * 1.8; // 80% bonus - high damage line weapon
                    // Additional bonus for multi-hit
                    if (multiHitBonus > 1.0) {
                        dptp = dptp * (1 + (multiHitBonus - 1) * 0.5);  // Scale with multi-hit
                        debugLog("    M-Laser multi-hit bonus applied!");
                    }
                    debugLog("    M-Laser prioritized - high damage");
                } else if (w == WEAPON_GRENADE_LAUNCHER) {
                    // Grenade should ONLY be used when no LOS or significant multi-hit
                    // SPECIAL: At close range, prefer moving to melee for Dark Katana!
                    if (dist <= 3 && inArray(weapons, WEAPON_DARK_KATANA) && myHP > darkKatanaSelfDmg) {
                        // We're close enough to use Dark Katana instead!
                        dptp = dptp * 0.1; // 90% penalty - Dark Katana is better
                        debugLog("    Grenade PENALIZED - close enough for Dark Katana!");
                    } else if (!hasLine) {
                        // Major bonus when we can't hit directly
                        var grenadeTarget = findBestGrenadeTarget(myCell);
                        if (grenadeTarget != null && !grenadeTarget["directHit"]) {
                            dptp = dptp * 1.5; // 50% bonus for indirect hits
                            debugLog("    Grenade useful - no LOS!");
                        }
                    } else if (multiHitBonus > 1.5) {
                        // Only prioritize for SIGNIFICANT multi-hit (1.5x+ damage)
                        dptp = dptp * (1 + (multiHitBonus - 1) * 0.3);  // Reduced scale
                        debugLog("    Grenade OK for major multi-hit!");
                    } else {
                        // With LOS and no multi-hit, grenade is TERRIBLE
                        // Check if we can use rifle or M-laser instead
                        var canUseRifle = (dist >= 7 && dist <= 9 && inArray(weapons, WEAPON_RIFLE));
                        var canUseMLaser = (dist >= 5 && dist <= 12 && inArray(weapons, WEAPON_M_LASER) && 
                                           isOnSameLine(myCell, enemyCell));
                        
                        if (canUseRifle || canUseMLaser) {
                            // We have MUCH better weapons available!
                            dptp = dptp * 0.05; // 95% penalty - almost never use
                            debugLog("    Grenade SEVERELY penalized - rifle/laser available!");
                        } else {
                            // Still bad but maybe our only option
                            dptp = dptp * 0.3; // 70% penalty
                            debugLog("    Grenade deprioritized - prefer moving to better range");
                        }
                    }
                }
                
                // Dark Katana - HIGH damage but self-damage tradeoff
                if (w == WEAPON_DARK_KATANA) {
                    if (dist == 1) {
                        // Calculate self-damage (scales with strength)
                        var selfDamage = 44 * (1 + mySTR / 100);
                        
                        // At melee range, Dark Katana should be STRONGLY preferred!
                        if (myHP > selfDamage * 3) {  // Can survive 3+ uses
                            dptp = dptp * 3.0; // 200% bonus - excellent health
                            debugLog("    Dark Katana STRONGLY prioritized - can survive 3+ uses");
                        } else if (myHP > selfDamage * 2) {  // Can survive 2 uses
                            dptp = dptp * 2.5; // 150% bonus - decent health
                            debugLog("    Dark Katana prioritized - can survive 2 uses");
                        } else if (myHP > selfDamage) {  // Can survive 1 use
                            dptp = dptp * 2.0; // 100% bonus - still worth it
                            debugLog("    Dark Katana viable - can survive 1 use");
                        } else {
                            dptp = dptp * 0.5; // Penalty - would kill us!
                            debugLog("    Dark Katana too risky - would be fatal!");
                        }
                    } else if (dist <= 3) {
                        // Close range - we can reach melee this turn!
                        // Don't add to attack options, but note we could move to melee
                        debugLog("    Dark Katana not in range (dist=" + dist + ") but could move to melee");
                        // Don't add negative multiplier - just skip it
                        return acc;  // Skip adding this weapon option
                    } else {
                        // Too far for Dark Katana
                        return acc;  // Don't add it as an option
                    }
                }
                
                // Rifle - EXTRA bonus at optimal range
                if (w == WEAPON_RIFLE) {
                    if (dist >= 7 && dist <= 9) {
                        dptp = dptp * 1.3; // 30% MORE bonus at optimal range
                        debugLog("    Rifle at perfect range!");
                    }
                }
                
                // Dark Katana vulnerability reduction bonus
                if (w == WEAPON_DARK_KATANA && dist == 1) {
                    dptp = dptp * 1.15; // 15% bonus for -15% vulnerability
                    debugLog("    Dark Katana reduces incoming damage by 15%");
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
                push(option, multiHitBonus); // multiHitBonus at index 7
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
    
    // PRIORITY CHECK: If we only have chip options but could move to weapon range, do that instead
    var hasWeaponOptions = false;
    var hasOnlyChipOptions = false;
    for (var i = 0; i < count(attackOptions); i++) {
        if (attackOptions[i][0] == "weapon") {
            hasWeaponOptions = true;
            break;
        }
    }
    if (count(attackOptions) > 0 && !hasWeaponOptions) {
        hasOnlyChipOptions = true;  // We have attack options, but they're all chips
    }
    
    if (count(attackOptions) == 0 || (hasOnlyChipOptions && getMP() > 0 && dist > 8)) {
        if (count(attackOptions) == 0) {
            debug("WARNING: No attack options - checking weapons: " + count(getWeapons()));
        } else {
            debugLog("Only chip options available, but can move to weapon range - prioritizing movement");
        }
        
        // If we're out of range OR have no line of sight, move closer!
        if (getMP() > 0 && (dist > 8 || !hasLine)) {
            if (dist > 8) {
                debugLog("Out of attack range - moving closer");
            } else {
                debugLog("No line of sight - repositioning for better angle");
            }
            var targetDist = 7;  // Optimal range for most weapons
            moveToward(enemy, min(getMP(), dist - targetDist));
            myMP = getMP();
            myCell = getCell();
            enemyCell = getCell(enemy);
            enemyDistance = getCellDistance(myCell, enemyCell);
            var newLOS = hasLOS(myCell, enemyCell);
            debugLog("Repositioned - new distance: " + enemyDistance + ", new LOS: " + newLOS);
            
            // Clear chip-only options since we moved - reevaluate next turn
            if (hasOnlyChipOptions) {
                debugLog("Clearing chip options after movement - will reevaluate weapons next turn");
                attackOptions = [];
            }
        }
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
    var currentWeapon = getWeapon();  // Track current weapon to avoid switching
    
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
            var needsSwap = (getWeapon() != option[1]);
            if (needsSwap) {
                // Skip weapons that require switching if we've already used the current weapon
                // This prevents excessive switching between equally viable weapons
                if (totalDamage > 0 && tpLeft < (option[3] + 1)) {
                    debugLog("  Skipping " + option[6] + " - would require weapon switch with insufficient TP");
                    continue;
                }
                setWeaponIfNeeded(option[1]);  // This costs 1 TP
                myTP = getTP();  // Update TP after swap
                tpLeft = myTP;
                currentWeapon = option[1];
                // Recalculate uses after weapon swap!
                uses = min(floor(tpLeft / option[3]), option[5]);
                if (uses <= 0) continue;  // Skip if no TP left after swap
                debugLog("  Switched to " + option[6] + " (1 TP cost)");
            }
            for (var j = 0; j < uses; j++) {
                debugLog("    Use #" + (j+1) + " of weapon " + option[6]);
                var result;
                var weaponId = option[1];
                
                // Check if this is an AoE/line weapon that needs cell targeting
                if (weaponId == WEAPON_GRENADE_LAUNCHER || weaponId == WEAPON_M_LASER) {
                    // Check for multi-hit opportunity
                    var targetCell = enemyCell;
                    
                    // Use multi-hit targeting if available (index 7 has multiHitBonus)
                    if (count(getAliveEnemies()) > 1 && count(option) > 7 && option[7] > 1.0) {
                        if (weaponId == WEAPON_M_LASER) {
                            var bestLaser = getBestLaserTarget();
                            if (bestLaser != null) {
                                targetCell = bestLaser;
                                debugLog("    🎯 M-Laser multi-hit target: " + targetCell);
                            }
                        } else if (weaponId == WEAPON_B_LASER) {
                            var bestBLaser = findBestBLaserTarget();
                            if (bestBLaser != null && bestBLaser["targetCell"] != null) {
                                targetCell = bestBLaser["targetCell"];
                                debugLog("    🎯 B-Laser multi-hit target: " + targetCell);
                            }
                        } else if (weaponId == WEAPON_GRENADE_LAUNCHER) {
                            var bestAoE = getBestAoETarget(weaponId);
                            if (bestAoE != null) {
                                targetCell = bestAoE;
                                debugLog("    🎯 Grenade multi-hit target: " + targetCell);
                            }
                        }
                    } else {
                        targetCell = getCell(enemy);
                    }
                    
                    debugLog("    Using " + option[6] + " on cell " + targetCell);
                    result = useWeaponOnCell(targetCell);
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
    
    // PRIORITY: Try MORE aggressive repositioning for direct shots before AoE fallback
    if (totalDamage == 0 && myMP > 0 && myTP >= 5 && !hasLine) {
        debugLog("No direct damage dealt - trying aggressive repositioning for LOS");
        
        // More aggressive line-of-sight seeking
        var reachable = getReachableCells(myCell, myMP);
        var bestLOSCell = null;
        var bestLOSScore = -999999;
        
        // Search ALL reachable cells for line of sight, not just optimal range
        for (var i = 0; i < min(50, count(reachable)); i++) {
            var cell = reachable[i];
            if (hasLOS(cell, enemyCell)) {
                var newDist = getCellDistance(cell, enemyCell);
                var score = 0;
                
                // Score based on weapon effectiveness at this range
                if (newDist >= 1 && newDist <= 8) {  // Magnum/B-Laser range
                    if (newDist >= 4 && newDist <= 7) {
                        score = 8000;  // Perfect for grenade with LOS
                        debugLog("  Found LOS position at range " + newDist + " (grenade range)");
                    } else if (newDist >= 2 && newDist <= 8) {
                        score = 7000;  // Good for B-Laser/Magnum
                        debugLog("  Found LOS position at range " + newDist + " (B-Laser/Magnum range)");
                    } else {
                        score = 5000;  // Some LOS is better than none
                        debugLog("  Found LOS position at range " + newDist + " (basic LOS)");
                    }
                    
                    if (score > bestLOSScore) {
                        bestLOSScore = score;
                        bestLOSCell = cell;
                    }
                }
            }
        }
        
        // Move to LOS position if found
        if (bestLOSCell != null) {
            debugLog("Moving to LOS position for direct shots instead of AoE");
            if (moveToCell(bestLOSCell) > 0) {
                // Update position variables
                myCell = getCell();
                enemyCell = getCell(enemy);
                dist = getCellDistance(myCell, enemyCell);
                hasLine = hasLOS(myCell, enemyCell);
                myMP = getMP();
                debugLog("Repositioned for LOS - new distance: " + dist + ", new LOS: " + hasLine);
                
                // Try direct attacks again with new position
                if (hasLine && myTP >= 5) {
                    if (dist >= 4 && dist <= 7 && inArray(getWeapons(), WEAPON_GRENADE_LAUNCHER)) {
                        debugLog("Now in range for DIRECT grenade shot!");
                        setWeaponIfNeeded(WEAPON_GRENADE_LAUNCHER);
                        var result = useWeapon(enemy);
                        if (result == USE_SUCCESS || result == USE_CRITICAL) {
                            totalDamage += 150 + mySTR * 2;  // Direct grenade damage
                            myTP -= 6;
                            debugLog("DIRECT grenade hit successful!");
                            return;  // Success! Don't fall back to AoE
                        }
                    } else if (dist >= 2 && dist <= 8 && inArray(getWeapons(), WEAPON_B_LASER)) {
                        debugLog("Now in range for B-Laser shot!");
                        setWeaponIfNeeded(WEAPON_B_LASER);
                        var result = useWeapon(enemy);
                        if (result == USE_SUCCESS || result == USE_CRITICAL) {
                            totalDamage += 55;  // B-Laser damage
                            myTP -= 5;
                            debugLog("B-Laser hit successful!");
                            return;  // Success! Don't fall back to AoE
                        }
                    } else if (dist >= 1 && dist <= 8 && inArray(getWeapons(), WEAPON_MAGNUM)) {
                        debugLog("Now in range for Magnum shot!");
                        setWeaponIfNeeded(WEAPON_MAGNUM);
                        var result = useWeapon(enemy);
                        if (result == USE_SUCCESS || result == USE_CRITICAL) {
                            totalDamage += 45;  // Magnum damage
                            myTP -= 5;
                            debugLog("Magnum hit successful!");
                            return;  // Success! Don't fall back to AoE
                        }
                    }
                }
            }
        }
    }

    // ENHANCED: Try AoE splash through obstacles with proper patterns! (ONLY as final fallback)
    if (totalDamage == 0 && myTP >= 5) {
        debugLog("Checking for AoE opportunities (including diagonal patterns)...");
        
        var bestSplash = null;
        var bestDamage = 0;
        
        // Check Grenade Launcher splash positions
        if (inArray(getWeapons(), WEAPON_GRENADE_LAUNCHER)) {
            var splashPositions = findAoESplashPositions(WEAPON_GRENADE_LAUNCHER, myCell, enemyCell);
            
            for (var i = 0; i < count(splashPositions); i++) {
                var splash = splashPositions[i];
                var grenadeBase = 150 + mySTR * 2;
                var damage = grenadeBase * splash["damagePercent"];
                
                if (damage > bestDamage) {
                    bestDamage = damage;
                    bestSplash = splash;
                    bestSplash["weapon"] = WEAPON_GRENADE_LAUNCHER;
                }
            }
        }
        
        // IMPROVED: Check M-Laser line pattern optimization
        if (inArray(getWeapons(), WEAPON_M_LASER) && myTP >= 8) {
            var laserResult = findBestMLaserTarget();
            
            if (laserResult != null && laserResult["totalDamage"] > 0) {
                // Compare with standard line detection
                var standardLine = findAoESplashPositions(WEAPON_M_LASER, myCell, enemyCell);
                
                // Use the better of the two methods
                if (laserResult["totalDamage"] > bestDamage) {
                    bestDamage = laserResult["totalDamage"];
                    bestSplash = [:];
                    bestSplash["target"] = laserResult["targetCell"];
                    bestSplash["weapon"] = WEAPON_M_LASER;
                    bestSplash["damagePercent"] = 1.0;
                    bestSplash["isIndirect"] = (laserResult["targetCell"] != enemyCell);
                    bestSplash["patternHits"] = laserResult["numHits"];
                    
                    // Log line pattern detection
                    if (count(laserResult["cellsHit"]) > 1) {
                        debugLog("M-Laser line pattern: " + count(laserResult["cellsHit"]) + " cells hit!");
                    }
                }
            }
        }
        
        // Check B-Laser if available (dual damage/heal weapon)
        if (inArray(getWeapons(), WEAPON_B_LASER) && myTP >= B_LASER_COST && bLaserUsesRemaining > 0) {
            var bLaserResult = findBestBLaserTarget();
            
            if (bLaserResult != null) {
                // B-Laser has both damage and heal value
                var totalValue = bLaserResult["totalValue"];
                
                // Prioritize B-Laser when we need healing
                if (totalValue > bestDamage || (myHP < myMaxHP * B_LASER_HEAL_THRESHOLD && totalValue > bestDamage * 0.8)) {
                    bestDamage = totalValue;
                    bestSplash = [:];
                    bestSplash["target"] = bLaserResult["targetCell"];
                    bestSplash["weapon"] = WEAPON_B_LASER;
                    bestSplash["damagePercent"] = 1.0;
                    bestSplash["isIndirect"] = false;
                    bestSplash["isHealCombo"] = (bLaserResult["healValue"] > 0);
                    
                    if (bLaserResult["hits"] > 1) {
                        debugLog("B-Laser multi-hit opportunity: " + bLaserResult["hits"] + " targets!");
                    }
                }
            }
        }
        
        // Check Magnum if available
        if (inArray(getWeapons(), WEAPON_MAGNUM) && myTP >= MAGNUM_COST && magnumUsesRemaining > 0) {
            var distMagnum = getCellDistance(myCell, enemyCell);
            if (distMagnum >= MAGNUM_MIN_RANGE && distMagnum <= MAGNUM_MAX_RANGE && lineOfSight(myCell, enemyCell)) {
                var magnumDamage = getWeaponDamage(WEAPON_MAGNUM, enemy);
                if (magnumDamage > bestDamage) {
                    bestDamage = magnumDamage;
                    // Use bestSplash for consistency with weapon execution  
                    bestSplash = [:];
                    bestSplash["target"] = enemyCell;
                    bestSplash["weapon"] = WEAPON_MAGNUM;
                    bestSplash["damagePercent"] = 1.0;
                    bestSplash["isIndirect"] = false;
                }
            }
        }
        
        // Check Destroyer if available  
        if (inArray(getWeapons(), WEAPON_DESTROYER) && myTP >= DESTROYER_COST && destroyerUsesRemaining > 0) {
            var distDestroyer = getCellDistance(myCell, enemyCell);
            if (distDestroyer >= DESTROYER_MIN_RANGE && distDestroyer <= DESTROYER_MAX_RANGE && lineOfSight(myCell, enemyCell)) {
                var destroyerDamage = getWeaponDamage(WEAPON_DESTROYER, enemy);
                if (destroyerDamage > bestDamage) {
                    bestDamage = destroyerDamage;
                    // Use bestSplash for consistency with weapon execution
                    bestSplash = [:];
                    bestSplash["target"] = enemyCell;
                    bestSplash["weapon"] = WEAPON_DESTROYER;
                    bestSplash["damagePercent"] = 1.0;
                    bestSplash["isIndirect"] = false;
                }
            }
        }
        
        // Execute best splash attack
        if (bestSplash != null && bestDamage > 0) {
            var targetCell = bestSplash["target"];
            var weapon = bestSplash["weapon"];
            
            setWeaponIfNeeded(weapon);
            if (useWeaponOnCell(targetCell)) {
                // Get weapon name for logging and update use counters
                var weaponName = "Unknown";
                if (weapon == WEAPON_GRENADE_LAUNCHER) weaponName = "Grenade";
                else if (weapon == WEAPON_LIGHTNINGER) weaponName = "Lightninger";
                else if (weapon == WEAPON_M_LASER) weaponName = "M-Laser";
                else if (weapon == WEAPON_B_LASER) {
                    weaponName = "B-Laser";
                    bLaserUsesRemaining--;
                    if (bestSplash["isHealCombo"]) {
                        debugLog("B-Laser heal + damage combo!");
                    }
                }
                else if (weapon == WEAPON_MAGNUM) {
                    weaponName = "Magnum";
                    magnumUsesRemaining--;
                }
                else if (weapon == WEAPON_DESTROYER) {
                    weaponName = "Destroyer";
                    destroyerUsesRemaining--;
                }
                
                if (bestSplash["isIndirect"]) {
                    debugLog("INDIRECT " + weaponName + " splash through obstacle!");
                    debugLog("Target: " + targetCell + ", Enemy at: " + enemyCell);
                } else {
                    debugLog("Direct " + weaponName + " hit!");
                }
                
                if (bestSplash["splashDistance"] != null) {
                    debugLog("Splash distance: " + bestSplash["splashDistance"] + 
                            ", damage: " + round(bestDamage) + 
                            " (" + round(bestSplash["damagePercent"] * 100) + "%)");
                } else {
                    debugLog("Damage: " + round(bestDamage));
                }
                
                totalDamage = bestDamage;
                myLastTurnDamage = bestDamage;
            }
        }
    }
    
    // CRITICAL: Reposition after attacking to OPTIMAL weapon range
    if (getMP() > 0 && enemy != null && getLife(enemy) > 0) {
        debugLog("Post-attack repositioning with " + getMP() + " MP remaining");
        
        // Find best position for next turn (prioritize RIFLE range!)
        var reachable = getReachableCells(getCell(), getMP());
        var bestCell = getCell();
        var bestScore = -999999;
        var currentEID = calculateEID(getCell());
        var currentDist = getCellDistance(getCell(), getCell(enemy));
        
        for (var i = 0; i < min(20, count(reachable)); i++) {
            var cell = reachable[i];
            var cellEID = calculateEID(cell);
            var cellDist = getCellDistance(cell, getCell(enemy));
            
            // Score based on safety (low EID) and OPTIMAL weapon range
            var score = -cellEID * 2;  // Prioritize safety
            
            // STRONGLY prefer RIFLE range for next turn
            if (cellDist >= 7 && cellDist <= 9 && hasLOS(cell, getCell(enemy))) {
                score += 1000;  // RIFLE range - best weapon!
                if (cellDist == 8) score += 200;  // Perfect rifle range
            }
            // M-Laser range is good too
            else if (cellDist >= 10 && cellDist <= 12 && hasLOS(cell, getCell(enemy))) {
                score += 600;  // M-Laser range
            }
            // Penalize grenade-only range
            else if (cellDist >= 4 && cellDist <= 6 && hasLOS(cell, getCell(enemy))) {
                score += 200;  // Can attack but not optimal
            }
            
            // BONUS: Moving from grenade range to rifle range
            if (currentDist >= 4 && currentDist <= 6 && cellDist >= 7 && cellDist <= 9) {
                score += 500;  // Incentive to improve position
                debugLog("  Cell " + cell + ": Moving to rifle range!");
            }
            
            // Avoid getting too close
            if (cellDist < 5) {
                score -= 1000;
            }
            
            if (score > bestScore) {
                bestScore = score;
                bestCell = cell;
            }
        }
        
        if (bestCell != getCell()) {
            var newEID = calculateEID(bestCell);
            debugLog("Repositioning to safer position");
            if (moveToCell(bestCell) > 0) {
                enemyDistance = getCellDistance(getCell(), getCell(enemy));
                debugLog("Repositioned to distance " + enemyDistance);
            }
        }
    }
    
    // End of executeAttack function
}


// Function: executeDefensive
function executeDefensive() {
    var hpRatio = myHP / myMaxHP;
    var myEHP = calculateEHP(myHP, myAbsShield, myRelShield, 0, myResistance);
    var currentEID = calculateEID(myCell);
    var threatLevel = myEHP > 0 ? currentEID / myEHP : 1.0;
    
    debugLog("Defensive: HP=" + round(hpRatio*100) + "%, Threat=" + round(threatLevel*100) + "%, TP=" + myTP);
    
    // Priority 0: Liberation if enemy is buffed/shielded
    if (enemy != null && enemyDistance <= 6) {
        if (useAntiTankStrategy()) {
            debugLog("Liberation successful - enemy buffs/shields stripped!");
        }
    }
    
    // Priority 1: Antidote for poison
    var myEffects = getEffects(myLeek);
    var hasPoisonEffect = false;
    
    for (var i = 0; i < count(myEffects); i++) {
        if (myEffects[i][0] == 13) {  // EFFECT_POISON
            hasPoisonEffect = true;
            break;
        }
    }
    
    if (hasPoisonEffect && getCooldown(CHIP_ANTIDOTE) == 0 && myTP >= 3) {
        if (tryUseChip(CHIP_ANTIDOTE, myLeek)) {
            debugLog("Antidote applied - poison removed!");
        }
    }
    
    // ADAPTIVE DEFENSE STRATEGY based on actual combat situation
    
    // Critical HP - Always heal first
    if (hpRatio < 0.3) {
        debugLog("CRITICAL HP - Emergency healing priority!");
        var healChips = [CHIP_CURE, CHIP_VACCINE, CHIP_SERUM, CHIP_ARMORING];
        for (var i = 0; i < count(healChips); i++) {
            if (getCooldown(healChips[i]) == 0 && myTP >= getChipCost(healChips[i])) {
                tryUseChip(healChips[i], myLeek);
            }
        }
    }
    // High threat and in combat range - Shield up for trading
    else if (threatLevel > 0.5 && enemyDistance <= 10 && myTP >= 3) {
        debugLog("HIGH THREAT TRADING - Shields for damage exchange");
        
        // Prioritize shields when we're about to trade damage
        var shieldChips = [CHIP_FORTRESS, CHIP_ARMOR, CHIP_SHIELD];
        for (var i = 0; i < count(shieldChips); i++) {
            if (getCooldown(shieldChips[i]) == 0 && myTP >= getChipCost(shieldChips[i])) {
                tryUseChip(shieldChips[i], myLeek);
            }
        }
        
        // Heal if still hurt after shielding
        if (hpRatio < 0.5 && myTP >= 4) {
            tryUseChip(CHIP_CURE, myLeek);
        }
    }
    // Low threat or out of range - Heal up
    else if (threatLevel < 0.3 || enemyDistance > 10) {
        debugLog("LOW THREAT - Healing opportunity");
        
        var healThreshold = 0.7;  // Heal up to 70% when safe
        if (hpRatio < healThreshold) {
            // Prefer HoT when safe for efficiency
            var healChips = [CHIP_SERUM, CHIP_VACCINE, CHIP_CURE];
            for (var i = 0; i < count(healChips); i++) {
                if (getCooldown(healChips[i]) == 0 && myTP >= getChipCost(healChips[i])) {
                    tryUseChip(healChips[i], myLeek);
                    if (hpRatio >= 0.6) break;  // Don't overheal
                }
            }
        }
        
        // Shield after healing if TP remains
        if (myTP >= 3) {
            tryUseChip(CHIP_SHIELD, myLeek);
        }
    }
    // Medium threat - Balanced approach
    else {
        debugLog("BALANCED DEFENSE - Mixed strategy");
        
        // Balance healing and shielding
        if (hpRatio < 0.5 && myTP >= 4) {
            tryUseChip(CHIP_CURE, myLeek);
        }
        
        if (myTP >= 3) {
            tryUseChip(CHIP_SHIELD, myLeek);
        }
        
        // Add fortress if we have extra TP
        if (myTP >= 6) {
            tryUseChip(CHIP_FORTRESS, myLeek);
        }
    }
    
    // Priority 3: Buffs if TP remains and not critically threatened
    if (myTP >= 3 && threatLevel < 0.8) {
        executeBuffs();
    }
    
    // CRITICAL: Reposition after defensive actions to minimize EID
    if (getMP() > 0 && enemy != null && getLife(enemy) > 0) {
        debugLog("Post-defense repositioning with " + getMP() + " MP");
        repositionDefensive();
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
    // Turn 2+ should use makeDecision() from ai/decision_making.ls
    
    if (turn != 1) {
        debugLog("ERROR: executeEarlyGameSequence called on turn " + turn + " - should not happen!");
        // Force proper combat execution instead of recursion
        executeAttack();
        if (myTP >= 4) executeDefensive();
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
    // TURN 1: OPTIMAL HP BUFF STRATEGY - Knowledge -> Armoring -> Elevation
    debugLog("=== TURN 1: MAX HP BUFF STRATEGY ===");
    debugLog("TP: " + myTP + ", Enemy at distance " + enemyDistance);
    
    // Since enemy is usually out of range on Turn 1, focus on permanent HP buffs
    // These last the entire fight and provide maximum value
    
    // PRIORITY 1: KNOWLEDGE - Wisdom boost first (enhances other buffs)
    // Knowledge gives +250-270 flat Wisdom, which scales our HP buffs
    if (getCooldown(CHIP_KNOWLEDGE) == 0 && myTP >= 6) {
        if (tryUseChip(CHIP_KNOWLEDGE, myLeek)) {
            var oldWisdom = myWisdom;
            myWisdom = getWisdom();
            var wisBoost = myWisdom - oldWisdom;
            debugLog("📚 KNOWLEDGE: +" + wisBoost + " Wisdom (now " + myWisdom + ")");
            myTP = getTP();
        }
    }
    
    // PRIORITY 2: ARMORING - First HP buff (scales with Wisdom we just gained)
    if (getCooldown(CHIP_ARMORING) == 0 && myTP >= 4) {
        if (tryUseChip(CHIP_ARMORING, myLeek)) {
            var oldMaxHP = myMaxHP;
            myMaxHP = getTotalLife();
            myHP = getLife();
            var armorHP = myMaxHP - oldMaxHP;
            debugLog("🛡️ ARMORING: +" + armorHP + " max HP (total " + myMaxHP + ")");
            myTP = getTP();
        }
    }
    
    // PRIORITY 3: ELEVATION - Second HP buff (also scales with Wisdom)
    // Elevation gives +80 base max HP that scales with Wisdom
    if (getCooldown(CHIP_ELEVATION) == 0 && myTP >= 6) {
        if (tryUseChip(CHIP_ELEVATION, myLeek)) {
            var oldMaxHP = myMaxHP;
            myMaxHP = getTotalLife();
            myHP = getLife();
            var elevHP = myMaxHP - oldMaxHP;
            debugLog("⬆️ ELEVATION: +" + elevHP + " max HP (total " + myMaxHP + ")");
            myTP = getTP();
        }
    }
    
    // EMERGENCY: Only use shields if enemy is very close and can attack
    if (enemyDistance <= 7 && myTP >= 3) {
        // Enemy can attack next turn - shield now!
        if (getCooldown(CHIP_SHIELD) == 0) {
            if (tryUseChip(CHIP_SHIELD, myLeek)) {
                myAbsShield = getAbsoluteShield(myLeek);
                debugLog("🛡️ EMERGENCY SHIELD: +" + myAbsShield + " (enemy at range " + enemyDistance + ")");
                myTP = getTP();
            }
        }
    }
    
    debugLog("Turn 1 complete. HP: " + myHP + "/" + myMaxHP + ", Shields: " + myAbsShield + "+" + myRelShield + "%, Position: " + myCell);
    
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
        // After teleporting, check if we need to move to attack range
        var currentDist = getCellDistance(getCell(), getCell(enemy));
        if (currentDist > 9 && getMP() > 0) {
            // Still too far, move closer
            var targetCell = bestApproachStep(getCell(enemy));
            if (targetCell != getCell()) {
                moveToCell(targetCell);
                debugLog("  Moved to range " + getCellDistance(getCell(), getCell(enemy)) + " after teleport");
            }
        }
        // Now attack from new position
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
        
        debugLog("Threat: EHP=" + myEHP + ", ratio=" + round(threatRatio * 100) + "%");
        
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
            var simStrength = mySTR + 260;  // Approximate flat boost
            var weaponBoost = floor((simStrength - mySTR) * 2);  // Rough weapon damage increase
            
            if (weaponBoost > 100 && getCooldown(CHIP_STEROID) == 0 && myTP >= 7) {
                if (tryUseChip(CHIP_STEROID, myLeek)) {
                    mySTR = getStrength();
                    debugLog("💉 STEROID: Damage boost ~" + weaponBoost + " (STR: " + mySTR + ")");
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
                debugLog("🌀 Teleported! Now checking if we need to move to attack...");
                
                // After teleporting, we likely need to MOVE to attack range!
                var currentDist = getCellDistance(getCell(), getCell(enemy));
                var canAttack = false;
                
                // Check if we can attack from teleport position
                if (hasLOS(getCell(), getCell(enemy))) {
                    if (currentDist >= 7 && currentDist <= 9) canAttack = true;  // Rifle
                    else if (currentDist >= 5 && currentDist <= 12 && isOnSameLine(getCell(), getCell(enemy))) canAttack = true;  // M-Laser
                }
                
                // If can't attack, MOVE closer!
                if (!canAttack && getMP() > 0) {
                    debugLog("  Need to move after teleport - distance: " + currentDist);
                    var targetRange = 8;  // Optimal rifle range
                    var reachable = getReachableCells(getCell(), getMP());
                    var bestMove = getCell();
                    var bestScore = -999999;
                    
                    for (var i = 0; i < min(20, count(reachable)); i++) {
                        var cell = reachable[i];
                        var dist = getCellDistance(cell, getCell(enemy));
                        var score = -abs(dist - targetRange) * 100;
                        
                        // Bonus for attack ranges
                        if (dist >= 7 && dist <= 9) score += 1000;  // Rifle
                        if (dist >= 5 && dist <= 12) score += 500;   // M-Laser
                        
                        if (score > bestScore) {
                            bestScore = score;
                            bestMove = cell;
                        }
                    }
                    
                    if (bestMove != getCell()) {
                        moveToCell(bestMove);
                        debugLog("  Moved to range " + getCellDistance(getCell(), getCell(enemy)) + " after teleport");
                    }
                }
                
                // Now attack from new position
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
            mySTR = getStrength();
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
        
        // FORCE ATTACK at range 5-12 with M-Laser if available
        if (enemyDistance >= 5 && enemyDistance <= 12 && myTP >= 8) {
            if (inArray(getWeapons(), WEAPON_M_LASER)) {
                setWeaponIfNeeded(WEAPON_M_LASER);
                var shots = 0;
                while (myTP >= 8 && shots < 2) {
                    var result = useWeapon(enemy);
                    if (result == USE_SUCCESS || result == USE_CRITICAL) {
                        shots++;
                        myTP = getTP();
                        if (result == USE_CRITICAL) {
                            debugLog("CRITICAL M-Laser!");
                        }
                    } else {
                        debugLog("Failed to use M-Laser: " + result);
                        break;
                    }
                }
                debugLog("→ M-Laser: " + shots + " shots fired");
            }
        // Attack at range 7-9 with Rifle if available
        } else if (enemyDistance >= 7 && enemyDistance <= 9 && myTP >= 7) {
            if (inArray(getWeapons(), WEAPON_RIFLE)) {
                setWeaponIfNeeded(WEAPON_RIFLE);
                var shots = 0;
                while (myTP >= 7 && shots < 2) {
                    var result = useWeapon(enemy);
                    if (result == USE_SUCCESS || result == USE_CRITICAL) {
                        shots++;
                        myTP = getTP();
                        if (result == USE_CRITICAL) {
                            debugLog("CRITICAL Rifle shot!");
                        }
                    } else {
                        debugLog("Failed to use Rifle: " + result);
                        break;
                    }
                }
                debugLog("→ Rifle: " + shots + " shots fired");
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
            debugLog("→ Safe to continue attacks");
            if (myTP >= 3) {
                executeAttack();
                myTP = getTP();
            }
        } else {
            // Dangerous - shield up
            debugLog("→ Dangerous position, applying shields");
            if (getCooldown(CHIP_FORTRESS) == 0 && myTP >= 6) tryUseChip(CHIP_FORTRESS, myLeek);
            if (getCooldown(CHIP_ARMOR) == 0 && myTP >= 6) tryUseChip(CHIP_ARMOR, myLeek);
            if (getCooldown(CHIP_SHIELD) == 0 && myTP >= 4) tryUseChip(CHIP_SHIELD, myLeek);
        }
    }
    
} else if (!shouldUseBaitTactic()) {
    // SEQUENCED COMBAT STRATEGY WITH EID DECISION MAKING
    debugLog("=== TURN " + turn + " SEQUENCED COMBAT ===");
    
    // PHASE 1: MINIMAL BUFFS AFTER TURN 1 - RESERVE TP FOR ATTACKS!
    debugLog("PHASE 1: Buff sequence (minimal after turn 1)");
    
    // CRITICAL: After Turn 1, we need to ATTACK, not buff endlessly!
    // Reserve at least 9 TP for Lightninger or 6 TP for Grenade Launcher
    var tpReserveForAttack = 9;  // Enough for Lightninger
    
    // Only use essential buffs after Turn 1
    if (turn <= 2) {
        // Turn 2: Can use ONE key buff if we have excess TP
        
        // 1A: Adrenaline for TP boost (only if we have spare TP)
        if (getCooldown(CHIP_ADRENALINE) == 0 && myTP >= (tpReserveForAttack + 1)) {
            if (tryUseChip(CHIP_ADRENALINE, myLeek)) {
                debugLog("→ Adrenaline: +5 TP next turn");
                myTP = getTP();
            }
        }
        
        // 1B: Solidification ONLY if enemy is magic/science heavy
        if (enemyMagic > 400 || enemyScience > 400) {
            if (getResistance() < 300 && getCooldown(CHIP_SOLIDIFICATION) == 0 && myTP >= (tpReserveForAttack + 6)) {
                if (tryUseChip(CHIP_SOLIDIFICATION, myLeek)) {
                    debugLog("→ Solidification: Shields 5.3x effective");
                    myResistance = getResistance();
                    myTP = getTP();
                }
            }
        }
        
        // 1C: Steroid ONLY if we have tons of TP and need damage
        if (myTP >= (tpReserveForAttack + 7) && getStrength() < 500 && getCooldown(CHIP_STEROID) == 0) {
            if (tryUseChip(CHIP_STEROID, myLeek)) {
                debugLog("→ Steroid: " + getStrength() + " STR");
                mySTR = getStrength();
                myTP = getTP();
            }
        }
    } else if (turn == 3) {
        // Turn 3+: ONLY use Adrenaline if available (1 TP for 5 TP gain is worth it)
        if (getCooldown(CHIP_ADRENALINE) == 0 && myTP >= (tpReserveForAttack + 1)) {
            if (tryUseChip(CHIP_ADRENALINE, myLeek)) {
                debugLog("→ Adrenaline: +5 TP next turn");
                myTP = getTP();
            }
        }
    }
    // Turn 4+: NO MORE BUFFS - PURE COMBAT!
    
    debugLog("TP after buffs: " + myTP + " (reserved " + tpReserveForAttack + " for attacks)");
    
    // PHASE 2: POSITIONING (Strategy-based positioning)
    debugLog("PHASE 2: " + COMBAT_STRATEGY + " positioning");
    
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
    
    // PHASE 4: EID DECISION - Prioritize attacks over defense!
    if (enemy != null) {
        debugLog("PHASE 4: Attack Priority Decision");
        
        // Recalculate EID after attacks
        currentEID = eidOf(myCell);
        myEHP = calculateEHP(myHP, myAbsShield, myRelShield, 0, myResistance);
        eidRatio = currentEID / myEHP;
        var hpRatio = myHP / myMaxHP;
        
        debugLog("→ Current state: HP=" + round(hpRatio*100) + "%");
        
        // CRITICAL CHANGE: Only defend if TRULY critical, otherwise keep attacking!
        if (hpRatio < 0.25) {
            // EMERGENCY: Below 25% HP - must heal
            debugLog("→ EMERGENCY! HP critical (<25%)");
            
            // Emergency heal
            if (myTP >= 8 && getCooldown(CHIP_REGENERATION) == 0) {
                tryUseChip(CHIP_REGENERATION, myLeek);
                myTP = getTP();
            } else if (myTP >= 4 && getCooldown(CHIP_CURE) == 0) {
                tryUseChip(CHIP_CURE, myLeek);
                myTP = getTP();
            }
            
            // One shield if we have TP left
            if (myTP >= 4 && getCooldown(CHIP_SHIELD) == 0) {
                tryUseChip(CHIP_SHIELD, myLeek);
                myTP = getTP();
            }
            
        } else if (hpRatio < 0.5 && eidRatio > 0.6) {
            // HIGH DANGER: Below 50% HP and high incoming damage
            debugLog("→ High danger, quick shield then attack");
            
            // ONE shield only
            if (myTP >= 4 && getCooldown(CHIP_SHIELD) == 0) {
                tryUseChip(CHIP_SHIELD, myLeek);
                myTP = getTP();
            }
            
            // Use remaining TP for attacks
            if (myTP >= 3) {
                executeAttack();
            }
            
        } else {
            // DEFAULT: Keep attacking! We have 3700+ HP after buffs
            debugLog("→ Continuing offense (HP: " + round(hpRatio*100) + "%)");
            
            // Use ALL remaining TP for attacks
            var attackCount = 0;
            var prevTP = myTP;
            while (myTP >= 3 && enemy != null && attackCount < 5) {
                executeAttack();
                myTP = getTP();
                attackCount++;
                // If TP didn't change, we can't attack, so break
                if (myTP == prevTP) break;
                prevTP = myTP;
            }
            
            // Only shield if we have leftover TP and nothing else to do
            if (myTP >= 4 && attackCount == 0 && getCooldown(CHIP_SHIELD) == 0) {
                tryUseChip(CHIP_SHIELD, myLeek);
            }
        }
    }
    
    // PHASE 5: REMOVED - No more wasting TP on random buffs!
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
    // Ultra-simple combat for panic mode - just heal and attack
    debugLog("PANIC MODE - HP: " + myHP + "/" + myMaxHP);
    
    // Try to heal first
    if (myTP >= 8 && getCooldown(CHIP_REGENERATION) == 0) {
        useChip(CHIP_REGENERATION, getEntity());
    } else if (myTP >= 4 && getCooldown(CHIP_CURE) == 0) {
        useChip(CHIP_CURE, getEntity());
    }
    
    // Then attack or move
    if (enemyDistance <= 12 && hasLOS(myCell, enemyCell)) {
        // Just attack with best available weapon
        if (enemyDistance == 1 && myHP > 50) {
            setWeaponIfNeeded(WEAPON_DARK_KATANA);
        } else if (enemyDistance <= 7) {
            setWeaponIfNeeded(WEAPON_GRENADE_LAUNCHER);
        } else if (enemyDistance <= 9) {
            setWeaponIfNeeded(WEAPON_RIFLE);
        } else {
            setWeaponIfNeeded(WEAPON_M_LASER);
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

