# Missing Semester → Burmese translation

This folder contains a local batch translation script. It produces Burmese
Markdown files from the English source; review those files before using them
in a published site.

## Setup

```bash
pip install google-genai pyyaml
export GEMINI_API_KEY=...        # https://aistudio.google.com/apikey

# Run commands below from the repository root.
```

## Run

```bash
# 1. sanity check on a couple of files first (costs little, catches prompt issues)
python my/translate_missing_semester.py --repo . --years _2020 --limit 2 --dry-run

# 2. full run
python my/translate_missing_semester.py \
    --repo . \
    --years _2019 _2020 _2026 \
    --lang-code my --lang-name "Burmese (Myanmar)" \
    --out ../missing-semester-my
```

Re-running later only re-translates files that changed upstream (content-hash
tracked in `.translation_progress.json` inside the output dir); pass `--force`
to redo everything. The dry run prints a preview and does not write output
files or progress data.

## Add the translation to a Jekyll fork

The script produces translated `.md` files but does not configure the site.
Community translations are maintained in separate forks, with translated
content in the same `_2019`/`_2020`/`_2026` directory structure. To prepare
this fork:

1. Fork `missing-semester/missing-semester` on GitHub.
2. Copy the translated files for the years you processed from the output
   directory into the matching `_2019`/`_2020`/`_2026` directories in the
   fork.
3. Update `_config.yml` (site title/description), `README.md`, and
   `about.md` for the Burmese audience; add a note that content is
   machine-translated and welcomes corrections, per the upstream
   [translation/license notes](https://missing.csail.mit.edu/license).
4. `bundle exec jekyll serve -w` (or `docker compose up --build` if you'd
   rather not install Ruby) to preview at `localhost:4000`, per the repo's
   own README.
5. Open a PR back to `missing-semester/missing-semester` if you want it
   listed alongside the other translations — check open issues/discussions
   first in case someone's already tracking a Burmese effort.

## Quality notes

- Gemini is asked to translate the explanatory prose into natural Burmese,
  retaining established CS terms in English where that helps learners.
  Review terminology and spot-check translated files before publication.
- Code fences, inline code, links, and Liquid/HTML tags are stripped out
  before the text ever reaches the model and spliced back in afterward, so
  they can't be mistranslated — but do diff a file or two to confirm
  nothing got mangled before trusting a big batch run.
- The script defaults to `gemini-3.8-flash`. Google's model names/aliases
  can change — if you get a 404, check
  https://ai.google.dev/gemini-api/docs/models for the current flash model.
