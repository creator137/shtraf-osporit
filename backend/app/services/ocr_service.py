from dataclasses import dataclass

import aiohttp

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
        api_key = (
            self.settings.ocr_space_api_key.get_secret_value()
            if self.settings.ocr_space_api_key is not None
            else "helloworld"
        )
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
                payload = await response.json(content_type=None)
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
            raise RuntimeError("OCR returned empty text")
        return OcrResult(text=text)


def create_ocr_provider(settings: Settings) -> OcrProvider:
    if settings.ocr_provider == "ocrspace":
        return OcrSpaceProvider(settings)
    return DisabledOcrProvider()
