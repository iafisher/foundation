import subprocess

from .. import colors
from ..prelude import *


def sh0(cmd: str, check: bool = True, **kwargs: Any) -> None:
    _sh(cmd, check=check)


def sh1(cmd: str, check: bool = True, **kwargs: Any) -> str:
    try:
        proc = _sh(cmd, check=check, capture_output=True, **kwargs)
    except subprocess.CalledProcessError as e:
        print(e.stderr, file=sys.stderr, end="", flush=True)
        raise
    else:
        return proc.stdout


def sh2(cmd: str, check: bool = True, **kwargs: Any) -> Tuple[str, str]:
    proc = _sh(cmd, check=check, capture_output=True, **kwargs)
    return proc.stdout, proc.stderr


def _sh(cmd: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["/usr/bin/env", "bash", "-c", cmd], text=True, **kwargs)


def log(*args: Any, **kwargs: Any):
    hhmm = datetime.datetime.now().strftime("%H:%M")
    print(colors.yellow(f"[{hhmm}]"), end=" ", file=sys.stderr)
    print(*args, file=sys.stderr, **kwargs)
