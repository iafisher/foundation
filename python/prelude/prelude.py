import enum
import itertools
import os
import sys
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    NoReturn,
    Optional,
    Protocol,
    TypeVar,
    Union,
    runtime_checkable,
)

NOTHING = object()

StrDict = Dict[str, Any]
PathLike = Union[os.PathLike[str], str]


class SupportsWrite(Protocol):
    def write(self, s: str, /) -> int: ...


class KgError(Exception):
    _values: StrDict

    def __init__(self, msg: str, **values: Any) -> None:
        super().__init__(msg, values)
        self._values = values

    def val(self, key: str) -> Any:
        return self._values[key]

    def to_human_str(self) -> str:
        builder: List[str] = []
        builder.append(f"{self.args[0]}")
        for key, value in self._values.items():
            builder.append(f"  {key}: {value!r}")
        return "\n".join(builder)


def eprint(*args: Any, **kwargs: Any) -> None:
    print(*args, file=sys.stderr, **kwargs)


def bail(*args: Any, **kwargs: Any) -> None:
    eprint(*args, **kwargs)
    sys.exit(1)


def remove_prefix(s: str, *, prefix: str, or_throw: bool = False) -> str:
    # TODO(2025-02): move to `strhelper` library?
    if s.startswith(prefix):
        return s[len(prefix) :]
    else:
        if or_throw:
            raise KgError("string does not have expected prefix", s=s, prefix=prefix)

        return s


def remove_suffix(s: str, *, suffix: str, or_throw: bool = False) -> str:
    # TODO(2025-02): move to `strhelper` library?
    if s.endswith(suffix):
        return s[: -len(suffix)]
    else:
        if or_throw:
            raise KgError("string does not have expected suffix", s=s, suffix=suffix)

        return s


def pluralize(n: int, word: str, plural: str = "") -> str:
    # TODO(2025-02): move to `strhelper` library?
    if not plural:
        plural = word + "s"
    return f"{n:,} {word}" if n == 1 else f"{n:,} {plural}"


@runtime_checkable
class SupportsGreaterThan(Protocol):
    def __gt__(self, other: object) -> bool: ...


T = TypeVar("T", bound=SupportsGreaterThan)


def max_or_none(xs: Iterable[Optional[T]]) -> Optional[T]:
    m = None
    for x in xs:
        if x is None:
            return None
        elif m is None or x > m:
            m = x
    return m


T1 = TypeVar("T1")


def flatten_list(xs: List[List[T1]]) -> List[T1]:
    return list(itertools.chain.from_iterable(xs))


T2 = TypeVar("T2")
T3 = TypeVar("T3")


def map_or_none(x: Optional[T2], f: Callable[[T2], T3]) -> Optional[T3]:
    return f(x) if x is not None else None


T4 = TypeVar("T4")


def map_str_or_none(x: Optional[str], f: Callable[[str], T4]) -> Optional[T4]:
    return f(x) if x else None


class StringEnum(enum.Enum):
    @classmethod
    def of_string(cls, s: str) -> "StringEnum":
        s_upper = s.upper()
        for key, val in cls.__members__.items():
            if s_upper == key:
                return val

        raise ValueError(s)


def confirm(prompt: str) -> bool:
    while True:
        r = input(prompt).strip().lower()
        if r in ("y", "yes"):
            return True
        elif r in ("n", "no"):
            return False
        else:
            print("Please enter 'yes' or 'no'.")


def confirm_or_bail(prompt: str) -> None:
    if not confirm(prompt):
        bail("Aborted.")


def todo() -> NoReturn:
    raise NotImplementedError


def impossible() -> NoReturn:
    raise Exception("This code path should never be reached.")
