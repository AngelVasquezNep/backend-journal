"""Real local extraction/OCR and leased publication preserve provenance and reject unreadable data."""

from pathlib import Path

import pytest


@pytest.mark.parametrize(
    "filename,kind",
    [
        ("a/a-policy-1.txt", "text"),
        ("a/a-policy-2.pdf", "pdf"),
        ("a/a-policy-3.docx", "docx"),
        ("a/a-policy-4.png", "image"),
        ("a/a-policy-5.jpg", "image"),
        ("a/a-policy-6.pdf", "pdf"),
    ],
)
def test_supported_formats_extract_readable_text(
    corpus: Path, extractor, filename: str, kind: str
) -> None:
    """Use actual parsers/Tesseract and retain source kind/page/table/line provenance."""
    blocks = extractor.extract_path(corpus / filename)
    assert blocks and any("policy" in block.normalized_text.lower() for block in blocks)
    assert all(block.locator.kind == kind for block in blocks)
    assert [block.ordinal for block in blocks] == list(range(len(blocks)))
    assert all(block.source_offset_map for block in blocks)


@pytest.mark.parametrize(
    "filename",
    [
        "invalid/corrupt.pdf",
        "invalid/protected.pdf",
        "invalid/empty.txt",
        "invalid/not-utf8.txt",
        "invalid/mismatch.png",
    ],
)
def test_invalid_files_never_produce_readable_blocks(
    corpus: Path, extractor, filename: str
) -> None:
    """Reject corrupt/protected/empty/mismatched content with a typed safe processing error."""
    from taskify_knowledge.domain.errors import ApplicationError

    with pytest.raises(ApplicationError):
        extractor.extract_path(corpus / filename)


def test_abandoned_lease_is_fenced(
    knowledge_service, knowledge_worker, clock, admin_principal
) -> None:
    """Reclaim expired durable work; an obsolete lease cannot publish or terminally overwrite it."""
    from taskify_knowledge.application.upload import upload

    actor = admin_principal
    item = upload(
        knowledge_service,
        actor,
        "Policy",
        "policy.txt",
        "text/plain",
        iter([b"Company A policy grants 20 days."]),
    )
    first = knowledge_worker.claim()
    assert first is not None
    clock.advance(121)
    recovered = knowledge_worker.claim()
    assert recovered is not None and recovered.id == first.id
    assert recovered.lease_version > first.lease_version
    assert not knowledge_worker.process(first)
    assert knowledge_worker.process(recovered)
    with knowledge_service.store.transaction(actor.company_id) as transaction:
        assert transaction.item(item.item.id).active_revision_id is not None


def test_decoded_pixel_and_archive_limits_are_explicit(extractor, tmp_path) -> None:
    """Reject oversized decoded input from headers before allocation or archive expansion."""
    import io
    import struct
    import zipfile
    import zlib

    from taskify_knowledge.domain.errors import ApplicationError

    def png_chunk(kind, payload):
        """Build a valid PNG envelope without allocating its declared large raster."""
        return (
            struct.pack(">I", len(payload))
            + kind
            + payload
            + struct.pack(">I", zlib.crc32(kind + payload))
        )

    image = tmp_path / "oversized.png"
    header = struct.pack(">IIBBBBB", 40000001, 1, 8, 0, 0, 0, 0)
    image.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", header)
        + png_chunk(b"IDAT", zlib.compress(b"\x00"))
        + png_chunk(b"IEND", b"")
    )
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr("word/document.xml", b"x")
        output.writestr("[Content_Types].xml", b"x")
    data = bytearray(archive.getvalue())
    central = data.index(b"PK\x01\x02")
    struct.pack_into("<I", data, central + 24, 256 * 1024 * 1024 + 1)
    document = tmp_path / "oversized.docx"
    document.write_bytes(data)
    for original in (image, document):
        with pytest.raises(ApplicationError) as error:
            extractor.extract_path(original)
        assert error.value.code == "resource_limit"


def test_normalization_preserves_original_and_chunk_provenance(extractor, tmp_path) -> None:
    """NFC/newline/BOM normalization preserves exact bytes and maps bounded chunks to source lines."""
    import hashlib
    from uuid import uuid4

    from taskify_knowledge.adapters.outbound.chunking import TokenChunker
    from taskify_knowledge.domain.block import ExtractedBlock

    original = tmp_path / "unicode.txt"
    content = ("\ufeffCafe\u0301\r\n" + "Company policy text.\r\n" * 500).encode("utf-8")
    original.write_bytes(content)
    before = hashlib.sha256(content).digest()
    extracted = extractor.extract_path(original)
    assert extracted[0].normalized_text.startswith("Café\n")
    value = extracted[0]
    block = ExtractedBlock(
        id=uuid4(),
        company_id=uuid4(),
        revision_id=uuid4(),
        ordinal=value.ordinal,
        normalized_text=value.normalized_text,
        locator=value.locator,
        source_offset_map=value.source_offset_map,
        extractor_version=value.extractor_version,
    )
    chunks = TokenChunker().split((block,))
    assert len(chunks) > 1
    assert all(1 <= chunk.token_count <= 800 for chunk in chunks)
    assert all(
        chunk.locator.kind == "text" and chunk.locator.line_start <= chunk.locator.line_end
        for chunk in chunks
    )
    assert list(value.source_offset_map) == sorted(value.source_offset_map)
    assert hashlib.sha256(original.read_bytes()).digest() == before


