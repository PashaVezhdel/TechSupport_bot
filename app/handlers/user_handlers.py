import uuid
import re
import logging
from datetime import datetime
from aiogram import F, types, Bot, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest

from app.db.database import users_collection, tickets_collection, get_support_ids
from app.keyboards.user_keyboards import main_menu, contact_request_kb, skip_button, priority_keyboard
from app.keyboards.support_keyboards import server_call_kb
from app.fsm.user_forms import TicketForm

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("start"))
async def start_cmd(msg: types.Message):
    try:
        user = users_collection.find_one({"telegram_id": msg.from_user.id})
        if not user:
            users_collection.insert_one({
                "telegram_id": msg.from_user.id,
                "username": msg.from_user.username,
                "registered_at": datetime.utcnow()
            })
            logger.info(f"New user registered: {msg.from_user.id} (@{msg.from_user.username})")
        else:
            logger.info(f"User {msg.from_user.id} started bot")
        
        await msg.answer("👋 Вітаю у боті техпідтримки!", reply_markup=main_menu())
    except Exception as e:
        logger.error(f"Error in /start for user {msg.from_user.id}: {e}")

@router.message(F.text == "🔔 Виклик в серверну")
async def call_master_instant(msg: types.Message, bot: Bot):
    initiator_id = msg.from_user.id
    logger.info(f"User {initiator_id} initiated server room call")
    
    try:
        last_ticket = tickets_collection.find_one(
            {"telegram_id": initiator_id},
            sort=[("created_at", -1)]
        )
        user_phone = last_ticket.get("phone", "Не вказано") if last_ticket else "Не вказано"
        
        alert_text = (
            f"🔔 <b>Виклик до серверної</b>\n\n"
            f"👤 Ініціатор: <b>{msg.from_user.full_name}</b>\n"
            f"📞 Тел: <b>{user_phone}</b>"
        )
        
        support_ids = get_support_ids()
        count = 0
        
        for support_id in support_ids:
            try:
                await bot.send_message(
                    chat_id=support_id, 
                    text=alert_text, 
                    reply_markup=server_call_kb(initiator_id)
                )
                count += 1
            except Exception as e:
                logger.error(f"Failed to send alert to support {support_id}: {e}")
                
        await msg.answer(f"✅ Сповіщення надіслано.", reply_markup=main_menu())
    except Exception as e:
        logger.error(f"Error in call_master_instant: {e}")

@router.message(F.text == "📝 Створити заявку")
async def create_ticket(msg: types.Message, state: FSMContext):
    logger.info(f"User {msg.from_user.id} started creating ticket")
    await state.set_state(TicketForm.name)
    await msg.answer("Введіть своє ПІБ:", reply_markup=ReplyKeyboardRemove())

@router.message(TicketForm.name, F.text)
async def get_name(msg: types.Message, state: FSMContext):
    logger.info(f"User {msg.from_user.id} entered name: {msg.text}")
    await state.update_data(name=msg.text)
    await msg.answer("Надішліть свій номер телефону:", reply_markup=contact_request_kb())
    await state.set_state(TicketForm.phone)

@router.message(TicketForm.name)
async def get_name_invalid(msg: types.Message):
    logger.warning(f"User {msg.from_user.id} sent invalid name type")
    await msg.answer("❌ Будь ласка, введіть ПІБ текстом.")

