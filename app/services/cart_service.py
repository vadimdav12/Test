"""
CartService - сервис управления корзиной покупателя.
"""

from typing import List, Optional
from decimal import Decimal

from app.dto import Cart, CartItem, CartTotals
from app.exceptions import (
    InsufficientStockError,
    CartItemNotFoundError,
    ProductNotFoundError
)


class CartService:
    """Сервис управления корзиной"""

    def __init__(self, cart_repo=None, product_repo=None, discount_service=None):
        self.cart_repo = cart_repo
        self.product_repo = product_repo
        self.discount_service = discount_service

    async def get_cart(self, user_id: int) -> Cart:
        """
        Загрузка текущего состояния корзины пользователя.
        Автоматически удаляет позиции с деактивированными товарами.
        """
        cart_items_raw = await self.cart_repo.get_cart_items(user_id)
        
        items = []
        for item in cart_items_raw:
            # Фильтруем деактивированные товары
            if item.get('is_active', True):
                items.append(CartItem(
                    product_id=item['product_id'],
                    product_name=item['name'],
                    price=Decimal(str(item['price'])),
                    qty=item['qty'],
                    stock=item.get('stock', 0)
                ))
        
        return Cart(user_id=user_id, items=items)

    async def add_item(self, user_id: int, product_id: int, qty: int) -> Cart:
        """
        Добавление товара в корзину или увеличение количества.
        """
        if qty <= 0:
            raise ValueError("Количество должно быть положительным числом")
        
        # Проверка существования товара
        product = await self.product_repo.fetch_product_by_id(product_id)
        if not product or not product.is_active:
            raise ProductNotFoundError(product_id)
        
        # Проверка остатка
        current_cart = await self.get_cart(user_id)
        current_qty = 0
        for item in current_cart.items:
            if item.product_id == product_id:
                current_qty = item.qty
                break
        
        total_qty = current_qty + qty
        
        if product.stock < total_qty:
            raise InsufficientStockError(
                product_id=product_id,
                available=product.stock,
                requested=total_qty
            )
        
        # Добавление/обновление позиции
        await self.cart_repo.upsert_cart_item(user_id, product_id, total_qty)
        
        return await self.get_cart(user_id)

    async def update_item(self, user_id: int, product_id: int, qty: int) -> Cart:
        """
        Изменение количества товара в корзине.
        При qty=0 позиция удаляется.
        """
        if qty < 0:
            raise ValueError("Количество не может быть отрицательным")
        
        # Проверка существования позиции
        current_cart = await self.get_cart(user_id)
        found = False
        for item in current_cart.items:
            if item.product_id == product_id:
                found = True
                break
        
        if not found:
            raise CartItemNotFoundError(user_id, product_id)
        
        if qty == 0:
            await self.cart_repo.delete_cart_item(user_id, product_id)
        else:
            # Проверка остатка
            product = await self.product_repo.fetch_product_by_id(product_id)
            if product.stock < qty:
                raise InsufficientStockError(
                    product_id=product_id,
                    available=product.stock,
                    requested=qty
                )
            await self.cart_repo.upsert_cart_item(user_id, product_id, qty)
        
        return await self.get_cart(user_id)

    async def remove_item(self, user_id: int, product_id: int) -> Cart:
        """
        Полное удаление позиции из корзины.
        Операция идемпотентна.
        """
        await self.cart_repo.delete_cart_item(user_id, product_id)
        return await self.get_cart(user_id)

    async def clear_cart(self, user_id: int) -> None:
        """
        Полная очистка корзины пользователя.
        """
        await self.cart_repo.clear_cart(user_id)

    def calc_totals(self, cart: Cart, discount: Decimal = Decimal('0')) -> CartTotals:
        """
        Расчёт итоговых сумм по корзине.
        """
        subtotal = Decimal('0')
        items_count = 0
        
        for item in cart.items:
            subtotal += item.price * item.qty
            items_count += item.qty
        
        total = subtotal - discount
        if total < 0:
            total = Decimal('0')
        
        return CartTotals(
            subtotal=subtotal,
            discount=discount,
            total=total,
            items_count=items_count,
            positions_count=len(cart.items)
        )

    async def check_stock(self, product_id: int, qty: int) -> bool:
        """
        Проверка достаточности складского остатка.
        """
        product = await self.product_repo.fetch_product_by_id(product_id)
        if not product:
            return False
        return product.stock >= qty
