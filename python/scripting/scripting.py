import subprocess

from ian.prelude import *


def sh0(cmd: str, check: bool = True, **kwargs: Any) -> None:
    _sh(cmd, check=check)


def sh1(cmd: str, check: bool = True, **kwargs: Any) -> str:
    proc = _sh(cmd, check=check, stdout=subprocess.PIPE, **kwargs)
    return proc.stdout


def sh2(cmd: str, check: bool = True, **kwargs: Any) -> Tuple[str, str]:
    proc = _sh(check=check, capture_output=True, **kwargs)
    return proc.stdout, proc.stderr


def _sh(cmd: str, **kwargs: Any) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["/usr/bin/env", "bash", "-c", cmd], text=True, **kwargs)
