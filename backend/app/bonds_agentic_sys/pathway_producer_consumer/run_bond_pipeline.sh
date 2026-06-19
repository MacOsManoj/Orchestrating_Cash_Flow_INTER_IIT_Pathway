#!/bin/bash

################################################################################
# Bond Pipeline Multi-Terminal Launcher (macOS Optimized)
# 
# This script launches the bond forecasting pipeline across multiple Terminal.app
# windows on macOS, ensuring proper conda 'pathway' environment activation.
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
    echo -e "${BLUE}[$(log_timestamp)] INFO:${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(log_timestamp)] SUCCESS:${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(log_timestamp)] WARNING:${NC} $1"
}

log_error() {
    echo -e "${RED}[$(log_timestamp)] ERROR:${NC} $1"
}

# Function to check if Python script exists
check_script_exists() {
    if [ ! -f "$1" ]; then
        log_error "Script not found: $1"
        return 1
    fi
    return 0
}

# Function to launch in macOS Terminal.app (using simple conda activate approach from launch_pathway.sh)
run_in_terminal_macos() {
    local script_name="$1"
    local python_command="$2"
    local log_file="$3"
    
    log_info "Launching: $script_name"
    
    # Create a script that ensures conda activation happens first, then runs the command
    local temp_script="${LOG_DIR}/.${script_name// /_}_$$.sh"
        cat > "$temp_script" <<SCRIPT_EOF
#!/bin/bash
# Change to project directory
cd '$SCRIPT_DIR' || exit 1

# Initialize conda properly
echo "Initializing conda..."

# Method 1: Try to use conda if it's in PATH and initialized
if command -v conda &> /dev/null; then
    # Initialize conda for this shell session
    eval "\$(conda shell.bash hook)" 2>/dev/null
fi

# Method 2: If conda not in PATH, try to source from common locations
if ! command -v conda &> /dev/null; then
    for conda_path in \\
        "\$HOME/miniconda3/etc/profile.d/conda.sh" \\
        "\$HOME/anaconda3/etc/profile.d/conda.sh" \\
        "/opt/homebrew/anaconda3/etc/profile.d/conda.sh" \\
        "/opt/homebrew/miniconda3/etc/profile.d/conda.sh"; do
        if [ -f "\$conda_path" ]; then
            source "\$conda_path"
            # Initialize conda after sourcing
            eval "\$(conda shell.bash hook)" 2>/dev/null
            break
        fi
    done
fi

# Verify conda is available
if ! command -v conda &> /dev/null; then
    echo "ERROR: conda not found. Please install conda or ensure it's in PATH."
    exit 1
fi

# Activate pathway environment
echo "Activating pathway conda environment..."
conda activate pathway

# Verify activation
if [ "\$CONDA_DEFAULT_ENV" = "pathway" ]; then
    echo "Pathway environment activated: \$CONDA_DEFAULT_ENV"
    echo "Python: \$(which python3)"
    echo "Directory: \$(pwd)"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    # Run the command
    python3 $python_command 2>&1 | tee '$log_file'
else
    echo "ERROR: Failed to activate pathway environment. Current: \$CONDA_DEFAULT_ENV"
    echo "Please ensure 'pathway' conda environment exists: conda create -n pathway"
    exit 1
fi
SCRIPT_EOF
        chmod +x "$temp_script"
        
    # Launch Terminal with the script
    osascript -e "tell application \"Terminal\"
        do script \"$temp_script\"
    activate
    end tell"
    
    log_success "$script_name launched in new Terminal window with pathway environment"
    sleep 2  # Give time for terminal to open
}

# Main execution
main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════════════╗"
    echo "║     Bond Forecasting Pipeline - macOS Multi-Terminal Launcher   ║"
    echo "║                        (Pathway Env Enabled)                      ║"
    echo "╚════════════════════════════════════════════════════════════════════╝"
    echo ""
    
    log_info "Pipeline directory: $SCRIPT_DIR"
    log_info "Log directory: $LOG_DIR"
    echo ""
    
    # Verify macOS
    if [[ "$OSTYPE" != "darwin"* ]]; then
        log_error "This script is optimized for macOS only"
        log_info "For Linux, remove macOS-specific sections"
        exit 1
    fi
    
    # Verify Terminal.app exists
    if ! pgrep -x "Terminal" > /dev/null; then
        log_warning "Terminal.app not running. Starting..."
        open -a Terminal
        sleep 2
    fi
    
    # Verify all scripts exist
    log_info "Verifying dependencies..."
    
    local scripts=(
        "historical_quotes_scarper.py"
        "nse_gsec_script.py"
        "pathway_producer_new.py"
        "bond_server_manager.py"
    )
    
    for script in "${scripts[@]}"; do
        if check_script_exists "$SCRIPT_DIR/$script"; then
            log_success "$script"
        else
            log_error "Missing: $script"
            exit 1
        fi
    done
    
    echo ""
    log_info "All dependencies verified. Launching pipeline..."
    echo ""
    
    # Step 1: Historical Quotes Scraper
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "1. HISTORICAL QUOTES SCRAPER"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    run_in_terminal_macos \
        "Historical Quotes Scraper" \
        "historical_quotes_scarper.py" \
        "$LOG_DIR/scraper.log"
    
    # Step 2: NSE GSEC Scheduler
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "2. NSE GSEC BOND FETCHER"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    run_in_terminal_macos \
        "NSE GSEC Scheduler" \
        "nse_gsec_script.py --schedule" \
        "$LOG_DIR/nse_gsec.log"
    
    # Step 3: Pathway Producer
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "3. PATHWAY PRODUCER"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    run_in_terminal_macos \
        "Pathway Producer" \
        "pathway_producer_new.py" \
        "$LOG_DIR/pathway_producer.log"
    
    # Step 4: Bond Server Manager (with delay)
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    log_info "4. BOND SERVER MANAGER (starting in ${STARTUP_DELAY}s)"
    log_info "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # Visual countdown
    for ((i = STARTUP_DELAY; i > 0; i--)); do
        printf "\rBond Server Manager: %3ds remaining... " $i
        sleep 1
    done
    echo ""
    
    run_in_terminal_macos \
        "Bond Server Manager" \
        "bond_server_manager.py" \
        "$LOG_DIR/bond_server_manager.log"
    
    echo ""
    echo "═══════════════════════════════════════════════════════════════"
    log_success "ALL 4 PIPELINE COMPONENTS LAUNCHED SUCCESSFULLY!"
    echo "═══════════════════════════════════════════════════════════════"
    echo ""
    
    log_info "All logs: $LOG_DIR/"
    log_info "Each component runs in separate Terminal window"
    log_info "Close individual windows to stop components"
    log_info "Relaunch with: bash $0"
    echo ""
    
    log_warning "Pipeline launcher complete. Components running independently."
    log_warning "Monitor logs in $LOG_DIR for status updates."
}

# Clean trap
trap 'log_info "Pipeline launcher interrupted. Components continue running in terminals."; exit 0' INT

# Launch!
main "$@"
