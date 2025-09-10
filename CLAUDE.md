# CLAUDE.md - LeekWars V6 AI Development Guide

## Overview
This document provides context for Claude Code when working on the LeekWars V6 AI system. It covers the development workflow, testing procedures, and current implementation status.

## Project Structure
```
LeekWars-AI/
├── V6_modules/          # Core AI modules (56 total)
│   ├── V6_main.ls      # Main entry point
│   ├── core/           # Core systems (4 modules)
│   ├── combat/         # Combat execution (18 modules including refactored versions)
│   ├── movement/       # Movement & positioning (7 modules)
│   ├── strategy/       # Tactical decisions (9 modules)
│   ├── ai/             # AI decision making (10 modules with refactored versions)
│   ├── utils/          # Utilities & helpers (4 modules)
│   └── blaser/         # B-Laser weapon support (2 modules)
└── tools/              # Python automation tools
    ├── lw_test_script.py       # Automated testing with log retrieval
    ├── upload_v6_complete.py   # Full deployment script
    └── analyze_combat_logs.py  # Log analysis tool
```

## Key Commands & Workflows

### 1. Upload V6 AI to LeekWars
```bash
python3 tools/upload_v6_complete.py
```
Uploads all 56 modules to LeekWars under the 6.0/V6/ folder structure.

### 2. Run Test Fights with Log Retrieval
```bash
# Test against specific opponent (with automatic log retrieval)
python3 tools/lw_test_script.py <script_id> <num_tests> <opponent>

# Example: 20 fights against Domingo
python3 tools/lw_test_script.py 445497 20 domingo

# Available opponents:
# - domingo: Balanced, 600 strength
# - betalpha: Magic build, 600 magic  
# - tisma: Wisdom/Science, 600 wisdom
# - guj: Tank, 5000 life
# - hachess: Defensive, 600 resistance
# - rex: Agile, 600 agility
```

## Current V6 AI Status

### Latest Implementation (September 2025)
- **Total Modules**: 56 modules across all subsystems
- **Multi-Weapon Support**: Automatic detection and adaptation to any weapon loadout
- **Advanced Features**: Multi-enemy support, EID positioning, ensemble decision-making, operation optimization
- **Recent Additions**: Flame Thrower weapon support with poison DoT calculations

### Key Features
- **Dynamic Operations Budget**: Adapts to leek core count (`getCores() * 1000000`)
- **Smart Weapon Selection**: Damage-per-TP calculations with line alignment checks
- **Advanced Positioning**: Weapon-aware positioning prevents "dead zones"
- **Multi-Hit Optimization**: M-Laser pierces multiple enemies, Grenade AoE targeting
- **Operation Efficiency**: 87.9% operation budget utilization in recent tests

## Major System Components

### Core Systems ⭐⭐⭐⭐⭐
- **Dynamic operations budget**: Adapts to leek core count
- **Smooth operation degradation**: OPTIMAL → EFFICIENT → SURVIVAL → PANIC modes
- **Multi-weapon architecture**: Full backward compatibility with single-weapon scenarios

### Combat System ⭐⭐⭐⭐ 
- **Smart attack prioritization**: Damage-per-TP calculations for optimal weapon selection
- **Multi-hit optimization**: M-Laser pierces multiple enemies, Grenade AoE targeting
- **Weapon-aware positioning**: Prevents getting stuck in "weapon dead zones"
- **Flame Thrower support**: Line weapon with poison DoT calculations

### Movement & Positioning ⭐⭐⭐⭐
- **A* pathfinding** with operation-aware fallback
- **Teleportation system**: Proper validation and post-teleport movement
- **EID-based positioning**: Uses Expected Incoming Damage for proactive positioning

### AI Decision Making ⭐⭐⭐⭐
- **Refactored modular system**: Split from monolithic 963-line module into focused components
- **Emergency decisions**: Panic mode and emergency handling
- **Tactical decisions**: Strategic positioning and teleportation
- **Combat decisions**: Attack execution and kill strategies

## Recent Updates (September 2025)

### Weapon Support Enhancements
- **Flame Thrower**: Level 90 line weapon (2-8 range) with poison DoT
- **M-Laser prioritization**: Fixed alignment checks and weapon selection
- **Multi-weapon adaptation**: Automatic detection of equipped weapons

### Bug Fixes
- **Variable reference errors**: Fixed `myMagic` global variable usage
- **Positioning priorities**: Flame Thrower preferred over Destroyer at optimal range
- **Line alignment**: Proper `isOnSameLine()` checks for all line weapons

### Performance Optimizations
- **Operation utilization**: Achieved 87.9% operation budget usage
- **Smart position analysis**: Focuses on weapon-relevant ranges
- **Debug system**: Tiered logging based on operation cost

## System Strengths
1. **Modular Architecture**: 56 well-organized modules with clear separation of concerns
2. **Multi-Weapon Support**: Automatically adapts to any weapon loadout
3. **Advanced AI Features**: EID positioning, ensemble decisions, pattern learning
4. **Operation Efficiency**: Utilizes 87.9% of available computational budget
5. **Multi-Enemy Ready**: Full support for team battles and FFA modes
6. **Smart Positioning**: Weapon-aware positioning prevents tactical dead zones

## Development Best Practices

1. **Testing**: Always run 10-20 fights per opponent for statistical significance
2. **Incremental Changes**: Test after each modification to measure impact
3. **Log Analysis**: Use combat logs to identify patterns in wins/losses
4. **Modular Development**: Leverage the refactored architecture for easier maintenance


## Important Files to Monitor

- `V6_modules/V6_main.ls` - Main entry point
- `V6_modules/core/globals.ls` - Global constants and thresholds
- `V6_modules/combat/execute_combat.ls` - Combat execution
- `V6_modules/ai/decision_making_refactored.ls` - Refactored decision logic
- `V6_modules/combat/weapon_selection.ls` - Weapon prioritization

## Contact & Resources

- LeekWars Game: https://leekwars.com
- Main Script ID: 445497 (V6_main)
- Test Farmer Account: Virus (ID: 18035)

---
*Last Updated: September 2025*
*Document Version: 3.0*



## V6.1 Refactoring Summary

*Completed: January 2025*

### Key Achievements
- **AI Decision Making**: Refactored from 963-line monolith into 4 focused modules (595 lines total)
- **Combat Execution**: Split 1,952-line module into 4 components (755 lines total)  
- **Debug Optimization**: Tiered logging system based on operation cost
- **Code Reduction**: 53.7% reduction through better organization
- **Backward Compatibility**: 100% maintained with `_refactored` suffix pattern

