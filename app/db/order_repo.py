"""
OrderRepo - репозиторий хранения заказов.
"""

from typing import List, Optional
from decimal import Decimal

from app.db.models import db, Order, OrderItem, User
from app.dto import OrderData


class OrderRepo:
    """Репозиторий для работы с заказами"""

    async def insert_order(self, data: OrderData, order_number: str) -> Order:
        """
        Создание заказа с позициями в транзакции.
        """
        async with db.transaction():
            order = await Order.create(
                user_id=data.user_id,
                order_number=order_number,
                status='created',
                total=Decimal(str(data.total)),
                discount=Decimal(str(data.discount)),
                contact_name=data.contact.name,
                contact_phone=data.contact.phone,
                contact_address=data.contact.address,
                payment_method=data.payment_method
            )
            
            for item in data.items:
                await OrderItem.create(
                    order_id=order.id,
                    product_id=item.product_id,
                    product_name=item.product_name,
                    price=Decimal(str(item.price)),
                    qty=item.qty
                )
            
            return order

    async def get_order_by_id(self, order_id: int) -> Optional[Order]:
        """Получение заказа по ID"""
        return await Order.get(order_id)

    async def list_orders_by_user(self, user_id: int) -> List[Order]:
        """Получение всех заказов пользователя"""
        return await Order.query.where(
            Order.user_id == user_id
        ).order_by(Order.created_at.desc()).gino.all()

    async def update_order_status(self, order_id: int, status: str) -> None:
        """Обновление статуса заказа"""
        order = await Order.get(order_id)
        if order:
            await order.update(status=status).apply()

    async def get_order_items(self, order_id: int) -> List[OrderItem]:
        """Получение позиций заказа"""
        return await OrderItem.query.where(
            OrderItem.order_id == order_id
        ).gino.all()

    async def get_user_by_order(self, order_id: int) -> Optional[User]:
        """Получение пользователя по заказу"""
        order = await Order.get(order_id)
        if order:
            return await User.get(order.user_id)
        return None
