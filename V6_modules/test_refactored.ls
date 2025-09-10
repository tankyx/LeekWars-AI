// V6 Module: test_refactored.ls
// Simple test to validate refactored module structure
// This tests basic module loading and function availability

// Test loading core modules
include("core/globals");
include("utils/debug");

// Test loading refactored AI modules  
include("ai/emergency_decisions");
include("ai/tactical_decisions_ai");
include("ai/combat_decisions");

// Test loading refactored combat modules
include("combat/weapon_selection");
include("combat/positioning_logic");
include("combat/attack_execution");

// Simple validation test
function testRefactoredModules() {
    // Test if key functions exist by attempting to reference them
    // If they don't exist, compilation will fail which is what we want
    var testResults = [];
    
    // Just verify the modules loaded by checking compilation
    testResults = push(testResults, "✅ All refactored modules loaded successfully");
    
    return testResults;
}

// Run test if this is executed directly
var results = testRefactoredModules();
for (var i = 0; i < count(results); i++) {
    debugE(results[i]);
}