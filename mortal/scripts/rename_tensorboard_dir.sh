#!/bin/bash
DIR="built/tensorboard"
if [ -d "$DIR" ]; then
    BASE_NAME="${DIR}_$(date +%y%m%d)"
    TARGET_DIR="$BASE_NAME"
    ID=1
    
    # Find an available directory name
    while [ -d "$TARGET_DIR" ]; do
        TARGET_DIR="${BASE_NAME}_${ID}"
        ID=$((ID + 1))
    done
    
    mv "$DIR" "$TARGET_DIR"
    echo "Renamed ${DIR} to ${TARGET_DIR}"
else
    echo "Tensorboard directory not found. Skipping rename."
fi