#!/bin/bash

################################################################################
# Launch Pathway Terminal
# 
# Opens a new Terminal window with pathway conda environment activated
# Optionally runs a command after activation
#
# Usage:
#   ./launch_pathway.sh                    # Just activate environment
#   ./launch_pathway.sh "python3 script.py" # Activate and run command
################################################################################

# Get script directory (more portable than hardcoded path)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${SCRIPT_DIR%/*}"  # Go up one level to bond-pipeline directory

# Optional command to run after activation
COMMAND="${1:-}"

# Create a temporary script to ensure proper conda activation
TEMP_SCRIPT=$(mktemp /tmp/launch_pathway_XXXXXX.sh)
chmod +x "$TEMP_SCRIPT"

if [ -n "$COMMAND" ]; then
    cat > "$TEMP_SCRIPT" <<SCRIPT_EOF
#!/bin/bash
cd '$PROJECT_DIR' || exit 1

# Initialize conda properly
echo "Initializing conda..."

# Method 1: Try to use conda if it's in PATH
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
    $COMMAND
else
    echo "ERROR: Failed to activate pathway environment. Current: \$CONDA_DEFAULT_ENV"
    echo "Please ensure 'pathway' conda environment exists: conda create -n pathway"
fi
SCRIPT_EOF
else
    cat > "$TEMP_SCRIPT" <<SCRIPT_EOF
#!/bin/bash
cd '$PROJECT_DIR' || exit 1

# Initialize conda properly
echo "Initializing conda..."

# Method 1: Try to use conda if it's in PATH
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
    echo "Ready to run commands."
else
    echo "ERROR: Failed to activate pathway environment. Current: \$CONDA_DEFAULT_ENV"
    echo "Please ensure 'pathway' conda environment exists: conda create -n pathway"
fi
SCRIPT_EOF
fi

# Launch Terminal with the script
osascript -e "tell application \"Terminal\"
    do script \"$TEMP_SCRIPT\"
    activate
end tell"

# Cleanup temp script after a delay
(sleep 5 && rm -f "$TEMP_SCRIPT") &

echo "Terminal window opened with pathway environment"
if [ -n "$COMMAND" ]; then
    echo "Running: $COMMAND"
fi