#!/bin/bash
# LeekWars V7 AI Management Script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Ensure we're in the right directory
cd "$(dirname "$0")"

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}   LeekWars V7 AI Management Tool${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""

function show_menu() {
    echo "Available commands:"
    echo "  1) upload      - Upload V7 to LeekWars"
    echo "  2) test        - Run bot tests (specify opponent)"
    echo "  3) test-all    - Run bot tests for all opponents"
    echo "  4) team        - Run team fights (all compositions)"
    echo "  5) farmer      - Run farmer fights (garden/challenge)"
    echo "  6) boss        - Run boss fights (websocket env)"
    echo "  7) validate    - Validate script (websocket env)"
    echo "  8) update      - Update LeekScript from local file"
    echo "  9) setup       - Install Python dependencies"
    echo "  10) git-push   - Commit and push to GitHub"
    echo "  0) exit        - Exit"
    echo ""
}

DEFAULT_SCRIPT_ID=446029

function upload_v7() {
    echo -e "${YELLOW}Uploading V7 modules to LeekWars...${NC}"
    python3 tools/upload_v7.py
}

function test_opponent() {
    echo -e "${YELLOW}Available opponents:${NC}"
    echo "  - domingo  (Balanced, 600 strength)"
    echo "  - betalpha (Magic, 600 magic)"
    echo "  - tisma    (Wisdom/Science, 600 wisdom)"
    echo "  - guj      (Tank, 5000 HP)"
    echo "  - hachess  (Defensive, 600 resistance)"
    echo "  - rex      (Agile, 600 agility)"
    echo ""
    read -p "Enter script ID (default ${DEFAULT_SCRIPT_ID}): " script_id
    script_id=${script_id:-$DEFAULT_SCRIPT_ID}
    read -p "Enter opponent name: " opponent
    read -p "Number of tests (default 15): " num_tests
    num_tests=${num_tests:-15}
    
    echo -e "${YELLOW}Running $num_tests tests against $opponent (script $script_id)...${NC}"
    python3 tools/lw_test_script.py "$script_id" "$num_tests" "$opponent"
}

function test_all() {
    read -p "Enter script ID (default ${DEFAULT_SCRIPT_ID}): " script_id
    script_id=${script_id:-$DEFAULT_SCRIPT_ID}
    echo -e "${YELLOW}Testing against all standard opponents (script $script_id)...${NC}"
    for opponent in domingo betalpha tisma guj hachess rex; do
        echo -e "${BLUE}Testing vs $opponent...${NC}"
        python3 tools/lw_test_script.py "$script_id" 5 "$opponent"
    done
}

function team_fights() {
    echo -e "${YELLOW}Running team fights for all compositions...${NC}"
    read -p "Use --quick mode? (y/N): " quick
    if [[ "$quick" =~ ^[Yy]$ ]]; then
        python3 tools/lw_team_fights_all.py --quick
    else
        python3 tools/lw_team_fights_all.py
    fi
}

function farmer_fights() {
    echo -e "${YELLOW}Farmer fights modes:${NC}"
    echo "  - garden"
    echo "  - challenge"
    read -p "Choose mode: " mode
    case "$mode" in
        garden)
            read -p "Number of fights (default 5): " num
            num=${num:-5}
            python3 tools/lw_farmer_fights.py garden "$num"
            ;;
        challenge)
            read -p "Farmer ID: " fid
            read -p "Number of fights (default 3): " num
            num=${num:-3}
            read -p "Seed (optional): " seed
            read -p "Side (L/R, optional): " side
            read -p "Use --quick? (y/N): " quick
            cmd=(python3 tools/lw_farmer_fights.py challenge "$fid" "$num")
            [[ -n "$seed" ]] && cmd+=(--seed "$seed")
            [[ -n "$side" ]] && cmd+=(--side "$side")
            [[ "$quick" =~ ^[Yy]$ ]] && cmd+=(--quick)
            echo -e "${YELLOW}Running: ${cmd[*]}${NC}"
            "${cmd[@]}"
            ;;
        *)
            echo -e "${RED}Invalid mode${NC}"
            ;;
    esac
}

