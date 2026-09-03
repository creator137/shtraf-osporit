from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from enum import Enum
from typing import Literal

RULES_VERSION = "2026-08-28"
NEXT_RULES_VERSION = "2026-09-01"
NEXT_RULES_EFFECTIVE_FROM = date(2026, 9, 1)


class EvidenceStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    NEEDED = "NEEDED"
    VERIFY = "VERIFY"


@dataclass(frozen=True)
class LegalContext:
    article: str | None = None
    ocr_text: str | None = None
    violation_place: str | None = None
    speed_related: bool = False
    parking_related: bool = False
    sign_related: bool = False
    technical_related: bool = False


def _normalize(text: str | None) -> str:
    return " ".join((text or "").casefold().split())


def build_context(
    article: str | None = None,
    ocr_text: str | None = None,
    violation_place: str | None = None,
) -> LegalContext:
    normalized_article = _normalize(article)
    normalized_text = _normalize(ocr_text)
    normalized_place = _normalize(violation_place)
    combined = " ".join(
        part for part in (normalized_article, normalized_text, normalized_place) if part
    )
    speed_related = any(
        marker in combined
        for marker in (
            "12.9",
            "скорост",
            "превышен",
            "превышени",
            "скорость",
            "скоростью",
        )
    )
    parking_related = any(
        marker in combined
        for marker in (
            "парков",
            "стоянк",
            "остановк",
            "парковоч",
        )
    )
    sign_related = any(
        marker in combined
        for marker in (
            "знак",
            "разметк",
            "запрещ",
            "уступ",
        )
    ) or "12.16" in combined
    technical_related = any(
        marker in combined
        for marker in (
            "камера",
            "камер",
            "комплекс",
            "автоматич",
            "фиксац",
            "радар",
            "измеритель",
        )
    )
    if parking_related or sign_related:
        speed_related = False
    return LegalContext(
        article=article,
        ocr_text=ocr_text,
        violation_place=violation_place,
        speed_related=speed_related,
        parking_related=parking_related,
        sign_related=sign_related,
        technical_related=technical_related,
    )


def _appeal_deadline(received_at: date) -> date:
    return received_at + timedelta(days=10)


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    value = value.strip()
    date_part = value.split(maxsplit=1)[0].split("T", maxsplit=1)[0].rstrip(",")
    for pattern in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            if pattern == "%d.%m.%Y":
                day, month, year = date_part.split(".")
                return date(int(year), int(month), int(day))
            return date.fromisoformat(date_part)
        except ValueError:
            continue
    return None


def format_date(value: date | None) -> str | None:
    return value.strftime("%d.%m.%Y") if value else None


def normalize_date_answer(value: str | None) -> str | None:
    parsed = parse_date(value)
    return format_date(parsed) if parsed else (value.strip() if value else None)


@dataclass(frozen=True)
class QuestionOption:
    value: str
    label: str


@dataclass(frozen=True)
class LegalQuestion:
    id: str
    text: str
    options: tuple[QuestionOption, ...]
    depends_on: tuple[str, tuple[str, ...]] | None = None
    scopes: tuple[str, ...] = ("always",)
    input_kind: Literal["choice", "date", "text"] = "choice"

    def is_relevant(self, answers: dict[str, str], context: LegalContext) -> bool:
        if self.depends_on is None:
            has_dependency = True
        else:
            question_id, accepted_answers = self.depends_on
            has_dependency = answers.get(question_id) in accepted_answers
        if not has_dependency:
            return False
        if "always" in self.scopes:
            return True
        context_flags = {
            "speed_related": context.speed_related,
            "parking_related": context.parking_related,
            "sign_related": context.sign_related,
            "technical_related": context.technical_related,
        }
        return any(context_flags.get(scope, False) for scope in self.scopes)


@dataclass(frozen=True)
class LegalRule:
    code: str
    title: str
    direction: str
    legal_basis: str
    required_evidence: tuple[str, ...]
    source_ids: tuple[str, ...]
    evidence_question_id: str | None = None
    evidence_status: EvidenceStatus = EvidenceStatus.NEEDED


