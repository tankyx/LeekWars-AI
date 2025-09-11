// V6 Module: ai/combat_decisions.ls
// Combat-focused decision making and execution
// Refactored from decision_making.ls for better modularity

// NOTE: Global variables are defined in core/globals.ls when included via V6_main.ls
// For standalone testing only, uncomment the lines below:
// global debugEnabled = true;
// global myTP = 0;
// global myHP = 0;
// global myMaxHP = 100;
// global myMP = 0;
// global myCell = 0;
// global enemy = null;
// global enemyCell = 0;
// global enemyHP = 100;
// global enemyDistance = 5;
// global turn = 1;
// global PKILL_COMMIT = 0.7;
// global THREAT_HIGH_RATIO = 0.8;
// global TP_DEFENSIVE_RATIO = 0.6;
// global ENEMY_MIN_RANGE = 1;
// global ENEMY_HAS_BAZOOKA = false;
// global WEAPON_DARK_KATANA = 301;
// global WEAPON_RIFLE = 101;
// global myAbsShield = 0;
// global myRelShield = 0;
// global myResistance = 0;

// Functions from debug system
// debugLog is provided by utils/debug.ls when included via V6_main.ls
// canSpendOps is provided by core/operations.ls when included via V6_main.ls

// Functions from combat system  
// executeAttack is provided by combat/attack_execution.ls when included via V6_main.ls
// executeDefensive is provided by combat/execute_combat_refactored.ls when included via V6_main.ls

// canSetupKill is provided by strategy/kill_calculations.ls when included via V6_main.ls
// findHitCells is provided by movement/range_finding.ls when included via V6_main.ls  
// canReachDistance is provided by movement/reachability.ls when included via V6_main.ls
// findBestAttackPosition is provided by combat/positioning_logic.ls when included via V6_main.ls

// executeCloseRangeDomination defined later in file

// handleBazookaRange defined later in file

// executeHighThreatStrategy defined later in file

// executeStandardStrategy defined later in file

// findReachableHitCells is provided by movement/range_finding.ls when included via V6_main.ls

// executeStandardCombat defined later in file

// bestApproachStep is provided by movement/pathfinding.ls when included via V6_main.ls
// moveToward is provided by movement/positioning.ls when included via V6_main.ls
// repositionDefensive is provided by combat/positioning_logic.ls when included via V6_main.ls

// Functions from damage calculation
// calculatePkill is provided by strategy/kill_calculations.ls when included via V6_main.ls
// calculateLifeSteal is provided by combat/damage_calculation.ls when included via V6_main.ls
// calculateEID is provided by ai/eid_system.ls when included via V6_main.ls  
// calculateEHP is provided by ai/evaluation.ls when included via V6_main.ls

// Functions from weapon management
// getWeapons is provided by combat/weapon_management.ls when included via V6_main.ls
// switchToWeaponIfNeeded is provided by combat/weapon_management.ls when included via V6_main.ls
// getWeaponCost is provided by combat/weapon_analysis.ls when included via V6_main.ls
// useWeapon is provided by combat/weapon_management.ls when included via V6_main.ls
// getReachableCells is provided by movement/reachability.ls when included via V6_main.ls
// moveToCell is provided by movement/positioning.ls when included via V6_main.ls
// hasLOS is provided by movement/line_of_sight.ls when included via V6_main.ls

// LeekScript constants (defined by LeekScript engine)
// global USE_CRITICAL = 2;

// getStrength is provided by LeekScript built-in functions when included via V6_main.ls
// inArray is provided by LeekScript built-in functions when included via V6_main.ls
// round is provided by LeekScript built-in functions when included via V6_main.ls

// Include required modules

// Function: makeCombatDecision
// Main combat decision logic - Stage C from original

