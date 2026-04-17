#!/usr/bin/env python3
"""
docuConverter — 문서 → Markdown 변환 도구 모음

지원 포맷:
  PDF  → Markdown  (marker-pdf 기반, 이미지 유/무 선택)
  EPUB → Markdown  (ebooklib + BeautifulSoup 기반)
  HWP  → Markdown  (COM 자동화 → pyhwp 폴백)
  HWPX → Markdown  (ZIP+XML 직접 파싱)
  HML  → Markdown  (XML 직접 파싱)
  HTML → Markdown  (markdownify 기반)

시나리오:
  1. PDF 단일 변환 (이미지 포함, 고품질)
  2. PDF 단일 변환 (텍스트 전용, 빠름)
  3. PDF 배치 변환 (이미지 포함, 순차)
  4. PDF 배치 변환 (텍스트 전용, 순차, 빠름)
  5. PDF 배치 변환 (병렬 처리, 멀티코어)
  6. EPUB 단일 변환
  7. EPUB 배치 변환
  8. HWP / HWPX / HML 변환 (한글 문서)
  9. HTML 배치 변환 (input/ 폴더)
 10. 이미지만 추출 (PDF → 이미지 파일)
 11. Markdown 병합 (output/ 폴더의 .md 파일들을 하나로)
 12. 이미지 경로 업데이트 (Markdown 내 이미지 링크 재연결)
"""

import os
import sys
import glob
from pathlib import Path


# ─── 시나리오 함수들 ──────────────────────────────────────────────────────────

def scenario_pdf_single_with_images():
    """PDF 단일 변환 — 이미지 포함 (고품질, 느림)"""
    from convert_with_cropped_images import convert_pdf_with_cropped_images

    pdf_path = input("변환할 PDF 경로를 입력하세요: ").strip()
    if not pdf_path:
        pdf_files = sorted(glob.glob("input/*.pdf"))
        if not pdf_files:
            print("ERROR: input/ 폴더에 PDF 파일이 없습니다.")
            return
        pdf_path = pdf_files[0]
        print(f"  → 자동 선택: {pdf_path}")

    output_dir = input("출력 폴더 [기본: output]: ").strip() or "output"
    convert_pdf_with_cropped_images(pdf_path, output_dir)


def scenario_pdf_single_fast():
    """PDF 단일 변환 — 텍스트 전용 (빠름)"""
    from convert_pdfs_fast import convert_pdf_to_markdown_fast

    pdf_path = input("변환할 PDF 경로를 입력하세요: ").strip()
    if not pdf_path:
        pdf_files = sorted(glob.glob("input/*.pdf"))
        if not pdf_files:
            print("ERROR: input/ 폴더에 PDF 파일이 없습니다.")
            return
        pdf_path = pdf_files[0]
        print(f"  → 자동 선택: {pdf_path}")

    output_dir = input("출력 폴더 [기본: output]: ").strip() or "output"
    convert_pdf_to_markdown_fast(pdf_path, output_dir)


def scenario_pdf_batch_with_images():
    """PDF 배치 변환 — 이미지 포함 (순차, input/ → output/)"""
    from convert_with_cropped_images import convert_all_pdfs

    input_dir = input("입력 폴더 [기본: input]: ").strip() or "input"
    output_dir = input("출력 폴더 [기본: output]: ").strip() or "output"
    convert_all_pdfs(input_dir, output_dir)


def scenario_pdf_batch_fast():
    """PDF 배치 변환 — 텍스트 전용 (순차, 빠름)"""
    from convert_pdfs_fast import convert_all_pdfs_fast

    input_dir = input("입력 폴더 [기본: input]: ").strip() or "input"
    output_dir = input("출력 폴더 [기본: output]: ").strip() or "output"
    convert_all_pdfs_fast(input_dir, output_dir)


