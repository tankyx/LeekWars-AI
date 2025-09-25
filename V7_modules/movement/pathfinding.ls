// V7 Module: movement/pathfinding.ls
// A* pathfinding to optimal damage cells
// Version 7.0.1 - Object literal fixes (Jan 2025)

// === HELPER FUNCTIONS ===
function createPathResult(targetCell, path, damage, weaponId, reachable, distance, useTeleport) {
    // Use push() instead of direct array indexing which doesn't work in LeekScript V4+
    var result = [];
    push(result, (targetCell != null) ? targetCell : -1);    // [0] targetCell
    push(result, (path != null) ? path : []);                // [1] path
    push(result, (damage != null) ? damage : 0);             // [2] damage
    push(result, weaponId);                                  // [3] weaponId (can be null)
    push(result, (reachable != null) ? reachable : false);   // [4] reachable
    push(result, (distance != null) ? distance : 0);        // [5] distance
    push(result, (useTeleport != null) ? useTeleport : false); // [6] useTeleport
    
    // PathResult created
    
    return result;
}

// === MAIN PATHFINDING FUNCTION (ARRAY-BASED) ===
function findOptimalPathFromArray(currentCell, damageArray) {
    // Pathfinding array processed
    var localCap = terrainLOSDone ? MAX_PATHFIND_CELLS : 8;
    
    // Sort array by damage potential (highest first); filter out dead enemies cheaply first
    var aliveDamageArray = [];
    for (var di = 0; di < count(damageArray); di++) {
        var de = damageArray[di];
        if (de == null) continue;
        if (count(de) > 3) { var en = de[3]; if (en != null && getLife(en) <= 0) continue; }
        push(aliveDamageArray, de);
    }
    var sortedArray = sortArrayByDamage(aliveDamageArray);
    // Unified behavior for all builds: rely solely on the damage array
    
    // Try single-turn A* first to each high-damage cell (weapon-only)
    // Trying top damage cells
    
    for (var i = 0; i < min(localCap, count(sortedArray)); i++) {
        var targetData = sortedArray[i];
        var targetCell = targetData[0];
        var expectedDamage = targetData[1];
        var weaponId = targetData[2]; // weapon/chip ID from damage calculation
        // Skip chip-only zones in the primary pass so we don't march to
        // non-weapon cells and then have no attack available.
        if (weaponId == null || !isWeapon(weaponId)) {
            continue;
        }
        
        // Trying pathfinding to damage cell
        
        var path = aStar(currentCell, targetCell, myMP);
        
        if (path != null && count(path) <= myMP + 1) {
            // Mark chosen path with text indicators
            // Path found and marked
            
            return createPathResult(targetCell, path, expectedDamage, weaponId, true, count(path) - 1, false);
        } else {
            // Path attempt failed
        }
    }

    // Secondary single-turn pass: allow chip zones only if no weapon-vantage
    for (var i = 0; i < min(localCap, count(sortedArray)); i++) {
        var t2 = sortedArray[i];
        if (t2 == null) continue;
        var t2cell = t2[0];
        var t2dmg = t2[1];
        var t2wid = t2[2];
        if (t2wid != null && isWeapon(t2wid)) continue; // weapon pass already tried
        var pathc = aStar(currentCell, t2cell, myMP);
        if (pathc != null && count(pathc) <= myMP + 1) {
            // Carry the chip id as the recommended action so combat can use it
            return createPathResult(t2cell, pathc, t2dmg, t2wid, true, count(pathc) - 1, false);
        }
    }
    
    // Secondary pass: prefer any reachable damage cell within MP (by distance),
    // not just the top-by-damage ones. This fixes cases where a slightly lower
    // damage but reachable cell is ignored.
    var reachableCandidates = [];
    for (var ri = 0; ri < count(aliveDamageArray); ri++) {
        var rd = aliveDamageArray[ri];
        if (rd == null || count(rd) < 3) continue;
        var rcell = rd[0];
        var rdam = rd[1];
        var rweap = rd[2];
        if (rweap != null && !isWeapon(rweap)) continue;
        if (getCellDistance(currentCell, rcell) <= myMP) {
            // Maintain a small top list by damage
            if (count(reachableCandidates) < 20) {
                push(reachableCandidates, rd);
            } else {
                // Insert if better than the smallest in list
                var minIdx = 0;
                for (var mi = 1; mi < count(reachableCandidates); mi++) {
                    if (reachableCandidates[mi][1] < reachableCandidates[minIdx][1]) {
                        minIdx = mi;
                    }
                }
                if (rdam > reachableCandidates[minIdx][1]) {
                    reachableCandidates[minIdx] = rd;
                }
            }
        }
    }
    // Try A* to those reachable-by-distance candidates, highest damage first
    if (count(reachableCandidates) > 0) {
        // Sort desc by damage
    for (var i = 0; i < count(reachableCandidates) - 1; i++) {
        for (var j = i + 1; j < count(reachableCandidates); j++) {
            if (reachableCandidates[j][1] > reachableCandidates[i][1]) {
                var tmp = reachableCandidates[i];
                reachableCandidates[i] = reachableCandidates[j];
                reachableCandidates[j] = tmp;
            }
        }
    }
    var rcLimit = terrainLOSDone ? count(reachableCandidates) : min(6, count(reachableCandidates));
    for (var ci = 0; ci < rcLimit; ci++) {
        var cand = reachableCandidates[ci];
        var tCell = cand[0];
        var tDmg = cand[1];
        var tWeap = cand[2];
        var path2 = aStar(currentCell, tCell, myMP);
            if (path2 != null && count(path2) <= myMP + 1) {
                return createPathResult(tCell, path2, tDmg, tWeap, true, count(path2) - 1, false);
            }
        }
    }

    // MAGIC-BUILD TARGETED FALLBACK: walk toward nearest FLAME/DESTROYER vantage (multi-turn)
    if (isMagicBuild && enemyCell != null) {
        var bestPathLen = 9999;
        var bestPath = null;
        var bestCell = null;
        var maxProbe = min(100, count(sortedArray));
        for (var i = 0; i < maxProbe; i++) {
            var e = sortedArray[i];
            if (e == null || count(e) < 3) continue;
            var cell = e[0];
            var wid = e[2];
            if (wid != WEAPON_FLAME_THROWER && wid != WEAPON_DESTROYER) continue;
            // Probe a longer A* to plan multi-turn closing
            var p = aStar(currentCell, cell, myMP * 6);
            if (p != null && count(p) > 1) {
                var plen = count(p) - 1;
                if (plen < bestPathLen) {
                    bestPathLen = plen;
                    bestPath = p;
                    bestCell = cell;
                }
            }
        }
        if (bestPath != null) {
            var steps = min(myMP, count(bestPath) - 1);
            var moveTo = bestPath[steps];
            var actual2 = [];
            for (var s = 0; s <= steps; s++) { push(actual2, bestPath[s]); }
            return createPathResult(moveTo, actual2, 0, null, steps <= myMP, steps, false);
        }
    }

    // LAST-MILE ALIGNMENT (MAGIC + FLAME): only when we have exactly 1 MP left; otherwise prefer full-path vantages
    if (isMagicBuild && myMP == 1 && enemyCell != null && inArray(getWeapons(), WEAPON_FLAME_THROWER)) {
        var distBand = getCellDistance(currentCell, enemyCell);
        if (distBand >= 6 && distBand <= 8 && !isOnSameLine(currentCell, enemyCell)) {
            var neigh = getWalkableNeighbors(currentCell);
            var bestAlign = null;
            var bestScore = -9999;
            for (var ni = 0; ni < count(neigh); ni++) {
                var n = neigh[ni];
                if (getCellContent(n) != CELL_EMPTY) continue;
                var d = getCellDistance(n, enemyCell);
                if (d < 2 || d > 8) continue; // FLAME range
                if (!isOnSameLine(n, enemyCell)) continue;
                if (!checkLineOfSight(n, enemyCell)) continue;
                // Prefer safer alignment positions
                var eid = estimateIncomingDamageAtCell(n);
                var score = 200 - eid; // low EID better
                if (score > bestScore) { bestScore = score; bestAlign = n; }
            }
            if (bestAlign != null) {
                var pathAlign = [currentCell, bestAlign];
                return createPathResult(bestAlign, pathAlign, 0, WEAPON_FLAME_THROWER, true, 1, false);
            }
        }
    }

    // LAST-MILE NUDGE (MAGIC + DESTROYER): only when we have exactly 1 MP left; otherwise prefer full-path vantages
    if (isMagicBuild && myMP == 1 && enemyCell != null && inArray(getWeapons(), WEAPON_DESTROYER)) {
        var distD = getCellDistance(currentCell, enemyCell);
        var needCloser = (distD == 7); // one step away from range
        var needLoSFix = (distD >= 1 && distD <= 6 && !checkLineOfSight(currentCell, enemyCell));
        if (needCloser || needLoSFix) {
            var neighD = getWalkableNeighbors(currentCell);
            var bestD = null;
            var bestDScore = -9999;
            for (var di = 0; di < count(neighD); di++) {
                var n2 = neighD[di];
                if (getCellContent(n2) != CELL_EMPTY) continue;
                var d2 = getCellDistance(n2, enemyCell);
                if (d2 < 1 || d2 > 6) continue; // DESTROYER range
                if (!checkLineOfSight(n2, enemyCell)) continue; // needs LoS
                // Prefer safer squares with lower EID
                var eid2 = estimateIncomingDamageAtCell(n2);
                var score2 = 220 - eid2; // slight bias over FLAME align
                if (score2 > bestDScore) { bestDScore = score2; bestD = n2; }
            }
            if (bestD != null) {
                var pathD = [currentCell, bestD];
                return createPathResult(bestD, pathD, 0, WEAPON_DESTROYER, true, 1, false);
            }
        }
    }

    // No single-turn path found - consider M-LASER alignment first if equipped
    // MAGIC CLOSE-IN BAND CHASE: if we still have no actionable path, greedily step toward
    // DESTROYER/FLAME/VENOM bands even without a precomputed damage zone.
    if (isMagicBuild && enemyCell != null) {
        var distNow = getCellDistance(currentCell, enemyCell);
        // Target bands in order of priority: ≤6 (DESTROYER), ≤8 (FLAME), ≤10 (VENOM)
        var targets = [6, 8, 10];
        for (var ti = 0; ti < count(targets); ti++) {
            var band = targets[ti];
            if (distNow <= band) continue;
            var ring = getCellsAtExactDistance(enemyCell, band);
            var stride = max(1, floor(count(ring) / (terrainLOSDone ? 24 : 40)));
            var bestCell = null;
            var bestScore = -99999;
            for (var ri = 0; ri < count(ring); ri += stride) {
                var cell = ring[ri];
                if (cell == null || cell < 0 || cell > 612) continue;
                if (getCellContent(cell) != CELL_EMPTY) continue;
                var p = aStar(currentCell, cell, myMP);
                if (p == null || count(p) <= 1) continue;
                // Prefer LoS to enemy and lower EID
                var los = checkLineOfSight(cell, enemyCell) ? 1 : 0;
                var eid = estimateIncomingDamageAtCell(cell);
                var score = 100 * los - eid;
                if (score > bestScore) { bestScore = score; bestCell = cell; }
            }
            if (bestCell != null) {
                var path = aStar(currentCell, bestCell, myMP);
                if (path != null && count(path) > 1) {
                    return createPathResult(path[min(myMP, count(path) - 1)], path, 0, null, true, min(myMP, count(path) - 1), false);
                }
            }
        }
        // If no band cell is reachable, step toward enemy to reduce distance
        var toward = aStar(currentCell, enemyCell, myMP);
        if (toward != null && count(toward) > 1) {
            return createPathResult(toward[min(myMP, count(toward) - 1)], toward, 0, null, false, min(myMP, count(toward) - 1), false);
        }
    }
    var myWeaponsForAlign = getWeapons();
    if (enemyCell != null && myWeaponsForAlign != null && inArray(myWeaponsForAlign, WEAPON_M_LASER)) {
        var alignTarget = findMLaserAlignmentPosition();
        if (alignTarget != null) {
            var alignPath = aStar(currentCell, alignTarget, myMP);
            if (alignPath != null && count(alignPath) > 1) {
                var moveToCell = alignPath[min(myMP, count(alignPath) - 1)];
                return createPathResult(moveToCell, alignPath, 0, WEAPON_M_LASER, getCellDistance(currentCell, moveToCell) <= myMP, getCellDistance(currentCell, moveToCell), false);
            }
        }
    }

    // KEEP-OUT VS STRENGTH BUILDS: if we can't attack this turn, bias stepping to 7–10 ring with cover
    if (primaryTarget != null && enemyCell != null) {
        var enemyStr = getStrength(primaryTarget);
        var enemyMag = getMagic(primaryTarget);
        var enemyAgi = getAgility(primaryTarget);
        var isStrengthEnemy = (enemyStr > max(enemyMag, enemyAgi) + 100);
        if (isStrengthEnemy) {
            var myWs = getWeapons();
            var hasNonMelee = false;
            for (var i = 0; i < count(myWs); i++) {
                if (getWeaponMaxRange(myWs[i]) >= 5) { hasNonMelee = true; break; }
            }
            if (hasNonMelee) {
                var bestKeepCell = null;
                var bestKeepScore = -9999;
                var topCells = [];
                var topScores = [];
                // Evaluate ring distances 7..10
                for (var d = 7; d <= 10; d++) {
                    var ring = getCellsAtExactDistance(enemyCell, d);
                    // Sample ring to cap operations (max ~24 samples per ring)
                    var stride = max(1, floor(count(ring) / 24));
                    for (var r = 0; r < count(ring); r += stride) {
                        var cell = ring[r];
                        if (cell == null || cell < 0 || cell > 612) continue;
                        if (getCellContent(cell) != CELL_EMPTY) continue;
                        // Approximate path length by Manhattan/hex distance; confirm with A* only for winner
                        var pathLen = getCellDistance(currentCell, cell);
                        var reachable = (pathLen <= myMP);
                        // Cover and LOS metrics
                        var cover = countAdjacentObstacles(cell);
                        var hasLOS = checkLineOfSight(cell, enemyCell);
                        // Score: prefer reachable, more cover, no LOS, and shorter path
                        var score = 0;
                        if (reachable) score += 200; else score += 50;
                        score += min(cover * 10, 40);
                        if (!hasLOS) score += 60; // bonus to break LOS
                        score += max(0, 30 - pathLen); // closer to us is better
                        // Poke bonus: if we can shoot from here with a mid/long weapon and EID is acceptable
                        if (hasLOS) {
                            var myWs2 = getWeapons();
                            var poke = false;
                            for (var pw = 0; pw < count(myWs2); pw++) {
                                var wpn = myWs2[pw];
                                if (getWeaponMaxRange(wpn) >= 5) {
                                    var inRange = (getCellDistance(cell, enemyCell) >= getWeaponMinRange(wpn) && getCellDistance(cell, enemyCell) <= getWeaponMaxRange(wpn));
                                    if (inRange) { poke = true; break; }
                                }
                            }
                            if (poke) {
                                var eidHere = estimateIncomingDamageAtCell(cell);
                                if (eidHere < 250) score += 60; else if (eidHere < 400) score += 30; // modest poke bonus
                            }
                        }
                        if (score > bestKeepScore) { bestKeepScore = score; bestKeepCell = cell; }
                        // Maintain top-3 candidates for refinement
                        if (count(topCells) < 3) {
                            push(topCells, cell);
                            push(topScores, score);
                        } else {
                            var minIdx = 0;
                            for (var ti = 1; ti < 3; ti++) { if (topScores[ti] < topScores[minIdx]) minIdx = ti; }
                            if (score > topScores[minIdx]) { topCells[minIdx] = cell; topScores[minIdx] = score; }
                        }
                    }
                }
                // Refine top candidates by estimating enemy A* steps to LoS on the cell
                if (count(topCells) > 0) {
                    var refinedBestCell = bestKeepCell;
                    var refinedBestScore = bestKeepScore;
                    var emp = getMP(primaryTarget);
                    for (var ti = 0; ti < count(topCells); ti++) {
                        var c = topCells[ti];
                        var base = topScores[ti];
                        var refinedSteps = refinedStepsForEnemyToGainLoS(primaryTarget, c);
                        var delta = refinedSteps - emp;
                        var bonus = (delta <= 0) ? -20 : min(delta * 12, 60);
                        var total = base + bonus;
                        if (total > refinedBestScore) {
                            refinedBestScore = total;
                            refinedBestCell = c;
                        }
                    }
                    bestKeepCell = refinedBestCell;
                    bestKeepScore = refinedBestScore;
                }
                if (bestKeepCell != null) {
                    // Mark chosen hiding/keep-out cell
                    markText(bestKeepCell, "H", getColor(0, 128, 255), 10);
                    var kp = aStar(currentCell, bestKeepCell, myMP * 2);
                    if (kp != null && count(kp) > 1) {
                        var steps = min(myMP, count(kp) - 1);
                        var moveTo = kp[steps];
                        var actual = [];
                        for (var s = 0; s <= steps; s++) { push(actual, kp[s]); }
                        return createPathResult(moveTo, actual, 0, null, steps <= myMP, steps, false);
                    }
                }
            }
        }
    }

    // No single-turn path found - move toward best damage zone
    // No single-turn paths found, moving toward damage zone
    
    // Try to move toward the highest damage cell (even if unreachable this turn)
    if (count(sortedArray) > 0) {
        var bestTarget = sortedArray[0];
        var bestCell = bestTarget[0];
        var bestDamage = bestTarget[1];
        var bestWeapon = bestTarget[2];
        
        // Moving toward best damage cell
        
        // IMPROVED: Instead of moving toward damage zone, move to weapon range of enemy
        // Get equipped weapons to find optimal positioning
        var weapons = getWeapons();
        var targetPosition = null;
        
        if (weapons != null && count(weapons) > 0 && enemyCell != null) {
            // Find the best weapon we can afford and its optimal range
            var affordableWeapon = null;
            var weaponRange = null;
            var bestWeaponValue = 0;
            
            // Weapon selection based on build type
            
            for (var w = 0; w < count(weapons); w++) {
                var weapon = weapons[w];
                var cost = getWeaponCost(weapon);
                
                if (myTP >= cost) {
                    var minRange = getWeaponMinRange(weapon);
                    var maxRange = getWeaponMaxRange(weapon);
                    
                    // Use dynamic weapon selection to find best weapon for current situation
                    // For pathfinding, use weapon's optimal range instead of current distance
                    var optimalDistance = floor((minRange + maxRange) / 2);
                    var testScenario = buildScenarioForWeapon(weapon, myTP, getChips(), optimalDistance, false);
                    if (testScenario != null) {
                        var weaponValue = calculateScenarioValue(testScenario, weapon);
                        
                        // Select weapon with highest value
                        if (affordableWeapon == null || weaponValue > bestWeaponValue) {
                            affordableWeapon = weapon;
                            weaponRange = [minRange, maxRange];
                            bestWeaponValue = weaponValue;
                            // Weapon selected for pathfinding
                        }
                    }
                }
            }
            
            if (affordableWeapon != null && weaponRange != null) {
                // Targeting optimal weapon range
                
                // Find optimal distance within weapon range
                var targetDistance = weaponRange[0]; // Start with minimum range
                if (affordableWeapon == WEAPON_RHINO) {
                    targetDistance = 3; // Middle of 2-4 range for flexibility
                } else if (affordableWeapon == WEAPON_ELECTRISOR) {
                    targetDistance = 7; // Exact range required
                } else if (weaponRange[1] > weaponRange[0]) {
                    targetDistance = floor((weaponRange[0] + weaponRange[1]) / 2); // Middle of range
                }
                
                // Find cells at target distance from enemy
                var targetCells = getCellsAtExactDistance(enemyCell, targetDistance);
                var bestTargetCell = null;
                var bestTargetDistance = 999;
                
                for (var t = 0; t < count(targetCells) && t < 15; t++) {
                    var cell = targetCells[t];
                    if (getCellContent(cell) == CELL_EMPTY) {
                        var distanceFromUs = getCellDistance(currentCell, cell);
                        if (distanceFromUs < bestTargetDistance) {
                            bestTargetDistance = distanceFromUs;
                            bestTargetCell = cell;
                        }
                    }
                }
                
                if (bestTargetCell != null) {
                    targetPosition = bestTargetCell;
                    if (debugEnabled) {
                        // Optimal weapon position found
                    }
                }
            }
        }
        
        // If no weapon-specific position found, fall back to original logic
        if (targetPosition == null) {
            targetPosition = bestCell;
        }
        
        // Try to get as close as possible to the target position
        var pathToBest = aStar(currentCell, targetPosition, myMP * 4); // Allow longer path for distant enemies
        if (pathToBest != null && count(pathToBest) > 1) {
            // Take as many steps as possible toward the target
            var stepsToTake = min(myMP, count(pathToBest) - 1);
            var moveToCell = pathToBest[stepsToTake];

            // Create a path with only the steps we can take this turn
            var actualPath = [];
            for (var step = 0; step <= stepsToTake; step++) {
                push(actualPath, pathToBest[step]);
            }

            // Moving steps toward target position

            // ALWAYS move if we can - even if we can't attack immediately, we're making progress
            // Do NOT set a recommended weapon when we cannot attack this turn to avoid
            // starting combat with an unreachable weapon choice.
            if (stepsToTake > 0) {
                return createPathResult(moveToCell, actualPath, 0, null, false, stepsToTake, false);
            }
        }
    }
    
    // Multi-turn pathfinding fallback
    var multiTurnResult = findMultiTurnPath(currentCell, sortedArray);
    if (multiTurnResult != null) {
        return multiTurnResult;
    }
    
    // No high-damage cell reachable - find max damage from array
    var maxDamage = 0;
    for (var i = 0; i < count(damageArray); i++) {
        var damage = damageArray[i][1];
        if (damage > maxDamage) {
            maxDamage = damage;
        }
    }
    
    // If all damage is 0, move toward enemy to get in weapon range
    // Damage analysis complete
    
    if (maxDamage == 0) {
        // Check if we have M-Laser and should seek alignment
        var weapons = getWeapons();
        if (inArray(weapons, WEAPON_M_LASER)) {
            var alignmentTarget = findMLaserAlignmentPosition();
            if (alignmentTarget != null) {
                // Seeking M-Laser alignment position
                var pathToAlignment = aStar(currentCell, alignmentTarget, myMP);
                if (pathToAlignment != null && count(pathToAlignment) > 1) {
                    var moveToCell = pathToAlignment[min(myMP, count(pathToAlignment) - 1)];
                    
                    return createPathResult(moveToCell, pathToAlignment, 0, WEAPON_M_LASER, getCellDistance(currentCell, moveToCell) <= myMP, getCellDistance(currentCell, moveToCell), false);
                }
            }
        }
        
        // Smart positioning based on equipped weapons and their DPS potential
        var bestPosition = findBestWeaponPosition(currentCell, weapons);
        if (bestPosition != null) {
            // Moving to optimal weapon position
            
            var pathToPosition = aStar(currentCell, bestPosition.cell, myMP);
            if (pathToPosition != null && count(pathToPosition) > 1) {
                var moveToCell = pathToPosition[min(myMP, count(pathToPosition) - 1)];
                
                return createPathResult(moveToCell, pathToPosition, 0, bestPosition.weapon, false, min(myMP, count(pathToPosition) - 1), false);
            }
        }
        
        // IMPROVED: If smart positioning failed, use weapon-specific targeting
        if (enemyCell != null) {
            var targetPosition = findWeaponSpecificPosition(currentCell, weapons, enemyCell);
            if (targetPosition != null) {
                // Using weapon-specific position
                
                var pathToTarget = aStar(currentCell, targetPosition.cell, myMP);
                if (pathToTarget != null && count(pathToTarget) > 1) {
                    var moveToCell = pathToTarget[min(myMP, count(pathToTarget) - 1)];
                    
                    // VALIDATION: Ensure destination allows attack with the weapon
                    var destDistance = getCellDistance(moveToCell, enemyCell);
                    var minRange = getWeaponMinRange(targetPosition.weapon);
                    var maxRange = getWeaponMaxRange(targetPosition.weapon);
                    var canAttack = (destDistance >= minRange && destDistance <= maxRange);
                    
                    // Weapon-specific validation complete
                    
                    if (canAttack) {
                        return createPathResult(moveToCell, pathToTarget, 0, targetPosition.weapon, false, min(myMP, count(pathToTarget) - 1), false);
                    } else if (debugEnabled) {
                        // Position rejected - not in attack range
                    }
                }
            }
        }
        
        // Fallback: Move toward enemy when no smart position found
        if (debugEnabled) {
            // Fallback - moving toward enemy
        }

        var pathToEnemy = aStar(currentCell, enemyCell, myMP * 4); // Allow longer search for distant enemies
        if (pathToEnemy != null && count(pathToEnemy) > 1) {
            var stepsToTake = min(myMP, count(pathToEnemy) - 1);
            var moveToCell = pathToEnemy[stepsToTake];

            // Create path with only the steps we can take
            var actualPath = [];
            for (var step = 0; step <= stepsToTake; step++) {
                push(actualPath, pathToEnemy[step]);
            }

            // Moving toward enemy as fallback

            return createPathResult(moveToCell, actualPath, 0, null, false, stepsToTake, false);
        }
    }
    
    // Check if we should use teleportation for strategic positioning
    var currentHPPercent = getLife() / getTotalLife();
    var shouldUseTeleport = false;
    
    // Trigger teleportation if:
    // 1. HP < 40% (late-game threshold)
    // 2. No high-damage paths were found by movement
    // 3. We have high-damage cells that are only reachable by teleport
    if (currentHPPercent < 0.4 && maxDamage > 0) {
        shouldUseTeleport = true;
        // Late-game teleportation triggered
    } else if (maxDamage == 0 && count(damageArray) > 0) {
        // No movement paths found, but damage zones exist - try teleport
        shouldUseTeleport = true;
        // Strategic teleportation for positioning
    }
    
    // Last resort: Try teleport + movement fallback (or forced teleport for late-game)
    if (shouldUseTeleport || maxDamage == 0) {
        // Pathfinding fallback with teleportation
        
        var teleportResult = tryTeleportMovementFallback(currentCell, damageArray);
        if (teleportResult != null) {
            return teleportResult;
        }
    }
    
    // ABSOLUTE FALLBACK: Use simple directional movement if everything else fails
    // Absolute fallback - simple movement toward enemy

    if (enemyCell != null) {
        var simpleMovePath = findMultiStepMovementToward(currentCell, enemyCell, myMP);
        if (simpleMovePath != null && count(simpleMovePath) > 1) {
            // Simple movement path found
            return createPathResult(
                simpleMovePath[count(simpleMovePath) - 1], // Final position
                simpleMovePath,                            // Path
                0,                                         // No immediate damage
                null,                                      // No specific weapon
                false,                                     // Not immediately reachable
                count(simpleMovePath) - 1,                 // Distance moved
                false                                      // No teleport
            );
        }
    }

    // Return null if no path found
    return null;
}

