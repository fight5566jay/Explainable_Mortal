#!/usr/bin/env python3
"""
MJAI Log HTML Generator

This script generates HTML files for reviewing mjai logs from .json.gz files.
It extracts the log data, replaces the template in index.example.html, and
creates individual HTML files for each log.
"""

import gzip
import json
import os
import shutil
import sys
import argparse
from pathlib import Path


def extract_mjai_log(json_gz_path):
    """
    Extract mjai log data from a .json.gz file.
    
    Args:
        json_gz_path (str): Path to the .json.gz file
        
    Returns:
        str: The extracted mjai log data as a multi-line string
    """
    try:
        with gzip.open(json_gz_path, 'rt', encoding='utf-8') as f:
            lines = []
            for line in f:
                line = line.strip()
                if line:  # Skip empty lines
                    # Validate that it's valid JSON
                    try:
                        json.loads(line)
                        lines.append(line)
                    except json.JSONDecodeError:
                        print(f"Warning: Skipping invalid JSON line in {json_gz_path}: {line[:100]}...")
                        continue
            
            return '\n'.join(lines)
    
    except Exception as e:
        print(f"Error extracting {json_gz_path}: {e}")
        return None


def generate_html_file(json_gz_path, template_path, output_dir=None):
    """
    Generate an HTML file from a .json.gz mjai log file.
    
    Args:
        json_gz_path (str): Path to the .json.gz file
        template_path (str): Path to the index.example.html template
        output_dir (str): Directory to save the HTML file (default: same as json_gz_path)
        
    Returns:
        str: Path to the generated HTML file, or None if failed
    """
    # Extract the mjai log data
    mjai_data = extract_mjai_log(json_gz_path)
    if mjai_data is None:
        return None
    
    # Read the template file
    try:
        with open(template_path, 'r', encoding='utf-8') as f:
            template_content = f.read()
    except Exception as e:
        print(f"Error reading template {template_path}: {e}")
        return None
    
    # Find the start and end of the allActions template section
    start_marker = "allActions = `\n"
    end_marker = "\n    `.trim().split('\\n').map(s => JSON.parse(s))"
    
    start_pos = template_content.find(start_marker)
    end_pos = template_content.find(end_marker)
    
    if start_pos == -1 or end_pos == -1:
        print(f"Error: Could not find template markers in {template_path}")
        return None
    
    # Replace the template data with the extracted mjai data
    before_data = template_content[:start_pos + len(start_marker)]
    after_data = template_content[end_pos:]
    
    new_content = before_data + mjai_data + after_data
    
    # Generate output filename
    json_gz_name = os.path.basename(json_gz_path)
    html_name = json_gz_name.replace('.json.gz', '.html')
    
    if output_dir is None:
        output_dir = os.path.dirname(json_gz_path)
    
    output_path = os.path.join(output_dir, html_name)
    
    # Write the new HTML file
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        
        print(f"Generated: {output_path}")
        return output_path
    
    except Exception as e:
        print(f"Error writing HTML file {output_path}: {e}")
        return None


def process_directory(input_dir, template_path, output_dir=None, pattern="*.json.gz"):
    """
    Process all .json.gz files in a directory.
    
    Args:
        input_dir (str): Directory containing .json.gz files
        template_path (str): Path to the index.example.html template
        output_dir (str): Directory to save HTML files (default: same as input_dir)
        pattern (str): File pattern to match (default: "*.json.gz")
        
    Returns:
        list: List of paths to generated HTML files
    """
    input_path = Path(input_dir)
    generated_files = []
    
    # Safety check: ensure we're only processing .json.gz files
    if not pattern.endswith('.json.gz'):
        print(f"Warning: Pattern '{pattern}' does not end with .json.gz")
        if not pattern.endswith('.gz'):
            print("Error: Will only process compressed files for safety")
            return generated_files
    
    json_gz_files = list(input_path.glob(pattern))
    
    if not json_gz_files:
        print(f"No files matching '{pattern}' found in {input_dir}")
        return generated_files
    
    print(f"Found {len(json_gz_files)} files to process...")
    
    for i, json_gz_file in enumerate(json_gz_files, 1):
        print(f"Processing {i}/{len(json_gz_files)}: {json_gz_file.name}")
        
        html_file = generate_html_file(str(json_gz_file), template_path, output_dir)
        if html_file:
            generated_files.append(html_file)
    
    return generated_files


def main():
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    parser = argparse.ArgumentParser(description="Generate HTML files for reviewing mjai logs")
    parser.add_argument("input", help="Input .json.gz file or directory containing .json.gz files")
    parser.add_argument("--template", default=os.path.join(script_dir, "index.example.html"),
                        help="Path to the HTML template file (default: index.example.html in script directory)")
    parser.add_argument("--output", "-o", help="Output directory (default: same as input)")
    parser.add_argument("--pattern", default="*.json.gz", 
                        help="File pattern for directory processing (default: *.json.gz)")
    parser.add_argument("--limit", "-l", type=int, 
                        help="Limit number of files to process (for testing)")
    
    args = parser.parse_args()
    
    # Validate template file exists
    if not os.path.exists(args.template):
        print(f"Error: Template file not found: {args.template}")
        sys.exit(1)
    
    if os.path.isfile(args.input):
        # Process single file
        if not args.input.endswith('.json.gz'):
            print("Error: Input file must be a .json.gz file")
            sys.exit(1)
        
        html_file = generate_html_file(args.input, args.template, args.output)
        if html_file:
            print(f"Successfully generated: {html_file}")
        else:
            print("Failed to generate HTML file")
            sys.exit(1)
    
    elif os.path.isdir(args.input):
        # Process directory
        generated_files = process_directory(args.input, args.template, args.output, args.pattern)
        
        if args.limit and len(generated_files) > args.limit:
            # Remove excess HTML files if limit specified (only touch .html files)
            for file_path in generated_files[args.limit:]:
                try:
                    # Safety check: only remove .html files in output directory
                    if file_path.endswith('.html') and os.path.exists(file_path):
                        os.remove(file_path)
                        print(f"Removed (limit exceeded): {file_path}")
                except Exception as e:
                    print(f"Warning: Could not remove {file_path}: {e}")
            generated_files = generated_files[:args.limit]
        
        print(f"\nSuccessfully generated {len(generated_files)} HTML files")
    
    else:
        print(f"Error: Input path does not exist: {args.input}")
        sys.exit(1)


if __name__ == "__main__":
    main()