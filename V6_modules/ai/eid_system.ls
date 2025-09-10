// V6 Module: ai/eid_system.ls
// Expected Incoming Damage system
// Auto-generated from V5.0 script

// Function: calculateEID
function calculateEID(cell) {
    // Multi-enemy support: calculate total EID from all enemies
    if (count(allEnemies) > 1) {
        return calculateMultiEID(cell);
    }
    
    if (enemy == null) return 0;
    
    // Early exit if enemy can't possibly reach
    if (getCellDistance(enemyCell, cell) > ENEMY_MAX_RANGE + getTotalMP(enemy)) {
        CACHE_EID[cell] = 0;
        return 0;
    }
    
    // Check cache first
    var cached = mapGet(CACHE_EID, cell, null);
    if (cached != null) return cached;
    
    // FIX: Enemy's next turn resources are their total TP/MP
    var enemyTPNext = getTotalTP(enemy);
    var enemyMPNext = getTotalMP(enemy);
    
    // Get enemy's reachable positions (blocking my position)
    var enemyReachable = getEnemyReachable(enemyCell, enemyMPNext);
    
    // Limit to R_E_MAX most likely positions based on operation level
    var currentMode = getOperationLevel();
    // INCREASED limits since we're only using 1-19% operations
    var maxPositions = 20;  // Increased from 10 to check more enemy positions
    if (currentMode == "SURVIVAL" || currentMode == "PANIC") {
        maxPositions = 5;  // Still limited in panic mode
    } else if (turn >= 10) {
        maxPositions = 10;  // Moderate after turn 10
    } else if (turn >= 5) {
        maxPositions = 15;  // Good coverage mid-game
    }
    
    if (count(enemyReachable) > maxPositions) {
        // Use arrayFoldLeft for 300% better performance
        var sortable = arrayFoldLeft(enemyReachable, function(acc, r) {
            var dist = getCellDistance(r, cell);
            push(acc, [dist, r]);
            return acc;
        }, []);
        
        sort(sortable);
        
        // Extract just the cells we need
        enemyReachable = arrayFoldLeft(sortable, function(acc, item, idx) {
            if (idx < maxPositions) {
                push(acc, item[1]);
            }
            return acc;
        }, []);
    }
    
    // Calculate EID from each enemy position using arrayFoldLeft (adversarial max)
    var bestEV = arrayFoldLeft(enemyReachable, function(maxDamage, enemyPos) {
        var dist = getCellDistance(enemyPos, cell);
        
        // Skip expensive operations if we're very low
        if (!canSpendOps(500000)) {
            // Simple estimate based on distance
            if (dist <= 7) {
                return max(maxDamage, 200);  // Rough estimate
            }
            return maxDamage;
        }
        
        // Check weapons using arrayFoldLeft
        var weapons = getWeapons(enemy);
        var weaponDamage = 0;
        if (weapons != null) {
            weaponDamage = arrayFoldLeft(weapons, function(maxWpnDmg, w) {
                if (dist >= getWeaponMinRange(w) && dist <= getWeaponMaxRange(w)) {
                    // Check LOS if needed
                    if (!weaponNeedLos(w) || hasLOS(enemyPos, cell)) {
                        // Calculate damage including AoE threat
                        var baseDamage = getWeaponDamage(w, enemy);
                        var area = getWeaponArea(w);
                        
                        // HUGE penalty for large AoE weapons (Bazooka)
                        if (area >= 25) {  // Bazooka-sized AoE
                            // Can't dodge this easily - massive threat multiplier
                            baseDamage = baseDamage * 1.8;  // 80% extra threat
                            if (dist >= getWeaponMinRange(w) && dist <= getWeaponMaxRange(w) + 2) {
                                // We're in prime Bazooka range - even more dangerous
                                baseDamage = baseDamage * 1.2;  // Total 2.16x threat
                            }
                        } else if (area >= 9) {  // Medium AoE
                            baseDamage = baseDamage * 1.3;  // 30% extra threat
                        } else if (area > 1) {  // Small AoE
                            baseDamage = baseDamage * 1.1;  // 10% extra threat
                        }
                        
                        return max(maxWpnDmg, baseDamage);
                    }
                }
                return maxWpnDmg;
            }, 0);
        }
        
        // Check chips if still have ops - using slice to limit and arrayFoldLeft
        var chipDamage = 0;
        if (canSpendOps(5000)) {
            var chips = getChips(enemy);
            if (chips != null) {
                // Limit to first 5 chips
                var limitedChips = count(chips) > 5 ? arrayFilter(chips, function(ch, idx) { return idx < 5; }) : chips;
                chipDamage = arrayFoldLeft(limitedChips, function(maxChpDmg, ch) {
                    if (!chipHasDamage(ch)) return maxChpDmg;
                    if (getCooldown(ch, enemy) > 0) return maxChpDmg;  // Fixed: check cooldown
                    
                    if (dist >= getChipMinRange(ch) && dist <= getChipMaxRange(ch)) {
                        if (!chipNeedLos(ch) || hasLOS(enemyPos, cell)) {
                            // Calculate damage including AoE
                            var baseDamage = getChipDamage(ch, enemy);
                            var area = getChipArea(ch);
                            // If AoE chip, adjust damage estimate
                            if (area > 1) {
                                baseDamage = baseDamage * 0.8;
                            }
                            return max(maxChpDmg, baseDamage);
                        }
                    }
                    return maxChpDmg;
                }, 0);
            }
        }
        
        // Return max of current max and this position's damage
        var totalDamage = max(weaponDamage, chipDamage);
        return max(maxDamage, totalDamage);
    }, 0);
    
    // Use maximum expected damage (adversarial)
    var finalEID = bestEV;
    
    CACHE_EID[cell] = finalEID;
    return finalEID;
}

