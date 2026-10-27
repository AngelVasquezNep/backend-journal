"""Validated source positions contain neither filesystem paths nor arbitrary URLs."""

import math
from dataclasses import dataclass


def nonnegative(value: int) -> None:
    """Require an integer position >= 0; exclude booleans and coercion."""
    if type(value) is not int or value < 0:
        raise ValueError("Source positions must be nonnegative integers.")


@dataclass(frozen=True)
class PdfLocator:
    """Identify a one-based PDF page and optional normalized text offsets."""

    page: int
    text_start: int | None = None
    text_end: int | None = None
    kind: str = "pdf"

    def __post_init__(self) -> None:
        """Reject invalid pages, reversed offsets and a forged discriminator."""
        nonnegative(self.page)
        if self.page < 1 or self.kind != "pdf":
            raise ValueError("A PDF source requires a positive page.")
        for value in (self.text_start, self.text_end):
            if value is not None:
                nonnegative(value)
        if (
            self.text_start is not None
            and self.text_end is not None
            and self.text_end < self.text_start
        ):
            raise ValueError("Source text end cannot precede its start.")


@dataclass(frozen=True)
class TextLocator:
    """Identify an inclusive one-based line range in a UTF-8 original."""

    line_start: int
    line_end: int
    kind: str = "text"

    def __post_init__(self) -> None:
        """Reject zero, reversed or non-integer line positions."""
        nonnegative(self.line_start)
        nonnegative(self.line_end)
        if self.line_start < 1 or self.line_end < self.line_start or self.kind != "text":
            raise ValueError("A text source requires an ordered positive line range.")


@dataclass(frozen=True)
class DocxLocator:
    """Retain ordered headings, a zero-based block and optional table/row/cell indices."""

    heading_path: tuple[str, ...]
    block: int
    table: int | None = None
    row: int | None = None
    cell: int | None = None
    kind: str = "docx"

    def __post_init__(self) -> None:
        """Validate structural positions and heading strings without accepting path/URL fields."""
        if (
            self.kind != "docx"
            or not isinstance(self.heading_path, tuple)
            or any(not isinstance(h, str) for h in self.heading_path)
        ):
            raise ValueError("Invalid DOCX source location.")
        nonnegative(self.block)
        for value in (self.table, self.row, self.cell):
            if value is not None:
                nonnegative(value)


@dataclass(frozen=True)
class ImageLocator:
    """Identify page 1 and an optional normalized (x, y, width, height) raster box."""

    page: int = 1
    bbox: tuple[float, float, float, float] | None = None
    kind: str = "image"

    def __post_init__(self) -> None:
        """Reject unbounded, nonfinite, out-of-image and forged source coordinates."""
        if type(self.page) is not int or self.page != 1 or self.kind != "image":
            raise ValueError("An image source requires page 1.")
        if self.bbox is not None:
            if len(self.bbox) != 4 or any(
                type(v) not in (int, float) or not math.isfinite(v) for v in self.bbox
            ):
                raise ValueError("Image coordinates must be finite numbers.")
            x, y, width, height = self.bbox
            if min(x, y) < 0 or min(width, height) <= 0 or x + width > 1 or y + height > 1:
                raise ValueError("Image coordinates must fit within the original image.")


type Locator = PdfLocator | TextLocator | DocxLocator | ImageLocator


def locator_dict(value: Locator) -> dict[str, object]:
    """Serialize only actual locator fields, omitting optional nulls rejected by the public schema."""
    from dataclasses import asdict

    return {key: item for key, item in asdict(value).items() if item is not None}


def decode_locator(value: object) -> Locator:
    """Revalidate an exact discriminated locator from stored/worker/HTTP data; reject unknown fields."""
    if not isinstance(value, dict) or not isinstance(value.get("kind"), str):
        raise ValueError("A typed source location is required.")
    data = dict(value)
    kind = data.pop("kind")
    if kind == "pdf" and set(data) <= {"page", "text_start", "text_end"} and "page" in data:
        return PdfLocator(**data)
    if kind == "text" and set(data) == {"line_start", "line_end"}:
        return TextLocator(**data)
    if (
        kind == "docx"
        and set(data) <= {"heading_path", "block", "table", "row", "cell"}
        and {"heading_path", "block"} <= set(data)
    ):
        if not isinstance(data["heading_path"], (list, tuple)):
            raise ValueError("Invalid heading path.")
        data["heading_path"] = tuple(data["heading_path"])
        return DocxLocator(**data)
    if kind == "image" and set(data) <= {"page", "bbox"} and "page" in data:
        if "bbox" in data:
            if not isinstance(data["bbox"], (list, tuple)):
                raise ValueError("Invalid image position.")
            data["bbox"] = tuple(data["bbox"])
        return ImageLocator(**data)
    raise ValueError("Unknown source location fields.")