function makeCombatDecision() {
    if (debugEnabled && canSpendOps(1000)) {
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Entering Stage C: Full evaluation");
        }
    }
    
    // Stage C: Full evaluation (skip expensive parts on turn 5+)
    
    // Unified kill commitment: use effective pkill with lifesteal modifier

    var pkillCurrent = calculatePkill(enemyHP, myTP);

    var lifeStealNow = calculateLifeSteal(100, enemy);  // Estimated damage for lifesteal calculation

    var effectivePkill = min(1.0, pkillCurrent + lifeStealNow * 0.1);
    
    if (effectivePkill >= PKILL_COMMIT) {
        if (debugEnabled && canSpendOps(1000)) {
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("Committing to attack - effectivePkill=" + effectivePkill + 
                    " (base=" + pkillCurrent + " lifesteal=" + lifeStealNow + ")");
            }
        }
        executeAttack();
        if (myTP >= 4) executeDefensive();
        return "attack_committed";
    }
    
    // Check if we can setup a 2-turn kill
    if (debugEnabled && canSpendOps(1000)) {
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Checking canSetupKill...");
        }
    }
    
    if (canSetupKill() && canSpendOps(1500000)) {
        if (debugEnabled && canSpendOps(1000)) {
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("Setting up 2-turn kill");
            }
        }
        // Find cells where we can hit the enemy
        if (debugEnabled && canSpendOps(1000)) {
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("Calling findHitCells...");
            }
        }

        var raw = findHitCells();
        if (debugEnabled && canSpendOps(1000)) {
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("Found " + count(raw) + " hit cells");
            }
        }
        
        // Setup positioning for kill - simplified
        if (debugEnabled && canSpendOps(1000)) {
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("Potential kill setup detected");
            }
        }
        executeAttack();
        return "kill_setup";
    }
    
    return evaluateCombatStrategy();
}

// Function: evaluateCombatStrategy
// Evaluate different combat strategies based on current situation

function evaluateCombatStrategy() {
    // KITING STRATEGY: If we have regeneration effects, prioritize maintaining distance
    if (myHP < myMaxHP * 0.7) {
        if (debugEnabled && canSpendOps(1000)) {
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("Low HP - maintaining distance");
            }
        }
        
        if (enemyDistance <= 8 && myMP > 2) {
            // Simple kiting - move away and attack
            executeDefensive();
            if (debugEnabled && canSpendOps(1000)) {
                if (debugEnabled && canSpendOps(1000)) {
		debugLog("Executed defensive positioning");
                }
            }
            return "kiting_executed";
        }
    }
    
    // TACTICAL: Exploit enemy min range weapons (like Bazooka)
    if (enemyDistance <= ENEMY_MIN_RANGE && ENEMY_MIN_RANGE >= 4) {
        if (debugEnabled && canSpendOps(1000)) {
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("🎯 CLOSE COMBAT ADVANTAGE! Enemy can't shoot (dist=" + enemyDistance + ", min=" + ENEMY_MIN_RANGE + ")");
            }
        }
        
        if (ENEMY_HAS_BAZOOKA) {
            if (debugEnabled && canSpendOps(1000)) {
                if (debugEnabled && canSpendOps(1000)) {
		debugLog("🦔 BAZOOKA TRAP: Enemy must waste MP to escape!");
                }
            }
            return executeCloseRangeDomination();
        }
    }
    
    // DANGER: Bazooka optimal range - be extra defensive
    if (ENEMY_HAS_BAZOOKA && enemyDistance >= 2 && enemyDistance <= 4) {
        if (debugEnabled && canSpendOps(1000)) {
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("⚠️ BAZOOKA DANGER ZONE! Distance " + enemyDistance);
            }
        }
        return handleBazookaRange();
    }
    
    // Standard threat-based combat logic

    var threatRatio = calculateEID(myCell) / calculateEHP(myHP, myAbsShield, myRelShield, 0, myResistance);

    var potentialLifeSteal = calculateLifeSteal(100, enemy);  // Estimated damage for lifesteal calculation

    var willAttackThisTurn = (myTP >= 5 && enemyDistance <= 10);
    
    if (threatRatio >= THREAT_HIGH_RATIO || (threatRatio >= TP_DEFENSIVE_RATIO && potentialLifeSteal > 100)) {
        return executeHighThreatStrategy(threatRatio, potentialLifeSteal, willAttackThisTurn);
    } else {
        return executeStandardStrategy(threatRatio);
    }
}
// Function: executeCloseRangeDomination
// Execute close range combat advantage

