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
                r"(?:ПОСТАНОВЛЕНИЕ\s+)(\d{10,25})",
                r"(?:постановлени[ея]\s*(?:N|№|Nº)?\s*)(\d{10,25})",
                r"(?:N|№|Nº)\s*(\d{10,25})",
            ),
            notice_date=self._first(
                normalized,
                r"ПОСТАНОВЛЕНИЕ\s+\d{10,25}\s+(\d{2}\.\d{2}\.\d{4})",
                r"ПОСТАНОВЛЕНИЕ\s+\d{10,25}.{0,120}?(\d{2}\.\d{2}\.\d{4})",
                r"постановлени[ея].{0,80}?от\s*(\d{2}\.\d{2}\.\d{4})",
                r"(\d{2}\.\d{2}\.\d{4})",
            ),
            uin=self._first(
                normalized,
                r"(?:УИН|уникальный идентификатор начисления)\s*[:№N]?\s*(\d{20,25})",
                r"/uin/(\d{20,25})",
            ),
            fine_amount=self._amount(normalized),
            article=self._first(
                normalized,
                r"предусмотренного\s+((?:ч\.?\s*\d+\s*)?ст\.?\s*\d+(?:\.\d+)?)",
                r"((?:ч\.?\s*\d+\s*)?ст\.?\s*\d+(?:\.\d+)?)\s+КоАП",
            ),
            vehicle_plate=self._plate(
                normalized,
                r"государственный регистрационный знак\s*([АВЕКМНОРСТУХABEKMHOPCTYX0-9]{6,10})",
                r"Госномер\s*([АВЕКМНОРСТУХABEKMHOPCTYX0-9]{6,10})",
                r"\b([АВЕКМНОРСТУХABEKMHOPCTYX]\d{3}[АВЕКМНОРСТУХABEKMHOPCTYX]{2}\d{2,3})\b",
            ),
            violation_datetime=self._first(
                normalized,
                r"Время и место нарушения\s*(\d{2}\.\d{2}\.\d{4}).{0,40}?(\d{2}:\d{2})",
                r"(\d{2}\.\d{2}\.\d{4})\s+в\s+(\d{2}:\d{2})",
                r"(\d{2}\.\d{2}\.\d{4}\s+\d{2}:\d{2})",
            ),
            violation_place=self._first(
                normalized,
                r"Время и место нарушения.{0,80}?\d{2}:\d{2}\s+(.+?)(?:\s+©|\s+Яндекс|\s+Штраф выписан|$)",
                r"по адресу\s+(.{10,200}?)\s+водитель",
                r"(?:мест[оа]\s+(?:совершения|нарушения)\s*[:\-]?\s*)([^.]{10,200})",
            ),
            issuing_authority=self._first(
                normalized,
                r"Штраф выписан\s+(.+?)(?:\s+ГОС\s+услуги|\s+Установите|\s+https?://|$)",
            )
            or self._first(
                normalized,
                r"((?:ЦАФАП|ГИБДД|МВД).{0,120}?)(?:\s+ул\.|\s+Я,|\s+рассмотрев)",
            ),
        )

    def _first(self, text: str, *patterns: str) -> str | None:
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                groups = [item for item in match.groups() if item]
                return " ".join(groups).strip()
        return None

    def _plate(self, text: str, *patterns: str) -> str | None:
        value = self._first(text, *patterns)
        return value.replace(" ", "") if value is not None else None

    def _amount(self, text: str) -> int | None:
        for pattern in (
            r"(?:штраф|сумм[аы](?:\s+начисления)?)\s*[:\-]?\s*(\d[\d\s]*)\s*(?:руб|р\.?|₽)",
            r"штрафа\s+в\s+размере\s*(\d[\d\s]*)\s*(?:руб|р\.?|₽)",
        ):
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return int(match.group(1).replace(" ", ""))
        return None
