#!/usr/bin/env python3
"""
Debug image extraction for a single page
"""

import os
from pathlib import Path
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
import pypdfium2 as pdfium


def debug_single_page(pdf_path: str, page_num: int = 1):
    """
    Debug image extraction for a specific page (page_num is 1-indexed)
    """
    pdf_file = Path(pdf_path)
    print(f"Debugging page {page_num} of: {pdf_file.name}")
    print("=" * 60)

    # First check what PyPDFium2 sees
    print("\n1. Checking with PyPDFium2:")
    try:
        pdf = pdfium.PdfDocument(pdf_path)
        page = pdf[page_num - 1]  # 0-indexed

        print(f"   Page {page_num} objects:")
        obj_count = 0
        for obj in page.get_objects():
            obj_count += 1
            if hasattr(pdfium, 'FPDF_PAGEOBJ_IMAGE'):
                if obj.type == pdfium.FPDF_PAGEOBJ_IMAGE:
                    print(f"     - Image object found (old API)")
            else:
                print(f"     - Object type: {obj.type}")

        print(f"   Total objects on page: {obj_count}")
        pdf.close()
    except Exception as e:
        print(f"   PyPDFium2 error: {e}")

    # Now check marker-pdf
    print("\n2. Checking with marker-pdf:")
    try:
        converter = PdfConverter(
            artifact_dict=create_model_dict(),
        )

        print("   Converting...")
        rendered = converter(pdf_path)

        # Check rendered object
        print(f"\n   Rendered type: {type(rendered)}")

        if hasattr(rendered, 'images'):
            print(f"   rendered.images: {len(rendered.images) if rendered.images else 0} images")
            if rendered.images:
                for img_name, img_data in list(rendered.images.items())[:5]:
                    print(f"     - {img_name}: {len(img_data) if img_data else 0} bytes")

        # Extract using text_from_rendered
        print("\n3. Extracting with text_from_rendered:")
        text, metadata, images = text_from_rendered(rendered)

        print(f"   Extracted images: {len(images) if images else 0}")
        if images:
            for img_name, img_data in images.items():
                print(f"     - {img_name}: {len(img_data) if img_data else 0} bytes")
                if not img_data or len(img_data) == 0:
                    print(f"       ⚠️ WARNING: Empty image data!")

        # Save a test image if available
        if images:
            output_dir = "output/debug_test"
            os.makedirs(output_dir, exist_ok=True)

            for img_name, img_data in images.items():
                if img_data and len(img_data) > 0:
                    img_path = os.path.join(output_dir, img_name)
                    with open(img_path, "wb") as f:
                        f.write(img_data)
                    print(f"\n   ✓ Saved test image: {img_path}")
                    break

    except Exception as e:
        print(f"   marker-pdf error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    import glob
    pdf_files = glob.glob("input/*.pdf")
    if pdf_files:
        # Test page 2 (should have Figure 1.2, 1.3 according to the markdown)
        debug_single_page(pdf_files[0], page_num=2)
    else:
        print("No PDF files found in input folder")
