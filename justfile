set shell := ["bash", "-c"]

[working-directory: 'python']
publish-to-pypi:
  #!/usr/bin/env bash
  set -eu
  current_branch=$(git rev-parse --abbrev-ref HEAD)
  if [[ "$current_branch" != "master" ]]; then
    echo "aborting: not on master branch"
    exit 1
  fi
  local_ref=$(git rev-parse HEAD)
  upstream_ref=$(git rev-parse @{u})
  if [[ "$local_ref" != "$upstream_ref" ]]; then
    echo "aborting: local branch is not in sync with upstream"
    exit 1
  fi
  poetry publish --build

[working-directory: 'python']
test:
  .venv/bin/python3 -m unittest discover -s iafisher_foundation -t .
