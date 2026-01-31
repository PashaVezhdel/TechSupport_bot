import asyncio
import logging
import sys
import os
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from app.filters.role_filters import IsSupport, IsNotSupport
from app.handlers import user_handlers, support_handlers
from app.handlers.error_handler import error_router
from app.utils.health_check import db_health_check
from app.utils.backup import create_db_backup

async def main():
    if not os.path.exists('logs'):
        os.makedirs('logs')

    current_date = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join('logs', f'{current_date}.log')
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    logging.basicConfig(level=logging.INFO, handlers=[file_handler, console_handler])

    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()

    user_handlers.router.message.filter(IsNotSupport())
    user_handlers.router.callback_query.filter(IsNotSupport())
    support_handlers.router.message.filter(IsSupport())
    support_handlers.router.callback_query.filter(IsSupport())

    dp.include_router(support_handlers.router)
    dp.include_router(user_handlers.router)
    dp.include_router(error_router)
    
    logging.info("Bot started...")
    
    asyncio.create_task(db_health_check(bot))
    asyncio.create_task(create_db_backup(bot))

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass