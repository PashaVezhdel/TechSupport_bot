from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def support_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📢 Активні заявки"), KeyboardButton(text="📨 Створити розсилку")],
            [KeyboardButton(text="📖 Історія всіх заявок"), KeyboardButton(text="⚙️ Стан БД")]
        ],
        resize_keyboard=True
    )

def super_admin_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📢 Активні заявки"), KeyboardButton(text="📨 Створити розсилку")],
            [KeyboardButton(text="📖 Історія всіх заявок"), KeyboardButton(text="⚙️ Стан БД")],
            [KeyboardButton(text="👥 Керування персоналом")]
        ],
        resize_keyboard=True
    )

def admin_management_reply_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="➕ Додати адміна"), KeyboardButton(text="➖ Видалити адміна")],
            [KeyboardButton(text="📋 Список адмінів")],
            [KeyboardButton(text="🔙 Назад до головного меню")]
        ],
        resize_keyboard=True
    )

def delete_admin_list_kb(admins_list):
    builder = InlineKeyboardBuilder()
    
    for admin in admins_list:
        name = admin.get('username', 'User')
        if not name: name = "User"
        label = f"❌ {name} ({admin['telegram_id']})"
        builder.button(text=label, callback_data=f"del_adm|{admin['telegram_id']}")

    builder.button(text="🔙 Скасувати", callback_data="admin_cancel")
    builder.adjust(1)
    return builder.as_markup()

def cancel_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="🔙 Скасувати", callback_data="admin_cancel")
    return builder.as_markup()

def support_accept_kb(ticket_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Прийняти", callback_data=f"accept|{ticket_id}")
    builder.button(text="❌ Відхилити", callback_data=f"reject|{ticket_id}")
    builder.adjust(1)
    return builder.as_markup()

def support_work_kb(ticket_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Завершити виконання", callback_data=f"complete|{ticket_id}")
    return builder.as_markup()

def server_call_kb(initiator_id):
    builder = InlineKeyboardBuilder()
    builder.button(text="👍 Буду", callback_data=f"srv_reply|yes|{initiator_id}")
    builder.button(text="👎 Не зможу", callback_data=f"srv_reply|no|{initiator_id}")
    builder.adjust(2)
    return builder.as_markup()

def broadcast_confirm_kb():
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Надіслати", callback_data="broadcast_send")
    builder.button(text="❌ Скасувати", callback_data="broadcast_cancel")
    builder.adjust(2)
    return builder.as_markup()

def skip_media_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Пропустити")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )