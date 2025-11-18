from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from config import SUPPORT_IDS
from app.db.database import tickets_collection, db
from app.keyboards.support_keyboards import support_main_menu, support_accept_kb, support_work_kb
from app.fsm.support_forms import RejectForm

router = Router()

async def notify_support_new_ticket(ticket, bot: Bot):
    text = (
        f"🆕 <b>Нова заявка #{ticket['ticket_id']}</b>\n"
        f"👤 {ticket['name']}\n"
        f"📞 {ticket['phone']}\n"
        f"📄 {ticket['description']}\n"
        f"⚙️ Пріоритет: {ticket['priority']}"
    )
    kb = support_accept_kb(ticket['ticket_id'])
    for support_id in SUPPORT_IDS:
        try:
            if ticket.get("image"):
                if ticket.get("file_type") == 'photo':
                    await bot.send_photo(chat_id=support_id, photo=ticket["image"], caption=text, reply_markup=kb)
                elif ticket.get("file_type") == 'document':
                    await bot.send_document(chat_id=support_id, document=ticket["image"], caption=text, reply_markup=kb)
            else:
                await bot.send_message(chat_id=support_id, text=text, reply_markup=kb)
        except Exception:
            pass

async def notify_user(bot: Bot, chat_id: int, text: str):
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    except Exception:
        pass

@router.message(Command("start"))
async def start_cmd_support(msg: types.Message):
    await msg.answer("👋 Вітаю у панелі техпідтримки!", reply_markup=support_main_menu())

@router.message(F.text == "📢 Активні заявки")
async def view_all_active_tickets(msg: types.Message):
    tickets = list(tickets_collection.find({
        "status": {"$in": ["Очікує", "Прийнята"]}
    }).sort("created_at", 1))
    if not tickets:
        await msg.answer("✅ Активних заявок немає.")
        return
    await msg.answer(f"Знайдено активних заявок: {len(tickets)}")
    for ticket in tickets:
        text = (
            f"<b>Заявка #{ticket['ticket_id']} ({ticket['status']})</b>\n"
            f"👤 {ticket['name']} | 📞 {ticket['phone']}\n"
            f"📄 {ticket['description']}\n"
            f"⚙️ Пріоритет: {ticket['priority']}"
        )
        if ticket['status'] == 'Очікує':
            kb = support_accept_kb(ticket['ticket_id'])
        else: 
            text += f"\n\n👨‍💻 <b>Прийняв:</b> @{ticket.get('accepted_by', '???')}"
            kb = support_work_kb(ticket['ticket_id'])
        await msg.answer(text, reply_markup=kb)

@router.message(F.text == "📖 Історія всіх заявок")
async def view_history_all(msg: types.Message):
    tickets = list(tickets_collection.find({
        "status": {"$in": ["Завершена", "Відхилена", "Скасована"]}
    }).sort("created_at", -1).limit(20))
    if not tickets:
        await msg.answer("Архів порожній.")
        return
    for t in tickets:
        status_icon = "✅" if t['status'] == "Завершена" else "❌"
        txt = f"{status_icon} <b>#{t['ticket_id']}</b> | {t['status']}\n{t['description']}"
        if t.get('decline_reason'):
             txt += f"\n🛑 Причина: {t['decline_reason']}"
        await msg.answer(txt)

@router.message(F.text == "⚙️ Стан БД")
async def check_db_status(msg: types.Message):
    try:
        db.command("ping")
        count = tickets_collection.count_documents({})
        await msg.answer(f"✅ З'єднання стабільне.\nВсього заявок у базі: {count}")
    except Exception as e:
        await msg.answer(f"❌ Помилка з'єднання: {e}")

@router.callback_query(F.data.startswith("accept|"))
async def accept_ticket(query: types.CallbackQuery, bot: Bot):
    ticket_id = query.data.split("|")[1]
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    if not ticket:
        await query.answer("Заявку не знайдено.", show_alert=True)
        return
    if ticket["status"] != "Очікує":
        await query.answer(f"Статус заявки вже: {ticket['status']}", show_alert=True)
        await query.message.edit_text(f"🔒 Заявка #{ticket_id} вже оброблена ({ticket['status']}).")
        return
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$set": {"status": "Прийнята", "accepted_by": query.from_user.username}}
    )
    await notify_user(bot, ticket["telegram_id"], f"👨‍💻 Вашу заявку #{ticket_id} прийняв оператор @{query.from_user.username}.")
    new_text = (
        f"<b>Заявка #{ticket_id} (В роботі)</b>\n"
        f"👤 {ticket['name']} | 📞 {ticket['phone']}\n"
        f"📄 {ticket['description']}\n"
        f"⚙️ Пріоритет: {ticket['priority']}\n"
        f"👨‍💻 <b>Прийняв:</b> @{query.from_user.username}"
    )
    await query.message.edit_text(new_text, reply_markup=support_work_kb(ticket_id))
    await query.answer("Ви прийняли заявку!")

@router.callback_query(F.data.startswith("complete|"))
async def complete_ticket(query: types.CallbackQuery, bot: Bot): 
    ticket_id = query.data.split("|")[1]
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    if not ticket or ticket['status'] != "Прийнята":
         await query.answer("Цю заявку вже не можна завершити.", show_alert=True)
         return
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$set": {"status": "Завершена"}}
    )
    await notify_user(bot, ticket["telegram_id"], f"✅ Вашу заявку #{ticket_id} успішно виконано/завершено.")
    await query.message.edit_text(f"✅ Заявка #{ticket_id} завершена.")
    await query.answer("Готово!")

@router.callback_query(F.data.startswith("reject|"))
async def reject_ticket_start(query: types.CallbackQuery, state: FSMContext):
    ticket_id = query.data.split("|")[1]
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    if not ticket:
         await query.answer("Заявку не знайдено.", show_alert=True)
         return
    if ticket["status"] in ["Відхилена", "Скасована", "Завершена"]:
        await query.answer(f"Ця заявка вже закрита (статус: {ticket['status']}).", show_alert=True)
        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except:
            pass
        return 
    await state.update_data(
        ticket_id=ticket_id,
        chat_id=query.message.chat.id,
        msg_id=query.message.message_id
    )
    await state.set_state(RejectForm.reason)
    await query.message.answer(f"✍️ Введіть причину відхилення для заявки <b>#{ticket_id}</b>:")
    await query.answer()

@router.message(RejectForm.reason)
async def process_rejection_reason(msg: types.Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    ticket_id = data["ticket_id"]
    reason = msg.text
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$set": {"status": "Відхилена", "decline_reason": reason}}
    )
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    if ticket:
        await notify_user(bot, ticket["telegram_id"], f"❌ Вашу заявку #{ticket_id} відхилено.\n<b>Причина:</b> {reason}")
    try:
        await bot.edit_message_text(
            chat_id=data['chat_id'],
            message_id=data['msg_id'],
            text=f"❌ Заявку #{ticket_id} відхилено.\n<b>Причина:</b> {reason}",
            reply_markup=None
        )
    except TelegramBadRequest:
        await msg.answer(f"❌ Заявку #{ticket_id} відхилено.")
    await msg.answer("Причину збережено.")
    await state.clear()