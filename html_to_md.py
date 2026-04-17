import re
import shutil
import html2text
from pathlib import Path
from bs4 import BeautifulSoup


def convert_background_images_to_img_tags(html_content, html_file, output_img_dir):
    """Replace background-image CSS with actual img tags and copy images."""
    images_copied = []
    image_counter = 0

    # Pattern to match elements with background-image in style
    pattern = r"(<[^>]+style=\"[^\"]*background-image:url\('([^']+)'\)[^\"]*\"[^>]*>)"

    def replace_with_img(match):
        nonlocal image_counter
        full_tag = match.group(1)
        img_url = match.group(2)
        image_counter += 1

        # Get source image path
        src_img_path = html_file.parent / img_url

        if src_img_path.exists():
            img_filename = src_img_path.name

            # Copy image to output directory
            dst_img_path = output_img_dir / img_filename
            if not dst_img_path.exists():
                shutil.copy2(src_img_path, dst_img_path)
                images_copied.append(img_filename)

            # Create img tag to insert
            img_tag = f'<img src="images/{img_filename}" alt="그림 {image_counter}">'

            # Return original tag with img inserted
            # Find the closing > and insert img before the content
            if '/>' in full_tag:
                return full_tag.replace('/>', f'>{img_tag}')
            else:
                return full_tag + img_tag
        return full_tag

    new_content = re.sub(pattern, replace_with_img, html_content)
    return new_content, images_copied


def clean_html_to_md(input_dir, output_dir):
    """
    Convert HTML files to clean Markdown using markdownify.
    Handles background-image styles and copies images to output.
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir)
    output_path.mkdir(exist_ok=True)

    # Create images subdirectory
    output_img_dir = output_path / 'images'
    output_img_dir.mkdir(exist_ok=True)

    html_files = list(input_path.glob("*.html"))
    print(f"Found {len(html_files)} HTML files")

    for html_file in html_files:
        print(f"Processing: {html_file.name}")

        with open(html_file, 'r', encoding='utf-8-sig') as f:
            html_content = f.read()

        # Convert background-images to img tags
        html_content, images_copied = convert_background_images_to_img_tags(
            html_content, html_file, output_img_dir
        )
        if images_copied:
            print(f"  Copied {len(images_copied)} images")

        # Parse HTML
        soup = BeautifulSoup(html_content, 'html.parser')

        # Remove unwanted elements
        for tag in soup.find_all(['script', 'style', 'nav', 'header', 'footer', 'button', 'form', 'svg']):
            tag.decompose()

        # Remove page number divs
        for tag in soup.find_all('div', class_='hpN'):
            tag.decompose()

        # Try to extract main content
        main_content = soup.find('article') or soup.find('main') or soup.find('body')

        if main_content:
            h = html2text.HTML2Text()
            h.body_width = 0
            h.ignore_links = False
            h.ignore_images = False
            h.ignore_tables = False

            markdown = h.handle(str(main_content))

            # Clean up markdown
            markdown = re.sub(r'\n{3,}', '\n\n', markdown)
            markdown = re.sub(r'__+', '', markdown)
            markdown = re.sub(r'\[\s*\]\([^)]*\)', '', markdown)
            markdown = markdown.strip()

            # Save markdown file
            output_file = output_path / f"{html_file.stem}.md"
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(markdown)

            print(f"  Saved: {output_file.name} ({len(markdown)} chars)")
        else:
            print(f"  Skipped: No content found")

    print(f"\nDone! Output directory: {output_path}")


if __name__ == "__main__":
    input_dir = "./input"
    output_dir = "./output"
    clean_html_to_md(input_dir, output_dir)
