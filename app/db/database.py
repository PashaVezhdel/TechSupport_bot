import logging
from pymongo import MongoClient
from config import MONGO_URI, DB_NAME

logger = logging.getLogger(__name__)

try:
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]

    users_collection = db["users"]
    tickets_collection = db["tickets"]
    admins_collection = db["admins"]
    broadcasts_collection = db["broadcasts"]
    
    client.admin.command('ping')
    logger.info("Connected to MongoDB Atlas")
except Exception as e:
    logger.critical(f"Failed to connect to MongoDB: {e}")

def get_support_ids():
    admins = admins_collection.find({})
    return [admin["telegram_id"] for admin in admins]

def is_support(user_id):
    return admins_collection.find_one({"telegram_id": user_id}) is not None

def add_support(user_id, username=None):
    if not is_support(user_id):
        admins_collection.insert_one({
            "telegram_id": user_id, 
            "username": username
        })
        logger.info(f"New admin added: {user_id} ({username})")
        return True
    return False

def get_all_users():
    users = users_collection.find({})
    return [user["telegram_id"] for user in users]