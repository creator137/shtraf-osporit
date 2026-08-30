from aiogram.fsm.state import State, StatesGroup


class DocumentUpload(StatesGroup):
    waiting_for_consent = State()
    waiting_for_file = State()


class LegalQuestionnaire(StatesGroup):
    waiting_for_answer = State()
