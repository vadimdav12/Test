"""
UserRepo - репозиторий данных пользователей.
"""

from typing import Optional

from app.db.models import db, User
from app.dto import ProfileUpdate


class UserRepo:
    """Репозиторий для работы с пользователями"""

    async def get_or_create_user(self, telegram_id: int) -> User:
        """
        Получение или создание пользователя по Telegram ID.
        """
        user = await User.query.where(
            User.telegram_id == telegram_id
        ).gino.first()
        
        if not user:
            user = await User.create(
                telegram_id=telegram_id,
                is_admin=False
            )
        
        return user

    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Получение пользователя по внутреннему ID"""
        return await User.get(user_id)

    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Получение пользователя по Telegram ID"""
        return await User.query.where(
            User.telegram_id == telegram_id
        ).gino.first()

    async def update_profile(self, user_id: int, data: ProfileUpdate) -> None:
        """Обновление профиля пользователя"""
        user = await User.get(user_id)
        if not user:
            return
        
        update_data = {}
        if data.name is not None:
            update_data['name'] = data.name
        if data.phone is not None:
            update_data['phone'] = data.phone
        if data.address is not None:
            update_data['address'] = data.address
        
        if update_data:
            await user.update(**update_data).apply()

    async def is_admin(self, user_id: int) -> bool:
        """Проверка прав администратора"""
        user = await User.get(user_id)
        return user.is_admin if user else False
