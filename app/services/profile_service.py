"""
ProfileService - сервис управления личным кабинетом пользователя.
"""

from typing import List
from decimal import Decimal
import re

from app.db.models import Order, User
from app.dto import Profile, ProfileUpdate, Cart
from app.exceptions import ValidationError, OrderNotFoundError


class ProfileService:
    """Сервис управления профилем пользователя"""

    def __init__(self, user_repo=None, order_repo=None, cart_service=None):
        self.user_repo = user_repo
        self.order_repo = order_repo
        self.cart_service = cart_service

    def _validate_phone(self, phone: str) -> bool:
        """Валидация формата телефона"""
        if not phone:
            return True  # Пустой телефон допустим
        
        # Убираем все символы кроме цифр и +
        clean_phone = re.sub(r'[^\d+]', '', phone)
        
        # Проверка формата
        if clean_phone.startswith('+7'):
            return len(clean_phone) == 12
        elif clean_phone.startswith('8'):
            return len(clean_phone) == 11
        
        return False

    async def get_profile(self, user_id: int) -> Profile:
        """
        Получение данных профиля пользователя.
        """
        user = await self.user_repo.get_user_by_id(user_id)
        
        if not user:
            # Создаём профиль для нового пользователя
            user = await self.user_repo.get_or_create_user(user_id)
        
        # Получение статистики заказов
        orders = await self.order_repo.list_orders_by_user(user_id)
        
        orders_count = len(orders)
        total_spent = Decimal('0')
        
        for order in orders:
            if order.status in ('paid', 'shipped', 'delivered'):
                total_spent += Decimal(str(order.total))
        
        return Profile(
            user_id=user.id,
            telegram_id=user.telegram_id,
            name=user.name or '',
            phone=user.phone or '',
            address=user.address or '',
            orders_count=orders_count,
            total_spent=total_spent,
            registered_at=user.created_at
        )

    async def update_profile(self, user_id: int, data: ProfileUpdate) -> Profile:
        """
        Обновление контактных данных пользователя.
        """
        # Валидация телефона
        if data.phone is not None and not self._validate_phone(data.phone):
            raise ValidationError("Некорректный формат телефона. Используйте +7 XXX XXX-XX-XX")
        
        await self.user_repo.update_profile(user_id, data)
        
        return await self.get_profile(user_id)

    async def get_order_history(self, user_id: int, limit: int = 10) -> List[Order]:
        """
        Получение истории заказов пользователя.
        """
        orders = await self.order_repo.list_orders_by_user(user_id)
        
        # Сортировка по дате (новые первыми)
        orders.sort(key=lambda x: x.created_at, reverse=True)
        
        return orders[:limit]

    async def repeat_order(self, user_id: int, order_id: int) -> Cart:
        """
        Создание новой корзины на основе предыдущего заказа.
        """
        order = await self.order_repo.get_order_by_id(order_id)
        
        if not order or order.user_id != user_id:
            raise OrderNotFoundError(order_id)
        
        # Получение состава заказа
        order_items = await self.order_repo.get_order_items(order_id)
        
        # Очистка текущей корзины
        await self.cart_service.clear_cart(user_id)
        
        # Добавление позиций из заказа
        for item in order_items:
            try:
                await self.cart_service.add_item(user_id, item.product_id, item.qty)
            except Exception:
                # Если товар недоступен, пропускаем его
                pass
        
        return await self.cart_service.get_cart(user_id)
