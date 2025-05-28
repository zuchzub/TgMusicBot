#!/bin/bash

# Make it executable by : chmod +x setup.sh
# You can run it after cloning with: ./setup.sh

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to display error and exit
error_exit() {
    echo -e "${RED}Error: $1${NC}" >&2
    exit 1
}

# Function to validate integer input
validate_int() {
    if [[ ! "$1" =~ ^[0-9]+$ ]]; then
        error_exit "Please enter a valid integer for $2"
    fi
}

# Function to validate URL input
validate_url() {
    if [[ -n "$1" && ! "$1" =~ ^https?:// ]]; then
        error_exit "Please enter a valid URL for $2 (starting with http:// or https://)"
    fi
}

# Function to validate boolean input
validate_bool() {
    local lower=${1,,}
    if [[ ! "$lower" =~ ^(true|false)$ ]]; then
        error_exit "Please enter either 'True' or 'False' for $2"
    fi
}

# Function to ask for environment variables
ask_env() {
    local var_name=$1
    local prompt=$2
    local default=$3
    local validate_func=$4
    local secret=$5

    while true; do
        if [ "$secret" = "true" ]; then
            read -s -p "$prompt [$default]: " value
            echo
        else
            read -p "$prompt [$default]: " value
        fi

        value=${value:-$default}

        if [ -n "$validate_func" ]; then
            $validate_func "$value" "$var_name" || continue
        fi

        break
    done

    echo "$value"
}

# Main installation function
install_tgmusicbot() {
    echo -e "${GREEN}Starting TgMusicBot installation...${NC}"

    # Step 1: System Preparation
    echo -e "${YELLOW}Updating system packages...${NC}"
    sudo apt-get update && sudo apt-get upgrade -y || error_exit "Failed to update system packages"

    echo -e "${YELLOW}Installing required tools...${NC}"
    sudo apt-get install git python3-pip ffmpeg tmux -y || error_exit "Failed to install required packages"

    # Step 2: Python Environment
    echo -e "${YELLOW}Setting up Python environment...${NC}"
    pip3 install uv || error_exit "Failed to install uv"
    uv venv || error_exit "Failed to create virtual environment"

    # Activate virtual environment
    source .venv/bin/activate || error_exit "Failed to activate virtual environment"

    # Install dependencies
    uv pip install -e . || error_exit "Failed to install dependencies"

    # Step 3: Configuration
    echo -e "${YELLOW}Configuring environment variables...${NC}"
    [ -f sample.env ] && cp sample.env .env || touch .env

    # Collect environment variables
    API_ID=$(ask_env "API_ID" "Enter your Telegram API ID" "" validate_int)
    API_HASH=$(ask_env "API_HASH" "Enter your Telegram API Hash" "" "" "true")
    TOKEN=$(ask_env "TOKEN" "Enter your bot token" "" "" "true")
    MIN_MEMBER_COUNT=$(ask_env "MIN_MEMBER_COUNT" "Enter minimum member count" "50" validate_int)

    # Session strings
    SESSION_STRINGS=()
    echo -e "${YELLOW}Setting up session strings (up to 10, leave empty to skip):${NC}"
    for i in {1..10}; do
        STRING=$(ask_env "STRING$i" "  Enter STRING$i (leave empty to skip)" "")
        if [ -n "$STRING" ]; then
            SESSION_STRINGS+=("$STRING")
        else
            break
        fi
    done

    OWNER_ID=$(ask_env "OWNER_ID" "Enter owner ID" "5938660179" validate_int)
    LOGGER_ID=$(ask_env "LOGGER_ID" "Enter logger ID (0 to disable)" "0" validate_int)
    MONGO_URI=$(ask_env "MONGO_URI" "Enter MongoDB URI (leave empty if not using)" "")
    API_URL=$(ask_env "API_URL" "Enter API URL (leave empty if not using)" "" validate_url)
    API_KEY=$(ask_env "API_KEY" "Enter API key (leave empty if not using)" "" "" "true")
    PROXY=$(ask_env "PROXY" "Enter proxy URL (leave empty if not using)" "" validate_url)
    DEFAULT_SERVICE=$(ask_env "DEFAULT_SERVICE" "Enter default service (youtube, etc)" "youtube")
    DOWNLOADS_DIR=$(ask_env "DOWNLOADS_DIR" "Enter downloads directory" "database/music")
    SUPPORT_GROUP=$(ask_env "SUPPORT_GROUP" "Enter support group URL" "https://t.me/GuardxSupport" validate_url)
    SUPPORT_CHANNEL=$(ask_env "SUPPORT_CHANNEL" "Enter support channel URL" "https://t.me/FallenProjects" validate_url)
    IGNORE_BACKGROUND_UPDATES=$(ask_env "IGNORE_BACKGROUND_UPDATES" "Ignore background updates? (True/False)" "True" validate_bool)
    AUTO_LEAVE=$(ask_env "AUTO_LEAVE" "Enable auto leave? (True/False)" "True" validate_bool)
    COOKIES_URL=$(ask_env "COOKIES_URL" "Enter cookies URL(s) comma separated (leave empty if not using)" "")
    DEVS=$(ask_env "DEVS" "Enter developer IDs space separated (leave empty if none)" "")

    # Write to .env file
    echo -e "${YELLOW}Writing configuration to .env file...${NC}"
    {
        echo "API_ID=$API_ID"
        echo "API_HASH=$API_HASH"
        echo "TOKEN=$TOKEN"
        echo "MIN_MEMBER_COUNT=$MIN_MEMBER_COUNT"

        # Write session strings
        for i in "${!SESSION_STRINGS[@]}"; do
            echo "STRING$((i+1))=${SESSION_STRINGS[i]}"
        done

        echo "OWNER_ID=$OWNER_ID"
        echo "LOGGER_ID=$LOGGER_ID"
        [ -n "$MONGO_URI" ] && echo "MONGO_URI=$MONGO_URI"
        [ -n "$API_URL" ] && echo "API_URL=$API_URL"
        [ -n "$API_KEY" ] && echo "API_KEY=$API_KEY"
        [ -n "$PROXY" ] && echo "PROXY=$PROXY"
        echo "DEFAULT_SERVICE=$DEFAULT_SERVICE"
        echo "DOWNLOADS_DIR=$DOWNLOADS_DIR"
        echo "SUPPORT_GROUP=$SUPPORT_GROUP"
        echo "SUPPORT_CHANNEL=$SUPPORT_CHANNEL"
        echo "IGNORE_BACKGROUND_UPDATES=$IGNORE_BACKGROUND_UPDATES"
        echo "AUTO_LEAVE=$AUTO_LEAVE"
        [ -n "$COOKIES_URL" ] && echo "COOKIES_URL=$COOKIES_URL"
        [ -n "$DEVS" ] && echo "DEVS=$DEVS"
    } > .env

    # Final instructions
    echo -e "${GREEN}Installation complete!${NC}"
    echo -e "${YELLOW}To start the bot, run these commands:${NC}"
    echo "tmux new -s musicbot"
    echo "tgmusic"
    echo
    echo -e "${YELLOW}Tmux cheatsheet:${NC}"
    echo "Detach: Ctrl+B then D"
    echo "Reattach: tmux attach -t musicbot"
    echo "Kill session: tmux kill-session -t musicbot"
}

# Run the installation
install_tgmusicbot