LEGAL_SOURCES = (
    {
        "id": "koap-rf",
        "title": "Кодекс Российской Федерации об административных правонарушениях",
        "reference": "Статьи 1.5, 2.6.1, 2.7, 24.5, глава 26 и глава 30",
        "effective_note": "Применимая редакция должна определяться по дате нарушения.",
        "document_available": False,
    },
    {
        "id": "plenum-vs-20",
        "title": "Постановление Пленума Верховного Суда РФ от 25.06.2019 № 20",
        "reference": "О вопросах судебной практики по делам главы 12 КоАП РФ",
        "effective_note": "Источник предоставлен заказчиком; юридические обновления проверяются отдельно.",
        "document_available": True,
    },
)


RULE_VERSIONS = (
    {
        "version": RULES_VERSION,
        "effective_from": "28.08.2026",
        "title": "Текущая редакция правил",
    },
    {
        "version": NEXT_RULES_VERSION,
        "effective_from": format_date(NEXT_RULES_EFFECTIVE_FROM) or "01.09.2026",
        "title": "Редакция с 01.09.2026",
    },
)


QUESTIONS = (
    LegalQuestion(
        id="appeal_received_at",
        text="Когда вы получили постановление? Отправьте дату в формате ДД.ММ.ГГГГ.",
        options=(),
        input_kind="date",
    ),
    LegalQuestion(
        id="appeal_delay_reason",
        text="Почему срок обжалования уже пропущен?",
        options=(
            QuestionOption("late_receipt", "Получил поздно"),
            QuestionOption("illness", "Болезнь или лечение"),
            QuestionOption("travel", "Командировка или поездка"),
            QuestionOption("other", "Другая причина"),
        ),
    ),
    LegalQuestion(
        id="complaint_recipient",
        text=(
            "Не удалось определить адресата из постановления. Укажите полное "
            "наименование суда, вышестоящего органа или должностного лица, куда "
            "будет направлена жалоба."
        ),
        options=(),
        input_kind="text",
    ),
    LegalQuestion(
        id="correspondence_address",
        text=(
            "Укажите адрес для корреспонденции. "
            "Он будет использован в проекте жалобы."
        ),
        options=(),
        input_kind="text",
    ),
    LegalQuestion(
        id="driver",
        text="Кто фактически пользовался автомобилем в момент нарушения?",
        options=(
            QuestionOption("owner", "Я"),
            QuestionOption("other", "Другой человек"),
            QuestionOption("sold", "Автомобиль был продан"),
            QuestionOption("lost", "Автомобиль выбыл из владения"),
        ),
    ),
    LegalQuestion(
        id="driver_docs",
        text="Есть документы или объяснение, подтверждающие передачу автомобиля другому человеку?",
        options=(QuestionOption("yes", "Да"), QuestionOption("no", "Нет")),
        depends_on=("driver", ("other",)),
    ),
    LegalQuestion(
        id="sale_docs",
        text="Есть договор купли-продажи или акт передачи, оформленный до даты нарушения?",
        options=(QuestionOption("yes", "Да"), QuestionOption("no", "Нет")),
        depends_on=("driver", ("sold",)),
    ),
    LegalQuestion(
        id="possession_docs",
        text="Есть документы о выбытии автомобиля из владения до даты нарушения?",
        options=(QuestionOption("yes", "Да"), QuestionOption("no", "Нет")),
        depends_on=("driver", ("lost",)),
    ),
    LegalQuestion(
        id="vehicle_photo",
        text="Автомобиль на фотографии в постановлении соответствует вашему автомобилю?",
        options=(
            QuestionOption("yes", "Да"),
            QuestionOption("different", "Нет, другой автомобиль"),
            QuestionOption("unclear", "Невозможно определить"),
            QuestionOption("no_photo", "Фотографии нет"),
        ),
    ),
    LegalQuestion(
        id="plate_photo",
        text="Госномер на фотографии совпадает с номером в постановлении?",
        options=(
            QuestionOption("yes", "Да"),
            QuestionOption("different", "Нет, номер отличается"),
            QuestionOption("unreadable", "Номер не читается"),
            QuestionOption("no_photo", "Фотографии нет"),
        ),
    ),
    LegalQuestion(
        id="place_time_match",
        text="Место и время нарушения в постановлении совпадают с фактическими обстоятельствами?",
        options=(
            QuestionOption("yes", "Да"),
            QuestionOption("wrong_place", "Нет, место указано неверно"),
            QuestionOption("wrong_time", "Нет, время указано неверно"),
            QuestionOption("unclear", "Нужно проверить"),
        ),
    ),
    LegalQuestion(
        id="place_time_docs",
        text="Есть подтверждение вашего местоположения или маршрута в момент нарушения?",
        options=(QuestionOption("yes", "Да"), QuestionOption("no", "Нет")),
        depends_on=("place_time_match", ("wrong_place", "wrong_time")),
    ),
    LegalQuestion(
        id="speed",
        text="Вы оспариваете указанную в постановлении скорость?",
        options=(
            QuestionOption("no", "Нет"),
            QuestionOption("dispute", "Да, скорость определена неверно"),
            QuestionOption("not_speed", "Штраф не связан со скоростью"),
        ),
        scopes=("speed_related",),
    ),
    LegalQuestion(
        id="speed_docs",
        text="Есть видеорегистратор, GPS-трек, телематика или другие данные о скорости?",
        options=(QuestionOption("yes", "Да"), QuestionOption("no", "Нет")),
        depends_on=("speed", ("dispute",)),
        scopes=("speed_related",),
    ),
    LegalQuestion(
        id="camera",
        text="Есть конкретные сомнения в работе комплекса фиксации?",
        options=(
            QuestionOption("none", "Нет"),
            QuestionOption("calibration", "Нужно проверить поверку"),
            QuestionOption("manual", "Комплекс мог работать не автоматически"),
            QuestionOption("other", "Есть другие технические сомнения"),
        ),
        scopes=("technical_related", "speed_related", "sign_related", "parking_related"),
    ),
    LegalQuestion(
        id="sign",
        text="Есть замечания к дорожному знаку, на котором основан штраф?",
        options=(
            QuestionOption("none", "Нет"),
            QuestionOption("absent", "Знак отсутствовал"),
            QuestionOption("hidden", "Знак был закрыт или не виден"),
            QuestionOption("unclear", "Нужно проверить"),
        ),
        scopes=("sign_related", "parking_related"),
    ),
    LegalQuestion(
        id="sign_docs",
        text="Есть фото, видео или иные сведения о состоянии знака в дату нарушения?",
        options=(QuestionOption("yes", "Да"), QuestionOption("no", "Нет")),
        depends_on=("sign", ("absent", "hidden")),
        scopes=("sign_related", "parking_related"),
    ),
    LegalQuestion(
        id="marking",
        text="Есть замечания к дорожной разметке, если она важна для штрафа?",
        options=(
            QuestionOption("none", "Нет"),
            QuestionOption("absent", "Разметки не было"),
            QuestionOption("unreadable", "Разметка была не видна"),
            QuestionOption("conflict", "Разметка противоречила знаку"),
        ),
        scopes=("sign_related", "parking_related"),
    ),
    LegalQuestion(
        id="marking_docs",
        text="Есть фото, видео или схема участка с разметкой?",
        options=(QuestionOption("yes", "Да"), QuestionOption("no", "Нет")),
        depends_on=("marking", ("absent", "unreadable", "conflict")),
        scopes=("sign_related", "parking_related"),
    ),
    LegalQuestion(
        id="owner_data_match",
        text="Данные собственника или адресата в постановлении указаны верно?",
        options=(
            QuestionOption("yes", "Да"),
            QuestionOption("wrong", "Нет, есть ошибка"),
            QuestionOption("unclear", "Нужно проверить"),
        ),
    ),
    LegalQuestion(
        id="owner_data_docs",
        text="Есть документы с корректными данными собственника или адресата?",
        options=(QuestionOption("yes", "Да"), QuestionOption("no", "Нет")),
        depends_on=("owner_data_match", ("wrong",)),
    ),
    LegalQuestion(
        id="previous_resolution",
        text="Есть сведения, что этот штраф уже отменён, исполнен или связан с другим решением?",
        options=(
            QuestionOption("no", "Нет"),
            QuestionOption("paid", "Штраф уже исполнен"),
            QuestionOption("cancelled", "Постановление уже отменялось"),
            QuestionOption("related", "Есть связанное решение"),
        ),
    ),
    LegalQuestion(
        id="previous_resolution_docs",
        text="Можете предоставить подтверждение оплаты, отмены или связанного решения?",
        options=(QuestionOption("yes", "Да"), QuestionOption("no", "Нет")),
        depends_on=("previous_resolution", ("paid", "cancelled", "related")),
    ),
    LegalQuestion(
        id="article_qualification",
        text="Есть сомнения, что статья или квалификация нарушения указаны верно?",
        options=(
            QuestionOption("no", "Нет"),
            QuestionOption("yes", "Да, нужна юридическая проверка"),
            QuestionOption("unclear", "Не уверен"),
        ),
    ),
    LegalQuestion(
        id="duplicate",
        text="Есть другое постановление за тот же автомобиль, место и время?",
        options=(
            QuestionOption("no", "Нет"),
            QuestionOption("yes", "Да"),
            QuestionOption("unclear", "Не уверен"),
        ),
    ),
    LegalQuestion(
        id="duplicate_docs",
        text="Можете предоставить второе постановление для сравнения?",
        options=(QuestionOption("yes", "Да"), QuestionOption("no", "Нет")),
        depends_on=("duplicate", ("yes",)),
    ),
    LegalQuestion(
        id="emergency",
        text="Нарушение было связано с необходимостью избежать непосредственной опасности?",
        options=(QuestionOption("no", "Нет"), QuestionOption("yes", "Да")),
    ),
    LegalQuestion(
        id="emergency_docs",
        text="Есть подтверждения чрезвычайных обстоятельств: запись, свидетели или документы?",
        options=(QuestionOption("yes", "Да"), QuestionOption("no", "Нет")),
        depends_on=("emergency", ("yes",)),
    ),
)


