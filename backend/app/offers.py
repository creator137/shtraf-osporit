from dataclasses import dataclass


@dataclass(frozen=True)
class Offer:
    code: str
    title: str
    description: str
    price: str
    icon: str


OFFERS = {
    "fine_check": Offer(
        code="fine_check",
        title="Проверка штрафа",
        description="Анализ перспектив с помощью ИИ",
        price="0–99 ₽",
        icon="🔎",
    ),
    "complaint": Offer(
        code="complaint",
        title="Жалоба",
        description="Готовый пакет документов",
        price="299–990 ₽",
        icon="📄",
    ),
    "turnkey": Offer(
        code="turnkey",
        title="Под ключ",
        description="Сопровождение обжалования",
        price="990–2 990 ₽",
        icon="⚖️",
    ),
}