// === DUAL-MAP PATHFINDING (WEAPON-FIRST, THEN CHIPS) ===
function findOptimalPathFromDualArrays(currentCell, weaponArray, chipArray) {
    // 1) Try weapon vantages first (full scan up to cap)
    var localCap = terrainLOSDone ? MAX_PATHFIND_CELLS : 8;
    var weaponSorted = sortArrayByDamage(weaponArray);
    for (var i = 0; i < min(localCap, count(weaponSorted)); i++) {
        var w = weaponSorted[i];
        if (w == null) continue;
        var tCell = w[0];
        var dmg = w[1];
        var wid = (count(w) > 2) ? w[2] : null;
        if (wid == null || !isWeapon(wid)) continue;
        var p = aStar(currentCell, tCell, myMP);
        if (p != null && count(p) <= myMP + 1) {
            return createPathResult(tCell, p, dmg, wid, true, count(p) - 1, false);
        }
    }
    // 2) Greedy fallback: any reachable weapon vantage within MP by distance
    var wLimit = terrainLOSDone ? count(weaponArray) : min(12, count(weaponArray));
    for (var j = 0; j < wLimit; j++) {
        var we = weaponArray[j];
        if (we == null) continue;
        var wc = we[0];
        var ww = (count(we) > 2) ? we[2] : null;
        if (ww == null || !isWeapon(ww)) continue;
        if (getCellDistance(currentCell, wc) <= myMP) {
            var p2 = aStar(currentCell, wc, myMP);
            if (p2 != null && count(p2) > 1) {
                return createPathResult(wc, p2, we[1], ww, true, count(p2) - 1, false);
            }
        }
    }
    // 2a) Search within MP for a strong weapon vantage (multi-step), prefer FLAME/DESTROYER
    if (isMagicBuild && primaryTarget != null) {
        var tgtCell = getCell(primaryTarget);
        if (tgtCell != null) {
            var bestVCell = null;
            var bestVPath = null;
            var bestVScore = -99999;
            // DESTROYER band 1..6
            for (var d = 1; d <= 6; d++) {
                var ring = getCellsAtExactDistance(tgtCell, d);
                var stride = max(1, floor(count(ring) / (terrainLOSDone ? 20 : 36)));
                for (var r = 0; r < count(ring); r += stride) {
                    var c = ring[r];
                    if (c == null || getCellContent(c) != CELL_EMPTY) continue;
                    if (!checkLineOfSight(c, tgtCell)) continue;
                    var pathD = aStar(currentCell, c, myMP);
                    if (pathD == null || count(pathD) <= 1) continue;
                    var pathLen = count(pathD) - 1;
                    if (pathLen > myMP) continue;
                    // Score: prefer shorter path, lower EID, and LoS
                    var eid = estimateIncomingDamageAtCell(c);
                    var score = 300 - pathLen * 10 - eid;
                    if (score > bestVScore) { bestVScore = score; bestVCell = c; bestVPath = pathD; }
                }
            }
            // FLAME band 2..8 (aligned & LoS)
            for (var d2 = 2; d2 <= 8; d2++) {
                var ring2 = getCellsAtExactDistance(tgtCell, d2);
                var stride2 = max(1, floor(count(ring2) / (terrainLOSDone ? 20 : 36)));
                for (var r2 = 0; r2 < count(ring2); r2 += stride2) {
                    var c2 = ring2[r2];
                    if (c2 == null || getCellContent(c2) != CELL_EMPTY) continue;
                    if (!isOnSameLine(c2, tgtCell)) continue;
                    if (!checkLineOfSight(c2, tgtCell)) continue;
                    var pathF = aStar(currentCell, c2, myMP);
                    if (pathF == null || count(pathF) <= 1) continue;
                    var lenF = count(pathF) - 1;
                    if (lenF > myMP) continue;
                    // Combo-aware score: TOXIN safe boost, else VENOM boost
                    var eidF = estimateIncomingDamageAtCell(c2);
                    var scoreF = 290 - lenF * 10 - eidF;
                    var chips = getChips();
                    var dist = getCellDistance(c2, tgtCell);
                    if (inArray(chips, CHIP_TOXIN)) {
                        var area = getChipArea(CHIP_TOXIN);
                        var minR = getChipMinRange(CHIP_TOXIN);
                        var maxR = getChipMaxRange(CHIP_TOXIN);
                        if (dist >= minR && dist <= maxR && dist > area) scoreF += 80;
                    } else if (inArray(chips, CHIP_VENOM)) {
                        var vmin = getChipMinRange(CHIP_VENOM);
                        var vmax = getChipMaxRange(CHIP_VENOM);
                        if (dist >= vmin && dist <= vmax) scoreF += 50;
                    }
                    if (scoreF > bestVScore) { bestVScore = scoreF; bestVCell = c2; bestVPath = pathF; }
                }
            }
            if (bestVPath != null) {
                // Prefer DESTROYER if selected from 1..6 band else FLAME
                var wsel = null;
                var distSel = getCellDistance(bestVCell, tgtCell);
                if (distSel >= 1 && distSel <= 6) wsel = WEAPON_DESTROYER; else wsel = WEAPON_FLAME_THROWER;
                return createPathResult(bestVCell, bestVPath, 0, wsel, true, count(bestVPath) - 1, false);
            }
        }
    }

    // 2b) Last-mile weapon alignment before chips (prefer weapon over chip when 1 MP away)
    if (isMagicBuild && primaryTarget != null) {
        var tgtCellLM = getCell(primaryTarget);
        if (tgtCellLM != null) {
            var distBand = getCellDistance(currentCell, tgtCellLM);
            // FLAME: align in 6–8 band if misaligned
            if (inArray(getWeapons(), WEAPON_FLAME_THROWER) && distBand >= 6 && distBand <= 8 && !isOnSameLine(currentCell, tgtCellLM)) {
                var neigh = getWalkableNeighbors(currentCell);
                var bestAlign = null;
                var bestScore = -9999;
                for (var ni = 0; ni < count(neigh); ni++) {
                    var n = neigh[ni];
                    if (getCellContent(n) != CELL_EMPTY) continue;
                    var d = getCellDistance(n, tgtCellLM);
                    if (d < 2 || d > 8) continue; // FLAME range
                    if (!isOnSameLine(n, tgtCellLM)) continue;
                        if (!checkLineOfSight(n, tgtCellLM)) continue;
                    var eid = estimateIncomingDamageAtCell(n);
                    var score = 200 - eid;
                    if (score > bestScore) { bestScore = score; bestAlign = n; }
                }
                if (bestAlign != null) {
                    var pathAlign = [currentCell, bestAlign];
                    return createPathResult(bestAlign, pathAlign, 0, WEAPON_FLAME_THROWER, true, 1, false);
                }
                // Fallback: if no aligned+LoS neighbor, nudge toward alignment within FLAME band
                var bestNudge = null;
                var bestNudgeScore = -9999;
                var curDX = getCellX(tgtCellLM) - getCellX(currentCell);
                var curDY = getCellY(tgtCellLM) - getCellY(currentCell);
                for (var ni2 = 0; ni2 < count(neigh); ni2++) {
                    var n3 = neigh[ni2];
                    if (getCellContent(n3) != CELL_EMPTY) continue;
                    var d3 = getCellDistance(n3, tgtCellLM);
                    if (d3 < 2 || d3 > 8) continue; // keep in band
                    var ndx = getCellX(tgtCellLM) - getCellX(n3);
                    var ndy = getCellY(tgtCellLM) - getCellY(n3);
                    // Score how much this step reduces misalignment (minimize min(|dx|,|dy|) then EID)
                    var misBefore = min(abs(curDX), abs(curDY));
                    var misAfter = min(abs(ndx), abs(ndy));
                    var improve = misBefore - misAfter;
                    if (improve <= 0) continue;
                    var eid3 = estimateIncomingDamageAtCell(n3);
                    var s3 = improve * 100 - eid3;
                    if (s3 > bestNudgeScore) { bestNudgeScore = s3; bestNudge = n3; }
                }
                if (bestNudge != null) {
                    var pathN = [currentCell, bestNudge];
                    return createPathResult(bestNudge, pathN, 0, WEAPON_FLAME_THROWER, true, 1, false);
                }
            }
            // DESTROYER: step into 1–6 with LoS or fix LoS within 1 MP
            if (inArray(getWeapons(), WEAPON_DESTROYER)) {
                var needCloser = (distBand == 7);
            var needLoSFix = (distBand >= 1 && distBand <= 6 && !checkLineOfSight(currentCell, tgtCellLM));
                if (needCloser || needLoSFix) {
                    var neighD = getWalkableNeighbors(currentCell);
                    var bestD = null;
                    var bestDScore = -9999;
                    for (var di = 0; di < count(neighD); di++) {
                        var n2 = neighD[di];
                        if (getCellContent(n2) != CELL_EMPTY) continue;
                        var d2 = getCellDistance(n2, tgtCellLM);
                        if (d2 < 1 || d2 > 6) continue;
                        if (!checkLineOfSight(n2, tgtCellLM)) continue;
                        var eid2 = estimateIncomingDamageAtCell(n2);
                        var score2 = 220 - eid2;
                        if (score2 > bestDScore) { bestDScore = score2; bestD = n2; }
                    }
                    if (bestD != null) {
                        var pathD = [currentCell, bestD];
                        return createPathResult(bestD, pathD, 0, WEAPON_DESTROYER, true, 1, false);
                    }
                }
            }
        }
    }
    // 3) Try chip vantages (carry chip id so combat can use it)
    var chipSorted = sortChipArrayByDamage(chipArray);
    for (var k = 0; k < min(localCap, count(chipSorted)); k++) {
        var c = chipSorted[k];
        if (c == null) continue;
        var cc = c[0];
        var cdmg = c[1];
        var cid = (count(c) > 2) ? c[2] : null;
        if (cid == null || cid < CHIP_LIGHTNING) continue;
        var cp = aStar(currentCell, cc, myMP);
        if (cp != null && count(cp) <= myMP + 1) {
            return createPathResult(cc, cp, cdmg, cid, true, count(cp) - 1, false);
        }
    }
    // 4) Existing greedy band-chasing logic for MAGIC and generic fallbacks
    return findOptimalPathFromArray(currentCell, currentDamageArray);
}

