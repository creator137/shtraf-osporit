from dataclasses import dataclass


@dataclass(frozen=True)
class Offer:
    code: str
    title: str
    description: str
    price: str
    icon: str


OFFERS = {
    "petition": Offer(
        code="petition",
        title="Ходатайство",
        description="Подготовка ходатайства ботом",
        price="99 ₽",
        icon="📝",
    ),
    "complaint": Offer(
        code="complaint",
        title="Жалоба",
        description="Подготовка жалобы ботом",
        price="299–990 ₽",
        icon="📄",
    ),
    "lawyer_support": Offer(
        code="lawyer_support",
        title="Сопровождение юристом",
        description="Консультация и сопровождение обжалования",
        price="от 990 ₽",
        icon="⚖️",
    ),
}
