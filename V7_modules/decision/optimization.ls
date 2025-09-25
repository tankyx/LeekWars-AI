// V7 Module: decision/optimization.ls
// Operations optimization for multi-enemy scenarios

// === CORRIDOR-BASED CELL FILTERING ===
// Instead of full circles, get cells in tactical corridor between leek and enemy
function getCellsInCorridor(myCell, enemyCell, range, corridorWidth) {
    var cells = [];
    if (corridorWidth == null) corridorWidth = 4; // Default corridor width (2 cells each side)

    var myX = getCellX(myCell);
    var myY = getCellY(myCell);
    var enemyX = getCellX(enemyCell);
    var enemyY = getCellY(enemyCell);

    // Calculate direction vector to enemy
    var deltaX = enemyX - myX;
    var deltaY = enemyY - myY;
    var totalDistance = sqrt(deltaX * deltaX + deltaY * deltaY);

    // Normalize direction vector
    var dirX = (totalDistance > 0) ? deltaX / totalDistance : 0;
    var dirY = (totalDistance > 0) ? deltaY / totalDistance : 0;

    // Calculate perpendicular vector for corridor width
    var perpX = -dirY; // Perpendicular to direction
    var perpY = dirX;

    // Get all cells at exact range from enemy
    var allCells = getCellsAtExactDistance(enemyCell, range);

    // Filter cells that fall within tactical corridor
    for (var i = 0; i < count(allCells); i++) {
        var cell = allCells[i];
        var cellX = getCellX(cell);
        var cellY = getCellY(cell);

        // Project cell position onto the direction vector
        var toCellX = cellX - myX;
        var toCellY = cellY - myY;

        // Calculate distance from corridor centerline
        var perpDistance = abs(toCellX * perpX + toCellY * perpY);

        // Include cell if it's within corridor width
        if (perpDistance <= corridorWidth) {
            push(cells, cell);
        }
    }

    // If corridor is too narrow, fall back to key tactical positions
    if (count(cells) < 3) {
        // Add cardinal directions from enemy at this range
        var cardinalOffsets = [
            [range, 0], [-range, 0], [0, range], [0, -range],
            [floor(range * 0.7), floor(range * 0.7)], // Diagonal positions
            [floor(-range * 0.7), floor(range * 0.7)],
            [floor(range * 0.7), floor(-range * 0.7)],
            [floor(-range * 0.7), floor(-range * 0.7)]
        ];

        for (var j = 0; j < count(cardinalOffsets); j++) {
            var offset = cardinalOffsets[j];
            var testX = enemyX + offset[0];
            var testY = enemyY + offset[1];
            var testCell = getCellFromXY(testX, testY);

            if (testCell != null && testCell >= 0 && testCell <= 612) {
                var actualRange = getCellDistance(enemyCell, testCell);
                if (abs(actualRange - range) < 0.5) { // Close enough to target range
                    push(cells, testCell);
                }
            }
        }
    }

    return cells;
}

// === SMART RANGE SELECTION ===
// Return 1-2 optimal ranges instead of full range sweep
function getOptimalRanges(weapon, myCell, enemyCell) {
    var minRange = getWeaponMinRange(weapon);
    var maxRange = getWeaponMaxRange(weapon);
    var currentDistance = getCellDistance(myCell, enemyCell);

    var ranges = [];

    // Priority 1: Current distance if weapon can use it
    if (currentDistance >= minRange && currentDistance <= maxRange) {
        push(ranges, currentDistance);
        return ranges; // Only need current distance
    }

    // Priority 2: Closest valid range to current position
    if (currentDistance < minRange) {
        push(ranges, minRange); // Need to move closer
    } else {
        push(ranges, maxRange); // Use maximum range
    }

    // Priority 3: Add middle range if weapon has wide range spread
    var rangeSpread = maxRange - minRange;
    if (rangeSpread >= 4 && count(ranges) == 1) {
        var middleRange = floor((minRange + maxRange) / 2);
        if (middleRange != ranges[0]) {
            push(ranges, middleRange);
        }
    }

    return ranges;
}

// === ENEMY PRIORITIZATION SYSTEM ===
// Assign calculation tiers to enemies based on threat/priority
function prioritizeEnemiesForCalculation(allEnemies, myCell) {
    var prioritizedEnemies = [];

    for (var i = 0; i < count(allEnemies); i++) {
        var currentEnemy = allEnemies[i];
        if (getLife(currentEnemy) <= 0) continue;

        var currentEnemyCell = getCell(currentEnemy);
        var distance = getCellDistance(myCell, currentEnemyCell);
        var hp = getLife(currentEnemy);
        var maxHP = getTotalLife(currentEnemy);
        var hpPercent = hp / maxHP;

        // Calculate priority score
        var priority = 0;

        // Distance factor (closer = higher priority)
        priority += max(0, 100 - distance * 3);

        // HP factor (lower HP = higher priority for finishing)
        if (hpPercent < 0.3) priority += 50;
        else if (hpPercent < 0.6) priority += 20;

        // Primary target bonus
        if (currentEnemy == primaryTarget) priority += 100;

        // Assign calculation tier based on priority
        var tier = 3; // Default: basic calculation
        if (priority >= 120) tier = 1; // Full calculation
        else if (priority >= 60) tier = 2; // Simplified calculation

        push(prioritizedEnemies, {
            enemyEntity: currentEnemy,
            cell: currentEnemyCell,
            distance: distance,
            priority: priority,
            tier: tier
        });
    }

    // Sort by priority (highest first)
    for (var i = 0; i < count(prioritizedEnemies) - 1; i++) {
        for (var j = i + 1; j < count(prioritizedEnemies); j++) {
            if (prioritizedEnemies[j].priority > prioritizedEnemies[i].priority) {
                var temp = prioritizedEnemies[i];
                prioritizedEnemies[i] = prioritizedEnemies[j];
                prioritizedEnemies[j] = temp;
            }
        }
    }

    return prioritizedEnemies;
}

