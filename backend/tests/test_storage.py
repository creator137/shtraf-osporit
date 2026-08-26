from pathlib import Path

from app.services.document_service import build_storage_path, is_supported_document


def test_build_storage_path_does_not_use_untrusted_filename(tmp_path: Path) -> None:
    path = build_storage_path(
        case_id=42,
        filename="../../private/unsafe name.PDF",
        mime_type="application/pdf",
        storage_root=tmp_path,
    )

    assert path.parent == tmp_path / "cases" / "42"
    assert path.suffix == ".pdf"
    assert "unsafe" not in path.name
    assert ".." not in path.parts


def test_supported_document_types() -> None:
    assert is_supported_document("fine.pdf", "application/pdf")
    assert is_supported_document("fine.JPEG", None)
    assert is_supported_document(None, "image/png")
    assert not is_supported_document("fine.exe", "application/octet-stream")
