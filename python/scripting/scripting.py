import subprocess

from ian.prelude import *


def sh(cmd: str, check: bool = True, **kwargs: Any) -> str:
    proc = subprocess.run(
        ["/usr/bin/env", "bash", "-c", cmd],
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        **kwargs
    )
    return proc.stdout


def sh2(cmd: str, check: bool = True, **kwargs: Any) -> Tuple[str, str]:
    proc = subprocess.run(
        ["/usr/bin/env", "bash", "-c", cmd],
        check=check,
        text=True,
        capture_output=True,
        **kwargs
    )
    return proc.stdout, proc.stderr
