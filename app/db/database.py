from pymongo import MongoClient
from config import MONGO_URI, DB_NAME

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

users_collection = db["users"]
tickets_collection = db["tickets"]
admins_collection = db["admins"]

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
        return True
    return False