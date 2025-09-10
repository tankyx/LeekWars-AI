// ===================================================================
// VIRUS LEEK v6.1 - REFACTORED MODULAR WIS-TANK BUILD WITH EID POSITIONING
// ===================================================================
// Refactored version with improved modularity and performance
// Uses enhanced modular architecture for better maintainability

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
include("strategy/multi_enemy");

// COMBAT modules - refactored
include("combat/chip_management");
include("combat/weapon_management");
include("combat/aoe_tactics");
include("combat/m_laser_tactics");
include("combat/grenade_tactics");
include("combat/erosion");
include("combat/damage_sequences");
include("combat/b_laser_tactics");

// MOVEMENT modules
include("movement/positioning");
include("movement/teleportation");

// STRATEGY modules
include("strategy/ensemble_system");
include("strategy/tactical_decisions");
include("strategy/bait_tactics");
include("strategy/kill_calculations");
include("strategy/anti_tank");

// AI modules - refactored
include("ai/emergency_decisions");
include("ai/tactical_decisions_ai");  // Renamed to avoid conflict
include("ai/combat_decisions");
include("ai/decision_making_refactored");
include("ai/visualization");

// COMBAT modules - refactored
include("combat/weapon_selection");
include("combat/positioning_logic");
include("combat/attack_execution");
include("combat/execute_combat_refactored");

// CORE modules
include("core/initialization");

// === MAIN EXECUTION ===

debugLogCheap("=== V6.1 REFACTORED MAIN STARTING ===");

// Initialize the system
initialize();
debugLogCheap("Initialized - enemy=" + enemy);

// Main combat loop
if (enemy != null) {
    // Make tactical decision based on operational mode
    if (isInPanicMode()) {
        debugLogCheap("Entering PANIC mode");
        simplifiedCombat();
    } else if (turn == 1) {
        // Turn 1 special handling - early game sequence
        debugLogCheap("Turn 1 - executing early game sequence");
        executeEarlyGameSequence();
    } else {
        // Turn 2+ uses refactored decision making
        debugLogCheap("Turn " + turn + " - entering refactored combat mode");
        makeDecision(); // This now uses the refactored decision_making_refactored.ls
        
        // Fallback in case makeDecision() doesn't execute properly
        if (myTP >= 3 && enemy != null) {
            debugLogConditional("Ensuring combat execution for turn " + turn, 2000);
            executeAttack(); // This now uses execute_combat_refactored.ls
            if (myTP >= 4) executeDefensive();
            
            // REPOSITION after combat if we have MP left
            if (getMP() > 0 && enemy != null && getLife(enemy) > 0) {
                debugLogConditional("Post-combat repositioning with " + getMP() + " MP", 2000);
                repositionDefensive();
            }
        }
    }
} else {
    debugLogCheap('No enemy found');
}

debugLogCheap("Main combat loop complete");

// Visualize battle state if debug enabled - using optimized visualization
if (debugEnabled && !isInPanicMode()) {
    debugVisualization(function() {
        debugLogExpensive("Final visualization...");
        visualizeEID();
        debugLogExpensive("Final visualization complete");
    });
}

debugLogCheap("V6_main_refactored.ls complete - end of turn " + turn);