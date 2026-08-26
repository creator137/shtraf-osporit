from aiogram.fsm.state import State, StatesGroup


class DocumentUpload(StatesGroup):
    waiting_for_file = State()


class ProfileSetup(StatesGroup):
    waiting_for_name = State()