// Simple sort by damage (desc) for chip arrays
function sortChipArrayByDamage(arr) {
    var a2 = [];
    for (var i = 0; i < count(arr); i++) {
        var e = arr[i];
        if (e == null || count(e) < 2) continue;
        var cellId = e[0];
        var dmg = e[1];
        if (cellId >= 0 && cellId <= 612 && dmg > 0) {
            push(a2, [cellId, dmg, (count(e) > 2) ? e[2] : null, (count(e) > 3) ? e[3] : null]);
        }
    }
    // selection sort by damage desc
    for (var i = 0; i < count(a2) - 1; i++) {
        var maxIdx = i;
        for (var j = i + 1; j < count(a2); j++) {
            if (a2[j][1] > a2[maxIdx][1]) { maxIdx = j; }
        }
        if (maxIdx != i) {
            var tmp = a2[i]; a2[i] = a2[maxIdx]; a2[maxIdx] = tmp;
        }
    }
    return a2;
}

// === ARRAY SORTING FUNCTION ===
function sortArrayByDamage(damageArray) {
    // Sorting damage array by priority
    
    // Make a copy to avoid modifying original array
    var sortedArray = [];
    for (var i = 0; i < count(damageArray); i++) {
        var entry = damageArray[i];
        var cellId = entry[0];
        var damage = entry[1];
        var weaponId = (count(entry) > 2) ? entry[2] : null; // Preserve weapon ID
        var enemyEntity = (count(entry) > 3) ? entry[3] : null; // NEW: Preserve enemy association
        
        // Validate cell and damage
        if (cellId >= 0 && cellId <= 612 && damage > 0) {
            // Enhanced format: [cellId, damage, weaponId, enemyEntity]
            push(sortedArray, [cellId, damage, weaponId, enemyEntity]);
        } else if (debugEnabled && i < 3) {
            // Rejecting invalid cell
        }
    }
    
    // Sort by damage AND weapon priority (highest first) - optimized for small arrays
    var arraySize = count(sortedArray);
    if (arraySize > 50) {
        // If array too large, take top entries and skip full sort
        var topEntries = [];
        var maxEntries = 20; // Limit to top 20 entries
        
        for (var k = 0; k < min(maxEntries, arraySize); k++) {
            var maxIndex = k;
            var maxScore = getWeaponSortScore(sortedArray[k]);
            
            // Find max in remaining elements
            for (var m = k + 1; m < arraySize; m++) {
                var score = getWeaponSortScore(sortedArray[m]);
                if (score > maxScore) {
                    maxIndex = m;
                    maxScore = score;
                }
            }
            
            // Swap if needed
            if (maxIndex != k) {
                var temp = sortedArray[k];
                sortedArray[k] = sortedArray[maxIndex];
                sortedArray[maxIndex] = temp;
            }
        }
        
        // Truncate to top entries only
        var truncated = [];
        for (var t = 0; t < min(maxEntries, arraySize); t++) {
            push(truncated, sortedArray[t]);
        }
        sortedArray = truncated;
    } else {
        // Use simple selection sort for small arrays with weapon prioritization
        for (var i = 0; i < arraySize - 1; i++) {
            var maxIndex = i;
            var maxScore = getWeaponSortScore(sortedArray[i]);
            for (var j = i + 1; j < arraySize; j++) {
                var score = getWeaponSortScore(sortedArray[j]);
                if (score > maxScore) {
                    maxIndex = j;
                    maxScore = score;
                }
            }
            if (maxIndex != i) {
                var temp = sortedArray[i];
                sortedArray[i] = sortedArray[maxIndex];
                sortedArray[maxIndex] = temp;
            }
        }
    }
    
    // Array sorting complete
    
    return sortedArray;
}

