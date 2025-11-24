from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Створити заявку")],
            # Змінив текст кнопки тут:
            [KeyboardButton(text="📜 Історія заявок"), KeyboardButton(text="🔔 Виклик в серверну")],
            [KeyboardButton(text="❌ Скасувати заявку")]
        ],
        resize_keyboard=True
    )

def contact_request_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📞 Надіслати номер телефону", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def skip_button():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Пропустити")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )

def priority_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔵 Низький")],
            [KeyboardButton(text="🟡 Середній")],
            [KeyboardButton(text="🔴 Високий")]
        ],
        resize_keyboard=True,
        one_time_keyboard=True
    )