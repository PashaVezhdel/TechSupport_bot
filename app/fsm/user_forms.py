from aiogram.fsm.state import State, StatesGroup

class TicketForm(StatesGroup):
    name = State()
    phone = State()
    description = State()
    image = State()
    priority = State()