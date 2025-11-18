from aiogram.fsm.state import State, StatesGroup

class RejectForm(StatesGroup):
    reason = State()
    ticket_id = State()
    chat_id = State()
    msg_id = State()
    status_before = State()