"""
CartRepo - репозиторий хранения корзины пользователя.
"""

from typing import List, Dict, Any

from app.db.models import db, Cart, Product


class CartRepo:
    """Репозиторий для работы с корзиной"""

    async def get_cart_items(self, user_id: int) -> List[Dict[str, Any]]:
        """
        Загрузка позиций корзины с JOIN таблицы товаров.
        """
        query = db.select([
            Cart.product_id,
            Cart.qty,
            Product.name,
            Product.price,
            Product.stock,
            Product.is_active
        ]).select_from(
            Cart.join(Product, Cart.product_id == Product.id)
        ).where(
            Cart.user_id == user_id
        )
        
        rows = await query.gino.all()
        
        return [
            {
                'product_id': row[0],
                'qty': row[1],
                'name': row[2],
                'price': row[3],
                'stock': row[4],
                'is_active': row[5]
            }
            for row in rows
        ]

    async def upsert_cart_item(self, user_id: int, product_id: int, qty: int) -> None:
        """
        Добавление или обновление позиции корзины.
        """
        existing = await Cart.query.where(
            (Cart.user_id == user_id) &
            (Cart.product_id == product_id)
        ).gino.first()
        
        if existing:
            await existing.update(qty=qty).apply()
        else:
            await Cart.create(
                user_id=user_id,
                product_id=product_id,
                qty=qty
            )

    async def delete_cart_item(self, user_id: int, product_id: int) -> None:
        """
        Удаление позиции из корзины.
        """
        await Cart.delete.where(
            (Cart.user_id == user_id) &
            (Cart.product_id == product_id)
        ).gino.status()

    async def clear_cart(self, user_id: int) -> None:
        """
        Очистка корзины пользователя.
        """
        await Cart.delete.where(
            Cart.user_id == user_id
        ).gino.status()
