// V6 Module: movement/reachability.ls
// Cell reachability calculations
// Auto-generated from V5.0 script

// Function: getReachableCells
function getReachableCells(fromCell, mp) {
    // Fix 9: Better caching - cache per turn/position/mp
    if (REACHABLE_CACHE_TURN == turn && 
        REACHABLE_CACHE_FROM == fromCell && 
        REACHABLE_CACHE_MP == mp) {
        return REACHABLE_CACHE_RESULT;
    }
    
    var cacheKey = fromCell + "_" + mp;
    var cached = mapGet(CACHE_REACHABLE, cacheKey, null);
    if (cached != null) {
        REACHABLE_CACHE_TURN = turn;
        REACHABLE_CACHE_FROM = fromCell;
        REACHABLE_CACHE_MP = mp;
        REACHABLE_CACHE_RESULT = cached;
        return cached;
    }

    var reachable = [];
    var visited = [:];
    var queue = [[fromCell, 0]];
    
    // Removed verbose reachability start logging

    while (count(queue) > 0) {
        var cur = shift(queue);
        var cell = cur[0];
        var dist = cur[1];
        
        // Removed verbose cell processing logging
        
        if (mapGet(visited, cell, false)) continue;
        visited[cell] = true;
        push(reachable, cell);

        if (dist < mp) {
            var x = getCellX(cell);
            var y = getCellY(cell);
            var neighbors = [
                getCellFromXY(x+1, y),
                getCellFromXY(x-1, y),
                getCellFromXY(x, y+1),
                getCellFromXY(x, y-1)
            ];
            
            for (var i = 0; i < count(neighbors); i++) {
                var n = neighbors[i];
                // Check validity first (fastest), then obstacles, then visited status  
                // TEMPORARY FIX: Skip obstacle check to allow movement
                if (n != null && n != -1 && n != enemyCell && !mapGet(visited, n, false)) {
                    push(queue, [n, dist+1]);
                    // Don't mark as visited here - let the main loop handle it
                    // Removed verbose neighbor addition logging
                }
                // Removed verbose neighbor rejection logging
            }
        }
    }
    
    CACHE_REACHABLE[cacheKey] = reachable;
    
    // Fix 9: Update turn-based cache
    REACHABLE_CACHE_TURN = turn;
    REACHABLE_CACHE_FROM = fromCell;
    REACHABLE_CACHE_MP = mp;
    REACHABLE_CACHE_RESULT = reachable;
    
    // Keep summary log but remove verbose cell listing
    // Reachable cells found - debug removed to reduce spam
    
    return reachable;
}

// FIX: Enemy reachable cells - blocks my cell

// Function: getEnemyReachable
function getEnemyReachable(fromCell, mp) {
    var key = "E_" + fromCell + "_" + mp;
    var cached = mapGet(CACHE_REACHABLE, key, null);
    if (cached != null) return cached;

    var reachable = [];
    var visited = [:];
    var queue = [[fromCell, 0]];

    while (count(queue) > 0) {
        var cur = shift(queue);
        var c = cur[0];
        var d = cur[1];
        
        if (mapGet(visited, c, false)) continue;
        visited[c] = true;
        push(reachable, c);

        if (d < mp) {
            var x = getCellX(c);
            var y = getCellY(c);
            var ns = [getCellFromXY(x+1,y), getCellFromXY(x-1,y), getCellFromXY(x,y+1), getCellFromXY(x,y-1)];
            
            for (var i = 0; i < count(ns); i++) {
                var n = ns[i];
                // Check validity first (fastest), then obstacles, then visited status
                if (n != null && n != -1 && !isObstacle(n) && n != myCell && !mapGet(visited, n, false)) {
                    push(queue, [n, d+1]);
                    visited[n] = true;  // Mark as visited immediately to prevent re-queueing
                }
            }
        }
    }
    
    CACHE_REACHABLE[key] = reachable;
    return reachable;
}


// Function: findReachableHitCells
function findReachableHitCells(allHitCells) {
    var reachableHitCells = [];
    var myReachable = getReachableCells(myCell, myMP);
    
    // Build set for O(1) lookup
    var rset = [:];
    for (var i = 0; i < count(myReachable); i++) {
        rset[myReachable[i]] = true;
    }
    
    // Check which hit cells are in reachable set
    for (var i = 0; i < count(allHitCells); i++) {
        var hitData = allHitCells[i];
        var cell = hitData[0];
        if (mapGet(rset, cell, false)) {
            push(reachableHitCells, hitData);
        }
    }
    
    // If no reachable cells but current position is valid, check it
    if (count(reachableHitCells) == 0 && mapGet(rset, myCell, false)) {
        for (var i = 0; i < count(allHitCells); i++) {
            var hitData = allHitCells[i];
            if (hitData[0] == myCell) {
                push(reachableHitCells, hitData);
                break;
            }
        }
    }
    
    // Hit cells reachable - debug removed to reduce spam
    return reachableHitCells;
}

