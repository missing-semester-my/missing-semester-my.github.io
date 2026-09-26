#!/usr/bin/env python3
"""
translate_missing_semester.py

Translate MIT Missing Semester (github.com/missing-semester/missing-semester)
lecture markdown into another language using the Gemini API — the same kind
of effort behind the existing kr/jp/th community translations, but automated
and run entirely on your own machine.

WHY A LOCAL SCRIPT INSTEAD OF AN MCP SERVER
This is a one-shot batch job (translate N files, review, commit), not a
tool Claude needs to call repeatedly across conversations — so a plain
script you run, diff, and re-run is simpler and more transparent than
standing up an MCP server for it. You get a normal git diff to review
before opening a PR to your own fork.

WHAT IT DOES
  - Walks the lecture content directories (_2019, _2020, _2026, ... — pass
    whichever exist in your checkout) of a local clone of the repo.
  - For each .md file:
      * Parses Jekyll front matter (--- ... ---) and translates only the
        human-facing keys you name (default: "title"); layout/date/ready
        etc. are left untouched.
      * Protects fenced code blocks, inline code, and URLs inside
        [text](url) links with placeholder tokens before sending text to
        Gemini, then restores them verbatim afterwards — so shell commands,
        flags, and links are never mangled by the model.
      * Sends the remaining prose to Gemini with instructions to translate
        naturally into the target language while preserving code and
        established technical terms in English where that helps learners.
      * Writes the translated file to an output tree that mirrors the
        input, so you can drop it into your own fork alongside the other
        language forks and wire it up in Jekyll.
  - Tracks progress in a JSON file so you can stop and resume, and skips
    files whose source content hasn't changed since the last successful
    translation (content-hash keyed).

SETUP
    pip install google-genai pyyaml
    export GEMINI_API_KEY=your-key-here      # from https://aistudio.google.com/apikey

USAGE
    # dry run on a couple of files to sanity-check output before spending quota
    python translate_missing_semester.py \\
        --repo .. --years _2020 --limit 2 --dry-run

    # full run, Burmese, resumable
    python translate_missing_semester.py \\
        --repo .. --years _2019 _2020 _2026 \\
        --lang-code my --lang-name "Burmese (Myanmar)" \\
        --out ../missing-semester-my

    # re-run later after upstream changes: unchanged files are skipped,
    # new/edited ones are (re)translated
    python translate_missing_semester.py --repo .. --years _2020 --out ../missing-semester-my

NOTES
  - Model default is gemini-3.8-flash. Pass --model to override. Check
    https://ai.google.dev/gemini-api/docs/models if the default 404s.
  - This translates prose. It does NOT set up the Jekyll fork itself
    (front matter collections, _config.yml, nav links) — see the README
    written alongside this script for that part, following the pattern
    used by missing-semester-kr / -jp.
  - Review translated output before publishing. Flag machine-translation
    provenance in your fork's README, as the upstream license/translation
    notes ask (see missing.csail.mit.edu/license).
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("Missing dependency: pip install pyyaml")

try:
    from google import genai
except ImportError:
    sys.exit("Missing dependency: pip install google-genai")


# --------------------------------------------------------------------------
# Protect/restore: never let the model touch code, inline code, or URLs
# --------------------------------------------------------------------------

FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
LINK_URL_RE = re.compile(r"(\[[^\]]*\]\()([^)\s]+)(\s+\"[^\"]*\")?(\))")
LIQUID_RE = re.compile(r"\{%.*?%\}|\{\{.*?\}\}", re.DOTALL)
HTML_TAG_RE = re.compile(r"<[^>]+>")


class Protector:
    """Replace fragile substrings with tokens, translate the rest, restore."""

    def __init__(self):
        self._store = {}
        self._n = 0

    def _stash(self, text: str) -> str:
        token = f"\u0001PROT{self._n}\u0001"
        self._store[token] = text
        self._n += 1
        return token

    def protect(self, text: str) -> str:
        text = FENCE_RE.sub(lambda m: self._stash(m.group(0)), text)
        text = LIQUID_RE.sub(lambda m: self._stash(m.group(0)), text)
        text = HTML_TAG_RE.sub(lambda m: self._stash(m.group(0)), text)
        text = INLINE_CODE_RE.sub(lambda m: self._stash(m.group(0)), text)

        def _link(m):
            return m.group(1) + self._stash(m.group(2)) + (m.group(3) or "") + m.group(4)

        text = LINK_URL_RE.sub(_link, text)
        return text

    def restore(self, text: str) -> str:
        # tokens may be nested in restore order (innermost stashed last),
        # so keep substituting until nothing changes.
        changed = True
        while changed:
            changed = False
            for token, original in self._store.items():
                if token in text:
                    text = text.replace(token, original)
                    changed = True
        return text


# --------------------------------------------------------------------------
# Front matter
# --------------------------------------------------------------------------

FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?\n)---\s*\n?", re.DOTALL)


def split_frontmatter(raw: str):
    m = FRONTMATTER_RE.match(raw)
    if not m:
        return None, raw
    fm_text = m.group(1)
    body = raw[m.end():]
    try:
        fm = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        return None, raw
    return fm, body


def render_frontmatter(fm: dict) -> str:
    dumped = yaml.safe_dump(fm, allow_unicode=True, sort_keys=False, default_flow_style=False)
    return f"---\n{dumped}---\n"


# --------------------------------------------------------------------------
# Chunking — keep requests reasonably sized without splitting protected tokens
# --------------------------------------------------------------------------

def chunk_body(body: str, max_chars: int):
    paras = body.split("\n\n")
    chunks, current = [], []
    size = 0
    for p in paras:
        if size + len(p) > max_chars and current:
            chunks.append("\n\n".join(current))
            current, size = [], 0
        current.append(p)
        size += len(p) + 2
    if current:
        chunks.append("\n\n".join(current))
    return chunks


# --------------------------------------------------------------------------
# Gemini translation
# --------------------------------------------------------------------------

SYSTEM_INSTRUCTION_TEMPLATE = """You are translating a CS course's lecture notes (MIT's "Missing Semester") \
from English into {lang_name}, for students who read {lang_name} but work daily with English-language \
tools, terminals, and documentation.

