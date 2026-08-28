from dataclasses import asdict, dataclass
from enum import Enum


RULES_VERSION = "2026-08-28"


class EvidenceStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    NEEDED = "NEEDED"
    VERIFY = "VERIFY"


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

    def is_relevant(self, answers: dict[str, str]) -> bool:
        if self.depends_on is None:
            return True
        question_id, accepted_answers = self.depends_on
        return answers.get(question_id) in accepted_answers


@dataclass(frozen=True)
class LegalRule:
    code: str
    title: str
    direction: str
    legal_basis: str
    required_evidence: tuple[str, ...]
    source_ids: tuple[str, ...]


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


QUESTIONS = (
    LegalQuestion(
        id="driver",
        text="Кто фактически пользовался автомобилем в момент нарушения?",
        options=(
            QuestionOption("owner", "Я"),
            QuestionOption("other", "Другой человек"),
            QuestionOption("sold", "Автомобиль был продан"),
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
        id="speed",
        text="Вы оспариваете указанную в постановлении скорость?",
        options=(
            QuestionOption("no", "Нет"),
            QuestionOption("dispute", "Да, скорость определена неверно"),
            QuestionOption("not_speed", "Штраф не связан со скоростью"),
        ),
    ),
    LegalQuestion(
        id="speed_docs",
        text="Есть видеорегистратор, GPS-трек, телематика или другие данные о скорости?",
        options=(QuestionOption("yes", "Да"), QuestionOption("no", "Нет")),
        depends_on=("speed", ("dispute",)),
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
    ),
    LegalQuestion(
        id="sign_docs",
        text="Есть фото, видео или иные сведения о состоянии знака в дату нарушения?",
        options=(QuestionOption("yes", "Да"), QuestionOption("no", "Нет")),
        depends_on=("sign", ("absent", "hidden")),
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
        "A04",
        "Возможна ошибка распознавания госномера",
        "Сопоставить номер в постановлении, читаемый номер на фотографии и автомобиль.",
        "Ст. 26.1, 26.2 и 26.11 КоАП РФ.",
        ("Материалы фотофиксации", "документы на автомобиль"),
        ("koap-rf",),
    ),
    LegalRule(
        "A05",
        "На фотографии другой автомобиль",
        "Проверить признаки автомобиля на фотографии: марку, модель, цвет и госномер.",
        "Ст. 26.1, 26.2 и 26.11 КоАП РФ.",
        ("Материалы фотофиксации", "документы или фотографии автомобиля пользователя"),
        ("koap-rf",),
    ),
    LegalRule(
        "A07",
        "Возможна ошибка определения скорости",
        "Сопоставить данные комплекса с независимыми объективными сведениями о скорости.",
        "Ст. 26.2, 26.8 и 26.11 КоАП РФ.",
        ("Видеорегистратор", "GPS-трек", "телематические данные"),
        ("koap-rf",),
    ),
    LegalRule(
        "A11",
        "Требуется проверка применения технического средства",
        "Истребовать сведения о комплексе, месте установки и условиях его применения.",
        "Ст. 26.8 КоАП РФ.",
        ("Идентификатор комплекса", "материалы фиксации", "сведения о месте установки"),
        ("koap-rf", "plenum-vs-20"),
    ),
    LegalRule(
        "A12",
        "Требуется проверка поверки измерительного средства",
        "Истребовать сведения об утверждении типа и действующей поверке конкретного комплекса.",
        "Ст. 26.8 КоАП РФ в редакции, применимой на дату нарушения.",
        ("Тип и идентификатор комплекса", "свидетельство или сведения о поверке"),
        ("koap-rf",),
    ),
    LegalRule(
        "A13",
        "Требуется проверка автоматического режима фиксации",
        "Установить, работал ли комплекс без непосредственного воздействия человека.",
        "Постановление Пленума ВС РФ № 20.",
        ("Сведения о режиме работы комплекса", "материалы фиксации"),
        ("plenum-vs-20",),
    ),
    LegalRule(
        "A09",
        "Дорожный знак отсутствовал или не был виден",
        "Проверить наличие и видимость знака по направлению движения в дату нарушения.",
        "Ст. 26.1, 26.2 и 26.11 КоАП РФ.",
        ("Фото или видео", "координаты и направление движения", "схема организации движения"),
        ("koap-rf",),
    ),
    LegalRule(
        "A16",
        "Возможно повторное наказание за один факт",
        "Сопоставить оба постановления по времени, месту, составу и материалам фиксации.",
        "Ст. 30.7 КоАП РФ в редакции, применимой к делу.",
        ("Оба постановления", "материалы фиксации по каждому постановлению"),
        ("koap-rf",),
    ),
    LegalRule(
        "A17",
        "Возможна крайняя необходимость",
        "Проверить, существовала ли непосредственная опасность и нельзя ли было устранить её иначе.",
        "Ст. 2.7 КоАП РФ.",
        ("Видео или фотографии", "свидетельские показания", "подтверждающие документы"),
        ("koap-rf",),
    ),
)


def is_speed_notice(article: str | None) -> bool | None:
    if article is None or not article.strip():
        return None
    return "12.9" in article.replace(" ", "")


def get_next_question(
    answers: dict[str, str], notice_article: str | None = None
) -> LegalQuestion | None:
    return next(
        (
            question
            for question in QUESTIONS
            if question.is_relevant(answers)
            and question.id not in answers
            and not (
                question.id in {"speed", "speed_docs"}
                and is_speed_notice(notice_article) is False
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
    answers: dict[str, str], notice_article: str | None = None
) -> list[dict[str, object]]:
    matches: list[tuple[str, EvidenceStatus]] = []
    if answers.get("driver") == "other":
        matches.append(("A01", _evidence(answers, "driver_docs")))
    if answers.get("driver") == "sold":
        matches.append(("A02", _evidence(answers, "sale_docs")))
    if answers.get("plate_photo") in {"different", "unreadable"}:
        matches.append(("A04", EvidenceStatus.NEEDED))
    if answers.get("vehicle_photo") == "different":
        matches.append(("A05", EvidenceStatus.NEEDED))
    if (
        answers.get("speed") == "dispute"
        and is_speed_notice(notice_article) is not False
    ):
        matches.append(("A07", _evidence(answers, "speed_docs")))
    if answers.get("camera") == "other":
        matches.append(("A11", EvidenceStatus.VERIFY))
    if answers.get("camera") == "calibration":
        matches.append(("A12", EvidenceStatus.VERIFY))
    if answers.get("camera") == "manual":
        matches.append(("A13", EvidenceStatus.VERIFY))
    if answers.get("sign") in {"absent", "hidden"}:
        matches.append(("A09", _evidence(answers, "sign_docs")))
    if answers.get("duplicate") == "yes":
        matches.append(("A16", _evidence(answers, "duplicate_docs")))
    if answers.get("emergency") == "yes":
        matches.append(("A17", _evidence(answers, "emergency_docs")))

    rules_by_code = {rule.code: rule for rule in RULES}
    return [
        {**serialize_rule(rules_by_code[code]), "evidence_status": evidence.value}
        for code, evidence in matches
    ]


def _evidence(answers: dict[str, str], question_id: str) -> EvidenceStatus:
    return (
        EvidenceStatus.AVAILABLE
        if answers.get(question_id) == "yes"
        else EvidenceStatus.NEEDED
    )
