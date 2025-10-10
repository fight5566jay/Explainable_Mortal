#!/bin/bash

# Parse command line arguments
COPY_SRC_FILES=false
src_name=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --copy-src-files)
            COPY_SRC_FILES=true
            shift
            ;;
        *)
            if [ -z "$src_name" ]; then
                src_name="$1"
            else
                echo "Error: Multiple source names provided"
                echo "Usage: $0 [--copy-src-files] <source_log_name>"
                exit 1
            fi
            shift
            ;;
    esac
done

if [ -z "$src_name" ]; then
   echo "Usage: $0 [--copy-src-files] <source_log_name>"
   exit 1
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
podman run --rm \
   --entrypoint python3 \
   -v /mnt/nfs/work/sctang/Projects/Explainable_Mortal:/workspace \
   localhost/explainable-mortal \
   /workspace/view-logs/generate_mjai_html.py \
   /workspace/mortal/built/logs/test_play/${src_name} \
   --output /workspace/view-logs/generated_htmls