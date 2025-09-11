// V6 Module: core/state_management.ls
// Bitwise state management
// Auto-generated from V5.0 script

// Function: setState
function setState(flags) {
    combatState = combatState | flags;
}

// Clear state flags

// Function: clearState
function clearState(flags) {
    combatState = combatState & ~flags;
}

// Check if all specified flags are set

// Function: hasState
function hasState(flags) {
    return (combatState & flags) == flags;
}

// Check if any of the specified flags are set

// Function: hasAnyState
function hasAnyState(flags) {
    return (combatState & flags) != 0;
}

// Toggle state flags

// Function: toggleState
function toggleState(flags) {
    combatState = combatState ^ flags;
}

// Update all combat states at once

// Function: updateCombatState
function updateCombatState() {
    // Clear all states
    combatState = 0;
    
    // Movement state
    if (myMP > 0) {
        setState(STATE_CAN_MOVE);
    }
    
    // Attack state
    if (myTP >= 3 && enemy != null) {
        setState(STATE_CAN_ATTACK);
        
        var dist = getCellDistance(myCell, enemyCell);
        if (dist <= 10) {
            setState(STATE_IN_RANGE);
        }
        if (lineOfSight(myCell, enemyCell, enemy)) {
            setState(STATE_HAS_LOS);
        }
    }
    
    // Buff states from effects
    var myEffects = getEffects(getEntity());
    if (myEffects != null) {
        for (var i = 0; i < count(myEffects); i++) {
            var effectType = myEffects[i][0];
            
            if (effectType == EFFECT_BUFF_STRENGTH || 
                effectType == EFFECT_BUFF_AGILITY ||
                effectType == EFFECT_BUFF_WISDOM ||
                effectType == EFFECT_BUFF_RESISTANCE ||
                effectType == EFFECT_BUFF_TP ||
                effectType == EFFECT_BUFF_MP) {
                setState(STATE_IS_BUFFED);
            }
            
            if (effectType == EFFECT_ABSOLUTE_SHIELD ||
                effectType == EFFECT_RELATIVE_SHIELD) {
                // Note: STEALTH shield effects don't exist in LeekWars v4
                setState(STATE_IS_SHIELDED);
            }
            
            if (effectType == EFFECT_POISON) {
                setState(STATE_IS_POISONED);
            }
            
            if (effectType == EFFECT_HEAL) {
                setState(STATE_HAS_HOT);
            }
            
            // Liberation effect doesn't exist as a separate effect type
            // It's handled through chip usage
        }
    }
    
    // Enemy states
    if (enemy != null) {
        var enemyEffects = getEffects(enemy);
        if (enemyEffects != null && count(enemyEffects) > 0) {
            for (var i = 0; i < count(enemyEffects); i++) {
                var effectType = enemyEffects[i][0];
                
                if (effectType == EFFECT_BUFF_STRENGTH ||
                    effectType == EFFECT_BUFF_AGILITY ||
                    effectType == EFFECT_BUFF_WISDOM ||
                    effectType == EFFECT_BUFF_RESISTANCE) {
                    setState(STATE_ENEMY_BUFFED);
                }
                
                if (effectType == EFFECT_ABSOLUTE_SHIELD ||
                    effectType == EFFECT_RELATIVE_SHIELD) {
                    setState(STATE_ENEMY_SHIELDED);
                }
            }
        }
    }
    
    // Critical health state
    if (myHP < myMaxHP * 0.3) {
        setState(STATE_IS_CRITICAL);
    }
    
    // Combat readiness states
    if (enemy != null) {
        var pkill = calculatePkill(enemyHP, myTP);
        if (pkill >= PKILL_COMMIT) {
            setState(STATE_PKILL_READY);
        }
        
        // Check if we can setup for next turn kill
        var nextTurnDamage = calculateDamageFrom(myCell);
        if (nextTurnDamage >= enemyHP * 0.8) {
            setState(STATE_SETUP_KILL);
        }
    }
    
    // Panic mode check
    if (getOperationLevel() == "PANIC") {
        setState(STATE_PANIC_MODE);
    }
    
    // Turn 1 buff opportunity
    if (turn <= 2 && !hasState(STATE_IS_BUFFED)) {
        setState(STATE_TURN_1_BUFFS);
    }
}

// Ultra-fast decision making with bitwise checks

// Function: getStateDescription
function getStateDescription() {
    var states = [];
    
    if (hasState(STATE_CAN_MOVE)) push(states, "CAN_MOVE");
    if (hasState(STATE_CAN_ATTACK)) push(states, "CAN_ATTACK");
    if (hasState(STATE_HAS_LOS)) push(states, "HAS_LOS");
    if (hasState(STATE_IN_RANGE)) push(states, "IN_RANGE");
    if (hasState(STATE_IS_BUFFED)) push(states, "BUFFED");
    if (hasState(STATE_IS_SHIELDED)) push(states, "SHIELDED");
    if (hasState(STATE_IS_POISONED)) push(states, "POISONED");
    if (hasState(STATE_IS_CRITICAL)) push(states, "CRITICAL");
    if (hasState(STATE_ENEMY_BUFFED)) push(states, "ENEMY_BUFFED");
    if (hasState(STATE_ENEMY_SHIELDED)) push(states, "ENEMY_SHIELDED");
    if (hasState(STATE_PKILL_READY)) push(states, "PKILL_READY");
    if (hasState(STATE_PANIC_MODE)) push(states, "PANIC");
    
    return states;
}

// === GAME PHASE RECOGNITION ===
