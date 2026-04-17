#!/usr/bin/env python3
"""
HML to Markdown Converter
Converts Hancom Office (.hml) files to Markdown format.
- 표/제목: XML 직접 파싱 (정확한 마크다운 테이블)
- 이미지: HML 내 Base64 BINDATA 추출 → 실제 이미지 파일 저장
"""
import xml.etree.ElementTree as ET
import base64
import os
import re
import sys
from pathlib import Path


# ── 이미지 추출 ────────────────────────────────────────────────────────────────

def extract_images_from_hml(tree, images_dir: Path) -> dict:
    """
    HML의 BINDATASTORAGE에서 Base64 이미지를 추출해 파일로 저장.
    BINITEM의 Format 속성으로 확장자 결정.
    Returns: {bin_id: filename}  예) {'1': 'BIN0001.png'}
    """
    images_dir.mkdir(parents=True, exist_ok=True)
    bin_format = {}
    for item in tree.findall('.//BINITEM'):
        bid = item.get('BinData')
        fmt = item.get('Format', 'PNG').lower()
        if bid:
            bin_format[bid] = fmt

    id_to_file = {}
    for bindata in tree.findall('.//BINDATA'):
        bid = bindata.get('Id')
        enc = bindata.get('Encoding', 'Base64')
        raw = (bindata.text or '').strip()
        if not raw or enc.lower() != 'base64':
            continue

        fmt = bin_format.get(bid, 'png')
        filename = f'BIN{int(bid):04d}.{fmt}'
        out_path = images_dir / filename
        try:
            img_bytes = base64.b64decode(raw)
            out_path.write_bytes(img_bytes)
            id_to_file[bid] = filename
            print(f"  이미지 추출: {filename} ({len(img_bytes):,} bytes)")
        except Exception as e:
            print(f"  경고: 이미지 {bid} 추출 실패 - {e}")

    return id_to_file


def build_picture_order(tree) -> list:
    """
    문서 BODY에 등장하는 PICTURE 순서대로 BinItem Id 수집.
    Returns: ['1', '2', ...] (None 없음)
    """
    body = tree.find('.//BODY')
    if body is None:
        return []
    order = []
    for pic in body.findall('.//PICTURE'):
        for img in pic.findall('.//IMAGE'):
            bid = img.get('BinItem')
            if bid:
                order.append(bid)
        if not pic.findall('.//IMAGE'):
            order.append(None)
    return order


# ── 텍스트 추출 ────────────────────────────────────────────────────────────────

def extract_text_from_p(p_elem) -> str:
    """P 요소에서 순수 텍스트만 추출 (TABLE/PICTURE 제외)."""
    texts = []
    for text_elem in p_elem.findall('TEXT'):
        for child in text_elem:
            if child.tag == 'CHAR' and child.text:
                texts.append(child.text)
            elif child.tag == 'TAB':
                texts.append(' ')
    return ''.join(texts).strip()


def detect_structure(text: str):
    """
    텍스트 패턴으로 단락 종류 판단.
    Returns (kind, level, text)  kind: 'heading' | 'bullet' | 'paragraph'
    """
    if not text:
        return 'paragraph', 0, text

    # 숫자 점 계층
    if re.match(r'^\d+\.\d+\.\d+\s', text):  return 'heading', 4, text
    if re.match(r'^\d+\.\d+\s', text):        return 'heading', 3, text
    if re.match(r'^\d+\.\s.+', text):         return 'heading', 2, text

    # 괄호 번호: 1) 가) 등
    if re.match(r'^[\d가-힣]+\)\s+.+', text): return 'heading', 3, text

    # 기호 계층
    if re.match(r'^[□■]\s*.+', text):         return 'heading', 2, text
    if re.match(r'^[○●◎]\s*.+', text):        return 'heading', 3, text
    if re.match(r'^[▶▷]\s*.+', text):         return 'heading', 4, text
    if re.match(r'^[▪▫\-]\s*.+', text):       return 'bullet',  0, text
    if re.match(r'^[※]', text):               return 'paragraph', 0, f'> {text}'

    return 'paragraph', 0, text


