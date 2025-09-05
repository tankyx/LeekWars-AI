# V6 Module Index

## Module Structure

### CORE

#### `core/globals.ls`
*Global variables, constants, and caches*

#### `core/initialization.ls`
*System initialization*

Functions:
- `initialize()` (lines 206-300)
- `adjustKnobs()` (lines 902-905)
- `adjustKnobsSmooth()` (lines 852-901)

#### `core/state_management.ls`
*Bitwise state management*

Functions:
- `setState()` (lines 2195-2199)
- `clearState()` (lines 2200-2204)
- `hasState()` (lines 2205-2209)
- `hasAnyState()` (lines 2210-2214)
- `toggleState()` (lines 2215-2219)
- `updateCombatState()` (lines 2220-2328)
- `getStateDescription()` (lines 2382-2402)

#### `core/operations.ls`
*Operations budget management*

Functions:
- `canSpendOps()` (lines 780-784)
- `getOperationalMode()` (lines 785-834)
- `getOperationLevel()` (lines 835-838)
- `isInPanicMode()` (lines 839-842)
- `checkOperationCheckpoint()` (lines 843-851)
- `shouldUseAlgorithm()` (lines 906-919)

### COMBAT

#### `combat/damage_calculation.ls`
*Damage calculations*

Functions:
- `calculateActualDamage()` (lines 1669-1688)
- `calculateLifeSteal()` (lines 1689-1695)
- `calculateDamageFrom()` (lines 3447-3525)
- `calculateDamageFromTo()` (lines 2728-2762)
- `calculateEnemyDamageFrom()` (lines 2763-2791)
- `calculateDamageFromWithTP()` (lines 4019-4084)

#### `combat/weapon_matrix.ls`
*Weapon effectiveness matrix*

Functions:
- `initializeWeaponMatrix()` (lines 1916-2051)
- `getOptimalDamage()` (lines 2135-2160)
- `getWeaponDamageAt()` (lines 2161-2176)
- `getChipDamageAt()` (lines 2177-2194)
- `calculateOptimalCombo()` (lines 2052-2134)

#### `combat/weapon_analysis.ls`
*Weapon range analysis*

Functions:
- `analyzeWeaponRanges()` (lines 416-447)
- `initEnemyMaxRange()` (lines 301-346)
- `analyzeGrenadeEffectiveness()` (lines 2960-3072)
- `updateOptimalGrenadeRange()` (lines 3073-3101)

#### `combat/chip_management.ls`
*Chip usage and management*

Functions:
- `tryUseChip()` (lines 4099-4117)
- `getCachedCooldown()` (lines 4085-4098)
- `chipHasDamage()` (lines 6270-6279)
- `getChipDamage()` (lines 6280-6293)
- `chipNeedLos()` (lines 6317-6323)

#### `combat/weapon_management.ls`
*Weapon usage and switching*

Functions:
- `useWeapon()` (lines 4118-4136)
- `setWeaponIfNeeded()` (lines 4137-4144)
- `weaponNeedLos()` (lines 6312-6316)
- `getWeaponDamage()` (lines 6294-6311)

#### `combat/aoe_tactics.ls`
*Area of effect calculations*

Functions:
- `calculateOptimalAoEDamage()` (lines 3526-3585)
- `findAoESplashPositions()` (lines 3586-3630)
- `getAoEAffectedCells()` (lines 3752-3800)
- `calculateAoEDamageAtCell()` (lines 3801-3878)

#### `combat/lightninger_tactics.ls`
*Lightninger weapon tactics*

Functions:
- `evaluateLightningerPosition()` (lines 3631-3684)
- `getLightningerPattern()` (lines 3685-3717)
- `findBestLightningerTarget()` (lines 3718-3751)

#### `combat/grenade_tactics.ls`
*Grenade targeting*

Functions:
- `findBestGrenadeTarget()` (lines 3102-3164)

#### `combat/erosion.ls`
*Erosion damage tracking*

Functions:
- `updateErosion()` (lines 2923-2942)
- `evaluateErosionPotential()` (lines 2943-2959)

#### `combat/execute_combat.ls`
*Combat execution*

Functions:
- `executeAttack()` (lines 5708-6151)
- `executeDefensive()` (lines 6196-6269)
- `executeBuffs()` (lines 6324-6983)
- `simplifiedCombat()` (lines 4653-4673)

### MOVEMENT

#### `movement/pathfinding.ls`
*A* pathfinding algorithm*

Functions:
- `aStar()` (lines 606-717)
- `reconstructPath()` (lines 718-728)
- `findBestPathTo()` (lines 760-779)
- `getNeighborCells()` (lines 737-759)

#### `movement/reachability.ls`
*Cell reachability calculations*

Functions:
- `getReachableCells()` (lines 937-999)
- `getEnemyReachable()` (lines 1000-1036)
- `findReachableHitCells()` (lines 4422-4455)

#### `movement/positioning.ls`
*Movement and positioning*

Functions:
- `bestApproachStep()` (lines 4623-4652)
- `moveToCell()` (lines 4145-4189)
- `repositionDefensive()` (lines 5606-5707)

#### `movement/teleportation.ls`
*Teleportation tactics*

