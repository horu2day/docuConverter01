#!/usr/bin/env python3
"""
EPUB to Markdown converter using ebooklib and html2text
"""

import os
import json
import re
from pathlib import Path
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup


def html_to_markdown(soup):
    """Convert BeautifulSoup HTML to Markdown format"""

    def process_element(element):
        if isinstance(element, str):
            text = element.strip()
            if text:
                return text
            return ""

        tag = element.name

        # Headers
        if tag in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
            level_num = int(tag[1])
            text = element.get_text().strip()
            return '\n' + '#' * level_num + ' ' + text + '\n'

        # Paragraphs
        elif tag == 'p':
            text = ''.join(process_element(child) for child in element.children)
            return '\n' + text.strip() + '\n'

        # Line breaks
        elif tag == 'br':
            return '\n'

        # Bold
        elif tag in ['strong', 'b']:
            text = ''.join(process_element(child) for child in element.children)
            return '**' + text.strip() + '**'

        # Italic
        elif tag in ['em', 'i']:
            text = ''.join(process_element(child) for child in element.children)
            return '*' + text.strip() + '*'

        # Links
        elif tag == 'a':
            text = ''.join(process_element(child) for child in element.children)
            href = element.get('href', '')
            if href:
                return f'[{text.strip()}]({href})'
            return text.strip()

        # Images
        elif tag == 'img':
            src = element.get('src', '')
            alt = element.get('alt', '')
            return f'![{alt}]({src})'

        # Lists
        elif tag == 'ul':
            items = []
            for li in element.find_all('li', recursive=False):
                text = ''.join(process_element(child) for child in li.children)
                items.append('- ' + text.strip())
            return '\n' + '\n'.join(items) + '\n'

        elif tag == 'ol':
            items = []
            for i, li in enumerate(element.find_all('li', recursive=False), 1):
                text = ''.join(process_element(child) for child in li.children)
                items.append(f'{i}. ' + text.strip())
            return '\n' + '\n'.join(items) + '\n'

        # Blockquote
        elif tag == 'blockquote':
            text = ''.join(process_element(child) for child in element.children)
            lines = text.strip().split('\n')
            return '\n' + '\n'.join('> ' + line for line in lines) + '\n'

        # Code
        elif tag == 'code':
            text = element.get_text()
            return '`' + text + '`'

        elif tag == 'pre':
            text = element.get_text()
            return '\n```\n' + text + '\n```\n'

        # Div and span - just process children
        elif tag in ['div', 'span', 'section', 'article']:
            return ''.join(process_element(child) for child in element.children)

        # Default - process children
        else:
            return ''.join(process_element(child) for child in element.children)

    # Process body or entire soup
    body = soup.find('body') if soup.find('body') else soup
    markdown = process_element(body)

    # Clean up multiple newlines
    markdown = re.sub(r'\n{3,}', '\n\n', markdown)

    return markdown.strip()


def convert_epub_to_markdown(epub_path: str, output_dir: str = "output"):
    """
    Convert EPUB file to Markdown

    Args:
        epub_path: Path to the EPUB file
        output_dir: Directory to save the output (default: "output")
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Get the base filename without extension
    epub_file = Path(epub_path)
    base_name = epub_file.stem

    print(f"Converting {epub_path} to Markdown...")

    # Read the EPUB file
    book = epub.read_epub(epub_path)

    # Extract all text content
    chapters = []
    images = {}
    image_counter = 0

    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            # Get HTML content
            html_content = item.get_content().decode('utf-8')

            # Parse with BeautifulSoup
            soup = BeautifulSoup(html_content, 'html.parser')

            # Convert to markdown-like format
            markdown_content = html_to_markdown(soup)

            # Clean up the markdown
            markdown_content = markdown_content.strip()

            if markdown_content:
                chapters.append(markdown_content)

        elif item.get_type() == ebooklib.ITEM_IMAGE:
            # Save image
            image_counter += 1
            img_name = item.get_name().split('/')[-1]
            if not img_name:
                img_name = f"image_{image_counter}.{item.media_type.split('/')[-1]}"
            images[img_name] = item.get_content()

    # Combine all chapters
    full_markdown = "\n\n---\n\n".join(chapters)

    # Save as markdown
    output_path = os.path.join(output_dir, f"{base_name}.md")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(full_markdown)

    print(f"OK Conversion complete!")
    print(f"OK Output saved to: {output_path}")
    print(f"OK Total chapters: {len(chapters)}")

    # Save images if any
    if images:
        images_dir = os.path.join(output_dir, f"{base_name}_images")
        os.makedirs(images_dir, exist_ok=True)
        for img_name, img_data in images.items():
            img_path = os.path.join(images_dir, img_name)
            with open(img_path, "wb") as f:
                f.write(img_data)
        print(f"OK {len(images)} images saved to: {images_dir}")

    # Save metadata if available
    metadata = {
        'title': book.get_metadata('DC', 'title'),
        'creator': book.get_metadata('DC', 'creator'),
        'language': book.get_metadata('DC', 'language'),
        'publisher': book.get_metadata('DC', 'publisher'),
        'description': book.get_metadata('DC', 'description'),
    }

    if any(metadata.values()):
        metadata_path = os.path.join(output_dir, f"{base_name}_metadata.json")
        with open(metadata_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        print(f"OK Metadata saved to: {metadata_path}")


if __name__ == "__main__":
    # Convert the EPUB file in the input directory
    epub_path = "input/the-art-of-spending-money.epub"
    convert_epub_to_markdown(epub_path)
