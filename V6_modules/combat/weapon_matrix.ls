// V6 Module: combat/weapon_matrix.ls
// Weapon effectiveness matrix
// Auto-generated from V5.0 script

// Function: initializeWeaponMatrix
function initializeWeaponMatrix() {
    if (MATRIX_INITIALIZED) return;
    
    debugLog("Pre-computing weapon effectiveness matrix...");
    
    var myWeapons = getWeapons();
    var myChips = getChips();
    
    // Pre-compute weapon effectiveness at each range
    for (var w = 0; w < count(myWeapons); w++) {
        var weapon = myWeapons[w];
        var minRange = getWeaponMinRange(weapon);
        var maxRange = getWeaponMaxRange(weapon);
        var cost = getWeaponCost(weapon);
        var maxUses = getWeaponMaxUses(weapon);
        var area = getWeaponArea(weapon);
        
        // Get base damage from weapon effects
        var weaponEffects = getWeaponEffects(weapon);
        var baseDamage = 0;
        if (weaponEffects != null) {
            for (var e = 0; e < count(weaponEffects); e++) {
                var effect = weaponEffects[e];
                if (effect[0] == EFFECT_DAMAGE) {
                    // Average of min and max damage
                    baseDamage = (effect[1] + effect[2]) / 2;
                    break;
                }
            }
        }
        
        // Apply strength bonus
        baseDamage = baseDamage * (1 + myStrength / 100.0);
        
        for (var range = 0; range <= 20; range++) {
            var key = weapon + "_" + range;
            
            if (range < minRange || range > maxRange) {
                WEAPON_MATRIX[key] = [:];
                WEAPON_MATRIX[key]["canUse"] = false;
                WEAPON_MATRIX[key]["damage"] = 0;
                WEAPON_MATRIX[key]["dptp"] = 0;
                WEAPON_MATRIX[key]["uses"] = 0;
            } else {
                var effectiveDamage = baseDamage;
                
                // Adjust for AoE falloff if applicable
                if (area == AREA_CIRCLE_2) {
                    // Average damage across all possible hit positions
                    effectiveDamage = baseDamage * 0.73;  // Weighted average
                } else if (area == AREA_X_1) {
                    // Average for diagonal cross
                    effectiveDamage = baseDamage * 0.84;  // 1 center + 4*0.8
                }
                
                WEAPON_MATRIX[key] = [:];
                WEAPON_MATRIX[key]["canUse"] = true;
                WEAPON_MATRIX[key]["damage"] = effectiveDamage;
                WEAPON_MATRIX[key]["dptp"] = cost > 0 ? effectiveDamage / cost : effectiveDamage;
                WEAPON_MATRIX[key]["uses"] = maxUses > 0 ? maxUses : 99;
                WEAPON_MATRIX[key]["cost"] = cost;
                WEAPON_MATRIX[key]["needsLos"] = true;  // All weapons need LOS
                WEAPON_MATRIX[key]["area"] = area;
            }
        }
    }
    
    // Pre-compute chip effectiveness
    for (var c = 0; c < count(myChips); c++) {
        var chip = myChips[c];
        
        // Get chip damage effects
        var chipEffects = getChipEffects(chip);
        var hasDamage = false;
        var baseDamage = 0;
        
        if (chipEffects != null) {
            for (var e = 0; e < count(chipEffects); e++) {
                var effect = chipEffects[e];
                if (effect[0] == EFFECT_DAMAGE) {
                    hasDamage = true;
                    baseDamage = (effect[1] + effect[2]) / 2;
                    break;
                }
            }
        }
        
        if (!hasDamage) continue;
        
        var minRange = getChipMinRange(chip);
        var maxRange = getChipMaxRange(chip);
        var cost = getChipCost(chip);
        var maxUses = getChipMaxUses(chip);
        var area = getChipArea(chip);
        
        // Apply strength bonus for damage chips
        baseDamage = baseDamage * (1 + myStrength / 100.0);
        
        for (var range = 0; range <= 20; range++) {
            var key = chip + "_" + range;
            
            if (range < minRange || range > maxRange) {
                CHIP_MATRIX[key] = [:];
                CHIP_MATRIX[key]["canUse"] = false;
                CHIP_MATRIX[key]["damage"] = 0;
                CHIP_MATRIX[key]["dptp"] = 0;
                CHIP_MATRIX[key]["uses"] = 0;
            } else {
                CHIP_MATRIX[key] = [:];
                CHIP_MATRIX[key]["canUse"] = true;
                CHIP_MATRIX[key]["damage"] = baseDamage;
                CHIP_MATRIX[key]["dptp"] = cost > 0 ? baseDamage / cost : baseDamage;
                CHIP_MATRIX[key]["uses"] = maxUses > 0 ? maxUses : 99;
                CHIP_MATRIX[key]["cost"] = cost;
                CHIP_MATRIX[key]["needsLos"] = chipNeedLos(chip);
                CHIP_MATRIX[key]["cooldown"] = getChipCooldown(chip);
            }
        }
    }
    
    // Pre-compute optimal combinations at each range
    for (var range = 1; range <= 15; range++) {
        var tpBudgets = [18, 23, 28];  // Different TP scenarios
        
        for (var b = 0; b < count(tpBudgets); b++) {
            var budget = tpBudgets[b];
            var key = range + "_" + budget;
            
            COMBO_MATRIX[key] = calculateOptimalCombo(range, budget);
        }
    }
    
    MATRIX_INITIALIZED = true;
    debugLog("Matrix initialization complete");
}


