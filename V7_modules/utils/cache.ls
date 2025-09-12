// V7 Module: utils/cache.ls
// Simple caching utilities

function clearCaches() {
    pathCache = [:];
    losCache = [:];
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