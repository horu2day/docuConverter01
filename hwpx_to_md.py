#!/usr/bin/env python3
"""
HWPX to Markdown Converter
HWPX(ZIP+XML) 파일을 Markdown으로 변환.
- 표/병합셀: HTML <table> (colspan/rowspan 보존)
- 이미지: BinData/ 폴더에서 직접 추출
- 제목: 텍스트 패턴 기반 감지 (□○▶ 1. 1) 등)
"""
import zipfile
import xml.etree.ElementTree as ET
import re
import sys
from pathlib import Path

NS = {
    'hp': 'http://www.hancom.co.kr/hwpml/2011/paragraph',
    'hs': 'http://www.hancom.co.kr/hwpml/2011/section',
    'hc': 'http://www.hancom.co.kr/hwpml/2011/core',
    'hh': 'http://www.hancom.co.kr/hwpml/2011/head',
}


# ── 이미지 추출 ────────────────────────────────────────────────────────────────

def extract_images(zf: zipfile.ZipFile, images_dir: Path) -> dict:
    """BinData/ 폴더의 이미지를 output 폴더로 복사. {binaryItemIDRef: filename}"""
    images_dir.mkdir(parents=True, exist_ok=True)
    id_to_file = {}
    for name in zf.namelist():
        if not name.startswith('BinData/'):
            continue
        filename = Path(name).name
        if not filename:
            continue
        stem = Path(filename).stem  # 'image1'
        out_path = images_dir / filename
        out_path.write_bytes(zf.read(name))
        id_to_file[stem] = filename
        print(f'  이미지 추출: {filename} ({out_path.stat().st_size:,} bytes)')
    return id_to_file


# ── 텍스트 추출 ────────────────────────────────────────────────────────────────

def extract_text_from_para(p_elem) -> str:
    """hp:p 에서 순수 텍스트 추출 (표/그림 제외)."""
    parts = []
    for run in p_elem.findall('hp:run', NS):
        for t in run.findall('hp:t', NS):
            if t.text:
                parts.append(t.text)
        for tab in run.findall('hp:tab', NS):
            parts.append(' ')
    return ''.join(parts).strip()


def detect_structure(text: str):
    """텍스트 패턴으로 단락 종류 판단 (hml_to_md.py와 동일 로직)."""
    if not text:
        return 'paragraph', 0, text
    if re.match(r'^\d+\.\d+\.\d+\s', text):  return 'heading', 4, text
    if re.match(r'^\d+\.\d+\s', text):        return 'heading', 3, text
    if re.match(r'^\d+\.\s.+', text):         return 'heading', 2, text
    if re.match(r'^[\d가-힣]+\)\s+.+', text): return 'heading', 3, text
    if re.match(r'^[□■]\s*.+', text):         return 'heading', 2, text
    if re.match(r'^[○●◎]\s*.+', text):        return 'heading', 3, text
    if re.match(r'^[▶▷]\s*.+', text):         return 'heading', 4, text
    if re.match(r'^[▪▫\-]\s*.+', text):       return 'bullet',  0, text
    if re.match(r'^[※]', text):               return 'paragraph', 0, f'> {text}'
    return 'paragraph', 0, text


# ── 표 처리 ───────────────────────────────────────────────────────────────────

def extract_cell_text(tc_elem) -> str:
    """hp:tc → hp:subList → hp:p 에서 텍스트 추출."""
    parts = []
    for sub in tc_elem.findall('hp:subList', NS):
        for p in sub.findall('hp:p', NS):
            if p.find('.//hp:tbl', NS) is not None:
                continue
            t = extract_text_from_para(p)
            if t:
                parts.append(t)
    return '<br>'.join(parts)


def _get_span(tc_elem):
    """hp:tc의 colspan/rowspan 추출 (속성 또는 cellSpan 자식 요소)."""
    col_span = int(tc_elem.get('colSpan', 1))
    row_span = int(tc_elem.get('rowSpan', 1))
    cs = tc_elem.find('hp:cellSpan', NS)
    if cs is not None:
        col_span = int(cs.get('colSpan', col_span))
        row_span = int(cs.get('rowSpan', row_span))
    return col_span, row_span


def extract_table(tbl_elem) -> str:
    """hp:tbl → 병합셀 있으면 HTML, 없으면 마크다운."""
    has_merge = False
    raw_rows = []

    for tr in tbl_elem.findall('hp:tr', NS):
        cells = []
        for tc in tr.findall('hp:tc', NS):
            col_span, row_span = _get_span(tc)
            if col_span > 1 or row_span > 1:
                has_merge = True
            text = extract_cell_text(tc)
            cells.append((col_span, row_span, text))
        if cells:
            raw_rows.append(cells)

    if not raw_rows:
        return ''

    if has_merge:
        return _to_html_table(raw_rows)
    else:
        return _to_md_table(raw_rows)


