# Myanmar Translation Guide

## Translation rules

- **Naming Rule**: Use **`Myanmar`** when referencing the translation in site lists, links, or documentation. Do **NOT** use `"မြန်မာ"` or `"Burmese (မြန်မာဘာသာ)"` — just use **`Myanmar`**.
- Translate explanatory prose into natural, clear Burmese text.
- Line wrapping: Do not hard-wrap Burmese text at 80 characters like the English source. Keep sentences/paragraphs as complete logical lines to prevent awkward breaks in Burmese text rendering.
- **Technical Terminology Principle**: If a technical term or CS concept is not 100% natural, clear, or common in Burmese prose, **use the original English word directly** in Latin script (e.g., `Developer`, `OS`, `Programmer`, `Software`, `Server`, `Client`, `Database`, `Command`, `Terminal`, `Debugger`, `Repository`, `Package`).
  - Keep "Developer" / "Developers" as original English (`Developer` / `Developers`, NEVER `"ဒေဗလော့ပါ"`).
  - Keep "Operating Systems" as original English abbreviation (`OS` / `OS များ`, NEVER `"အိုပါရဲတန်းစနစ်များ"`).
  - Keep "Documentation" / "Docs" / "Document" as original English (`Documentation` / `Docs` / `Document`, NEVER `"စာရွက်စာတမ်း"` in software/tech context).
  - Keep "tool" / "tools" as original English (`tool` / `tools`, NEVER `"ကိရိယာ"` or `"ကိရိယာများ"`).
  - Keep "toolbox" as original English (`toolbox`, NEVER `"ကိရိယာအိတ်"`).
  - Keep "interface" / "user interface" as original English or `"interface (မျက်နှာပြင်)"` (NEVER `"အතුරුအပြင်"`).
  - Keep "bug" / "bugs" as original English (`bug` / `bugs` or `"bug (အမှား)"`, NEVER translate literally as `"ပိုးကောင်"`).
  - Standardize "Code" / "code": Use **`Code`** or **`ကုဒ်`** (NEVER `"ကုတ်"`, `"ကုတ်ဒ်"`, or `"ကိုဒ်"`).
  - Keep Course Title in English: Use **`The Missing Semester of Your CS Education`** (or **`Missing Semester`**) + **`(Burmese)`** / **`(မြန်မာဘာသာ)`**. NEVER translate the title as `"ကွန်ပျူတာသိပ္ပံ သင်ယူသူများအတွက် လိုအပ်နေသော သင်ခန်းစာများ"`, `"သင်၏ CS ပညာရေး၌ လိုအပ်နေသော သင်ရိုး"`, or similar translated titles.

  - Translate "independent lectures" as `"သီးခြားစီ လေ့လာနိုင်သော ခေါင်းစဉ်များ"` (NEVER `"ကင်းလွတ်"`).

  - Avoid phonetic transliterations in Burmese script when the original English word is clearer to readers.
- Keep code blocks, inline code, commands, flags, paths, URLs, Markdown links, HTML, and Liquid/Jekyll tags unchanged.
- Translate the surrounding sentence; do not leave whole explanations in English just because they discuss technical topics.
- Preserve Markdown structure, including headings, lists, emphasis, tables, and paragraph breaks.
- Do not add translator commentary inside lecture content. Record uncertainties in a separate review note.

## Current script behavior

`translate_missing_semester.py` currently protects fenced code, inline code, link URLs, Liquid tags, and HTML tags. Its default front matter key is `title`, so titles are currently translated unless the caller overrides it. To keep titles in English for now, invoke it with an empty key list only if the CLI supports that safely; otherwise change the script's default `--frontmatter-keys` to an empty list before running.

The script does not explicitly protect Markdown tables, reference-style link definitions, or every possible block format. Review those structures in a small sample before translating a full year, and expand the protection logic if the sample shows formatting damage.

## Review checklist

1. Confirm front matter values other than title (such as `layout`, `date`, `ready`, and video URLs) are unchanged.
2. Compare code blocks, inline code, commands, links, tables, and Markdown structure with the English source.
3. Check that prose reads naturally in Burmese and that technical terms are consistent.
4. Keep a separate list of uncertain phrases for a Burmese-speaking reviewer.
5. Label machine-translated content and invite corrections before publication.
