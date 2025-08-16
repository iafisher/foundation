status() {
  echo "==> $1"
}

__assert_zero_args() {
  if ! [[ $# -eq 0 ]]; then
    echo "error: command takes 0 arguments"
    return 1
  fi
}

__assert_one_arg() {
  if ! [[ $# -eq 1 ]]; then
    echo "error: command takes 1 argument"
    return 1
  fi
}

__assert_zero_or_one_arg() {
  if [[ $# -gt 1 ]] || [[ "$1" = -* ]]; then
    echo "error: command takes 0-1 arguments"
    return 1
  fi
}

__assert_one_or_more_args() {
  if [[ $# -eq 0 ]]; then
    echo "error: command takes 1 or more arguments"
    return 1
  fi
}