// === OPTIMIZED MULTI-ENEMY CALCULATION (FULL RANGE VERSION) ===
// Main optimization function - keeps full range sweeps but optimizes cells and enemies
function calculateOptimizedDamageZones(allEnemies, weapons, maxOperations) {
    var enemyDamageZones = [];
    var operationsUsed = 0;

    // Step 1: Prioritize enemies by threat/distance
    var prioritizedEnemies = prioritizeEnemiesForCalculation(allEnemies, myCell);

    // Step 2: Process enemies by priority tier
    for (var e = 0; e < count(prioritizedEnemies) && operationsUsed < maxOperations; e++) {
        var targetData = prioritizedEnemies[e];
        var targetEntity = targetData.enemyEntity;
        var targetCell = targetData.cell;
        var tier = targetData.tier;

        // Step 3: Select weapons based on tier
        var weaponsToProcess = [];
        if (tier == 1) {
            weaponsToProcess = weapons; // Full weapon set for high priority
        } else if (tier == 2) {
            // Top 2-3 weapons for medium priority
            weaponsToProcess = getTopWeaponsForRange(weapons, targetData.distance, 3);
        } else {
            // Single best weapon for low priority
            weaponsToProcess = getTopWeaponsForRange(weapons, targetData.distance, 1);
        }

        // Step 4: Process each weapon with FULL RANGE SWEEP (as requested)
        for (var w = 0; w < count(weaponsToProcess) && operationsUsed < maxOperations; w++) {
            var weapon = weaponsToProcess[w];

            // Skip unaffordable weapons
            if (getWeaponCost(weapon) > myTP) continue;

            var minRange = getWeaponMinRange(weapon);
            var maxRange = getWeaponMaxRange(weapon);

            // Step 5: Full range sweep (keeping original behavior)
            for (var range = minRange; range <= maxRange && operationsUsed < maxOperations; range++) {

                // Step 6: Use corridor-based cell filtering (THE BIG OPTIMIZATION!)
                var corridorWidth = (tier == 1) ? 5 : 3; // Wider corridor for high priority
                var zoneCells = getCellsInCorridor(myCell, targetCell, range, corridorWidth);

                // Step 7: Process cells with operation limit
                var cellsToProcess = min(count(zoneCells), maxOperations - operationsUsed);
                for (var c = 0; c < cellsToProcess; c++) {
                    var attackPosition = zoneCells[c];
                    operationsUsed++;

                    // Quick validation
                    if (attackPosition < 0 || attackPosition > 612) continue;

                    // Calculate damage (simplified for lower tiers)
                    var damage = 0;
                    if (tier == 1) {
                        damage = calculateBaseWeaponDamage(weapon, attackPosition, targetCell);
                    } else {
                        damage = estimateSimpleDamage(weapon); // Faster estimation
                    }

                    if (damage > 0) {
                        // LoS check (skip for tier 3 to save operations)
                        var hasLoS = (tier >= 2) ? checkLineOfSight(attackPosition, targetCell) : true;

                        if (hasLoS || damage > 50) {
                            push(enemyDamageZones, [attackPosition, damage, weapon, targetEntity]);
                        }
                    }
                }

                // Early termination: if we have enough good zones, stop
                if (tier == 1 && count(enemyDamageZones) > 30) break;
                if (tier == 2 && count(enemyDamageZones) > 15) break;
            }
        }
    }

    return enemyDamageZones;
}

// === HELPER FUNCTIONS ===

// Get top N weapons suitable for a given range
function getTopWeaponsForRange(weapons, targetDistance, maxWeapons) {
    var suitableWeapons = [];

    for (var i = 0; i < count(weapons); i++) {
        var weapon = weapons[i];
        var minRange = getWeaponMinRange(weapon);
        var maxRange = getWeaponMaxRange(weapon);

        // Score weapon based on how well it fits the target distance
        var score = 0;
        if (targetDistance >= minRange && targetDistance <= maxRange) {
            score = 100; // Perfect fit
        } else {
            // Penalty based on distance from range
            var distanceFromRange = min(abs(targetDistance - minRange), abs(targetDistance - maxRange));
            score = max(0, 50 - distanceFromRange * 10);
        }

        if (score > 0) {
            push(suitableWeapons, {weapon: weapon, score: score});
        }
    }

    // Sort by score and return top N
    for (var i = 0; i < count(suitableWeapons) - 1; i++) {
        for (var j = i + 1; j < count(suitableWeapons); j++) {
            if (suitableWeapons[j].score > suitableWeapons[i].score) {
                var temp = suitableWeapons[i];
                suitableWeapons[i] = suitableWeapons[j];
                suitableWeapons[j] = temp;
            }
        }
    }

    var result = [];
    for (var k = 0; k < min(maxWeapons, count(suitableWeapons)); k++) {
        push(result, suitableWeapons[k].weapon);
    }

    return result;
}

// Fast damage estimation for lower priority enemies
function estimateSimpleDamage(weapon) {
    var effects = getWeaponEffects(weapon);
    var baseDamage = 0;

    for (var i = 0; i < count(effects); i++) {
        if (effects[i][0] == 1) { // EFFECT_DAMAGE
            baseDamage = (effects[i][1] + effects[i][2]) / 2;
            break;
        }
    }

    // Apply basic strength scaling without complex calculations
    return baseDamage * (1 + myStrength / 100.0);
}
