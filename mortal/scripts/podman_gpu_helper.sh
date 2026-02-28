#!/bin/bash
# Helper script to build podman GPU flags automatically

# Function to build GPU device flags
build_gpu_flags() {
    local flags=""
    
    # Add all NVIDIA devices
    for dev in /dev/nvidia* /dev/nvidiactl /dev/nvidia-modeset /dev/nvidia-uvm /dev/nvidia-uvm-tools; do
        if [ -e "$dev" ]; then
            flags="$flags --device $dev"
        fi
    done
    
    # Find NVIDIA libraries
    local cuda_lib=$(ldconfig -p | grep 'libcuda.so.1' | awk '{print $NF}' | head -1)
    local nvml_lib=$(ldconfig -p | grep 'libnvidia-ml.so.1' | awk '{print $NF}' | head -1)
    
    # Mount libraries if found
    if [ -n "$cuda_lib" ] && [ -e "$cuda_lib" ]; then
        flags="$flags -v $cuda_lib:/usr/local/lib/libcuda.so.1:ro"
    fi
    
    if [ -n "$nvml_lib" ] && [ -e "$nvml_lib" ]; then
        flags="$flags -v $nvml_lib:/usr/local/lib/libnvidia-ml.so.1:ro"
    fi
    
    # Add library path environment variable
    flags="$flags --env LD_LIBRARY_PATH=/usr/local/lib:/opt/conda/lib"
    
    # Add security options
    flags="$flags --group-add keep-groups --security-opt=label=disable"
    
    echo "$flags"
}

# Export the function for use in other scripts
export -f build_gpu_flags

# If called directly, print the flags
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    build_gpu_flags
fi
