# LeekWars AI - V6 Modular Combat System

A sophisticated AI combat system for [LeekWars](https://leekwars.com), featuring modular architecture, advanced tactics, and machine learning-inspired decision making.

## Overview

V6 is a complete rewrite of the V5 AI system, utilizing LeekScript's `include()` capability for modular code organization. The system features:

- **Modular Architecture**: 38 specialized modules organized by functionality
- **Advanced Combat AI**: Influence maps, Expected Incoming Damage (EID) calculations, AoE zone analysis
- **WIS-Tank Build**: Optimized for Wisdom/HP/Healing strategy
- **Performance**: 60% win rate vs agile opponents, 33% vs defensive builds

## Project Structure

```
LeekWars-AI/
├── V6_modules/          # Core AI modules
│   ├── V6_main.ls      # Main entry point
│   ├── core/           # Core systems (4 modules)
│   ├── combat/         # Combat execution (10 modules)
│   ├── movement/       # Movement & positioning (7 modules)
│   ├── strategy/       # Tactical decisions (8 modules)
│   ├── ai/             # AI decision making (5 modules)
│   └── utils/          # Utilities & helpers (4 modules)
└── tools/              # Python automation tools
    ├── lw_test_script.py       # Automated testing
    ├── lw_update_script.py     # Script updater
    └── upload_v6_complete.py   # Full deployment
```

## Key Features

### Combat System
- **Influence Mapping**: Real-time battlefield analysis
- **EID (Expected Incoming Damage)**: Predictive damage calculations
- **AoE Optimization**: Area-of-effect weapon targeting
- **Weapon Matrix**: Pre-computed damage optimization tables

### Tactical Systems
- **Anti-Tank Strategy**: Liberation-based counter to high-HP builds
- **Bait Tactics**: Predictive enemy movement exploitation
- **Phase Management**: Early/mid/late game strategies
- **Ensemble Decision Making**: Multi-strategy voting system

### Performance Optimizations
- **Operation Management**: Dynamic resource allocation
- **arrayFoldLeft/arrayFoldRight**: Functional programming for 300% better performance
- **Caching System**: Reduces redundant calculations
- **Panic Mode**: Simplified tactics under time pressure

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/LeekWars-AI.git
cd LeekWars-AI
```

2. Set up LeekWars credentials:
```bash
mkdir -p ~/.config/leekwars
echo '{"username": "your_email", "password": "your_password"}' > ~/.config/leekwars/config.json
```

3. Deploy to LeekWars:
```bash
python3 tools/upload_v6_complete.py
```

## Usage

### Testing
Run automated tests against different opponents:
```bash
# Test against specific opponent
python3 tools/lw_test_script.py 445497 15 hachess

# Test against all standard opponents
python3 tools/test_v6_all_opponents.py

# Run solo ranked fights
python3 tools/lw_solo_fights_flexible.py 1 10  # 10 fights with leek 1
python3 tools/lw_solo_fights_flexible.py 1 50 --quick  # 50 quick fights
```

### Updating
Update specific modules or the entire system:
```bash
# Update complete V6 system
python3 tools/upload_v6_complete.py

# Update single module
python3 tools/lw_update_script.py /path/to/module.ls SCRIPT_ID
```

## Recent Improvements (Sept 2024)

### Bug Fixes
- Fixed variable shadowing in influence_map.ls causing "Invalid AI" errors
- Resolved control flow issue in executeEarlyGameSequence() blocking turn 2+ combat
- Fixed turn routing to ensure proper attack execution

### Performance Gains
- Increased win rate from 0% to 60% (Rex) and 33% (Hachess)
- Expanded EID calculations from 5-10 to 15-30 cells
- Re-enabled AoE calculations with optimization

## Module Documentation

### Core Modules
- `globals.ls`: Global variables and constants
- `initialization.ls`: Turn initialization and setup
- `operations.ls`: Operation budget management
- `state_management.ls`: Game state tracking

### Combat Modules
- `execute_combat.ls`: Main combat execution
- `damage_calculation.ls`: Damage formulas and calculations
- `weapon_management.ls`: Weapon selection and usage
- `chip_management.ls`: Chip (ability) usage optimization

### AI Modules
- `decision_making.ls`: Main decision tree
- `eid_system.ls`: Expected Incoming Damage calculations
- `influence_map.ls`: Battlefield influence mapping
- `evaluation.ls`: Position and action evaluation

## Contributing

Contributions are welcome! Please ensure:
- Code follows existing LeekScript conventions
- New features include appropriate debug logging
- Changes are tested against multiple opponent types
- Performance impact is measured (operation count)

## License

This project is open source. Feel free to use and modify for your own LeekWars AI development.

## Acknowledgments

- LeekWars community for testing and feedback
- Original V5 system contributors
- LeekScript documentation maintainers