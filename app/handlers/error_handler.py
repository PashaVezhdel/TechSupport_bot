import logging
import os
from dotenv import load_dotenv
from aiogram import Router, Bot
from aiogram.types import ErrorEvent
from aiogram.filters import ExceptionTypeFilter

load_dotenv()
ADMIN_ID = os.getenv("SUPPORT_IDS")

error_router = Router()

@error_router.error(ExceptionTypeFilter(Exception))
async def global_error_handler(event: ErrorEvent, bot: Bot):
    logging.error(f"Critical Error: {event.exception}")

    if event.update.message:
        try:
            await event.update.message.answer(
                "Вибачте, сталась технічна помилка. Ми вже працюємо над цим."
            )
        except:
            pass

    if ADMIN_ID:
        await bot.send_message(ADMIN_ID, f"Error: {event.exception}")