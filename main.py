import asyncio
import logging
import sys
import os
from datetime import datetime
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties

from config import BOT_TOKEN
from app.db.database import client, users_collection
from app.filters.role_filters import IsSupport, IsNotSupport
from app.handlers import user_handlers
from app.handlers import support_handlers
from app.handlers.error_handler import error_router

async def get_super_admin_id():
    try:
        admin = await users_collection.find_one({"role": "super_admin"})
        return admin['user_id'] if admin else None
    except Exception:
        return None

async def db_health_check(bot: Bot):
    last_status = True
    while True:
        try:
            await client.admin.command('ping')
            if not last_status:
                admin_id = await get_super_admin_id()
                if admin_id:
                    await bot.send_message(admin_id, "✅ Зв'язок з MongoDB відновлено!")
                last_status = True
        except Exception as e:
            if last_status:
                admin_id = await get_super_admin_id()
                if admin_id:
                    try:
                        await bot.send_message(admin_id, f"🚨 ПОМИЛКА: Втрачено зв'язок з MongoDB!\n\n{e}")
                    except Exception:
                        pass
                last_status = False
        await asyncio.sleep(60)

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

    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, console_handler]
    )

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

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass