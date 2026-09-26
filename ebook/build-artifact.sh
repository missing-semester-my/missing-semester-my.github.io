#!/bin/bash
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"
echo "Building all eBook artifacts (PDF & EPUB)..."
python3 ebook/scripts/build_ebook.py --year all --format all "$@"