RULES = (
    LegalRule(
        "A01",
        "Автомобилем управлял другой человек",
        "Проверить, подтверждается ли передача автомобиля другому лицу на момент фиксации.",
        "Ч. 2 ст. 2.6.1 КоАП РФ; п. 27 Постановления Пленума ВС РФ № 20.",
        ("Полис ОСАГО", "договор пользования или аренды", "объяснение водителя"),
        ("koap-rf", "plenum-vs-20"),
        evidence_question_id="driver_docs",
    ),
    LegalRule(
        "A02",
        "Автомобиль продан до нарушения",
        "Проверить дату фактической передачи автомобиля новому собственнику.",
        "Ч. 2 ст. 2.6.1 КоАП РФ; п. 27 Постановления Пленума ВС РФ № 20.",
        ("Договор купли-продажи", "акт передачи", "подтверждение оплаты или переписка"),
        ("koap-rf", "plenum-vs-20"),
    ),
    LegalRule(
        "A03",
        "Автомобиль выбыл из владения до нарушения",
        "Проверить, подтверждается ли утрата владения автомобилем до момента фиксации.",
        "Ч. 2 ст. 2.6.1 КоАП РФ; ст. 24.5, 26.1 и 26.2 КоАП РФ.",
        ("Заявление в полицию", "акт изъятия или эвакуации", "иные документы о выбытии"),
        ("koap-rf", "plenum-vs-20"),
        evidence_question_id="possession_docs",
    ),
    LegalRule(
        "A04",
        "Возможна ошибка распознавания госномера",
        "Сопоставить номер в постановлении, читаемый номер на фотографии и автомобиль.",
        "Ст. 26.1, 26.2 и 26.11 КоАП РФ.",
        ("Материалы фотофиксации", "документы на автомобиль"),
        ("koap-rf",),
        evidence_question_id="plate_photo",
    ),
    LegalRule(
        "A05",
        "На фотографии другой автомобиль",
        "Проверить признаки автомобиля на фотографии: марку, модель, цвет и госномер.",
        "Ст. 26.1, 26.2 и 26.11 КоАП РФ.",
        ("Материалы фотофиксации", "документы или фотографии автомобиля пользователя"),
        ("koap-rf",),
        evidence_question_id="vehicle_photo",
    ),
    LegalRule(
        "A06",
        "Материалы фиксации отсутствуют или не позволяют проверить событие",
        "Проверить, достаточно ли материалов фиксации для подтверждения события и автомобиля.",
        "Ст. 26.1, 26.2 и 26.11 КоАП РФ.",
        ("Полный комплект материалов фиксации", "фотографии постановления", "сведения о месте и времени"),
        ("koap-rf",),
        evidence_status=EvidenceStatus.VERIFY,
    ),
    LegalRule(
        "A07",
        "Возможна ошибка определения скорости",
        "Сопоставить данные комплекса с независимыми объективными сведениями о скорости.",
        "Ст. 26.2, 26.8 и 26.11 КоАП РФ.",
        ("Видеорегистратор", "GPS-трек", "телематические данные"),
        ("koap-rf",),
        evidence_question_id="speed_docs",
    ),
    LegalRule(
        "A08",
        "Неверно указаны место или время нарушения",
        "Сопоставить место и время в постановлении с маршрутом, документами и материалами фиксации.",
        "Ст. 26.1, 26.2 и 26.11 КоАП РФ.",
        ("Маршрут или геоданные", "видеозапись", "чеки, парковочные или иные подтверждения"),
        ("koap-rf",),
        evidence_question_id="place_time_docs",
    ),
    LegalRule(
        "A11",
        "Требуется проверка применения технического средства",
        "Истребовать сведения о комплексе, месте установки и условиях его применения.",
        "Ст. 26.8 КоАП РФ.",
        ("Идентификатор комплекса", "материалы фиксации", "сведения о месте установки"),
        ("koap-rf", "plenum-vs-20"),
        evidence_status=EvidenceStatus.VERIFY,
    ),
    LegalRule(
        "A12",
        "Требуется проверка поверки измерительного средства",
        "Истребовать сведения об утверждении типа и действующей поверке конкретного комплекса.",
        "Ст. 26.8 КоАП РФ в редакции, применимой на дату нарушения.",
        ("Тип и идентификатор комплекса", "свидетельство или сведения о поверке"),
        ("koap-rf",),
        evidence_status=EvidenceStatus.VERIFY,
    ),
    LegalRule(
        "A13",
        "Требуется проверка автоматического режима фиксации",
        "Установить, работал ли комплекс без непосредственного воздействия человека.",
        "Постановление Пленума ВС РФ № 20.",
        ("Сведения о режиме работы комплекса", "материалы фиксации"),
        ("plenum-vs-20",),
        evidence_status=EvidenceStatus.VERIFY,
    ),
    LegalRule(
        "A09",
        "Дорожный знак отсутствовал или не был виден",
        "Проверить наличие и видимость знака по направлению движения в дату нарушения.",
        "Ст. 26.1, 26.2 и 26.11 КоАП РФ.",
        ("Фото или видео", "координаты и направление движения", "схема организации движения"),
        ("koap-rf",),
        evidence_question_id="sign_docs",
    ),
    LegalRule(
        "A10",
        "Дорожная разметка отсутствовала или была не видна",
        "Проверить состояние разметки и её соответствие знакам на участке нарушения.",
        "Ст. 26.1, 26.2 и 26.11 КоАП РФ.",
        ("Фото или видео участка", "схема организации движения", "координаты и направление движения"),
        ("koap-rf",),
        evidence_question_id="marking_docs",
    ),
    LegalRule(
        "A14",
        "Неверно указаны данные собственника или адресата",
        "Проверить корректность данных лица, которому вынесено постановление.",
        "Ст. 26.1, 26.2, 28.2 и 29.10 КоАП РФ.",
        ("Паспортные или регистрационные данные", "СТС или ПТС", "копия постановления"),
        ("koap-rf",),
        evidence_question_id="owner_data_docs",
    ),
    LegalRule(
        "A15",
        "Нужна проверка ранее отменённого, исполненного или связанного постановления",
        "Сопоставить постановление с подтверждением оплаты, отмены или другим связанным решением.",
        "Ст. 24.5, 31.7 и 30.7 КоАП РФ.",
        ("Квитанция или платёжный документ", "решение об отмене", "связанное постановление"),
        ("koap-rf",),
        evidence_question_id="previous_resolution_docs",
    ),
    LegalRule(
        "A16",
        "Возможно повторное наказание за один факт",
        "Сопоставить оба постановления по времени, месту, составу и материалам фиксации.",
        "Ст. 30.7 КоАП РФ в редакции, применимой к делу.",
        ("Оба постановления", "материалы фиксации по каждому постановлению"),
        ("koap-rf",),
        evidence_question_id="duplicate_docs",
    ),
    LegalRule(
        "A17",
        "Возможна крайняя необходимость",
        "Проверить, существовала ли непосредственная опасность и нельзя ли было устранить её иначе.",
        "Ст. 2.7 КоАП РФ.",
        ("Видео или фотографии", "свидетельские показания", "подтверждающие документы"),
        ("koap-rf",),
        evidence_question_id="emergency_docs",
    ),
    LegalRule(
        "A18",
        "Требуется юридическая проверка статьи или квалификации нарушения",
        "Передать юристу проверку применённой статьи, состава и квалификации нарушения.",
        "Ст. 1.5, 24.5, 26.1 и 30.7 КоАП РФ.",
        ("Постановление", "описание обстоятельств", "материалы фиксации"),
        ("koap-rf", "plenum-vs-20"),
        evidence_status=EvidenceStatus.VERIFY,
    ),
)


