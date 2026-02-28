#!/bin/bash

# Parse command line arguments
RENAME_TENSORBOARD=true
SKIP_BUILD_LIBRIICHI=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --no-rename-tensorboard)
            RENAME_TENSORBOARD=false
            shift
            ;;
        --skip-build-libriichi)
            SKIP_BUILD_LIBRIICHI=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--no-rename-tensorboard] [--skip-build-libriichi]"
            exit 1
            ;;
    esac
done

# Rename the old tensorboard directory if it exists
if [ "$RENAME_TENSORBOARD" = true ]; then
    ./scripts/rename_tensorboard_dir.sh
fi

# Build libriichi
if [ "$SKIP_BUILD_LIBRIICHI" = false ]; then
    echo "[run_train.sh] Start building libriichi."
    cd ..
    ./scripts/build_libriichi.sh
    cd mortal
    echo "[run_train.sh] libriichi is built."
else
    echo "[run_train.sh] Skipping libriichi build."
fi

# Build GPU flags using helper script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GPU_FLAGS=$("$SCRIPT_DIR/podman_gpu_helper.sh")

# start the training process using podman with GPU support
podman run --rm \
   $GPU_FLAGS \
   -v .:/workspace/mortal \
   -w /workspace/mortal \
   --network=host \
   --entrypoint python \
   localhost/explainable-mortal \
   train.py
