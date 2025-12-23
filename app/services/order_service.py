"""
OrderService - сервис оформления и сопровождения заказов.
"""

from typing import List, Optional
from decimal import Decimal
from datetime import datetime

from app.db.models import Order
from app.dto import Cart, ContactData, OrderData
from app.exceptions import (
    EmptyCartError,
    OrderNotFoundError,
    OrderCannotBeCancelledError,
    InvalidStatusTransitionError,
    ValidationError
)


# Допустимые переходы статусов
STATUS_TRANSITIONS = {
    'created': ['confirmed', 'cancelled'],
    'confirmed': ['paid', 'cancelled'],
    'paid': ['shipped'],
    'shipped': ['delivered'],
    'delivered': [],
    'cancelled': []
}


class OrderService:
    """Сервис управления заказами"""

    def __init__(self, order_repo=None, cart_service=None, product_repo=None,
                 discount_service=None, notification_service=None):
        self.order_repo = order_repo
        self.cart_service = cart_service
        self.product_repo = product_repo
        self.discount_service = discount_service
        self.notification_service = notification_service

    def _generate_order_number(self) -> str:
        """Генерация уникального номера заказа"""
        now = datetime.now()
        date_part = now.strftime('%Y%m%d')
        import random
        seq_part = str(random.randint(1000, 9999))
        return f"ORD-{date_part}-{seq_part}"

    def _validate_contact(self, contact: ContactData) -> None:
        """Валидация контактных данных"""
        if not contact.name or len(contact.name.strip()) < 2:
            raise ValidationError("Укажите корректное имя")
        
        if not contact.phone:
            raise ValidationError("Укажите номер телефона")
        
        # Простая проверка телефона
        phone = contact.phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        if not (phone.startswith('+7') or phone.startswith('8')):
            raise ValidationError("Некорректный формат телефона. Используйте формат +7 XXX XXX-XX-XX")
        
        if len(phone) < 11:
            raise ValidationError("Некорректный номер телефона")
        
        if not contact.address or len(contact.address.strip()) < 10:
            raise ValidationError("Укажите полный адрес доставки")

    async def create_order(self, user_id: int, contact: ContactData, 
                          payment_method: str = 'card') -> Order:
        """
        Создание нового заказа на основе корзины пользователя.
        """
        # Валидация контактных данных
        self._validate_contact(contact)
        
        # Получение корзины
        cart = await self.cart_service.get_cart(user_id)
        
        if cart.is_empty:
            raise EmptyCartError(user_id)
        
        # Расчёт скидок
        discount_result = await self.discount_service.apply_discounts(cart, cart.promocode)
        
        # Расчёт итогов
        totals = self.cart_service.calc_totals(cart, discount_result.total_discount)
        
        # Создание данных заказа
        order_data = OrderData(
            user_id=user_id,
            items=cart.items,
            contact=contact,
            payment_method=payment_method,
            subtotal=totals.subtotal,
            discount=totals.discount,
            total=totals.total,
            promocode=cart.promocode
        )
        
        # Генерация номера заказа
        order_number = self._generate_order_number()
        
        # Сохранение заказа в БД
        order = await self.order_repo.insert_order(order_data, order_number)
        
        # Резервирование товаров
        await self.reserve_stock(order.id)
        
        # Очистка корзины
        await self.cart_service.clear_cart(user_id)
        
        # Отправка уведомлений
        if self.notification_service:
            await self.notification_service.notify_order_created(order)
            await self.notification_service.notify_admin_new_order(order)
        
        return order

    async def get_order(self, order_id: int, user_id: int) -> Optional[Order]:
        """
        Получение заказа по ID с проверкой принадлежности пользователю.
        """
        order = await self.order_repo.get_order_by_id(order_id)
        
        if not order:
            return None
        
        if order.user_id != user_id:
            return None
        
        return order

    async def list_orders(self, user_id: int) -> List[Order]:
        """
        Получение списка всех заказов пользователя.
        """
        return await self.order_repo.list_orders_by_user(user_id)

    async def update_status(self, order_id: int, status: str) -> Order:
        """
        Изменение статуса заказа.
        """
        order = await self.order_repo.get_order_by_id(order_id)
        
        if not order:
            raise OrderNotFoundError(order_id)
        
        # Проверка допустимости перехода
        allowed = STATUS_TRANSITIONS.get(order.status, [])
        if status not in allowed:
            raise InvalidStatusTransitionError(order_id, order.status, status)
        
        # Обновление статуса
        await self.order_repo.update_order_status(order_id, status)
        
        # Перезагрузка заказа
        order = await self.order_repo.get_order_by_id(order_id)
        
        # Отправка уведомления
        if self.notification_service:
            await self.notification_service.notify_status_changed(order)
        
        return order

    async def cancel_order(self, order_id: int, user_id: int) -> Order:
        """
        Отмена заказа пользователем.
        """
        order = await self.order_repo.get_order_by_id(order_id)
        
        if not order:
            raise OrderNotFoundError(order_id)
        
        if order.user_id != user_id:
            raise OrderNotFoundError(order_id)
        
        if order.status not in ('created', 'confirmed'):
            raise OrderCannotBeCancelledError(order_id, order.status)
        
        # Снятие резерва товаров
        await self.release_stock(order_id)
        
        # Обновление статуса
        await self.order_repo.update_order_status(order_id, 'cancelled')
        
        return await self.order_repo.get_order_by_id(order_id)

    async def reserve_stock(self, order_id: int) -> bool:
        """
        Резервирование товаров на складе.
        """
        order_items = await self.order_repo.get_order_items(order_id)
        
        for item in order_items:
            product = await self.product_repo.fetch_product_by_id(item.product_id)
            if not product or product.stock < item.qty:
                return False
            
            await self.product_repo.update_stock(item.product_id, -item.qty)
        
        return True

    async def release_stock(self, order_id: int) -> None:
        """
        Снятие резерва товаров при отмене заказа.
        """
        order_items = await self.order_repo.get_order_items(order_id)
        
        for item in order_items:
            await self.product_repo.update_stock(item.product_id, item.qty)
