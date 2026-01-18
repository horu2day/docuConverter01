#!/usr/bin/env python3
"""
Merge multiple Markdown files into a single file
"""

import os
import glob
from pathlib import Path


def merge_markdown_files(input_dir: str = "output", output_file: str = "merged_output.md", separator: str = "\n\n---\n\n"):
    """
    Merge all markdown files in the input directory into a single file

    Args:
        input_dir: Directory containing markdown files
        output_file: Name of the merged output file
        separator: Separator between merged files (default: horizontal rule with newlines)
    """
    # Find all markdown files
    md_pattern = os.path.join(input_dir, "*.md")
    md_files = sorted(glob.glob(md_pattern))

    if not md_files:
        print(f"No markdown files found in {input_dir}")
        return

    print(f"Found {len(md_files)} markdown files to merge")
    print("=" * 60)

    merged_content = []

    for i, md_file in enumerate(md_files, 1):
        file_path = Path(md_file)
        print(f"[{i}/{len(md_files)}] Reading {file_path.name}...")

        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Add file header (optional, comment out if not needed)
            header = f"# {file_path.stem}\n\n"
            merged_content.append(header + content)

        except Exception as e:
            print(f"  ERROR: Failed to read {file_path.name}: {e}")
            continue

    if not merged_content:
        print("No content to merge")
        return

    # Join all content with separator
    final_content = separator.join(merged_content)

    # Save merged file
    output_path = os.path.join(input_dir, output_file)
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(final_content)
        print("\n" + "=" * 60)
        print(f"SUCCESS: Merged file saved to: {output_path}")
        print(f"Total files merged: {len(merged_content)}")
        print(f"Total size: {len(final_content):,} characters")
    except Exception as e:
        print(f"\nERROR: Failed to save merged file: {e}")


if __name__ == "__main__":
    # Customize these parameters as needed
    merge_markdown_files(
        input_dir="output",           # Directory with markdown files
        output_file="merged_all.md",  # Output filename
        separator="\n\n---\n\n"       # Separator between files
    )
