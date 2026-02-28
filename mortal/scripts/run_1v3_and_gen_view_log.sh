#!/bin/bash

# Parse command line arguments
SKIP_BUILD_LIBRIICHI=false
while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-build-libriichi)
            SKIP_BUILD_LIBRIICHI=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--skip-build-libriichi]"
            exit 1
            ;;
    esac
done

# --- Step 1: build libriichi ---
# Build libriichi
if [ "$SKIP_BUILD_LIBRIICHI" = false ]; then
    echo "[run_1v3_and_gen_view_log.sh] Start building libriichi."
    cd ..
    ./scripts/build_libriichi.sh
    cd mortal
    # if the build failed, exit
    if [ $? -ne 0 ]; then
        echo "[run_1v3_and_gen_view_log.sh] libriichi build failed."
        exit 1
    fi
    echo "[run_1v3_and_gen_view_log.sh] libriichi is built."
else
    echo "[run_1v3_and_gen_view_log.sh] Skipping libriichi build."
fi

# --- Step 2: run the target code with podman ---
echo "[run_1v3_and_gen_view_log.sh] running one_vs_three.py."

# Build GPU flags using helper script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GPU_FLAGS=$("$SCRIPT_DIR/podman_gpu_helper.sh")

podman run --rm \
    $GPU_FLAGS \
   -v .:/workspace/mortal \
   -w /workspace/mortal \
   --network=host \
   --entrypoint python \
   localhost/explainable-mortal \
   one_vs_three.py

echo "[run_1v3_and_gen_view_log.sh] finished running one_vs_three.py."



# --- Step 3: generate view log ---
echo "[run_1v3_and_gen_view_log.sh] generating view log for 1v3 log: $LATEST_1v3_LOG_PATH"

# Get the absolute path of the latest log file (before changing directory)
LATEST_1v3_LOG_PATH=$(readlink -f $(ls -t built/1v3/* | head -n 1))
LATEST_1v3_FILENAME=$(basename "$LATEST_1v3_LOG_PATH")
echo "Latest log filename: $LATEST_1v3_FILENAME"
cd ../view-logs
./gen_html.sh --1v3_log $LATEST_1v3_FILENAME

echo "[run_1v3_and_gen_view_log.sh] finished generating view log."