// === MAIN PATHFINDING FUNCTION (MAP-BASED - LEGACY) ===
function findOptimalPath(currentCell, damageZones) {
    // Sort cells by damage potential (highest first)
    var sortedCells = sortCellsByDamage(damageZones);
    
    // Try A* to each high-damage cell until we find a reachable one
    for (var i = 0; i < min(MAX_PATHFIND_CELLS, count(sortedCells)); i++) {
        var targetData = sortedCells[i];
        var targetCell = targetData[0];
        var expectedDamage = targetData[1];
        var weaponId = (count(targetData) > 2) ? targetData[2] : null;
        
        var path = aStar(currentCell, targetCell, myMP);
        
        if (path != null && count(path) <= myMP + 1) {
            // Mark chosen path in bright orange
            // TEMPORARILY DISABLED: Testing if mark() corrupts the map
            // Path found and marked
            
            return createPathResult(targetCell, path, expectedDamage, weaponId, true, count(path) - 1, false);
        }
    }
    
    // No high-damage cell reachable - check if all damage zones are 0
    var maxDamage = 0;
    for (var cell in damageZones) {
        var damage = damageZones[cell] + 0; // Convert to number
        if (damage > maxDamage) {
            maxDamage = damage;
        }
    }
    
    // If all damage is 0, move toward enemy to get in weapon range
    // Pathfinding damage analysis complete
    if (maxDamage == 0) {
        // Moving toward enemy
        var moveTowardEnemy = aStar(currentCell, enemyCell, myMP);
        if (moveTowardEnemy != null && count(moveTowardEnemy) > 1) {
            var moveToCell = moveTowardEnemy[min(myMP, count(moveTowardEnemy) - 1)];
            
            if (debugEnabled) {
                // Moving toward enemy - no damage zones
            }
            
            return createPathResult(moveToCell, arraySlice(moveTowardEnemy, 0, min(myMP + 1, count(moveTowardEnemy))), 0, null, false, min(myMP, count(moveTowardEnemy) - 1), false);
        } else {
            // A* failed, try simple directional movement
            var simplePath = findMultiStepMovementToward(currentCell, enemyCell, myMP);
            if (simplePath != null && count(simplePath) > 1) {
                return createPathResult(simplePath[count(simplePath) - 1], simplePath, 0, null, false, count(simplePath) - 1, false);
            }
        }
    }
    
    // Move toward best damage zone (even if 0)
    if (count(sortedCells) > 0) {
        var bestCell = sortedCells[0][0];
        var bestDamage = sortedCells[0][1];
        var bestWeapon = (count(sortedCells[0]) > 2) ? sortedCells[0][2] : null;
        var partialPath = aStar(currentCell, bestCell, myMP);
        
        if (partialPath != null && count(partialPath) > 1) {
            var moveToCell = partialPath[min(myMP + 1, count(partialPath) - 1)];
            return createPathResult(moveToCell, arraySlice(partialPath, 0, min(myMP + 1, count(partialPath))), bestDamage, bestWeapon, false, min(myMP, count(partialPath) - 1), false);
        }
    }
    
    // Fallback: stay in place
    return createPathResult(currentCell, [currentCell], (damageZones[currentCell] + 0) || 0, null, true, 0, false);
}

// === CELL SORTING BY DAMAGE ===
function sortCellsByDamage(damageZones) {
    var cellArray = [];
    
    for (var cell in damageZones) {
        // Use cell ID directly
        var cellId = cell + 0;  // Convert to number
        if (cellId != null && !isNaN(cellId) && cellId >= 0 && cellId <= 612) {
            var damage = damageZones[cell] + 0; // Convert damage to number
            push(cellArray, [cellId, damage]);
        }
    }
    
    // Cell array prepared for sorting
    
    // Sort by damage (highest first) - manual bubble sort
    for (var i = 0; i < count(cellArray) - 1; i++) {
        for (var j = 0; j < count(cellArray) - 1 - i; j++) {
            if (cellArray[j][1] < cellArray[j + 1][1]) {
                var temp = cellArray[j];
                cellArray[j] = cellArray[j + 1];
                cellArray[j + 1] = temp;
            }
        }
    }
    
    return cellArray;
}

// === A* PATHFINDING IMPLEMENTATION ===
function aStar(startCell, goalCell, maxDistance) {
    // Check cache first
    var cacheKey = startCell + "_" + goalCell + "_" + maxDistance;
    if (pathCache[cacheKey] != null) {
        return pathCache[cacheKey];
    }

    // Enforce per-turn A* call budget
    var budget = terrainLOSDone ? PATH_ASTAR_BUDGET_DEFAULT : PATH_ASTAR_BUDGET_DURING_LOS;
    if (aStarCallsThisTurn >= budget) {
        return null;
    }
    aStarCallsThisTurn++;
    
    
    var openSet = [startCell];
    var cameFrom = [:];
    var gScore = [:];
    var fScore = [:];
    
    gScore[startCell] = 0;
    fScore[startCell] = heuristic(startCell, goalCell);
    
    var searchCount = 0;
    // Tighten search while LOS precompute is in progress
    var maxSearchSteps = terrainLOSDone ? 300 : 200;
    
    while (count(openSet) > 0 && searchCount < maxSearchSteps) {
        searchCount++;
        // Find node with lowest fScore
        var current = openSet[0];
        var currentIndex = 0;
        for (var i = 1; i < count(openSet); i++) {
            if (fScore[openSet[i]] < fScore[current]) {
                current = openSet[i];
                currentIndex = i;
            }
        }
        
        // Remove current from openSet
        // Remove current from openSet by shifting elements
        for (var k = currentIndex; k < count(openSet) - 1; k++) {
            openSet[k] = openSet[k + 1];
        }
        // Remove last element
        var newOpenSet = [];
        for (var m = 0; m < count(openSet) - 1; m++) {
            push(newOpenSet, openSet[m]);
        }
        openSet = newOpenSet;
        
        // Goal reached
        if (current == goalCell) {
            var path = reconstructPath(cameFrom, current);
            pathCache[cacheKey] = path;
            return path;
        }
        
        // Don't search beyond max distance (AFTER goal check)
        if (gScore[current] > maxDistance) continue;
        
        // Check neighbors
        var neighbors = getWalkableNeighbors(current);
        for (var i = 0; i < count(neighbors); i++) {
            var neighbor = neighbors[i];
            var tentativeGScore = gScore[current] + 1;
            
            if (gScore[neighbor] == null || tentativeGScore < gScore[neighbor]) {
                cameFrom[neighbor] = current;
                gScore[neighbor] = tentativeGScore;
                fScore[neighbor] = gScore[neighbor] + heuristic(neighbor, goalCell);
                
                if (!inArray(openSet, neighbor)) {
                    push(openSet, neighbor);
                }
            }
        }
    }
    
    // No path found
    pathCache[cacheKey] = null;
    return null;
}

// === M-LASER ALIGNMENT SEEKING ===
function findMLaserAlignmentPosition() {
    // Find the best position to align M-Laser with enemy
    var enemyX = getCellX(enemyCell);
    var enemyY = getCellY(enemyCell);
    var myX = getCellX(myCell);
    var myY = getCellY(myCell);
    
    var bestTarget = null;
    var bestScore = 0;
    
    if (debugEnabled) {
        // M-Laser alignment search
    }
    
    // Check cells on same X axis as enemy (vertical line)
    for (var y = enemyY - 10; y <= enemyY + 10; y++) {
        var cell = getCellFromXY(enemyX, y);
        if (cell != null && cell != -1 && cell != enemyCell) {
            var score = evaluateMLaserPosition(cell);
            if (score > bestScore) {
                bestScore = score;
                bestTarget = cell;
                if (debugEnabled) {
                    // M-Laser vertical alignment checked
                }
            }
        }
    }
    
    // Check cells on same Y axis as enemy (horizontal line)
    for (var x = enemyX - 10; x <= enemyX + 10; x++) {
        var cell = getCellFromXY(x, enemyY);
        if (cell != null && cell != -1 && cell != enemyCell) {
            var score = evaluateMLaserPosition(cell);
            if (score > bestScore) {
                bestScore = score;
                bestTarget = cell;
                if (debugEnabled) {
                    // M-Laser horizontal alignment checked
                }
            }
        }
    }
    
    if (bestTarget != null && debugEnabled) {
        // Best M-Laser position found
        markText(bestTarget, "M-LASER", getColor(255, 255, 0), 8);
    }
    
    return bestTarget;
}

function evaluateMLaserPosition(cell) {
    var distance = getCellDistance(cell, enemyCell);
    
    // Must be in M-Laser range (6-10)
    if (distance < 6 || distance > 10) return 0;
    
    // Must be walkable
    var isWalkable = (getCellContent(cell) == CELL_EMPTY);
    if (!isWalkable) return 0;
    
    // Must have LOS to enemy
    if (!checkLineOfSight(cell, enemyCell)) return 0;
    
    var score = 0;
    
    // Base score: favor optimal range (7-9 for M-Laser)
    if (distance >= 7 && distance <= 9) {
        score += 50; // Optimal range bonus
    } else {
        score += 20; // Still in range bonus
    }
    
    // Reachability bonus (closer to current position is better)
    var reachability = max(0, 15 - getCellDistance(myCell, cell));
    score += reachability;
    
    // Cover bonus - check adjacent cells for obstacles
    var coverBonus = 0;
    var adjacentCells = getCellsAtExactDistance(cell, 1);
    for (var i = 0; i < count(adjacentCells); i++) {
        var adjCell = adjacentCells[i];
        if (getCellContent(adjCell) == CELL_OBSTACLE) {
            coverBonus += 2; // Small bonus for each adjacent obstacle
        }
    }
    score += min(coverBonus, 8); // Cap cover bonus at 8
    
    // MAGIC BUILD HIDE-AND-SEEK BONUSES
    if (isMagicBuild && count(allEnemies) > 0) {
        // Enhanced cover bonus for magic builds (hit-and-run tactics)
        score += min(coverBonus * 2, 15); // Double cover bonus for magic builds
        
        // Escape route bonus - prefer positions with multiple movement options
        var escapeRoutes = 0;
        var escapeDistance = 3; // Check 3 cells in each direction for escape routes
        var directions = [
            [-1, 0], [1, 0], [0, -1], [0, 1],  // Cardinal directions
            [-1, -1], [-1, 1], [1, -1], [1, 1] // Diagonal directions
        ];
        
        for (var d = 0; d < count(directions); d++) {
            var dx = directions[d][0];
            var dy = directions[d][1];
            var routeOpen = true;
            
            for (var step = 1; step <= escapeDistance; step++) {
                var escapeCell = cell + (dx * step) + (dy * step * MAP_WIDTH);
                if (getCellContent(escapeCell) != CELL_EMPTY) {
                    routeOpen = false;
                    break;
                }
            }
            
            if (routeOpen) {
                escapeRoutes++;
            }
        }
        
        // Bonus for having multiple escape routes (max 8 directions)
        var escapeBonus = min(escapeRoutes * 2, 16); // Max 16 points for escape routes
        score += escapeBonus;
        
        // Line of sight penalty for magic builds - prefer positions where enemies can't see you
        var losBlockedFromEnemies = 0;
        for (var e = 0; e < count(allEnemies); e++) {
            var targetEnemyCell = getCell(allEnemies[e]);
            if (!checkLineOfSight(cell, targetEnemyCell)) {
                losBlockedFromEnemies++;
            }
        }
        
        // Bonus for breaking line of sight with enemies
        var stealthBonus = losBlockedFromEnemies * 10; // 10 points per enemy we can hide from
        score += stealthBonus;
        
        if (debugEnabled && stealthBonus > 0) {
            // Magic stealth bonus applied
        }
    }
    
    // Penalty for being on same line as current position (avoids minimal movement)
    if (isOnSameLine(myCell, cell)) {
        score -= 5;
    }
    
    return score;
}

// === PATHFINDING UTILITIES ===
function heuristic(cellA, cellB) {
    // Manhattan distance heuristic
    return getCellDistance(cellA, cellB);
}

function reconstructPath(cameFrom, current) {
    var path = [current];
    
    while (cameFrom[current] != null) {
        current = cameFrom[current];
        unshift(path, current);
    }
    
    return path;
}

function getWalkableNeighbors(cell) {
    var neighbors = [];
    var x = getCellX(cell);
    var y = getCellY(cell);
    
    var directions = [
        [0, 1], [0, -1], [1, 0], [-1, 0]  // North, South, East, West
    ];
    
    for (var i = 0; i < count(directions); i++) {
        var dir = directions[i];
        var neighborCell = getCellFromXY(x + dir[0], y + dir[1]);
        
        // Enhanced walkability checks with debugging
        if (neighborCell != null && neighborCell != -1 && neighborCell >= 0 && neighborCell <= 612) {
            // Check if cell is empty and not an obstacle
            var isEmpty = isEmptyCell(neighborCell);
            var isObst = isObstacle(neighborCell);
            
            
            // Simplified walkability check: only use isEmpty
            if (isEmpty) {
                push(neighbors, neighborCell);
            }
        }
    }
    
    return neighbors;
}

// === MAGIC VANTAGE SEEKING (FLAME/DESTROYER/CHEMS) ===
function findMagicApproachPath(currentCell, targetCell) {
    // Build a small set of candidate vantages around the enemy for:
    // - FLAME_THROWER: 2..8 with LoS
    // - DESTROYER: 1..6 with LoS
    // Score also prefers distances safe for TOXIN (outside chip area).

    var bestReachable = null;
    var bestReachScore = -99999;
    var bestReachPath = null;
    var bestReachWeapon = null;

    var bestStep = null; // best overall candidate to step toward
    var bestStepScore = -99999;
    var toxinArea = getChipArea(CHIP_TOXIN);
    if (toxinArea == null) toxinArea = 4;

    // (No nested functions allowed in LeekScript) – compute score inline

    // Sample FLAME ring 2..8 and DESTROYER ring 1..6
    var rings = [];
    for (var d = 2; d <= 8; d++) { push(rings, d); }
    for (var d = 1; d <= 6; d++) { push(rings, d); }

    // Limit ops with stride
    for (var ri = 0; ri < count(rings); ri++) {
        var d = rings[ri];
        var ring = getCellsAtExactDistance(targetCell, d);
        var stride = max(1, floor(count(ring) / 18));
        for (var i = 0; i < count(ring); i += stride) {
            var c = ring[i];
            if (c == null || c < 0 || c > 612) continue;
            if (getCellContent(c) != CELL_EMPTY) continue;
            if (!checkLineOfSight(c, targetCell)) continue;
            var s = 0;
            if (d >= 2 && d <= 8) s += 1000; // FLAME range
            if (d >= 1 && d <= 6) s += 400;  // DESTROYER range
            if (d > toxinArea) s += 300; else s -= 500; // TOXIN safety
            s += max(0, 10 - abs(6 - d)) * 10; // prefer mid-distance within band
            // If reachable within MP this turn, check A*
            if (getCellDistance(currentCell, c) <= myMP) {
                var p = aStar(currentCell, c, myMP);
                if (p != null && count(p) <= myMP + 1) {
                    if (s > bestReachScore) {
                        bestReachScore = s;
                        bestReachPath = p;
                        bestReachable = c;
                        // Decide weapon to recommend from this vantage
                        bestReachWeapon = (d >= 2 && d <= 8) ? WEAPON_FLAME_THROWER : ((d >= 1 && d <= 6) ? WEAPON_DESTROYER : null);
                    }
                }
            }
            // Track best step-to candidate (even if not reachable fully)
            if (s > bestStepScore) { bestStepScore = s; bestStep = c; }
        }
    }

    if (bestReachable != null && bestReachPath != null) {
        // Found a reachable vantage this turn
        return createPathResult(bestReachable, bestReachPath, 0, bestReachWeapon, true, count(bestReachPath) - 1, false);
    }

    // Otherwise, step toward best vantage
    if (bestStep != null) {
        var pathTo = aStar(currentCell, bestStep, myMP * 3);
        if (pathTo != null && count(pathTo) > 1) {
            var steps = min(myMP, count(pathTo) - 1);
            var moveTo = pathTo[steps];
            var actual = [];
            for (var s = 0; s <= steps; s++) { push(actual, pathTo[s]); }
            return createPathResult(moveTo, actual, 0, null, steps <= myMP, steps, false);
        }
    }

    return null;
}