@router.message(TicketForm.phone, F.contact)
async def get_phone_contact(msg: types.Message, state: FSMContext):
    logger.info(f"User {msg.from_user.id} sent contact: {msg.contact.phone_number}")
    await state.update_data(phone=msg.contact.phone_number)
    await msg.answer("Опишіть проблему:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(TicketForm.description)

@router.message(TicketForm.phone, F.text)
async def get_phone_text(msg: types.Message, state: FSMContext):
    phone_input = msg.text.strip()
    clean_phone = re.sub(r'[^\d+]', '', phone_input)
    
    if not re.match(r'^\+?\d{10,15}$', clean_phone):
        logger.warning(f"User {msg.from_user.id} entered invalid phone format: {phone_input}")
        await msg.answer("❌ Некоректний формат.\nВведіть 10-15 цифр (наприклад 0991234567):")
        return

    logger.info(f"User {msg.from_user.id} entered phone text: {clean_phone}")
    await state.update_data(phone=clean_phone)
    await msg.answer("Опишіть проблему:", reply_markup=ReplyKeyboardRemove())
    await state.set_state(TicketForm.description)

@router.message(TicketForm.phone)
async def get_phone_invalid(msg: types.Message):
    logger.warning(f"User {msg.from_user.id} sent invalid phone type")
    await msg.answer("❌ Будь ласка, надішліть контакт кнопкою або введіть номер цифрами.")

@router.message(TicketForm.description, F.text)
async def get_description(msg: types.Message, state: FSMContext):
    logger.info(f"User {msg.from_user.id} entered description")
    await state.update_data(description=msg.text)
    await msg.answer("Додайте скріншот/файл або натисніть 'Пропустити'", reply_markup=skip_button())
    await state.set_state(TicketForm.image)

@router.message(TicketForm.description)
async def get_description_invalid(msg: types.Message):
    logger.warning(f"User {msg.from_user.id} sent invalid description type")
    await msg.answer("❌ Спочатку опишіть проблему текстом.")

@router.message(TicketForm.image, F.photo)
async def get_image_photo(msg: types.Message, state: FSMContext):
    logger.info(f"User {msg.from_user.id} attached photo")
    await state.update_data(image=msg.photo[-1].file_id, file_type='photo')
    await msg.answer("Оберіть пріоритет заявки:", reply_markup=priority_keyboard())
    await state.set_state(TicketForm.priority)

@router.message(TicketForm.image, F.document)
async def get_image_doc(msg: types.Message, state: FSMContext):
    logger.info(f"User {msg.from_user.id} attached document")
    await state.update_data(image=msg.document.file_id, file_type='document')
    await msg.answer("Оберіть пріоритет заявки:", reply_markup=priority_keyboard())
    await state.set_state(TicketForm.priority)

@router.message(TicketForm.image, F.text == "Пропустити")
async def skip_image(msg: types.Message, state: FSMContext):
    logger.info(f"User {msg.from_user.id} skipped image upload")
    await state.update_data(image=None, file_type=None)
    await msg.answer("Оберіть пріоритет заявки:", reply_markup=priority_keyboard())
    await state.set_state(TicketForm.priority)

@router.message(TicketForm.image)
async def invalid_image_input(msg: types.Message):
    logger.warning(f"User {msg.from_user.id} sent invalid image input")
    await msg.answer("📷 Надішліть фото/файл або натисніть кнопку 'Пропустити'.")

@router.message(TicketForm.priority)
async def get_priority(msg: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    priority_map = {"🔵 Низький": "Низький", "🟡 Середній": "Середній", "🔴 Високий": "Високий"}
    
    if msg.text not in priority_map:
        logger.warning(f"User {msg.from_user.id} selected invalid priority: {msg.text}")
        await msg.answer("Будь ласка, оберіть пріоритет із кнопок.")
        return
    
    priority = priority_map[msg.text]
    ticket_id = str(uuid.uuid4())[:8]
    
    ticket = {
        "ticket_id": ticket_id,
        "telegram_id": msg.from_user.id,
        "name": data["name"],
        "phone": data["phone"],
        "description": data["description"],
        "image": data.get("image"),
        "file_type": data.get("file_type"),
        "priority": priority,
        "status": "Очікує",
        "created_at": datetime.utcnow(),
        "accepted_by": None,
        "decline_reason": None
    }
    
    try:
        tickets_collection.insert_one(ticket)
        logger.info(f"Ticket #{ticket_id} created by User {msg.from_user.id}")
        await msg.answer("✅ Заявку створено! Очікуйте відповіді.", reply_markup=main_menu())
        
        from app.handlers.support_handlers import notify_support_new_ticket
        await notify_support_new_ticket(ticket, bot)
        
    except Exception as e:
        logger.error(f"Failed to create/notify ticket {ticket_id}: {e}")
        await msg.answer("❌ Помилка. Спробуйте пізніше.")

    await state.clear()

@router.message(F.text == "📜 Історія заявок")
async def history(msg: types.Message):
    logger.info(f"User {msg.from_user.id} requested history")
    try:
        tickets = list(tickets_collection.find({"telegram_id": msg.from_user.id}).sort("created_at", -1))
        
        if not tickets:
            await msg.answer("У вас ще немає заявок.")
            return
        
        for t in tickets:
            status_emoji = "⏳" if t['status'] == "Очікує" else "✅" if t['status'] == "Завершена" else "❌"
            txt = f"<b>#{t['ticket_id']} | {status_emoji} {t['status']} | {t['priority']}</b>\n{t['description']}"
            if t['status'] == 'Відхилена' and t.get('decline_reason'):
                txt += f"\n\n🛑 <b>Причина відхилення:</b> {t['decline_reason']}"
            await msg.answer(txt)
    except Exception as e:
        logger.error(f"Error fetching history for user {msg.from_user.id}: {e}")

@router.message(F.text == "❌ Скасувати заявку")
async def cancel_list(msg: types.Message):
    logger.info(f"User {msg.from_user.id} requested cancel list")
    tickets = list(tickets_collection.find({
        "telegram_id": msg.from_user.id,
        "status": {"$in": ["Очікує", "Прийнята"]}
    }))
    
    if not tickets:
        await msg.answer("Немає активних заявок для скасування.")
        return
    
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"❌ #{t['ticket_id']} ({t['priority']})", callback_data=f"user_cancel|{t['ticket_id']}")]
            for t in tickets
        ]
    )
    await msg.answer("Оберіть заявку для скасування:", reply_markup=kb)

@router.callback_query(F.data.startswith("user_cancel|"))
async def user_cancel(cb: types.CallbackQuery):
    ticket_id = cb.data.split("|")[1]
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    
    if not ticket or ticket["telegram_id"] != cb.from_user.id:
        logger.warning(f"User {cb.from_user.id} tried to cancel invalid/other ticket {ticket_id}")
        await cb.answer("Помилка.", show_alert=True)
        return
    
    if ticket.get("status") in ["Скасована", "Відхилена", "Завершена"]:
        await cb.answer("Вже закрито.", show_alert=True)
        try:
            await cb.message.edit_text("Ця заявка вже не активна.")
        except TelegramBadRequest:
            pass
        return
    
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$set": {"status": "Скасована"}}
    )
    logger.info(f"User {cb.from_user.id} cancelled ticket {ticket_id}")
    
    try:
        await cb.message.edit_text(f"🗑 Вашу заявку #{ticket_id} успішно скасовано.")
    except TelegramBadRequest:
        await cb.message.answer(f"🗑 Вашу заявку #{ticket_id} успішно скасовано.")
        
    await cb.answer("Скасовано")