def _to_html_table(raw_rows) -> str:
    lines = ['<table>']
    for ri, cells in enumerate(raw_rows):
        lines.append('<tr>')
        tag = 'th' if ri == 0 else 'td'
        for col_span, row_span, text in cells:
            attrs = ''
            if col_span > 1: attrs += f' colspan="{col_span}"'
            if row_span > 1: attrs += f' rowspan="{row_span}"'
            lines.append(f'<{tag}{attrs}>{text}</{tag}>')
        lines.append('</tr>')
    lines.append('</table>')
    return '\n'.join(lines)


def _to_md_table(raw_rows) -> str:
    rows = [[text for _, _, text in cells] for cells in raw_rows]
    max_cols = max(len(r) for r in rows)
    for row in rows:
        row += [''] * (max_cols - len(row))

    def esc(s):
        return s.replace('|', '\\|').replace('\n', ' ')

    lines = ['| ' + ' | '.join(esc(c) for c in rows[0]) + ' |',
             '| ' + ' | '.join(['---'] * max_cols) + ' |']
    for row in rows[1:]:
        lines.append('| ' + ' | '.join(esc(c) for c in row) + ' |')
    return '\n'.join(lines)


# ── 단락 처리 ─────────────────────────────────────────────────────────────────

def process_para(p_elem, pic_counter: list, id_to_file: dict, base_name: str) -> list:
    """hp:p 처리 → 마크다운 줄 목록."""
    lines = []

    # 표
    tbl = p_elem.find('.//hp:tbl', NS)
    if tbl is not None:
        md = extract_table(tbl)
        if md:
            lines.append(md)
        return lines

    # 그림
    pic = p_elem.find('.//hp:pic', NS)
    if pic is not None:
        idx = pic_counter[0]
        pic_counter[0] += 1
        img_elem = pic.find('.//hc:img', NS)
        if img_elem is not None:
            ref_id = img_elem.get('binaryItemIDRef', '')
            filename = id_to_file.get(ref_id, '')
            if filename:
                lines.append(f'![그림 {idx+1}]({base_name}_images/{filename})')
            else:
                lines.append(f'![그림 {idx+1}](그림_{idx+1}.png)')
        else:
            lines.append(f'![그림 {idx+1}](그림_{idx+1}.png)')
        return lines

    # 텍스트
    text = extract_text_from_para(p_elem)
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

def convert_hwpx_to_md(hwpx_path, output_path=None):
    """HWPX 파일을 Markdown으로 변환."""
    hwpx_path = Path(hwpx_path)

    if output_path is None:
        output_dir = hwpx_path.parent.parent / 'output'
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / (hwpx_path.stem + '.md')
    else:
        output_path = Path(output_path)
        output_dir = output_path.parent

    base_name = hwpx_path.stem
    images_dir = output_dir / f'{base_name}_images'

    with zipfile.ZipFile(hwpx_path, 'r') as zf:
        # 1) 이미지 추출
        print('  이미지 추출 중...')
        id_to_file = extract_images(zf, images_dir)
        print(f'  이미지 {len(id_to_file)}개 추출 완료')

        # 2) section XML 목록
        section_files = sorted(
            [n for n in zf.namelist() if re.match(r'Contents/section\d+\.xml', n)]
        )

        # 3) 단락 파싱
        md_lines = []
        pic_counter = [0]

        for sec_file in section_files:
            root = ET.fromstring(zf.read(sec_file))
            # 직접 자식 hp:p만 처리 — 표 내부 hp:p 중복 방지
            # secPr 포함 단락(머리말/꼬리말/섹션설정) 스킵
            for p_elem in root.findall('hp:p', NS):
                if p_elem.find('.//hp:secPr', NS) is not None:
                    continue
                chunk = process_para(p_elem, pic_counter, id_to_file, base_name)
                for line in chunk:
                    if line.startswith('#'):
                        if md_lines and md_lines[-1] != '':
                            md_lines.append('')
                        md_lines.append(line)
                        md_lines.append('')
                    elif line.startswith('<table') or line.startswith('|'):
                        md_lines.append(line)
                        md_lines.append('')
                    elif line.startswith('!['):
                        md_lines.append(line)
                        md_lines.append('')
                    elif line:
                        md_lines.append(line)
                        md_lines.append('')

    # 4) 정리 및 저장
    result = '\n'.join(md_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(result)

    print(f'  완료: {output_path}')
    return output_path


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) > 1:
        path = sys.argv[1]
        print(f'\n변환 시작: {path}')
        convert_hwpx_to_md(path)
    else:
        script_dir = Path(__file__).parent
        input_dir = script_dir / 'input'

        if not input_dir.exists():
            print(f'input 폴더 없음: {input_dir}')
            return

        hwpx_files = sorted(input_dir.glob('*.hwpx'))
        if not hwpx_files:
            print('input 폴더에 .hwpx 파일 없음')
            return

        print(f'HWPX 파일 {len(hwpx_files)}개 발견')
        print('=' * 60)
        for f in hwpx_files:
            print(f'\n변환 중: {f.name}')
            convert_hwpx_to_md(f)
        print('\n' + '=' * 60)
        print('전체 변환 완료')


if __name__ == '__main__':
    main()
