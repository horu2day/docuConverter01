#!/usr/bin/env python3
"""
Debug marker-pdf image extraction
"""

import os
from pathlib import Path
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered


def debug_image_extraction(pdf_path: str):
    """
    Debug why images are not being extracted properly
    """
    pdf_file = Path(pdf_path)
    print(f"Debugging image extraction for: {pdf_file.name}")
    print("=" * 60)

    try:
        # Initialize converter
        converter = PdfConverter(
            artifact_dict=create_model_dict(),
        )

        # Convert
        print("\nConverting PDF...")
        rendered = converter(pdf_path)
        print(f"  Rendered type: {type(rendered)}")
        print(f"  Rendered attributes: {dir(rendered)}")

        # Check what's in rendered
        if hasattr(rendered, 'images'):
            print(f"\n  rendered.images exists: {len(rendered.images) if rendered.images else 0} images")
            if rendered.images:
                for idx, (key, val) in enumerate(list(rendered.images.items())[:3]):
                    print(f"    Image {idx}: {key}, data size: {len(val) if val else 0}")

        # Extract text and images
        print("\nExtracting text and images...")
        text, metadata, images = text_from_rendered(rendered)

        print(f"\n  Text length: {len(text)} characters")
        print(f"  Metadata: {type(metadata)}")
        print(f"  Images dict: {len(images) if images else 0} items")

        if images:
            print("\n  Detailed image info:")
            for idx, (img_name, img_data) in enumerate(images.items()):
                print(f"    {idx + 1}. Name: {img_name}")
                print(f"       Data type: {type(img_data)}")
                print(f"       Data size: {len(img_data) if img_data else 0} bytes")
                if img_data:
                    print(f"       First 20 bytes: {img_data[:20]}")
                else:
                    print(f"       WARNING: Empty data!")
        else:
            print("\n  WARNING: No images returned!")

        # Check rendered object for image data
        print("\n  Checking rendered object structure:")
        if hasattr(rendered, '__dict__'):
            for key, val in rendered.__dict__.items():
                if 'image' in key.lower():
                    print(f"    {key}: {type(val)}, length: {len(val) if hasattr(val, '__len__') else 'N/A'}")

        # Try to access images directly from rendered
        if hasattr(rendered, 'images') and rendered.images:
            print("\n  Attempting direct image access:")
            print(f"    Total images in rendered: {len(rendered.images)}")
            for idx, (img_name, img_obj) in enumerate(list(rendered.images.items())[:3]):
                print(f"\n    Image {idx + 1}: {img_name}")
                print(f"      Type: {type(img_obj)}")
                print(f"      Attributes: {dir(img_obj) if hasattr(img_obj, '__dir__') else 'None'}")
                if hasattr(img_obj, 'tobytes'):
                    img_bytes = img_obj.tobytes()
                    print(f"      Bytes: {len(img_bytes)}")
                elif hasattr(img_obj, 'save'):
                    print(f"      Has save method (PIL Image?)")

    except Exception as e:
        print(f"\n  ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Debug the first PDF in input folder
    import glob
    pdf_files = glob.glob("input/*.pdf")
    if pdf_files:
        debug_image_extraction(pdf_files[0])
    else:
        print("No PDF files found in input folder")
