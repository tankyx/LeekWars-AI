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
    var percentUsed = opsUsed / 7000000.0;  // 7M total ops
    var previousMode = OPERATIONAL_MODE;
    
    // Smooth transitions based on percentage
    if (percentUsed < 0.70) {
        OPERATIONAL_MODE = "OPTIMAL";
    } else if (percentUsed < 0.85) {
        OPERATIONAL_MODE = "EFFICIENT";
    } else if (percentUsed < 0.95) {
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
    return getOperationalMode() == "PANIC";
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

