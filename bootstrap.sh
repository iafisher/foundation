#!/usr/bin/env bash

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
  mkdir -p "$HOME/.vim-backup"

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

  (cat << EOF
source "$HOME/.ian/foundation/shell/env"
" This file contains machine-specific configuration.
EOF
) > "$shellrc"
  git add "$shellrc"

  (cat << EOF
source $HOME/.ian/foundation/vimrc
" This file contains machine-specific configuration.
EOF
) > vimrc
  git add vimrc

  (cat << EOF
[include]
  path = $HOME/.ian/foundation/gitconfig
EOF
) > gitconfig
  git add gitconfig

  git config --global user.name 'Ian Fisher'
  git config --global user.email 'ian@iafisher.com'
  git commit -m "initial commit" --author 'Ian Fisher <ian@iafisher.com>'

  echo "==> configuring shell"
  f="$HOME/.$shellrc"
  if [[ -e "$f" ]]; then
    echo "WARNING: will not overwrite $f. You must either:"
    echo "  - Run 'ln -sf $dotfiles_dir/$shellrc $f'"
    echo "  - Add 'source $dotfiles_dir/$shellrc' to the end of the file."
  else
    ln -s "$dotfiles_dir/$shellrc" "$f"
  fi

  echo "==> configuring vim"
  f="$HOME/.vimrc"
  if [[ -e "$f" ]]; then
    echo "WARNING: will not overwrite $f. You must either:"
    echo "  - Run 'ln -sf $dotfiles_dir/vimrc $f'"
    echo "  - Add 'source $dotfiles_dir/vimrc' to the end of the file."
  else
    ln -s "$dotfiles_dir/vimrc" "$f"
  fi

  echo "==> configuring git"
  f="$HOME/.gitconfig"
  if [[ -e "$f" ]]; then
    echo "WARNING: will not overwrite $f. You must either:"
    echo "  - Run 'ln -sf $dotfiles_dir/gitconfig $f'"
    echo "  - Add 'path = $dotfiles_dir/gitconfig' to an '[include]' block in the file."
  else
    ln -s "$dotfiles_dir/gitconfig" "$f"
  fi

  echo
  echo "==> done"
}

main "$@"
