import asyncio
from dataclasses import dataclass
from pathlib import Path

import aiohttp
import pymupdf

from app.config import Settings


@dataclass(frozen=True)
class OcrResult:
    text: str


class OcrProvider:
    async def recognize(
        self,
        content: bytes,
        filename: str,
        mime_type: str | None,
    ) -> OcrResult:
        raise NotImplementedError


class DisabledOcrProvider(OcrProvider):
    async def recognize(
        self,
        content: bytes,
        filename: str,
        mime_type: str | None,
    ) -> OcrResult:
        raise RuntimeError("OCR provider is disabled")


class OcrSpaceProvider(OcrProvider):
    endpoint = "https://api.ocr.space/parse/image"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def recognize(
        self,
        content: bytes,
        filename: str,
        mime_type: str | None,
    ) -> OcrResult:
        files = [(content, filename, mime_type)]
        if (
            mime_type == "application/pdf"
            and len(content) > self.settings.ocr_max_file_size_bytes
        ):
            files = await asyncio.to_thread(
                self._render_pdf_pages, content, filename
            )

        results = [
            await self._recognize_file(file_content, file_name, file_mime_type)
            for file_content, file_name, file_mime_type in files
        ]
        return OcrResult(text="\n\n".join(result.text for result in results))

    async def _recognize_file(
        self,
        content: bytes,
        filename: str,
        mime_type: str | None,
    ) -> OcrResult:
        if len(content) > self.settings.ocr_max_file_size_bytes:
            limit_mb = self.settings.ocr_max_file_size_bytes / 1_000_000
            raise RuntimeError(
                f"Файл превышает лимит OCR.space Free ({limit_mb:g} МБ)"
            )
        configured_api_key = (
            self.settings.ocr_space_api_key.get_secret_value()
            if self.settings.ocr_space_api_key is not None
            else ""
        )
        api_key = configured_api_key or "helloworld"
        form = aiohttp.FormData()
        form.add_field("language", self.settings.ocr_space_language)
        form.add_field("isOverlayRequired", "false")
        form.add_field("scale", "true")
        form.add_field("OCREngine", "2")
        form.add_field(
            "file",
            content,
            filename=filename,
            content_type=mime_type or "application/octet-stream",
        )
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as client:
            async with client.post(
                self.endpoint,
                data=form,
                headers={"apikey": api_key},
            ) as response:
                if response.status >= 400:
                    raise RuntimeError(
                        f"OCR.space временно недоступен (HTTP {response.status})"
                    )
                try:
                    payload = await response.json(content_type=None)
                except (aiohttp.ContentTypeError, ValueError) as exc:
                    raise RuntimeError("OCR.space вернул некорректный ответ") from exc
        if payload.get("IsErroredOnProcessing"):
            message = payload.get("ErrorMessage") or payload.get("ErrorDetails")
            if isinstance(message, list):
                message = "; ".join(str(item) for item in message)
            raise RuntimeError(str(message or "OCR processing failed"))
        parsed_results = payload.get("ParsedResults") or []
        text = "\n".join(
            result.get("ParsedText", "")
            for result in parsed_results
            if isinstance(result, dict)
        ).strip()
        if not text:
            page_errors = [
                result.get("ErrorMessage") or result.get("ErrorDetails")
                for result in parsed_results
                if isinstance(result, dict)
                and (result.get("ErrorMessage") or result.get("ErrorDetails"))
            ]
            message = "; ".join(str(item) for item in page_errors if item)
            raise RuntimeError(message or "OCR.space не смог распознать текст")
        return OcrResult(text=text)

    def _render_pdf_pages(
        self, content: bytes, original_filename: str
    ) -> list[tuple[bytes, str, str]]:
        try:
            document = pymupdf.open(stream=content, filetype="pdf")
        except (pymupdf.FileDataError, RuntimeError) as exc:
            raise RuntimeError("Не удалось открыть PDF для распознавания") from exc

        with document:
            if document.page_count == 0:
                raise RuntimeError("PDF не содержит страниц")
            if document.page_count > self.settings.ocr_max_pdf_pages:
                raise RuntimeError(
                    "PDF содержит слишком много страниц: "
                    f"максимум {self.settings.ocr_max_pdf_pages}"
                )

            stem = Path(original_filename).stem or "document"
            return [
                (
                    self._render_page(document[page_index]),
                    f"{stem}-page-{page_index + 1}.jpg",
                    "image/jpeg",
                )
                for page_index in range(document.page_count)
            ]

    def _render_page(self, page: pymupdf.Page) -> bytes:
        for dpi, quality in ((150, 78), (130, 68), (110, 58), (90, 48)):
            pixmap = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csRGB, alpha=False)
            rendered = pixmap.tobytes("jpeg", jpg_quality=quality)
            if len(rendered) <= self.settings.ocr_max_file_size_bytes:
                return rendered
        raise RuntimeError("Страницу PDF не удалось сжать до лимита OCR.space")


def create_ocr_provider(settings: Settings) -> OcrProvider:
    if settings.ocr_provider == "ocrspace":
        return OcrSpaceProvider(settings)
    return DisabledOcrProvider()
