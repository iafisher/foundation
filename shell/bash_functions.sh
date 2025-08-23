red() {
  echo "\033[31m$@\033[0m"
}

yellow() {
  echo "\033[33m$@\033[0m"
}

cyan() {
  echo "\033[36m$@\033[0m"
}

green() {
  echo "\033[32m$@\033[0m"
}

gray() {
  echo "\033[90m$@\033[0m"
}

error() {
  echo "$(red error:) $@" >&2
}

status() {
  echo "$(gray ==>) $1"
}

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
