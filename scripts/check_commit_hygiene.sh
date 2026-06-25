#!/usr/bin/env bash
set -euo pipefail

range="${1:-origin/main..HEAD}"
pattern='claude|codex|anthropic|openai|copilot|co-authored-by|generated with|🤖'

if git log --format='%B' "$range" | grep -iEq "$pattern"; then
  echo "Commit hygiene check failed: forbidden attribution/tool reference found."
  git log --format='%h %s' "$range"
  exit 1
fi

echo "Commit hygiene OK."