Functions:
- `shouldUseTeleport()` (lines 448-479)
- `findBestTeleportTarget()` (lines 480-526)
- `executeTeleport()` (lines 527-541)
- `evaluateTeleportValue()` (lines 542-554)

#### `movement/distance.ls`
*Distance calculations*

Functions:
- `manhattanDistance()` (lines 729-736)
- `getCellFromOffset()` (lines 926-931)

#### `movement/range_finding.ls`
*Range and cell finding*

Functions:
- `getCellsInRange()` (lines 4369-4421)
- `getCellsAtDistance()` (lines 588-605)
- `findHitCells()` (lines 4190-4368)

#### `movement/line_of_sight.ls`
*Line of sight checks*

Functions:
- `hasLOS()` (lines 1037-1049)
- `canAttackFromPosition()` (lines 555-587)

### STRATEGY

#### `strategy/enemy_profiling.ls`
*Enemy analysis and strategy selection*

Functions:
- `profileEnemy()` (lines 347-372)
- `selectCombatStrategy()` (lines 373-415)

#### `strategy/phase_management.ls`
*Game phase management*

Functions:
- `determineGamePhase()` (lines 2403-2445)
- `adjustStrategyForPhase()` (lines 2446-2512)
- `adjustKnobsForPhase()` (lines 2513-2538)
- `getPhaseSpecificTactics()` (lines 2539-2575)
- `shouldUsePhaseTactic()` (lines 2576-2590)
- `getPhaseMP()` (lines 2591-2609)

#### `strategy/pattern_learning.ls`
*Enemy pattern recognition*

Functions:
- `initializePatternLearning()` (lines 1050-1064)
- `updatePatternLearning()` (lines 1065-1131)
- `predictEnemyBehavior()` (lines 1132-1207)
- `getQuadrant()` (lines 1208-1221)
- `applyPatternPredictions()` (lines 1222-1260)
- `predictEnemyResponse()` (lines 2687-2727)

#### `strategy/ensemble_system.ls`
*Ensemble decision making*

Functions:
- `initializeEnsemble()` (lines 1261-1278)
- `ensembleDecision()` (lines 1279-1336)
- `ensembleDecisionLight()` (lines 1337-1383)
- `evaluateAggressive()` (lines 1456-1492)
- `evaluateDefensive()` (lines 1493-1531)
- `evaluateBalanced()` (lines 1532-1589)
- `executeEnsembleAction()` (lines 1590-1668)

#### `strategy/tactical_decisions.ls`
*Quick tactical decisions*

Functions:
- `getQuickTacticalDecision()` (lines 1384-1408)
- `executeQuickAction()` (lines 1409-1455)
- `quickCombatDecision()` (lines 2329-2381)

#### `strategy/bait_tactics.ls`
*Bait and trap tactics*

Functions:
- `executeBaitTactic()` (lines 2792-2851)
- `evaluateBaitPosition()` (lines 2610-2686)
- `updateBaitSuccess()` (lines 2852-2884)
- `shouldUseBaitTactic()` (lines 2885-2922)

#### `strategy/kill_calculations.ls`
*Kill probability calculations*

Functions:
- `calculatePkill()` (lines 3879-3974)
- `canSetupKill()` (lines 3975-3986)
- `estimateNextTurnEV()` (lines 3987-4018)

#### `strategy/anti_tank.ls`
*Anti-tank strategy*

Functions:
- `useAntiTankStrategy()` (lines 6152-6195)

### AI

#### `ai/eid_system.ls`
*Expected Incoming Damage system*

Functions:
- `calculateEID()` (lines 3206-3349)
- `precomputeEID()` (lines 4606-4616)
- `eidOf()` (lines 4617-4622)
- `visualizeEID()` (lines 4545-4605)

#### `ai/influence_map.ls`
*Influence mapping*

Functions:
- `buildInfluenceMap()` (lines 1696-1736)
- `calculateMyAoEZones()` (lines 1737-1807)
- `calculateEnemyAoEZones()` (lines 1808-1851)
- `visualizeInfluenceMap()` (lines 1852-1915)

#### `ai/evaluation.ls`
*Position evaluation*

Functions:
- `evaluateCandidates()` (lines 5453-5469)
- `evaluatePosition()` (lines 5470-5605)
- `calculateEHP()` (lines 3165-3190)
- `calculateEffectiveShieldValue()` (lines 3191-3205)

#### `ai/decision_making.ls`
*Main decision making*

Functions:
- `makeDecision()` (lines 4674-5452)

#### `ai/visualization.ls`
*Debug visualization*

Functions:
- `visualizeHitCells()` (lines 4494-4544)
- `findSafeCells()` (lines 4456-4493)

### UTILS

#### `utils/debug.ls`
*Debug logging*

Functions:
- `debugLog()` (lines 920-925)

#### `utils/helpers.ls`
*Helper functions*

Functions:
- `inRange()` (lines 932-936)

#### `utils/cache.ls`
*Cache management utilities*

#### `utils/constants.ls`
*Visual colors and configuration*


## Statistics

- Total modules: 38
- Total functions: 124
- Original script lines: 6983
