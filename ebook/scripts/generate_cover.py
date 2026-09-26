#!/usr/bin/env python3
"""
Generate high-resolution cover image for The Missing Semester of Your CS Education (Burmese) eBook.
"""

import os
from PIL import Image, ImageDraw, ImageFont

def get_font(font_path, size):
    try:
        return ImageFont.truetype(font_path, size, layout_engine=ImageFont.Layout.RAQM)
    except Exception:
        try:
            return ImageFont.truetype(font_path, size)
        except Exception:
            return ImageFont.load_default()

def generate_cover():
    width = 1600
    height = 2400
    
    img = Image.new('RGB', (width, height), color='#0f172a')
    draw = ImageDraw.Draw(img)
    
    # Accent borders
    draw.rectangle([0, 0, width, 40], fill='#38bdf8')
    draw.rectangle([0, height-40, width, height], fill='#38bdf8')
    draw.rectangle([60, 60, width-60, height-60], outline='#334155', width=4)
    
    # Try Padauk font for Burmese / English, or DejaVuSans
    padauk_bold = "/usr/share/fonts/truetype/padauk/Padauk-Bold.ttf"
    padauk_reg = "/usr/share/fonts/truetype/padauk/Padauk-Regular.ttf"
    dejavu_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    
    title_font = get_font(dejavu_bold if os.path.exists(dejavu_bold) else padauk_bold, 85)
    subtitle_font = get_font(dejavu_bold if os.path.exists(dejavu_bold) else padauk_bold, 60)
    burmese_font = get_font(padauk_bold, 50)
    code_font = get_font(dejavu_bold if os.path.exists(dejavu_bold) else padauk_reg, 45)
    
    # Graphic terminal box (positioned BEFORE title with doubled top gap)
    draw.rectangle([400, 650, 1200, 1200], fill='#1e293b', outline='#475569', width=4)
    draw.rectangle([400, 650, 1200, 720], fill='#334155')
    draw.ellipse([425, 675, 455, 705], fill='#ef4444')
    draw.ellipse([470, 675, 500, 705], fill='#f59e0b')
    draw.ellipse([515, 675, 545, 705], fill='#10b981')
    
    draw.text((440, 800), "$ missing-semester --lang my", fill="#38bdf8", font=code_font)
    draw.text((440, 900), "> PDF & EPUB Edition", fill="#10b981", font=code_font)
    draw.text((440, 1000), "> MIT 6.MISSING", fill="#94a3b8", font=code_font)

    # Main English Title (positioned after logo)
    draw.text((width // 2, 1380), "THE MISSING SEMESTER", fill="#ffffff", font=title_font, anchor="mm")
    draw.text((width // 2, 1500), "OF YOUR CS EDUCATION", fill="#38bdf8", font=subtitle_font, anchor="mm")
    
    # Simple Burmese badge
    draw.rectangle([550, 1620, 1050, 1710], fill='#1e293b', outline='#38bdf8', width=3)
    draw.text((width // 2, 1665), "Burmese", fill="#f8fafc", font=burmese_font, anchor="mm")
    
    # Footer
    draw.text((width // 2, 2100), "MIT CSIL • FOSS Myanmar and Vibe Code Tours", fill="#94a3b8", font=code_font, anchor="mm")
    
    out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, "cover.png")
    img.save(out_path, "PNG")
    print(f"Cover generated at {out_path}")

if __name__ == "__main__":
    generate_cover()
