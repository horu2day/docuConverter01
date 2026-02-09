#!/usr/bin/env python3
"""
Update image paths in markdown files to point to extracted images
"""

import os
import re
import glob
from pathlib import Path


def update_markdown_image_paths(md_path: str, output_dir: str = "output"):
    """
    Update image paths in markdown file to point to extracted images
    """
    md_file = Path(md_path)
    base_name = md_file.stem

    # Path to extracted images folder
    extracted_images_dir = f"{base_name}_extracted_images"

    # Check if extracted images folder exists
    extracted_images_path = os.path.join(output_dir, extracted_images_dir)
    if not os.path.exists(extracted_images_path):
        print(f"No extracted images folder found: {extracted_images_path}")
        return False

    # Read markdown content
    with open(md_path, 'r', encoding='utf-8') as f:
        content = f.read()

    original_content = content

    # Pattern to match image references like ![](_page_1_Figure_1.jpeg)
    # Replace with actual extracted images
    def replace_image_path(match):
        old_path = match.group(1)

        # Extract page number from old path (e.g., _page_1_Figure_1.jpeg -> page 1)
        page_match = re.search(r'_page_(\d+)_', old_path)
        if page_match:
            page_num = page_match.group(1)
            # Map to extracted image: page_1_img_1.png
            new_path = f"{extracted_images_dir}/page_{page_num}_img_1.png"
            return f'![]({new_path})'

        return match.group(0)  # Return original if no match

    # Replace all image paths
    content = re.sub(r'\!\[\]\(([^)]+\.jpeg)\)', replace_image_path, content)

    if content == original_content:
        print(f"No changes needed for {md_file.name}")
        return True

    # Save updated markdown
    output_path = md_path.replace('.md', '_updated.md')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"Updated markdown saved to: {output_path}")

    # Count replacements
    old_count = len(re.findall(r'\!\[\]\([^)]+\.jpeg\)', original_content))
    new_count = len(re.findall(r'\!\[\]\([^)]+\.png\)', content))
    print(f"  Replaced {new_count} image paths (out of {old_count} references)")

    return True


def update_all_markdown_files(output_dir: str = "output"):
    """
    Update image paths in all markdown files
    """
    md_pattern = os.path.join(output_dir, "*.md")
    md_files = [f for f in glob.glob(md_pattern) if not f.endswith('_updated.md')]

    if not md_files:
        print(f"No markdown files found in {output_dir}")
        return

    print(f"Found {len(md_files)} markdown files")
    print("=" * 60)

    for md_file in md_files:
        update_markdown_image_paths(md_file, output_dir)
        print()

    print("=" * 60)
    print("Done!")


if __name__ == "__main__":
    update_all_markdown_files()
