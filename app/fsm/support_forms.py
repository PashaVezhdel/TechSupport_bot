from aiogram.fsm.state import State, StatesGroup

class RejectForm(StatesGroup):
    reason = State()
    ticket_id = State()
    chat_id = State()
    msg_id = State()
    status_before = State()

class BroadcastForm(StatesGroup):
    waiting_for_text = State()
    waiting_for_media = State()
    waiting_for_confirm = State()

class AdminManageForm(StatesGroup):
    waiting_for_new_admin_id = State() 
    waiting_for_del_admin_id = State() 