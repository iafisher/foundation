red() {
  echo -e "\033[31m$@\033[0m"
}

yellow() {
  echo -e "\033[33m$@\033[0m"
}

cyan() {
  echo -e "\033[36m$@\033[0m"
}

green() {
  echo -e "\033[32m$@\033[0m"
}

gray() {
  echo -e "\033[90m$@\033[0m"
}

error() {
  echo -e "$(red error:) $@" >&2
}

fatal() {
  error "$@"
  exit 1
}

status() {
  echo -e "==> $@"
}

# TODO(2025-08): Replace uses of these functions with `ian_parse_flags`.
__assert_zero_args() {
  if ! [[ $# -eq 0 ]]; then
    error "command takes 0 arguments"
    return 1
  fi
}

__assert_one_arg() {
  if ! [[ $# -eq 1 ]]; then
    error "command takes 1 argument"
    return 1
  fi
}

__assert_zero_or_one_arg() {
  if [[ $# -gt 1 ]] || [[ "$1" = -* ]]; then
    error "command takes 0 or 1 argument"
    return 1
  fi
}

__assert_one_or_more_args() {
  if [[ $# -eq 0 ]]; then
    error "command takes 1 or more arguments"
    return 1
  fi
}

### Example usage:
###
###     ian_parse_flags 'PATH [--name=] --verbose' "$@"
###     path="${__args[PATH]}"
###     name="${__args[--name]}"
###     verbose="${__args[--verbose]}"
###
### `PATH` is a positional argument. `[--name=]` is an optional flag that takes an argument.
### `--verbose` is a switch (a flag that takes no argument).
declare -A __args
ian_parse_flags() {
  if (( $# == 0 )); then
    echo "BUG: ian_parse_flags takes at least one argument"
    exit 1
  fi

  desc="$1"
  shift

  cmd="${IAN_PARSE_FLAGS_CMD:-$0}"
  __usage_error() {
    echo "usage: $cmd $desc"
    echo
    echo "error: $1"
    exit 1
  }

  known_positionals=()
  declare -A required_flags
  declare -A optional_flags
  declare -A known_switches

  for x in $desc; do
    case "$x" in
      # e.g., [--flag=] (an optional flag)
      \[-*=\])
        name="${x%=\]}"
        name="${name#\[}"
        optional_flags["$name"]="0"
        __args["$name"]=""
        ;;
        # e.g., --flag= (a required flag)
      -*=)
        name="${x%=}"
        required_flags["$name"]="0"
        ;;
      # e.g., --flag (a switch)
      -*)
        known_switches["$x"]="0"
        __args["$x"]="0"
        ;;
      *)
        known_positionals+=("$x")
        ;;
    esac
  done

  __do_positional() {
    if (( ${#known_positionals[@]} > 0 )); then
      __args["${known_positionals[0]}"]="$1"
      known_positionals=("${known_positionals[@]:1}")
    else
      __usage_error "too many anonymous arguments (at '$1')"
    fi
  }

  flags_done="0"
  while (( $# > 0 )); do
    arg="$1"
    shift
    case "$arg" in
      -h|-help|--help)
        echo "usage: $cmd $desc"
        exit 0
        ;;
      -)
        __do_positional "$arg"
        ;;
      --)
        flags_done="1"
        ;;
      -*)
        if (( flags_done == 1 )); then
          __do_positional "$arg"
        else
          if [[ -v required_flags["$arg"] ]]; then
            b="${required_flags[$arg]}"
            (( b == 1 )) && __usage_error "flag: $arg was repeated"
            required_flags["$arg"]="1"

            if (( $# == 0 )) || [[ "$1" = -* ]]; then
              __usage_error "flag $arg requires an argument"
            fi

            __args["$arg"]="$1"
            shift
          elif [[ -v optional_flags["$arg"] ]]; then
            b="${optional_flags[$arg]}"
            (( b == 1 )) && __usage_error "flag $arg was repeated"
            optional_flags["$arg"]="1"

            if (( $# == 0 )) || [[ "$1" = -* ]]; then
              __usage_error "flag $arg requires an argument"
            fi

            __args["$arg"]="$1"
            shift
          elif [[ -v known_switches["$arg"] ]]; then
            b="${known_switches[$arg]}"
            (( b == 1 )) && __usage_error "flag $arg was repeated"
            known_switches["$arg"]="1"
            __args["$arg"]="1"
          else
            __usage_error "unknown flag $arg"
          fi
        fi
        ;;
      *)
        __do_positional "$arg"
        ;;
    esac
  done

  unset __do_positional

  if (( ${#known_positionals[@]} > 0 )); then
    __usage_error "missing anonymous argument '${known_positionals[0]}'"
  fi

  for flag in "${!required_flags[@]}"; do
    if (( ${required_flags[$flag]} == 0 )); then
      __usage_error "missing required flag $flag"
    fi
  done

  unset __usage_error
}

### Example usage:
###
###     ian_parse_flags_subcmd \
###       add 'PATH [--name=] --verbose' \
###       remove 'NAME' \
###       -- "$@"
###
###     case "$__subcmd" in
###       add)
###         main_add  # `main_add` can access `__args` like usual
###         ;;
###       remove)
###         main_remove
###         ;;
###     esac
###
__subcmd=""
ian_parse_flags_subcmd() {
  declare -A subcmds
  subcmds_help=()
  while (( $# > 0 )); do
    arg="$1"
    case "$1" in
      --)
        shift
        break
        ;;
      -*)
        echo "BUG: unexpected flag: $arg (in ian_parse_flags_subcmd)"
        exit 1
        ;;
      *)
        (( $# == 1 )) && ( echo "BUG: subcmd $arg missing description (in ian_parse_flags_subcmd)"; exit 1 )
        subcmds["$arg"]="$2"
        subcmds_help+=("  $arg $2")
        shift 2
        ;;
    esac
  done

  __print_usage() {
    echo "usage: $0 SUBCMD"
    echo
    for help in "${subcmds_help[@]}"; do
      echo "$help"
    done
    echo
  }

  __usage_error() {
    __print_usage
    echo "error: $1"
    exit 1
  }

  if (( $# == 0 )); then
    __usage_error "missing subcommand"
  fi

  if [[ "$1" = -h ]] || [[ "$1" = -help ]] || [[ "$1" = --help ]] || [[ "$1" = help ]]; then
    __print_usage
    exit
  fi

  __subcmd="$1"
  shift

  if ! [[ -v subcmds[$__subcmd] ]]; then
    __usage_error "unknown subcommand: $__subcmd"
  fi
  subcmd_desc="${subcmds[$__subcmd]}"

  export IAN_PARSE_FLAGS_CMD="$0 $__subcmd"
  ian_parse_flags "$subcmd_desc" "$@"
  unset IAN_PARSE_FLAGS_CMD

  unset __print_usage
  unset __usage_error
}
