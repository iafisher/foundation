from .. import colors
from ..prelude import *


class Table:
    _widths: List[int]
    _rows: List[List[str]]
    _n: int
    _numformat: str

    DEFAULT_SPACING = 2

    def __init__(self, *, numformat: str = "{}") -> None:
        self._widths: List[int] = []
        self._rows: List[List[str]] = []
        self._n = 0
        self._numformat = numformat

    def header(self, items: List[Any]) -> None:
        self.row(items, color=colors.yellow)

    def row(
        self, items: List[Any], *, color: Optional[Callable[[str], str]] = None
    ) -> None:
        if len(self._rows) == 0:
            if not items:
                raise KgError("first row cannot be empty")

            self._n = len(items)
        else:
            if len(items) != self._n:
                raise KgError(
                    "row wrong length", expected=self._n, actual=len(items), items=items
                )

        items_as_str: List[str] = []
        for item in items:
            if isinstance(item, int):
                item = self._numformat.format(item)
            else:
                item = str(item)

            if color is not None:
                item = color(item)

            items_as_str.append(item)

        self._update_widths(items_as_str)
        self._rows.append(items_as_str)

    def sort(self, column: str) -> None:
        column_index = self._get_sort_column(column)
        sorted_rows = sorted(self._rows[1:], key=lambda row: row[column_index])
        self._rows = [self._rows[0]] + list(sorted_rows)

    def to_list(self, *, spacing: int = DEFAULT_SPACING) -> List[str]:
        return [line for line in self._to_list_iter(spacing=spacing)]

    def flush(
        self,
        *,
        spacing: int = 2,
        file: SupportsWrite = sys.stdout,
        align: Optional[List[str]] = None
    ) -> None:
        # TODO(2025-07): handle terminal overflow
        for line in self._to_list_iter(spacing=spacing, align=align):
            colors.print(line, file=file)

    def to_string(self, *, spacing: int = 2, align: Optional[List[str]] = None) -> str:
        return "\n".join(self._to_list_iter(spacing=spacing, align=align)) + "\n"

    def _to_list_iter(
        self, *, spacing: int, align: Optional[List[str]] = None
    ) -> Generator[str, None, None]:
        spaces = " " * spacing

        if align is not None:
            if len(align) != self._n:
                raise KgError(
                    "alignment list must match number of columns",
                    expected=self._n,
                    actual=len(align),
                )

            valid_alignments = {"l", "c", "r"}
            if not all(a in valid_alignments for a in align):
                raise KgError(
                    "invalid alignment values",
                    valid_values=list(valid_alignments),
                    provided=align,
                )

        for row in self._rows:
            line_builder: List[str] = []
            for item, width, alignment in zip(
                row, self._widths, align or ["l"] * self._n
            ):
                if alignment == "l":
                    formatted = left_justify(item, width)
                elif alignment == "r":
                    formatted = right_justify(item, width)
                else:  # 'c'
                    formatted = center_justify(item, width)
                line_builder.append(formatted)

            line = spaces.join(line_builder).rstrip()
            yield line

    def _update_widths(self, items: List[str]) -> None:
        if len(self._widths) == 0:
            self._widths = [display_width(item) for item in items]
        else:
            for i in range(len(items)):
                self._widths[i] = max(display_width(items[i]), self._widths[i])

    def _get_sort_column(self, column: str) -> int:
        if not self._rows:
            raise KgError("cannot sort an empty table")

        header = [colors.strip(s) for s in self._rows[0]]
        for i, header_column in enumerate(header):
            if header_column == column:
                return i

        raise KgError("sort column not found", column=column, options=header)


def display_width(s: str) -> int:
    return len(colors.strip(s))


def left_justify(s: str, width: int) -> str:
    extra = len(s) - display_width(s)
    return s.ljust(width + extra)


def right_justify(s: str, width: int) -> str:
    extra = len(s) - display_width(s)
    return s.rjust(width + extra)


def center_justify(s: str, width: int) -> str:
    extra = len(s) - display_width(s)
    return s.center(width + extra)


def quicktable(
    *rows: List[Any],
    headers: Optional[List[Any]] = None,
    init_kwargs: StrDict = {},
    flush_kwargs: StrDict = {}
) -> None:
    table = Table(**init_kwargs)

    if headers is not None:
        table.header(headers)

    for row in rows:
        table.row(row)
    table.flush(**flush_kwargs)
