var enemy = getNearestEnemy();
if (enemy == null) {
    return;
}

var weapons = getWeapons();
var weapon = null;
if (weapons != null && count(weapons) > 0) {
    var order = [WEAPON_PISTOL, WEAPON_MACHINE_GUN, WEAPON_SWORD, WEAPON_MAGNUM, WEAPON_B_LASER, WEAPON_RIFLE];
    for (var i = 0; i < count(order); i++) {
        if (inArray(weapons, order[i])) {
            weapon = order[i];
            break;
        }
    }
    if (weapon == null) {
        weapon = weapons[0];
    }
}

// Move toward enemy until in range
var minRange = (weapon != null) ? getWeaponMinRange(weapon) : 1;
var maxRange = (weapon != null) ? getWeaponMaxRange(weapon) : 1;
while (getMP() > 0) {
    var enemyCell = getCell(enemy);
    if (enemyCell == null) {
        break;
    }
    var dist = getCellDistance(getCell(), enemyCell);
    if (weapon != null && dist >= minRange && dist <= maxRange && checkAlignedLOS(weapon, getCell(), enemyCell)) {
        break;
    }
        if (!seekAlignment(weapon, enemyCell, minRange, maxRange, enemy)) {
            break;
        }
}

// Equip weapon if needed
if (weapon != null && getWeapon() != weapon && getTP() > 0) {
    setWeapon(weapon);
}

// Try to shoot
var shot = false;
if (weapon != null) {
    var cost = getWeaponCost(weapon);
    while (getTP() >= cost) {
        var enemyCell = getCell(enemy);
        if (enemyCell == null) break;
        var dist = getCellDistance(getCell(), enemyCell);
        if (dist < getWeaponMinRange(weapon) || dist > getWeaponMaxRange(weapon)) break;
        if (!checkAlignedLOS(weapon, getCell(), enemyCell)) break;
        if (useWeapon(enemy) > 0) {
            shot = true;
        } else {
            break;
        }
    }
}

// Step back if shot succeeded
if (shot && getMP() > 0) {
    var myCell = getCell();
    var enemyCell = getCell(enemy);
    if (enemyCell != null) {
        var dx = getCellX(myCell) - getCellX(enemyCell);
        dx = (dx > 0) ? 1 : (dx < 0 ? -1 : 0);
        var dy = getCellY(myCell) - getCellY(enemyCell);
        dy = (dy > 0) ? 1 : (dy < 0 ? -1 : 0);
        var targetCell = getCellFromXY(getCellX(myCell) + dx, getCellY(myCell) + dy);
        if (targetCell != null && targetCell != -1 && getCellContent(targetCell) == CELL_EMPTY) {
            moveTowardCell(targetCell);
        }
    }
} else {
    // otherwise keep moving closer if possible
    while (getMP() > 0) {
        var enemyCell = getCell(enemy);
        if (enemyCell == null) break;
        var dist = getCellDistance(getCell(), enemyCell);
        if (weapon != null && dist >= getWeaponMinRange(weapon) && dist <= getWeaponMaxRange(weapon) && checkAlignedLOS(weapon, getCell(), enemyCell)) {
            var cost = getWeaponCost(weapon);
            while (getTP() >= cost) {
                if (useWeapon(enemy) <= 0) {
                    break;
                }
            }
            break;
        }
        if (!seekAlignment(weapon, enemyCell, getWeaponMinRange(weapon), getWeaponMaxRange(weapon), enemy)) {
            break;
        }
    }
}

function checkAlignedLOS(weapon, fromCell, targetCell) {
    if (!lineOfSight(fromCell, targetCell)) {
        return false;
    }
    var launch = getWeaponLaunchType(weapon);
    if (launch == LAUNCH_TYPE_LINE || launch == LAUNCH_TYPE_LINE_INVERTED) {
        return getCellX(fromCell) == getCellX(targetCell) || getCellY(fromCell) == getCellY(targetCell);
    }
    if (launch == LAUNCH_TYPE_DIAGONAL || launch == LAUNCH_TYPE_DIAGONAL_INVERTED) {
        return abs(getCellX(fromCell) - getCellX(targetCell)) == abs(getCellY(fromCell) - getCellY(targetCell));
    }
    if (launch == LAUNCH_TYPE_STAR || launch == LAUNCH_TYPE_STAR_INVERTED) {
        var alignedLine = getCellX(fromCell) == getCellX(targetCell) || getCellY(fromCell) == getCellY(targetCell);
        var alignedDiag = abs(getCellX(fromCell) - getCellX(targetCell)) == abs(getCellY(fromCell) - getCellY(targetCell));
        return alignedLine || alignedDiag;
    }
    return true;
}

function seekAlignment(weapon, enemyCell, minRange, maxRange, enemy) {
    var moved = false;
    if (weapon != null) {
        var launch = getWeaponLaunchType(weapon);
        if (launch == LAUNCH_TYPE_LINE || launch == LAUNCH_TYPE_LINE_INVERTED) {
            moved = stepAlignLine(enemyCell, minRange, maxRange);
        }
    }
    if (!moved) {
        var before = getMP();
        moveToward(enemy);
        moved = getMP() < before;
    }
    return moved;
}

function stepAlignLine(enemyCell, minRange, maxRange) {
    var myCell = getCell();
    var myX = getCellX(myCell);
    var myY = getCellY(myCell);
    var enemyX = getCellX(enemyCell);
    var enemyY = getCellY(enemyCell);
    var targets = [];

    if (myX != enemyX) {
        var stepX = myX + ((enemyX > myX) ? 1 : -1);
        push(targets, getCellFromXY(stepX, myY));
    }
    if (myY != enemyY) {
        var stepY = myY + ((enemyY > myY) ? 1 : -1);
        push(targets, getCellFromXY(myX, stepY));
    }

    for (var i = 0; i < count(targets); i++) {
        var cell = targets[i];
        if (cell == null || cell == -1) continue;
        if (getCellContent(cell) != CELL_EMPTY) continue;
        var dist = getCellDistance(cell, enemyCell);
        if (dist < minRange || dist > maxRange) continue;
        var before = getMP();
        moveTowardCell(cell);
        if (getMP() < before) {
            return true;
        }
    }
    return false;
}
