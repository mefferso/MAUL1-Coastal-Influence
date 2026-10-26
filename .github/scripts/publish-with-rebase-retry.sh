#!/usr/bin/env bash
# Commit staged archive outputs and publish without overwriting a concurrent push.
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "usage: $0 <branch> <commit-message>" >&2
  exit 2
fi

branch="$1"
message="$2"
if git diff --cached --quiet; then
  echo "No staged changes to publish."
  exit 0
fi

git commit -m "$message"
for attempt in 1 2 3; do
  git fetch origin "$branch"
  if ! git rebase "origin/$branch"; then
    git rebase --abort >/dev/null 2>&1 || true
    echo "::error::Rebase conflict while publishing to $branch; remote history was left unchanged." >&2
    exit 1
  fi
  if git push origin "HEAD:$branch"; then
    exit 0
  fi
  if [[ "$attempt" -lt 3 ]]; then
    sleep $((attempt * 2))
  fi
done

echo "::error::Could not publish to $branch after three fetch/rebase/push attempts." >&2
exit 1
