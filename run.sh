#!/bin/bash
# LeekWars V6 AI Management Script

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Ensure we're in the right directory
cd "$(dirname "$0")"

echo -e "${BLUE}=====================================${NC}"
echo -e "${BLUE}   LeekWars V6 AI Management Tool${NC}"
echo -e "${BLUE}=====================================${NC}"
echo ""

function show_menu() {
    echo "Available commands:"
    echo "  1) upload    - Upload V6 to LeekWars"
    echo "  2) test      - Run tests (specify opponent)"
    echo "  3) test-all  - Test against all opponents"
    echo "  4) update    - Update specific module"
    echo "  5) setup     - Install Python dependencies"
    echo "  6) git-push  - Commit and push to GitHub"
    echo "  0) exit      - Exit"
    echo ""
}

function upload_v6() {
    echo -e "${YELLOW}Uploading V6 modules to LeekWars...${NC}"
    python3 tools/upload_v6_complete.py
}

function test_opponent() {
    echo -e "${YELLOW}Available opponents:${NC}"
    echo "  - hachess (Defensive, 600 resistance)"
    echo "  - rex (Agile, 600 agility)"
    echo "  - betalpha (Magic, 600 magic)"
    echo "  - tisma (Wisdom, 600 wisdom)"
    echo "  - guj (Tank, 5000 HP)"
    echo ""
    read -p "Enter opponent name: " opponent
    read -p "Number of tests (default 15): " num_tests
    num_tests=${num_tests:-15}
    
    echo -e "${YELLOW}Running $num_tests tests against $opponent...${NC}"
    python3 tools/lw_test_script.py 445497 $num_tests $opponent
}

function test_all() {
    echo -e "${YELLOW}Testing against all standard opponents...${NC}"
    for opponent in hachess rex betalpha tisma guj; do
        echo -e "${BLUE}Testing vs $opponent...${NC}"
        python3 tools/lw_test_script.py 445497 5 $opponent
    done
}

function update_module() {
    read -p "Enter module path (e.g., ai/decision_making.ls): " module
    if [ -f "V6_modules/$module" ]; then
        echo -e "${YELLOW}Updating $module...${NC}"
        # Need to implement module-specific update
        echo "Feature coming soon..."
    else
        echo -e "${RED}Module not found: V6_modules/$module${NC}"
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
    read -p "Enter command (0-6): " choice
    echo ""
    
    case $choice in
        1|upload)
            upload_v6
            ;;
        2|test)
            test_opponent
            ;;
        3|test-all)
            test_all
            ;;
        4|update)
            update_module
            ;;
        5|setup)
            setup_env
            ;;
        6|git-push)
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