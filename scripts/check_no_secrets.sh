#!/usr/bin/env bash
set -euo pipefail

if git ls-files | grep -E '(^|/)\.env($|\.)' | grep -v '\.env\.example$' >/dev/null; then
  echo "Secret guard failed: .env files must not be tracked."
  git ls-files | grep -E '(^|/)\.env($|\.)' | grep -v '\.env\.example$'
  exit 1
fi

if git grep -n -E '(api_key|secret|token|password)[[:space:]]*=[[:space:]]*["'\''][^"'\'']{12,}' -- \
  ':!scripts/check_no_secrets.sh' ':!docs/**' ':!README.md' >/tmp/agent_consistency_secret_scan.txt; then
  echo "Secret guard failed: suspicious credential assignment found."
  cat /tmp/agent_consistency_secret_scan.txt
  exit 1
fi

rm -f /tmp/agent_consistency_secret_scan.txt
echo "Secret guard OK."
