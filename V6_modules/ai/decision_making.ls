// V6 Module: ai/decision_making.ls
// Main decision making
// Auto-generated from V5.0 script

// Function: makeDecision
function makeDecision() {
    debugLog("makeDecision called - enemy=" + enemy);
    if (enemy == null) {
        debugLog("No enemy found");
        return;
    }
    
    // Check for panic mode first
    if (isInPanicMode()) {
        debugLog("PANIC MODE - Using simplified tactics");
        simplifiedCombat();
        return;
    }
    debugLog("Not in panic mode, continuing...");
    
    // Emergency check for mid-game turns to avoid timeout
    if (turn >= 5 && !canSpendOps(2000000)) {
        debugLog("Turn 5+ emergency mode - simplified logic");
        // Just find a decent position and attack
        if (enemyDistance <= 7 && hasLOS(myCell, enemyCell)) {
            executeAttack();
        } else {
            // Move to attack range
            var reach = getReachableCells(myCell, myMP);
            var bestCell = myCell;
            for (var i = 0; i < min(20, count(reach)); i++) {
                var c = reach[i];
                var d = getCellDistance(c, enemyCell);
                if (d >= 3 && d <= 7 && hasLOS(c, enemyCell)) {
                    bestCell = c;
                    break;
                }
            }
            if (bestCell != myCell) {
                if (moveToCell(bestCell) > 0) {
                    enemyDistance = getCellDistance(myCell, enemyCell);
                }
            }
            executeAttack();
        }
        return;
    }
    
    // Emergency check for late turns to avoid timeout
    if (turn >= 9 && !canSpendOps(1000000)) {
        debugLog("Turn 9+ emergency mode - direct attack");
        if (enemyDistance <= 10) {
            executeAttack();
        } else {
            var step = bestApproachStep(enemyCell);
            if (moveToCell(step) > 0) {
                enemyDistance = getCellDistance(myCell, enemyCell);
            }
            executeAttack();
        }
        return;
    }
    
    // Update pattern learning and get predictions
    debugLog("Updating pattern learning...");
    var predictions = updatePatternLearning();
    if (predictions != null) {
        debugLog("Applying pattern predictions");
        applyPatternPredictions(predictions);
    }
    
    // Build influence map for tactical awareness (only in OPTIMAL/EFFICIENT modes)
    var currentMode = getOperationLevel();
    debugLog("Current mode: " + currentMode);
    if ((currentMode == "OPTIMAL" || currentMode == "EFFICIENT") && shouldUseAlgorithm(30000)) {
        debugLog("Building influence map...");
        buildInfluenceMap();
        
        // Visualize in debug mode for early turns
        if (debugEnabled && turn <= 3) {
            visualizeInfluenceMap();
        }
    }
    
    // Calculate current state
    var myEHP = calculateEHP(myHP, myAbsShield, myRelShield, 0, myResistance);
    var enemyEHP = calculateEHP(enemyHP, getAbsoluteShield(enemy), getRelativeShield(enemy), 0, getResistance(enemy));
    
    // Precompute EID for likely positions - INCREASED since we have ops to spare
    var candidateCells = getReachableCells(myCell, myMP + 2);  // Full movement + buffer
    var eidCap = turn >= 5 ? 15 : 30;  // Increased from 5/10 to 15/30
    debugLog("Precomputing EID for " + min(eidCap, count(candidateCells)) + " cells...");
    precomputeEID(candidateCells, eidCap);
    debugLog("EID precomputation complete");
    
    var currentEID = eidOf(myCell);
    var currentDamage = calculateDamageFrom(myCell);
    var pkillCurrent = calculatePkill(enemyHP, myTP);  // Fixed: use raw HP, not EHP
    
    // Calculate life steal based on ACTUAL damage after enemy shields
    var lifeStealPotential = calculateLifeSteal(currentDamage, enemy);
    debugLog("State: MyEHP=" + myEHP + " EnemyEHP=" + enemyEHP + " EID=" + currentEID + " Damage=" + currentDamage + " LifeSteal=" + lifeStealPotential + " Pkill=" + pkillCurrent);
    
    // Determine game phase and adjust strategy accordingly
    debugLog("Calling determineGamePhase...");
    determineGamePhase();
    debugLog("Current phase: " + GAME_PHASE);
    
    // Adjust knobs based on ops and phase
    debugLog("Calling adjustKnobs...");
    adjustKnobs();
    debugLog("Knobs adjusted");
    
    // Try ultra-fast bitwise decision first for common scenarios
    debugLog("Checking quick combat decision...");
    if (canSpendOps(100)) {
        debugLog("Calling quickCombatDecision...");
        var quickDecision = quickCombatDecision();
        debugLog("Quick decision result: " + quickDecision);
        
        // Log state for debugging
        if (debugEnabled && turn <= 5) {
            var stateDesc = getStateDescription();
            debugLog("Combat states: " + join(stateDesc, ", "));
            debugLog("Quick decision: " + quickDecision);
        }
        
        // Execute quick decisions that don't need complex analysis
        if (quickDecision == "EXECUTE_KILL" || quickDecision == "EMERGENCY_SHIELD" || 
            quickDecision == "USE_ANTIDOTE" || quickDecision == "DEFENSIVE_RETREAT") {
            // These are urgent actions - execute immediately
            if (quickDecision == "EXECUTE_KILL") {
                executeAttack();
                return;
            } else if (quickDecision == "EMERGENCY_SHIELD") {
                executeDefensive();
                executeAttack();
                return;
            } else if (quickDecision == "DEFENSIVE_RETREAT") {
                repositionDefensive();
                executeDefensive();
                return;
            }
        }
    }
    
    // Try ensemble decision for complex scenarios
    // Mode-specific algorithm selection (using currentMode from line 3213)
    debugLog("Checking ensemble decision for mode: " + currentMode);
    if (currentMode == "OPTIMAL") {
        // Full ensemble with all strategies
        debugLog("Calling ensembleDecision...");
        var ensembleAction = ensembleDecision();
        debugLog("Ensemble action: " + ensembleAction);
        if (ensembleAction != null) {
            executeEnsembleAction(ensembleAction);
            return;
        }
    } else if (currentMode == "EFFICIENT") {
        // Limited ensemble - skip expensive strategies
        if (shouldUseAlgorithm(50000)) {
            var ensembleAction = ensembleDecisionLight();
            if (ensembleAction != null) {
                executeEnsembleAction(ensembleAction);
                return;
            }
        }
    } else if (currentMode == "SURVIVAL") {
        // Skip ensemble, use direct tactics
        if (shouldUseAlgorithm(20000)) {
            var quickAction = getQuickTacticalDecision();
            if (quickAction != null) {
                executeQuickAction(quickAction);
                return;
            }
        }
    }
    
    // Stage A: Ultra-Basic (UB) decisions
    if (getOperationLevel() == "PANIC") {
        // Emergency mode - just attack or flee
        if (currentDamage >= enemyHP) {
            executeAttack();
        } else if (currentEID >= myHP * 0.8) {
            // KITE away - move but keep attacking!
            var cells = getReachableCells(myCell, myMP);
            
            // Use arrayFoldLeft to find best kiting position
            var limitedCells = count(cells) > 10 ? arrayFilter(cells, function(c, idx) { return idx < 10; }) : cells;
            var bestResult = arrayFoldLeft(limitedCells, function(best, cell) {
                var dist = getCellDistance(cell, enemyCell);
                var score = dist * 10;  // Distance is good
                
                // But prefer kiting range where we can attack back
                if (dist >= 7 && dist <= 9) {
                    score += 150;  // Perfect for Lightninger
                }
                // Small bonus for Rhino gap coverage (2-3 only)
                if (enemyDistance >= 2 && enemyDistance <= 3) {
                    score += 50;  // Rhino gap filler (not primary!)
                }
                
                if (score > best[1]) {
                    return [cell, score];
                }
                return best;
            }, [myCell, -999999]);
            
            var bestCell = bestResult[0];
            
            if (bestCell != myCell) {
                if (moveToCell(bestCell) > 0) {
                    enemyDistance = getCellDistance(myCell, enemyCell);
                }
                // Attack while kiting! (26% life steal helps us survive)
                executeAttack();
            }
        } else {
            executeAttack();
        }
        return;
    }
    
    // Stage B: Standard positioning (skip when we have lots of ops for full evaluation)
    debugLog("Stage B: Standard positioning check");
    if (!canSpendOps(200000)) {
        // Find hit cells only
        var hitCells = findHitCells();
        
        if (count(hitCells) == 0) {
            // Move closer
            if (moveToCell(enemyCell) > 0) {
                enemyDistance = getCellDistance(myCell, enemyCell);
            }
            return;
        }
        
        // Pick best by simple score
        var bestCell = myCell;
        var bestScore = -999999;
        
        for (var i = 0; i < min(20, count(hitCells)); i++) {
            var cell = hitCells[i][0];  // FIX: hitCells returns [cell, weapon, damage] tuples
            var damage = calculateDamageFrom(cell);
            var eid = eidOf(cell);
            var score = damage - eid * 0.5;
            
            if (score > bestScore) {
                bestScore = score;
                bestCell = cell;
            }
        }
        
        if (bestCell != myCell) {
            if (moveToCell(bestCell) > 0) {
                enemyDistance = getCellDistance(myCell, enemyCell);
            }
        }
        executeAttack();
        return;
    }
    
    debugLog("Entering Stage C: Full evaluation");
    // Stage C: Full evaluation (skip expensive parts on turn 5+)
    
    // Unified kill commitment: use effective pkill with lifesteal modifier
    var lifeStealNow = calculateLifeSteal(currentDamage, enemy);
    var effectivePkill = pkillCurrent + min(0.2, lifeStealNow / enemyHP);  // Cap lifesteal contribution at 20%
    
    if (effectivePkill >= PKILL_COMMIT) {
        debugLog("Committing to attack - effectivePkill=" + effectivePkill + " (base=" + pkillCurrent + " lifesteal=" + lifeStealNow + ")");
        // Move to best position first if we can (but limit on turn 5+)
        var hitCells = turn >= 5 ? [] : findHitCells();
        var reachableHit = turn >= 5 ? [] : findReachableHitCells(hitCells);
        if (count(reachableHit) > 0) {
            var bestHit = reachableHit[0];
            for (var i = 1; i < count(reachableHit); i++) {
                if (reachableHit[i][2] > bestHit[2]) {  // Compare damage
                    bestHit = reachableHit[i];
                }
            }
            if (moveToCell(bestHit[0]) > 0) {
                enemyDistance = getCellDistance(myCell, enemyCell);
            }
        }
        executeAttack();
        
        // If enemy still alive and we have MP, reposition
        if (getLife(enemy) > 0 && myMP >= MP_REPOSITION_MIN) {
            repositionDefensive();
        }
        return;
    }
    
    // Check if we can setup 2-turn kill
    debugLog("Checking canSetupKill...");
    if (canSetupKill()) {
        debugLog("Setting up 2-turn kill");
        // Find position that maximizes damage while minimizing EID
        debugLog("Calling findHitCells...");
        var raw = findHitCells();
        debugLog("Found " + count(raw) + " hit cells");
        var candidates = [];
        // FIX: Extract just the cells from tuples [cell, weapon, damage]
        for (var i = 0; i < count(raw); i++) {
            push(candidates, raw[i][0]);
        }
        
        if (count(candidates) > M_CANDIDATES) {
            // Score and sort
            var scored = [];
            for (var i = 0; i < count(candidates); i++) {
                var cell = candidates[i];
                var damage = calculateDamageFrom(cell);
                var eid = eidOf(cell);
                var score = damage * 2 - eid; // Prioritize damage for setup
                push(scored, [score, cell]);
            }
            sort(scored);
            
            // Keep top M_CANDIDATES
            candidates = [];
            for (var i = count(scored) - 1; i >= max(0, count(scored) - M_CANDIDATES); i--) {
                push(candidates, scored[i][1]);
            }
        }
        
        var bestCell = evaluateCandidates(candidates);
        if (bestCell != myCell) {
            if (moveToCell(bestCell) > 0) {
                enemyDistance = getCellDistance(myCell, enemyCell);
            }
        }
        executeAttack();
        return;
    }
    
    // Check if we have healing over time active for kiting strategy
    var hasHoT = false;
    var myEffects = getEffects(myLeek);
    for (var i = 0; i < count(myEffects); i++) {
        if (myEffects[i][0] == EFFECT_HEAL) {  // Healing over time effect
            hasHoT = true;
            break;
        }
    }
    
    // KITING STRATEGY: If we have HoT, prioritize maintaining distance
    if (hasHoT && myHP < myMaxHP * 0.7) {
        debugLog("Kiting with HoT active - maintaining distance while healing");
        // Prefer 7-10 range for kiting
        var kitingRange = 8;
        
        if (enemyDistance < kitingRange - 1) {
            // Too close - back off
            var candidates = [];
            var reachable = getReachableCells(myCell, myMP);
            
            for (var i = 0; i < min(30, count(reachable)); i++) {
                var cell = reachable[i];
                var dist = getCellDistance(cell, enemyCell);
                if (dist >= kitingRange - 1 && dist <= kitingRange + 1) {
                    push(candidates, cell);
                }
            }
            
            if (count(candidates) > 0) {
                var bestKiteCell = candidates[0];
                var bestSafety = 999999;
                
                for (var i = 0; i < count(candidates); i++) {
                    var eid = eidOf(candidates[i]);
                    if (eid < bestSafety) {
                        bestSafety = eid;
                        bestKiteCell = candidates[i];
                    }
                }
                
                if (moveToCell(bestKiteCell) > 0) {
                    enemyDistance = getCellDistance(myCell, enemyCell);
                    debugLog("Kited to range " + enemyDistance);
                }
            }
        }
    }
    
    // Check threat level WITH LIFE STEAL (only if we'll actually attack)
    var willAttackThisTurn = false;
    var potentialLifeSteal = 0;
    
    // Check if we can and will attack this turn
    if (enemyDistance <= 10 && hasLOS(myCell, enemyCell) && myTP >= 5) {
        var weapons = getWeapons();
        for (var i = 0; i < count(weapons); i++) {
            var w = weapons[i];
            if (enemyDistance >= getWeaponMinRange(w) && enemyDistance <= getWeaponMaxRange(w) && myTP >= getWeaponCost(w)) {
                willAttackThisTurn = true;
                break;
            }
        }
    }
    
    if (willAttackThisTurn) {
        var potentialDamage = calculateDamageFrom(myCell);
        potentialLifeSteal = calculateLifeSteal(potentialDamage, enemy);
    }
    
    var netIncomingDamage = currentEID - potentialLifeSteal;
    var threatRatio = myEHP > 0 ? netIncomingDamage / myEHP : 1.0;
    
    // Dynamic threat adjustment based on actual lifesteal potential
    var adjustedHighThreat = THREAT_HIGH_RATIO * (1 + min(0.5, potentialLifeSteal / myEHP));
    
    // TACTICAL: Exploit enemy min range weapons (like Bazooka)
    if (ENEMY_MIN_RANGE >= 4 && enemyDistance < ENEMY_MIN_RANGE) {
        debugLog("🎯 CLOSE COMBAT ADVANTAGE! Enemy can't shoot (dist=" + enemyDistance + ", min=" + ENEMY_MIN_RANGE + ")");
        adjustedHighThreat = THREAT_HIGH_RATIO * 5.0;  // Be VERY aggressive when they can't shoot!
        
        // Enhanced Bazooka trap at range 3
        if (ENEMY_HAS_BAZOOKA && enemyDistance == 3) {
            debugLog("🦔 BAZOOKA TRAP: Enemy must waste MP to escape!");
            
            // Exploit with Rhino for massive damage
            if (inArray(getWeapons(), WEAPON_RHINO) && myTP >= 6) {
                debugLog("Rhino ready: 3 uses = 600+ damage potential!");
                setWeaponIfNeeded(WEAPON_RHINO);
                
                // Use all Rhino shots
                var rhinoUses = 0;
                while (rhinoUses < 3 && myTP >= 6) {
                    var result = useWeapon(enemy);
                    if (result == USE_SUCCESS || result == USE_CRITICAL) {
                        rhinoUses++;
                        myTP = getTP();
                        if (result == USE_CRITICAL) {
                            debugLog("CRITICAL Rhino shot!");
                        }
                    } else {
                        break;
                    }
                }
                debugLog("Rhino burst: " + rhinoUses + " shots fired");
            }
        }
        
        // General close range exploitation
        if (myTP >= 5) {
            debugLog("Exploiting close range - full attack!");
            executeAttack();
            
            // Stay close to deny their weapon
            if (myMP > 0) {
                var targetRange = ENEMY_HAS_BAZOOKA ? 3 : (ENEMY_MIN_RANGE - 1);
                var stayClose = getReachableCells(myCell, myMP);
                
                for (var i = 0; i < count(stayClose); i++) {
                    var c = stayClose[i];
                    var dist = getCellDistance(c, enemyCell);
                    
                    // Prioritize the trap range
                    if (dist == targetRange) {
                        if (moveToCell(c) > 0) {
                            enemyDistance = getCellDistance(myCell, enemyCell);
                            debugLog("Maintaining trap at range " + enemyDistance);
                        }
                        break;
                    }
                }
            }
            return;  // Skip normal decision flow
        }
    }
    
    // DANGER: Bazooka optimal range - be extra defensive
    if (ENEMY_HAS_BAZOOKA && enemyDistance >= 4 && enemyDistance <= 8) {
        debugLog("⚠️ BAZOOKA DANGER ZONE! Distance " + enemyDistance);
        adjustedHighThreat = THREAT_HIGH_RATIO * 0.6;  // Much lower threshold - prioritize survival
        
        // Try to get OUT of Bazooka range or INTO min range
        if (threatRatio >= adjustedHighThreat * 0.8) {
            debugLog("Evading Bazooka range!");
            // Either close to <4 or retreat to >8
            if (enemyDistance <= 6) {
                // Closer to min range - rush in!
                debugLog("Rushing to close combat!");
                var step = bestApproachStep(enemyCell);
                if (moveToCell(step) > 0) {
                    enemyDistance = getCellDistance(myCell, enemyCell);
                }
                executeAttack();
            } else {
                // Closer to max range - back off
                debugLog("Retreating from Bazooka range!");
                repositionDefensive();
            }
            return;
        }
    }
    
    if (threatRatio >= adjustedHighThreat) {
        debugLog("High threat mode - KITING - ratio=" + threatRatio + " (lifesteal=" + potentialLifeSteal + ", willAttack=" + willAttackThisTurn + ")");
        
        // KITE: Attack FIRST while in range, THEN flee!
        if (enemyDistance >= 2 && enemyDistance <= 12 && hasLOS(myCell, enemyCell)) {
            debugLog("Kiting - attacking BEFORE retreating");
            executeAttack();  // This heals us with 26% life steal!
        }
        
        // NOW move away to safer position
        repositionDefensive();
        
        // Try to attack again from new position if still in range
        enemyDistance = getCellDistance(myCell, enemyCell);
        if (myTP > 0 && enemyDistance >= 6 && enemyDistance <= 10 && hasLOS(myCell, enemyCell)) {
            debugLog("Kiting - bonus attack from new position");
            executeAttack();
        }
        
        // Use remaining TP defensively
        if (myTP >= 3) {
            executeDefensive();
        }
    } else {
        debugLog("Standard mode - ratio=" + threatRatio);
        
        // Find optimal position
        var candidates = [];
        
        // Get ALL hit cells around enemy (aggressive limits on early turns)
        var allHitCells = [];
        var reachableHitCells = [];
        
        // Much more aggressive early turn limits
        debugLog("Checking hit cells for turn " + turn);
        if (turn <= 2) {
            debugLog("Turn " + turn + " - skip complex hit detection");
            // On turns 1-2, just check if we can hit from current position
            var dist = getCellDistance(myCell, enemyCell);
            if (dist >= 2 && dist <= 10 && hasLOS(myCell, enemyCell)) {
                push(allHitCells, [myCell, WEAPON_LIGHTNINGER, 400]);
                push(reachableHitCells, [myCell, WEAPON_LIGHTNINGER, 400]);
            }
        } else if (canSpendOps(2000000)) {
            debugLog("Calling findHitCells for standard detection...");
            allHitCells = findHitCells();
            debugLog("Found " + count(allHitCells) + " hit cells");
            debugLog("Calling findReachableHitCells...");
            reachableHitCells = findReachableHitCells(allHitCells);
            debugLog("Found " + count(reachableHitCells) + " reachable hit cells");
        } else {
            debugLog("Turn " + turn + " - simplified hit detection");
            // Just check current position and immediate moves
            var simple = getReachableCells(myCell, min(3, myMP));
            for (var i = 0; i < min(10, count(simple)); i++) {
                var cell = simple[i];
                var dist = getCellDistance(cell, enemyCell);
                if (dist >= 1 && dist <= 7 && hasLOS(cell, enemyCell)) {
                    push(allHitCells, [cell, null, 100]);
                    push(reachableHitCells, [cell, null, 100]);
                }
            }
        }
        
        // Fix 10: Debug visualization - add early exit for performance
        if (turn >= 5 && turn <= 8 && canSpendOps(50000)) {  // Only if we have ops to spare
            visualizeHitCells(allHitCells);
        }
        
        // If we have reachable hit cells, ATTACK IMMEDIATELY!
        if (count(reachableHitCells) > 0) {
            debugLog("Have " + count(reachableHitCells) + " reachable hit cells - ATTACKING!");
            
            // Find best reachable hit cell by damage AND position
            var bestHitCell = reachableHitCells[0][0];
            var bestScore = 0;
            
            for (var i = 0; i < count(reachableHitCells); i++) {
                var cell = reachableHitCells[i][0];
                var damage = reachableHitCells[i][2];
                var dist = getCellDistance(cell, enemyCell);
                
                // Score based on damage with proper weapon range preferences
                var score = damage;
                if (dist == 5) score += 1200;  // Best for Grenade AoE flexibility
                if (dist == 6) score += 1000;  // Good for both weapons
                if (dist == 7) score += 800;   // OK for both but less AoE options
                if (dist == 3) score += 600;   // Rhino sweet spot (3 uses!)
                if (dist == 2) score -= 300;   // Too close, limited options
                
                if (score > bestScore) {
                    bestScore = score;
                    bestHitCell = cell;
                }
            }
            
            // Move to best hit cell and attack
            if (bestHitCell != myCell) {
                if (moveToCell(bestHitCell) > 0) {
                    enemyDistance = getCellDistance(myCell, enemyCell);
                }
            }
            executeAttack();
            return;  // Exit after attacking
        }
        
        // If no reachable hit cells, MOVE INTO ATTACK RANGE!
        if (count(reachableHitCells) == 0) {
            debugLog("No reachable hit cells, need to move into weapon range");
            
            // Priority: Get into optimal range for best damage/TP ratio
            var targetDist = 7;  // OPTIMAL for both Grenade AND Lightninger!
            var reach = getReachableCells(myCell, myMP);
            var bestMove = myCell;
            var bestScore = -999999;
            
            for (var i = 0; i < min(30, count(reach)); i++) {
                var cell = reach[i];
                var dist = getCellDistance(cell, enemyCell);
                var mpCost = getCellDistance(myCell, cell);
                var score = 0;
                
                // Fix 11: Consider TP opportunity cost of movement
                // Moving costs MP which could be saved for next turn's positioning
                var tpValueOfMP = myTP < 10 ? 50 : 20;  // MP more valuable when low on TP
                score -= mpCost * tpValueOfMP;
                
                // Strongly prefer cells in optimal weapon range
                // Fix 8: Recognize Rhino as highest DPS at range 3
                if (dist == 3) score += 4000;  // BEST for Rhino - 3x200 damage!
                if (dist == 5) score += 3500;  // BEST - Grenade with max AoE flexibility
                if (dist == 6) score += 3000;  // Great - both weapons work well
                if (dist == 7) score += 2500;  // Good - both weapons but less AoE
                if (dist == 4) score += 2000;  // OK - Grenade works
                if (dist == 2) score += 1500;  // Rhino still works
                if (dist >= 8 && dist <= 10) score += 1500; // Lightninger only
                if (dist == 2) score += 500;   // Close range, limited options
                
                // Penalize being too close or too far
                if (dist < 4) score -= 500;  // Too close for main weapons!
                if (dist > 10) score -= 300; // Too far
                
                // Extra bonus for optimal range 7
                score -= abs(dist - 7) * 150;  // Strong preference for range 7
                
                // Check if we'd have LOS
                if (hasLOS(cell, enemyCell)) score += 500;
                
                if (score > bestScore) {
                    bestScore = score;
                    bestMove = cell;
                }
            }
            
            if (bestMove != myCell) {
                debugLog("Moving to cell for attack range");
                if (moveToCell(bestMove) > 0) {
                    enemyDistance = getCellDistance(myCell, enemyCell);
                }
                // Try to attack after moving!
                executeAttack();
                return;
            }
            
            // Fallback to original logic if needed
            var bestHitCell = null;
            bestScore = -999999;
            
            for (var i = 0; i < min(20, count(allHitCells)); i++) {
                var hitData = allHitCells[i];
                var cell = hitData[0];
                var damage = hitData[2];  // Use stored damage
                var dist = getCellDistance(myCell, cell);
                var eid = eidOf(cell);  // Use cached EID
                
                // Score based on damage potential and safety
                var score = damage - eid * 0.5 - dist * 10;
                
                if (score > bestScore) {
                    bestScore = score;
                    bestHitCell = cell;
                }
            }
            
            // Use single best step approach
            var targetCell = bestHitCell != null ? bestHitCell : enemyCell;
            var step = bestApproachStep(targetCell);
            if (step != myCell) {
                debugLog("Moving to approach step " + step);
                if (moveToCell(step) > 0) {
                    enemyDistance = getCellDistance(myCell, enemyCell);
                }
            }
            
            // HARASSMENT: Attack from any range we can!
            if (enemyDistance <= 10) {
                // In Lightninger range - HARASS!
                debugLog("In harassment range " + enemyDistance + " - attacking!");
                executeAttack();  // Attack FIRST to maximize damage
                // Shield with remaining TP
                if (myTP >= 3) executeDefensive();
            } else if (enemyDistance > 10 && enemyDistance <= 12) {
                // Almost in range - move closer and attack
                debugLog("Near harassment range - approaching to attack");
                // Try to get to range 10 or better
                var reachableCells = getReachableCells(myCell, min(myMP, 3));
                var bestDist = enemyDistance;
                var bestCell = myCell;
                
                for (var i = 0; i < count(reachableCells); i++) {
                    var cell = reachableCells[i];
                    var dist = getCellDistance(cell, enemyCell);
                    if (dist <= 10 && dist < bestDist && hasLOS(cell, enemyCell)) {
                        bestDist = dist;
                        bestCell = cell;
                    }
                }
                
                if (bestCell != myCell) {
                    moveToCell(bestCell);
                    enemyDistance = getCellDistance(myCell, enemyCell);
                }
                
                // Now attack if in range
                if (enemyDistance <= 10) {
                    executeAttack();
                }
                // Shield with remaining TP
                if (myTP >= 3) executeDefensive();
            } else {
                // Too far - approach while shielding
                debugLog("Far approach - using shields first");
                executeDefensive();
                // Attack with remaining TP if any (shouldn't happen but just in case)
                if (myTP >= 6) executeAttack();
            }
            return;
        }
        
        // Add some safe cells if we have ops
        if (canSpendOps(100000)) {
            var safeCells = findSafeCells();
            for (var i = 0; i < min(20, count(safeCells)); i++) {
                push(candidates, safeCells[i]);
            }
        }
        
        // Evaluate candidates
        if (count(candidates) > M_CANDIDATES) {
            // Quick score and filter
            var scored = [];
            for (var i = 0; i < count(candidates); i++) {
                var cell = candidates[i];
                var damage = calculateDamageFrom(cell);
                var eid = eidOf(cell);
                var score = damage - eid * WEIGHT_SAFETY;
                push(scored, [score, cell]);
            }
            sort(scored);
            
            candidates = [];
            for (var i = count(scored) - 1; i >= max(0, count(scored) - M_CANDIDATES); i--) {
                push(candidates, scored[i][1]);
            }
        }
        
        var bestCell = evaluateCandidates(candidates);
        
        // Move if beneficial
        if (bestCell != myCell) {
            var currentScore = evaluatePosition(myCell);
            var newScore = evaluatePosition(bestCell);
            
            // If we have reachable hit cells, always move to the best one
            // Otherwise require 10% improvement
            var moveThreshold = count(reachableHitCells) > 0 ? 1.0 : 1.1;
            
            if (newScore >= currentScore * moveThreshold) {
                if (moveToCell(bestCell) > 0) {
                    enemyDistance = getCellDistance(myCell, enemyCell);
                }
            }
        }
        
        // ALWAYS ATTACK if we can hit the enemy!
        var canHit = false;
        if (enemyDistance <= 10 && hasLOS(myCell, enemyCell)) {
            canHit = true;
            debugLog("Can hit from current position at range " + enemyDistance);
        }
        
        if (canHit) {
            // Attack FIRST to maximize damage
            executeAttack();
            
            // Use remaining TP for defense if needed
            if (myTP >= 3) {
                executeDefensive();
            }
        } else {
            // Can't hit - move closer and shield
            debugLog("Can't hit from distance " + enemyDistance + ", need to approach");
            
            // Move closer first
            if (myMP > 0) {
                var step = bestApproachStep(enemyCell);
                if (step != myCell) {
                    debugLog("Moving closer to enemy");
                    if (moveToCell(step) > 0) {
                        enemyDistance = getCellDistance(myCell, enemyCell);
                        debugLog("New distance: " + enemyDistance);
                    }
                }
            }
            
            // Then shield with remaining TP
            if (myTP >= 4) {
                executeDefensive();
            }
        }
    }
    
    // Visualize EID map at end of decision
    debugLog("Checking visualization...");
    if (debugEnabled) {
        debugLog("Calling visualizeEID...");
        visualizeEID();
        debugLog("Visualization complete");
    }
    debugLog("makeDecision() complete - exiting");
}

