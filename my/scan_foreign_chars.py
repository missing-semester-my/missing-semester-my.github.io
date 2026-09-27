import os
import re

def is_foreign_char(c):
    # Check if character is outside English, Myanmar, punctuation, and common symbols/emojis
    code = ord(c)
    
    # Allow Basic Latin and Latin-1
    if code <= 0x00FF: return False
    
    # Allow Myanmar blocks
    if 0x1000 <= code <= 0x109F: return False
    if 0xAA60 <= code <= 0xAA7F: return False
    if 0xA9E0 <= code <= 0xA9FF: return False
    
    # Allow General Punctuation and common math/symbols
    if 0x2000 <= code <= 0x206F: return False
    if 0x2070 <= code <= 0x21FF: return False
    if 0x2200 <= code <= 0x22FF: return False
    if 0x2500 <= code <= 0x257F: return False # Box drawing
    
    # Allow Emojis and Miscellaneous Symbols
    if 0x2600 <= code <= 0x27BF: return False
    if 0x1F300 <= code <= 0x1F9FF: return False
    if 0x1F000 <= code <= 0x1F02F: return False
    if 0x1F0A0 <= code <= 0x1F0FF: return False
    if 0x2B00 <= code <= 0x2BFF: return False # Misc symbols and arrows
    if 0x2300 <= code <= 0x23FF: return False # Misc technical
    
    return True

def scan_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    findings = []
    for line_num, line in enumerate(lines, 1):
        for c in line:
            if is_foreign_char(c):
                findings.append((line_num, c, line.strip()))
                break # Only record the line once
                
    return findings

directories = ['_2019', '_2020', '_2026', '.']
found_files = []

for d in directories:
    if not os.path.isdir(d): continue
    for filename in os.listdir(d):
        if filename.endswith('.md'):
            filepath = os.path.join(d, filename)
            if not os.path.isfile(filepath): continue
            
            res = scan_file(filepath)
            if res:
                found_files.append((filepath, res))

for filepath, findings in found_files:
    print(f"File: {filepath}")
    for line_num, char, line in findings:
        print(f"  Line {line_num} [Char: {char} (U+{ord(char):04X})]: {line[:100]}")
    print()