def select_rules_version_for_date(violation_date: date | None) -> str:
    if violation_date is not None and violation_date >= NEXT_RULES_EFFECTIVE_FROM:
        return NEXT_RULES_VERSION
    return RULES_VERSION


def is_speed_notice(article: str | None, context: LegalContext | None = None) -> bool | None:
    normalized = _normalize(article)
    if not normalized:
        return None
    if context is not None and not context.speed_related:
        return False
    if context is not None and context.parking_related and "12.9" not in normalized:
        return False
    return "12.9" in normalized or "скорост" in normalized


def get_next_question(
    answers: dict[str, str],
    notice_article: str | None = None,
    ocr_text: str | None = None,
    violation_place: str | None = None,
) -> LegalQuestion | None:
    context = build_context(notice_article, ocr_text, violation_place)
    appeal_received = parse_date(answers.get("appeal_received_at"))
    appeal_overdue = bool(
        appeal_received is not None
        and datetime.now(UTC).date() > _appeal_deadline(appeal_received)
    )
    if appeal_received is None and "appeal_received_at" not in answers:
        return next(
            question for question in QUESTIONS if question.id == "appeal_received_at"
        )
    if appeal_overdue and "appeal_delay_reason" not in answers:
        return next(
            question for question in QUESTIONS if question.id == "appeal_delay_reason"
        )
    if "complaint_recipient" not in answers:
        return next(
            question for question in QUESTIONS if question.id == "complaint_recipient"
        )
    if "correspondence_address" not in answers:
        return next(
            question for question in QUESTIONS if question.id == "correspondence_address"
        )
    return next(
        (
            question
            for question in QUESTIONS
            if question.is_relevant(
                answers,
                context,
            )
            and question.id not in answers
            and not (
                question.id == "appeal_delay_reason" and not appeal_overdue
            )
            and not (
                question.id in {"speed", "speed_docs"}
                and is_speed_notice(notice_article, context) is False
            )
        ),
        None,
    )


