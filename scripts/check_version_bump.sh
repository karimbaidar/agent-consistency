#!/usr/bin/env bash
set -euo pipefail

range="${1:-origin/main..HEAD}"
base_ref="${range%%..*}"

changed_files="$(
  {
    git diff --name-only "$range"
    git diff --name-only
  } | sort -u
)"

if ! grep -qx "pyproject.toml" <<<"$changed_files"; then
  echo "Version bump check failed: pyproject.toml must change in every contribution."
  echo "Update [project].version so the PyPI publish workflow can ship a new package."
  echo "$changed_files"
  exit 1
fi

base_pyproject="$(mktemp)"
git show "${base_ref}:pyproject.toml" > "$base_pyproject"

python3 - "$base_pyproject" <<'PY'
import pathlib
import re
import sys

def read_version(text: str) -> str:
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, flags=re.MULTILINE)
    if not match:
        raise SystemExit("Version bump check failed: could not read [project].version.")
    return match.group(1)

def version_key(version: str) -> tuple[int, ...]:
    parts = re.findall(r"\d+", version)
    if not parts:
        raise SystemExit(f"Version bump check failed: invalid version {version!r}.")
    return tuple(int(part) for part in parts)

base_path = pathlib.Path(sys.argv[1])
base = read_version(base_path.read_text(encoding="utf-8"))
head = read_version(pathlib.Path("pyproject.toml").read_text(encoding="utf-8"))

if version_key(head) <= version_key(base):
    raise SystemExit(
        f"Version bump check failed: pyproject.toml version must increase; base={base}, head={head}."
    )

print(f"Version bump OK: {base} -> {head}")
PY
