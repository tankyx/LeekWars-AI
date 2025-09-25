// V7 Module: utils/cache.ls
// Simple caching utilities

function clearCaches() {
    pathCache = [:];
    losCache = [:];
    eidCache = [:];
}

function getCacheStats() {
    var pathCount = 0;
    var losCount = 0;
    
    for (var key in pathCache) {
        pathCount++;
    }
    
    for (var key in losCache) {
        losCount++;
    }
    
    return "Path cache: " + pathCount + ", LOS cache: " + losCount;
}

// =========================
// Terrain LOS Precomputation
// =========================

// Globals declared in core/globals.ls:
// - terrainLOS: Map[startCell -> Map[endCell -> 0/1]] storing upper-triangle entries (start < end)
// - terrainLOSDone: boolean
// - terrainLOSI, terrainLOSJ: progress pointers for chunked build
// - LOS_PRECOMP_PAIRS_PER_TURN: pair budget per turn (safety throttle)

// Set a terrain LOS value for an unordered pair (a,b). Store only in upper triangle.
function setTerrainLOS(a, b, value) {
    var i = (a < b) ? a : b;
    var j = (a < b) ? b : a;
    if (i == j) return;
    if (terrainLOS[i] == null) { terrainLOS[i] = [:]; }
    terrainLOS[i][j] = value ? 1 : 0;
}

// Get a terrain LOS value for an unordered pair. Returns -1 if unknown, 0 or 1 otherwise.
function getTerrainLOS(a, b) {
    if (a == b) return 1; // same cell has trivial LOS
    var i = (a < b) ? a : b;
    var j = (a < b) ? b : a;
    var row = terrainLOS[i];
    if (row == null) return -1;
    var v = row[j];
    if (v == null) return -1;
    return v;
}

// Build a list of all entities to ignore (terrain-only LOS baseline)
function buildIgnoreAllEntities() {
    var ignore = [getEntity()];
    var allies = getAllies();
    for (var i = 0; i < count(allies); i++) { push(ignore, allies[i]); }
    var enemies = getEnemies();
    for (var j = 0; j < count(enemies); j++) { push(ignore, enemies[j]); }
    return ignore;
}

// Precompute a chunk of terrain LOS pairs. Call this once per turn until terrainLOSDone.
function precomputeTerrainLOSChunk() {
    if (terrainLOSDone) return 0;
    var processed = 0;
    var budget = LOS_PRECOMP_PAIRS_PER_TURN;
    var ignoreAll = buildIgnoreAllEntities();

    var i = terrainLOSI;
    var j = terrainLOSJ;

    while (i <= 612) {
        while (j <= 612) {
            // Compute and store terrain-only LOS
            var los = lineOfSight(i, j, ignoreAll);
            setTerrainLOS(i, j, los == true);
            processed++;
            if (processed >= budget) {
                terrainLOSI = i;
                terrainLOSJ = j + 1;
                return processed;
            }
            j = j + 1;
        }
        i = i + 1;
        j = i + 1;
    }
    terrainLOSDone = true;
    terrainLOSI = 613;
    terrainLOSJ = 613;
    return processed;
}

// =========================
// Cached LOS Wrapper
// =========================

// Cached line-of-sight that leverages the terrain LOS table first, then calls native LOS.
// Optional ignore parameter is forwarded to the native API when provided.
function cachedLineOfSight(fromCell, toCell, ignoreEntities) {
    // Validate cells
    if (fromCell == null || toCell == null) return false;
    if (fromCell < 0 || fromCell > 612 || toCell < 0 || toCell > 612) return false;
    // Same cell: trivial LOS
    if (fromCell == toCell) return true;

    var key = fromCell + "_" + toCell;
    if (losCache[key] != null) {
        return losCache[key] == true;
    }

    // Terrain shortcut: if terrain blocks, no need to call native LOS
    var t = getTerrainLOS(fromCell, toCell);
    if (t == 0) {
        losCache[key] = false;
        return false;
    }
    // Unknown or terrain clear -> check true LOS (entities included unless ignored)
    var result = null;
    if (ignoreEntities != null) {
        result = lineOfSight(fromCell, toCell, ignoreEntities);
    } else {
        result = lineOfSight(fromCell, toCell);
    }
    var ok = (result == true);
    losCache[key] = ok;
    return ok;
}