// === SIMPLE MOVEMENT (FALLBACK) ===
function findMultiStepMovementToward(fromCell, toCell, maxMP) {
    var path = [fromCell];
    var currentCell = fromCell;
    
    for (var step = 0; step < maxMP; step++) {
        var nextCell = findSimpleMovementToward(currentCell, toCell, 1);
        if (nextCell == null || nextCell == currentCell) {
            if (debugEnabled) {
                // Multi-step blocked, trying alternative
            }
            // Try alternative directions if blocked
            nextCell = findAlternativeMovement(currentCell, toCell);
            if (nextCell == null || nextCell == currentCell) {
                break; // Really can't move further
            }
        }
        push(path, nextCell);
        currentCell = nextCell;
        
        // Stop if we've reached the target
        if (currentCell == toCell) {
            break;
        }
    }
    
    if (debugEnabled) {
        // Multi-step path created
    }
    
    return (count(path) > 1) ? path : null;
}

function findSimpleMovementToward(fromCell, toCell, maxMP) {
    var fromX = getCellX(fromCell);
    var fromY = getCellY(fromCell);
    var toX = getCellX(toCell);
    var toY = getCellY(toCell);
    
    if (debugEnabled) {
        // Simple directional movement
    }
    
    // Try moving directly toward enemy
    var deltaX = toX - fromX;
    var deltaY = toY - fromY;
    
    // Normalize to get direction
    var dirX = (deltaX > 0) ? 1 : ((deltaX < 0) ? -1 : 0);
    var dirY = (deltaY > 0) ? 1 : ((deltaY < 0) ? -1 : 0);
    
    // Try the direction with the largest delta first (greedy approach)
    var tryX = (abs(deltaX) >= abs(deltaY));
    
    if (tryX && dirX != 0) {
        var targetCell = getCellFromXY(fromX + dirX, fromY);
        if (targetCell != null && targetCell != -1) {
            if (debugEnabled) {
                // Moving in X direction
            }
            return targetCell;
        }
    }
    
    if (!tryX && dirY != 0) {
        var targetCell = getCellFromXY(fromX, fromY + dirY);
        if (targetCell != null && targetCell != -1) {
            if (debugEnabled) {
                // Moving in Y direction
            }
            return targetCell;
        }
    }
    
    // Try the other direction if first choice failed
    if (tryX && dirY != 0) {
        var targetCell = getCellFromXY(fromX, fromY + dirY);
        if (targetCell != null && targetCell != -1) {
            if (debugEnabled) {
                // Moving in Y direction (fallback)
            }
            return targetCell;
        }
    }
    
    if (!tryX && dirX != 0) {
        var targetCell = getCellFromXY(fromX + dirX, fromY);
        if (targetCell != null && targetCell != -1) {
            if (debugEnabled) {
                // Moving in X direction (fallback)
            }
            return targetCell;
        }
    }
    
    if (debugEnabled) {
        // No valid movement directions found
    }
    return null;
}

// === MOVEMENT EXECUTION ===
function executeMovement(pathResult) {
    if (pathResult == null) {
        return; // No movement needed
    }
    
    // Handle teleport + movement combo  
    if (pathResult[6]) { // pathResult[6] = useTeleport
        if (debugEnabled) {
            // Executing teleportation
        }
        
        var chips = getChips();
        if (inArray(chips, CHIP_TELEPORTATION) && canUseChip(CHIP_TELEPORTATION, pathResult[0])) {
            useChip(CHIP_TELEPORTATION, pathResult[0]);
            
            // Update position after teleport
            myCell = getCell();
            myMP = getMP(); // MP should be unchanged after teleport
            
            if (debugEnabled) {
                // Teleport successful
            }
            // After teleport, perform post-teleport movement along provided path if any
            if (pathResult[1] != null && count(pathResult[1]) > 1) {
                executeNormalMovement(pathResult);
            }
        } else {
            if (debugEnabled) {
                // Teleport failed
            }
        }
        return;
    }
    
    // Normal movement execution
    executeNormalMovement(pathResult);
}

function executeNormalMovement(pathResult) {
    if (pathResult == null || pathResult[1] == null || count(pathResult[1]) <= 1) {
        return; // No movement needed
    }
    
    var path = pathResult[1]; // pathResult[1] = path
    var mpRemaining = myMP;
    
    // Execute movement along path
    for (var i = 1; i < count(path) && mpRemaining > 0; i++) {
        var targetCell = path[i];
        
        var mpUsed = moveTowardCells([targetCell], 1);
        if (mpUsed > 0) {
            mpRemaining -= mpUsed;
            if (debugEnabled) {
                // Movement completed
            }
        } else {
            if (debugEnabled) {
                // Movement blocked, trying alternative
            }
            // Try alternative movement when blocked
            var currentPos = getCell();
            var alternative = findAlternativeMovement(currentPos, targetCell);
            if (alternative != null) {
                var altMpUsed = moveTowardCells([alternative], 1);
                if (altMpUsed > 0) {
                    mpRemaining -= altMpUsed;
                    if (debugEnabled) {
                        // Alternative movement completed
                    }
                } else {
                    if (debugEnabled) {
                        // Alternative movement blocked
                    }
                    break;
                }
            } else {
                break;
            }
        }
    }
    
    // Update global state after movement
    myCell = getCell();
    myMP = getMP();
}

// === TELEPORTATION SUPPORT ===
function considerTeleportation(damageZones) {
    if (!canUseChip(CHIP_TELEPORTATION, getEntity())) return null;
    
    // Find best teleport target within range
    var teleportRange = 12;
    var bestCell = null;
    var bestDamage = 0;
    
    for (var cell in damageZones) {
        var cellId = cell + 0; // Convert to number
        var distance = getCellDistance(myCell, cellId);
        var damage = damageZones[cell] + 0; // Convert to number
        if (distance <= teleportRange && damage > bestDamage) {
            bestDamage = damage;
            bestCell = cellId;
        }
    }
    
    var currentDamage = (damageZones[myCell] != null) ? (damageZones[myCell] + 0) : 0;
    if (bestCell != null && bestDamage > currentDamage * 1.5) {
        return {
            targetCell: bestCell,
            damage: bestDamage,
            cost: getChipCost(CHIP_TELEPORTATION)
        };
    }
    
    return null;
}

function findAlternativeMovement(fromCell, toCell) {
    var fromX = getCellX(fromCell);
    var fromY = getCellY(fromCell);
    var toX = getCellX(toCell);
    var toY = getCellY(toCell);
    
    // Try different movement priorities when primary direction is blocked
    var directions = [
        [1, 0], [-1, 0], [0, 1], [0, -1],  // Cardinal directions
        [1, 1], [1, -1], [-1, 1], [-1, -1]  // Diagonal directions
    ];
    
    // Find any valid alternative that's NOT the blocked target
    for (var i = 0; i < count(directions); i++) {
        var dir = directions[i];
        var testX = fromX + dir[0];
        var testY = fromY + dir[1];
        var testCell = getCellFromXY(testX, testY);
        
        // Skip if invalid cell or same as blocked target
        if (testCell == null || testCell == -1 || testCell < 0 || testCell > 612 || testCell == toCell) {
            continue;
        }
        
        if (debugEnabled) {
            // Trying alternative direction
        }
        
        return testCell; // Return first valid alternative
    }
    
    if (debugEnabled) {
        // No movement alternatives found
    }
    
    return null;
}

// === MULTI-TURN PATHFINDING ===
function findMultiTurnPath(currentCell, sortedArray) {
    
    // Try to find paths to high-damage cells with extended range
    var maxTurnDistance = myMP * 3; // Allow paths up to 3 turns away
    var bestTarget = null;
    var bestDamagePerTurn = 0;
    
    for (var i = 0; i < min(MAX_PATHFIND_CELLS, count(sortedArray)); i++) {
        var targetData = sortedArray[i];
        var targetCell = targetData[0];
        var expectedDamage = targetData[1];
        var weaponId = targetData[2]; // Get weapon ID
        
        // Skip if damage is 0
        if (expectedDamage <= 0) continue;
        
        // Try A* with extended range
        var fullPath = aStar(currentCell, targetCell, maxTurnDistance);
        
        if (fullPath != null && count(fullPath) > 1) {
            var totalDistance = count(fullPath) - 1;
            var turnsNeeded = ceil(totalDistance * 1.0 / myMP);
            var damagePerTurn = expectedDamage / turnsNeeded;
            
            
            // Consider this target if it offers good damage per turn
            if (damagePerTurn > bestDamagePerTurn) {
                bestDamagePerTurn = damagePerTurn;
                // Create array instead of object: [targetCell, fullPath, damage, weaponId, turnsNeeded, damagePerTurn]
                bestTarget = [];
                push(bestTarget, targetCell);       // [0] targetCell
                push(bestTarget, fullPath);         // [1] fullPath
                push(bestTarget, expectedDamage);   // [2] damage
                push(bestTarget, weaponId);         // [3] weaponId
                push(bestTarget, turnsNeeded);      // [4] turnsNeeded  
                push(bestTarget, damagePerTurn);    // [5] damagePerTurn
            }
        } else {
            // Debug invalid path
            if (debugEnabled && i < 3) {
                // Multi-turn path invalid
            }
        }
    }
    
    // If we found a good multi-turn target, take first steps toward it
    if (bestTarget != null && bestDamagePerTurn > 100) { // Minimum threshold
        // Validate bestTarget[1] (fullPath) before using it
        if (bestTarget[1] != null && count(bestTarget[1]) > 1) {
            var firstTurnPath = [];
            var pathLength = min(myMP + 1, count(bestTarget[1]));
            
            for (var j = 0; j < pathLength; j++) {
                if (j < count(bestTarget[1])) {
                    push(firstTurnPath, bestTarget[1][j]);
                }
            }
            
            if (debugEnabled) {
                var pathStr = "";
                for (var p = 0; p < count(firstTurnPath); p++) {
                    pathStr += (pathStr == "" ? "" : ",") + firstTurnPath[p];
                }
                // Multi-turn path created
                markText(bestTarget[0], "T" + floor(bestTarget[2] + 0.5), getColor(255, 255, 0), 10); // Yellow target
            }
        
            if (count(firstTurnPath) > 0) {
                return createPathResult(
                    firstTurnPath[count(firstTurnPath) - 1], // targetCell
                    firstTurnPath,                           // path
                    0,                                       // damage (no immediate damage)
                    bestTarget[3],                           // weaponId for future use
                    false,                                   // reachable (not reachable this turn)
                    count(firstTurnPath) - 1,                // distance
                    false                                    // useTeleport
                );
            } else {
                if (debugEnabled) {
                    // Empty path generated, falling back
                }
            }
        } else {
            if (debugEnabled) {
                // Best target has invalid path
            }
        }
    }
    
    // If no damage zones reachable, find best cover position toward target
    if (debugEnabled) {
        // No damage zones reachable, seeking cover
    }
    
    var targetDirection = null;
    if (count(sortedArray) > 0) {
        targetDirection = sortedArray[0][0]; // Highest damage cell
    } else if (enemyCell != null) {
        targetDirection = enemyCell; // Fall back to enemy position
    }
    
    if (targetDirection != null) {
        // Find cover positions along path to target
        var pathToTarget = aStar(currentCell, targetDirection, myMP * 2);
        if (pathToTarget != null && count(pathToTarget) > 1) {
            var bestCoverCell = null;
            var bestCoverScore = 0;
            
            // Check each cell along the path for cover quality
            var checkLimit = min(myMP + 1, count(pathToTarget));
            for (var p = 1; p < checkLimit; p++) {
                var pathCell = pathToTarget[p];
                
                // Must be walkable
                if (getCellContent(pathCell) != CELL_EMPTY) continue;
                
                var coverScore = calculateCoverScore(pathCell);
                
                // Bonus for being closer to target
                var distanceToTarget = getCellDistance(pathCell, targetDirection);
                coverScore += (50 - distanceToTarget); // Closer is better
                
                // Additional bonus for being along the optimal path
                coverScore += 10;
                
                if (coverScore > bestCoverScore) {
                    bestCoverScore = coverScore;
                    bestCoverCell = pathCell;
                }
            }
            
            if (bestCoverCell != null) {
                var coverPath = aStar(currentCell, bestCoverCell, myMP);
                if (coverPath != null && count(coverPath) > 1) {
                    if (debugEnabled) {
                        // Moving to cover position
                        markText(bestCoverCell, "C" + floor(bestCoverScore), getColor(0, 255, 255), 10); // Cyan cover marker
                    }
                    
                    return createPathResult(
                        bestCoverCell,           // targetCell
                        coverPath,               // path
                        0,                       // damage
                        null,                    // weaponId
                        true,                    // reachable
                        count(coverPath) - 1,    // distance
                        false                    // useTeleport
                    );
                }
            }
        }
    }
    
    return null;
}

