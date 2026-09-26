#!/usr/bin/env python3
"""
Markdown Preprocessor for Missing Semester (Burmese Version) eBook Generator.
Processes Jekyll lecture markdowns, generates QR codes, video cards, link references,
and appends a compact External Links Appendix Table with Micro QR codes at the end of each session.
"""

import os
import re
import sys
import glob
import hashlib
import subprocess
import urllib.request

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EBOOK_DIR = os.path.join(REPO_ROOT, "ebook")
BUILD_DIR = os.path.join(EBOOK_DIR, "build")
ASSETS_DIR = os.path.join(EBOOK_DIR, "assets")
QR_DIR = os.path.join(ASSETS_DIR, "qrcodes")
THUMB_DIR = os.path.join(ASSETS_DIR, "thumbnails")
TEMPLATES_DIR = os.path.join(EBOOK_DIR, "templates")

os.makedirs(BUILD_DIR, exist_ok=True)
os.makedirs(QR_DIR, exist_ok=True)
os.makedirs(THUMB_DIR, exist_ok=True)


def parse_simple_frontmatter(yaml_text):
    """Simple zero-dependency frontmatter parser."""
    data = {}
    lines = yaml_text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
            
        if ":" in line and not line.startswith(" ") and not line.startswith("\t"):
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip()
            
            if val == ">" or val == "|":
                multiline = []
                i += 1
                while i < len(lines) and (lines[i].startswith(" ") or lines[i].startswith("\t")):
                    multiline.append(lines[i].strip())
                    i += 1
                data[key] = " ".join(multiline)
                continue
            elif not val:
                sub_dict = {}
                i += 1
                while i < len(lines) and (lines[i].startswith(" ") or lines[i].startswith("\t")):
                    if ":" in lines[i]:
                        sk, sv = lines[i].split(":", 1)
                        sub_dict[sk.strip()] = sv.strip().strip('"\'')
                    i += 1
                data[key] = sub_dict
                continue
            else:
                data[key] = val.strip('"\'')
        i += 1
    return data