def get_question(question_id: str) -> LegalQuestion | None:
    return next((question for question in QUESTIONS if question.id == question_id), None)


def answer_label(question_id: str, value: str) -> str:
    question = get_question(question_id)
    if question is None:
        return value
    option = next((item for item in question.options if item.value == value), None)
    return option.label if option else value


def serialize_rule(rule: LegalRule) -> dict[str, object]:
    return asdict(rule)


def evaluate_rules(
    answers: dict[str, str],
    notice_article: str | None = None,
    ocr_text: str | None = None,
    violation_place: str | None = None,
) -> list[dict[str, object]]:
    context = build_context(notice_article, ocr_text, violation_place)
    matches: list[tuple[str, EvidenceStatus]] = []
    if answers.get("driver") == "other":
        matches.append(("A01", _evidence(answers, "driver_docs")))
    if answers.get("driver") == "sold":
        matches.append(("A02", _evidence(answers, "sale_docs")))
    if answers.get("driver") == "lost":
        matches.append(("A03", _evidence(answers, "possession_docs")))
    if answers.get("plate_photo") in {"different", "unreadable"}:
        matches.append(("A04", EvidenceStatus.NEEDED))
    if answers.get("vehicle_photo") == "different":
        matches.append(("A05", EvidenceStatus.NEEDED))
    if answers.get("vehicle_photo") == "no_photo" or answers.get("plate_photo") == "no_photo":
        matches.append(("A06", EvidenceStatus.VERIFY))
    if (
        answers.get("speed") == "dispute"
        and is_speed_notice(notice_article, context) is not False
    ):
        matches.append(("A07", _evidence(answers, "speed_docs")))
    if answers.get("place_time_match") in {"wrong_place", "wrong_time"}:
        matches.append(("A08", _evidence(answers, "place_time_docs")))
    if answers.get("camera") == "other":
        matches.append(("A11", EvidenceStatus.VERIFY))
    if answers.get("camera") == "calibration":
        matches.append(("A12", EvidenceStatus.VERIFY))
    if answers.get("camera") == "manual":
        matches.append(("A13", EvidenceStatus.VERIFY))
    if answers.get("sign") in {"absent", "hidden"}:
        matches.append(("A09", _evidence(answers, "sign_docs")))
    if answers.get("marking") in {"absent", "unreadable", "conflict"}:
        matches.append(("A10", _evidence(answers, "marking_docs")))
    if answers.get("owner_data_match") == "wrong":
        matches.append(("A14", _evidence(answers, "owner_data_docs")))
    if answers.get("previous_resolution") in {"paid", "cancelled", "related"}:
        matches.append(("A15", _evidence(answers, "previous_resolution_docs")))
    if answers.get("duplicate") == "yes":
        matches.append(("A16", _evidence(answers, "duplicate_docs")))
    if answers.get("emergency") == "yes":
        matches.append(("A17", _evidence(answers, "emergency_docs")))
    if answers.get("article_qualification") in {"yes", "unclear"}:
        matches.append(("A18", EvidenceStatus.VERIFY))

    rules_by_code = {rule.code: rule for rule in RULES}
    return [
        {
            **serialize_rule(rules_by_code[code]),
            "evidence_status": evidence.value,
            "evidence_items": _evidence_items(rules_by_code[code], evidence),
            "reasons": _rule_reasons(code, answers),
        }
        for code, evidence in matches
    ]


