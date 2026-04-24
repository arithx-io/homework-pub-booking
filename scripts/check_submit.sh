#!/usr/bin/env bash
# Convenience wrapper around `python -m grader.check_submit`.
# Pass --verbose, --json, --only ex5 etc.

set -euo pipefail
cd "$(dirname "$0")/.."
exec uv run python -m grader.check_submit "$@"
