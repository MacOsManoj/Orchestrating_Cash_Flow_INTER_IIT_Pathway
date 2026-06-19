#!/bin/bash

################################################################################
# Bond Pipeline Multi-Terminal Launcher
# 
# This script launches the bond forecasting pipeline across multiple terminals
# ensuring proper sequencing and resource management.
#
# Usage: bash run_bond_pipeline.sh
################################################################################

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_DIR="${SCRIPT_DIR}/logs"
STARTUP_DELAY=60  # Seconds to wait before starting bond_server_manager

# Create logs directory
mkdir -p "$LOG_DIR"

# Timestamp function
log_timestamp() {
    echo "$(date '+%Y-%m-%d %H:%M:%S')"
}

# Logging functions
log_info() {
    echo -e "${BLUE}[$(log_timestamp)] ℹ️  INFO:${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(log_timestamp)] ✅ SUCCESS:${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(log_timestamp)] ⚠️  WARNING:${NC} $1"
}

log_error() {
    echo -e "${RED}[$(log_timestamp)] ❌ ERROR:${NC} $1"
}

# Function to check if Python script exists
check_script_exists() {
    if [ ! -f "$1" ]; then
        log_error "Script not found: $1"
        return 1
    fi
    return 0
}

# Function to open terminal and run command
run_in_terminal() {
    local script_name="$1"
    local command="$2"
    local log_file="$3"
    
    log_info "Launching: $script_name"
    
    # Detect OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux - use gnome-terminal or xterm
        if command -v gnome-terminal &> /dev/null; then
            gnome-terminal --title="$script_name" -- bash -c "cd '$SCRIPT_DIR' && $command; exec bash" &
        elif command -v xterm &> /dev/null; then
            xterm -title "$script_name" -e "cd '$SCRIPT_DIR' && $command; bash" &
        else
            log_error "No compatible terminal found. Please install gnome-terminal or xterm."
            return 1
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS - use Terminal.app
        osascript <<EOF
tell application "Terminal"
    do script "cd '$SCRIPT_DIR' && $command"
end tell
EOF
    else
        log_error "Unsupported OS: $OSTYPE"
        return 1
    fi
    
    log_success "$script_name started in new terminal"
    return 0
}

# Main execution
main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════════════╗"
    echo "║          Bond Forecasting Pipeline - Multi-Terminal Launcher       ║"
    echo "╚════════════════════════════════════════════════════════════════════╝"
    echo ""
    
    log_info "Pipeline working directory: $SCRIPT_DIR"
    log_info "Log directory: $LOG_DIR"
    echo ""
    
    # Verify all scripts exist
    log_info "Verifying script dependencies..."
    
    local scripts=(
        "historical_quotes_scraper.py"
        "nse_gsec_script.py"
        "pathway_producer_new.py"
        "bond_server_manager.py"
    )
    
    for script in "${scripts[@]}"; do
        if check_script_exists "$SCRIPT_DIR/$script"; then
            log_success "Found: $script"
        else
            log_error "Missing: $script"
            return 1
        fi
    done
    
    echo ""
    log_info "All dependencies verified. Starting pipeline..."
    echo ""
    
    # Store PIDs for potential cleanup
    declare -a PIDS
    
    # Step 1: Launch Historical Quotes Scraper
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "STEP 1/4: Historical Quotes Scraper"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    run_in_terminal \
        "Historical Quotes Scraper" \
        "python3 historical_quotes_scraper.py 2>&1 | tee '$LOG_DIR/scraper.log'" \
        "$LOG_DIR/scraper.log" || return 1
    
    PIDS+=($!)
    sleep 5
    
    # Step 2: Launch NSE GSEC Script with Scheduler
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "STEP 2/4: NSE GSEC Bond Fetcher (Scheduler Mode)"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    run_in_terminal \
        "NSE GSEC Scheduler" \
        "python3 nse_gsec_script.py --schedule 2>&1 | tee '$LOG_DIR/nse_gsec.log'" \
        "$LOG_DIR/nse_gsec.log" || return 1
    
    PIDS+=($!)
    sleep 5
    
    # Step 3: Launch Pathway Producer
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "STEP 3/4: Pathway Producer (Yield Forecasting)"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    run_in_terminal \
        "Pathway Producer" \
        "python3 pathway_producer_new.py 2>&1 | tee '$LOG_DIR/pathway_producer.log'" \
        "$LOG_DIR/pathway_producer.log" || return 1
    
    PIDS+=($!)
    
    # Step 4: Wait and launch Bond Server Manager
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "STEP 4/4: Waiting ${STARTUP_DELAY}s before starting Bond Server Manager..."
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Countdown timer
    for ((i = STARTUP_DELAY; i > 0; i--)); do
        if [ $((i % 10)) -eq 0 ] || [ $i -le 5 ]; then
            echo -ne "\r⏳ Starting Bond Server Manager in ${i}s...  "
        fi
        sleep 1
    done
    echo ""
    
    run_in_terminal \
        "Bond Server Manager" \
        "python3 bond_server_manager.py 2>&1 | tee '$LOG_DIR/bond_server_manager.log'" \
        "$LOG_DIR/bond_server_manager.log" || return 1
    
    PIDS+=($!)
    
    # All launched successfully
    echo ""
    echo "╔════════════════════════════════════════════════════════════════════╗"
    log_success "All components launched successfully!"
    echo "╚════════════════════════════════════════════════════════════════════╝"
    echo ""
    
    log_info "Running processes (PIDs): ${PIDS[@]}"
    log_info "Log files available in: $LOG_DIR"
    echo ""
    
    log_warning "Press Ctrl+C in any terminal to stop that component"
    log_warning "To stop all components gracefully, you may need to stop each terminal manually"
    echo ""
    
    # Keep script running and monitor
    log_info "Pipeline launcher active. Press Ctrl+C to exit (components will continue running)."
    wait
}

# Trap Ctrl+C for cleanup
trap 'log_info "Pipeline launcher interrupted. Components will continue running."; exit 0' INT

# Run main
main "$@"