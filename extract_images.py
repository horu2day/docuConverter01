#!/usr/bin/env python3
"""
Extract embedded images from PDF files
"""

import os
import glob
from pathlib import Path

def extract_images_pypdfium2(pdf_path: str, output_dir: str = "output"):
    """
    Extract images using pypdfium2
    """
    try:
        import pypdfium2 as pdfium
        from PIL import Image
        import io

        pdf_file = Path(pdf_path)
        base_name = pdf_file.stem
        images_dir = os.path.join(output_dir, f"{base_name}_extracted_images")
        os.makedirs(images_dir, exist_ok=True)

        print(f"\nExtracting images from {pdf_file.name}...")

        pdf = pdfium.PdfDocument(pdf_path)
        image_count = 0

        for page_num in range(len(pdf)):
            page = pdf[page_num]

            # Get images from page
            for obj_index, obj in enumerate(page.get_objects()):
                if obj.type == pdfium.FPDF_PAGEOBJ_IMAGE:
                    try:
                        # Extract image
                        bitmap = obj.get_bitmap()
                        pil_image = bitmap.to_pil()

                        # Skip very small images (likely noise or artifacts)
                        if pil_image.width < 50 or pil_image.height < 50:
                            continue

                        image_count += 1
                        img_filename = f"page_{page_num + 1}_img_{obj_index + 1}.png"
                        img_path = os.path.join(images_dir, img_filename)
                        pil_image.save(img_path)
                        print(f"  Saved: {img_filename} ({pil_image.width}x{pil_image.height})")

                    except Exception as e:
                        print(f"  Warning: Could not extract image {obj_index} from page {page_num + 1}: {e}")

        pdf.close()

        if image_count > 0:
            print(f"  OK Total {image_count} images extracted to: {images_dir}")
            return True
        else:
            print(f"  INFO: No images found in {pdf_file.name}")
            return True

    except Exception as e:
        print(f"  ERROR: Failed with pypdfium2: {e}")
        return False


def extract_images_pymupdf(pdf_path: str, output_dir: str = "output"):
    """
    Extract images using PyMuPDF (fitz) - fallback method
    """
    try:
        import fitz  # PyMuPDF

        pdf_file = Path(pdf_path)
        base_name = pdf_file.stem
        images_dir = os.path.join(output_dir, f"{base_name}_extracted_images")
        os.makedirs(images_dir, exist_ok=True)

        print(f"\nExtracting images from {pdf_file.name} using PyMuPDF...")

        doc = fitz.open(pdf_path)
        image_count = 0

        for page_num in range(len(doc)):
            page = doc[page_num]
            image_list = page.get_images(full=True)

            for img_index, img_info in enumerate(image_list):
                xref = img_info[0]

                try:
                    # Extract image
                    base_image = doc.extract_image(xref)
                    image_bytes = base_image["image"]
                    image_ext = base_image["ext"]

                    # Skip very small images
                    if len(image_bytes) < 1000:  # Less than 1KB
                        continue

                    image_count += 1
                    img_filename = f"page_{page_num + 1}_img_{img_index + 1}.{image_ext}"
                    img_path = os.path.join(images_dir, img_filename)

                    with open(img_path, "wb") as f:
                        f.write(image_bytes)

                    print(f"  Saved: {img_filename} ({len(image_bytes)} bytes)")

                except Exception as e:
                    print(f"  Warning: Could not extract image {img_index} from page {page_num + 1}: {e}")

        doc.close()

        if image_count > 0:
            print(f"  OK Total {image_count} images extracted to: {images_dir}")
            return True
        else:
            print(f"  INFO: No images found in {pdf_file.name}")
            return True

    except ImportError:
        print("  ERROR: PyMuPDF not installed. Install with: pip install PyMuPDF")
        return False
    except Exception as e:
        print(f"  ERROR: Failed with PyMuPDF: {e}")
        return False


def extract_images_from_pdf(pdf_path: str, output_dir: str = "output"):
    """
    Try to extract images using available methods
    """
    # Try pypdfium2 first (already installed)
    success = extract_images_pypdfium2(pdf_path, output_dir)

    if not success:
        print("\nTrying PyMuPDF as fallback...")
        success = extract_images_pymupdf(pdf_path, output_dir)

    return success


def extract_all_images(input_dir: str = "input", output_dir: str = "output"):
    """
    Extract images from all PDF files in the input directory
    """
    pdf_pattern = os.path.join(input_dir, "*.pdf")
    pdf_files = sorted(glob.glob(pdf_pattern))

    if not pdf_files:
        print(f"No PDF files found in {input_dir}")
        return

    print(f"Found {len(pdf_files)} PDF files")
    print("=" * 60)

    successful = 0
    failed = 0

    for pdf_file in pdf_files:
        if extract_images_from_pdf(pdf_file, output_dir):
            successful += 1
        else:
            failed += 1

    print("\n" + "=" * 60)
    print(f"Image extraction complete!")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Total: {len(pdf_files)}")


if __name__ == "__main__":
    extract_all_images()
