# LeekWars AI ? Technical Reference

> **Budget:** 14M ops · 7 MP · 24?25 TP per turn
> **Build:** Offensive-focused with Magic/Poison capabilities
> **Architecture:** Scenario-based planner (Beam Search disabled)

---

## Table of Contents

1. [Critical Bugs ? Fix Immediately](#1-critical-bugs)
2. [Architecture Overview](#2-architecture)
3. [Formulas & Constants](#3-formulas)
4. [Scenario System](#4-scenario-system)
5. [Combat Subsystems](#5-combat-subsystems)
6. [Battle Royale Strategy](#6-battle-royale)
7. [Code Patterns](#7-code-patterns)
8. [Files to Delete](#8-cleanup)
9. [Priority Roadmap](#9-roadmap)

---

## 1. Critical Bugs

### Cache Hash Collision
```javascript
// BUG: enemyHash % 100 causes collisions ? stale damage data
var cacheKey = enemyHash % 100;

// FIX: Use unique composite keys
var cacheKey = "" + sourceCell + ":" + targetCell + ":" + enemyPositionHash;
```

### Mutation Corruption
```javascript
// BUG: In-place modification corrupts best scenario
var mutated = topScenarios[i];
mutated.actions.push(newAction);

// FIX: Clone before mutating
var mutated = cloneScenario(topScenarios[i]);
mutated.actions.push(newAction);
```

### Teleport TP Cost Mismatch
- Some files use `tpCost = 5`, others use `tpCost = 9`
- FIX: Always use `getChipCost(chip)` from a centralized cache

### Global State Leak
```javascript
// FIX: Add at turn start
function resetTurnState() {
    POISON_PHASE = false;
    MOVEMENT_COMPLETED = false;
    damageCache = {};
    threatCache = {};
    pathCache = {};
}
```

### QuickScorer TP Bias
```javascript
// BUG: Rewards spending TP as proxy for value
score = damageEstimate + (tpEstimate * tpWeight);

// FIX: Use efficiency-aware scoring
score = (damageEstimate / tpEstimate) - (endPositionThreat * threatWeight);
```

---

## 2. Architecture

### Target V9 Structure
```
GameContext (single source of truth)
??? player { id, cell, hp, tp, mp, stats }
??? enemies[]
??? map (reachability graph)
??? arsenal (weapons/chips)
??? caches { distances, threats, los }
        ?
        ?
Single-Path Scenario Planner
??? 5?8 Template Families
??? QuickScorer (fixed)
??? Full Simulator (top 10 only)
        ?
        ?
Scenario Executor (with validation guards)
```

### Template Families
| Family | Contains |
|--------|----------|
| OFFENSIVE | OTKO, Burst, AoE, Poison Dump |
| DEFENSIVE | Retreat, Heal, Shield, HNS |
| COMBO | Grapple+Melee, Wizardry+Poison, Debuff+Burst |
| UTILITY | Liberation, Antidote, Teleport Escape |
| BULB | Bulb Clear, Bulb Ignore (Race) |

### Ops Budget Allocation
| Component | Target Ops |
|-----------|------------|
| Caches & maps | 1.0M |
| Scenario generation | 1.5M |
| Scenario simulation | 2.0M |
| Threat map | 1.0M |
| Safety buffer | 1.5M |
| **Typical turn** | **~7M** |

---

## 3. Formulas

### Damage
```javascript
FinalDamage = BaseDamage * (1 + Strength/100)  // Physical
FinalDamage = BaseDamage * (1 + Magic/100)     // Magic/Poison
```

### Healing
```javascript
FinalHeal = BaseHeal * (1 + Wisdom/100)
// CHIP_REGENERATION: Base 500, 8 TP, ? cooldown (once per match)
// CHIP_REMISSION: Base 71.5 (avg 66-77), 5 TP, 1 turn cooldown
```

### Shields (Relative)
```javascript
FinalRelativeShield = BaseRelativeShield * (1 + Resistance/100)
FinalDamage = BaseDamage * (1 - RelativeShield/100) - AbsoluteShield
// Example: FORTRESS (8%) at 200 Resistance = 24% reduction
```

### Damage Return
```javascript
FinalDamageReturn = BaseDamageReturn * (1 + Agility/100)
```

### Poison
```javascript
FinalPoisonDamage = BasePoisonDamage * (1 + Magic/100)
```

### Bulb Stats
```javascript
characteristic = floor(min + (max - min) * min(300, summonerLevel) / 300)
// Capped at level 300
```

---

## 4. Scenario System

### Adaptive Top-K
```javascript
var topK;
if (turn < 5 || aliveEnemies > 3) topK = 20;
else if (aliveEnemies == 1) topK = 50;
else topK = 35;
```

### Early-Exit Logic
```javascript
if (gap > 2000 && simulatedCount >= 10) break; // Execute best found
```

### Budget Checkpoints
```javascript
if (getOperations() > 8_000_000) topK = Math.floor(topK * 0.5);
if (getOperations() > 12_000_000) break; // Execute best found
```

### Knapsack-Style TP Allocation
```javascript
var efficiency = damage / tpCost;
if (weapon != equippedWeapon) efficiency = damage / (tpCost + 1);
// Sort by efficiency, select greedily
```

---

## 5. Combat Subsystems

### Healing Logic
```javascript
function getHealingAction(tpBudget) {
    var hpRatio = currHealth / maxHealth;
    
    // Emergency: REGENERATION (8 TP)
    if (hpRatio < 0.35 && getCooldown(CHIP_REGENERATION) == 0 && tpBudget >= 8) {
        return CHIP_REGENERATION;
    }
    
    // Sustain: REMISSION (5 TP)
    if (hpRatio < 0.80 && getCooldown(CHIP_REMISSION) == 0 && tpBudget >= 5) {
        return CHIP_REMISSION;
    }
    return null;
}
```

### Shield/Buff Uptime
```javascript
var threshold = (player.resistance >= 200) ? 2 : 1;
if (shieldBuffTurns <= threshold) generateShieldActions();

// Kill Margin Override
var killMargin = totalDamage / enemyHP;
if (killMargin >= 1.1) buffWeight *= 0.1;      // Kill likely ? skip buffs
else if (criticalBuffMissing) buffWeight *= 5.0; // Force buffs
```

### Poison ? Antidote Window
```javascript
var antidoteCD = cooldownTracker.get(enemy, CHIP_ANTIDOTE);

if (antidoteCD == 0) {
    dotScore *= 0.2;  // Bait only (Venom, Toxin, Gazor)
} else {
    dotScore *= (1.5 + 0.2 * antidoteCD);  // Dump window
}

// Never cast COVID unless antidoteCD >= 3
```

### Bulb Handling
```javascript
function classifyBulbThreat(entity) {
    var name = getName(entity);
    if (contains(name, "heal")) return "HEALER";   // Priority 1
    if (contains(name, "buff")) return "BUFFER";   // Priority 2
    return "ATTACKER";                              // Priority 3
}

// Race Clock
var turnsToKill = enemyHP / yourDPS;
var turnsToDie = yourHP / (enemyDPS + bulbDamagePerTurn);
if (turnsToKill < turnsToDie) state = "RACE";      // Ignore bulbs
else state = "BULB_CLEAR";                          // Kill healers first
```

### Damage Return ? Suicide Guard
```javascript
if (target.hasEffect(EFFECT_DAMAGE_RETURN)) {
    var returnDmg = outgoingDamage * (returnPct / 100);
    simulatedPlayerHP -= returnDmg;
}

if (simulatedPlayerHP <= 0) {
    score += -1_000_000;  // Reject suicidal scenario
    // Consider: CHIP_LIBERATION (strips 40%) or Retreat
}
```

### Hide & Seek (HNS)
```javascript
// Utility scoring for cover cells
Score(C) = -(ThreatMap[C] * W1)
         - (ExposureCount * W2)
         + (FutureDamagePotential * W3)

// Weight tuning by HP
// Low HP:  W1=3.0, W2=2.0, W3=0.5
// Mid HP:  W1=2.0, W2=1.5, W3=1.5
// High HP: W1=1.0, W2=1.0, W3=2.5
```

---

## 6. Battle Royale

### Cumulative Threat
```javascript
function getLobbyThreatAtCell(cellId, enemies) {
    var totalThreat = 0, sources = 0;
    for (var enemy in enemies) {
        var dmg = getEstimatedDamage(enemy, cellId);
        if (dmg > 0) { totalThreat += dmg; sources++; }
    }
    return totalThreat * (1 + sources * 0.2);  // Multi-source penalty
}
```

### Phase System
```javascript
if (aliveEnemies > 4) phase = "EARLY";      // Edge positioning, opportunistic
else if (aliveEnemies >= 3) phase = "MID";  // Attrition, target isolated
else phase = "LATE";                         // Full aggro 1v1
```

### Target Selection
```javascript
TargetScore = (100 - EnemyHP%) * 2
            + (200 - Distance * 10)
            - (ThreatAtEnemyPosition * 0.5)
```

### Ops Optimization for 7+ Enemies
```javascript
// Distance-tiered evaluation
if (enemyDistance <= 10) fullDamageCalc();
else if (enemyDistance <= 20) estimateDamage();
else excludeFromThreatMap();
```

---

## 7. Code Patterns

### GameContext Singleton
```javascript
var GameContext = {
    player: null,
    enemies: [],
    caches: { distances: {}, threats: {}, los: {} },
    
    init: function() {
        this.player = { /* populate */ };
        this.enemies = scanEnemies();
        this.invalidateCaches();
    },
    
    invalidateCaches: function() {
        this.caches = { distances: {}, threats: {}, los: {} };
    }
};
```

### Item Classifier
```javascript
var ItemRoles = {
    BUFFS: [CHIP_STEROID, CHIP_DOPING, CHIP_WIZARDRY, CHIP_WALL, CHIP_FORTRESS],
    HEALS: [CHIP_REGENERATION, CHIP_REMISSION],
    POISONS: [CHIP_VENOM, CHIP_TOXIN, CHIP_PLAGUE, CHIP_COVID, CHIP_ARSENIC],
    RETURNS: [CHIP_THORN, CHIP_MIRROR, CHIP_BRAMBLE],
    
    isBuff: function(id) { return contains(this.BUFFS, id); },
    isHeal: function(id) { return contains(this.HEALS, id); },
    isPoison: function(id) { return contains(this.POISONS, id); },
    isReturn: function(id) { return contains(this.RETURNS, id); }
};
```

### Lazy Debugging
```javascript
function debugInfo(fn) {
    if (DEBUG_ENABLED) debug(fn());
}
// Usage: debugInfo(() => "Score: " + score);
```

### Execution Guard
```javascript
function executeScenario(scenario) {
    for (var action in scenario.actions) {
        if (!validateAction(action, GameContext)) break;
        var result = executeAction(action);
        if (result == ACTION_FAILED) break;
        updateGameContext(result);
    }
}
```

### One BFS Per Turn
```javascript
// At turn start ONLY:
var reachableGraph = computeReachableCells(playerCell, playerMP);
var threatMap = computeThreatMap(reachableGraph, enemies);
// Pass to all consumers ? never call BFS in loops
```

---

## 8. Cleanup

### Files to DELETE
- `beam_search_planner.lk`
- `world_state.lk`
- `state_transition.lk`
- `atomic_action.lk`
- `polynomial.lk`
- `probability_distribution.lk`

### Files to CREATE
- `game_context.lk` ? Centralized state
- `item_roles.lk` ? Unified chip/weapon classification

### Files to REFACTOR
- `scenario_generator.lk` ? Collapse 30 methods into 5?8 Template Families

---

## 9. Roadmap

### Week 1: Critical Fixes
- [ ] Fix cache hash collision (`enemyHash % 100` ? unique keys)
- [ ] Fix mutation corruption (clone before mutate)
- [ ] Fix Teleport/Grapple TP cost mismatches
- [ ] Implement `resetTurnState()`
- [ ] Fix QuickScorer TP bias

### Week 2: Efficiency
- [ ] Cached BFS (once per turn)
- [ ] Adaptive Top-K
- [ ] Simulation early-exit
- [ ] Delete dead Beam Search code
- [ ] Create `GameContext` singleton

### Week 3: Intelligence
- [ ] Create `ItemRoles` classifier
- [ ] Implement Interrupt & Replan logic
- [ ] Add synergy matrix for combos
- [ ] Threat-aware cover bonus (HNS)

### Week 4: Polish
- [ ] Consolidate Scenario Generators into Template Families
- [ ] Kill-Reserve conditional logic
- [ ] AoE masks to Turn 1 init only
- [ ] Poison Antidote window scoring
- [ ] Bulb Race Clock implementation

---

## Quick Reference Tables

### Chip Costs & Cooldowns
| Chip | TP | Cooldown | Notes |
|------|-----|----------|-------|
| REGENERATION | 8 | ? | 500 base heal, once per match |
| REMISSION | 5 | 1 | 66-77 base heal |
| WALL | 3 | 3 | 4-5% shield, 2 turns |
| FORTRESS | 6 | 4 | 7-8% shield, 3 turns |
| THORN | 4 | 3 | 3-4% return, 2 turns |
| MIRROR | 5 | 4 | 5-6% return, 3 turns |
| BRAMBLE | 4 | 8 | 25% return, 1 turn (burst only) |
| WIZARDRY | 6 | 4 | +150-170 Magic, 2 turns |
| VENOM | 4 | 1 | 15-20 poison, 3 turns |
| TOXIN | 5 | 2 | 25-35 poison, AoE, 3 turns |
| PLAGUE | 6 | 4 | 40-50 poison, AoE, 4 turns |
| COVID | 8 | 7 | 69-79 poison, spreads, 7 turns |
| ARSENIC | 8 | 2 | 62-67 poison, through obstacles, 2 turns |
| ANTIDOTE | 3 | 4 | Clears ALL poisons + 25-35 heal |
| LIBERATION | ? | ? | Strips 40% enemy buffs/debuffs |

### Scoring Bonuses
| Event | Score |
|-------|-------|
| Kill any enemy | +5000 |
| Kill healer bulb | +2500 |
| Kill buffer bulb | +1500 |
| Kill attacker bulb | +800 |
| Synergy combo (Grapple+Melee) | +300 |
| Synergy combo (Wizardry+Poison) | +400 |
| End in cover (breaks LoS) | +400 |
| Suicidal scenario | -1,000,000 |

### Ops Safety Thresholds
| Checkpoint | Action |
|------------|--------|
| > 8M ops | Reduce topK by 50% |
| > 12M ops | Stop simulation, execute best found |
| > 13.5M ops | Hard stop, return current best |
