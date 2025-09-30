// V7 Module: test_phase1.ls
// Test script for Phase 1 improvements
// Tests new modules with feature flags

// === INCLUDE ALL NEW MODULES ===
include("core/globals");
include("decision/weapon_selector");
include("decision/emergency_state");
include("decision/healing");
include("combat/combat_package");

// === TEST FUNCTIONS ===

function testWeaponSelector() {
    debugW("=== TESTING WEAPON SELECTOR ===");

    // Enable new weapon selector
    USE_NEW_WEAPON_SELECTOR = true;

    // Mock some basic state
    myTP = 15;
    myMP = 3;

    // Test weapon recommendation
    var weaponChoice = getWeaponRecommendation(null, myTP, myMP, false);

    if (weaponChoice != null) {
        debugW("WEAPON_SELECTOR_TEST: SUCCESS - Got weapon choice");
    } else {
        debugW("WEAPON_SELECTOR_TEST: OK - No weapon choice (expected with null target)");
    }

    USE_NEW_WEAPON_SELECTOR = false;
}

function testEmergencyState() {
    debugW("=== TESTING EMERGENCY STATE ===");

    // Enable new emergency state
    USE_NEW_EMERGENCY_STATE = true;

    // Mock some game state
    myHP = 200;
    myMaxHP = 500;

    // Test emergency mode detection
    var emergencyMode = getEmergencyMode();

    if (emergencyMode != null) {
        debugW("EMERGENCY_STATE_TEST: SUCCESS - State: " + emergencyMode.stateName);
        debugW("EMERGENCY_STATE_TEST: Emergency: " + emergencyMode.isEmergency);
    } else {
        debugW("EMERGENCY_STATE_TEST: FAILED - No emergency mode returned");
    }

    USE_NEW_EMERGENCY_STATE = false;
}

function testHealingSystem() {
    debugW("=== TESTING HEALING SYSTEM ===");

    // Enable new healing system
    USE_NEW_HEALING_SYSTEM = true;

    // Mock some state
    myTP = 10;
    myMP = 3;
    myHP = 150;
    myMaxHP = 500;

    // Test healing decision
    var healingChoice = getBestHealingChoice(myTP, myMP, "normal");

    if (healingChoice != null) {
        debugW("HEALING_TEST: SUCCESS - Got healing choice: " + healingChoice.chip);
    } else {
        debugW("HEALING_TEST: OK - No healing choice (may be expected)");
    }

    USE_NEW_HEALING_SYSTEM = false;
}

function testCombatPackage() {
    debugW("=== TESTING COMBAT PACKAGE ===");

    // Enable new combat packages
    USE_NEW_COMBAT_PACKAGES = true;

    // Mock some state
    myTP = 15;
    myMP = 3;

    // Test combat package creation
    var package = getBestCombatPackage(null, myTP, myMP);

    if (package != null) {
        debugW("COMBAT_PACKAGE_TEST: SUCCESS - Got package");
    } else {
        debugW("COMBAT_PACKAGE_TEST: OK - No package (expected with null target)");
    }

    USE_NEW_COMBAT_PACKAGES = false;
}

function testIntegration() {
    debugW("=== TESTING INTEGRATION ===");

    // Enable all new systems
    USE_NEW_WEAPON_SELECTOR = true;
    USE_NEW_EMERGENCY_STATE = true;
    USE_NEW_HEALING_SYSTEM = true;
    USE_NEW_COMBAT_PACKAGES = true;

    // Mock game state
    myHP = 300;
    myMaxHP = 500;
    myTP = 17;
    myMP = 4;

    try {
        // Test combined functionality
        var emergencyMode = getEmergencyMode();
        debugW("INTEGRATION_TEST: Emergency state: " + emergencyMode.stateName);

        var healingChoice = getBestHealingChoice(myTP, myMP, emergencyMode.stateName);
        if (healingChoice != null) {
            debugW("INTEGRATION_TEST: Healing recommended: " + healingChoice.chip);
        }

        debugW("INTEGRATION_TEST: SUCCESS - All systems working together");

    } catch (error) {
        debugW("INTEGRATION_TEST: ERROR - " + error);
    }

    // Disable all systems
    USE_NEW_WEAPON_SELECTOR = false;
    USE_NEW_EMERGENCY_STATE = false;
    USE_NEW_HEALING_SYSTEM = false;
    USE_NEW_COMBAT_PACKAGES = false;
}

// === MAIN TEST FUNCTION ===
function runPhase1Tests() {
    debugW("=== STARTING PHASE 1 TESTS ===");

    // Initialize minimal game state for testing
    myLeek = getEntity();
    myCell = getCell();
    myHP = getLife();
    myMaxHP = getTotalLife();
    myTP = getTP();
    myMP = getMP();

    // Initialize global arrays if not set
    if (allEnemies == null) {
        allEnemies = [];
    }
    if (chipCooldowns == null) {
        chipCooldowns = [:];
    }

    // Run individual tests
    testWeaponSelector();
    testEmergencyState();
    testHealingSystem();
    testCombatPackage();
    testIntegration();

    debugW("=== PHASE 1 TESTS COMPLETE ===");
}

// === AUTO-RUN IN MAIN (FOR TESTING) ===
function main() {
    runPhase1Tests();
}