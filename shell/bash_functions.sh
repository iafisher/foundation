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
  echo "$(red error:) $@" >&2
}

fatal() {
  error "$@"
  exit 1
}

status() {
  echo "$(gray '==>') $1"
}

# TODO(2025-08): Replace uses of these functions with `__parse_flags`.
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
###     __parse_flags 'PATH [--name=] --verbose' "$@"
###     path="${__args[PATH]}"
###     name="${__args[--name]}"
###     verbose="${__args[--verbose]}"
###
### `PATH` is a positional argument. `[--name=]` is an optional flag that takes an argument.
### `--verbose` is a switch (a flag that takes no argument).
declare -A __args
__parse_flags() {
  if [[ $- == *u* ]]; then
    restore_nounset="1"
  else
    restore_nounset="0"
  fi
  # We need to do potentially unbound hash-map lookups, so this has to be turned off.
  set +u

  desc="$1"
  shift

  __usage_error() {
    echo "usage: $0 $desc"
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

  while (( $# > 0 )); do
    arg="$1"
    case "$arg" in
      -h|-help|--help)
        echo "Usage: $desc"
        exit 0
        ;;
      -*)
        b_rf="${required_flags[$arg]}"
        b_of="${optional_flags[$arg]}"
        b_sw="${known_switches[$arg]}"
        if [[ -n "$b_rf" ]]; then
          (( b_rf == 1 )) && __usage_error "flag: $arg was repeated"
          required_flags["$arg"]="1"

          (( $# == 1 )) && __usage_error "flag $arg requires an argument"
          __args["$arg"]="$2"
          shift 2
        elif [[ -n "$b_of" ]]; then
          (( b_of == 1 )) && __usage_error "flag $arg was repeated"
          optional_flags["$arg"]="1"

          (( $# == 1 )) && __usage_error "flag $arg requires an argument"
          __args["$arg"]="$2"
          shift 2
        elif [[ -n "$b_sw" ]]; then
          (( b_sw == 1 )) && __usage_error "flag $arg was repeated"
          known_switches["$arg"]="1"
          __args["$arg"]="1"
          shift
        else
          __usage_error "unknown flag $arg"
        fi
        ;;
      *)
        if (( ${#known_positionals[@]} > 0 )); then
          __args["${known_positionals[0]}"]="$arg"
          known_positionals=("${known_positionals[@]:1}")
          shift
        else
          __usage_error "too many anonymous arguments (at '$arg')"
        fi
    esac
  done

  if (( ${#known_positionals[@]} > 0 )); then
    __usage_error "missing anonymous argument '${known_positionals[0]}'"
  fi

  for flag in "${!required_flags[@]}"; do
    if (( ${required_flags[$flag]} == 0 )); then
      __usage_error "missing required flag $flag"
    fi
  done

  if (( restore_nounset == 1 )); then
    set -u
  fi

  unset __usage_error
}
