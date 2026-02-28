#!/bin/bash

PORT=6006
# parsing arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port|-p)
            PORT=$2
            shift 2
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [--port|-p PORT]"
            exit 1
            ;;
    esac
done

# Build GPU flags using helper script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GPU_FLAGS=$("$SCRIPT_DIR/podman_gpu_helper.sh")

# Run tensorboard with podman and GPU support
podman run --rm -it \
    $GPU_FLAGS \
   -p $PORT:$PORT \
   -v .:/workspace/mortal \
   -w /workspace/mortal \
   --entrypoint tensorboard \
   localhost/explainable-mortal \
   --logdir=/workspace/mortal/built/tensorboard \
   --host=0.0.0.0 \
   --port=$PORT
