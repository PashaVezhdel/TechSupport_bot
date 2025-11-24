from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def support_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📢 Активні заявки")],
            [KeyboardButton(text="📖 Історія всіх заявок"), KeyboardButton(text="⚙️ Стан БД")]
        ],
        resize_keyboard=True
    )

def support_accept_kb(ticket_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Прийняти", callback_data=f"accept|{ticket_id}")],
            [InlineKeyboardButton(text="❌ Відхилити", callback_data=f"reject|{ticket_id}")]
        ]
    )

def support_work_kb(ticket_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Завершити", callback_data=f"complete|{ticket_id}"),
                InlineKeyboardButton(text="❌ Відхилити", callback_data=f"reject|{ticket_id}")
            ]
        ]
    )

def server_call_kb(initiator_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="👍", callback_data=f"srv_reply|yes|{initiator_id}"),
                InlineKeyboardButton(text="👎", callback_data=f"srv_reply|no|{initiator_id}")
            ]
        ]
    )