def generate_qr_code(url, filename_prefix="qr", micro=False):
    """Generate PNG QR Code for a given URL using qrencode."""
    safe_prefix = re.sub(r'[^a-zA-Z0-9_-]', '_', filename_prefix)
    safe_name = f"{safe_prefix}_micro.png" if micro else f"{safe_prefix}.png"
    out_path = os.path.join(QR_DIR, safe_name)
    rel_path = os.path.relpath(out_path, REPO_ROOT)
    
    if os.path.exists(out_path):
        return out_path, rel_path

    size = "3" if micro else "6"
    margin = "1" if micro else "2"
    
    try:
        subprocess.run(
            ["qrencode", "-o", out_path, "-s", size, "-m", margin, url],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    except Exception as e:
        print(f"Warning: Failed to generate QR for {url} using qrencode: {e}")
        from PIL import Image, ImageDraw
        dim = 80 if micro else 150
        img = Image.new('RGB', (dim, dim), color='white')
        d = ImageDraw.Draw(img)
        d.rectangle([5, 5, dim-5, dim-5], outline='black', width=2)
        d.text((15, dim//2 - 10), "QR", fill='black')
        img.save(out_path)
        
    return out_path, rel_path

def fetch_youtube_thumbnail(video_id):
    """Download YouTube video thumbnail image in original 16:9 aspect ratio."""
    thumb_name = f"yt_{video_id}.jpg"
    out_path = os.path.join(THUMB_DIR, thumb_name)
    rel_path = os.path.relpath(out_path, REPO_ROOT)
    
    if os.path.exists(out_path):
        return out_path, rel_path

    # Try 16:9 maxresdefault first, fallback to sddefault/hqdefault
    qualities = ["maxresdefault.jpg", "sddefault.jpg", "hqdefault.jpg"]
    for q in qualities:
        url = f"https://img.youtube.com/vi/{video_id}/{q}"
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as resp:
                data = resp.read()
                # Filter out YouTube 404 error placeholder images (< 2KB)
                if len(data) > 3000:
                    with open(out_path, 'wb') as f:
                        f.write(data)
                    return out_path, rel_path
        except Exception:
            continue

    print(f"Warning: Could not download 16:9 thumbnail for {video_id}, generating fallback...")
    from PIL import Image, ImageDraw
    img = Image.new('RGB', (640, 360), color='#1e293b') # 16:9 ratio
    d = ImageDraw.Draw(img)
    d.polygon([(290, 140), (290, 220), (360, 180)], fill='#ef4444')
    img.save(out_path)
        
    return out_path, rel_path


def load_video_card_template():
    card_tmpl_path = os.path.join(TEMPLATES_DIR, "video_card.html")
    if os.path.exists(card_tmpl_path):
        with open(card_tmpl_path, "r", encoding="utf-8") as f:
            return f.read()
    return ""

def rewrite_internal_links(text):
    """Rewrite relative site links starting with / (e.g. /2020/, /about/) to live https:// URLs."""
    def rel_link_sub(match):
        label = match.group(1)
        path = match.group(2)
        if path.startswith("/static/") or re.match(r'^/[0-9]{4}/files/', path):
            return match.group(0)  # Preserve static file assets for local file:// rewriting
        full_url = f"https://missing-semester-my.github.io{path}"
        return f"[{label}]({full_url})"

    return re.sub(r'\[([^\]]+)\]\((/[^\)]*)\)', rel_link_sub, text)

def process_lecture_markdown(file_path):
    """Parse single lecture markdown file and transform for eBook."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    frontmatter = {}
    body = content
    
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parse_simple_frontmatter(parts[1])
            body = parts[2]
            
    title = frontmatter.get("title", os.path.basename(file_path))
    date = frontmatter.get("date", "")
    desc = frontmatter.get("description", "").strip()
    video_data = frontmatter.get("video", {})
    video_id = video_data.get("id") if isinstance(video_data, dict) else None
    panopto_url = frontmatter.get("panopto", "")
    
    output_sections = []
    
    # Lecture Title Heading
    output_sections.append(f"# {title}\n")
    if desc:
        output_sections.append(f"> **အနှစ်ချုပ်** - {desc}\n")
        
    # Video Card generation
    video_url = ""
    if video_id:
        video_url = f"https://www.youtube.com/watch?v={video_id}"
    elif panopto_url:
        video_url = panopto_url
        
    if video_url:
        yt_id = video_id or "panopto"
        thumb_path, _ = fetch_youtube_thumbnail(yt_id)
        qr_path, _ = generate_qr_code(video_url, f"yt_{yt_id}")
        
        # Absolute file:// scheme URLs so Pandoc and Chromium load images flawlessly
        thumb_abs_url = f"file://{os.path.abspath(thumb_path)}"
        qr_abs_url = f"file://{os.path.abspath(qr_path)}"
        
        card_tmpl = load_video_card_template()
        if card_tmpl:
            card_html = card_tmpl.format(
                title=title,
                video_url=video_url,
                thumbnail_rel_path=thumb_abs_url,
                qr_rel_path=qr_abs_url
            )
            output_sections.append(f"\n```{{=html}}\n{card_html}\n```\n")

    # Clean body content
    # 0. Convert 4-space indented code blocks to fenced blocks
    def normalize_code_blocks(text):
        lines = text.splitlines()
        in_fenced = False
        in_indented = False
        res = []
        for l in lines:
            stripped = l.strip()
            if stripped.startswith("```"):
                if in_fenced:
                    in_fenced = False
                else:
                    in_fenced = True
                    if in_indented:
                        res.append("```")
                        in_indented = False
                res.append(l)
                continue
                
            if in_fenced:
                res.append(l)
                continue

            if (l.startswith("    ") or l.startswith("\t")) and stripped:
                if not in_indented:
                    res.append("```bash")
                    in_indented = True
                res.append(l[4:] if l.startswith("    ") else l[1:])
            elif in_indented and not stripped:
                res.append("")
            else:
                if in_indented:
                    res.append("```")
                    in_indented = False
                res.append(l)
        if in_indented:
            res.append("```")
        return "\n".join(res)

    body_clean = normalize_code_blocks(body)

    # 1. Remove Liquid {% comment %} ... {% endcomment %} blocks
    body_clean = re.sub(r'\{%\s*comment\s*%\}[\s\S]*?\{%\s*endcomment\s*%\}', '', body_clean, flags=re.DOTALL)
    
    # 2. Remove Jekyll Liquid tags like {% ... %} or {{ ... }}
    body_clean = re.sub(r'\{%.*?%\}', '', body_clean)
    body_clean = re.sub(r'\{\{.*?\}\}', '', body_clean)
    
    # 3. Clean GitHub Action status badges (SVG) to prevent broken missing image icons
    body_clean = re.sub(
        r'\[\!\[([^\]]+)\]\([^)]*badge\.svg[^)]*\)\]\([^)]+\)',
        r'<span class="status-badge-pill">\1</span>',
        body_clean
    )
    body_clean = re.sub(
        r'\!\[([^\]]+)\]\([^)]*badge\.svg[^)]*\)',
        r'<span class="status-badge-pill">\1</span>',
        body_clean
    )
    
    # 4. Rewrite internal web links and static image paths
    body_clean = rewrite_internal_links(body_clean)
    static_abs = os.path.join(REPO_ROOT, "static")
    body_clean = re.sub(r'\]\(/static/', f'](file://{static_abs}/', body_clean)
    body_clean = re.sub(r'src="/static/', f'src="file://{static_abs}/', body_clean)
    body_clean = re.sub(r'\]\(/([0-9]{4})/files/', f'](file://{REPO_ROOT}/_\\1/files/', body_clean)
    body_clean = re.sub(r'src="/([0-9]{4})/files/', f'src="file://{REPO_ROOT}/_\\1/files/', body_clean)

    
    # 5. Extract external links for session appendix table
    raw_links = re.findall(r'\[([^\]]+)\]\((https?://[^\)]+)\)', body_clean)
    unique_links = []
    seen_urls = set()
    
    for link_text, link_url in raw_links:
        # Ignore video link if already in header card or internal anchors
        if link_url not in seen_urls and not link_url.startswith("mailto:"):
            seen_urls.add(link_url)
            clean_label = link_text.strip()
            unique_links.append((clean_label, link_url))

    # 6. Format links in prose with subtle footnote style
    def link_replacer(match):
        text = match.group(1)
        url = match.group(2)
        if url.startswith("http://") or url.startswith("https://"):
            return f'<a href="{url}" class="ext-link">{text}</a> <span class="ext-url-print">({url})</span>'
        return match.group(0)

    body_clean = re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', link_replacer, body_clean)
    output_sections.append(body_clean)
    
    # 7. Append Session External Links Appendix Table
    if unique_links:
        table_rows = []
        for idx, (label, url) in enumerate(unique_links, start=1):
            url_hash = hashlib.md5(url.encode('utf-8')).hexdigest()[:8]
            micro_qr_path, _ = generate_qr_code(url, f"link_{url_hash}", micro=True)
            micro_qr_abs_url = f"file://{os.path.abspath(micro_qr_path)}"
            
            table_rows.append(f"""<tr>
  <td class="col-label"><strong>{idx}. {label}</strong></td>
  <td class="col-url"><a href="{url}" class="appendix-link">{url}</a></td>
  <td class="col-qr"><img src="{micro_qr_abs_url}" alt="QR" class="micro-qr" /></td>
</tr>""")

            
        appendix_html = f"""<div class="lecture-links-appendix">
  <h4 class="links-appendix-title">🔗 External Links & References (ပြင်ပ လင့်ခ်များနှင့် ကိုးကားချက်များ)</h4>
  <table class="links-table">
    <thead>
      <tr>
        <th style="width: 30%;">Resource / Description</th>
        <th style="width: 56%;">URL</th>
        <th style="width: 14%; text-align: center;">Micro QR</th>
      </tr>
    </thead>
    <tbody>
      {"".join(table_rows)}
    </tbody>
  </table>
</div>"""

        output_sections.append(f"\n```{{=html}}\n{appendix_html}\n```\n")


    return "\n".join(output_sections)

def process_root_page(file_path, year="2026"):
    """Parse top-level site markdown (index.md, about.md, past.md, license.md) for eBook inclusion."""
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    frontmatter = {}
    body = content
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            frontmatter = parse_simple_frontmatter(parts[1])
            body = parts[2]

    title = frontmatter.get("title", os.path.basename(file_path))
    filename = os.path.basename(file_path)

    # 1. Expand Liquid loops in index.md
    if filename == "index.md":
        year_dir = os.path.join(REPO_ROOT, f"_{year}")
        lecture_files = sorted(glob.glob(os.path.join(year_dir, "*.md")))
        lecture_items = []
        for lpath in lecture_files:
            lf_title = ""
            with open(lpath, "r", encoding="utf-8") as lf:
                lcontent = lf.read()
                if lcontent.startswith("---"):
                    lparts = lcontent.split("---", 2)
                    if len(lparts) >= 3:
                        lfm = parse_simple_frontmatter(lparts[1])
                        lf_title = lfm.get("title", "")
            if not lf_title:
                lf_title = os.path.basename(lpath).replace(".md", "").replace("-", " ").title()
            lecture_items.append(f"- **{lf_title}**")
        
        body = re.sub(r'<ul>\s*\{%\s*assign\s+lectures[\s\S]*?</ul>', "\n".join(lecture_items), body)

        # Special topics list for index.md
        special_items = []
        for prev_year in ["2020", "2019"]:
            p_dir = os.path.join(REPO_ROOT, f"_{prev_year}")
            if os.path.exists(p_dir):
                for pf in sorted(glob.glob(os.path.join(p_dir, "*.md"))):
                    with open(pf, "r", encoding="utf-8") as pfile:
                        pcontent = pfile.read()
                        if "special: true" in pcontent:
                            p_title = ""
                            if pcontent.startswith("---"):
                                pparts = pcontent.split("---", 2)
                                if len(pparts) >= 3:
                                    pfm = parse_simple_frontmatter(pparts[1])
                                    p_title = pfm.get("title", "")
                            if not p_title:
                                p_title = os.path.basename(pf).replace(".md", "").title()
        special_md = "\n".join(special_items) if special_items else "- *No special topics listed.*"
        body = re.sub(r'<ul>\s*\{%\s*for\s+collection\s+in\s+sorted_collections[\s\S]*?</ul>', special_md, body)
        body = re.sub(r'<ul>\s*\{%\s*assign\s+sorted_collections[\s\S]*?</ul>', special_md, body)

    elif filename == "past.md":
        past_md = """
- **2026 Edition (၂၀၂၆ သင်တန်းများ)** — [https://missing-semester-my.github.io/2026/](https://missing-semester-my.github.io/2026/)
- **2020 Edition (၂၀၂၀ သင်တန်းများ)** — [https://missing-semester-my.github.io/2020/](https://missing-semester-my.github.io/2020/)
- **2019 Edition (၂၀၁၉ သင်တန်းများ)** — [https://missing-semester-my.github.io/2019/](https://missing-semester-my.github.io/2019/)
"""
        body = re.sub(r'<ul>\s*\{%\s*for\s+collection[\s\S]*?</ul>', past_md, body)
        body = re.sub(r'\{%\s*comment\s*%\}[\s\S]*?\{%\s*endcomment\s*%\}', '', body)

    elif filename == "about.md":
        def replace_video_card(match):
            src = match.group(1)
            filename = os.path.basename(src)
            title_name = os.path.splitext(filename)[0].replace("-", " ").replace("_", " ").title()
            url = f"https://missing-semester-my.github.io/static/media/demos/{filename}"
            qr_path, _ = generate_qr_code(url, f"demo_{os.path.splitext(filename)[0]}")
            qr_abs_url = f"file://{os.path.abspath(qr_path)}"
            return f"""
```{{=html}}
<div class="video-demo-box">
  <div class="video-demo-qr-col">
    <img src="{qr_abs_url}" alt="QR Demo" class="video-demo-qr-img" />
  </div>
  <div class="video-demo-info-col">
    <div class="video-demo-header">📹 <strong>Video Demo ({title_name})</strong></div>
    <div class="video-demo-subtext">Scan QR code or visit link to watch demo:</div>
    <div class="video-demo-link"><a href="{url}" class="ext-link">{url}</a></div>
  </div>
</div>
```
"""
        body = re.sub(
            r'<video[\s\S]*?<source\s+src=["\']([^"\']+)["\'][\s\S]*?</video>',
            replace_video_card,
            body
        )

    # Clean remaining liquid tags
    body_clean = re.sub(r'\{%\s*comment\s*%\}[\s\S]*?\{%\s*endcomment\s*%\}', '', body, flags=re.DOTALL)
    body_clean = re.sub(r'\{%.*?%\}', '', body_clean)
    body_clean = re.sub(r'\{\{.*?\}\}', '', body_clean)

    # Rewrite relative site links starting with /
    body_clean = rewrite_internal_links(body_clean)

    # Static image/media path rewriting
    static_abs = os.path.join(REPO_ROOT, "static")
    body_clean = re.sub(r'\]\(/static/', f'](file://{static_abs}/', body_clean)
    body_clean = re.sub(r'src="/static/', f'src="file://{static_abs}/', body_clean)

    # For root intro/outro pages, tag internal headings with {.unnumbered .unlisted}
    # so they render in text but do not pollute the Table of Contents (TOC)
    def add_unlisted_to_headers(text):
        lines = text.splitlines()
        in_code_block = False
        res_lines = []
        for line in lines:
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                res_lines.append(line)
                continue
            if not in_code_block:
                m = re.match(r'^(#{1,6})\s+(.+)$', line)
                if m:
                    hashes = m.group(1)
                    htitle = m.group(2).strip()
                    if "{." not in htitle:
                        line = f"{hashes} {htitle} {{.unnumbered .unlisted}}"
            res_lines.append(line)
        return "\n".join(res_lines)

    body_clean = add_unlisted_to_headers(body_clean)

    # Give root pages clean, distinct top-level titles for the TOC
    if filename == "index.md":
        root_heading = "# သင်တန်း မိတ်ဆက် (Introduction) {.unnumbered}\n"
    elif filename == "about.md":
        root_heading = "## ဤသင်တန်းကို သင်ကြားပေးရသည့် ရည်ရွယ်ချက် (Course Motivation) {.unnumbered .unlisted}\n"
    elif filename == "license.md":
        root_heading = "# လိုင်စင်နှင့် မူပိုင်ခွင့် (License) {.unnumbered}\n"
    else:
        root_heading = f"# {title} {{.unnumbered}}\n"

    output = []
    output.append(root_heading)
    output.append(body_clean)
    return "\n".join(output)


def compile_year_ebook(year="2026"):
    """Compile root site pages and lecture files of a year into a single combined Markdown document."""
    year_dir = os.path.join(REPO_ROOT, f"_{year}")
    if not os.path.exists(year_dir):
        print(f"Error: Year directory {year_dir} does not exist.")
        sys.exit(1)
        
    all_files = sorted(glob.glob(os.path.join(year_dir, "*.md")))
    # Exclude the web collection index page (_year/index.md) to avoid duplicate TOC entries
    md_files = [f for f in all_files if os.path.basename(f) != "index.md"]
    
    def sort_key(filepath):
        name = os.path.basename(filepath)
        if name in ("index.md", "course-overview.md"):
            return "00_" + name
        return "10_" + name
        
    md_files.sort(key=sort_key)
    
    print(f"Found {len(md_files)} lecture files in _{year}:")
    for f in md_files:
        print(f" - {os.path.basename(f)}")
        
    combined_md = []
    
    # Title & Metadata Header
    combined_md.append(f"""---
title: "The Missing Semester of Your CS Education ({year}) - Burmese"
subtitle: "{year} Edition"
author: "MIT CSIL • FOSS Myanmar and Vibe Code Tours"
language: "my"
rights: "CC BY-NC-SA 4.0"
---
""")

    # 1. Process Root Intro Site Pages (index.md + about.md) merged under Introduction section
    combined_md.append("\n\\pagebreak\n")
    root_intro_files = ["index.md", "about.md"]
    for root_name in root_intro_files:
        rpath = os.path.join(REPO_ROOT, root_name)
        if os.path.exists(rpath):
            print(f"Processing root site page {root_name}...")
            processed_root = process_root_page(rpath, year)
            combined_md.append(processed_root)
            combined_md.append("\n\n")
    combined_md.append("\n\\pagebreak\n")

    # 2. Process Year Lecture Files
    for fpath in md_files:
        print(f"Processing lecture {os.path.basename(fpath)}...")
        processed_text = process_lecture_markdown(fpath)
        combined_md.append(processed_text)
        combined_md.append("\n\\pagebreak\n")

    # 3. Process Root Outro Site Pages (license.md)
    root_outro_files = ["license.md"]
    for root_name in root_outro_files:
        rpath = os.path.join(REPO_ROOT, root_name)
        if os.path.exists(rpath):
            print(f"Processing root site page {root_name}...")
            processed_root = process_root_page(rpath, year)
            combined_md.append(processed_root)
            combined_md.append("\n\\pagebreak\n")

        combined_md.append("\n\\pagebreak\n")
        
    # Append Back Page HTML Block for PDF/EPUB
    site_qr_path, _ = generate_qr_code("https://missing-semester-my.github.io/", "burmese_site_qr")
    site_qr_abs_url = f"file://{os.path.abspath(site_qr_path)}"
    back_tmpl_path = os.path.join(TEMPLATES_DIR, "back_page.html")
    if os.path.exists(back_tmpl_path):
        with open(back_tmpl_path, "r", encoding="utf-8") as f:
            back_tmpl = f.read()
        back_html = back_tmpl.format(year=year, qr_img_url=site_qr_abs_url)
        combined_md.append(f"\n```{{=html}}\n{back_html}\n```\n")


    out_combined_path = os.path.join(EBOOK_DIR, "build", f"combined_{year}.md")
    os.makedirs(os.path.dirname(out_combined_path), exist_ok=True)
    with open(out_combined_path, "w", encoding="utf-8") as f:
        f.write("\n".join(combined_md))


        
    print(f"Compiled combined markdown at: {out_combined_path}")
    return out_combined_path

if __name__ == "__main__":
    year_arg = sys.argv[1] if len(sys.argv) > 1 else "2026"
    compile_year_ebook(year_arg)