// Function: getOptimalDamage
function getOptimalDamage(range, tpAvailable) {
    if (!MATRIX_INITIALIZED) {
        initializeWeaponMatrix();
    }
    
    // Round TP to nearest bucket
    var tpBucket = 18;
    if (tpAvailable >= 26) {
        tpBucket = 28;
    } else if (tpAvailable >= 21) {
        tpBucket = 23;
    }
    
    var key = range + "_" + tpBucket;
    var combo = mapGet(COMBO_MATRIX, key, null);
    
    if (combo != null) {
        // Scale damage if actual TP differs from bucket
        var scale = min(1.0, tpAvailable / tpBucket);
        return floor(combo["totalDamage"] * scale);
    }
    
    return 0;
}

// Quick weapon lookup

// Function: getWeaponDamageAt
function getWeaponDamageAt(weapon, range) {
    if (!MATRIX_INITIALIZED) {
        initializeWeaponMatrix();
    }
    
    var key = weapon + "_" + range;
    var data = mapGet(WEAPON_MATRIX, key, null);
    
    if (data != null && data["canUse"]) {
        return data["damage"];
    }
    
    return 0;
}

// Quick chip lookup

// Function: getChipDamageAt
function getChipDamageAt(chip, range) {
    if (!MATRIX_INITIALIZED) {
        initializeWeaponMatrix();
    }
    
    var key = chip + "_" + range;
    var data = mapGet(CHIP_MATRIX, key, null);
    
    if (data != null && data["canUse"]) {
        return data["damage"];
    }
    
    return 0;
}

// === BITWISE STATE MANAGEMENT ===

// Set state flags

// Function: calculateOptimalCombo
function calculateOptimalCombo(range, tpBudget) {
    var combo = [:];
    combo["weapons"] = [];
    combo["chips"] = [];
    combo["totalDamage"] = 0;
    combo["tpUsed"] = 0;
    
    var items = [];
    
    // Collect all usable items at this range
    var myWeapons = getWeapons();
    for (var i = 0; i < count(myWeapons); i++) {
        var key = myWeapons[i] + "_" + range;
        var data = mapGet(WEAPON_MATRIX, key, null);
        if (data != null && data["canUse"] && data["cost"] <= tpBudget) {
            var item = [:];
            item["type"] = "weapon";
            item["id"] = myWeapons[i];
            item["data"] = data;
            push(items, item);
        }
    }
    
    var myChips = getChips();
    for (var i = 0; i < count(myChips); i++) {
        var key = myChips[i] + "_" + range;
        var data = mapGet(CHIP_MATRIX, key, null);
        if (data != null && data["canUse"] && data["cost"] <= tpBudget) {
            var item = [:];
            item["type"] = "chip";
            item["id"] = myChips[i];
            item["data"] = data;
            push(items, item);
        }
    }
    
    // Sort by DPTP (manual sort since LeekScript doesn't support comparison functions)
    var sorted = [];
    while (count(items) > 0) {
        var bestIdx = 0;
        var bestDptp = items[0]["data"]["dptp"];
        for (var j = 1; j < count(items); j++) {
            if (items[j]["data"]["dptp"] > bestDptp) {
                bestIdx = j;
                bestDptp = items[j]["data"]["dptp"];
            }
        }
        push(sorted, items[bestIdx]);
        removeElement(items, items[bestIdx]);
    }
    items = sorted;
    
    // Greedy allocation
    var tpLeft = tpBudget;
    
    for (var i = 0; i < count(items); i++) {
        var item = items[i];
        var itemCost = item["data"]["cost"];
        var uses = itemCost > 0 ? min(floor(tpLeft / itemCost), item["data"]["uses"]) : 0;
        
        if (uses > 0) {
            var comboItem = [:];
            comboItem["id"] = item["id"];
            comboItem["uses"] = uses;
            
            if (item["type"] == "weapon") {
                push(combo["weapons"], comboItem);
            } else {
                push(combo["chips"], comboItem);
            }
            
            combo["totalDamage"] += uses * item["data"]["damage"];
            combo["tpUsed"] += uses * itemCost;
            tpLeft -= uses * itemCost;
        }
        
        if (tpLeft < 3) break;
    }
    
    return combo;
}

// Fast lookup function
