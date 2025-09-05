// V6 Module: strategy/tactical_decisions.ls
// Quick tactical decisions
// Auto-generated from V5.0 script

// Function: getQuickTacticalDecision
function getQuickTacticalDecision() {
    var myDamage = calculateDamageFrom(myCell);
    var enemyEID = calculateEID(myCell);
    
    // Ultra-simple decision tree
    if (myDamage >= enemyHP) {
        return "KILLSHOT";
    }
    
    if (enemyEID >= myHP * 0.8) {
        return "ESCAPE";
    }
    
    if (myHP < myMaxHP * 0.3) {
        return "HEAL";
    }
    
    if (enemyDistance <= 7 && myDamage > 0) {
        return "ATTACK";
    }
    
    return "POSITION";
}

// Execute quick action for SURVIVAL mode

// Function: executeQuickAction
function executeQuickAction(action) {
    if (action == "KILLSHOT" || action == "ATTACK") {
        executeAttack();
    } else if (action == "ESCAPE") {
        var cells = getReachableCells(myCell, myMP);
        var bestCell = myCell;
        var bestDist = enemyDistance;
        
        // Find cell furthest from enemy (check max 10 cells)
        for (var i = 0; i < min(10, count(cells)); i++) {
            var c = cells[i];
            var d = getCellDistance(c, enemyCell);
            if (d > bestDist) {
                bestCell = c;
                bestDist = d;
            }
        }
        
        if (bestCell != myCell) {
            moveToCell(bestCell);
        }
        executeAttack();
    } else if (action == "HEAL") {
        executeDefensive();  // Use existing defensive function
        executeAttack();
    } else {
        // Default positioning - simple movement logic
        var reach = getReachableCells(myCell, myMP);
        var bestCell = myCell;
        var bestDist = 999;
        
        for (var i = 0; i < min(10, count(reach)); i++) {
            var c = reach[i];
            var d = abs(getCellDistance(c, enemyCell) - optimalAttackRange);
            if (d < bestDist) {
                bestCell = c;
                bestDist = d;
            }
        }
        
        if (bestCell != myCell) {
            moveToCell(bestCell);
        }
        executeAttack();
    }
}


// Function: quickCombatDecision
function quickCombatDecision() {
    updateCombatState();
    
    // Single bitwise check for multiple conditions
    var attackReady = STATE_CAN_ATTACK | STATE_IN_RANGE | STATE_HAS_LOS;
    if (hasState(attackReady)) {
        // Can attack immediately
        if (hasState(STATE_PKILL_READY)) {
            debugLog("Quick decision: Kill shot ready!");
            return "EXECUTE_KILL";
        }
        
        if (hasState(STATE_SETUP_KILL)) {
            debugLog("Quick decision: Setup kill");
            return "SETUP_ATTACK";
        }
        
        return "STANDARD_ATTACK";
    }
    
    // Check critical defensive needs
    if (hasState(STATE_IS_CRITICAL)) {
        if (!hasState(STATE_IS_SHIELDED)) {
            return "EMERGENCY_SHIELD";
        }
        if (hasState(STATE_IS_POISONED)) {
            return "USE_ANTIDOTE";
        }
        return "DEFENSIVE_RETREAT";
    }
    
    // Check buff opportunities
    if (hasState(STATE_TURN_1_BUFFS)) {
        return "APPLY_BUFFS";
    }
    
    // Check movement needs
    if (hasState(STATE_CAN_MOVE) && !hasState(STATE_IN_RANGE)) {
        return "MOVE_TO_RANGE";
    }
    
    // Enemy is buffed/shielded - need to counter
    if (hasState(STATE_ENEMY_BUFFED | STATE_ENEMY_SHIELDED)) {
        if (hasState(STATE_HAS_LIBERATION)) {
            return "USE_LIBERATION";
        }
        return "BURST_DAMAGE";
    }
    
    return "DEFENSIVE";
}

// Get readable state description for debugging
