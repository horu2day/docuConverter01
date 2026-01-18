#!/usr/bin/env python3
"""
Fast PDF to Markdown converter - optimized for text-heavy documents
"""

import os
import glob
from pathlib import Path
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
from marker.config.parser import ConfigParser


def convert_pdf_to_markdown_fast(pdf_path: str, output_dir: str = "output"):
    """
    Convert PDF file to Markdown with speed optimizations for text-heavy documents

    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save the output (default: "output")
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Get the base filename without extension
    pdf_file = Path(pdf_path)
    base_name = pdf_file.stem

    print(f"\nConverting {pdf_file.name} to Markdown...")

    try:
        # Configure for speed - text-focused processing
        config = {
            "output_format": "markdown",
            # Disable image extraction for speed (images won't be saved separately)
            # "disable_image_extraction": True,  # Uncomment if you want to skip all images
        }

        config_parser = ConfigParser(config)

        # Initialize the converter with optimized settings
        converter = PdfConverter(
            config=config_parser.generate_config_dict(),
            artifact_dict=create_model_dict(),
            processor_list=config_parser.get_processors(),
            renderer=config_parser.get_renderer(),
        )

        # Convert the PDF file
        rendered = converter(pdf_path)

        # Extract text and images from rendered output
        text, metadata, images = text_from_rendered(rendered)

        # Save as markdown
        output_path = os.path.join(output_dir, f"{base_name}.md")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)

        print(f"  OK Output saved to: {output_path}")

        # Save images if any (skip to save time)
        if images:
            print(f"  INFO: {len(images)} images found (not saved for speed)")
            # Uncomment below to save images
            # images_dir = os.path.join(output_dir, f"{base_name}_images")
            # os.makedirs(images_dir, exist_ok=True)
            # for img_name, img_data in images.items():
            #     img_path = os.path.join(images_dir, img_name)
            #     with open(img_path, "wb") as f:
            #         f.write(img_data)
            # print(f"  OK {len(images)} images saved to: {images_dir}")

        # Skip metadata saving for speed
        # if metadata:
        #     metadata_path = os.path.join(output_dir, f"{base_name}_metadata.json")
        #     import json
        #     with open(metadata_path, "w", encoding="utf-8") as f:
        #         json.dump(metadata, f, indent=2, ensure_ascii=False)
        #     print(f"  OK Metadata saved to: {metadata_path}")

        return (True, pdf_file.name)

    except Exception as e:
        print(f"  ERROR: Failed to convert {pdf_file.name}: {e}")
        return (False, pdf_file.name)


def convert_all_pdfs_fast(input_dir: str = "input", output_dir: str = "output"):
    """
    Convert all PDF files in the input directory to Markdown (sequential, memory-safe)

    Args:
        input_dir: Directory containing PDF files
        output_dir: Directory to save the output
    """
    # Find all PDF files
    pdf_pattern = os.path.join(input_dir, "*.pdf")
    pdf_files = sorted(glob.glob(pdf_pattern))

    if not pdf_files:
        print(f"No PDF files found in {input_dir}")
        return

    print(f"Found {len(pdf_files)} PDF files to convert")
    print("Mode: FAST (text-focused, sequential processing)")
    print("=" * 60)

    successful = 0
    failed = 0
    failed_files = []

    for i, pdf_file in enumerate(pdf_files, 1):
        print(f"\n[{i}/{len(pdf_files)}]", end=" ")
        success, filename = convert_pdf_to_markdown_fast(pdf_file, output_dir)
        if success:
            successful += 1
        else:
            failed += 1
            failed_files.append(filename)

    print("\n" + "=" * 60)
    print(f"Conversion complete!")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Total: {len(pdf_files)}")

    if failed_files:
        print(f"\nFailed files:")
        for filename in failed_files:
            print(f"  - {filename}")


if __name__ == "__main__":
    convert_all_pdfs_fast()
