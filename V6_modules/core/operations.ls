// V6 Module: core/operations.ls
// Operations budget management
// Auto-generated from V5.0 script

// Function: canSpendOps
function canSpendOps(amount) {
    var remaining = getMaxOperations() - getOperations();
    return remaining >= (amount + OPS_SAFETY_RESERVE);
}


// Function: getOperationalMode
function getOperationalMode() {
    var opsUsed = getOperations();
    var percentUsed = opsUsed / maxOperations;  // Use dynamic operation budget
    var previousMode = OPERATIONAL_MODE;
    
    // Use operations aggressively based on actual core count!
    if (percentUsed < 0.90) {  // Use up to 90% ops freely
        OPERATIONAL_MODE = "OPTIMAL";
    } else if (percentUsed < 0.95) {  // 90%-95% ops
        OPERATIONAL_MODE = "EFFICIENT";
    } else if (percentUsed < 0.98) {  // 95%-98% ops
        OPERATIONAL_MODE = "SURVIVAL";
    } else {
        OPERATIONAL_MODE = "PANIC";
    }
    
    // Hysteresis to prevent oscillation
    if (previousMode != OPERATIONAL_MODE) {
        // Don't downgrade too eagerly
        if (previousMode == "EFFICIENT" && OPERATIONAL_MODE == "OPTIMAL") {
            if (percentUsed > 0.65) {
                OPERATIONAL_MODE = "EFFICIENT";  // Stay in efficient
            }
        } else if (previousMode == "SURVIVAL" && OPERATIONAL_MODE == "EFFICIENT") {
            if (percentUsed > 0.82) {
                OPERATIONAL_MODE = "SURVIVAL";  // Stay in survival
            }
        }
        
        // Track mode change if it actually changed
        if (OPERATIONAL_MODE != previousMode) {
            var transition = [:];
            transition["turn"] = turn;
            transition["ops"] = opsUsed;
            transition["from"] = previousMode;
            transition["to"] = OPERATIONAL_MODE;
            push(MODE_HISTORY, transition);
            
            if (turn <= 10) {
                debugLog("Mode transition: " + previousMode + " → " + OPERATIONAL_MODE + 
                        " at " + round(percentUsed * 100) + "% ops");
            }
        }
    }
    
    LAST_MODE_CHECK_OPS = opsUsed;
    return OPERATIONAL_MODE;
}

// Backwards compatibility

// Function: getOperationLevel
function getOperationLevel() {
    return getOperationalMode();
}


// Function: isInPanicMode
function isInPanicMode() {
    // Panic mode triggers on either operation usage OR very low HP
    if (getOperationalMode() == "PANIC") {
        return true;  // Operation-based panic
    }
    
    // HP-based panic mode (20% HP threshold - only in critical situations)
    if (myHP < myMaxHP * 0.2 && myHP < 500) {
        debugLog("HP PANIC MODE TRIGGERED - HP at " + round(myHP/myMaxHP*100) + "%");
        return true;
    }
    
    return false;
}


// Function: checkOperationCheckpoint
function checkOperationCheckpoint() {
    var mode = getOperationalMode();
    if (mode == "PANIC") {
        debugLog("⚠️ PANIC MODE - Emergency only!");
        return false;
    }
    return true;
}


// Function: shouldUseAlgorithm
function shouldUseAlgorithm(algorithmCost) {
    var mode = getOperationalMode();
    
    if (mode == "OPTIMAL") {
        return true;  // Use all algorithms
    } else if (mode == "EFFICIENT") {
        return algorithmCost < 100000;  // Skip very expensive
    } else if (mode == "SURVIVAL") {
        return algorithmCost < 20000;  // Only cheap algorithms
    } else {  // PANIC
        return algorithmCost < 5000;  // Emergency only
    }
}

