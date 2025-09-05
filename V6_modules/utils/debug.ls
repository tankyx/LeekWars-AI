// V6 Module: utils/debug.ls
// Debug logging
// Auto-generated from V5.0 script

// Function: debugLog
function debugLog(message) {
    if (debugEnabled && turn <= 20) {  // Extended to turn 20
        debugE("[Turn " + turn + "] " + message);
    }
}

