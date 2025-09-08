// V6 Module: strategy/phase_management.ls
// Game phase management
// Auto-generated from V5.0 script

// Function: determineGamePhase
function determineGamePhase() {
    var previousPhase = GAME_PHASE;
    
    // Calculate phase indicators
    var turnNumber = turn;
    var myHPPercent = myHP / myMaxHP;
    var enemyHPPercent = enemy ? enemyHP / enemyMaxHP : 1.0;
    var totalBuffs = count(getEffects(myLeek));
    var enemyBuffs = enemy ? count(getEffects(enemy)) : 0;
    var combatIntensity = (myMaxHP - myHP) + (enemy ? enemyMaxHP - enemyHP : 0);
    
    // Phase determination logic
    if (turnNumber <= 3) {
        GAME_PHASE = "OPENING";
    } else if (myHPPercent < 0.25 || enemyHPPercent < 0.25) {
        GAME_PHASE = "ENDGAME";
    } else if (turnNumber > 15 || combatIntensity > 3000) {
        GAME_PHASE = "LATE_GAME";
    } else if (turnNumber <= 8 && combatIntensity < 1000) {
        GAME_PHASE = "MID_GAME";
    } else if (turnNumber > 8 && combatIntensity >= 1000) {
        GAME_PHASE = "LATE_GAME";
    } else {
        GAME_PHASE = "MID_GAME";
    }
    
    // Track phase transitions
    if (GAME_PHASE != previousPhase) {
        var transition = [:];
        transition["turn"] = turn;
        transition["from"] = previousPhase;
        transition["to"] = GAME_PHASE;
        transition["myHP"] = myHPPercent;
        transition["enemyHP"] = enemyHPPercent;
        push(PHASE_HISTORY, transition);
        
        debugLog("PHASE TRANSITION: " + previousPhase + " → " + GAME_PHASE);
        adjustStrategyForPhase();
    }
    
    return GAME_PHASE;
}


// Function: adjustStrategyForPhase
function adjustStrategyForPhase() {
    // Adjust combat weights based on phase
    if (GAME_PHASE == "OPENING") {
        // Focus on buffing and positioning
        WEIGHT_DAMAGE = 0.3;
        WEIGHT_SAFETY = 0.2;
        WEIGHT_POSITION = 0.5;
        
        // Balanced opening - setup focused
        THREAT_HIGH_RATIO = 0.85;  // Moderately cautious
        THREAT_SAFE_RATIO = 0.4;
        PKILL_COMMIT = 0.85;       // Prefer good opportunities
        
        // Prefer longer range
        optimalAttackRange = 9;
        
        debugLog("Opening phase: Focus on setup and positioning");
        
    } else if (GAME_PHASE == "MID_GAME") {
        // Balanced approach
        WEIGHT_DAMAGE = 0.4;
        WEIGHT_SAFETY = 0.3;
        WEIGHT_POSITION = 0.3;
        
        THREAT_HIGH_RATIO = 0.75;  // Balanced mid-game
        THREAT_SAFE_RATIO = 0.45;
        PKILL_COMMIT = 0.7;       // Reasonable aggression
        
        // Keep dynamically calculated range
        
        debugLog("Mid-game: Balanced tactics");
        
    } else if (GAME_PHASE == "LATE_GAME") {
        // Resource conservation
        WEIGHT_DAMAGE = 0.5;
        WEIGHT_SAFETY = 0.4;
        WEIGHT_POSITION = 0.1;
        
        THREAT_HIGH_RATIO = 0.65;  // Calculated risks late game
        THREAT_SAFE_RATIO = 0.5;
        PKILL_COMMIT = 0.65;       // Opportunistic
        
        // Closer range for efficiency
        optimalAttackRange = 6;
        
        debugLog("Late game: Resource conservation");
        
    } else if (GAME_PHASE == "ENDGAME") {
        // All-out damage
        WEIGHT_DAMAGE = 0.8;
        WEIGHT_SAFETY = 0.1;
        WEIGHT_POSITION = 0.1;
        
        THREAT_HIGH_RATIO = 1.0;  // Accept high risk in endgame
        THREAT_SAFE_RATIO = 0.7;  // Aggressive but not reckless
        PKILL_COMMIT = 0.5;       // Take any decent chance
        
        // Get close for maximum damage
        optimalAttackRange = 4;
        
        debugLog("ENDGAME: Maximum aggression!");
    }
    
    // Adjust operation knobs based on phase
    adjustKnobsForPhase();
}


