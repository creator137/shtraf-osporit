import re
from dataclasses import dataclass


@dataclass(frozen=True)
class FineNoticeFields:
    notice_number: str | None = None
    notice_date: str | None = None
    uin: str | None = None
    fine_amount: int | None = None
    article: str | None = None
    vehicle_plate: str | None = None
    violation_datetime: str | None = None
    violation_place: str | None = None
    issuing_authority: str | None = None


class FineNoticeExtractor:
    def extract(self, text: str) -> FineNoticeFields:
        normalized = " ".join(text.split())
        return FineNoticeFields(
            notice_number=self._first(
                normalized,
                r"(?:постановлени[ея]\s*(?:N|№)?\s*)([A-ZА-Я0-9\-\/]{4,})",
                r"(?:N|№)\s*([A-ZА-Я0-9\-\/]{4,})",
            ),
            notice_date=self._first(normalized, r"(\d{2}\.\d{2}\.\d{4})"),
            uin=self._first(normalized, r"(?:УИН|уникальный идентификатор начисления)\s*[:№N]?\s*(\d{20,25})"),
            fine_amount=self._amount(normalized),
            article=self._first(normalized, r"(ст\.?\s*\d+(?:\.\d+)?(?:\s*ч\.?\s*\d+)?)"),
            vehicle_plate=self._first(
                normalized,
                r"\b([АВЕКМНОРСТУХABEKMHOPCTYX]\d{3}[АВЕКМНОРСТУХABEKMHOPCTYX]{2}\d{2,3})\b",
            ),
            violation_datetime=self._first(
                normalized,
                r"(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2})",
            ),
            violation_place=self._first(
                normalized,
                r"(?:мест[оа]\s+(?:совершения|нарушения)\s*[:\-]?\s*)([^.]{10,200})",
            ),
            issuing_authority=self._first(
                normalized,
                r"((?:ЦАФАП|ГИБДД|МВД)[^.]{0,160})",
            ),
        )

    def _first(self, text: str, *patterns: str) -> str | None:
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _amount(self, text: str) -> int | None:
        match = re.search(
            r"(?:штраф|сумм[аы])\s*[:\-]?\s*(\d[\d\s]*)\s*(?:руб|р\.?)",
            text,
            flags=re.IGNORECASE,
        )
        if not match:
            return None
        return int(match.group(1).replace(" ", ""))