Rules:
- Translate explanatory prose fully and naturally into {lang_name}. Use clear, idiomatic language \
appropriate for students; do not follow English word order when it sounds unnatural.
- Keep established technical terms in English when they are commonly used that way by learners or \
when translating them would make the concept harder to recognize. This includes command-line tool \
names, flags, file paths, package names, keyboard shortcuts, and proper nouns (e.g. "Git", "SSH", \
"vim", "grep"). Translate ordinary explanations around those terms. Do not leave whole sentences in \
English just because they discuss technical topics.
- For a technical concept without a widely used Burmese equivalent, use a brief Burmese explanation \
and include the English term in parentheses on first mention. Use the English term alone afterwards.
- Do not translate or alter any text that looks like a placeholder token of the form \
\\u0001PROTn\\u0001 — copy it through completely unchanged, including the surrounding characters.
- Preserve Markdown structure exactly: headings, list markers, emphasis (*, **), blockquotes, and \
blank-line paragraph breaks.
- Do not add commentary, notes, or explanations of your own. Output only the translated Markdown.
- Do not wrap the output in a code fence.
"""


def translate_chunk(client, model: str, lang_name: str, chunk: str, retries: int = 4) -> str:
    if not chunk.strip():
        return chunk
    system = SYSTEM_INSTRUCTION_TEMPLATE.format(lang_name=lang_name)
    delay = 2.0
    last_err = None
    for attempt in range(retries):
        try:
            resp = client.models.generate_content(
                model=model,
                contents=chunk,
                config={"system_instruction": system, "temperature": 0.2},
            )
            text = resp.text
            if text is None:
                raise RuntimeError("empty response (likely safety-filtered)")
            return text
        except Exception as e:  # noqa: BLE001 - want to retry on any transient API error
            last_err = e
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"translation failed after {retries} attempts: {last_err}")


def translate_file(client, model: str, lang_name: str, raw: str, max_chars: int,
                    frontmatter_keys, sleep_s: float) -> str:
    fm, body = split_frontmatter(raw)

    prot = Protector()
    protected_body = prot.protect(body)
    chunks = chunk_body(protected_body, max_chars)

    translated_chunks = []
    for chunk in chunks:
        translated_chunks.append(translate_chunk(client, model, lang_name, chunk))
        if sleep_s:
            time.sleep(sleep_s)
    translated_body = "\n\n".join(translated_chunks)
    translated_body = prot.restore(translated_body)

    if fm:
        for key in frontmatter_keys:
            if key in fm and isinstance(fm[key], str) and fm[key].strip():
                fm[key] = translate_chunk(client, model, lang_name, fm[key]).strip()
                if sleep_s:
                    time.sleep(sleep_s)
        return render_frontmatter(fm) + translated_body
    return translated_body


# --------------------------------------------------------------------------
# Progress tracking (resumable, idempotent on unchanged source content)
# --------------------------------------------------------------------------

def load_progress(path: Path) -> dict:
    if path.exists():
        return json.loads(path.read_text())
    return {}


def save_progress(path: Path, data: dict):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


# --------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", required=True, type=Path, help="Path to local clone of missing-semester")
    ap.add_argument("--years", nargs="+", default=["_2019", "_2020", "_2026"],
                     help="Content directories to translate (default: _2019 _2020 _2026)")
    ap.add_argument("--out", type=Path, default=None,
                     help="Output directory (default: <repo>-<lang-code> next to --repo)")
    ap.add_argument("--lang-code", default="my", help="Target language code, used in output dir name (default: my)")
    ap.add_argument("--lang-name", default="Burmese (Myanmar)",
                     help='Target language name for the translation prompt (default: "Burmese (Myanmar)")')
    ap.add_argument("--model", default="gemini-3.8-flash", help="Gemini model id (default: gemini-3.8-flash)")
    ap.add_argument("--api-key-env", default="GEMINI_API_KEY", help="Env var holding the Gemini API key")
    ap.add_argument("--frontmatter-keys", nargs="+", default=["title"],
                     help="Front matter keys to translate (default: title)")
    ap.add_argument("--max-chunk-chars", type=int, default=3000, help="Max chars per API call (default: 3000)")
    ap.add_argument("--sleep", type=float, default=1.0, help="Seconds to sleep between API calls (default: 1.0)")
    ap.add_argument("--limit", type=int, default=None, help="Only process the first N files (for testing)")
    ap.add_argument("--force", action="store_true", help="Re-translate even if unchanged since last run")
    ap.add_argument("--dry-run", action="store_true", help="Translate but don't write files; print a preview")
    args = ap.parse_args()

    api_key = os.environ.get(args.api_key_env)
    if not api_key:
        sys.exit(f"Set {args.api_key_env} in your environment first.")
    client = genai.Client(api_key=api_key)

    repo = args.repo.resolve()
    if not repo.is_dir():
        sys.exit(f"--repo not found: {repo}")
    out_dir = args.out.resolve() if args.out else repo.parent / f"{repo.name}-{args.lang_code}"
    progress_path = out_dir / ".translation_progress.json"
    progress = load_progress(progress_path) if not args.dry_run and progress_path.exists() else {}

    md_files = []
    for year in args.years:
        year_dir = repo / year
        if not year_dir.is_dir():
            print(f"skip (not found): {year_dir}", file=sys.stderr)
            continue
        md_files.extend(sorted(year_dir.rglob("*.md")))

    if args.limit:
        md_files = md_files[: args.limit]

    print(f"{len(md_files)} markdown file(s) to check, model={args.model}, target={args.lang_name}")

    for i, src_path in enumerate(md_files, 1):
        rel = src_path.relative_to(repo)
        raw = src_path.read_text(encoding="utf-8")
        h = content_hash(raw)

        if not args.force and progress.get(str(rel), {}).get("hash") == h:
            print(f"[{i}/{len(md_files)}] unchanged, skip: {rel}")
            continue

        print(f"[{i}/{len(md_files)}] translating: {rel}")
        try:
            translated = translate_file(
                client, args.model, args.lang_name, raw,
                args.max_chunk_chars, args.frontmatter_keys, args.sleep,
            )
        except Exception as e:  # noqa: BLE001
            print(f"  FAILED: {e}", file=sys.stderr)
            continue

        if args.dry_run:
            print("  --- preview (first 400 chars) ---")
            print("  " + translated[:400].replace("\n", "\n  "))
            continue

        dest = out_dir / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        out_dir.mkdir(parents=True, exist_ok=True)
        dest.write_text(translated, encoding="utf-8")

        progress[str(rel)] = {"hash": h, "translated_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        save_progress(progress_path, progress)

    if not args.dry_run:
        print(f"Done. Output: {out_dir}")


if __name__ == "__main__":
    main()
