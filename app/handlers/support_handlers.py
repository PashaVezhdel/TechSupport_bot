import logging
from aiogram import Router, F, types, Bot
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.exceptions import TelegramBadRequest

from app.db.database import tickets_collection, db, get_support_ids
from app.keyboards.support_keyboards import (
    support_main_menu, 
    support_accept_kb, 
    support_work_kb, 
    server_call_kb
)
from app.fsm.support_forms import RejectForm

router = Router()
logger = logging.getLogger(__name__)

async def notify_support_new_ticket(ticket, bot: Bot):
    text = (
        f"🆕 <b>Нова заявка #{ticket['ticket_id']}</b>\n"
        f"👤 {ticket['name']}\n"
        f"📞 {ticket['phone']}\n"
        f"📄 {ticket['description']}\n"
        f"⚙️ Пріоритет: {ticket['priority']}"
    )
    kb = support_accept_kb(ticket['ticket_id'])
    
    support_ids = get_support_ids()
    
    for support_id in support_ids:
        try:
            if ticket.get("image"):
                if ticket.get("file_type") == 'photo':
                    await bot.send_photo(chat_id=support_id, photo=ticket["image"], caption=text, reply_markup=kb)
                elif ticket.get("file_type") == 'document':
                    await bot.send_document(chat_id=support_id, document=ticket["image"], caption=text, reply_markup=kb)
            else:
                await bot.send_message(chat_id=support_id, text=text, reply_markup=kb)
        except Exception as e:
            logger.error(f"Failed to notify support {support_id}: {e}")

async def notify_user(bot: Bot, chat_id: int, text: str):
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    except Exception as e:
        logger.warning(f"Failed to notify user {chat_id}: {e}")

@router.message(Command("start"))
async def start_cmd_support(msg: types.Message):
    await msg.answer("👋 Вітаю у панелі техпідтримки!", reply_markup=support_main_menu())

@router.callback_query(F.data.startswith("srv_reply|"))
async def server_call_reaction(query: types.CallbackQuery, bot: Bot):
    parts = query.data.split("|")
    action = parts[1]
    initiator_id = parts[2]
    
    responder_name = query.from_user.full_name
    original_text = query.message.html_text if query.message.html_text else query.message.caption
    if not original_text: original_text = "🔔 Виклик"

    logger.info(f"Support {query.from_user.id} reacted to call: {action}")

    if action == "yes":
        new_text = f"{original_text}\n\n✅ <b>Ви підтвердили: 👍!</b>"
        reply_for_initiator = f"✅ <b>{responder_name}</b> відповів: <b>👍!</b>"
    else:
        new_text = f"{original_text}\n\n❌ <b>Ви відхилили: 👎.</b>"
        reply_for_initiator = f"❌ <b>{responder_name}</b> відповів: <b>👎.</b>"
    
    try:
        await query.message.edit_text(new_text, reply_markup=None)
    except Exception:
        await query.message.answer(new_text)

    try:
        await bot.send_message(chat_id=initiator_id, text=reply_for_initiator)
    except Exception:
        pass

    await query.answer()

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
        
        kb = None
        if ticket['status'] == 'Очікує':
            kb = support_accept_kb(ticket['ticket_id'])
        else: 
            text += f"\n\n👨‍💻 <b>Прийняв:</b> @{ticket.get('accepted_by', '???')}"
            kb = support_work_kb(ticket['ticket_id'])
        
        try:
            if ticket.get("image"):
                if ticket.get("file_type") == 'photo':
                    await msg.answer_photo(photo=ticket["image"], caption=text, reply_markup=kb)
                elif ticket.get("file_type") == 'document':
                    await msg.answer_document(document=ticket["image"], caption=text, reply_markup=kb)
            else:
                await msg.answer(text, reply_markup=kb)
        except Exception as e:
            logger.error(f"Media error for ticket {ticket['ticket_id']}: {e}")
            await msg.answer(text + "\n(Медіа недоступне)", reply_markup=kb)

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
        logger.critical(f"DB Connection Error: {e}")
        await msg.answer(f"❌ Помилка з'єднання: {e}")