def scenario_pdf_batch_parallel():
    """PDF 배치 변환 — 병렬 처리 (멀티코어)"""
    from convert_pdfs_parallel import convert_all_pdfs_parallel
    import multiprocessing

    input_dir = input("입력 폴더 [기본: input]: ").strip() or "input"
    output_dir = input("출력 폴더 [기본: output]: ").strip() or "output"
    cpu_count = multiprocessing.cpu_count()
    workers_input = input(f"병렬 워커 수 [기본: 2, CPU: {cpu_count}]: ").strip()
    max_workers = int(workers_input) if workers_input.isdigit() else 2
    convert_all_pdfs_parallel(input_dir, output_dir, max_workers)


def scenario_epub_single():
    """EPUB 단일 변환 → Markdown"""
    from convert_epub import convert_epub_to_markdown

    epub_path = input("변환할 EPUB 경로를 입력하세요: ").strip()
    if not epub_path:
        epub_files = sorted(glob.glob("input/*.epub"))
        if not epub_files:
            print("ERROR: input/ 폴더에 EPUB 파일이 없습니다.")
            return
        epub_path = epub_files[0]
        print(f"  → 자동 선택: {epub_path}")

    output_dir = input("출력 폴더 [기본: output]: ").strip() or "output"
    convert_epub_to_markdown(epub_path, output_dir)


def scenario_epub_batch():
    """EPUB 배치 변환 — input/ 폴더의 모든 .epub 파일"""
    from convert_epub import convert_epub_to_markdown

    input_dir = input("입력 폴더 [기본: input]: ").strip() or "input"
    output_dir = input("출력 폴더 [기본: output]: ").strip() or "output"

    epub_files = sorted(glob.glob(os.path.join(input_dir, "*.epub")))
    if not epub_files:
        print(f"ERROR: {input_dir}/ 폴더에 EPUB 파일이 없습니다.")
        return

    print(f"Found {len(epub_files)} EPUB file(s)")
    print("=" * 60)
    successful = 0
    failed = 0
    for i, epub_file in enumerate(epub_files, 1):
        print(f"\n[{i}/{len(epub_files)}] {Path(epub_file).name}")
        try:
            convert_epub_to_markdown(epub_file, output_dir)
            successful += 1
        except Exception as e:
            print(f"  ERROR: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Conversion complete! Successful: {successful}, Failed: {failed}")


def scenario_hwp():
    """HWP / HWPX / HML → Markdown 변환"""
    from convert import convert_file, convert_all, SUPPORTED

    mode = input("모드 — [1] 단일 파일  [2] input/ 폴더 전체: ").strip()
    output_dir = Path(input("출력 폴더 [기본: output]: ").strip() or "output")

    if mode == "1":
        file_path = input(f"파일 경로 ({', '.join(SUPPORTED)}): ").strip()
        if not file_path:
            print("ERROR: 경로가 비어 있습니다.")
            return
        output_dir.mkdir(parents=True, exist_ok=True)
        convert_file(Path(file_path), output_dir)
    else:
        input_dir = Path(input("입력 폴더 [기본: input]: ").strip() or "input")
        convert_all(input_dir, output_dir)


def scenario_html():
    """HTML → Markdown 배치 변환 (input/ 폴더)"""
    from html_to_md import clean_html_to_md

    input_dir  = input("HTML 폴더 [기본: input]: ").strip() or "input"
    output_dir = input("출력 폴더 [기본: output]: ").strip() or "output"
    clean_html_to_md(input_dir, output_dir)


def scenario_extract_images():
    """PDF에서 이미지만 추출 (Markdown 변환 없음)"""
    from extract_images import extract_all_images, extract_images_from_pdf

    mode = input("모드 선택 — [1] 단일 파일  [2] 배치 (input/ 폴더): ").strip()
    output_dir = input("출력 폴더 [기본: output]: ").strip() or "output"

    if mode == "1":
        pdf_path = input("PDF 경로를 입력하세요: ").strip()
        if not pdf_path:
            print("ERROR: 경로가 비어 있습니다.")
            return
        extract_images_from_pdf(pdf_path, output_dir)
    else:
        input_dir = input("입력 폴더 [기본: input]: ").strip() or "input"
        extract_all_images(input_dir, output_dir)


