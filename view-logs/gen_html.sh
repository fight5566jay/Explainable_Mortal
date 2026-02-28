#!/bin/bash

# Parse command line arguments
COPY_SRC_FILES=false
src_name=""
LOG_TYPE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --copy-src-files)
            COPY_SRC_FILES=true
            shift
            ;;
        --online_log)
            LOG_TYPE="online"
            shift
            ;;
        --offline_log)
            LOG_TYPE="offline"
            shift
            ;;
        --1v3_log)
            LOG_TYPE="1v3"
            shift
            ;;
        *)
            if [ -z "$src_name" ]; then
                src_name="$1"
            else
                echo "Error: Multiple source names provided"
                echo "Usage: $0 [--copy-src-files] [--online_log|--offline_log|--1v3_log] <source_log_name>"
                exit 1
            fi
            shift
            ;;
    esac
done

if [ -z "$src_name" ]; then
   echo "Usage: $0 [--copy-src-files] [--online_log|--offline_log|--1v3_log] <source_log_name>"
   exit 1
fi

# Determine log path based on flag
if [ "$LOG_TYPE" = "online" ]; then
    LOG_PATH="/workspace/mortal/built/online_server/drain/${src_name}"
elif [ "$LOG_TYPE" = "offline" ]; then
    LOG_PATH="/workspace/mortal/built/logs/test_play/${src_name}"
elif [ "$LOG_TYPE" = "1v3" ]; then
    LOG_PATH="/workspace/mortal/built/1v3/${src_name}"
else
    # Default to offline if no flag specified
    LOG_PATH="/workspace/mortal/built/logs/test_play/${src_name}"
    echo "No log type specified, defaulting to offline logs"
fi

# Check if the directory 'files' exists or the flag '--copy-src-files' is set
if [ ! -d "files" ] || [ "$COPY_SRC_FILES" = true ]; then
    echo "Copying source files from ../log-viewer/files to current directory..."
    if [ -d "../log-viewer/files" ]; then
        cp -r ../log-viewer/files generated_htmls
        echo "Source files copied successfully."
    else
        echo "Warning: ../log-viewer/files directory not found. HTML files may not display correctly."
    fi
fi

# Run the podman command to generate HTML
echo "src_name: $src_name"
echo "log_type: ${LOG_TYPE:-offline}"
echo "log_path: $LOG_PATH"
podman run --rm \
   --entrypoint python3 \
   -v ../:/workspace \
   localhost/explainable-mortal \
   /workspace/view-logs/generate_mjai_html.py \
   ${LOG_PATH} \
   --output /workspace/view-logs/generated_htmls