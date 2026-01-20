import logging
from datetime import datetime
from aiogram import Router, F, types, Bot
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import ReplyKeyboardRemove

from app.db.database import (
    tickets_collection, db, get_support_ids, broadcasts_collection, 
    get_all_users, is_super_admin, 
    add_support, remove_support, get_all_admins_details
)

from app.keyboards.support_keyboards import (
    support_main_menu, 
    support_accept_kb, 
    support_work_kb, 
    server_call_kb,
    broadcast_confirm_kb,
    skip_media_kb,
    super_admin_main_menu,
    admin_management_reply_kb,
    delete_admin_list_kb,
    cancel_kb
)
from app.fsm.support_forms import RejectForm, BroadcastForm, AdminManageForm

router = Router()
logger = logging.getLogger(__name__)

@router.message(Command("start"))
async def start_cmd_support(msg: types.Message):
    if is_super_admin(msg.from_user.id):
        await msg.answer("👋 Вітаю, Шеф! Ви в панелі Супер-Адміністратора.", reply_markup=super_admin_main_menu())
    else:
        await msg.answer("👋 Вітаю у панелі техпідтримки!", reply_markup=support_main_menu())

@router.message(F.text == "👥 Керування персоналом", StateFilter("*"))
async def open_staff_management(msg: types.Message, state: FSMContext, bot: Bot):
    if not is_super_admin(msg.from_user.id):
        await msg.answer("⛔ Доступ заборонено.")
        return

    data = await state.get_data()
    old_menu_id = data.get("admin_menu_msg_id")

    if old_menu_id:
        try:
            await bot.delete_message(chat_id=msg.chat.id, message_id=old_menu_id)
        except Exception:
            pass
    
    await state.clear()
    await msg.answer("Оберіть дію:", reply_markup=admin_management_reply_kb())

@router.message(F.text == "📋 Список адмінів")
async def show_admin_list(msg: types.Message):
    if not is_super_admin(msg.from_user.id): return
    
    admins = get_all_admins_details()
    text = "📋 <b>Список адміністраторів:</b>\n\n"
    for i, admin in enumerate(admins, 1):
        role_icon = "👑" if admin.get("is_super_admin") else "👤"
        username = f"@{admin.get('username')}" if admin.get('username') else "NoName"
        text += f"{i}. {role_icon} <code>{admin['telegram_id']}</code> - {username}\n"
    
    await msg.answer(text)

@router.message(F.text == "➕ Додати адміна")
async def start_add_admin(msg: types.Message, state: FSMContext):
    if not is_super_admin(msg.from_user.id): return
    
    await msg.answer("✍️ Введіть <b>Telegram ID</b> нового співробітника:")
    await state.set_state(AdminManageForm.waiting_for_new_admin_id)

@router.message(AdminManageForm.waiting_for_new_admin_id)
async def process_add_admin(msg: types.Message, state: FSMContext, bot: Bot):
    try:
        new_id = int(msg.text.strip())
        
        try:
            chat_info = await bot.get_chat(new_id)
            username = chat_info.username if chat_info.username else chat_info.full_name
        except Exception:
            username = "New Admin"

        if add_support(new_id, username):
            result_text = f"✅ Користувача <code>{new_id}</code> ({username}) успішно додано!"
        else:
            result_text = "⚠️ Цей користувач вже є в списку."
        
        await state.clear()
        await msg.answer(result_text, reply_markup=admin_management_reply_kb())
            
    except ValueError:
        await msg.answer("❌ Це не схоже на ID. Спробуйте ще раз.")
        return

@router.message(F.text == "➖ Видалити адміна")
async def start_del_admin_menu(msg: types.Message):
    if not is_super_admin(msg.from_user.id): return
    
    admins = get_all_admins_details()
    my_id = msg.from_user.id
    filtered_admins = [a for a in admins if a['telegram_id'] != my_id and not a.get('is_super_admin')]

    if not filtered_admins:
        await msg.answer("❌ Немає кого видаляти.")
        return

    await msg.answer("🗑 <b>Оберіть адміністратора для звільнення:</b>", reply_markup=delete_admin_list_kb(filtered_admins))

@router.callback_query(F.data.startswith("del_adm|"))
async def finish_del_admin(query: types.CallbackQuery, state: FSMContext):
    if not is_super_admin(query.from_user.id): return

    target_id = int(query.data.split("|")[1])
    
    if remove_support(target_id):
        await query.answer("✅ Адміна звільнено!")
        await query.message.edit_text(f"✅ Адміністратора <code>{target_id}</code> видалено.")
    else:
        await query.answer("❌ Помилка.", show_alert=True)
    
    await state.clear()
    await query.message.answer("Оберіть дію:", reply_markup=admin_management_reply_kb())

@router.message(F.text == "🔙 Назад до головного меню")
async def back_to_main_menu(msg: types.Message, state: FSMContext):
    await state.clear()
    if is_super_admin(msg.from_user.id):
        await msg.answer("🏠 Головне меню", reply_markup=super_admin_main_menu())
    else:
        await msg.answer("🏠 Головне меню", reply_markup=support_main_menu())