def scenario_merge_markdown():
    """output/ 폴더의 .md 파일들을 하나의 파일로 병합"""
    from merge_markdown import merge_markdown_files

    input_dir = input("병합할 Markdown 폴더 [기본: output]: ").strip() or "output"
    output_file = input("병합 결과 파일명 [기본: merged_all.md]: ").strip() or "merged_all.md"
    separator_choice = input("구분자 — [1] 수평선 (---) [2] 빈줄만: ").strip()
    separator = "\n\n---\n\n" if separator_choice != "2" else "\n\n"
    merge_markdown_files(input_dir, output_file, separator)


def scenario_update_image_paths():
    """Markdown 내 이미지 경로를 추출된 실제 이미지 경로로 업데이트"""
    from update_image_paths import update_all_markdown_files

    output_dir = input("Markdown 폴더 [기본: output]: ").strip() or "output"
    update_all_markdown_files(output_dir)


# ─── 메뉴 ────────────────────────────────────────────────────────────────────

SCENARIOS = [
    ("PDF 단일 변환 (이미지 포함, 고품질)",            scenario_pdf_single_with_images),
    ("PDF 단일 변환 (텍스트 전용, 빠름)",              scenario_pdf_single_fast),
    ("PDF 배치 변환 (이미지 포함, 순차)",              scenario_pdf_batch_with_images),
    ("PDF 배치 변환 (텍스트 전용, 순차, 빠름)",        scenario_pdf_batch_fast),
    ("PDF 배치 변환 (병렬 처리, 멀티코어)",            scenario_pdf_batch_parallel),
    ("EPUB 단일 변환 → Markdown",                     scenario_epub_single),
    ("EPUB 배치 변환 (input/ 폴더 전체)",              scenario_epub_batch),
    ("HWP / HWPX / HML → Markdown (한글 문서)",       scenario_hwp),
    ("HTML → Markdown 배치 변환 (input/ 폴더)",        scenario_html),
    ("이미지만 추출 (PDF → 이미지 파일)",              scenario_extract_images),
    ("Markdown 파일 병합 (여러 .md → 하나로)",         scenario_merge_markdown),
    ("이미지 경로 업데이트 (Markdown 링크 수정)",      scenario_update_image_paths),
]


def print_menu():
    print("\n" + "=" * 60)
    print("  docuConverter — 문서 → Markdown 변환 도구")
    print("=" * 60)
    for i, (label, _) in enumerate(SCENARIOS, 1):
        print(f"  {i:2}. {label}")
    print("   0. 종료")
    print("=" * 60)


def run_interactive():
    """대화형 메뉴 실행"""
    while True:
        print_menu()
        choice = input("시나리오 번호를 선택하세요: ").strip()

        if choice == "0":
            print("종료합니다.")
            break

        if not choice.isdigit() or not (1 <= int(choice) <= len(SCENARIOS)):
            print("잘못된 입력입니다. 다시 선택하세요.")
            continue

        idx = int(choice) - 1
        label, fn = SCENARIOS[idx]
        print(f"\n▶ {label}")
        print("-" * 60)
        try:
            fn()
        except KeyboardInterrupt:
            print("\n중단되었습니다.")
        except Exception as e:
            print(f"\nERROR: {e}")
            import traceback
            traceback.print_exc()

        input("\n[Enter] 키를 누르면 메뉴로 돌아갑니다...")


