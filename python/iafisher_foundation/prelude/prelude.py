import datetime
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
    Tuple,
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
    """
    An exception with key-value diagnostic information and a human-readable string format.
    """

    _values: StrDict

    def __init__(self, msg: str, **values: Any) -> None:
        super().__init__(msg, values)
        self._values = values

    def val(self, key: str) -> Any:
        """
        Returns the value associated with `key`.
        """
        return self._values[key]

    def attach(self, **extra: Any) -> "KgError":
        """
        Attaches more information to an existing `KgError` object.
        """
        values = self._values.copy()
        values.update(extra)
        return KgError(self.args[0], **values)

    def to_human_str(self) -> str:
        """
        Formats the exception as a human-readable string suitable to be printed.
        """
        builder: List[str] = []
        builder.append(f"{self.args[0]}")
        for key, value in self._values.items():
            builder.append(f"  {key}: {value!r}")
        return "\n".join(builder)


def eprint(*args: Any, **kwargs: Any) -> None:
    """
    Prints to standard error.
    """
    print(*args, file=sys.stderr, **kwargs)


def bail(*args: Any, **kwargs: Any) -> NoReturn:
    """
    Prints the arguments to standard error and exit.
    """
    eprint(*args, **kwargs)
    sys.exit(1)


def remove_prefix(s: str, *, prefix: str, or_throw: bool = False) -> str:
    """
    Returns `s` without the initial substring `prefix`.

    When `or_throw` is False (the default), if `s` does not begin with `prefix`,
    it is returned unchanged.
    """
    # TODO(2025-02): move to `strhelper` library?
    if s.startswith(prefix):
        return s[len(prefix) :]
    else:
        if or_throw:
            raise KgError("string does not have expected prefix", s=s, prefix=prefix)

        return s


def remove_suffix(s: str, *, suffix: str, or_throw: bool = False) -> str:
    """
    Returns `s` without the ending substring `suffix`.

    When `or_throw` is False (the default), if `s` does not end with `suffix`,
    it is returned unchanged.
    """
    # TODO(2025-02): move to `strhelper` library?
    if s.endswith(suffix):
        return s[: -len(suffix)]
    else:
        if or_throw:
            raise KgError("string does not have expected suffix", s=s, suffix=suffix)

        return s


def pluralize(n: int, word: str, plural: str = "") -> str:
    """
    Appends 's' to `word` if `n` is not 1.

    If `word` has a non-standard plural form, pass it in as `plural`.
    """
    # TODO(2025-02): move to `strhelper` library?
    if not plural:
        plural = word + "s"
    return f"{n:,} {word}" if n == 1 else f"{n:,} {plural}"


@runtime_checkable
class SupportsGreaterThan(Protocol):
    def __gt__(self, _other: object) -> bool: ...


T_gt = TypeVar("T_gt", bound=SupportsGreaterThan)


def max_or_none(xs: Iterable[Optional[T_gt]]) -> Optional[T_gt]:
    """
    Returns the maximum non-null value in `xs`.
    """
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
    """
    Flattens `xs`, a list of lists, into a mere list.
    """
    return list(itertools.chain.from_iterable(xs))


def opt_call(x: Optional[T], f: Callable[[T], T2]) -> Optional[T2]:
    """
    Returns `f(x)` if `x` is not None, otherwise None.
    """
    return f(x) if x is not None else None


def opt_call_or(x: Optional[T], f: Callable[[T], T2], default: T2) -> Optional[T2]:
    """
    Returns `f(x)` if `x` is not None, otherwise `default`.
    """
    return f(x) if x is not None else default


def opt_or(x: Optional[T], default: T) -> T:
    """
    Returns `x` if not None, otherwise `default`.

    This is safer than the idiom `x or default` which evaluates to `default` on non-null
    values like 0 and the empty string.
    """
    return x if x is not None else default


# 2026-06: Old name retained for backwards compatibility.
map_or_none = opt_call


def partition_tf(xs: List[T], f: Callable[[T], bool]) -> Tuple[List[T], List[T]]:
    """
    Returns `(first, second)`, where `first` is every element in `xs` for which `f` returns True,
    and `second` is all others.
    """
    left: List[T] = []
    right: List[T] = []

    for x in xs:
        if f(x):
            left.append(x)
        else:
            right.append(x)

    return left, right


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
    """
    Creates a lazy regular expression that is not compiled until `.get()` is called.
    """
    return lazy(lambda: re.compile(pat, *args, **kwargs))


def sha256(s: str) -> str:
    """
    Computes the SHA-256 hash of the string and returns the hexadecimal representation.
    """
    return hashlib.sha256(s.encode("utf8")).hexdigest()


def sha256b(b: bytes) -> str:
    """
    Computes the SHA-256 hash of the bytestring and returns the hexadecimal representation.
    """
    return hashlib.sha256(b).hexdigest()


def parse_date(s: str) -> datetime.date:
    """
    Parses a string into a `datetime.date` object.

    Currently only supports ISO-8601 format (YYYY-MM-DD).
    """
    return datetime.date.fromisoformat(s)


def confirm(prompt: str) -> bool:
    """
    Prompts the user on standard input for confirmation and returns whether they answered 'yes' or
    'no'.
    """
    while True:
        r = input(prompt).strip().lower()
        if r in ("y", "yes"):
            return True
        elif r in ("n", "no"):
            return False
        else:
            print("Please enter 'yes' or 'no'.")


def confirm_or_bail(prompt: str) -> None:
    """
    Prompts the user on standard input for confirmation and exits the program if they answer 'no'.
    """
    if not confirm(prompt):
        bail("Aborted.")


def todo() -> NoReturn:
    raise NotImplementedError


def impossible() -> NoReturn:
    raise Exception("This code path should never be reached.")