def _evidence(answers: dict[str, str], question_id: str) -> EvidenceStatus:
    return (
        EvidenceStatus.AVAILABLE
        if answers.get(question_id) == "yes"
        else EvidenceStatus.NEEDED
    )


def _evidence_items(rule: LegalRule, status: EvidenceStatus) -> list[dict[str, str]]:
    return [{"name": item, "status": status.value} for item in rule.required_evidence]


def _rule_reasons(code: str, answers: dict[str, str]) -> list[str]:
    reasons = {
        "A01": "Вы указали, что автомобилем управлял другой человек.",
        "A02": "Вы указали, что автомобиль был продан до нарушения.",
        "A03": "Вы указали, что автомобиль выбыл из владения до нарушения.",
        "A04": "Есть сомнения в читаемости или совпадении госномера.",
        "A05": "На фотографии не совпадает автомобиль.",
        "A06": "Материалы фиксации отсутствуют или не позволяют проверить событие.",
        "A07": "Вы оспариваете указанную скорость.",
        "A08": "Есть сомнения в месте или времени нарушения.",
        "A09": "Есть замечания к знаку или его видимости.",
        "A10": "Есть замечания к дорожной разметке.",
        "A11": "Есть сомнения в применении комплекса фиксации.",
        "A12": "Запрошена проверка поверки комплекса.",
        "A13": "Запрошена проверка автоматического режима комплекса.",
        "A14": "Есть сомнения в данных собственника или адресата.",
        "A15": "Есть сведения об оплате, отмене или связанном решении.",
        "A16": "Указано второе постановление за тот же факт.",
        "A17": "Указаны обстоятельства крайней необходимости.",
        "A18": "Запрошена юридическая проверка статьи или квалификации.",
    }
    items = [reasons[code]]
    if code == "A01" and answers.get("driver_docs") == "yes":
        items.append("Подтверждающие документы отмечены как имеющиеся.")
    if code == "A02" and answers.get("sale_docs") == "yes":
        items.append("Есть договор или акт передачи.")
    if code == "A03" and answers.get("possession_docs") == "yes":
        items.append("Есть документы о выбытии автомобиля из владения.")
    if code == "A07" and answers.get("speed_docs") == "yes":
        items.append("Есть данные о скорости из независимого источника.")
    if code == "A08" and answers.get("place_time_docs") == "yes":
        items.append("Есть подтверждение места, времени или маршрута.")
    if code == "A09" and answers.get("sign_docs") == "yes":
        items.append("Есть фото, видео или иные сведения о знаке.")
    if code == "A10" and answers.get("marking_docs") == "yes":
        items.append("Есть материалы по разметке на участке.")
    if code == "A14" and answers.get("owner_data_docs") == "yes":
        items.append("Есть документы с корректными данными.")
    if code == "A15" and answers.get("previous_resolution_docs") == "yes":
        items.append("Есть подтверждение оплаты, отмены или связанного решения.")
    if code == "A16" and answers.get("duplicate_docs") == "yes":
        items.append("Второе постановление можно сравнить.")
    if code == "A17" and answers.get("emergency_docs") == "yes":
        items.append("Есть подтверждения чрезвычайных обстоятельств.")
    return items
