"""FR-016 Knowledge values, exact file bounds, strict pagination and safe locators."""

import pytest

from taskify_knowledge.domain.locators import DocxLocator, ImageLocator, PdfLocator, TextLocator
from taskify_knowledge.domain.values import FileMetadata, Pagination, Title, positive_version


def test_title_and_file_boundaries() -> None:
    """Accept one-byte and exactly-20-MiB metadata, Unicode titles and supported extensions."""
    assert Title(" x ").value == "x"
    assert len(Title("😀" * 200).value) == 200
    for size in (1, 20_971_520):
        assert FileMetadata("a.txt", size, "text/plain").size_bytes == size
    assert FileMetadata("a.JPEG", 1, "image/jpeg").media_type == "image/jpeg"
    for size in (0, 20_971_521, -1, True):
        with pytest.raises(ValueError):
            FileMetadata("a.txt", size, "text/plain")


@pytest.mark.parametrize("name", ["../a.txt", "a\\b.txt", "a\x00.txt", "", "x" * 256])
def test_filename_rejection(name: str) -> None:
    """Reject traversal, separators, controls, empty and oversized filenames."""
    with pytest.raises(ValueError):
        FileMetadata(name, 1, "text/plain")


def test_format_pagination_and_location_rejection() -> None:
    """Reject mismatched MIME, invalid page/line/table/box positions and coercion."""
    with pytest.raises(ValueError):
        FileMetadata("a.png", 1, "text/plain")
    for limit in (0, 101, True):
        with pytest.raises(ValueError):
            Pagination(limit=limit)
    with pytest.raises(ValueError):
        Pagination(cursor="x" * 513)
    with pytest.raises(ValueError):
        PdfLocator(0)
    with pytest.raises(ValueError):
        TextLocator(2, 1)
    with pytest.raises(ValueError):
        DocxLocator((), -1)
    with pytest.raises(ValueError):
        ImageLocator(bbox=(0.5, 0.5, 0.6, 0.5))
    with pytest.raises(ValueError):
        positive_version(True)


def test_valid_positions_and_default_pagination() -> None:
    """Preserve source provenance and the contracted default/max cursor lengths."""
    assert PdfLocator(1).page == 1
    assert TextLocator(1, 1).line_start == 1
    assert DocxLocator(("Policy",), 0, 0, 0, 0).block == 0
    assert ImageLocator(bbox=(0.0, 0.0, 1.0, 1.0)).page == 1
    assert Pagination().limit == 50
    assert len(Pagination(cursor="x" * 512).cursor or "") == 512
