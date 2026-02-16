import calendar
import contextlib
import time
import zoneinfo

from .. import colors
from ..prelude import *

TZ_NYC = zoneinfo.ZoneInfo("America/New_York")
TZ_UTC = zoneinfo.ZoneInfo("UTC")


def is_datetime_aware(dt: datetime.datetime) -> bool:
    # https://docs.python.org/3.11/library/datetime.html#determining-if-an-object-is-aware-or-naive
    return dt.tzinfo is not None and dt.tzinfo.utcoffset(dt) is not None


def now() -> datetime.datetime:
    return datetime.datetime.now(tz=TZ_NYC)


def utcnow() -> datetime.datetime:
    return datetime.datetime.now(tz=TZ_UTC)


def today() -> datetime.date:
    return now().date()


def start_of_week(date: datetime.date) -> datetime.date:
    return date - datetime.timedelta(days=date.weekday())


def epoch() -> datetime.datetime:
    return from_epoch_secs_utc(0.0)


def from_epoch_secs(secs: float) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(secs, tz=TZ_NYC)


def from_epoch_secs_utc(secs: float) -> datetime.datetime:
    return datetime.datetime.fromtimestamp(secs, tz=TZ_UTC)


def parse_date(s: str) -> datetime.date:
    try:
        return datetime.date.fromisoformat(s)
    except ValueError:
        raise KgError("could not parse date", s=s) from None


def range_inclusive(
    start: datetime.date, end: datetime.date
) -> Generator[datetime.date, None, None]:
    assert start <= end

    it = start
    while it <= end:
        yield it
        it += datetime.timedelta(days=1)


def range_months_inclusive(
    start: datetime.date, end: datetime.date
) -> Generator[datetime.date, None, None]:
    assert start <= end

    start = start.replace(day=1)
    end = end.replace(day=1)

    it = start
    while it <= end:
        yield it
        it = next_month(it)


def days_in_month(month: datetime.date) -> int:
    return calendar.monthrange(month.year, month.month)[1]


def last_month(date: datetime.date) -> datetime.date:
    if date.month == 1:
        return datetime.date(year=date.year - 1, month=12, day=1)
    else:
        return datetime.date(year=date.year, month=date.month - 1, day=1)


def next_month(date: datetime.date) -> datetime.date:
    if date.month == 12:
        return datetime.date(year=date.year + 1, month=1, day=1)
    else:
        return datetime.date(year=date.year, month=date.month + 1, day=1)


def range_days_of_month(month: datetime.date) -> Generator[datetime.date, None, None]:
    yield from range_inclusive(
        month.replace(day=1), month.replace(day=days_in_month(month))
    )


def to_month_str(date: datetime.date) -> str:
    return f"{date.year}-{date.month:0>2}"


def month_to_quarter(m: int) -> int:
    return ((m - 1) // 3) + 1


def is_month_in_quarter(*, month: int, quarter: int) -> bool:
    return month_to_quarter(month) == quarter


@contextlib.contextmanager
def print_time(label: str = "") -> Generator[None, None, None]:
    start_time_secs = time.time()
    try:
        yield
    finally:
        duration_secs = time.time() - start_time_secs
        if label:
            colors.print(colors.gray(f"==> duration ({label}): {duration_secs:.1f}s"))
        else:
            colors.print(colors.gray(f"==> duration: {duration_secs:.1f}s"))
