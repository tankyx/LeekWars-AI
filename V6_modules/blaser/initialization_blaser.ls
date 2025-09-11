// ===================================================================
// V6 B-LASER BUILD - INITIALIZATION MODULE
// ===================================================================

function initializeBLaser() {
    // Initialize turn counter
    turn = getTurn();
    opsStartTurn = getOperations();  // Store ops at start
    
    // Calculate max operations based on cores
    maxOperations = getCores(getEntity()) * 1000000;
    
    // Get enemies (supports both 1v1 and multi-enemy)
    enemies = getAliveEnemies();
    enemyCount = count(enemies);
    isTeamBattle = enemyCount > 1;
    
    // Primary enemy selection
    enemy = getNearestEnemy();
    if (enemy == null && enemyCount > 0) {
        enemy = enemies[0];

    
    // Initialize position data
    myCell = getCell();
    if (enemy != null) {
        enemyCell = getCell(enemy);
        enemyDistance = getCellDistance(myCell, enemyCell);
    } else {
        enemyCell = null;
        enemyDistance = 999;

    
    // Initialize stats
    myHP = getLife();
    myMaxHP = getTotalLife();
    myTP = getTP();
    myMP = getMP();
    myStrength = getStrength();
    myWisdom = getWisdom();
    myAgility = getAgility();
    myResistance = getResistance();
    
    // Enemy stats
    if (enemy != null) {
        enemyHP = getLife(enemy);
        enemyMaxHP = getTotalLife(enemy);
    } else {
        enemyHP = 0;
        enemyMaxHP = 1;

    
    // Reset weapon use counters each turn
    magnumUsesRemaining = MAGNUM_MAX_USES;
    destroyerUsesRemaining = DESTROYER_MAX_USES;
    bLaserUsesRemaining = B_LASER_MAX_USES;
    
    // Check active buffs
    hasProtein = count(getEffects(EFFECT_BUFF_STRENGTH)) > 0;
    hasMotivation = count(getEffects(EFFECT_BUFF_AGILITY)) > 0;
    hasStretching = count(getEffects(EFFECT_BUFF_MP)) > 0;
    hasLeatherBoots = count(getEffects(EFFECT_BUFF_MP)) > 0; // Both use MP buff
    hasSolidification = getAbsoluteShield() > 0;
    
    if (debugEnabled && canSpendOps(1000)) {
		debugLog("=== TURN " + turn + " B-LASER BUILD ===");
    if (debugEnabled && canSpendOps(1000)) {
		debugLog("HP: " + myHP + "/" + myMaxHP + " | Enemy: " + enemyHP + "/" + enemyMaxHP);
    if (debugEnabled && canSpendOps(1000)) {
		debugLog("Distance: " + enemyDistance + " | TP: " + myTP + " | MP: " + myMP);
    if (debugEnabled && canSpendOps(1000)) {
		debugLog("STR: " + myStrength + " | WIS: " + myWisdom);
    
    if (isTeamBattle) {
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Team battle detected - " + enemyCount + " enemies");



function isInPanicModeBLaser() {
    // Panic mode when very low HP
    return (myHP < myMaxHP * PANIC_HP_PERCENT) || (myHP < 300);


function executeEarlyGameBLaser() {
    // Turn 1 aggressive opening with movement buffs
    
    // Priority 1: Movement buffs for positioning
    if (myTP >= 3 && !hasStretching && canUseChip(CHIP_STRETCHING, getEntity())) {
        useChip(CHIP_STRETCHING, getEntity());
        myTP -= 3;
        hasStretching = true;
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Applied Stretching (+50% MP)");

    
    if (myTP >= 2 && !hasLeatherBoots && canUseChip(CHIP_LEATHER_BOOTS, getEntity())) {
        useChip(CHIP_LEATHER_BOOTS, getEntity());
        myTP -= 2;
        hasLeatherBoots = true;
        myMP = getMP(); // Update MP after buff
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Applied Leather Boots (+1 MP)");

    
    // Priority 2: Damage buff
    if (myTP >= 3 && !hasProtein && canUseChip(CHIP_PROTEIN, getEntity())) {
        useChip(CHIP_PROTEIN, getEntity());
        myTP -= 3;
        hasProtein = true;
        myStrength = getStrength(); // Update strength
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Applied Protein (+50% STR)");

    
    // Priority 3: Move to optimal position
    if (enemy != null && myMP > 0) {
        var targetDistance = OPTIMAL_RANGE_BLASER;
        if (enemyDistance > targetDistance) {
            moveToward(enemy, min(myMP, enemyDistance - targetDistance));
            updatePositionBLaser();


    
    // Priority 4: Execute remaining attacks
    executeAttackBLaser();


function updatePositionBLaser() {
    myCell = getCell();
    if (enemy != null) {
        enemyCell = getCell(enemy);
        enemyDistance = getCellDistance(myCell, enemyCell);

    myTP = getTP();
    myMP = getMP();


function simplifiedCombatBLaser() {
    // Panic mode - prioritize survival
    if (debugEnabled && canSpendOps(1000)) {
		debugLog("PANIC MODE - Survival priority");
    
    // Use solidification shield if available
    if (myTP >= 4 && !hasSolidification && canUseChip(CHIP_SOLIDIFICATION, getEntity())) {
        useChip(CHIP_SOLIDIFICATION, getEntity());
        myTP -= 4;
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Emergency shield applied");

    
    // Try B-Laser for heal + damage if in range and aligned
    if (enemy != null && myTP >= B_LASER_COST && bLaserUsesRemaining > 0) {
        if (enemyDistance >= B_LASER_MIN_RANGE && enemyDistance <= B_LASER_MAX_RANGE) {
            if (isOnSameLine(myCell, enemyCell)) {
                setWeapon(WEAPON_B_LASER);
                if (useWeaponOnCell(enemyCell) == USE_SUCCESS) {
                    myTP -= B_LASER_COST;
                    bLaserUsesRemaining--;
                    if (debugEnabled && canSpendOps(1000)) {
		debugLog("B-Laser heal + damage in panic mode");




    
    // Use any remaining TP for damage
    while (myTP > 0 && enemy != null) {
        var attacked = false;
        
        // Try Destroyer if in range
        if (myTP >= DESTROYER_COST && destroyerUsesRemaining > 0 && 
            enemyDistance >= DESTROYER_MIN_RANGE && enemyDistance <= DESTROYER_MAX_RANGE) {
            setWeapon(WEAPON_DESTROYER);
            if (useWeapon(enemy) == USE_SUCCESS) {
                myTP -= DESTROYER_COST;
                destroyerUsesRemaining--;
                attacked = true;
                if (debugEnabled && canSpendOps(1000)) {
		debugLog("Panic Destroyer shot");


        
        // Try Magnum if Destroyer failed
        if (!attacked && myTP >= MAGNUM_COST && magnumUsesRemaining > 0 &&
            enemyDistance >= MAGNUM_MIN_RANGE && enemyDistance <= MAGNUM_MAX_RANGE) {
            setWeapon(WEAPON_MAGNUM);
            if (useWeapon(enemy) == USE_SUCCESS) {
                myTP -= MAGNUM_COST;
                magnumUsesRemaining--;
                attacked = true;
                if (debugEnabled && canSpendOps(1000)) {
		debugLog("Panic Magnum shot");


        
        // Try Spark chip as last resort
        if (!attacked && myTP >= 2 && enemyDistance <= 6 && canUseChip(CHIP_SPARK, enemy)) {
            useChip(CHIP_SPARK, enemy);
            myTP -= 2;
            attacked = true;
            if (debugEnabled && canSpendOps(1000)) {
		debugLog("Panic Spark chip");

        
        if (!attacked) break;
        myTP = getTP();

    
    // Retreat if MP available
    if (enemy != null && myMP > 0) {
        moveAwayFrom(enemy, myMP);
        if (debugEnabled && canSpendOps(1000)) {
		debugLog("Panic retreat");



if (debugEnabled && canSpendOps(1000)) {
		debugLog("B-Laser initialization module loaded");