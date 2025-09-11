// V6 Module: core/globals.ls
// Global variables, constants, and caches
// Auto-generated from V5.0 script

// ===================================================================
// VIRUS LEEK v5.1 - WIS-TANK BUILD WITH EID POSITIONING
// ===================================================================
// Core Innovation: Expected Incoming Damage (EID) maps for proactive positioning
// Strategy: Wisdom-focused tank build with HP stacking and healing
// Build Focus: Knowledge (Wisdom) -> Elevation (HP) -> Armoring (HP) -> Combat
// Stat Scaling: WIS for heals/HP, STR for damage, RES for shields
// Operations: 7M budget (using 6.9M with minimal reserve)
// LeekScript 4 compliant - Optimized for WIS-tank playstyle

// === CONSTANTS ===
// Visual debugging colors
global COLOR_SAFE = 0x00FF00;        // Green - Low EID
global COLOR_CAUTION = 0xFFFF00;     // Yellow - Medium EID  
global COLOR_DANGER = 0xFF8800;      // Orange - High EID
global COLOR_LETHAL = 0xFF0000;      // Red - Lethal EID
global COLOR_TARGET = 0xFF00FF;      // Purple - Target
global COLOR_BLUE = 0x0066FF;        // Blue - Current position
global COLOR_WHITE = 0xFFFFFF;       // White - Text

// Threat thresholds - BALANCED AGGRESSION
global THREAT_HIGH_RATIO = 0.8;      // EID/EHP ratio for high threat - Moderately aggressive
global THREAT_SAFE_RATIO = 0.4;      // EID/EHP ratio for safe zone - Balanced risk
global PKILL_COMMIT = 0.7;            // Probability to commit to kill - Reasonable threshold
global PKILL_SETUP = 0.5;             // Probability to setup 2-turn kill - Balanced
global TP_DEFENSIVE_RATIO = 0.6;     // EID/EHP ratio to use TP defensively - Moderate
global MP_REPOSITION_MIN = 2;        // Minimum MP to attempt repositioning
global PANIC_HP_PERCENT = 0.2;       // Enter panic mode below 20% HP

// Critical hit constants - FIXED from 50% to 30%
global CRITICAL_FACTOR = 0.3;        // 30% damage bonus on critical hit
global EROSION_NORMAL = 0.05;        // 5% erosion on normal damage
global EROSION_CRITICAL = 0.15;      // 15% erosion on critical damage (3x)
global EROSION_POISON_NORMAL = 0.1;  // 10% erosion on poison
global EROSION_POISON_CRIT = 0.2;    // 20% erosion on poison crit

// Scoring weights - WIS-TANK BUILD (balanced sustain)
global WEIGHT_DAMAGE = 1.0;           // Damage importance - BALANCED
global WEIGHT_SAFETY = 0.8;           // Safety importance - HIGH for tank
global WEIGHT_DPTP = 0.6;             // Efficiency importance - MODERATE
global WEIGHT_POSITION = 0.6;         // Positioning importance - HIGH for teleport usage

// Operations budget management - AGGRESSIVE: Use 98.5% of 7M budget!
global OPS_BUDGET_INITIAL = 6900000;     // Use 98.5% (6.9M of 7M)
global OPS_PER_CELL_ESTIMATE = 10000;    // Estimated ops per cell evaluation
global OPS_SAFETY_RESERVE = 50000;       // Minimal 0.7% reserve (down from 500k)
global OPS_CHECKPOINT_INTERVAL = 100000; // Check operations every 100k
global OPS_PANIC_THRESHOLD = 6950000;    // Panic at 99.3% (up from 97%)

// Graduated operation levels for smooth quality degradation
global OPS_LEVEL_OPTIMAL = 5000000;      // 0-5M: Full quality algorithms
global OPS_LEVEL_EFFICIENT = 6000000;    // 5-6M: Reduced search depth
global OPS_LEVEL_SURVIVAL = 6800000;     // 6-6.8M: Minimal calculations
global OPS_LEVEL_PANIC = 6950000;        // 6.95M+: Emergency mode only