function executeCloseRangeDomination() {

    var weapons = getWeapons();
    
    // Check for Dark Katana opportunity
    if (inArray(weapons, WEAPON_DARK_KATANA) && enemyDistance == 1) {
        // Dark Katana damage scales with strength: BaseDamage * (1 + Strength/100)

        var mySTR = getStrength();

        var darkKatanaDamage = 99 * (1 + mySTR / 100);

        var darkKatanaSelfDmg = 44 * (1 + mySTR / 100);
        
        if (myHP > darkKatanaSelfDmg * 3) { // Safe health threshold
            if (debugEnabled && canSpendOps(1000)) {
                if (debugEnabled && canSpendOps(1000)) {
		debugLog("Dark Katana ready: " + round(darkKatanaDamage) + " damage per hit!");
                }
            }
            
            switchToWeaponIfNeeded(WEAPON_DARK_KATANA);

            var katanaUses = min(floor(myTP / getWeaponCost(WEAPON_DARK_KATANA)), 3);
            
            for (var k = 0; k < katanaUses; k++) {
                var result = useWeapon(enemy);
                if (result == USE_CRITICAL) {
                    if (debugEnabled && canSpendOps(1000)) {
                        if (debugEnabled && canSpendOps(1000)) {
		debugLog("CRITICAL Dark Katana strike!");
                        }
                    }
                }
            }
            
            if (debugEnabled && canSpendOps(1000)) {
                if (debugEnabled && canSpendOps(1000)) {
		debugLog("Dark Katana burst: " + katanaUses + " strikes landed");
                }
            }
            
            if (myTP >= 4) executeDefensive();
            return true;
        }
    }
    
    // Standard close combat
    if (debugEnabled && canSpendOps(1000)) {
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Exploiting close range - full attack!");
        }
    }
    executeAttack();
    
    // Stay in close range if possible
    if (myMP > 0 && enemyDistance > 1) {

        var closeCells = getReachableCells(myCell, myMP);
        for (var i = 0; i < count(closeCells); i++) {
            if (getCellDistance(closeCells[i], enemyCell) <= ENEMY_MIN_RANGE) {
                moveToCell(closeCells[i]);
                if (debugEnabled && canSpendOps(1000)) {
                    if (debugEnabled && canSpendOps(1000)) {
		debugLog("Maintaining trap at range " + getCellDistance(getCell(), enemyCell));
                    }
                }
                break;
            }
        }
    }
    
    if (myTP >= 4) executeDefensive();
    return true;
}

// Function: handleBazookaRange
// Handle being in dangerous bazooka range

function handleBazookaRange() {
    if (myMP >= 3) {
        if (debugEnabled && canSpendOps(1000)) {
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("Evading Bazooka range!");
            }
        }
        
        // Decide: rush in or back out?
        if (myHP > myMaxHP * 0.6 && canReachDistance(1, myMP)) {
            if (debugEnabled && canSpendOps(1000)) {
                if (debugEnabled && canSpendOps(1000)) {
		debugLog("Rushing to close combat!");
                }
            }
            // Move closer for melee range
            var meleePosition = findBestAttackPosition(getWeapons());
            if (meleePosition != null) {
                moveToCell(meleePosition);
            }
        } else {
            if (debugEnabled && canSpendOps(1000)) {
                if (debugEnabled && canSpendOps(1000)) {
		debugLog("Retreating from Bazooka range!");
                }
            }
            // Move to safer range
            var safePosition = findBestAttackPosition(getWeapons());
            if (safePosition != null) {
                moveToCell(safePosition);
            }
        }
    }
    
    executeAttack();
    if (myTP >= 4) executeDefensive();
    return true;
}

// Function: executeHighThreatStrategy
// Execute strategy when under high threat

function executeHighThreatStrategy(threatRatio, potentialLifeSteal, willAttackThisTurn) {
    if (debugEnabled && canSpendOps(1000)) {
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("High threat mode - KITING - ratio=" + threatRatio + 
                " (lifesteal=" + potentialLifeSteal + ", willAttack=" + willAttackThisTurn + ")");
        }
    }
    
    // KITE: Attack FIRST while in range, THEN flee!
    if (willAttackThisTurn) {
        if (debugEnabled && canSpendOps(1000)) {
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("Kiting - attacking BEFORE retreating");
            }
        }
        executeAttack();
        
        // FLEE after attacking
        if (myMP > 0 && enemyDistance < 9) {
            // Move to optimal rifle range
            var riflePosition = findBestAttackPosition(getWeapons());
            if (riflePosition != null) {
                moveToCell(riflePosition);
            }
            // Bonus attack from new position if we have TP and can hit
            if (myTP >= 5 && getCellDistance(getCell(), getCell(enemy)) <= 8) {
                if (debugEnabled && canSpendOps(1000)) {
                    if (debugEnabled && canSpendOps(1000)) {
		debugLog("Kiting - bonus attack from new position");
                    }
                }
                executeAttack();
            }
        }
    } else {
        // Just flee if we can't attack effectively
        if (myMP > 0) {
            // Move to optimal rifle range
            var riflePosition = findBestAttackPosition(getWeapons());
            if (riflePosition != null) {
                moveToCell(riflePosition);
            }
        }
    }
    
    if (myTP >= 4) executeDefensive();
    return true;
}