// === TELEPORT + MOVEMENT FALLBACK ===
function tryTeleportMovementFallback(currentCell, damageArray) {
    // Do not consider teleport in the first two turns
    if (getTurn() <= 2) {
        return null;
    }
    // Only try if we have teleportation equipped; validate per-destination later
    var chips = getChips();
    if (!inArray(chips, CHIP_TELEPORTATION)) {
        if (debugEnabled) {
            // Teleportation chip not equipped
        }
        return null;
    }

    // 1) PRIORITY: Directly search teleport -> A* to top damage cells (highest → lowest)
    // This strictly follows the requested strategy: for every teleportable cell,
    // run A* to the best damage cells and pick the first viable plan.
    // Limit to the 10 closest damage cells (weapon-based) to reduce operations
    var maxDamageChecks = 10;
    var closestDamage = [];
    for (var i = 0; i < count(damageArray); i++) {
        var e = damageArray[i];
        if (e == null || count(e) < 3) continue;
        var c = e[0];
        var dmg = e[1];
        var w = e[2];
        if (c == null || c < 0 || c > 612) continue;
        if (w == null || !isWeapon(w)) continue; // weapon-only
        if (dmg <= 0) continue;
        var dist = getCellDistance(currentCell, c);
        // Insert into top-10 by distance (selection-style)
        var inserted = false;
        for (var k = 0; k < count(closestDamage); k++) {
            if (dist < closestDamage[k][4]) { // compare distance
                // shift right by manual insert
                // Build a new array with insertion (LeekScript lacks insertAt)
                var newArr = [];
                for (var p = 0; p < k; p++) { push(newArr, closestDamage[p]); }
                push(newArr, [c, dmg, w, (count(e) > 3 ? e[3] : null), dist]);
                for (var p = k; p < count(closestDamage); p++) { push(newArr, closestDamage[p]); }
                closestDamage = newArr;
                inserted = true;
                break;
            }
        }
        if (!inserted) {
            push(closestDamage, [c, dmg, w, (count(e) > 3 ? e[3] : null), dist]);
        }
        if (count(closestDamage) > maxDamageChecks) {
            // truncate to 10 by dropping the farthest (last)
            var trimmed = [];
            for (var t = 0; t < maxDamageChecks; t++) { push(trimmed, closestDamage[t]); }
            closestDamage = trimmed;
        }
    }
    var teleportRange = 12; // CHIP_TELEPORTATION range
    var bestDAPlan = null; // {tele: cell, path: [tele..vantage], dmg: n, weapon: id}

    // Precompute and mark list of valid teleport destinations (light purple)
    var teleportDests = [];
    var COLOR_LIGHT_PURPLE = getColor(216, 191, 216); // Thistle-like light purple
    for (var r = 1; r <= teleportRange; r++) {
        var cellsAtR = getCellsAtExactDistance(currentCell, r);
        for (var i = 0; i < count(cellsAtR); i++) {
            var tc = cellsAtR[i];
            if (tc == null || tc < 0 || tc > 612) continue;
            if (getCellContent(tc) != CELL_EMPTY) continue;
            if (!canUseChip(CHIP_TELEPORTATION, tc)) continue; // respects range & rules
            // Mark every valid teleport destination
            mark(tc, COLOR_LIGHT_PURPLE);
            push(teleportDests, tc);
        }
    }

    // Iterate damage cells from highest to lowest damage
    for (var di = 0; di < min(maxDamageChecks, count(closestDamage)); di++) {
        var entry = closestDamage[di];
        if (entry == null || count(entry) < 3) continue;
        var vantageCell = entry[0];
        var vantageDamage = entry[1];
        var vantageWeapon = entry[2];

        // Prefer weapon-based damage cells (avoid chip-only bait)
        if (vantageWeapon == null || !isWeapon(vantageWeapon)) continue;

        // Ensure we can actually shoot from that vantage (alignment + LOS),
        // using associated enemy if provided; otherwise primary target.
        var enemyForVantage = (count(entry) > 3) ? entry[3] : primaryTarget;
        var enemyCellForVantage = (enemyForVantage != null) ? getCell(enemyForVantage) : enemyCell;
        if (enemyCellForVantage == null) continue;

        // Probe each teleport destination to see if we can walk to vantage within MP
        for (var ti = 0; ti < count(teleportDests); ti++) {
            var teleCell = teleportDests[ti];

            // Quick reject: if vantage == teleCell, skip A* cost and just validate TP and weapon
            var path = null;
            if (teleCell == vantageCell) {
                path = [teleCell];
            } else {
                path = aStar(teleCell, vantageCell, myMP);
            }
            if (path == null || count(path) - 1 > myMP) continue; // can't reach this turn

            // TP budget: teleport + optional weapon switch + one shot
            var tpAfterTeleport = getTP() - getChipCost(CHIP_TELEPORTATION);
            var switchCost = (getWeapon() != vantageWeapon) ? 1 : 0;
            var tpForShot = tpAfterTeleport - switchCost;
            if (tpForShot < getWeaponCost(vantageWeapon)) continue;

            // Do not re-check geometry/alignment here; the damage array already
            // encodes that this weapon can deal damage from vantageCell.

            // This plan is viable; record and stop — we iterate damage from highest to lowest
            bestDAPlan = {
                tele: teleCell,
                path: path,
                dmg: vantageDamage,
                weapon: vantageWeapon
            };
            break; // break tele loop; we found a viable tele for this top damage cell
        }

        if (bestDAPlan != null) break; // we selected the best damage cell we can realize
    }

    if (bestDAPlan != null) {
        if (debugEnabled) {
            debugW("TELEPORT→A*: teleport to " + bestDAPlan.tele + 
                   ", then path to " + bestDAPlan.path[count(bestDAPlan.path) - 1] +
                   " (dmg=" + bestDAPlan.dmg + ", weapon=" + bestDAPlan.weapon + ")");
            markText(bestDAPlan.tele, "T", getColor(255, 0, 255), 8);
            markText(bestDAPlan.path[count(bestDAPlan.path) - 1], "D", getColor(255, 128, 255), 8);
        }
        return createPathResult(
            bestDAPlan.tele,     // teleport destination
            bestDAPlan.path,     // post-teleport path (starts at tele cell)
            bestDAPlan.dmg,      // expected damage
            bestDAPlan.weapon,   // weapon to use
            true,                // reachable
            count(bestDAPlan.path) - 1,
            true                 // useTeleport
        );
    }

    var bestOption = null;
    var bestScore = 0;
    
    if (debugEnabled) {
        // Searching teleport + movement combinations
    }
    
    // Try teleporting to various positions within range
    // Reuse teleportRange for weapon vantage exploration (already defined above)
    // (Cells gathered above if we returned early are fine; else re-iterate)
    // Keep independent loop for clarity
    for (var range = 1; range <= teleportRange; range++) {
        var teleportCells = getCellsAtExactDistance(currentCell, range);
        
        for (var i = 0; i < count(teleportCells); i++) {
            var teleportCell = teleportCells[i];
            
            // Check if teleport destination is valid and chip usable for that cell
            var isWalkable = (getCellContent(teleportCell) == CELL_EMPTY);
            if (!isWalkable) continue;
            var chipCost = getChipCost(CHIP_TELEPORTATION);
            if (getTP() < chipCost) continue;
            if (!canUseChip(CHIP_TELEPORTATION, teleportCell)) continue;
            
            // Calculate what we could achieve from this teleport position
            var option = evaluateTeleportPosition(teleportCell, damageArray);
            if (option != null) {
                // Adjust score to account for TP cost for teleport
                var adjusted = option.score - chipCost;
                if (adjusted > bestScore) {
                    bestScore = adjusted;
                    bestOption = option;
                }
            }
        }
    }
    
    if (bestOption != null) {
        if (debugEnabled) {
            debugW("TELEPORT FALLBACK: Best option - teleport to " + bestOption.teleportCell + 
                   " then move to " + bestOption.targetCell + " (score: " + bestScore + ")");
            markText(bestOption.teleportCell, "TELE", getColor(255, 0, 255), 8);
            if (bestOption.targetCell != bestOption.teleportCell) {
                markText(bestOption.targetCell, "MOVE", getColor(255, 128, 255), 8);
            }
        }

        return createPathResult(
            bestOption.teleportCell,   // teleport destination (fix)
            bestOption.path,           // post-teleport path
            bestOption.damage,         // damage
            bestOption.weaponId,       // weaponId from teleport option
            true,                      // reachable
            bestOption.distance,       // distance
            true                       // useTeleport
        );
    }
    
    if (debugEnabled) {
        debugW("TELEPORT FALLBACK: No viable teleport + movement combinations found");
    }
    
    return null;
}

function evaluateTeleportPosition(teleportCell, damageArray) {
    // Evaluate all our weapons from teleportCell, allowing movement up to remaining MP
    var bestScore = -99999;
    var bestCell = null;
    var bestPath = null;
    var bestWeaponId = null;
    var remainingMP = myMP; // After teleport, all MP available
    var availableTP = getTP() - getChipCost(CHIP_TELEPORTATION);
    if (availableTP < 0) availableTP = 0;
    
    var tgt = (primaryTarget != null) ? getCell(primaryTarget) : enemyCell;
    if (tgt == null) return null;
    
    var weapons = getWeapons();
    for (var w = 0; w < count(weapons); w++) {
        var weap = weapons[w];
        var minR = getWeaponMinRange(weap);
        var maxR = getWeaponMaxRange(weap);
        var lt = getWeaponLaunchType(weap);
        // Sample ring cells at distances within weapon range
        for (var d = minR; d <= maxR; d++) {
            var ring = getCellsAtExactDistance(tgt, d);
            var stride = max(1, floor(count(ring) / 20));
            for (var i = 0; i < count(ring); i += stride) {
                var vcell = ring[i];
                if (vcell == null || vcell < 0 || vcell > 612) continue;
                if (getCellContent(vcell) != CELL_EMPTY) continue;
                // Alignment/LOS checks per launch type
                if (lt == LAUNCH_TYPE_LINE || lt == LAUNCH_TYPE_LINE_INVERTED) {
                    if (!isOnSameLine(vcell, tgt)) continue;
                } else if (lt == LAUNCH_TYPE_STAR || lt == LAUNCH_TYPE_STAR_INVERTED) {
                    // Enhanced Lightninger is normal; star only for regular
                    if (weap != WEAPON_ENHANCED_LIGHTNINGER && !isValidStarPattern(vcell, tgt)) continue;
                }
                if (!checkLineOfSight(vcell, tgt)) continue;
                // Can we walk from teleportCell to vcell with remaining MP?
                var path = aStar(teleportCell, vcell, remainingMP);
                if (path == null || count(path) - 1 > remainingMP) continue;
                // Estimate damage output from vcell with this weapon
                var switchCost = (getWeapon() != weap) ? 1 : 0;
                var tpAvail = availableTP - switchCost;
                var wCost = getWeaponCost(weap);
                if (tpAvail < wCost) continue;
                var uses = floor(tpAvail / wCost);
                var maxUses = getWeaponMaxUses(weap);
                if (maxUses > 0) uses = min(uses, maxUses);
                if (uses <= 0) continue;
                // Base damage estimate from effects
                var effects = getWeaponEffects(weap);
                var base = 0;
                for (var e = 0; e < count(effects); e++) {
                    if (effects[e][0] == 1) { base = (effects[e][1] + effects[e][2]) / 2; break; }
                }
                if (base == 0) base = wCost * 10;
                var dmg = base * (1 + myStrength / 100.0) * uses;
                // Safety via EID at vantage cell
                var eid = estimateIncomingDamageAtCell(vcell);
                var score = dmg - eid * 0.5;
                // Small bonus for Enhanced Lightninger sweet spot
                if (weap == WEAPON_ENHANCED_LIGHTNINGER && d >= 8 && d <= 10) score += 50;
                if (score > bestScore) {
                    bestScore = score;
                    bestCell = vcell;
                    bestPath = path;
                    bestWeaponId = weap;
                }
            }
        }
    }
    
    if (bestCell != null) {
        return {
            teleportCell: teleportCell,
            targetCell: bestCell,
            path: bestPath,
            damage: max(0, floor(bestScore + 0.5)), // score includes EID; pass as heuristic damage
            weaponId: bestWeaponId,
            distance: count(bestPath) - 1,
            score: bestScore
        };
    }
    
    // If no weapon vantage found, fall back to chip/damageArray or cover logic (legacy)
    var legacy = null;
    var bestDamage = 0;
    var bestLegacyCell = null;
    var bestLegacyPath = null;
    var bestLegacyWeapon = null;
    for (var i = 0; i < count(damageArray); i++) {
        var td = damageArray[i];
        if (td == null || count(td) < 3) continue;
        var tcell = td[0];
        var dmg2 = td[1];
        var wid = td[2];
        if (tcell == teleportCell && dmg2 > bestDamage) {
            bestDamage = dmg2; bestLegacyCell = teleportCell; bestLegacyPath = [teleportCell]; bestLegacyWeapon = wid;
        }
        var p2 = aStar(teleportCell, tcell, remainingMP);
        if (p2 != null && count(p2) <= remainingMP + 1 && dmg2 > bestDamage) {
            bestDamage = dmg2; bestLegacyCell = tcell; bestLegacyPath = p2; bestLegacyWeapon = wid;
        }
    }
    if (bestLegacyCell != null) {
        return {
            teleportCell: teleportCell,
            targetCell: bestLegacyCell,
            path: bestLegacyPath,
            damage: bestDamage,
            weaponId: bestLegacyWeapon,
            distance: count(bestLegacyPath) - 1,
            score: bestDamage
        };
    }
    
    var coverCell = findCoverFromPosition(teleportCell, remainingMP);
    if (coverCell != null) {
        var pathToCover = aStar(teleportCell, coverCell, remainingMP);
        if (pathToCover != null) {
            var coverScore = calculateCoverScore(coverCell);
            return {
                teleportCell: teleportCell,
                targetCell: coverCell,
                path: pathToCover,
                damage: 0,
                weaponId: null,
                distance: count(pathToCover) - 1,
                score: coverScore * 0.5
            };
        }
    }
    
    return null;
}