// Cache configuration
global CACHE_EID = [:];               // EID cache for cells
global CACHE_PATH = [:];              // Path cache
global CACHE_LOS = [:];               // Line of sight cache
global CACHE_REACHABLE = [:];         // Reachable cells cache

// Fix 9: Cache reachable cells properly to avoid recalculation
global REACHABLE_CACHE_TURN = -1;
global REACHABLE_CACHE_FROM = -1;
global REACHABLE_CACHE_MP = -1;
global REACHABLE_CACHE_RESULT = [];

// Fix 12: Cache cooldown checks to avoid redundant calls
global COOLDOWN_CACHE = [:];
global COOLDOWN_CACHE_TURN = -1;

// === GLOBAL VARIABLES ===
global turn;
global myLeek;
global myCell;
global myHP;
global myMaxHP;
global myTP;
global myMP;
global myStrength;
global myAgility;
global myScience;
global myMagic;
global myResistance;
global myWisdom;
global myAbsShield;
global myRelShield;

global enemy;
global enemyCell;
global enemyHP;
global enemyMaxHP;
global enemyTP;
global enemyMP;
global enemyDistance;
global enemyStrength;
global enemyAgility;
global enemyScience;
global enemyMagic;

// Multi-enemy support
global enemies = [];
global allEnemies = [];        // Array of all alive enemies (detailed data)
global enemyCount = 0;
global isTeamBattle = false;

// Erosion tracking
global ENEMY_EROSION = 0;            // Track cumulative erosion damage
global ENEMY_ORIGINAL_MAX_HP = 0;    // Store original max HP

global debugEnabled = true;
global opsStartTurn = 0;  // Track operations at turn start
global maxOperations = 0; // Maximum operations based on cores (set in initialization)

// Weapon analysis
global weaponRanges = [];  // [[minRange, maxRange], ...]
global optimalAttackRange = 7;  // Default, will be dynamically updated

// Weapon and chip constants are built-in to LeekScript
// Our loadout focuses on WIS-tank strategy:
// - CHIP_KNOWLEDGE: +250-270 flat Wisdom
// - CHIP_ELEVATION: +80 base max HP (scales with Wisdom)
// - CHIP_REGENERATION: 500 base heal (scales with Wisdom)
// - CHIP_TELEPORTATION: 1-12 range teleport for positioning
// Note: Healing/HP chips scale with WIS, damage with STR, shields with RES

// Enemy analysis
global ENEMY_MAX_RANGE = 0;
global ENEMY_MIN_RANGE = 999;
global ENEMY_MAX_AOE_SIZE = 1;
global ENEMY_HAS_BAZOOKA = false;

// EID precomputation
global EID_TURN = [:];

// WIS-Tank specific tracking
global TELEPORT_AVAILABLE = false;
global TELEPORT_LAST_USED = -10;  // Turn when last used
global MAX_HP_BUFFED = false;      // Track if we've applied max HP buffs
global EMERGENCY_HEAL_USED = false; // Track Regeneration chip usage

// Adaptive knobs based on operations budget - 7M ops available!
global K_BEAM = 40;      // Beam search width - Increased with 7M ops!
global SEARCH_DEPTH = 12; // Search depth - Deeper search with more ops!
global R_E_MAX = 150;     // Max enemy reachable cells - More thorough!
global DISP_K = 10;       // Displacement branches - More options!
global M_CANDIDATES = 150; // Top candidates to evaluate - We have 7M ops!

// Smooth Operational Mode Management
global OPERATIONAL_MODE = "OPTIMAL";
global MODE_HISTORY = [];  // Track mode transitions
global LAST_MODE_CHECK_OPS = 0;  // For hysteresis

// Combat Strategy System
global ENEMY_TYPE = "BALANCED";  // Enemy classification
global COMBAT_STRATEGY = "ADAPTIVE"; // Current strategy

// Ensemble Decision System - Multiple strategies vote on actions
global ENSEMBLE_STRATEGIES = [:];
global ENSEMBLE_INITIALIZED = false;

