#!/bin/bash

# Script to copy .json.gz files from ../mjai-reviewer-copy/converted_logs_compressed to mortal/built/dataset/
# Files with format YYYYMM*.json.gz are organized into ../mortal/built/dataset/YYYY/MM/ structure
# Usage: ./copy_dataset.sh [--dry-run] [--verbose]

DRY_RUN=false
VERBOSE=false
FILTER_YEAR=""
FILTER_MONTH=""
SOURCE_DIR="../../mjai-reviewer-copy/converted_logs_compressed"
TARGET_DIR="../mortal/built/dataset"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            echo "DRY RUN MODE: No files will be copied"
            shift
            ;;
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        -y|--year)
            FILTER_YEAR="$2"
            if [[ ! "$FILTER_YEAR" =~ ^[0-9]{4}$ ]]; then
                echo "Error: Year must be a 4-digit number (e.g., 2024)"
                exit 1
            fi
            shift 2
            ;;
        -m|--month)
            FILTER_MONTH="$2"
            if [[ ! "$FILTER_MONTH" =~ ^(0[1-9]|1[0-2])$ ]]; then
                echo "Error: Month must be 01-12 (e.g., 01, 02, ..., 12)"
                exit 1
            fi
            shift 2
            ;;
        --help|-h)
            echo "Usage: $0 [--dry-run] [--verbose] [-y YEAR] [-m MONTH] [--help]"
            echo ""
            echo "Copy .json.gz files from ../mjai-reviewer-copy/converted_logs_compressed to ../mortal/built/dataset/"
            echo "Files with format YYYYMM*.json.gz are organized into YYYY/MM/ directory structure"
            echo "Existing files are automatically skipped"
            echo ""
            echo "Options:"
            echo "  --dry-run         Show what would be copied without actually copying"
            echo "  --verbose, -v     Show detailed output"
            echo "  -y, --year YYYY   Only copy files from specific year (e.g., -y 2024)"
            echo "  -m, --month MM    Only copy files from specific month (e.g., -m 01)"
            echo "  --help, -h        Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --dry-run                    # Preview all files"
            echo "  $0 -y 2024                      # Copy only 2024 files"
            echo "  $0 -y 2024 -m 01                # Copy only January 2024 files"
            echo "  $0 -m 12 --verbose              # Copy all December files with details"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: Source directory '$SOURCE_DIR' does not exist"
    echo "Please make sure the mjai-reviewer-copy/converted_logs_compressed directory is in the parent directory"
    exit 1
fi

# Check if target directory exists, create if needed
if [ ! -d "$TARGET_DIR" ]; then
    echo "Target directory '$TARGET_DIR' does not exist"
    if [ "$DRY_RUN" = true ]; then
        echo "[DRY RUN] Would create directory: $TARGET_DIR"
    else
        echo "Creating target directory: $TARGET_DIR"
        mkdir -p "$TARGET_DIR"
        if [ $? -ne 0 ]; then
            echo "Error: Failed to create target directory"
            exit 1
        fi
    fi
fi

# Function to extract year and month from filename
extract_year_month() {
    local filename="$1"
    # Extract YYYYMM from the beginning of filename
    if [[ $filename =~ ^([0-9]{4})([0-9]{2}) ]]; then
        YEAR="${BASH_REMATCH[1]}"
        MONTH="${BASH_REMATCH[2]}"
        return 0
    else
        return 1
    fi
}

# Find all .json.gz files in source directory (including subdirectories)
# Build search pattern based on filters
SEARCH_PATTERN="*.json.gz"
if [ -n "$FILTER_YEAR" ] && [ -n "$FILTER_MONTH" ]; then
    SEARCH_PATTERN="${FILTER_YEAR}${FILTER_MONTH}*.json.gz"
elif [ -n "$FILTER_YEAR" ]; then
    SEARCH_PATTERN="${FILTER_YEAR}*.json.gz"
fi

echo "Searching for files matching pattern: $SEARCH_PATTERN in $SOURCE_DIR..."
files_found=$(find "$SOURCE_DIR" -name "$SEARCH_PATTERN" -type f | wc -l)

if [ $files_found -eq 0 ]; then
    echo "No files matching pattern '$SEARCH_PATTERN' found in $SOURCE_DIR"
    exit 0
fi

echo "Found $files_found .json.gz files"

