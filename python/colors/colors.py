from ian.prelude import *


def print_(*args: Any, file: Optional[SupportsWrite] = None, **kwargs: Any) -> None:
    not_a_terminal = not _isatty(file if file is not None else sys.stdout)

    message = " ".join(map(str, args))
    # https://no-color.org/
    if not_a_terminal or "NO_COLOR" in os.environ:
        message = strip(message)

    print(message, file=file, **kwargs)


def eprint_(*args: Any, **kwargs: Any) -> None:
    print_(*args, file=sys.stderr, **kwargs)


def error(*args: Any) -> None:
    print_(red("Error:"), *args, file=sys.stderr)


def red(s: str) -> str:
    return _colored(s, 31)


def yellow(s: str) -> str:
    return _colored(s, 33)


def cyan(s: str) -> str:
    return _colored(s, 36)


def green(s: str) -> str:
    return _colored(s, 32)


def gray(s: str) -> str:
    return _colored(s, 90)


_ansi_codes_re = re.compile(r"\033\[[;?0-9]*[a-zA-Z]")


def strip(s: str) -> str:
    return _ansi_codes_re.sub("", s)


def _colored(s: str, code: int) -> str:
    return f"\033[{code}m{s}\033[0m"


def _isatty(stream: Any) -> bool:
    try:
        return stream.isatty()
    except Exception:
        return False