def run_cli(args):
    """CLI 직접 실행 모드 (비대화형)

    사용 예:
      python main.py 1 path/to/file.pdf output/
      python main.py 4 input/ output/
      python main.py 6 path/to/book.epub output/
    """
    if not args:
        run_interactive()
        return

    scenario_num = args[0]
    if not scenario_num.isdigit() or not (1 <= int(scenario_num) <= len(SCENARIOS)):
        print(f"ERROR: 시나리오 번호는 1~{len(SCENARIOS)} 사이여야 합니다.")
        sys.exit(1)

    idx = int(scenario_num) - 1
    label, fn = SCENARIOS[idx]
    print(f"▶ {label}")

    # 인자를 stdin 처럼 흉내 내어 input() 호출을 우회
    # 직접 함수를 시나리오별로 호출
    extra = args[1:]

    if idx == 0:  # PDF 단일, 이미지 포함
        from convert_with_cropped_images import convert_pdf_with_cropped_images
        pdf_path = extra[0] if len(extra) > 0 else sorted(glob.glob("input/*.pdf"))[0]
        out = extra[1] if len(extra) > 1 else "output"
        convert_pdf_with_cropped_images(pdf_path, out)

    elif idx == 1:  # PDF 단일, fast
        from convert_pdfs_fast import convert_pdf_to_markdown_fast
        pdf_path = extra[0] if len(extra) > 0 else sorted(glob.glob("input/*.pdf"))[0]
        out = extra[1] if len(extra) > 1 else "output"
        convert_pdf_to_markdown_fast(pdf_path, out)

    elif idx == 2:  # PDF 배치, 이미지 포함
        from convert_with_cropped_images import convert_all_pdfs
        inp = extra[0] if len(extra) > 0 else "input"
        out = extra[1] if len(extra) > 1 else "output"
        convert_all_pdfs(inp, out)

    elif idx == 3:  # PDF 배치, fast
        from convert_pdfs_fast import convert_all_pdfs_fast
        inp = extra[0] if len(extra) > 0 else "input"
        out = extra[1] if len(extra) > 1 else "output"
        convert_all_pdfs_fast(inp, out)

    elif idx == 4:  # PDF 배치, 병렬
        from convert_pdfs_parallel import convert_all_pdfs_parallel
        inp = extra[0] if len(extra) > 0 else "input"
        out = extra[1] if len(extra) > 1 else "output"
        workers = int(extra[2]) if len(extra) > 2 else 2
        convert_all_pdfs_parallel(inp, out, workers)

    elif idx == 5:  # EPUB 단일
        from convert_epub import convert_epub_to_markdown
        epub_path = extra[0] if len(extra) > 0 else sorted(glob.glob("input/*.epub"))[0]
        out = extra[1] if len(extra) > 1 else "output"
        convert_epub_to_markdown(epub_path, out)

    elif idx == 6:  # EPUB 배치
        from convert_epub import convert_epub_to_markdown
        inp = extra[0] if len(extra) > 0 else "input"
        out = extra[1] if len(extra) > 1 else "output"
        for ep in sorted(glob.glob(os.path.join(inp, "*.epub"))):
            print(f"\n→ {Path(ep).name}")
            convert_epub_to_markdown(ep, out)

    elif idx == 7:  # HWP/HWPX/HML
        from convert import convert_file, convert_all, SUPPORTED
        if extra:
            out = Path(extra[-1]) if len(extra) > 1 else Path("output")
            out.mkdir(parents=True, exist_ok=True)
            for f in extra[:-1] if len(extra) > 1 else extra:
                convert_file(Path(f), out)
        else:
            convert_all(Path("input"), Path("output"))

    elif idx == 8:  # HTML → MD
        from html_to_md import clean_html_to_md
        inp = extra[0] if len(extra) > 0 else "input"
        out = extra[1] if len(extra) > 1 else "output"
        clean_html_to_md(inp, out)

    elif idx == 9:  # 이미지 추출
        from extract_images import extract_all_images
        inp = extra[0] if len(extra) > 0 else "input"
        out = extra[1] if len(extra) > 1 else "output"
        extract_all_images(inp, out)

    elif idx == 10:  # Markdown 병합
        from merge_markdown import merge_markdown_files
        inp = extra[0] if len(extra) > 0 else "output"
        out_file = extra[1] if len(extra) > 1 else "merged_all.md"
        merge_markdown_files(inp, out_file)

    elif idx == 11:  # 이미지 경로 업데이트
        from update_image_paths import update_all_markdown_files
        out = extra[0] if len(extra) > 0 else "output"
        update_all_markdown_files(out)


if __name__ == "__main__":
    # docuConverter 폴더를 cwd로 설정 (어느 경로에서 실행해도 input/output 경로 일관)
    script_dir = Path(__file__).parent
    os.chdir(script_dir)

    run_cli(sys.argv[1:])
