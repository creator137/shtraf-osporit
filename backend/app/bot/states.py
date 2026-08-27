from aiogram.fsm.state import State, StatesGroup


class DocumentUpload(StatesGroup):
    waiting_for_file = State()
