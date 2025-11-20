import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "support_db"

support_ids_str = os.getenv("SUPPORT_IDS", "")
SUPPORT_IDS = [int(x) for x in support_ids_str.split(",") if x.strip().isdigit()]