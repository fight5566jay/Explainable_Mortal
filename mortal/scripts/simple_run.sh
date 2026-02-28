#!/bin/bash

# Parse command line arguments
SKIP_BUILD_LIBRIICHI=false
TARGET_CODE=""
TARGET_CODE_ARGS=()

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build-libriichi)
            SKIP_BUILD_LIBRIICHI=true
            shift
            ;;
        *)
            if [ -z "$TARGET_CODE" ]; then
                TARGET_CODE=$1
                shift
            else
                # All remaining arguments are passed to the Python script
                TARGET_CODE_ARGS+=("$1")
                shift
            fi
            ;;
    esac
done

if [ -z "$TARGET_CODE" ]; then
    echo "Usage: $0 [--skip-build-libriichi] <target_code> [TARGET_CODE_ARGS...]"
    exit 1
fi

# Build libriichi
if [ "$SKIP_BUILD_LIBRIICHI" = false ]; then
    echo "[simple_run.sh] Start building libriichi."
    cd ..
    ./scripts/build_libriichi.sh
    cd mortal

    # if the build failed, exit
    if [ $? -ne 0 ]; then
        echo "[simple_run.sh] libriichi build failed."
        exit 1
    fi

    echo "[simple_run.sh] libriichi built."
else
    echo "[simple_run.sh] Skipping libriichi build."
fi

# Build GPU flags using helper script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GPU_FLAGS=$("$SCRIPT_DIR/podman_gpu_helper.sh")

# run the target code with podman 
echo "[simple_run.sh] Running ${TARGET_CODE} ${TARGET_CODE_ARGS[@]} with podman."
podman run --rm \
    $GPU_FLAGS \
   -v .:/workspace/mortal \
   -w /workspace/mortal \
   --network=host \
   --entrypoint python \
   localhost/explainable-mortal \
   ${TARGET_CODE} ${TARGET_CODE_ARGS[@]}