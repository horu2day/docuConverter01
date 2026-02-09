#!/usr/bin/env python3
"""
PDF to Markdown converter with cropped figure extraction
Uses marker-pdf to detect figures, then crops them from page images
"""

import os
import glob
from pathlib import Path
from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered
from PIL import Image
import fitz  # PyMuPDF


def extract_figure_images(pdf_path: str, rendered, output_dir: str, base_name: str):
    """
    Extract figure images by cropping from page images based on marker's detection

    Args:
        pdf_path: Path to PDF file
        rendered: Marker's rendered output with figure positions
        output_dir: Output directory
        base_name: Base filename

    Returns:
        dict: Mapping of image names to image data
    """
    images_dict = {}

    # Check if rendered has pages with image information
    if not hasattr(rendered, 'pages') or not rendered.pages:
        print("  No page information in rendered output")
        return images_dict

    # Open PDF with PyMuPDF to render pages as images
    doc = fitz.open(pdf_path)

    print(f"  Processing {len(rendered.pages)} pages for figure extraction...")

    for page_idx, page_data in enumerate(rendered.pages):
        page_num = page_idx + 1

        # Check if page has images/figures
        if not hasattr(page_data, 'images') or not page_data.images:
            continue

        print(f"    Page {page_num}: Found {len(page_data.images)} figure(s)")

        # Render page as image
        pdf_page = doc[page_idx]

        # Render at 2x resolution for better quality
        mat = fitz.Matrix(2, 2)
        pix = pdf_page.get_pixmap(matrix=mat)

        # Convert to PIL Image
        img_data = pix.tobytes("png")
        page_img = Image.open(io.BytesIO(img_data))

        # Extract each figure from this page
        for fig_idx, fig_info in enumerate(page_data.images):
            try:
                # Get bounding box (marker stores positions)
                if hasattr(fig_info, 'bbox'):
                    bbox = fig_info.bbox

                    # Scale bbox coordinates (marker uses PDF coordinates)
                    # Adjust for 2x rendering
                    x0, y0, x1, y1 = bbox
                    x0, y0, x1, y1 = int(x0 * 2), int(y0 * 2), int(x1 * 2), int(y1 * 2)

                    # Crop the figure
                    cropped = page_img.crop((x0, y0, x1, y1))

                    # Save to bytes
                    from io import BytesIO
                    img_bytes = BytesIO()
                    cropped.save(img_bytes, format='PNG')

                    # Generate image name
                    img_name = f"_page_{page_num}_Figure_{fig_idx + 1}.png"
                    images_dict[img_name] = img_bytes.getvalue()

                    print(f"      Cropped figure {fig_idx + 1}: {x1-x0}x{y1-y0}px")

            except Exception as e:
                print(f"      Warning: Could not crop figure {fig_idx + 1}: {e}")

    doc.close()
    return images_dict


def convert_pdf_with_cropped_images(pdf_path: str, output_dir: str = "output"):
    """
    Convert PDF to Markdown with cropped figure images
    """
    import io

    os.makedirs(output_dir, exist_ok=True)

    pdf_file = Path(pdf_path)
    base_name = pdf_file.stem

    print(f"\nConverting {pdf_file.name}...")

    try:
        # Initialize converter
        converter = PdfConverter(
            artifact_dict=create_model_dict(),
        )

        # Convert
        print("  Running marker-pdf OCR and layout detection...")
        rendered = converter(pdf_path)

        # Extract text
        text, metadata, marker_images = text_from_rendered(rendered)

        # Save markdown
        output_path = os.path.join(output_dir, f"{base_name}.md")
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"  OK Markdown saved: {output_path}")

        # Extract cropped figure images
        print("  Extracting figures from pages...")
        cropped_images = extract_figure_images(pdf_path, rendered, output_dir, base_name)

        if cropped_images:
            images_dir = os.path.join(output_dir, f"{base_name}_images")
            os.makedirs(images_dir, exist_ok=True)

            for img_name, img_data in cropped_images.items():
                img_path = os.path.join(images_dir, img_name)
                with open(img_path, "wb") as f:
                    f.write(img_data)

            print(f"  OK {len(cropped_images)} figures saved to: {images_dir}")
        else:
            print("  ! No figures extracted (trying alternative method...)")
            # Fallback: use marker's images if available
            if marker_images:
                images_dir = os.path.join(output_dir, f"{base_name}_images")
                os.makedirs(images_dir, exist_ok=True)

                saved_count = 0
                for img_name, img_data in marker_images.items():
                    try:
                        # Check if img_data is PIL Image or bytes
                        from io import BytesIO
                        if isinstance(img_data, Image.Image):
                            # Convert PIL Image to bytes
                            img_bytes = BytesIO()
                            img_data.save(img_bytes, format='PNG')
                            img_bytes = img_bytes.getvalue()
                        else:
                            img_bytes = img_data

                        if img_bytes and len(img_bytes) > 0:
                            img_path = os.path.join(images_dir, img_name)
                            with open(img_path, "wb") as f:
                                f.write(img_bytes)
                            saved_count += 1
                    except Exception as e:
                        print(f"    Warning: Could not save {img_name}: {e}")

                if saved_count > 0:
                    print(f"  OK {saved_count} images from marker saved")
                else:
                    print("  ! No valid images to save")

        # Save metadata
        if metadata:
            import json
            metadata_path = os.path.join(output_dir, f"{base_name}_metadata.json")
            with open(metadata_path, "w", encoding="utf-8") as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

        return True

    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def convert_all_pdfs(input_dir: str = "input", output_dir: str = "output"):
    """
    Convert all PDFs with cropped figure extraction
    Each PDF is converted in a separate process to avoid multiprocessing issues
    """
    pdf_pattern = os.path.join(input_dir, "*.pdf")
    pdf_files = sorted(glob.glob(pdf_pattern))

    if not pdf_files:
        print(f"No PDF files found in {input_dir}")
        return

    print(f"Found {len(pdf_files)} PDF file(s)")
    print("=" * 60)

    successful = 0
    failed = 0

    # Convert each PDF in a separate subprocess to avoid multiprocessing pool issues
    import subprocess
    import sys

    for pdf_file in pdf_files:
        print(f"\nStarting conversion of: {os.path.basename(pdf_file)}")

        # Run conversion in separate process
        result = subprocess.run(
            [sys.executable, __file__, "--single", pdf_file, output_dir],
            capture_output=False
        )

        if result.returncode == 0:
            successful += 1
        else:
            failed += 1
            print(f"  FAILED: {os.path.basename(pdf_file)}")

    print("\n" + "=" * 60)
    print(f"Conversion complete!")
    print(f"  Successful: {successful}")
    print(f"  Failed: {failed}")
    print(f"  Total: {len(pdf_files)}")


if __name__ == "__main__":
    import sys

    # Check if running in single-file mode (called by subprocess)
    if len(sys.argv) >= 4 and sys.argv[1] == "--single":
        pdf_file = sys.argv[2]
        output_dir = sys.argv[3]
        success = convert_pdf_with_cropped_images(pdf_file, output_dir)
        sys.exit(0 if success else 1)
    else:
        # Normal batch mode
        convert_all_pdfs()
