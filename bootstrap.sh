#!/bin/bash

set -eu

main() {
  if [[ $# -ne 0 ]]; then
    echo "bootstrap.sh takes no arguments."
    exit 1
  fi

  if ! command -v git &>/dev/null; then
    echo "git must be installed."
    exit 1
  fi

  mkdir -p "$HOME/.ian"
  mkdir -p "$HOME/.ian/bin"
  mkdir -p "$HOME/.ian/pythonpath"

  foundation_dir="$HOME/.ian/foundation"
  git clone 'https://github.com/iafisher/foundation.git' "$foundation_dir"

  (cat << EOF

source "$foundation_dir/shell/env"
EOF
) >> "$HOME/.bashrc"
}

main "$@"
