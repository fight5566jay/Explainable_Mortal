# MJAI Log HTML Generator

This tool generates HTML files for reviewing mjai logs from `.json.gz` files. It extracts the compressed game log data and creates individual HTML viewers using the log-viewer template.

Located in `view-logs/` directory for organization.

## Usage

### Single File Processing
```bash
# Process a single .json.gz file
podman run --rm --entrypoint python3 \
  -v /path/to/explainable_mortal:/workspace \
  localhost/explainable-mortal \
  /workspace/view-logs/generate_mjai_html.py \
  /workspace/view-logs/2024010100gm-00a9-0000-005a39ba.json.gz \
  --output /workspace/view-logs/generated_htmls
```

### Batch Processing
```bash
# Process all .json.gz files in view-logs directory (limit to first 3)
podman run --rm --entrypoint python3 \
  -v /path/to/explainable_mortal:/workspace \
  localhost/explainable-mortal \
  /workspace/view-logs/generate_mjai_html.py \
  /workspace/view-logs \
  --pattern "*.json.gz" \
  --output /workspace/view-logs/generated_htmls \
  --limit 3
```

## Command Line Options

- `input`: Input .json.gz file or directory containing .json.gz files
- `--template`: Path to the HTML template file (default: index.example.html)
- `--output, -o`: Output directory (default: same as input)
- `--pattern`: File pattern for directory processing (default: *.json.gz)
- `--limit, -l`: Limit number of files to process (for testing)

## Generated Files

Each `.json.gz` file generates a corresponding `.html` file:
- `10000_8192_a.json.gz` → `10000_8192_a.html`
- `10001_8192_b.json.gz` → `10001_8192_b.html`

## Features

1. **Extraction**: Decompresses .json.gz files and validates JSON format
2. **Template Replacement**: Replaces example log data with real mjai game data
3. **Batch Processing**: Processes multiple files with progress tracking
4. **Error Handling**: Skips invalid files and reports errors
5. **File Limits**: Optional limit for testing with large directories

## File Structure

The script expects:
- `.json.gz` files containing mjai log data (one JSON object per line)
- `index.example.html` template file (included in view-logs directory)
- `files/` directory with CSS and JavaScript support files (included)
- Container with Python 3 and required libraries

The `view-logs/` directory contains:
- `generate_mjai_html.py` - Main script
- `index.example.html` - HTML template
- `files/` - Supporting CSS/JS files
- `generated_htmls/` - Output directory for generated HTML files

## Example Output

Generated HTML files can be opened in a web browser to view interactive mahjong game replays with move analysis and Q-values.