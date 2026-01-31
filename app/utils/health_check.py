import asyncio
import logging
from aiogram import Bot
from app.db.database import client, users_collection

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