// V6 Module: utils/debug.ls
// Debug logging with performance optimization
// Refactored for better operation management

// Function: debugLog
// Standard debug logging with operation check
function debugLog(message) {
    if (debugEnabled && turn <= 20 && canSpendOps(1000)) {  // Operation check added
        debugE("[Turn " + turn + "] " + message);
    }
}

// Function: debugLogCheap
// Cheap debug logging for critical messages (minimal operation cost)
function debugLogCheap(message) {
    if (debugEnabled && turn <= 15) {  // No operation check for critical messages
        debugE("[Turn " + turn + "] " + message);
    }
}

// Function: debugLogExpensive
// Expensive debug logging for detailed analysis (higher operation cost)
function debugLogExpensive(message) {
    if (debugEnabled && turn <= 10 && canSpendOps(5000)) {  // Higher operation requirement
        debugE("[Turn " + turn + "] [DETAILED] " + message);
    }
}

// Function: debugLogConditional
// Conditional debug logging with custom operation cost
function debugLogConditional(message, operationCost) {
    if (debugEnabled && turn <= 20 && canSpendOps(operationCost)) {
        debugE("[Turn " + turn + "] " + message);
    }
}

// Function: debugVisualization
// Debug visualization with heavy operation checking
function debugVisualization(visualizationFunc) {
    if (debugEnabled && turn <= 8 && canSpendOps(50000)) {
        visualizationFunc();
    }
}