@router.callback_query(F.data.startswith("accept|"))
async def accept_ticket(query: types.CallbackQuery, bot: Bot):
    ticket_id = query.data.split("|")[1]
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    
    if not ticket:
        await query.answer("Заявку не знайдено.", show_alert=True)
        return
    
    if ticket["status"] != "Очікує":
        await query.answer(f"Статус: {ticket['status']}", show_alert=True)
        try:
            await query.message.edit_reply_markup(reply_markup=None)
        except:
            pass
        return

    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$set": {"status": "Прийнята", "accepted_by": query.from_user.username}}
    )
    
    logger.info(f"Admin {query.from_user.id} accepted ticket {ticket_id}")

    await notify_user(bot, ticket["telegram_id"], 
                      f"👨‍💻 Вашу заявку #{ticket_id} прийняв оператор @{query.from_user.username}.")

    new_text = (
        f"<b>Заявка #{ticket_id} (В роботі)</b>\n"
        f"👤 {ticket['name']} | 📞 {ticket['phone']}\n"
        f"📄 {ticket['description']}\n"
        f"⚙️ Пріоритет: {ticket['priority']}\n"
        f"👨‍💻 <b>Прийняв:</b> @{query.from_user.username}"
    )
    
    try:
        if query.message.caption:
            await query.message.edit_caption(caption=new_text, reply_markup=support_work_kb(ticket_id))
        else:
            await query.message.edit_text(new_text, reply_markup=support_work_kb(ticket_id))
    except Exception:
        await query.message.answer(new_text, reply_markup=support_work_kb(ticket_id))
        
    await query.answer("Ви прийняли заявку!")

@router.callback_query(F.data.startswith("complete|"))
async def complete_ticket(query: types.CallbackQuery, bot: Bot): 
    ticket_id = query.data.split("|")[1]
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})

    if not ticket or ticket['status'] != "Прийнята":
         await query.answer("Неможливо завершити.", show_alert=True)
         return
    
    tickets_collection.update_one(
        {"ticket_id": ticket_id},
        {"$set": {"status": "Завершена"}}
    )
    
    logger.info(f"Admin {query.from_user.id} completed ticket {ticket_id}")
    await notify_user(bot, ticket["telegram_id"], f"✅ Вашу заявку #{ticket_id} успішно виконано.")

    final_text = f"✅ Заявка #{ticket_id} завершена."
    try:
        if query.message.caption:
            await query.message.edit_caption(caption=final_text)
        else:
            await query.message.edit_text(final_text)
    except Exception:
        await query.message.answer(final_text)
        
    await query.answer("Готово!")

@router.callback_query(F.data.startswith("reject|"))
async def reject_ticket_start(query: types.CallbackQuery, state: FSMContext):
    ticket_id = query.data.split("|")[1]
    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    
    if not ticket:
         await query.answer("Заявку не знайдено.", show_alert=True)
         return
         
    if ticket["status"] in ["Відхилена", "Скасована", "Завершена"]:
        await query.answer(f"Ця заявка вже закрита.", show_alert=True)
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
    logger.info(f"Admin {msg.from_user.id} rejected ticket {ticket_id} (Reason: {reason})")

    ticket = tickets_collection.find_one({"ticket_id": ticket_id})
    if ticket:
        await notify_user(bot, ticket["telegram_id"], 
                          f"❌ Вашу заявку #{ticket_id} відхилено.\n<b>Причина:</b> {reason}")

    try:
        await bot.edit_message_reply_markup(
            chat_id=data['chat_id'], 
            message_id=data['msg_id'], 
            reply_markup=None
        )
        await bot.send_message(data['chat_id'], f"❌ Заявку #{ticket_id} відхилено.\nПричина: {reason}")
    except Exception:
        await msg.answer(f"❌ Заявку #{ticket_id} відхилено.")

    await state.clear()