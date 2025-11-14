from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from config import SUPPORT_IDS

class IsSupport(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        return event.from_user.id in SUPPORT_IDS

class IsNotSupport(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        return event.from_user.id not in SUPPORT_IDS