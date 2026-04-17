#!/usr/bin/env python3
"""
HWP to Markdown Converter
1차 시도: 한컴오피스 COM 자동화로 HWP → HML → MD
2차 시도(폴백): pyhwp HTML 변환 → MD 직접 생성

한컴오피스 미설치 환경에서도 pyhwp fallback으로 동작합니다.
"""
import sys
import re
import tempfile
import shutil
from pathlib import Path


# ── COM 방식: HWP → HML ───────────────────────────────────────────────────────

def _com_hwp_to_hml(hwp_path: Path, hml_path: Path, timeout: int = 15) -> bool:
    """한컴오피스 COM으로 HWP→HML 변환. 성공 True. timeout초 초과시 False."""
    import threading

    result = [False]

    def _run():
        try:
            import pythoncom, win32com.client
        except ImportError:
            return

        hwp = None
        try:
            pythoncom.CoInitialize()
            hwp = win32com.client.Dispatch('HWPFrame.HwpObject')
            try:
                hwp.RegisterModule('FilePathCheckDLL', 'SecurityModule')
            except Exception:
                pass

            win_path = str(hwp_path).replace('/', '\\')
            hml_win  = str(hml_path).replace('/', '\\')

            ok = hwp.Open(win_path, 'HWP', 'forceopen:true')
            if not ok:
                return

            hwp.SaveAs(hml_win, 'HML', '')
            result[0] = hml_path.exists()

        except Exception as e:
            print(f'  COM 오류: {e}')
        finally:
            if hwp:
                try: hwp.Quit()
                except Exception: pass
            try: pythoncom.CoUninitialize()
            except Exception: pass

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    t.join(timeout)
    if t.is_alive():
        print(f'  COM 타임아웃 ({timeout}초) — pyhwp로 전환')
    return result[0]


# ── pyhwp 방식: HWP → XHTML → MD ─────────────────────────────────────────────

def _pyhwp_hwp_to_md(hwp_path: Path, output_path: Path, base_name: str) -> bool:
    """pyhwp HTML 변환 후 BeautifulSoup으로 MD 생성."""
    try:
        from hwp5.hwp5html import HTMLTransform
        from hwp5.xmlmodel import Hwp5File
        from bs4 import BeautifulSoup
    except ImportError as e:
        print(f'  pyhwp/bs4 미설치: {e}')
        return False

    tmp_dir = Path(tempfile.mkdtemp())
    try:
        # 1) HWP → XHTML
        f = Hwp5File(str(hwp_path))
        HTMLTransform().transform_hwp5_to_dir(f, str(tmp_dir))

        xhtml_path = tmp_dir / 'index.xhtml'
        if not xhtml_path.exists():
            return False

        # 2) 이미지 복사
        images_dir = output_path.parent / f'{base_name}_images'
        images_dir.mkdir(exist_ok=True)
        bindata_dir = tmp_dir / 'bindata'
        img_map = {}
        if bindata_dir.exists():
            for img in bindata_dir.iterdir():
                shutil.copy(img, images_dir / img.name)
                img_map[img.name] = img.name
                print(f'  이미지: {img.name}')

        # 3) XHTML 파싱 → MD
        soup = BeautifulSoup(xhtml_path.read_text(encoding='utf-8'), 'lxml-xml')

        # 머리말/꼬리말만 제거 (HeaderPageFooter는 본문 포함하므로 제외)
        for area in soup.find_all(class_=re.compile(r'^(HeaderArea|FooterArea|Header parashape|Footer parashape)$')):
            area.decompose()

        md_lines = []
        img_counter = [0]

        # pyhwp: 표는 <p><span class="TableControl"><table> 로 중첩됨
        # → <p> 순회 시 내부 표 처리, 독립 <table>은 스킵
        for elem in soup.find_all(['p', 'table']):
            # 표 셀/행 안의 요소는 스킵
            if elem.find_parent('table'):
                continue

            if elem.name == 'table':
                # p 안에 있는 표는 p 순회 시 처리하므로 스킵
                if elem.find_parent('p'):
                    continue
                md = _table_to_md(elem)
                if md:
                    md_lines.append(md)
                    md_lines.append('')

            elif elem.name == 'p':
                # 이미지
                for img in elem.find_all('img'):
                    src = img.get('src', '')
                    filename = Path(src).name
                    if filename in img_map:
                        img_counter[0] += 1
                        md_lines.append(
                            f'![그림 {img_counter[0]}]({base_name}_images/{filename})'
                        )
                        md_lines.append('')

                # 표 포함 단락 → 표로 처리
                inner_table = elem.find('table')
                if inner_table:
                    md = _table_to_md(inner_table)
                    if md:
                        md_lines.append(md)
                        md_lines.append('')
                    continue

                # 순수 텍스트 단락
                text = elem.get_text(separator=' ', strip=True)
                text = re.sub(r'\s+', ' ', text).strip()
                if not text:
                    continue

                kind, level, fmt = _detect_structure(text)
                if kind == 'heading':
                    if md_lines and md_lines[-1] != '':
                        md_lines.append('')
                    md_lines.append(f'{"#" * level} {fmt}')
                    md_lines.append('')
                elif kind == 'bullet':
                    body = re.sub(r'^[▪▫\-]\s*', '', fmt)
                    md_lines.append(f'- {body}')
                else:
                    md_lines.append(fmt)
                    md_lines.append('')

        result = '\n'.join(md_lines)
        result = re.sub(r'\n{3,}', '\n\n', result)
        output_path.write_text(result, encoding='utf-8')
        print(f'  완료 (pyhwp): {output_path}')
        return True

    except Exception as e:
        print(f'  pyhwp 오류: {e}')
        import traceback; traceback.print_exc()
        return False

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _detect_structure(text: str):
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


