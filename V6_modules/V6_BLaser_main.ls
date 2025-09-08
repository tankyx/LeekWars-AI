// ===================================================================
// V6 B-LASER BUILD - MAIN SCRIPT
// ===================================================================
// STR/WIS Hybrid build with Magnum/Destroyer/B-Laser
// Leverages V6 module infrastructure for EID, positioning, pathfinding
// 6 MP, 13 TP configuration

// === INCLUDE SHARED MODULES ===

// CORE modules - shared infrastructure
include("core/globals");
include("core/state_management");
include("core/operations");

// UTILS modules - shared utilities
include("utils/debug");
include("utils/helpers");
include("utils/cache");
include("utils/constants");

// MOVEMENT modules - leverage existing pathfinding and positioning
include("movement/distance");
include("movement/line_of_sight");
include("movement/pathfinding");
include("movement/reachability");
include("movement/range_finding");

// COMBAT modules - damage calculations and analysis
include("combat/damage_calculation");
include("combat/weapon_analysis");
include("combat/weapon_matrix");

// AI modules - leverage EID and influence systems
include("ai/evaluation");
include("ai/eid_system");
include("ai/influence_map");

// STRATEGY modules - enemy profiling and multi-enemy support
include("strategy/enemy_profiling");
include("strategy/phase_management");
include("strategy/pattern_learning");
include("strategy/multi_enemy");

// COMBAT modules (continued)
include("combat/chip_management");
include("combat/weapon_management");
include("combat/aoe_tactics");
include("combat/grenade_tactics");
include("combat/erosion");
include("combat/damage_sequences");

// MOVEMENT modules (continued)
include("movement/positioning");
include("movement/teleportation");

// STRATEGY modules (continued)
include("strategy/ensemble_system");
include("strategy/tactical_decisions");
include("strategy/bait_tactics");
include("strategy/kill_calculations");
include("strategy/anti_tank");

// AI modules (continued)
include("ai/decision_making");
include("ai/visualization");

// COMBAT modules (continued)
include("combat/execute_combat");

// CORE modules (initialization must come after other modules are loaded)
include("core/initialization");

// === CUSTOM MODULES FOR B-LASER BUILD ===
include("blaser/initialization_blaser");
include("blaser/combat_execution_blaser");

// === MAIN EXECUTION ===

debug("=== V6 B-LASER BUILD STARTING ===");

// Initialize the B-Laser build system
initializeBLaser();
debug("Initialized B-Laser build - enemy=" + enemy);

// Main combat loop
if (enemy != null) {
    // Make tactical decision based on operational mode
    if (isInPanicModeBLaser()) {
        debugLog("Entering PANIC mode (B-Laser)");
        simplifiedCombatBLaser();
    } else if (turn == 1) {
        // Turn 1 special handling - aggressive opening with buffs
        debugLog("Turn 1 - executing B-Laser opening sequence");
        executeEarlyGameBLaser();
    } else {
        // Turn 2+ uses standard decision making with B-Laser adaptations
        debugLog("Turn " + turn + " - B-Laser combat mode");
        makeDecision();
        // Ensure combat execution
        if (myTP >= 2 && enemy != null) {
            executeAttackBLaser();
        }
    }
} else {
    debugLog("No enemy found");
}

// Visualize state (if operations allow)
if (debugEnabled && !isInPanicMode()) {
    debugLog("Final visualization...");
    visualizeEID();
    debugLog("Final visualization complete");
}

debug("=== V6 B-LASER TURN COMPLETE ===");