function findCoverFromPosition(startCell, maxMP) {
    var bestCover = null;
    var bestCoverScore = 0;
    
    // Check cells within movement range from start position
    for (var range = 1; range <= maxMP; range++) {
        var cells = getCellsAtExactDistance(startCell, range);
        
        for (var i = 0; i < count(cells); i++) {
            var cell = cells[i];
            
            // Must be walkable
            var isWalkable = (getCellContent(cell) == CELL_EMPTY);
            if (!isWalkable) continue;
            
            // Calculate cover score
            var coverScore = calculateCoverScore(cell);
            if (coverScore > bestCoverScore) {
                bestCoverScore = coverScore;
                bestCover = cell;
            }
        }
    }
    
    return bestCover;
}

// === COVER SCORING FUNCTION ===
function calculateCoverScore(cell) {
    var score = 0;
    
    // Base score: distance from primary enemy
    if (enemyCell != null) {
        score = getCellDistance(cell, enemyCell);
    }
    
    // Strong preference for breaking line of sight against enemies
    var losBroken = 0;
    var enemies = (count(allEnemies) > 0) ? allEnemies : [];
    for (var i = 0; i < count(enemies); i++) {
        var eCell = getCell(enemies[i]);
        if (eCell != null && eCell >= 0) {
            if (!checkLineOfSight(cell, eCell)) {
                losBroken++;
            }
        }
    }
    // Each broken LOS is valuable; if no enemies list, fall back to primary enemy check
    if (count(enemies) == 0 && enemyCell != null && !checkLineOfSight(cell, enemyCell)) {
        losBroken = 1;
    }
    score += losBroken * 10; // reward breaking LOS broadly
    
    // Bonus for adjacent obstacles (proxy for micro-cover); keep it small
    var obstacles = countAdjacentObstacles(cell);
    score += min(obstacles * 2, 6);

    // New: measure how many steps enemies need to regain LoS on this cell
    var minDeltaSteps = 0;
    if (count(enemies) > 0) {
        var bestDelta = -9999;
        for (var i = 0; i < count(enemies); i++) {
            var enemyEntity = enemies[i];
            if (getLife(enemyEntity) <= 0) continue;
            var steps = approxStepsForEnemyToGainLoS(enemyEntity, cell);
            var emp = getMP(enemyEntity);
            var delta = steps - emp; // positive means they need extra turns
            if (bestDelta == -9999 || delta < bestDelta) {
                bestDelta = delta; // be conservative: closest enemy
            }
        }
        if (bestDelta != -9999) {
            // If enemy can get LoS this turn (delta <= 0), penalize slightly; otherwise reward by 8 per step away
            if (bestDelta <= 0) {
                score -= 20;
            } else {
                score += min(bestDelta * 8, 40);
            }
        }
    }

    // Integrate EID (expected incoming damage) — penalize dangerous cells
    var eid = estimateIncomingDamageAtCell(cell);
    score -= min(floor(eid / 5), 60); // light penalty (don’t overwhelm other terms)

    // Penalty for being too close to map edges
    var x = getCellX(cell);
    var y = getCellY(cell);
    if (x < 2 || x > 15 || y < 2 || y > 15) {
        score -= 5;
    }
    
    return score;
}

// === APPROXIMATE ENEMY STEPS TO REGAIN LoS ===
// Estimate minimal number of steps an enemy needs to reach a cell that has LoS to targetCell.
// Uses ring distance (ignores obstacles for speed) and validates LoS per ring cell.
function approxStepsForEnemyToGainLoS(enemyEntity, targetCell) {
    var eCell = getCell(enemyEntity);
    if (eCell == null || eCell < 0) return 99;
    
    // Limit search to enemy MP + margin (cap to 12 for performance)
    var emp = getMP(enemyEntity);
    var maxStep = min(emp + 6, 12);
    
    for (var d = 0; d <= maxStep; d++) {
        var ring = getCellsAtExactDistance(eCell, d);
        for (var i = 0; i < count(ring); i++) {
            var cell = ring[i];
            if (cell == null || cell < 0 || cell > 612) continue;
            if (getCellContent(cell) != CELL_EMPTY) continue;
            if (checkLineOfSight(cell, targetCell)) {
                return d; // minimal ring steps to gain LoS
            }
        }
    }
    return maxStep + 1; // Not found within budget; treat as far
}

// Refined steps to regain LoS using A* to sampled LoS vantage cells
function refinedStepsForEnemyToGainLoS(enemyEntity, targetCell) {
    var eCell = getCell(enemyEntity);
    if (eCell == null || eCell < 0) return 99;
    var emp = getMP(enemyEntity);
    var maxStep = min(emp + 6, 12);
    var best = 99;
    for (var d = 0; d <= maxStep; d++) {
        var ring = getCellsAtExactDistance(targetCell, d);
        // Sample up to 20 cells per ring
        var stride = max(1, floor(count(ring) / 20));
        for (var i = 0; i < count(ring); i += stride) {
            var vCell = ring[i];
            if (vCell == null || vCell < 0 || vCell > 612) continue;
            if (getCellContent(vCell) != CELL_EMPTY) continue;
            if (!checkLineOfSight(vCell, targetCell)) continue;
            var path = aStar(eCell, vCell, maxStep);
            if (path != null) {
                var steps = count(path) - 1;
                if (steps < best) best = steps;
            }
        }
        if (best <= d) break; // early exit if we already found a nearby vantage
    }
    return best;
}

// === EID ESTIMATION AT A HYPOTHETICAL CELL ===
function estimateIncomingDamageAtCell(myTargetCell) {
    // Skip heavy EID estimation while LOS precompute is in progress or early turns
    if (!terrainLOSDone || getTurn() <= 3) return 0;
    if (count(allEnemies) == 0) return 0;
    if (eidCache[myTargetCell] != null) return eidCache[myTargetCell];
    var total = 0;
    for (var i = 0; i < count(allEnemies); i++) {
        var enemyEntity = allEnemies[i];
        if (getLife(enemyEntity) <= 0) continue;
        var enemyWeapons = getWeapons(enemyEntity);
        var availableTP = getTP(enemyEntity);
        var remainingTP = availableTP;
        
        // Weapons
        for (var w = 0; w < count(enemyWeapons); w++) {
            var weapon = enemyWeapons[w];
            var cost = getWeaponCost(weapon);
            if (remainingTP < cost) continue;
            // Check reach from enemy to our hypothetical cell
            var canReach = canWeaponReachTarget(weapon, getCell(enemyEntity), myTargetCell);
            if (!canReach) continue;
            var uses = getWeaponMaxUses(weapon);
            var maxUses = (uses > 0) ? min(uses, floor(remainingTP / cost)) : floor(remainingTP / cost);
            if (maxUses <= 0) continue;
            // Rough base damage per use — reuse getWeaponBaseDamage if available via evaluation/config, else proxy by cost
            var baseDmg = 0;
            var effects = getWeaponEffects(weapon);
            for (var e = 0; e < count(effects); e++) {
                if (effects[e][0] == 1) { // EFFECT_DAMAGE
                    baseDmg = (effects[e][1] + effects[e][2]) / 2;
                    break;
                }
            }
            if (baseDmg == 0) baseDmg = cost * 10; // fallback proxy
            var enemyStat = max(getStrength(enemyEntity), getMagic(enemyEntity));
            var dmgPerUse = baseDmg * (1 + enemyStat / 100.0);
            // Apply our resistance
            dmgPerUse = dmgPerUse * (1 - myResistance / 100.0);
            total += dmgPerUse * maxUses;
            remainingTP -= cost * maxUses;
        }
        // Chip lightning rough add (if enemy has TP)
        if (remainingTP >= 4) {
            // Only add if LOS and distance <= 10
            var dist = getCellDistance(getCell(enemyEntity), myTargetCell);
            if (dist <= 10 && checkLineOfSight(getCell(enemyEntity), myTargetCell)) {
                total += 50 * (1 - myResistance / 100.0);
            }
        }
    }
    var val = floor(total + 0.5);
    eidCache[myTargetCell] = val;
    return val;
}

// === SMART WEAPON POSITIONING ===
function findBestWeaponPosition(currentCell, weapons) {
    if (enemyCell == null) return null;
    
    var bestPosition = null;
    var bestScore = 0;
    
    if (debugEnabled) {
        debugW("SMART POSITION: Finding best position for " + count(weapons) + " weapons");
    }
    
    // Define weapon priorities based on build type and DPS potential
    var weaponPriorities = [];
    
    if (isMagicBuild) {
        // MAGIC BUILD: Prioritize DoT weapons as main DPS, DESTROYER for tactical debuffing
        if (debugEnabled) {
            debugW("SMART POSITION: Magic build detected, prioritizing DoT weapons as main DPS");
        }
        weaponPriorities = [
            {weapon: WEAPON_FLAME_THROWER, priority: 100, dps: 2, range: [2, 8]},   // Main DoT DPS (max 2 uses)
            {weapon: WEAPON_RHINO, priority: 90, dps: 3, range: [2, 4]},            // High DPS backup
            {weapon: WEAPON_ELECTRISOR, priority: 80, dps: 2, range: [7, 7]},       // AoE backup
            {weapon: WEAPON_DESTROYER, priority: 75, dps: 2, range: [1, 6]},        // Tactical debuff
            {weapon: WEAPON_GRENADE_LAUNCHER, priority: 70, dps: 2, range: [4, 7]}, // AoE backup
            {weapon: WEAPON_SWORD, priority: 60, dps: 2, range: [1, 1]},            // Melee backup
            {weapon: WEAPON_KATANA, priority: 50, dps: 1, range: [1, 1]},           // Melee backup
            {weapon: WEAPON_RIFLE, priority: 40, dps: 2, range: [7, 9]},            // Standard backup
            {weapon: WEAPON_M_LASER, priority: 35, dps: 2, range: [5, 12]},         // Alignment needed
            {weapon: WEAPON_LIGHTNINGER, priority: 32, dps: 2, range: [6, 10]},     // Star pattern AoE
            {weapon: WEAPON_ENHANCED_LIGHTNINGER, priority: 30, dps: 2, range: [6, 10]} // Healing
        ];
    } else {
        // STRENGTH BUILD: Standard DPS priorities
        weaponPriorities = [
            {weapon: WEAPON_RHINO, priority: 100, dps: 3, range: [2, 4]},           // 3 uses = highest DPS
            {weapon: WEAPON_ELECTRISOR, priority: 80, dps: 2, range: [7, 7]},       // 2 uses + AoE
            {weapon: WEAPON_GRENADE_LAUNCHER, priority: 75, dps: 2, range: [4, 7]}, // 2 uses + AoE
            {weapon: WEAPON_SWORD, priority: 60, dps: 2, range: [1, 1]},            // 2 uses melee
            {weapon: WEAPON_KATANA, priority: 50, dps: 1, range: [1, 1]},           // 1 use melee
            {weapon: WEAPON_RIFLE, priority: 40, dps: 2, range: [7, 9]},            // 2 uses
            {weapon: WEAPON_M_LASER, priority: 35, dps: 2, range: [5, 12]},         // Alignment needed
            {weapon: WEAPON_DESTROYER, priority: 32, dps: 2, range: [1, 6]},        // Lower priority for strength
            {weapon: WEAPON_FLAME_THROWER, priority: 31, dps: 2, range: [2, 8]},    // Lower priority for strength (max 2 uses)
            {weapon: WEAPON_LIGHTNINGER, priority: 30, dps: 2, range: [6, 10]},     // Star pattern AoE
            {weapon: WEAPON_ENHANCED_LIGHTNINGER, priority: 29, dps: 2, range: [6, 10]} // Healing
        ];
    }
    
    // Find highest priority weapon we have equipped
    var targetWeapon = null;
    var targetPriority = 0;
    var targetRange = null;
    
    for (var w = 0; w < count(weapons); w++) {
        var weapon = weapons[w];
        
        for (var p = 0; p < count(weaponPriorities); p++) {
            var wpn = weaponPriorities[p];
            if (wpn.weapon == weapon && wpn.priority > targetPriority) {
                targetWeapon = weapon;
                targetPriority = wpn.priority;
                targetRange = wpn.range;
                
                if (debugEnabled) {
                    debugW("SMART POSITION: Priority weapon " + weapon + " (priority=" + wpn.priority + ", DPS=" + wpn.dps + ")");
                }
                break;
            }
        }
    }
    
    if (targetWeapon == null) return null;
    
    // For high-DPS weapons, prioritize getting into range quickly
    var minRange = targetRange[0];
    var maxRange = targetRange[1];
    
    if (debugEnabled) {
        debugW("SMART POSITION: Target weapon " + targetWeapon + " range " + minRange + "-" + maxRange);
    }
    
    // Check positions at each distance in priority order
    var distancePriorities = [];
    
    if (targetWeapon == WEAPON_RHINO) {
        // RHINO: Prioritize distance 3 (middle of range) for flexibility
        push(distancePriorities, 3);
        push(distancePriorities, 2);
        push(distancePriorities, 4);
    } else if (targetWeapon == WEAPON_ELECTRISOR) {
        // ELECTRISOR: Must be exactly distance 7
        push(distancePriorities, 7);
    } else if (targetWeapon == WEAPON_GRENADE_LAUNCHER) {
        // GRENADE: Prefer distance 5-6 for good AoE coverage
        push(distancePriorities, 5);
        push(distancePriorities, 6);
        push(distancePriorities, 4);
        push(distancePriorities, 7);
    } else if (targetWeapon == WEAPON_SWORD || targetWeapon == WEAPON_KATANA) {
        // Melee: Must be distance 1
        push(distancePriorities, 1);
    } else {
        // Other weapons: Try middle of range first
        var midRange = floor((minRange + maxRange) / 2);
        for (var d = midRange; d >= minRange; d--) {
            push(distancePriorities, d);
        }
        for (var d = midRange + 1; d <= maxRange; d++) {
            push(distancePriorities, d);
        }
    }
    
    // Find best position at priority distances
    for (var dp = 0; dp < count(distancePriorities); dp++) {
        var targetDistance = distancePriorities[dp];
        var positions = getCellsAtExactDistance(enemyCell, targetDistance);
        
        for (var i = 0; i < count(positions); i++) {
            var cell = positions[i];
            
            // Must be walkable
            if (getCellContent(cell) == CELL_OBSTACLE) continue;
            
            // Calculate reachability score
            var moveDistance = getCellDistance(currentCell, cell);
            var reachableThisTurn = (moveDistance <= myMP);
            
            var score = 100 - moveDistance; // Closer is better
            
            if (reachableThisTurn) {
                score += 50; // Bonus for immediate reach
            }
            
            // Line of sight bonus
            if (checkLineOfSight(cell, enemyCell)) {
                score += 20;
            }
            
            // Cover bonus
            var coverBonus = countAdjacentObstacles(cell) * 3;
            score += min(coverBonus, 10); // Cap cover bonus
            
            if (score > bestScore) {
                bestScore = score;
                bestPosition = {
                    cell: cell,
                    distance: targetDistance,
                    weapon: targetWeapon,
                    reachable: reachableThisTurn
                };
                
                if (debugEnabled) {
                    debugW("SMART POSITION: New best position " + cell + " distance=" + targetDistance + " score=" + score);
                }
            }
        }
        
        // If we found a good position at this distance, use it
        if (bestPosition != null && bestScore > 50) {
            break;
        }
    }
    
    return bestPosition;
}

