#!/bin/bash

# Script to package current training results (models, tensorboard, logs)
# Usage: ./package_result.sh [OPTIONS] [optional_name]
# Options:
#   -m, --move    Move files instead of copying (saves disk space)
# Example: ./package_result.sh "experiment_v1"
#          ./package_result.sh --move "experiment_v1"

set -e  # Exit on error

# Get the script directory and project root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MORTAL_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILT_DIR="$MORTAL_DIR/built"
PACKAGE_DIR="$MORTAL_DIR/packaged_models"

# Parse arguments
MOVE_MODE=false
PACKAGE_SUFFIX=""

for arg in "$@"; do
    case $arg in
        -m|--move)
            MOVE_MODE=true
            shift
            ;;
        *)
            PACKAGE_SUFFIX="$arg"
            shift
            ;;
    esac
done

# Get timestamp from training files (newest model file)
# Falls back to current timestamp if no model files exist
if [ -d "$BUILT_DIR/models" ] && [ "$(ls -A $BUILT_DIR/models 2>/dev/null)" ]; then
    # Find the newest model file and get its modification time
    NEWEST_MODEL=$(find "$BUILT_DIR/models" -type f -name "*.pth" -printf '%T@ %p\n' 2>/dev/null | sort -n | tail -1 | cut -d' ' -f2-)
    if [ -n "$NEWEST_MODEL" ]; then
        TIMESTAMP=$(date -r "$NEWEST_MODEL" +"%y%m%d_%H%M%S")
        echo "Using timestamp from: $(basename "$NEWEST_MODEL")"
    else
        TIMESTAMP=$(date +"%y%m%d_%H%M%S")
        echo "No model files found, using current timestamp"
    fi
else
    TIMESTAMP=$(date +"%y%m%d_%H%M%S")
    echo "No models directory found, using current timestamp"
fi

# Get optional name from argument
if [ -n "$PACKAGE_SUFFIX" ]; then
    PACKAGE_NAME="${TIMESTAMP}_$PACKAGE_SUFFIX"
else
    PACKAGE_NAME="$TIMESTAMP"
fi

TARGET_DIR="$PACKAGE_DIR/$PACKAGE_NAME"

# Function to check if models are already packaged
check_already_packaged() {
    if [ ! -d "$PACKAGE_DIR" ]; then
        return 1  # Package dir doesn't exist, nothing to check
    fi
    
    # Look for existing packages with the same timestamp prefix
    local existing_packages=$(find "$PACKAGE_DIR" -maxdepth 1 -type d -name "${TIMESTAMP}*" 2>/dev/null)
    
    if [ -z "$existing_packages" ]; then
        return 0  # No matching packages found, safe to proceed
    fi
    
    # Check each matching package
    for pkg_dir in $existing_packages; do
        local pkg_name=$(basename "$pkg_dir")
        
        # Compare models if they exist in both places
        if [ -d "$BUILT_DIR/models" ] && [ -d "$pkg_dir/models" ]; then
            # Get list of model files and their sizes
            local current_models=$(cd "$BUILT_DIR/models" && find . -name "*.pth" -type f -exec stat -c '%s %n' {} \; 2>/dev/null | sort)
            local packaged_models=$(cd "$pkg_dir/models" && find . -name "*.pth" -type f -exec stat -c '%s %n' {} \; 2>/dev/null | sort)
            
            if [ "$current_models" = "$packaged_models" ] && [ -n "$current_models" ]; then
                echo "⚠ WARNING: These models appear to already be packaged!"
                echo "  Existing package: $pkg_name"
                echo ""
                read -p "Continue anyway? (y/N): " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    echo "Packaging cancelled."
                    exit 0
                fi
                return 0
            fi
        fi
    done
    
    return 0  # No duplicate content found
}

# Set operation type
if [ "$MOVE_MODE" = true ]; then
    OPERATION="Moving"
    OPERATION_VERB="moved"
else
    OPERATION="Copying"
    OPERATION_VERB="copied"
fi

echo "================================================"
echo "Packaging Training Results ($OPERATION)"
echo "================================================"
echo "Target directory: $TARGET_DIR"
echo "Mode: $OPERATION files"
echo ""