// Pattern Learning System - Track enemy behavior for prediction
global ENEMY_PATTERNS = [:];
global PATTERN_INITIALIZED = false;
global myLastTurnDamage = 0;  // Track damage we dealt last turn
global myLastHP = 0;          // Track our HP from last turn
global enemyLastHP = 0;       // Track enemy HP from last turn
global enemyLastCell = -1;    // Track enemy position from last turn

// Influence Map System - Visualize damage zones and tactical positioning
global INFLUENCE_MAP = [:];
global INFLUENCE_TURN = -1;

// Weapon Effectiveness Matrix - Pre-computed damage calculations
global WEAPON_MATRIX = [:];
global CHIP_MATRIX = [:];
global COMBO_MATRIX = [:];
global MATRIX_INITIALIZED = false;

// Bitwise State System - Ultra-fast state tracking
global combatState = 0;

// State flags as bit positions (much faster than booleans or maps)
global STATE_CAN_MOVE = 1;        // 0b00000001
global STATE_CAN_ATTACK = 2;      // 0b00000010
global STATE_HAS_LOS = 4;          // 0b00000100
global STATE_IN_RANGE = 8;        // 0b00001000
global STATE_IS_BUFFED = 16;      // 0b00010000
global STATE_IS_SHIELDED = 32;    // 0b00100000
global STATE_IS_POISONED = 64;    // 0b01000000
global STATE_IS_CRITICAL = 128;   // 0b10000000

// Extended flags (second byte)
global STATE_HAS_HOT = 256;       // 0b0000000100000000
global STATE_HAS_LIBERATION = 512; // 0b0000001000000000
global STATE_ENEMY_BUFFED = 1024;  // 0b0000010000000000
global STATE_ENEMY_SHIELDED = 2048; // 0b0000100000000000
global STATE_TURN_1_BUFFS = 4096;  // 0b0001000000000000
global STATE_PKILL_READY = 8192;   // 0b0010000000000000
global STATE_SETUP_KILL = 16384;   // 0b0100000000000000
global STATE_PANIC_MODE = 32768;   // 0b1000000000000000

// Game Phase System - Strategic adaptation based on game progression
global GAME_PHASE = "OPENING";
global PHASE_HISTORY = [];
global PHASE_INITIALIZED = false;

// Sacrificial Positioning System - Bait tactics
global BAIT_HISTORY = [];
global BAIT_SUCCESS_RATE = 0;
global LAST_BAIT_TURN = -1;

// Turn 1-3 Combo Strategy System
global COMBO_STRATEGY = null;  // "ANTI_BURST", "ANTI_MAGIC", "STANDARD", null

// ===================================================================
// ALTERNATE WEAPON LOADOUT SUPPORT
// ===================================================================
// B-Laser Build (Magnum/Destroyer/B-Laser)
global MAGNUM_MIN_RANGE = 1;
global MAGNUM_MAX_RANGE = 8;
global DESTROYER_MIN_RANGE = 1;
global DESTROYER_MAX_RANGE = 6;
global B_LASER_MIN_RANGE = 2;
global B_LASER_MAX_RANGE = 8;

// Weapon costs
global MAGNUM_COST = 5;
global DESTROYER_COST = 6;
global B_LASER_COST = 5;

// Weapon use limits
global MAGNUM_MAX_USES = 2;
global DESTROYER_MAX_USES = 2;
global B_LASER_MAX_USES = 3;

// B-Laser specific settings
global OPTIMAL_RANGE_BLASER = 4;     // Sweet spot for B-Laser weapons
global B_LASER_HEAL_THRESHOLD = 0.6; // Consider B-Laser healing below 60% HP
global HEAL_THRESHOLD = 0.6;         // General heal threshold
global SHIELD_THRESHOLD = 0.5;       // Apply shields below 50% HP

// Weapon tracking (reset each turn)
global magnumUsesRemaining = 0;
global destroyerUsesRemaining = 0;
global bLaserUsesRemaining = 0;
global enhancedLightningerUsesRemaining = 0;
global katanaUsesRemaining = 0;

// B-Laser build buff tracking
global hasProtein = false;
global hasMotivation = false;
global hasStretching = false;
global hasLeatherBoots = false;
global hasSolidification = false;
