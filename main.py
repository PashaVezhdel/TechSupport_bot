import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN, SUPPORT_IDS
from app.filters.role_filters import IsSupport, IsNotSupport

from app.keyboards.user_keyboards import main_menu
from app.keyboards.support_keyboards import support_main_menu

user_router = Router()
support_router = Router()

@user_router.message(Command("start"))
async def start_cmd_user(msg: Message):
    """
    Цей хендлер спрацює ТІЛЬКИ для звичайних користувачів
    """
    await msg.answer("ТЕСТ: Ви звичайний користувач.", reply_markup=main_menu())

@support_router.message(Command("start"))
async def start_cmd_support(msg: Message):
    """
    Цей хендлер спрацює ТІЛЬКИ для ID зі списку SUPPORT_IDS
    """
    await msg.answer("ТЕСТ: Ви сапорт.", reply_markup=support_main_menu())

async def main():
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    dp = Dispatcher()

    user_router.message.filter(IsNotSupport())
    user_router.callback_query.filter(IsNotSupport())
    
    support_router.message.filter(IsSupport())
    support_router.callback_query.filter(IsSupport())

    dp.include_router(support_router)
    dp.include_router(user_router)
    
    print("Test bot started...")
    print(f"Support IDs: {SUPPORT_IDS}")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())