import asyncio
import logging
import os
from datetime import datetime
from bson import json_util
from aiogram import Bot
from aiogram.types import FSInputFile
from app.db.database import client
from app.utils.health_check import get_super_admin_id

async def create_db_backup(bot: Bot):
    while True:
        await asyncio.sleep(60 * 60 * 24 * 7)
        try:
            admin_id = await get_super_admin_id()
            if not admin_id:
                continue

            backup_data = {}
            db = client.get_database()
            collections = await db.list_collection_names()
            
            for coll_name in collections:
                cursor = db[coll_name].find()
                items = await cursor.to_list(length=None)
                backup_data[coll_name] = items

            if not os.path.exists('backups'):
                os.makedirs('backups')
                
            file_path = f"backups/backup_{datetime.now().strftime('%Y-%m-%d')}.json"
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(json_util.dumps(backup_data, indent=4, ensure_ascii=False))

            await bot.send_document(
                admin_id, 
                FSInputFile(file_path), 
                caption=f"📦 Щотижневий бекап бази даних ({datetime.now().strftime('%d.%m.%Y')})"
            )
            logging.info(f"Backup sent to admin: {file_path}")
        except Exception as e:
            logging.error(f"Backup error: {e}")