from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from app.db.database import is_support

class IsSupport(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        return is_support(event.from_user.id)

class IsNotSupport(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery) -> bool:
        return not is_support(event.from_user.id)