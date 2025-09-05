// Minimal test to check if includes work

say("Test 1: Script started");

// Try to include globals
include("6.0/V6/core/globals");

say("Test 2: After globals include");

// Check if a global variable exists
if (typeof COLOR_SAFE != "undefined") {
    say("Test 3: Globals loaded - COLOR_SAFE exists");
} else {
    say("Test 3: ERROR - Globals not loaded");
}

// Try to include initialization
include("6.0/V6/core/initialization");

say("Test 4: After initialization include");

// Check if initialize function exists
if (typeof initialize != "undefined") {
    say("Test 5: Function exists");
    initialize();
    say("Test 6: Initialize ran - enemy=" + enemy);
} else {
    say("Test 5: ERROR - initialize function not found");
}

say("Test complete");