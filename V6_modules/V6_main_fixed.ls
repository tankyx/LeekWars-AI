// ===================================================================
// VIRUS LEEK v6.0 - MODULAR WIS-TANK BUILD WITH EID POSITIONING
// ===================================================================
// Modularized version preserving ALL V5 features
// Uses LeekScript's include() for better organization and maintainability

// === INCLUDE MODULES ===

// CORE modules
include("6.0/V6/core/globals");
include("6.0/V6/core/state_management");
include("6.0/V6/core/operations");

// UTILS modules
include("6.0/V6/utils/debug");
include("6.0/V6/utils/helpers");
include("6.0/V6/utils/cache");
include("6.0/V6/utils/constants");

// MOVEMENT modules
include("6.0/V6/movement/distance");
include("6.0/V6/movement/line_of_sight");
include("6.0/V6/movement/pathfinding");
include("6.0/V6/movement/reachability");
include("6.0/V6/movement/range_finding");

// COMBAT modules
include("6.0/V6/combat/damage_calculation");
include("6.0/V6/combat/weapon_analysis");
include("6.0/V6/combat/weapon_matrix");

// AI modules
include("6.0/V6/ai/evaluation");
include("6.0/V6/ai/eid_system");
include("6.0/V6/ai/influence_map");

// STRATEGY modules
include("6.0/V6/strategy/enemy_profiling");
include("6.0/V6/strategy/phase_management");
include("6.0/V6/strategy/pattern_learning");

// COMBAT modules
include("6.0/V6/combat/chip_management");
include("6.0/V6/combat/weapon_management");
include("6.0/V6/combat/aoe_tactics");
include("6.0/V6/combat/lightninger_tactics");
include("6.0/V6/combat/grenade_tactics");
include("6.0/V6/combat/erosion");

// MOVEMENT modules
include("6.0/V6/movement/positioning");
include("6.0/V6/movement/teleportation");

// STRATEGY modules
include("6.0/V6/strategy/ensemble_system");
include("6.0/V6/strategy/tactical_decisions");
include("6.0/V6/strategy/bait_tactics");
include("6.0/V6/strategy/kill_calculations");
include("6.0/V6/strategy/anti_tank");

// AI modules
include("6.0/V6/ai/decision_making");
include("6.0/V6/ai/visualization");

// COMBAT modules
include("6.0/V6/combat/execute_combat");

// CORE modules
include("6.0/V6/core/initialization");

// === MAIN EXECUTION ===

// Initialize the system
initialize();

// Main combat loop
if (enemy != null) {
    // Make tactical decision based on operational mode
    if (isInPanicMode()) {
        simplifiedCombat();
    } else {
        makeDecision();
    }
} else {
    debugLog('No enemy found');
}

// Visualize battle state if debug enabled
if (debugEnabled && !isInPanicMode()) {
    visualizeEID();
}