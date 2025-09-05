// ===================================================================
// VIRUS LEEK v6.0 - MODULAR WIS-TANK BUILD WITH EID POSITIONING
// ===================================================================
// Modularized version preserving ALL V5 features
// Uses LeekScript's include() for better organization and maintainability

// === INCLUDE MODULES ===

// CORE modules
include("core/globals");
include("core/state_management");
include("core/operations");

// UTILS modules
include("utils/debug");
include("utils/helpers");
include("utils/cache");
include("utils/constants");

// MOVEMENT modules
include("movement/distance");
include("movement/line_of_sight");
include("movement/pathfinding");
include("movement/reachability");
include("movement/range_finding");

// COMBAT modules
include("combat/damage_calculation");
include("combat/weapon_analysis");
include("combat/weapon_matrix");

// AI modules
include("ai/evaluation");
include("ai/eid_system");
include("ai/influence_map");

// STRATEGY modules
include("strategy/enemy_profiling");
include("strategy/phase_management");
include("strategy/pattern_learning");

// COMBAT modules
include("combat/chip_management");
include("combat/weapon_management");
include("combat/aoe_tactics");
include("combat/lightninger_tactics");
include("combat/grenade_tactics");
include("combat/erosion");

// MOVEMENT modules
include("movement/positioning");
include("movement/teleportation");

// STRATEGY modules
include("strategy/ensemble_system");
include("strategy/tactical_decisions");
include("strategy/bait_tactics");
include("strategy/kill_calculations");
include("strategy/anti_tank");

// AI modules
include("ai/decision_making");
include("ai/visualization");

// COMBAT modules
include("combat/execute_combat");

// CORE modules
include("core/initialization");

// === MAIN EXECUTION ===

debug("=== V6 MAIN STARTING ===");
// say("V6 Starting - Turn " + getTurn()); // Removed - costs 1 TP

// Initialize the system
initialize();
debug("Initialized - enemy=" + enemy);
// say("Enemy found: " + getName(enemy)); // Removed - costs 1 TP

// Main combat loop
if (enemy != null) {
    // Make tactical decision based on operational mode
    if (isInPanicMode()) {
        debugLog("Entering PANIC mode");
        simplifiedCombat();
    } else if (turn == 1) {
        // Turn 1 special handling - early game sequence
        debugLog("Turn 1 - executing early game sequence");
        executeEarlyGameSequence();
    } else {
        // Turn 2+ uses standard decision making
        debugLog("Entering normal combat mode");
        makeDecision();
        debugLog("Returned from makeDecision()");
    }
} else {
    debugLog('No enemy found');
}

debugLog("Main combat loop complete");

// Visualize battle state if debug enabled
if (debugEnabled && !isInPanicMode()) {
    debugLog("Final visualization...");
    visualizeEID();
    debugLog("Final visualization complete");
}

debugLog("V6_main.ls complete - end of turn " + turn);