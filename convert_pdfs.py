#!/usr/bin/env python3
"""
Batch PDF to Markdown converter using marker-pdf library
"""

import os
import glob
from pathlib import Path
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered


def convert_pdf_to_markdown(pdf_path: str, output_dir: str = "output"):
    """
    Convert PDF file to Markdown

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
        # Initialize the converter with model dictionary
        converter = PdfConverter(
            artifact_dict=create_model_dict(),
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

        # Save images if any
        if images:
            images_dir = os.path.join(output_dir, f"{base_name}_images")
            os.makedirs(images_dir, exist_ok=True)
            for img_name, img_data in images.items():
                img_path = os.path.join(images_dir, img_name)
                with open(img_path, "wb") as f:
                    f.write(img_data)
            print(f"  OK {len(images)} images saved to: {images_dir}")

        # Save metadata if available
        if metadata:
            metadata_path = os.path.join(output_dir, f"{base_name}_metadata.json")
            import json
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            print(f"  OK Metadata saved to: {metadata_path}")

        return True

    except Exception as e:
        print(f"  ERROR: Failed to convert {pdf_file.name}: {e}")
        return False


def convert_all_pdfs(input_dir: str = "input", output_dir: str = "output"):
    """
    Convert all PDF files in the input directory to Markdown

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
    print("=" * 60)

    successful = 0
    failed = 0

    for pdf_file in pdf_files:
        if convert_pdf_to_markdown(pdf_file, output_dir):
            successful += 1
        else:
            failed += 1

    print("\n" + "=" * 60)
    print(f"Conversion complete!")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Total: {len(pdf_files)}")


if __name__ == "__main__":
    convert_all_pdfs()
