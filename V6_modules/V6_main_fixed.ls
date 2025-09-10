// ===================================================================
// VIRUS LEEK v6.0 - MODULAR WIS-TANK BUILD WITH EID POSITIONING  
// ===================================================================
// Modularized version preserving ALL V5 features
// Uses LeekScript's include() for better organization and maintainability

// === INCLUDE MODULES ===

// CORE modules
// === INCLUDE MODULES ===
// Optimized include order to resolve compilation dependencies

// CORE modules
include("core/globals");
include("core/state_management");
include("core/operations");

// UTILS modules
include("utils/constants");
include("utils/cache");
include("utils/debug");
include("utils/helpers");

// MOVEMENT modules
include("movement/distance");
include("movement/line_of_sight");
include("movement/pathfinding");
include("movement/reachability");
include("movement/range_finding");
include("movement/positioning");
include("movement/teleportation");

// COMBAT modules
include("combat/damage_calculation");
include("combat/weapon_analysis");
include("combat/weapon_matrix");
include("combat/chip_management");
include("combat/weapon_management");
include("combat/aoe_tactics");
include("combat/m_laser_tactics");
include("combat/grenade_tactics");
include("combat/erosion");
include("combat/damage_sequences");
include("combat/b_laser_tactics");
include("combat/weapon_selection");
include("combat/positioning_logic");
include("combat/attack_execution");
include("combat/execute_combat_refactored");

// AI modules
include("ai/evaluation");
include("ai/eid_system");
include("ai/influence_map");
include("ai/emergency_decisions");
include("ai/tactical_decisions_ai");
include("ai/combat_decisions");
include("ai/decision_making_refactored");
include("ai/visualization");

// STRATEGY modules
include("strategy/enemy_profiling");
include("strategy/phase_management");
include("strategy/pattern_learning");
include("strategy/multi_enemy");
include("strategy/ensemble_system");
include("strategy/tactical_decisions");
include("strategy/bait_tactics");
include("strategy/kill_calculations");
include("strategy/anti_tank");

// INITIALIZATION modules
include("core/initialization");


// === MAIN EXECUTION ===

debug("=== V6 MAIN STARTING ===");

// Initialize the system
initialize();
debug("Initialized - enemy=" + enemy);

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
        // Turn 2+ uses standard decision making - ensure proper execution
        debugLog("Turn " + turn + " - entering normal combat mode");
        makeDecision();
        // Fallback in case makeDecision() doesn't execute properly
        if (myTP >= 3 && enemy != null) {
            debugLog("Ensuring combat execution for turn " + turn);
            executeAttack();
            if (myTP >= 4) executeDefensive();
            
            // REPOSITION after combat if we have MP left
            if (getMP() > 0 && enemy != null && getLife(enemy) > 0) {
                debugLog("Post-combat repositioning with " + getMP() + " MP");
                repositionDefensive();
            }
        }
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