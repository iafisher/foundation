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
  # `-b master` silences a warning about the default branch.
  git init -b master

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

  # If the system has a ~/.bashrc or ~/.zshrc already, copy it to the dotfiles
  # repo as bashrc.system or zshrc.system.
  shellrc_system="$HOME/.$shellrc"
  if [[ -e "$shellrc_system" ]]; then
    shellrc_system_local="$dotfiles_dir/${shellrc}.system"
    echo "WARNING: System has $shellrc file already. Copying to $shellrc_system_local."
    cp "$shellrc_system" "$shellrc_system_local"
    git add "$shellrc_system_local"
    echo "source $shellrc_system_local" >> "$shellrc"
  fi

  (cat << EOF
source $HOME/.ian/foundation/shell/env
# This file contains machine-specific configuration.
EOF
) >> "$shellrc"
  git add "$shellrc"

  (cat << EOF
source $HOME/.ian/foundation/vimrc
" This file contains machine-specific configuration.
EOF
) >> vimrc
  git add vimrc

  git_name="Ian Fisher"
  git_email="ian@iafisher.com"
  (cat << EOF
[user]
	name = $git_name
	email = $git_email

[include]
	path = $HOME/.ian/foundation/gitconfig
EOF
) >> gitconfig
  git add gitconfig

  export GIT_AUTHOR_NAME="$git_name"
  export GIT_AUTHOR_EMAIL="$git_email"
  export GIT_COMMITTER_NAME="$git_name"
  export GIT_COMMITTER_EMAIL="$git_email"
  git commit -m "initial commit"

  echo "==> configuring shell"
  make_symlink "$HOME/.$shellrc" "$dotfiles_dir/$shellrc"

  echo "==> configuring vim"
  make_symlink "$HOME/.vimrc" "$dotfiles_dir/vimrc"

  echo "==> configuring git"
  make_symlink "$HOME/.gitconfig" "$dotfiles_dir/gitconfig"

  echo
  echo "==> done"
  source "$HOME/.$shellrc"
}

make_symlink() {
  target_path="$1"
  src_path="$2"

  if [[ -e "$target_path" ]]; then
    backup="${target_path}.bak"
    echo "WARNING: overwriting ${target_path}. Backup saved to ${backup}."
    cp "$target_path" "$backup"
  fi
  ln -sf "$src_path" "$target_path"
}

main "$@"
