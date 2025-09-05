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