@router.callback_query(F.data == "admin_cancel")
async def admin_cancel_action(query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await query.message.delete()
    except Exception:
        pass
    await query.answer()

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

@router.callback_query(F.data.startswith("srv_reply|"))
async def server_call_reaction(query: types.CallbackQuery, bot: Bot):
    parts = query.data.split("|")
    action = parts[1]
    initiator_id = parts[2]
    
    responder_name = query.from_user.full_name
    original_text = query.message.html_text if query.message.html_text else query.message.caption
    if not original_text: original_text = "🔔 ВИКЛИК"

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

@router.message(F.text == "📨 Створити розсилку")
async def start_broadcast(msg: types.Message, state: FSMContext):
    await state.set_state(BroadcastForm.waiting_for_text)
    await msg.answer(
        "✍️ Введіть текст повідомлення для розсилки:",
        reply_markup=ReplyKeyboardRemove()
    )

@router.message(BroadcastForm.waiting_for_text)
async def process_broadcast_text(msg: types.Message, state: FSMContext):
    if not msg.text:
        await msg.answer("❌ Будь ласка, надішліть текст.")
        return
        
    await state.update_data(broadcast_text=msg.text, admin_id=msg.from_user.id)
    await state.set_state(BroadcastForm.waiting_for_media)
    
    await msg.answer(
        "📷 Прикріпіть медіа (фото, відео, документ) або натисніть 'Пропустити':",
        reply_markup=skip_media_kb()
    )

@router.message(BroadcastForm.waiting_for_media, F.text == "Пропустити")
async def skip_broadcast_media(msg: types.Message, state: FSMContext):
    await state.update_data(content_type='text', content_id=None)
    await show_broadcast_preview(msg, state)

@router.message(BroadcastForm.waiting_for_media)
async def process_broadcast_media(msg: types.Message, state: FSMContext):
    content_type = None
    content_id = None
    
    if msg.photo:
        content_type = 'photo'
        content_id = msg.photo[-1].file_id
    elif msg.video:
        content_type = 'video'
        content_id = msg.video.file_id
    elif msg.document:
        content_type = 'document'
        content_id = msg.document.file_id
    else:
        await msg.answer("❌ Непідтримуваний тип. Надішліть фото, відео, документ або натисніть 'Пропустити'.")
        return

    await state.update_data(content_type=content_type, content_id=content_id)
    await show_broadcast_preview(msg, state)

async def show_broadcast_preview(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    text = data['broadcast_text']
    c_type = data['content_type']
    c_id = data['content_id']
    
    await msg.answer("👁 <b>Попередній перегляд:</b>", reply_markup=ReplyKeyboardRemove())
    
    try:
        if c_type == 'photo':
            await msg.answer_photo(photo=c_id, caption=text)
        elif c_type == 'video':
            await msg.answer_video(video=c_id, caption=text)
        elif c_type == 'document':
            await msg.answer_document(document=c_id, caption=text)
        else:
            await msg.answer(text)
    except Exception as e:
        logger.error(f"Preview error: {e}")
        await msg.answer("❌ Помилка медіа. Спробуйте ще раз.")
        return

    await msg.answer("Надіслати всім користувачам?", reply_markup=broadcast_confirm_kb())
    await state.set_state(BroadcastForm.waiting_for_confirm)

@router.callback_query(BroadcastForm.waiting_for_confirm, F.data == "broadcast_cancel")
async def cancel_broadcast(query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    kb = super_admin_main_menu() if is_super_admin(query.from_user.id) else support_main_menu()
    await query.message.edit_reply_markup(reply_markup=None)
    await query.message.answer("❌ Розсилку скасовано.", reply_markup=kb)
    await query.answer()

@router.callback_query(BroadcastForm.waiting_for_confirm, F.data == "broadcast_send")
async def send_broadcast(query: types.CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    content_type = data['content_type']
    content_id = data['content_id']
    text = data['broadcast_text']
    admin_id = data['admin_id']
    
    await query.message.edit_reply_markup(reply_markup=None)
    status_msg = await query.message.answer("⏳ Розсилка почалася...")
    
    users = get_all_users()
    count_ok = 0
    count_fail = 0
    
    for user_id in users:
        try:
            if content_type == 'photo':
                await bot.send_photo(chat_id=user_id, photo=content_id, caption=text)
            elif content_type == 'video':
                await bot.send_video(chat_id=user_id, video=content_id, caption=text)
            elif content_type == 'document':
                await bot.send_document(chat_id=user_id, document=content_id, caption=text)
            else:
                await bot.send_message(chat_id=user_id, text=text)
            count_ok += 1
        except Exception:
            count_fail += 1
    
    broadcasts_collection.insert_one({
        "admin_id": admin_id,
        "content_type": content_type,
        "content_id": content_id,
        "text": text,
        "recipients_count": count_ok,
        "date": datetime.utcnow()
    })
    
    logger.info(f"Broadcast sent by {admin_id}. OK: {count_ok}, Fail: {count_fail}")
    
    try:
        await status_msg.delete()
    except:
        pass

    kb = super_admin_main_menu() if is_super_admin(query.from_user.id) else support_main_menu()
    await query.message.answer(
        f"✅ Розсилку завершено!\n"
        f"Успішно: {count_ok}\n"
        f"Не доставлено: {count_fail}",
        reply_markup=kb
    )
    await state.clear()
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