# Create the package directory structure
mkdir -p "$TARGET_DIR"

# Check if already packaged
check_already_packaged

# Function to copy or move directory if it exists
copy_if_exists() {
    local src="$1"
    local dst="$2"
    local name="$3"
    
    if [ -d "$src" ] && [ "$(ls -A $src 2>/dev/null)" ]; then
        echo "$OPERATION $name..."
        if [ "$MOVE_MODE" = true ]; then
            mv "$src" "$dst/"
            echo "  ✓ $name $OPERATION_VERB"
        else
            cp -r "$src" "$dst/"
            echo "  ✓ $name $OPERATION_VERB"
        fi
    else
        echo "  ⊘ $name not found or empty, skipping"
    fi
}

# Function to copy or move file if it exists
copy_file_if_exists() {
    local src="$1"
    local dst="$2"
    local name="$3"
    
    if [ -f "$src" ]; then
        echo "$OPERATION $name..."
        if [ "$MOVE_MODE" = true ]; then
            mv "$src" "$dst/"
            echo "  ✓ $name $OPERATION_VERB"
        else
            cp "$src" "$dst/"
            echo "  ✓ $name $OPERATION_VERB"
        fi
    else
        echo "  ⊘ $name not found, skipping"
    fi
}

# Copy models
copy_if_exists "$BUILT_DIR/models" "$TARGET_DIR" "models"

# Copy tensorboard logs
copy_if_exists "$BUILT_DIR/tensorboard" "$TARGET_DIR" "tensorboard"

# Copy training logs
#copy_if_exists "$BUILT_DIR/logs" "$TARGET_DIR" "logs"

# Copy config files (always copy, never move)
echo "Copying config files..."
if [ -f "$MORTAL_DIR/config.toml" ]; then
    cp "$MORTAL_DIR/config.toml" "$TARGET_DIR/"
    echo "  ✓ config.toml copied"
else
    echo "  ⊘ config.toml not found, skipping"
fi
#copy_file_if_exists "$MORTAL_DIR/config_online.toml" "$TARGET_DIR" "config_online.toml"

# Create a metadata file
METADATA_FILE="$TARGET_DIR/metadata.txt"
echo "Creating metadata file..."
cat > "$METADATA_FILE" << EOF
Package Name: $PACKAGE_NAME
Created: $(date)
Hostname: $(hostname)
User: $(whoami)

Directory Contents:
EOF

# List what was packaged
ls -lh "$TARGET_DIR" >> "$METADATA_FILE"

# Add git information if available
if command -v git &> /dev/null && git -C "$MORTAL_DIR" rev-parse --git-dir > /dev/null 2>&1; then
    echo "" >> "$METADATA_FILE"
    echo "Git Information:" >> "$METADATA_FILE"
    echo "  Commit: $(git -C "$MORTAL_DIR" rev-parse HEAD)" >> "$METADATA_FILE"
    echo "  Branch: $(git -C "$MORTAL_DIR" rev-parse --abbrev-ref HEAD)" >> "$METADATA_FILE"
    echo "  Status:" >> "$METADATA_FILE"
    git -C "$MORTAL_DIR" status --short >> "$METADATA_FILE" 2>&1 || echo "  Unable to get git status" >> "$METADATA_FILE"
fi

echo "  ✓ Metadata created"

# Calculate total size
#TOTAL_SIZE=$(du -sh "$TARGET_DIR" | cut -f1)

echo ""
echo "================================================"
echo "Package Complete!"
echo "================================================"
echo "Location: $TARGET_DIR"
#echo "Total size: $TOTAL_SIZE"
echo ""
if [ "$MOVE_MODE" = true ]; then
    echo "Files have been moved. Original directories are now empty/removed."
    echo "To restore, move the contents back to the built/ directory."
else
    echo "To restore this result, copy the contents back to:"
    echo "  - models → $BUILT_DIR/models/"
    echo "  - tensorboard → $BUILT_DIR/tensorboard/"
    echo "  - logs → $BUILT_DIR/logs/"
fi
echo ""
echo "You can now start a new training process."
echo "================================================"