def test_orphan_cleanup_keeps_referenced_and_inflight_originals(
    knowledge_service, admin_principal
) -> None:
    """Aging orphan cleanup removes only complete unreferenced objects, with acceptance serialization."""
    import os

    from taskify_knowledge.application.reconcile_storage import reconcile
    from taskify_knowledge.application.upload import upload

    orphan = knowledge_service.storage.stage(
        "orphan.txt", "text/plain", iter([b"Unreferenced policy."])
    )
    accepted = upload(
        knowledge_service,
        admin_principal,
        "Kept policy",
        "kept.txt",
        "text/plain",
        iter([b"Referenced policy."]),
    )
    with knowledge_service.store.transaction(admin_principal.company_id) as transaction:
        revision = transaction.revision(accepted.candidate_revision.id)
    assert revision is not None
    old = knowledge_service.clock.now().timestamp() - 90000
    for key in (orphan.storage_key, revision.storage_key):
        os.utime(knowledge_service.storage.path_for(key), (old, old))
    partial = knowledge_service.storage.path_for("1" * 32)
    partial.write_bytes(b"Writable staging remains private.")
    os.utime(partial, (old, old))
    with knowledge_service.storage.protect("1" * 32):
        assert reconcile(knowledge_service) == 1
        assert partial.exists()
    assert not knowledge_service.storage.path_for(orphan.storage_key).exists()
    assert knowledge_service.storage.path_for(revision.storage_key).exists()
    assert partial.exists()


def test_lifecycle_cleanup_cannot_restore_a_superseded_original(
    knowledge_service, knowledge_worker, admin_principal, clock
) -> None:
    """Retire only unavailable old bytes/derived data while retaining immutable historical metadata."""
    from taskify_knowledge.application.maintain_knowledge import replace_original
    from taskify_knowledge.application.read_knowledge import read
    from taskify_knowledge.application.reconcile_storage import reconcile
    from taskify_knowledge.application.upload import upload

    first = upload(
        knowledge_service,
        admin_principal,
        "Policy",
        "before.txt",
        "text/plain",
        iter([b"Company policy grants 20 days."]),
    )
    assert knowledge_worker.run_once()
    current = read(knowledge_service, admin_principal, first.item.id)
    old_revision = current.current_revision
    replacement = replace_original(
        knowledge_service,
        admin_principal,
        current.item.id,
        current.item.version,
        "after.txt",
        "text/plain",
        iter([b"Company policy grants 25 days."]),
    )
    assert knowledge_worker.run_once()
    clock.advance(90000)
    assert reconcile(knowledge_service) == 1
    assert not knowledge_service.storage.path_for(old_revision.storage_key).exists()
    with knowledge_service.store.transaction(admin_principal.company_id) as transaction:
        old = transaction.revision(old_revision.id)
        new = transaction.revision(replacement.candidate_revision.id)
        assert old.state == "superseded" and old.sha256 == old_revision.sha256
        assert new.state == "ready" and knowledge_service.storage.path_for(new.storage_key).exists()
    assert reconcile(knowledge_service) == 0


def test_revoked_login_after_staging_rolls_back_upload_and_replacement(
    knowledge_service, knowledge_worker, admin_principal
) -> None:
    """Final online authorization rejects credentials lost during long upload/inspection without changing valid data."""
    from taskify_knowledge.application.maintain_knowledge import replace_original
    from taskify_knowledge.application.read_knowledge import read
    from taskify_knowledge.application.upload import upload
    from taskify_knowledge.domain.errors import AuthenticationRequired

    def revoked():
        """Represent an online Identity rejection at the acceptance transaction checkpoint."""
        raise AuthenticationRequired()

    with pytest.raises(AuthenticationRequired):
        upload(
            knowledge_service,
            admin_principal,
            "Rejected",
            "reject.txt",
            "text/plain",
            iter([b"Company rejected policy."]),
            reauthorize=revoked,
        )
    with knowledge_service.store.transaction(admin_principal.company_id) as transaction:
        from taskify_knowledge.domain.values import Pagination

        assert not transaction.page(admin_principal, Pagination()).items
    original = upload(
        knowledge_service,
        admin_principal,
        "Kept",
        "kept.txt",
        "text/plain",
        iter([b"Company kept policy."]),
    )
    assert knowledge_worker.run_once()
    ready = read(knowledge_service, admin_principal, original.item.id)
    with pytest.raises(AuthenticationRequired):
        replace_original(
            knowledge_service,
            admin_principal,
            ready.item.id,
            ready.item.version,
            "rejected.txt",
            "text/plain",
            iter([b"Company rejected replacement."]),
            reauthorize=revoked,
        )
    unchanged = read(knowledge_service, admin_principal, ready.item.id)
    assert (
        unchanged.item.version == ready.item.version
        and unchanged.current_revision.id == ready.current_revision.id
    )