function boss_fights() {
    if [ ! -f websocket_env/bin/activate ]; then
        echo -e "${RED}websocket_env not found. Boss tools require the websocket venv.${NC}"
        echo "Expected at: websocket_env/bin/activate"
        return 1
    fi
    read -p "Boss number (1-3, default 2): " boss
    boss=${boss:-2}
    read -p "Number of fights (default 5): " num
    num=${num:-5}
    read -p "Use --quick? (y/N): " quick
    echo -e "${YELLOW}Activating websocket venv...${NC}"
    source websocket_env/bin/activate
    if [[ "$quick" =~ ^[Yy]$ ]]; then
        python3 tools/lw_boss_fights.py "$boss" "$num" --quick
    else
        python3 tools/lw_boss_fights.py "$boss" "$num"
    fi
    deactivate
}

function validate_script() {
    if [ ! -f websocket_env/bin/activate ]; then
        echo -e "${RED}websocket_env not found. Validation tools require the websocket venv.${NC}"
        return 1
    fi
    echo -e "${YELLOW}Validation mode:${NC}"
    echo "  r) Remote script by ID"
    echo "  l) Local file against script ID"
    read -p "Choose (r/l, default r): " mode
    mode=${mode:-r}
    source websocket_env/bin/activate
    if [[ "$mode" == "l" ]]; then
        read -p "Local file path (default V7_modules/V7_main.ls): " file
        file=${file:-V7_modules/V7_main.ls}
        read -p "Script ID (default ${DEFAULT_SCRIPT_ID}): " sid
        sid=${sid:-$DEFAULT_SCRIPT_ID}
        python3 tools/validate_local_file.py "$file" "$sid"
    else
        read -p "Script ID (default ${DEFAULT_SCRIPT_ID}): " sid
        sid=${sid:-$DEFAULT_SCRIPT_ID}
        python3 tools/validate_script.py "$sid"
    fi
    deactivate
}

function update_module() {
    read -p "Enter local file path (e.g., V7_modules/V7_main.ls): " module
    read -p "Enter script ID (default ${DEFAULT_SCRIPT_ID}): " sid
    sid=${sid:-$DEFAULT_SCRIPT_ID}
    if [ -f "$module" ]; then
        echo -e "${YELLOW}Updating script $sid from $module...${NC}"
        python3 tools/lw_update_script.py "$module" "$sid"
    else
        echo -e "${RED}File not found: $module${NC}"
    fi
}

function setup_env() {
    echo -e "${YELLOW}Installing Python dependencies...${NC}"
    pip3 install -r requirements.txt
    
    echo -e "${YELLOW}Setting up LeekWars credentials...${NC}"
    mkdir -p ~/.config/leekwars
    
    if [ ! -f ~/.config/leekwars/config.json ]; then
        read -p "Enter LeekWars email: " email
        read -sp "Enter LeekWars password: " password
        echo ""
        echo "{\"username\": \"$email\", \"password\": \"$password\"}" > ~/.config/leekwars/config.json
        chmod 600 ~/.config/leekwars/config.json
        echo -e "${GREEN}✅ Credentials saved${NC}"
    else
        echo -e "${GREEN}✅ Credentials already configured${NC}"
    fi
}

function git_push() {
    echo -e "${YELLOW}Preparing GitHub push...${NC}"
    git add .
    read -p "Enter commit message: " msg
    git commit -m "$msg"
    git push origin main
    echo -e "${GREEN}✅ Pushed to GitHub${NC}"
}

# Main loop
while true; do
    show_menu
    read -p "Enter command (0-10): " choice
    echo ""
    
    case $choice in
        1|upload)
            upload_v7
            ;;
        2|test)
            test_opponent
            ;;
        3|test-all)
            test_all
            ;;
        4|team)
            team_fights
            ;;
        5|farmer)
            farmer_fights
            ;;
        6|boss)
            boss_fights
            ;;
        7|validate)
            validate_script
            ;;
        8|update)
            update_module
            ;;
        9|setup)
            setup_env
            ;;
        10|git-push)
            git_push
            ;;
        0|exit)
            echo -e "${GREEN}Goodbye!${NC}"
            exit 0
            ;;
        *)
            echo -e "${RED}Invalid option${NC}"
            ;;
    esac
    
    echo ""
    read -p "Press Enter to continue..."
    echo ""
done
