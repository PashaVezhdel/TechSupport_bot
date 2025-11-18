import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from app.filters.role_filters import IsSupport, IsNotSupport
from app.handlers import user_handlers
from app.handlers import support_handlers

async def main():
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()

    user_handlers.router.message.filter(IsNotSupport())
    user_handlers.router.callback_query.filter(IsNotSupport())
    
    support_handlers.router.message.filter(IsSupport())
    support_handlers.router.callback_query.filter(IsSupport())

    dp.include_router(support_handlers.router)
    dp.include_router(user_handlers.router)
    
    print("Bot started...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())