// V6 Module: movement/distance.ls
// Distance calculations
// Auto-generated from V5.0 script

// Function: manhattanDistance
function manhattanDistance(cell1, cell2) {
    if (cell1 == null || cell1 == -1 || cell2 == null || cell2 == -1) {
        return 999999;
    }
    return abs(getCellX(cell1) - getCellX(cell2)) + 
           abs(getCellY(cell1) - getCellY(cell2));
}

// Function: getCellFromOffset
function getCellFromOffset(baseCell, offsetX, offsetY) {
    var x = getCellX(baseCell) + offsetX;
    var y = getCellY(baseCell) + offsetY;
    return getCellFromXY(x, y);
}

// Function: getCellsInRange
function getCellsInRange(center, maxRange) {
    // Returns array of cells within range, sorted by distance
    var cells = [];
    var centerX = getCellX(center);
    var centerY = getCellY(center);
    
    // Scan area around center
    for (var x = centerX - maxRange; x <= centerX + maxRange; x++) {
        for (var y = centerY - maxRange; y <= centerY + maxRange; y++) {
            var cell = getCellFromXY(x, y);
            if (cell != null) {
                var dist = getCellDistance(center, cell);
                if (dist <= maxRange) {
                    push(cells, cell);
                }
            }
        }
    }
    
    return cells;
}

// Function: getCellsAtDistance
function getCellsAtDistance(center, targetDistance) {
    // Returns array of cells exactly at targetDistance
    var cells = [];
    var centerX = getCellX(center);
    var centerY = getCellY(center);
    
    // Scan area around center
    for (var x = centerX - targetDistance; x <= centerX + targetDistance; x++) {
        for (var y = centerY - targetDistance; y <= centerY + targetDistance; y++) {
            var cell = getCellFromXY(x, y);
            if (cell != null) {
                var dist = getCellDistance(center, cell);
                if (dist == targetDistance) {
                    push(cells, cell);
                }
            }
        }
    }
    
    return cells;
}

// Function: getCellsInRangeWithLOS
function getCellsInRangeWithLOS(center, target, maxRange) {
    // Returns cells with line of sight to target
    var cells = getCellsInRange(center, maxRange);
    var result = [];
    
    for (var i = 0; i < count(cells); i++) {
        var cell = cells[i];
        if (lineOfSight(cell, target, target)) {
            push(result, cell);
        }
    }
    
    return result;
}