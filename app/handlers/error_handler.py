import logging
import os
from dotenv import load_dotenv
from aiogram import Router, Bot
from aiogram.types import ErrorEvent
from aiogram.filters import ExceptionTypeFilter

load_dotenv()

support_ids_str = os.getenv("SUPPORT_IDS", "")
ADMIN_IDS = [int(x) for x in support_ids_str.split(",") if x.strip().isdigit()]

error_router = Router()
logger = logging.getLogger(__name__)

@error_router.error(ExceptionTypeFilter(Exception))
async def global_error_handler(event: ErrorEvent, bot: Bot):
    logger.critical(f"Uncaught exception: {event.exception}", exc_info=True)

    if event.update.message:
        try:
            await event.update.message.answer("Вибачте, сталась технічна помилка. Ми вже працюємо над цим.")
        except Exception as e:
            logger.error(f"Could not send error message to user: {e}")

    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(admin_id, f"🚨 <b>Critical Error:</b>\n{event.exception}")
        except Exception as e:
            logger.error(f"Failed to send error log to admin {admin_id}: {e}")