# ── 표 추출 ───────────────────────────────────────────────────────────────────

def extract_table(table_elem) -> str:
    """TABLE 요소 → 병합셀 있으면 HTML <table>, 단순표는 마크다운."""
    col_count = int(table_elem.get('ColCount', 0))

    # 셀 정보 수집: (text, col_span, row_span, is_header)
    has_merge = False
    raw_rows = []
    for row_idx, row_elem in enumerate(table_elem.findall('.//ROW')):
        raw_cells = []
        for cell_elem in row_elem.findall('CELL'):
            col_span = int(cell_elem.get('ColSpan', 1))
            row_span = int(cell_elem.get('RowSpan', 1))
            col_addr = int(cell_elem.get('ColAddr', 0))
            if col_span > 1 or row_span > 1:
                has_merge = True
            parts = []
            for p in cell_elem.findall('.//P'):
                t = extract_text_from_p(p)
                if t:
                    parts.append(t)
            text = '<br>'.join(parts)
            raw_cells.append((col_addr, col_span, row_span, text))
        if raw_cells:
            raw_rows.append((row_idx, raw_cells))

    if not raw_rows:
        return ''

    if has_merge:
        return _table_to_html(raw_rows, col_count)
    else:
        return _table_to_markdown(raw_rows, col_count)


def _table_to_html(raw_rows, col_count) -> str:
    """병합셀 포함 표 → HTML <table>."""
    lines = ['<table>']
    for row_idx, (_, cells) in enumerate(raw_rows):
        lines.append('<tr>')
        tag = 'th' if row_idx == 0 else 'td'
        for _, col_span, row_span, text in cells:
            attrs = ''
            if col_span > 1:
                attrs += f' colspan="{col_span}"'
            if row_span > 1:
                attrs += f' rowspan="{row_span}"'
            lines.append(f'<{tag}{attrs}>{text}</{tag}>')
        lines.append('</tr>')
    lines.append('</table>')
    return '\n'.join(lines)


def _table_to_markdown(raw_rows, col_count) -> str:
    """단순 표 (병합셀 없음) → 마크다운 파이프 테이블."""
    rows = []
    for _, cells in raw_rows:
        grid = {}
        for col_addr, col_span, _, text in cells:
            grid[col_addr] = text
        n = col_count if col_count > 0 else (max(grid.keys()) + 1)
        rows.append([grid.get(i, '') for i in range(n)])

    max_cols = max(len(r) for r in rows)
    for row in rows:
        row += [''] * (max_cols - len(row))

    def esc(s):
        return s.replace('|', '\\|').replace('\n', ' ')

    lines = []
    lines.append('| ' + ' | '.join(esc(c) for c in rows[0]) + ' |')
    lines.append('| ' + ' | '.join(['---'] * max_cols) + ' |')
    for row in rows[1:]:
        lines.append('| ' + ' | '.join(esc(c) for c in row) + ' |')
    return '\n'.join(lines)


# ── P 처리 ────────────────────────────────────────────────────────────────────

