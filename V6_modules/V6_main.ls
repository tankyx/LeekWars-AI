// ===================================================================
// VIRUS LEEK v6.0 - MODULAR WIS-TANK BUILD WITH EID POSITIONING  
// ===================================================================
// Modularized version preserving ALL V5 features
// Uses LeekScript's include() for better organization and maintainability

// === INCLUDE MODULES ===

// CORE modules - globals first, initialization AFTER dependencies
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

// STRATEGY modules - multi_enemy FIRST (needed for initialization)
include("strategy/multi_enemy");
include("strategy/enemy_profiling");
include("strategy/phase_management");
include("strategy/pattern_learning");

// COMBAT modules
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

// AI modules - using refactored modules
include("ai/emergency_decisions");
include("ai/tactical_decisions_ai");
include("ai/combat_decisions");
include("ai/deep_analysis");
include("ai/decision_making_refactored");
include("ai/visualization");

// COMBAT modules - using refactored modules
include("combat/weapon_selection");
include("combat/positioning_logic");
include("combat/attack_execution");
include("combat/execute_combat_refactored");

// CORE modules - initialization AFTER all dependencies are loaded
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
    } else if (turn == 2 && shouldUseTurn2ComboSequence()) {
        // Turn 2 combo sequence for high damage opponents
        debugLog("Turn 2 - executing combo sequence");
        executeTurn2ComboSequence();
    } else {
        // Turn 2+ uses standard decision making - ensure proper execution
        debugLog("Turn " + turn + " - entering normal combat mode");
        makeDecision();
        // Fallback in case makeDecision() doesn't execute properly
        if (myTP >= 3 && enemy != null) {
            debugLog("Ensuring combat execution for turn " + turn);
            executeAttack();
            if (myTP >= 4) executeDefensive();
        }
        
        // REPOSITION after combat if we have MP left
        if (getMP() > 0 && enemy != null && getLife(enemy) > 0) {
            debugLog("Post-combat repositioning with " + getMP() + " MP");
            repositionDefensive();
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
