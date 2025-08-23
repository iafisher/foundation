#!/bin/bash

set -eu

main() {
  if [[ $# -ne 1 ]]; then
    echo "Error: You must pass exactly one argument, the directory to create the 'dotfiles' repo in."
    exit 1
  fi

  code_dir="$1"
  dotfiles_dir="$(realpath "$code_dir/dotfiles")"

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

  uses_zsh=0
  if [[ "$SHELL" = *zsh ]]; then
    uses_zsh=1
  fi

  if (( uses_zsh == 1 )); then
    shellrc="zshrc"
  else
    shellrc="bashrc"
  fi

  echo "# This file contains machine-specific configuration." > "$shellrc"
  git add "$shellrc"

  echo '" This file contains machine-specific configuration.' > vimrc
  git add vimrc

  git config --global user.name 'Ian Fisher'
  git config --global user.email 'ian@iafisher.com'
  git commit -m "initial commit" --author 'Ian Fisher <ian@iafisher.com>'

  git clone . "$HOME/.ian/dotfiles"
  git config --local receive.denyCurrentBranch updateInstead

  echo "==> appending to ~/.$shellrc"
  f="$HOME/.$shellrc"
  echo >> "$f"
  echo 'source "$HOME/.ian/foundation/shell/env"' >> "$f"
  echo 'source "$HOME/.ian/dotfiles/'$shellrc'"' >> "$f"
  tail "$f"

  echo "==> appending to ~/.vimrc"
  f="$HOME/.vimrc"
  echo >> "$f"
  echo 'source "$HOME/.ian/foundation/vimrc"' >> "$f"
  echo 'source "$HOME/.ian/dotfiles/vimrc"' >> "$f"
  tail "$f"

  echo
  echo "==> done"
}

main "$@"
