import enum
import hashlib
import itertools
import os
import re
import sys
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    List,
    NoReturn,
    Optional,
    Protocol,
    TypeVar,
    Union,
    runtime_checkable,
)

try:
    from typing_extensions import override  # type: ignore
except ModuleNotFoundError:
    override: Callable[..., Any] = lambda f: f


@dataclass(frozen=True)
class Nothing:
    """
    A subclass of `object` that exists only to signal the absence of a value.

    Typically this is used as a default argument for function parameters, to distinguish between
    "no value was passed" and "the value `None` was passed".

    This is its own class to override `repr`, as `object.__repr__` includes the object's memory
    address which is not stable for test output.

    It is a dataclass for the sake of automatically deriving `__repr__` and `__eq__`, as well as
    to specify `frozen=True` which allows objects of its type to be used as the default value of
    fields on other dataclasses.
    """


NOTHING = Nothing()

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

    def attach(self, **extra: Any) -> "KgError":
        values = self._values.copy()
        values.update(extra)
        return KgError(self.args[0], **values)

    def to_human_str(self) -> str:
        builder: List[str] = []
        builder.append(f"{self.args[0]}")
        for key, value in self._values.items():
            builder.append(f"  {key}: {value!r}")
        return "\n".join(builder)


def eprint(*args: Any, **kwargs: Any) -> None:
    print(*args, file=sys.stderr, **kwargs)


def bail(*args: Any, **kwargs: Any) -> NoReturn:
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
    def __gt__(self, _other: object) -> bool: ...


T_gt = TypeVar("T_gt", bound=SupportsGreaterThan)


def max_or_none(xs: Iterable[Optional[T_gt]]) -> Optional[T_gt]:
    m = None
    for x in xs:
        if x is None:
            return None
        elif m is None or x > m:
            m = x
    return m


T = TypeVar("T")
T2 = TypeVar("T2")


def find_first(xs: Iterable[T], pred: Callable[[T], bool]) -> Optional[T]:
    """
    Finds the first element of `xs` such that `pred` returns True.
    """
    for x in xs:
        if pred(x):
            return x

    return None


def flatten_list(xs: List[List[T]]) -> List[T]:
    return list(itertools.chain.from_iterable(xs))


def map_or_none(x: Optional[T], f: Callable[[T], T2]) -> Optional[T2]:
    return f(x) if x is not None else None


def map_str_or_none(x: Optional[str], f: Callable[[str], T]) -> Optional[T]:
    return f(x) if x else None


class StringEnum(enum.Enum):
    @classmethod
    def of_string(cls, s: str) -> "StringEnum":
        s_upper = s.upper()
        for key, val in cls.__members__.items():
            if s_upper == key:
                return val

        raise ValueError(s)


class lazy(Generic[T]):
    def __init__(self, f: Callable[[], T]):
        self.f = f
        self.value = NOTHING

    def get(self) -> T:
        if self.value is NOTHING:
            self.value = self.f()
        return self.value  # type: ignore


def lazy_re(pat: str, *args: Any, **kwargs: Any) -> lazy[re.Pattern[str]]:
    return lazy(lambda: re.compile(pat, *args, **kwargs))


def sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf8")).hexdigest()


def sha256b(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


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