def _table_to_md(table_elem) -> str:
    """BeautifulSoup table → HTML <table> (colspan/rowspan 보존)."""
    rows = table_elem.find_all('tr', recursive=False)
    if not rows:
        rows = table_elem.find_all('tr')
    if not rows:
        return ''

    has_merge = False
    parsed = []
    for tr in rows:
        cells = []
        for td in tr.find_all(['td', 'th']):
            cs = int(td.get('colspan', 1))
            rs = int(td.get('rowspan', 1))
            if cs > 1 or rs > 1:
                has_merge = True
            text = td.get_text(separator='<br>', strip=True)
            cells.append((cs, rs, text))
        if cells:
            parsed.append(cells)

    if not parsed:
        return ''

    if has_merge:
        lines = ['<table>']
        for ri, cells in enumerate(parsed):
            lines.append('<tr>')
            tag = 'th' if ri == 0 else 'td'
            for cs, rs, text in cells:
                attrs = ''
                if cs > 1: attrs += f' colspan="{cs}"'
                if rs > 1: attrs += f' rowspan="{rs}"'
                lines.append(f'<{tag}{attrs}>{text}</{tag}>')
            lines.append('</tr>')
        lines.append('</table>')
        return '\n'.join(lines)
    else:
        rows_text = [[text for _, _, text in cells] for cells in parsed]
        max_cols = max(len(r) for r in rows_text)
        for row in rows_text:
            row += [''] * (max_cols - len(row))

        def esc(s): return s.replace('|', '\\|')
        lines = ['| ' + ' | '.join(esc(c) for c in rows_text[0]) + ' |',
                 '| ' + ' | '.join(['---'] * max_cols) + ' |']
        for row in rows_text[1:]:
            lines.append('| ' + ' | '.join(esc(c) for c in row) + ' |')
        return '\n'.join(lines)


# ── 통합 변환 ─────────────────────────────────────────────────────────────────

def convert_hwp_to_md(hwp_path, output_path=None) -> Path | None:
    """
    HWP → MD 변환.
    1) COM으로 HWP→HML 변환 후 hml_to_md 실행
    2) COM 실패 시 pyhwp HTML 방식으로 직접 변환
    """
    hwp_path = Path(hwp_path)
    if output_path is None:
        output_dir = hwp_path.parent.parent / 'output'
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / (hwp_path.stem + '.md')
    else:
        output_path = Path(output_path)

    base_name = hwp_path.stem

    # 1차: COM → HML → MD
    print('  COM 변환 시도...')
    hml_path = output_path.with_suffix('.hml')
    if _com_hwp_to_hml(hwp_path, hml_path):
        print('  COM 성공, HML→MD 변환 중...')
        try:
            from hml_to_md import convert_hml_to_md
            result = convert_hml_to_md(hml_path, output_path)
            hml_path.unlink(missing_ok=True)
            return result
        except Exception as e:
            print(f'  HML→MD 오류: {e}')
            hml_path.unlink(missing_ok=True)

    # 2차: pyhwp HTML → MD
    print('  COM 실패. pyhwp 방식으로 변환...')
    if _pyhwp_hwp_to_md(hwp_path, output_path, base_name):
        return output_path

    print('  변환 실패')
    return None


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) > 1:
        hwp_path = sys.argv[1]
        out = sys.argv[2] if len(sys.argv) > 2 else None
        print(f'\nHWP → MD 변환: {hwp_path}')
        result = convert_hwp_to_md(hwp_path, out)
        print('완료:' if result else '실패', result or '')
    else:
        script_dir = Path(__file__).parent
        input_dir = script_dir / 'input'
        hwp_files = sorted(input_dir.glob('*.hwp'))
        if not hwp_files:
            print('input 폴더에 .hwp 파일 없음')
            return
        print(f'HWP 파일 {len(hwp_files)}개')
        print('=' * 60)
        for f in hwp_files:
            print(f'\n변환 중: {f.name}')
            convert_hwp_to_md(f)
        print('\n' + '=' * 60)
        print('완료')


if __name__ == '__main__':
    main()