// === WEAPON-SPECIFIC POSITIONING ===
function findWeaponSpecificPosition(currentCell, weapons, enemyCell) {
    if (weapons == null || count(weapons) == 0 || enemyCell == null) {
        return null;
    }
    
    var bestResult = null;
    var bestScore = 0;
    
    if (debugEnabled) {
        debugW("WEAPON-SPECIFIC: Finding position for " + count(weapons) + " weapons, enemy at " + enemyCell);
    }
    
    // Check each weapon for optimal positioning
    for (var w = 0; w < count(weapons); w++) {
        var weapon = weapons[w];
        var cost = getWeaponCost(weapon);
        
        // Skip if we can't afford this weapon
        if (myTP < cost) {
            continue;
        }
        
        var minRange = getWeaponMinRange(weapon);
        var maxRange = getWeaponMaxRange(weapon);
        
        // Determine optimal distance based on weapon type
        var optimalDistance = minRange;
        if (weapon == WEAPON_RHINO) {
            optimalDistance = 3; // Middle of 2-4 range for flexibility
        } else if (weapon == WEAPON_ELECTRISOR) {
            optimalDistance = 7; // Exact range required
        } else if (weapon == WEAPON_GRENADE_LAUNCHER) {
            optimalDistance = 5; // Good AoE range
        } else if (weapon == WEAPON_SWORD || weapon == WEAPON_KATANA) {
            optimalDistance = 1; // Melee
        } else if (maxRange > minRange) {
            optimalDistance = floor((minRange + maxRange) / 2); // Middle of range
        }
        
        if (debugEnabled) {
            debugW("WEAPON-SPECIFIC: Checking " + weapon + " optimal distance " + optimalDistance);
        }
        
        // Find cells at optimal distance from enemy
        var targetCells = getCellsAtExactDistance(enemyCell, optimalDistance);
        
        for (var t = 0; t < count(targetCells) && t < 10; t++) {
            var cell = targetCells[t];
            
            // Must be walkable
            if (getCellContent(cell) != CELL_EMPTY) {
                continue;
            }
            
            // Calculate score based on reachability and weapon priority
            var moveDistance = getCellDistance(currentCell, cell);
            var score = 100 - moveDistance; // Closer is better
            
            // Weapon priority bonuses based on build type
            if (isMagicBuild) {
                // MAGIC BUILD: Prioritize DESTROYER/FLAME/DOUBLE_GUN; devalue GRENADE_LAUNCHER
                if (weapon == WEAPON_FLAME_THROWER) {
                    score += 80; // Highest (DoT primary)
                } else if (weapon == WEAPON_DESTROYER) {
                    score += 70; // Next (debuff)
                } else if (weapon == WEAPON_DOUBLE_GUN) {
                    score += 65; // Strong DoT stacking with cheap TP
                } else if (weapon == WEAPON_ELECTRISOR) {
                    score += 35; // AoE backup
                } else if (weapon == WEAPON_RHINO) {
                    score += 30; // DPS backup
                } else if (weapon == WEAPON_GRENADE_LAUNCHER) {
                    score += 5;  // Lower priority for MAGIC
                } else if (weapon == WEAPON_SWORD) {
                    score += 0;
                } else if (weapon == WEAPON_KATANA) {
                    score += 0;
                }
            } else {
                // STRENGTH BUILD: Standard priorities
                if (weapon == WEAPON_RHINO) {
                    score += 50; // Highest DPS
                } else if (weapon == WEAPON_ELECTRISOR) {
                    score += 40; // High DPS + AoE
                } else if (weapon == WEAPON_GRENADE_LAUNCHER) {
                    score += 35; // Good DPS + AoE
                } else if (weapon == WEAPON_SWORD) {
                    score += 30; // Good melee
                } else if (weapon == WEAPON_KATANA) {
                    score += 25; // Standard melee
                } else if (weapon == WEAPON_DESTROYER) {
                    score += 22; // Lower priority for strength
                } else if (weapon == WEAPON_FLAME_THROWER) {
                    score += 21; // Lower priority for strength
                }
            }
            
            // Bonus for reachable this turn
            if (moveDistance <= myMP) {
                score += 25;
            }
            
            // Line of sight bonus
            if (checkLineOfSight(cell, enemyCell)) {
                score += 15;
            }
            
            if (score > bestScore) {
                bestScore = score;
                bestResult = {
                    cell: cell,
                    weapon: weapon,
                    distance: optimalDistance,
                    reachable: moveDistance <= myMP
                };
                
                if (debugEnabled) {
                    debugW("WEAPON-SPECIFIC: New best " + weapon + " position " + cell + " (score=" + score + ")");
                }
            }
        }
    }
    
    return bestResult;
}

// === WEAPON PRIORITY SCORING ===
function getWeaponSortScore(entry) {
    var damage = entry[1];
    var weaponId = (count(entry) > 2) ? entry[2] : null;
    
    // Base score is damage
    var score = damage;
    
    // Add weapon/chip priority bonuses based on build type
    if (weaponId != null) {
        // Demote chip-only zones (chip ids start at CHIP_LIGHTNING)
        if (weaponId >= CHIP_LIGHTNING) {
            score -= 1000; // Prefer real weapons over chip-only zones by default
        }
        if (isMagicBuild) {
            // Magic builds: elevate poison chips as valid DPS vantages
            if (weaponId == CHIP_TOXIN) {
                score += 900; // AoE poison is core to DPS
            } else if (weaponId == CHIP_VENOM) {
                score += 700; // Single-target poison is strong too
            }
            // MAGIC BUILD: DESTROYER first (cycle), then DoT; devalue grenade launcher
            if (weaponId == WEAPON_DESTROYER) {
                score += 1300; // Highest priority for debuff-first cycle
            } else if (weaponId == WEAPON_FLAME_THROWER) {
                score += 1200; // Next: apply DoT
                // Combo boost: prefer FLAME vantages where TOXIN is safe & in range
                if (primaryTarget != null && count(entry) > 0) {
                    var cellId = entry[0];
                    var tgtCell = getCell(primaryTarget);
                    var dist = getCellDistance(cellId, tgtCell);
                    var chips = getChips();
                    if (inArray(chips, CHIP_TOXIN)) {
                        var toxinArea = getChipArea(CHIP_TOXIN);
                        var toxinMax = getChipMaxRange(CHIP_TOXIN);
                        var toxinMin = getChipMinRange(CHIP_TOXIN);
                        var inRange = (dist >= toxinMin && dist <= toxinMax);
                        var safeAoE = (dist > toxinArea);
                        var hasLOS = checkLineOfSight(cellId, tgtCell);
                        if (inRange && safeAoE && hasLOS) {
                            score += 150; // boost FLAME cells that enable FLAME×2 + TOXIN
                        }
                    }
                    // Secondary combo boost: if TOXIN is not possible, prefer VENOM-capable cells
                    if (inArray(chips, CHIP_VENOM)) {
                        var vMin = getChipMinRange(CHIP_VENOM);
                        var vMax = getChipMaxRange(CHIP_VENOM);
                        var vInRange = (dist >= vMin && dist <= vMax);
                        var vHasLOS = checkLineOfSight(cellId, tgtCell);
                        if (vInRange && vHasLOS) {
                            score += 120; // boost for FLAME + VENOM follow-up
                        }
                    }
                }
            } else if (weaponId == WEAPON_RHINO) {
                score += 1100; // High DPS backup
            } else if (weaponId == WEAPON_ELECTRISOR) {
                score += 1000; // Good DPS + AoE
            } else if (weaponId == WEAPON_DESTROYER) {
                score += 900; // (kept for completeness; should be caught above)
            } else if (weaponId == WEAPON_DOUBLE_GUN) {
                score += 1050; // Double Gun: strong DoT stacking for MAGIC
            } else if (weaponId == WEAPON_GRENADE_LAUNCHER) {
                score += 200; // Lower priority for MAGIC compared to DESTROYER/FLAME
            } else if (weaponId == WEAPON_B_LASER) {
                score += 700; // Multi-use backup
            } else if (weaponId == WEAPON_ENHANCED_LIGHTNINGER) {
                score += 700; // Higher priority for Enhanced Lightninger vantage
            } else if (weaponId == WEAPON_M_LASER) {
                score += 500; // Alignment required
            } else if (weaponId == WEAPON_RIFLE) {
                score += 400; // Standard weapon
            } else if (weaponId == WEAPON_KATANA) {
                score += 300; // Melee backup
            } else if (weaponId == WEAPON_SWORD) {
                score += 200; // Basic melee
            }
        } else {
            // STRENGTH BUILD: Standard priorities
            if (weaponId == WEAPON_RHINO) {
                score += 1000; // Highest priority - excellent DPS, low cost
            } else if (weaponId == WEAPON_ELECTRISOR) {
                score += 900; // High priority - good DPS, AoE
            } else if (weaponId == WEAPON_GRENADE_LAUNCHER) {
                score += 800; // Good priority - decent DPS, AoE
            } else if (weaponId == WEAPON_B_LASER) {
                score += 700; // Good priority - multi-use
            } else if (weaponId == WEAPON_ENHANCED_LIGHTNINGER) {
                score += 750; // Strong priority for reachable Enhanced Lightninger
            } else if (weaponId == WEAPON_M_LASER) {
                score += 650; // Increased priority for non-magic builds
            } else if (weaponId == WEAPON_RIFLE) {
                score += 400; // Lower priority - standard weapon
            } else if (weaponId == WEAPON_DESTROYER) {
                score += 350; // Lower priority for strength builds
            } else if (weaponId == WEAPON_FLAME_THROWER) {
                score += 340; // Lower priority for strength builds
            } else if (weaponId == WEAPON_KATANA) {
                score += 300; // Low priority - melee, bonus damage
            } else if (weaponId == WEAPON_SWORD) {
                score += 100; // Lowest priority - basic melee
            }
        }
    }
    
    // KEEP-OUT VS STRENGTH BUILDS: prefer safer distances when we have non-melee options
    if (primaryTarget != null) {
        var enemyStr = getStrength(primaryTarget);
        var enemyMag = getMagic(primaryTarget);
        var enemyAgi = getAgility(primaryTarget);
        var isStrengthEnemy = (enemyStr > max(enemyMag, enemyAgi) + 100);
        if (isStrengthEnemy) {
            // Only apply if we carry at least one mid/long-range weapon
            var myWeapons = getWeapons();
            var hasNonMelee = false;
            for (var i = 0; i < count(myWeapons); i++) {
                if (getWeaponMaxRange(myWeapons[i]) >= 5) { hasNonMelee = true; break; }
            }
            if (hasNonMelee && count(entry) > 0) {
                var cellId = entry[0];
                var targetCell = getCell(primaryTarget);
                var dist = getCellDistance(cellId, targetCell);
                if (dist <= 3) {
                    score -= 200; // Strong penalty for brawling range
                } else if (dist <= 5) {
                    score -= 100; // Mild penalty for skirmish range
                } else if (dist >= 7 && dist <= 10) {
                    score += 80;  // Bonus for safe mid-long range
                }
            }
        }
    }
    
    // DISTANCE BONUS: For magic builds using FLAME_THROWER, prefer longer distances to stay out of enemy TOXIN range
    if (isMagicBuild && weaponId == WEAPON_FLAME_THROWER && count(entry) > 0) {
        var cellId = entry[0];
        if (primaryTarget != null) {
            var targetCell = getCell(primaryTarget);
            if (targetCell != null) {
                var dist = getCellDistance(cellId, targetCell);
                // Bonus for distances 6-8 (max FLAME_THROWER range), penalty for close range
                if (dist >= 6 && dist <= 8) {
                    score += 50; // Prefer max range for safety
                } else if (dist >= 4 && dist <= 5) {
                    score += 25; // Moderate range is acceptable
                } else if (dist <= 3) {
                    score -= 25; // Penalty for being too close to enemy TOXIN range
                }
            }
        }
    }

    // EID penalty: downweight dangerous positions
    if (count(entry) > 0) {
        var posCell = entry[0];
        var eidPos = estimateIncomingDamageAtCell(posCell);
        score -= min(eidPos, 800); // strong but capped penalty
    }

    // M-LASER ALIGNMENT BONUS: Prefer aligned cells at near-optimal ranges
    if (weaponId == WEAPON_M_LASER && primaryTarget != null && count(entry) > 0) {
        var mlCell = entry[0];
        var mlTarget = getCell(primaryTarget);
        var mlDist = getCellDistance(mlCell, mlTarget);
        if (isOnSameLine(mlCell, mlTarget)) {
            if (mlDist >= 7 && mlDist <= 9) {
                score += 100; // sweet spot
            } else if (mlDist >= 5 && mlDist <= 12) {
                score += 50;  // in-range alignment
            }
        }
    }
    
    return score;
}
    // (Removed misplaced magic block outside function scope)
