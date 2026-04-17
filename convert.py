#!/usr/bin/env python3
"""
통합 문서 → Markdown 변환기
.hwp / .hwpx / .hml / .pdf / .html 자동 감지 후 변환.

사용법:
  python convert.py                  # input/ 폴더 전체 일괄 변환
  python convert.py 파일.hwpx        # 단일 파일 변환
  python convert.py -o output/ *.hwpx  # 출력 폴더 지정
"""
import sys
import os
import argparse
from pathlib import Path

# 각 변환기 임포트
from hml_to_md import convert_hml_to_md
from hwpx_to_md import convert_hwpx_to_md


SUPPORTED = {'.hwp', '.hwpx', '.hml'}


def convert_file(file_path: Path, output_dir: Path = None) -> bool:
    """파일 하나를 변환. 성공 True, 실패 False."""
    ext = file_path.suffix.lower()

    if ext not in SUPPORTED:
        print(f'  건너뜀: 지원하지 않는 형식 ({ext})')
        return False

    try:
        if ext == '.hwp':
            from hwp_to_hml import convert_hwp_to_md
            out = output_dir / (file_path.stem + '.md') if output_dir else None
            return bool(convert_hwp_to_md(file_path, out))

        elif ext == '.hwpx':
            out = None
            if output_dir:
                out = output_dir / (file_path.stem + '.md')
            convert_hwpx_to_md(file_path, out)
            return True

        elif ext == '.hml':
            out = None
            if output_dir:
                out = output_dir / (file_path.stem + '.md')
            convert_hml_to_md(file_path, out)
            return True

    except Exception as e:
        print(f'  오류: {e}')
        import traceback; traceback.print_exc()
        return False

    return False



def convert_all(input_dir: Path, output_dir: Path):
    """input_dir 내 지원 파일 전체 변환."""
    files = []
    for ext in SUPPORTED:
        files.extend(sorted(input_dir.glob(f'*{ext}')))

    if not files:
        print(f'변환할 파일 없음: {input_dir} ({", ".join(SUPPORTED)})')
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f'파일 {len(files)}개 발견')
    print('=' * 60)

    ok = fail = 0
    for f in files:
        print(f'\n[{f.suffix.upper()}] {f.name}')
        if convert_file(f, output_dir):
            ok += 1
        else:
            fail += 1

    print('\n' + '=' * 60)
    print(f'완료: 성공 {ok} / 실패 {fail} / 합계 {len(files)}')


def main():
    parser = argparse.ArgumentParser(
        description='HWP/HWPX/HML → Markdown 통합 변환기'
    )
    parser.add_argument('files', nargs='*', help='변환할 파일 (없으면 input/ 폴더 전체)')
    parser.add_argument('-o', '--output', default=None, help='출력 폴더 (기본: output/)')
    args = parser.parse_args()

    script_dir = Path(__file__).parent
    output_dir = Path(args.output) if args.output else script_dir / 'output'

    if args.files:
        output_dir.mkdir(parents=True, exist_ok=True)
        ok = fail = 0
        for f in args.files:
            fp = Path(f)
            print(f'\n[{fp.suffix.upper()}] {fp.name}')
            if convert_file(fp, output_dir):
                ok += 1
            else:
                fail += 1
        print(f'\n완료: 성공 {ok} / 실패 {fail}')
    else:
        input_dir = script_dir / 'input'
        if not input_dir.exists():
            print(f'input 폴더 없음: {input_dir}')
            sys.exit(1)
        convert_all(input_dir, output_dir)


if __name__ == '__main__':
    main()
