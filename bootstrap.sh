#!/bin/bash

set -eu

main() {
  if [[ $# -ne 1 ]]; then
    echo "Error: You must pass exactly one argument, the directory to create the 'dotfiles' repo in."
    exit 1
  fi

  code_dir="$1"
  dotfiles_dir="$code_dir/dotfiles"

  if ! command -v git &>/dev/null; then
    echo "git must be installed."
    exit 1
  fi

  echo "==> creating $HOME/.ian and subdirectories"
  mkdir -p "$HOME/.ian"
  mkdir -p "$HOME/.ian/bin"
  mkdir -p "$HOME/.ian/pythonpath"

  echo "==> cloning 'foundation' repo"
  foundation_dir="$HOME/.ian/foundation"
  git clone 'https://github.com/iafisher/foundation.git' "$foundation_dir"

  echo "==> setting up local 'dotfiles' repo"
  mkdir -p "$dotfiles_dir"
  cd "$dotfiles_dir"
  git init

  cp "$foundation_dir/assets/gitignore" .gitignore
  git add .gitignore

  if [[ "$SHELL" = *zsh ]]; then
    shellrc="zshrc"
  else
    shellrc="bashrc"
  fi

  echo "# This file contains machine-specific configuration." > "$shellrc"
  git add "$shellrc"

  git config --global user.name 'Ian Fisher'
  git config --global user.email 'ian@iafisher.com'
  git commit -m "initial commit" --author 'Ian Fisher <ian@iafisher.com>'

  git clone . "$HOME/.ian/dotfiles"
  git config --local receive.denyCurrentBranch updateInstead

  echo
  echo "Please add the following line to your shell config:"
  echo
  echo "  source \"$HOME/.ian/foundation/shell/env\""
  echo "  source \"$dotfiles_dir/$shellrc\""
  echo
}

main "$@"