def process_p(p_elem, pic_counter: list, bin_order: list, id_to_file: dict,
              base_name: str) -> list:
    """
    P 요소 처리 → 마크다운 줄 목록 반환.
    pic_counter: [int] 변경 가능한 카운터
    """
    lines = []
    has_table = False
    has_pic   = False

    for text_elem in p_elem.findall('TEXT'):
        for child in text_elem:
            if child.tag == 'TABLE':
                has_table = True
                md = extract_table(child)
                if md:
                    lines.append(md)

            elif child.tag == 'PICTURE':
                has_pic = True
                # 이 문서에서 몇 번째 그림인지 추적
                idx = pic_counter[0]
                pic_counter[0] += 1

                # bin_order에서 해당 순서의 BinItem Id 확인
                if idx < len(bin_order):
                    bid = bin_order[idx]
                    filename = id_to_file.get(bid, '')
                    if filename:
                        ref = f'{base_name}_images/{filename}'
                        lines.append(f'![그림 {idx+1}]({ref})')
                    else:
                        lines.append(f'![그림 {idx+1}](그림_{idx+1}.png)')
                else:
                    lines.append(f'![그림 {idx+1}](그림_{idx+1}.png)')

            elif child.tag in ('HEADER', 'FOOTER'):
                pass  # 머리말/꼬리말 무시

    # 표나 그림이 없으면 텍스트 처리
    if not has_table and not has_pic:
        text = extract_text_from_p(p_elem)
        if text:
            kind, level, formatted = detect_structure(text)
            if kind == 'heading':
                lines.append(f'{"#" * level} {formatted}')
            elif kind == 'bullet':
                body = re.sub(r'^[▪▫\-]\s*', '', formatted)
                lines.append(f'- {body}')
            else:
                lines.append(formatted)

    return lines


# ── 메인 변환 ─────────────────────────────────────────────────────────────────

def convert_hml_to_md(hml_path, output_path=None):
    """HML 파일을 Markdown으로 변환."""
    hml_path = Path(hml_path)
    with open(hml_path, 'r', encoding='utf-8-sig') as f:
        content = f.read()

    tree = ET.fromstring(content)

    # 출력 경로 결정
    if output_path is None:
        output_dir = hml_path.parent.parent / 'output'
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / (hml_path.stem + '.md')
    else:
        output_path = Path(output_path)
        output_dir = output_path.parent

    base_name = hml_path.stem
    images_dir = output_dir / f'{base_name}_images'

    # 1) 이미지 추출
    print(f"  이미지 추출 중...")
    id_to_file = extract_images_from_hml(tree, images_dir)
    bin_order  = build_picture_order(tree)
    print(f"  이미지 {len(id_to_file)}개 추출 완료")

    # 2) 문서 제목
    title_elem = tree.find('.//TITLE')
    doc_title = (title_elem.text.strip()
                 if title_elem is not None and title_elem.text
                 else hml_path.stem)
    md_lines = [f'# {doc_title}', '']

    # 3) BODY 파싱
    body = tree.find('.//BODY')
    if body is None:
        print(f"Warning: No BODY found in {hml_path}")
        return

    pic_counter = [0]

    for section in body.findall('.//SECTION'):
        for p_elem in section.findall('P'):
            chunk = process_p(p_elem, pic_counter, bin_order, id_to_file, base_name)
            for line in chunk:
                if line.startswith('#'):
                    if md_lines and md_lines[-1] != '':
                        md_lines.append('')
                    md_lines.append(line)
                    md_lines.append('')
                elif line.startswith('|') or line.startswith('-'):
                    md_lines.append(line)
                else:
                    md_lines.append(line)
                    md_lines.append('')

    # 4) 정리 및 저장
    result = '\n'.join(md_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result)

    print(f"  완료: {output_path}")
    return output_path


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
        print(f"\n변환 시작: {path}")
        convert_hml_to_md(path)
    else:
        script_dir = Path(__file__).parent
        input_dir  = script_dir / 'input'

        if not input_dir.exists():
            print(f"input 폴더 없음: {input_dir}")
            return

        hml_files = sorted(input_dir.glob('*.hml'))
        if not hml_files:
            print("input 폴더에 .hml 파일 없음")
            return

        print(f"HML 파일 {len(hml_files)}개 발견")
        print("=" * 60)
        for hml_file in hml_files:
            print(f"\n변환 중: {hml_file.name}")
            convert_hml_to_md(hml_file)
        print("\n" + "=" * 60)
        print("전체 변환 완료")


if __name__ == '__main__':
    main()
