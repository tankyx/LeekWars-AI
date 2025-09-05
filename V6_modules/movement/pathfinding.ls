// V6 Module: movement/pathfinding.ls
// A* pathfinding algorithm
// Auto-generated from V5.0 script

// Function: aStar
function aStar(start, goal, maxOps) {
    if (start == goal) return [start];
    if (maxOps == null) maxOps = 50000;  // Default ops budget for pathfinding
    
    var openSet = [];
    var closedSet = [:];
    var cameFrom = [:];
    var gScore = [:];
    var fScore = [:];
    
    // Initialize start node
    gScore[start] = 0;
    fScore[start] = manhattanDistance(start, goal);
    push(openSet, [start, 0, fScore[start]]);
    
    var opsUsed = 0;
    var nodesEvaluated = 0;
    
    while (count(openSet) > 0 && opsUsed < maxOps) {
        // Find node with lowest f score
        var currentIndex = 0;
        var lowestF = openSet[0][2];
        
        for (var i = 1; i < count(openSet); i++) {
            if (openSet[i][2] < lowestF) {
                lowestF = openSet[i][2];
                currentIndex = i;
            }
        }
        
        var current = openSet[currentIndex];
        var currentCell = current[0];
        
        // Found goal!
        if (currentCell == goal) {
            return reconstructPath(cameFrom, currentCell);
        }
        
        // Move from open to closed
        removeElement(openSet, openSet[currentIndex]);
        closedSet[currentCell] = true;
        nodesEvaluated++;
        
        // Explore neighbors
        var neighbors = getNeighborCells(currentCell);
        
        for (var i = 0; i < count(neighbors); i++) {
            var neighbor = neighbors[i];
            
            // Skip invalid cells
            if (neighbor == null || neighbor == -1) continue;
            
            // Skip obstacles and already evaluated
            if (isObstacle(neighbor) || mapGet(closedSet, neighbor, false)) {
                continue;
            }
            
            // Skip enemy cell (can't move through enemy)
            if (neighbor == enemyCell) continue;
            
            // Calculate tentative g score
            var moveCost = 1;  // Base movement cost
            
            // Add penalty for dangerous cells
            if (enemy != null) {
                var distToEnemy = getCellDistance(neighbor, enemyCell);
                if (distToEnemy <= 2) {
                    moveCost += 3;  // Heavy penalty for very close to enemy
                } else if (distToEnemy <= 4) {
                    moveCost += 1;  // Light penalty for moderately close
                }
            }
            
            var tentativeG = mapGet(gScore, currentCell, 999999) + moveCost;
            var currentG = mapGet(gScore, neighbor, 999999);
            
            if (tentativeG < currentG) {
                // This path to neighbor is better
                cameFrom[neighbor] = currentCell;
                gScore[neighbor] = tentativeG;
                fScore[neighbor] = tentativeG + manhattanDistance(neighbor, goal);
                
                // Add to open set if not already there
                var inOpenSet = false;
                for (var j = 0; j < count(openSet); j++) {
                    if (openSet[j][0] == neighbor) {
                        openSet[j][1] = tentativeG;
                        openSet[j][2] = fScore[neighbor];
                        inOpenSet = true;
                        break;
                    }
                }
                
                if (!inOpenSet) {
                    push(openSet, [neighbor, tentativeG, fScore[neighbor]]);
                }
            }
        }
        
        opsUsed += 100;
        
        // Limit nodes to prevent timeout
        if (nodesEvaluated > 500) {
            debugLog("A* reached node limit, using partial path");
            break;
        }
    }
    
    // No path found - return null
    return null;
}


// Function: reconstructPath
function reconstructPath(cameFrom, current) {
    var path = [current];
    
    while (mapGet(cameFrom, current, null) != null) {
        current = cameFrom[current];
        unshift(path, current);  // Add to front
    }
    
    return path;
}


// Function: findBestPathTo
function findBestPathTo(targetCell, maxMP) {
    // Use A* to find optimal path
    var path = aStar(myCell, targetCell, 50000);
    
    if (path == null || count(path) == 0) {
        // No path found, fall back to direct approach
        debugLog("No A* path found to " + targetCell);
        return null;
    }
    
    // Return the next steps up to our MP
    var steps = [];
    for (var i = 1; i < min(count(path), maxMP + 1); i++) {
        push(steps, path[i]);
    }
    
    return steps;
}

// === SMOOTH OPERATIONAL MANAGEMENT ===

// Function: getNeighborCells
function getNeighborCells(cell) {
    if (cell == null || cell == -1) return [];
    
    var x = getCellX(cell);
    var y = getCellY(cell);
    var neighbors = [];
    
    // 4-way movement (no diagonals in LeekWars)
    var offsets = [[1, 0], [-1, 0], [0, 1], [0, -1]];
    
    for (var i = 0; i < count(offsets); i++) {
        var nx = x + offsets[i][0];
        var ny = y + offsets[i][1];
        var neighborCell = getCellFromXY(nx, ny);
        
        if (neighborCell != null && neighborCell != -1) {
            push(neighbors, neighborCell);
        }
    }
    
    return neighbors;
}