# Show filter information
if [ -n "$FILTER_YEAR" ] || [ -n "$FILTER_MONTH" ]; then
    filter_msg="Filtering: "
    if [ -n "$FILTER_YEAR" ]; then
        filter_msg="${filter_msg}Year=$FILTER_YEAR "
    fi
    if [ -n "$FILTER_MONTH" ]; then
        filter_msg="${filter_msg}Month=$FILTER_MONTH "
    fi
    echo "$filter_msg"
fi

# Copy files
copied_count=0
skipped_count=0
filtered_count=0
error_count=0
invalid_format_count=0

echo "Processing files with YYYYMM*.json.gz format..."

while IFS= read -r -d '' file; do
    # Get just the filename without path
    filename=$(basename "$file")
    
    if [ "$VERBOSE" = true ]; then
        echo "Processing: $filename"
    fi
    
    # Extract year and month from filename
    if extract_year_month "$filename"; then
        # Check if file matches year/month filters
        if [ -n "$FILTER_YEAR" ] && [ "$YEAR" != "$FILTER_YEAR" ]; then
            ((filtered_count++))
            if [ "$VERBOSE" = true ]; then
                echo "Filtered out (year): $filename (year=$YEAR, filter=$FILTER_YEAR)"
            fi
            continue
        fi
        
        if [ -n "$FILTER_MONTH" ] && [ "$MONTH" != "$FILTER_MONTH" ]; then
            ((filtered_count++))
            if [ "$VERBOSE" = true ]; then
                echo "Filtered out (month): $filename (month=$MONTH, filter=$FILTER_MONTH)"
            fi
            continue
        fi
        
        # Create target directory path YYYY/MM
        target_year_month_dir="$TARGET_DIR/$YEAR/$MONTH"
        target_file="$target_year_month_dir/$filename"
        
        # Check if file already exists
        if [ -f "$target_file" ]; then
            ((skipped_count++))
            if [ "$VERBOSE" = true ]; then
                echo "Skipped (already exists): $YEAR/$MONTH/$filename"
            fi
            continue
        fi
        
        if [ "$DRY_RUN" = true ]; then
            echo "[DRY RUN] Would copy: $filename -> $YEAR/$MONTH/$filename"
            ((copied_count++))
        else
            # Create target directory structure if needed
            if [ ! -d "$target_year_month_dir" ]; then
                mkdir -p "$target_year_month_dir"
                if [ $? -ne 0 ]; then
                    echo "Error: Failed to create directory $target_year_month_dir"
                    ((error_count++))
                    continue
                fi
            fi
            
            # Copy the file
            if cp "$file" "$target_file"; then
                ((copied_count++))
                if [ "$VERBOSE" = true ]; then
                    echo "Copied: $filename -> $YEAR/$MONTH/$filename"
                fi
            else
                echo "Error copying: $file"
                ((error_count++))
            fi
        fi
    else
        # File doesn't match YYYYMM*.json.gz format
        ((invalid_format_count++))
        if [ "$VERBOSE" = true ]; then
            echo "Skipped (invalid format): $filename (expected ${FILTER_YEAR}${FILTER_MONTH}*.json.gz)"
        fi
    fi
    
    # Show progress every 100 files processed
    total_processed=$((copied_count + skipped_count + filtered_count + error_count + invalid_format_count))
    if [ $((total_processed % 100)) -eq 0 ] && [ $total_processed -gt 0 ]; then
        echo "Progress: $total_processed files processed (copied: $copied_count, skipped: $skipped_count, filtered: $filtered_count, errors: $error_count, invalid format: $invalid_format_count)..."
    fi
    
done < <(find "$SOURCE_DIR" -name "$SEARCH_PATTERN" -type f -print0)

# Summary
echo ""
echo "=== SUMMARY ==="
if [ "$DRY_RUN" = true ]; then
    echo "DRY RUN completed"
    echo "Would copy: $copied_count files"
else
    echo "Copy operation completed"
    echo "Successfully copied: $copied_count files"
fi
echo "Already existed (skipped): $skipped_count files"
echo "Filtered out: $filtered_count files"
echo "Invalid format (skipped): $invalid_format_count files"
if [ $error_count -gt 0 ]; then
    echo "Errors encountered: $error_count files"
fi
echo "Files organized in $TARGET_DIR/${FILTER_YEAR}/${FILTER_MONTH}/ structure"

if [ $error_count -gt 0 ]; then
    exit 1
fi