// V6 Module: core/initialization.ls
// System initialization
// Auto-generated from V5.0 script

// Function: initialize
function initialize() {
    turn = getTurn();
    opsStartTurn = getOperations();  // Store ops at start
    myLeek = getEntity();
    
    // Calculate max operations based on cores
    maxOperations = getCores(myLeek) * 1000000;
    myCell = getCell();
    myHP = getLife();
    myMaxHP = getTotalLife();
    myTP = getTP();
    myMP = getMP();
    myStrength = getStrength();
    myAgility = getAgility();
    myScience = getScience();
    myMagic = getMagic();
    myResistance = getResistance();
    myWisdom = getWisdom();
    myAbsShield = getAbsoluteShield(myLeek);
    myRelShield = getRelativeShield(myLeek);
    
    // Initialize multi-enemy system
    initializeEnemies();
    
    // Backward compatibility - enemy variable is set by initializeEnemies()
    if (enemy != null) {
        // Initialize erosion tracking on first turn
        if (turn == 1) {
            ENEMY_ORIGINAL_MAX_HP = enemyMaxHP;
            ENEMY_EROSION = 0;
        } else if (ENEMY_ORIGINAL_MAX_HP > 0) {
            // Update erosion based on max HP change
            ENEMY_EROSION = ENEMY_ORIGINAL_MAX_HP - enemyMaxHP;
            if (ENEMY_EROSION > 0) {
                debugLog("🔥 Erosion damage: " + ENEMY_EROSION + " (" + round(ENEMY_EROSION * 100 / ENEMY_ORIGINAL_MAX_HP) + "%)");
            }
        }
        
        // Check teleportation availability (can't use turn 1, 10 turn cooldown)
        if (turn > 1) {
            // First check if we have the teleportation chip equipped
            var chips = getChips();
            if (inArray(chips, CHIP_TELEPORTATION)) {
                var teleportCD = getCooldown(CHIP_TELEPORTATION);
                TELEPORT_AVAILABLE = (teleportCD == 0);
                if (TELEPORT_AVAILABLE && turn <= 5) {
                    debugLog("🌀 Teleportation available!");
                }
            } else {
                TELEPORT_AVAILABLE = false;
                if (turn == 2) {
                    debugLog("No teleportation chip equipped");
                }
            }
        }
        
        // Check if we have max HP buffs active
        MAX_HP_BUFFED = (myMaxHP > 3000); // Rough check for elevated HP
        
        // Fix 20: Update optimal grenade range based on battlefield analysis
        updateOptimalGrenadeRange();
    }
    
    // Initialize obstacles array - removed since getAllCells() doesn't exist
    // Obstacles are checked dynamically with isObstacle() function
    
    // Clear caches each turn
    CACHE_EID = [:];
    CACHE_PATH = [:];
    CACHE_LOS = [:];
    CACHE_REACHABLE = [:];
    
    // Analyze our weapon loadout
    analyzeWeaponRanges();
    
    // Detect and initialize alternate weapon loadouts
    detectWeaponLoadout();
    
    // Initialize enemy max range
    if (enemy != null) {
        initEnemyMaxRange();
    }
    
    // Adjust knobs based on available operations
    adjustKnobs();
    
    // Initialize weapon effectiveness matrix on first turn
    if (turn == 1 && !MATRIX_INITIALIZED) {
        initializeWeaponMatrix();
    }
    
    if (enemy != null) {
        // Profile enemy and select strategy on first turn
        if (turn == 1) {
            profileEnemy();
            selectCombatStrategy();
        }
        debugLog("Turn " + turn + " initialized. Enemy: " + getName(enemy) + " at dist " + enemyDistance);
    }
}

// Initialize enemy's weapon analysis

// Function: adjustKnobs
function adjustKnobs() {
    adjustKnobsSmooth();
}


// Function: adjustKnobsSmooth
function adjustKnobsSmooth() {
    var mode = getOperationalMode();
    var opsPercent = getOperations() / maxOperations;
    
    if (mode == "OPTIMAL") {
        // Full quality algorithms
        K_BEAM = 50;
        SEARCH_DEPTH = 15;
        R_E_MAX = 200;
        DISP_K = 15;
        M_CANDIDATES = 200;
        
    } else if (mode == "EFFICIENT") {
        // Smooth degradation based on exact percentage
        var degradeFactor = (opsPercent - 0.70) / 0.15;  // 0-1 scale within mode
        K_BEAM = floor(50 - 10 * degradeFactor);        // 50 → 40
        SEARCH_DEPTH = floor(15 - 3 * degradeFactor);    // 15 → 12
        R_E_MAX = floor(200 - 50 * degradeFactor);       // 200 → 150
        DISP_K = floor(15 - 5 * degradeFactor);          // 15 → 10
        M_CANDIDATES = floor(200 - 50 * degradeFactor);  // 200 → 150
        
    } else if (mode == "SURVIVAL") {
        // More aggressive reduction but still smooth
        var survivalFactor = (opsPercent - 0.85) / 0.10;
        K_BEAM = floor(40 - 20 * survivalFactor);        // 40 → 20
        SEARCH_DEPTH = floor(12 - 4 * survivalFactor);   // 12 → 8
        R_E_MAX = floor(150 - 70 * survivalFactor);      // 150 → 80
        DISP_K = floor(10 - 5 * survivalFactor);         // 10 → 5
        M_CANDIDATES = floor(150 - 70 * survivalFactor); // 150 → 80
        
    } else {  // PANIC
        // Absolute minimum - just survive
        K_BEAM = 5;
        SEARCH_DEPTH = 2;
        R_E_MAX = 10;
        DISP_K = 1;
        M_CANDIDATES = 5;
        
        // Disable expensive features
        debugEnabled = false;
    }
    
    // Log current settings occasionally
    if (turn <= 3 || (turn % 10 == 0 && turn <= 30)) {
        debugLog("Mode: " + mode + " (" + round(opsPercent * 100) + "% ops) | " +
                "K=" + K_BEAM + " D=" + SEARCH_DEPTH + " R=" + R_E_MAX);
    }
}

// Function: detectWeaponLoadout
// Detect which weapon set we're using and initialize counters
function detectWeaponLoadout() {
    var weapons = getWeapons();
    
    // Check for B-Laser build (Magnum/Destroyer/B-Laser)
    if (inArray(weapons, WEAPON_B_LASER)) {
        debugLog("B-Laser weapon loadout detected");
        
        // Initialize use counters for B-Laser weapons
        magnumUsesRemaining = inArray(weapons, WEAPON_MAGNUM) ? MAGNUM_MAX_USES : 0;
        destroyerUsesRemaining = inArray(weapons, WEAPON_DESTROYER) ? DESTROYER_MAX_USES : 0;
        bLaserUsesRemaining = B_LASER_MAX_USES;
    } else {
        // Standard loadout - reset B-Laser counters
        magnumUsesRemaining = 0;
        destroyerUsesRemaining = 0;
        bLaserUsesRemaining = 0;
    }
}

// Alias for backwards compatibility
