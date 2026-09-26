#!/usr/bin/env python3
"""
EBook Build & Orchestration CLI Script for Missing Semester (Burmese Version).
Supports generating both EPUB and PDF editions for 2026, 2020, and 2019 lectures.
"""

import argparse
import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EBOOK_DIR = os.path.join(REPO_ROOT, "ebook")
BUILD_DIR = os.path.join(EBOOK_DIR, "build")
TEMPLATES_DIR = os.path.join(EBOOK_DIR, "templates")
ASSETS_DIR = os.path.join(EBOOK_DIR, "assets")

os.makedirs(BUILD_DIR, exist_ok=True)

def find_chromium():
    for cmd in ["chromium", "google-chrome-stable", "google-chrome", "chromium-browser"]:
        try:
            res = subprocess.run(["which", cmd], capture_output=True, text=True)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except Exception:
            pass
    return "chromium"

def build_year_ebook(year="2026", target_format="all"):
    print(f"\n==================================================")
    print(f"  Building Missing Semester eBook ({year} Edition)")
    print(f"==================================================\n")
    
    # 1. Run Preprocessor
    print(f"[1/3] Preprocessing Burmese markdown for year {year}...")
    preprocessor_script = os.path.join(EBOOK_DIR, "scripts", "preprocess_md.py")
    res = subprocess.run([sys.executable, preprocessor_script, year], cwd=REPO_ROOT)
    if res.returncode != 0:
        print(f"Error: Markdown preprocessing failed for year {year}.")
        return False
        
    combined_md = os.path.join(BUILD_DIR, f"combined_{year}.md")
    cover_png = os.path.join(ASSETS_DIR, "cover.png")
    epub_css = os.path.join(TEMPLATES_DIR, "epub_style.css")
    pdf_css = os.path.join(TEMPLATES_DIR, "pdf_style.css")
    
    # Generate Cover if missing
    if not os.path.exists(cover_png):
        print("Generating cover image...")
        gen_cover_script = os.path.join(EBOOK_DIR, "scripts", "generate_cover.py")
        subprocess.run([sys.executable, gen_cover_script], cwd=REPO_ROOT)

    # 2. Build EPUB
    if target_format in ("epub", "all"):
        epub_out = os.path.join(BUILD_DIR, f"missing-semester-my-{year}.epub")
        print(f"[2/3] Building EPUB: {epub_out}...")
        
        pandoc_cmd = [
            "pandoc", combined_md,
            "-o", epub_out,
            "--css", epub_css,
            "--epub-cover-image", cover_png,
            "--toc",
            "--toc-depth=2",
            "--metadata", f"title=The Missing Semester of Your CS Education ({year}) - Burmese",
            "--metadata", "language=my",
            "--metadata", "author=MIT CSIL • FOSS Myanmar and Vibe Code Tours"
        ]
        
        epub_res = subprocess.run(pandoc_cmd, cwd=REPO_ROOT)
        if epub_res.returncode == 0:
            size_mb = os.path.getsize(epub_out) / (1024 * 1024)
            print(f"✓ EPUB created successfully ({size_mb:.2f} MB): {epub_out}")
        else:
            print(f"✗ Failed to build EPUB.")

    # 3. Build PDF
    if target_format in ("pdf", "all"):
        html_intermediate = os.path.join(BUILD_DIR, f"combined_{year}.html")
        pdf_out = os.path.join(BUILD_DIR, f"missing-semester-my-{year}.pdf")
        pdf_template = os.path.join(TEMPLATES_DIR, "pdf_template.html")
        cover_abs_url = f"file://{os.path.abspath(cover_png)}"
        logo_png = os.path.join(ASSETS_DIR, "logo.png")
        logo_abs_url = f"file://{os.path.abspath(logo_png)}"
        print(f"[3/3] Building PDF: {pdf_out}...")
        
        # Pandoc MD -> HTML using custom pdf_template.html
        pandoc_html_cmd = [
            "pandoc", combined_md,
            "-s",
            "--template", pdf_template,
            "--css", pdf_css,
            "-o", html_intermediate,
            "--toc",
            "--toc-depth=2",
            "--metadata", f"year={year}",
            "--metadata", f"cover_img_url={cover_abs_url}",
            "--metadata", f"logo_img_url={logo_abs_url}",
            "--metadata", f"title=The Missing Semester of Your CS Education ({year}) - Burmese"
        ]


        
        html_res = subprocess.run(pandoc_html_cmd, cwd=REPO_ROOT)
        if html_res.returncode != 0:
            print(f"✗ Failed to convert MD to HTML for PDF build.")
            return False
            
        # Chromium HTML -> PDF
        chrome_bin = find_chromium()
        chrome_cmd = [
            chrome_bin,
            "--headless",
            "--disable-gpu",
            "--no-sandbox",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_out}",
            html_intermediate
        ]

        
        pdf_res = subprocess.run(chrome_cmd, cwd=REPO_ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if pdf_res.returncode == 0 and os.path.exists(pdf_out):
            size_mb = os.path.getsize(pdf_out) / (1024 * 1024)
            print(f"✓ PDF created successfully ({size_mb:.2f} MB): {pdf_out}")
        else:
            print(f"✗ Failed to build PDF.")
            
    # Copy generated artifacts to site static files directory
    static_ebooks_dir = os.path.join(REPO_ROOT, "static", "files", "ebooks")
    os.makedirs(static_ebooks_dir, exist_ok=True)
    for ext in ["pdf", "epub"]:
        src_file = os.path.join(BUILD_DIR, f"missing-semester-my-{year}.{ext}")
        if os.path.exists(src_file):
            import shutil
            dst_file = os.path.join(static_ebooks_dir, f"missing-semester-my-{year}.{ext}")
            shutil.copy2(src_file, dst_file)
            print(f"  -> Published to site static files: {dst_file}")

    return True

def main():
    parser = argparse.ArgumentParser(description="Missing Semester Burmese eBook Builder")
    parser.add_argument("--year", default="2026", choices=["2026", "2020", "2019", "all"], help="Year collection to build")
    parser.add_argument("--format", default="all", choices=["pdf", "epub", "all"], help="Output format")
    args = parser.parse_args()
    
    years_to_build = ["2026", "2020", "2019"] if args.year == "all" else [args.year]
    
    for y in years_to_build:
        build_year_ebook(y, args.format)
        
    print("\neBook Build Process Completed Successfully!\n")

if __name__ == "__main__":
    main()