// Function: adjustKnobsForPhase
function adjustKnobsForPhase() {
    if (GAME_PHASE == "OPENING") {
        // Can afford expensive operations
        K_BEAM = min(K_BEAM * 1.2, 60);
        SEARCH_DEPTH = min(SEARCH_DEPTH * 1.2, 18);
        R_E_MAX = min(R_E_MAX * 1.2, 240);
        
    } else if (GAME_PHASE == "MID_GAME") {
        // Standard operations
        // Use existing values
        
    } else if (GAME_PHASE == "LATE_GAME") {
        // Conserve operations
        K_BEAM = max(K_BEAM * 0.8, 20);
        SEARCH_DEPTH = max(SEARCH_DEPTH * 0.8, 8);
        R_E_MAX = max(R_E_MAX * 0.8, 80);
        
    } else if (GAME_PHASE == "ENDGAME") {
        // Minimal operations - just survive and kill
        K_BEAM = 10;
        SEARCH_DEPTH = 5;
        R_E_MAX = 30;
    }
}

// Phase-specific tactics

// Function: getPhaseSpecificTactics
function getPhaseSpecificTactics() {
    var tactics = [:];
    
    if (GAME_PHASE == "OPENING") {
        tactics["priorities"] = ["BUFF", "POSITION", "SCOUT"];
        tactics["buffOrder"] = [CHIP_ADRENALINE, CHIP_STEROID, CHIP_SOLIDIFICATION];
        tactics["idealRange"] = 12;  // Stay far initially
        tactics["healThreshold"] = 0.8;  // Heal early to stay healthy
        tactics["mpUsage"] = "CONSERVATIVE";  // Save MP for later
        tactics["preferredWeapon"] = WEAPON_M_LASER;  // Long range line attack
        
    } else if (GAME_PHASE == "MID_GAME") {
        tactics["priorities"] = ["DAMAGE", "SUSTAIN", "CONTROL"];
        tactics["healThreshold"] = 0.6;  // Heal at 60% HP
        tactics["idealRange"] = 7;
        tactics["mpUsage"] = "MODERATE";
        tactics["preferredWeapon"] = WEAPON_GRENADE_LAUNCHER;  // Balanced
        
    } else if (GAME_PHASE == "LATE_GAME") {
        tactics["priorities"] = ["EFFICIENCY", "SUSTAIN", "POSITION"];
        tactics["healThreshold"] = 0.5;
        tactics["idealRange"] = 6;
        tactics["mpUsage"] = "AGGRESSIVE";  // Use MP to secure positions
        tactics["preferredWeapon"] = WEAPON_GRENADE_LAUNCHER;  // AoE efficiency
        
    } else if (GAME_PHASE == "ENDGAME") {
        tactics["priorities"] = ["KILL", "DAMAGE", "SURVIVE"];
        tactics["healThreshold"] = 0.3;  // Only heal if critical
        tactics["idealRange"] = 3;  // Get close for maximum damage
        tactics["mpUsage"] = "ALL_IN";  // Use everything
        tactics["preferredWeapon"] = WEAPON_DARK_KATANA;  // Maximum burst damage (99 per hit)
    }
    
    return tactics;
}

// Check if we should use specific tactics based on phase

// Function: shouldUsePhaseTactic
function shouldUsePhaseTactic(tacticName) {
    var tactics = getPhaseSpecificTactics();
    var priorities = tactics["priorities"];
    
    // Check if tactic is in top priorities
    for (var i = 0; i < count(priorities); i++) {
        if (priorities[i] == tacticName) {
            return true;
        }
    }
    
    return false;
}

// Get phase-adjusted movement points to use

// Function: getPhaseMP
function getPhaseMP() {
    var tactics = getPhaseSpecificTactics();
    var mpUsage = tactics["mpUsage"];
    
    if (mpUsage == "CONSERVATIVE") {
        return min(myMP, floor(myMP * 0.5));  // Use only half
    } else if (mpUsage == "MODERATE") {
        return min(myMP, floor(myMP * 0.75));  // Use 75%
    } else if (mpUsage == "AGGRESSIVE") {
        return myMP;  // Use all
    } else if (mpUsage == "ALL_IN") {
        return myMP;  // Use everything
    }
    
    return myMP;
}

// === SACRIFICIAL POSITIONING SYSTEM ===