// Calculate optimal damage allocation with knapsack

// Function: precomputeEID
function precomputeEID(cells, cap) {
    EID_TURN = [:];
    var n = min(cap, count(cells));
    for (var i = 0; i < n; i++) {
        if (!canSpendOps(20000)) break;
        var c = cells[i];
        EID_TURN[c] = calculateEID(c);
    }
}

// Get EID with caching

// Function: eidOf
function eidOf(cell) {
    var v = mapGet(EID_TURN, cell, null);
    return (v != null) ? v : calculateEID(cell);
}

// Find best approach step

// Function: visualizeEID
function visualizeEID() {
    // Visualize EID in red gradient
    if (!debugEnabled || !canSpendOps(30000)) return;
    
    var myEHP = calculateEHP(myHP, myAbsShield, myRelShield, 0, myResistance);
    
    // Build EID map for nearby cells
    var reach = getReachableCells(myCell, 10);  // Check cells within 10 MP
    
    // Limit to 40 cells
    if (count(reach) > 40) {
        var sorted = [];
        for (var i = 0; i < count(reach); i++) {
            var dist = getCellDistance(reach[i], myCell);
            push(sorted, [dist, reach[i]]);
        }
        sort(sorted);
        reach = [];
        for (var i = 0; i < 40; i++) {
            push(reach, sorted[i][1]);
        }
    }
    
    for (var i = 0; i < count(reach); i++) {
        var cell = reach[i];
        var eid = eidOf(cell);
        var ratio = myEHP > 0 ? eid / myEHP : 0;
        
        // Red gradient based on danger
        var color;
        if (ratio >= 0.8) {
            color = 0xFF0000;  // Pure red - lethal
        } else if (ratio >= 0.6) {
            color = 0xFF3300;  // Red-orange - very dangerous
        } else if (ratio >= 0.4) {
            color = 0xFF6600;  // Orange - dangerous
        } else if (ratio >= 0.2) {
            color = 0xFF9900;  // Light orange - moderate
        } else if (ratio > 0) {
            color = 0xFFCC00;  // Yellow-orange - low threat
        } else {
            color = 0x00FF00;  // Green - safe
        }
        
        mark(cell, color);  // Fixed: removed opacity arg
        
        // Show EID value for high threat cells
        if (ratio >= 0.4) {
            markText(cell, floor(eid), COLOR_WHITE);
        }
    }
    
    // Mark special positions
    mark(myCell, COLOR_BLUE);
    if (enemy != null) {
        mark(enemyCell, COLOR_TARGET);
    }
    
    // Mark all enemies in multi-enemy scenarios
    if (count(allEnemies) > 1) {
        for (var i = 0; i < count(allEnemies); i++) {
            var e = allEnemies[i];
            if (e["entity"] == enemy) {
                mark(e["cell"], COLOR_TARGET);  // Primary target
            } else {
                mark(e["cell"], 0xFF00FF);  // Secondary targets (magenta)
            }
        }
    }
}

// Function: calculateMultiEID
function calculateMultiEID(cell) {
    // Calculate total expected incoming damage from all enemies
    var totalEID = 0;
    
    for (var i = 0; i < count(allEnemies); i++) {
        var e = allEnemies[i];
        var enemyEntity = e["entity"];
        var enemyPos = e["cell"];
        var enemyTPNext = getTotalTP(enemyEntity);
        var enemyMPNext = getTotalMP(enemyEntity);
        
        // Skip if enemy can't possibly reach
        if (getCellDistance(enemyPos, cell) > 14 + enemyMPNext) {
            continue;
        }
        
        // Get enemy's reachable positions
        var enemyReachable = getEnemyReachable(enemyPos, enemyMPNext);
        
        // Limit positions to check (performance)
        if (count(enemyReachable) > 10) {
            var sorted = [];
            for (var j = 0; j < count(enemyReachable); j++) {
                var dist = getCellDistance(enemyReachable[j], cell);
                push(sorted, [dist, enemyReachable[j]]);
            }
            sort(sorted);
            enemyReachable = [];
            for (var j = 0; j < 10; j++) {
                push(enemyReachable, sorted[j][1]);
            }
        }
        
        // Calculate max damage from this enemy
        var maxDamageFromEnemy = 0;
        for (var j = 0; j < count(enemyReachable); j++) {
            var enemyAttackPos = enemyReachable[j];
            var dist = getCellDistance(enemyAttackPos, cell);
            
            // Estimate damage based on enemy strength
            var estimatedDamage = 0;
            if (dist <= 7 && hasLOS(enemyAttackPos, cell)) {
                // Enemy can likely attack with weapons
                estimatedDamage = e["strength"] * 2.5;  // Rough estimate
            } else if (dist <= 10 && hasLOS(enemyAttackPos, cell)) {
                // Can use chips
                estimatedDamage = e["strength"] * 1.5;
            }
            
            maxDamageFromEnemy = max(maxDamageFromEnemy, estimatedDamage);
        }
        
        totalEID += maxDamageFromEnemy;
    }
    
    // Cache the result
    CACHE_EID[cell] = totalEID;
    return totalEID;
}

// === EID HELPERS ===
// Precompute EID for a set of cells
