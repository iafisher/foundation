`foundation` is a package of software libraries and utilities that I download on every machine that I use. It includes:

- My preferred basic configuration for the shell, Vim, and Git
- A few useful scripts
- Utility libraries written in Python (`from ian.prelude import *`, `from ian import colors`, etc.)
- Bash helper functions (available with `source "$IAN_BASH_PRELUDE"`)

I set up a new machine with the `bootstrap.sh` script, which can be downloaded with `wget https://iafisher.com/bootstrap.sh`. (This is an HTTP redirect to the master copy of the file on GitHub, so it is always up-to-date.)

`bootstrap.sh` creates two Git repositories: a clone of `foundation` in `~/.ian/foundation`, and a "dotfiles" repository for machine-specific configuration.

- `~/.ian/bin` is added to the `PATH` environment variable.
- `~/.ian/pythonpath` is added to `PYTHONPATH`, so that I can import the `ian` library from a Python file anywhere on the machine. 

Configuration files (`~/.bashrc`, etc.) are symlinked to the dotfiles repository.

The `foundation` repository can be updated by running `ian.selfupdate`.

## Requirements
- Python 3.11
- The Bash or Zsh shell
- Git

`foundation` does not require root access or the ability to install software.