// Function: executeStandardStrategy
// Execute standard combat strategy

function executeStandardStrategy(threatRatio) {
    if (debugEnabled && canSpendOps(1000)) {
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Standard mode - ratio=" + threatRatio);
        }
    }
    
    // Check hit cells for positioning
    if (debugEnabled && canSpendOps(1000)) {
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Checking hit cells for turn " + turn);
        }
    }
    

    var allHitCells = [];

    var reachableHitCells = [];
    
    if (turn <= 8 && canSpendOps(2000000)) {
        if (debugEnabled && canSpendOps(1000)) {
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("Turn " + turn + " - skip complex hit detection");
            }
        }
    } else {
        if (debugEnabled && canSpendOps(1000)) {
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("Calling findHitCells for standard detection...");
            }
        }
        allHitCells = findHitCells();
        if (debugEnabled && canSpendOps(1000)) {
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("Found " + count(allHitCells) + " hit cells");
            }
        }
        
        if (debugEnabled && canSpendOps(1000)) {
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("Calling findReachableHitCells...");
            }
        }
        reachableHitCells = findReachableHitCells(allHitCells);
        if (debugEnabled && canSpendOps(1000)) {
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("Found " + count(reachableHitCells) + " reachable hit cells");
            }
        }
    }
    
    if (turn <= 8) {
        if (debugEnabled && canSpendOps(1000)) {
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("Turn " + turn + " - simplified hit detection");
            }
        }
        // Simple hit detection for early turns
        if (enemyDistance <= 10 && hasLOS(myCell, enemyCell)) {
            reachableHitCells = [[myCell, WEAPON_RIFLE, 150]]; // Simplified
        }
    }
    
    return executeStandardCombat(reachableHitCells);
}

// Function: executeStandardCombat
// Execute standard combat based on hit cells

function executeStandardCombat(reachableHitCells) {
    if (count(reachableHitCells) > 0) {
        if (debugEnabled && canSpendOps(1000)) {
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("Have " + count(reachableHitCells) + " reachable hit cells - ATTACKING!");
            }
        }
        executeAttack();
        if (myTP >= 4) executeDefensive();
    } else {
        if (debugEnabled && canSpendOps(1000)) {
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("No reachable hit cells, need to move into weapon range");
            }
        }
        
        // Move toward enemy for attack range
        if (myMP > 0) {
            var bestStep = findBestAttackPosition(getWeapons());
            if (bestStep != null && bestStep != myCell) {
                if (debugEnabled && canSpendOps(1000)) {
                    if (debugEnabled && canSpendOps(1000)) {
		debugLog("Moving to cell for attack range");
                    }
                }
                moveToCell(bestStep);
            } else {
                var step = bestApproachStep(enemyCell);
                if (step != myCell) {
                    if (debugEnabled && canSpendOps(1000)) {
                        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Moving to approach step " + step);
                        }
                    }
                    moveToCell(step);
                }
            }
            
            // Update position after movement
            myCell = getCell();
            myMP = getMP();
            enemyDistance = getCellDistance(myCell, enemyCell);
        }
        
        // Attack after positioning
        if (enemyDistance <= 10) {
            if (debugEnabled && canSpendOps(1000)) {
                if (debugEnabled && canSpendOps(1000)) {
		debugLog("In harassment range " + enemyDistance + " - attacking!");
                }
            }
            executeAttack();
        } else if (enemyDistance <= 12 && myMP > 0) {
            if (debugEnabled && canSpendOps(1000)) {
                if (debugEnabled && canSpendOps(1000)) {
		debugLog("Near harassment range - approaching to attack");
                }
            }
            moveToward(enemy, min(2, myMP));
            executeAttack();
        } else {
            if (debugEnabled && canSpendOps(1000)) {
                if (debugEnabled && canSpendOps(1000)) {
		debugLog("Far approach - using shields first");
                }
            }
            if (myTP >= 4) executeDefensive();
        }
    }
    
    return true;
}