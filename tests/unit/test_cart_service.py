"""
Блочные тесты модуля корзины (CartService).
Тесты Б15-Б29 согласно плану тестирования.
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock

from app.services.cart_service import CartService
from app.dto import Cart, CartItem
from app.exceptions import (
    InsufficientStockError,
    CartItemNotFoundError,
    ProductNotFoundError
)


class TestCartServiceGetCart:
    """Тесты получения корзины"""

    @pytest.mark.asyncio
    async def test_get_cart_with_items(self, mock_cart_repo, mock_product_repo):
        """
        Б15: Получение корзины пользователя.
        Проверяет загрузку содержимого корзины.
        """
        # Arrange
        service = CartService(cart_repo=mock_cart_repo, product_repo=mock_product_repo)
        
        # Добавляем товары в корзину через мок
        mock_cart_repo._data[1] = [
            {'product_id': 2, 'qty': 1, 'name': 'iPhone 15', 'price': Decimal('89990'), 
             'stock': 5, 'is_active': True},
            {'product_id': 7, 'qty': 2, 'name': 'Чехол iPhone', 'price': Decimal('1990'), 
             'stock': 100, 'is_active': True}
        ]
        
        # Act
        cart = await service.get_cart(1)
        
        # Assert
        assert len(cart.items) == 2
        assert cart.user_id == 1
        assert not cart.is_empty

    @pytest.mark.asyncio
    async def test_get_cart_empty(self, mock_cart_repo, mock_product_repo):
        """
        Б16: Получение пустой корзины.
        Проверяет корзину нового пользователя.
        """
        # Arrange
        service = CartService(cart_repo=mock_cart_repo, product_repo=mock_product_repo)
        
        # Act
        cart = await service.get_cart(4)  # Новый пользователь
        
        # Assert
        assert cart.items == []
        assert cart.is_empty
        assert cart.user_id == 4

    @pytest.mark.asyncio
    async def test_get_cart_filters_inactive_products(self, mock_cart_repo, mock_product_repo):
        """
        Тест: деактивированные товары автоматически исключаются из корзины.
        """
        # Arrange
        service = CartService(cart_repo=mock_cart_repo, product_repo=mock_product_repo)
        
        mock_cart_repo._data[5] = [
            {'product_id': 2, 'qty': 1, 'name': 'iPhone 15', 'price': Decimal('89990'), 
             'stock': 5, 'is_active': True},
            {'product_id': 99, 'qty': 1, 'name': 'Архивный', 'price': Decimal('999'), 
             'stock': 0, 'is_active': False}  # Неактивный товар
        ]
        
        # Act
        cart = await service.get_cart(5)
        
        # Assert
        assert len(cart.items) == 1
        assert cart.items[0].product_id == 2


class TestCartServiceAddItem:
    """Тесты добавления товаров"""

    @pytest.mark.asyncio
    async def test_add_item_to_empty_cart(self, mock_cart_repo, mock_product_repo):
        """
        Б17: Добавление товара в пустую корзину.
        Проверяет создание первой позиции.
        """
        # Arrange
        service = CartService(cart_repo=mock_cart_repo, product_repo=mock_product_repo)
        
        # Act
        cart = await service.add_item(user_id=4, product_id=3, qty=2)  # Samsung, stock=10
        
        # Assert
        assert len(mock_cart_repo._data.get(4, [])) == 1
        assert mock_cart_repo._data[4][0]['product_id'] == 3
        assert mock_cart_repo._data[4][0]['qty'] == 2

    @pytest.mark.asyncio
    async def test_add_item_increments_existing(self, mock_cart_repo, mock_product_repo):
        """
        Б18: Повторное добавление товара (суммирование qty).
        Проверяет upsert логику.
        """
        # Arrange
        service = CartService(cart_repo=mock_cart_repo, product_repo=mock_product_repo)
        
        # Добавляем товар первый раз
        mock_cart_repo._data[1] = [
            {'product_id': 2, 'qty': 1, 'name': 'iPhone 15', 'price': Decimal('89990'), 
             'stock': 5, 'is_active': True}
        ]
        
        # Act - добавляем ещё 2 единицы
        await service.add_item(user_id=1, product_id=2, qty=2)
        
        # Assert
        assert mock_cart_repo._data[1][0]['qty'] == 3  # 1 + 2 = 3

    @pytest.mark.asyncio
    async def test_add_item_exceeds_stock_raises_error(self, mock_cart_repo, mock_product_repo):
        """
        Б19: Добавление при qty > stock.
        Проверяет валидацию остатков.
        """
        # Arrange
        service = CartService(cart_repo=mock_cart_repo, product_repo=mock_product_repo)
        
        # Act & Assert - product_id=4 (Xiaomi 14) имеет stock=3
        with pytest.raises(InsufficientStockError) as exc_info:
            await service.add_item(user_id=4, product_id=4, qty=5)
        
        assert exc_info.value.product_id == 4
        assert exc_info.value.available == 3
        assert exc_info.value.requested == 5
        assert "Недостаточно товара" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_add_item_zero_stock_raises_error(self, mock_cart_repo, mock_product_repo):
        """
        Б20: Добавление товара с stock=0.
        Проверяет запрет добавления отсутствующего товара.
        """
        # Arrange
        service = CartService(cart_repo=mock_cart_repo, product_repo=mock_product_repo)
        
        # Act & Assert - product_id=1 (iPhone 15 Pro) имеет stock=0
        with pytest.raises(InsufficientStockError) as exc_info:
            await service.add_item(user_id=4, product_id=1, qty=1)
        
        assert exc_info.value.available == 0

    @pytest.mark.asyncio
    async def test_add_nonexistent_product_raises_error(self, mock_cart_repo, mock_product_repo):
        """
        Тест: добавление несуществующего товара.
        """
        # Arrange
        service = CartService(cart_repo=mock_cart_repo, product_repo=mock_product_repo)
        
        # Act & Assert
        with pytest.raises(ProductNotFoundError):
            await service.add_item(user_id=4, product_id=99999, qty=1)

    @pytest.mark.asyncio
    async def test_add_item_negative_qty_raises_error(self, mock_cart_repo, mock_product_repo):
        """
        Тест: добавление отрицательного количества.
        """
        # Arrange
        service = CartService(cart_repo=mock_cart_repo, product_repo=mock_product_repo)
        
        # Act & Assert
        with pytest.raises(ValueError):
            await service.add_item(user_id=4, product_id=3, qty=-1)


class TestCartServiceUpdateItem:
    """Тесты изменения количества"""

    @pytest.mark.asyncio
    async def test_update_item_success(self, mock_cart_repo, mock_product_repo):
        """
        Б21: Обновление qty позиции.
        Проверяет изменение количества.
        """
        # Arrange
        service = CartService(cart_repo=mock_cart_repo, product_repo=mock_product_repo)
        mock_cart_repo._data[1] = [
            {'product_id': 2, 'qty': 1, 'name': 'iPhone 15', 'price': Decimal('89990'), 
             'stock': 5, 'is_active': True}
        ]
        
        # Act
        await service.update_item(user_id=1, product_id=2, qty=3)
        
        # Assert
        assert mock_cart_repo._data[1][0]['qty'] == 3

    @pytest.mark.asyncio
    async def test_update_item_zero_removes(self, mock_cart_repo, mock_product_repo):
        """
        Б22: Обновление qty=0 (удаление).
        Проверяет удаление через установку qty=0.
        """
        # Arrange
        service = CartService(cart_repo=mock_cart_repo, product_repo=mock_product_repo)
        mock_cart_repo._data[1] = [
            {'product_id': 7, 'qty': 2, 'name': 'Чехол iPhone', 'price': Decimal('1990'), 
             'stock': 100, 'is_active': True}
        ]
        
        # Act
        await service.update_item(user_id=1, product_id=7, qty=0)
        
        # Assert - позиция должна быть удалена
        items = [i for i in mock_cart_repo._data.get(1, []) if i['product_id'] == 7]
        assert len(items) == 0

    @pytest.mark.asyncio
    async def test_update_nonexistent_item_raises_error(self, mock_cart_repo, mock_product_repo):
        """
        Б23: Обновление несуществующей позиции.
        Проверяет обработку ошибки.
        """
        # Arrange
        service = CartService(cart_repo=mock_cart_repo, product_repo=mock_product_repo)
        
        # Act & Assert
        with pytest.raises(CartItemNotFoundError) as exc_info:
            await service.update_item(user_id=4, product_id=999, qty=1)
        
        assert exc_info.value.user_id == 4
        assert exc_info.value.product_id == 999


class TestCartServiceRemoveItem:
    """Тесты удаления товаров"""

    @pytest.mark.asyncio
    async def test_remove_item_success(self, mock_cart_repo, mock_product_repo):
        """
        Б24: Удаление позиции из корзины.
        Проверяет явное удаление.
        """
        # Arrange
        service = CartService(cart_repo=mock_cart_repo, product_repo=mock_product_repo)
        mock_cart_repo._data[1] = [
            {'product_id': 7, 'qty': 2, 'name': 'Чехол iPhone', 'price': Decimal('1990'), 
             'stock': 100, 'is_active': True}
        ]
        
        # Act
        await service.remove_item(user_id=1, product_id=7)
        
        # Assert
        items = [i for i in mock_cart_repo._data.get(1, []) if i['product_id'] == 7]
        assert len(items) == 0

    @pytest.mark.asyncio
    async def test_remove_item_idempotent(self, mock_cart_repo, mock_product_repo):
        """
        Б25: Удаление несуществующей позиции (идемпотентность).
        Проверяет, что повторное удаление не вызывает ошибку.
        """
        # Arrange
        service = CartService(cart_repo=mock_cart_repo, product_repo=mock_product_repo)
        
        # Act - удаление несуществующей позиции
        await service.remove_item(user_id=4, product_id=999)
        
        # Assert - не должно быть исключений
        assert True


class TestCartServiceClearCart:
    """Тесты очистки корзины"""

    @pytest.mark.asyncio
    async def test_clear_cart_success(self, mock_cart_repo, mock_product_repo):
        """
        Б26: Очистка корзины.
        Проверяет удаление всех позиций.
        """
        # Arrange
        service = CartService(cart_repo=mock_cart_repo, product_repo=mock_product_repo)
        mock_cart_repo._data[1] = [
            {'product_id': 2, 'qty': 1, 'name': 'iPhone 15', 'price': Decimal('89990'), 
             'stock': 5, 'is_active': True},
            {'product_id': 7, 'qty': 2, 'name': 'Чехол iPhone', 'price': Decimal('1990'), 
             'stock': 100, 'is_active': True}
        ]
        
        # Act
        await service.clear_cart(user_id=1)
        
        # Assert
        assert mock_cart_repo._data.get(1, []) == []


class TestCartServiceCalcTotals:
    """Тесты расчёта итогов"""

    @pytest.mark.asyncio
    async def test_calc_totals_multiple_items(self, mock_cart_repo, mock_product_repo):
        """
        Б27: Расчёт суммы корзины.
        Проверяет calc_totals с несколькими позициями.
        """
        # Arrange
        service = CartService(cart_repo=mock_cart_repo, product_repo=mock_product_repo)
        
        cart = Cart(
            user_id=1,
            items=[
                CartItem(product_id=2, product_name='iPhone 15', 
                        price=Decimal('89990'), qty=1),
                CartItem(product_id=7, product_name='Чехол iPhone', 
                        price=Decimal('1990'), qty=2)
            ]
        )
        
        # Act
        totals = service.calc_totals(cart)
        
        # Assert
        # 89990 + (1990 * 2) = 89990 + 3980 = 93970
        assert totals.subtotal == Decimal('93970')
        assert totals.items_count == 3  # 1 + 2 единицы товара
        assert totals.positions_count == 2  # 2 позиции
        assert totals.discount == Decimal('0')
        assert totals.total == Decimal('93970')

    @pytest.mark.asyncio
    async def test_calc_totals_with_discount(self, mock_cart_repo, mock_product_repo):
        """
        Тест: расчёт с учётом скидки.
        """
        # Arrange
        service = CartService(cart_repo=mock_cart_repo, product_repo=mock_product_repo)
        
        cart = Cart(
            user_id=1,
            items=[
                CartItem(product_id=3, product_name='Samsung', 
                        price=Decimal('100000'), qty=1)
            ]
        )
        
        # Act
        totals = service.calc_totals(cart, discount=Decimal('10000'))
        
        # Assert
        assert totals.subtotal == Decimal('100000')
        assert totals.discount == Decimal('10000')
        assert totals.total == Decimal('90000')

    @pytest.mark.asyncio
    async def test_calc_totals_empty_cart(self, mock_cart_repo, mock_product_repo):
        """
        Тест: расчёт пустой корзины.
        """
        # Arrange
        service = CartService(cart_repo=mock_cart_repo, product_repo=mock_product_repo)
        cart = Cart(user_id=1, items=[])
        
        # Act
        totals = service.calc_totals(cart)
        
        # Assert
        assert totals.subtotal == Decimal('0')
        assert totals.items_count == 0
        assert totals.positions_count == 0


class TestCartServiceCheckStock:
    """Тесты проверки остатков"""

    @pytest.mark.asyncio
    async def test_check_stock_sufficient(self, mock_cart_repo, mock_product_repo):
        """
        Б28: Проверка остатка (достаточно).
        """
        # Arrange
        service = CartService(cart_repo=mock_cart_repo, product_repo=mock_product_repo)
        
        # Act - product_id=3 (Samsung) имеет stock=10
        result = await service.check_stock(product_id=3, qty=5)
        
        # Assert
        assert result == True

    @pytest.mark.asyncio
    async def test_check_stock_insufficient(self, mock_cart_repo, mock_product_repo):
        """
        Б29: Проверка остатка (недостаточно).
        """
        # Arrange
        service = CartService(cart_repo=mock_cart_repo, product_repo=mock_product_repo)
        
        # Act - product_id=4 (Xiaomi) имеет stock=3
        result = await service.check_stock(product_id=4, qty=5)
        
        # Assert
        assert result == False

    @pytest.mark.asyncio
    async def test_check_stock_nonexistent_product(self, mock_cart_repo, mock_product_repo):
        """
        Тест: проверка остатка несуществующего товара.
        """
        # Arrange
        service = CartService(cart_repo=mock_cart_repo, product_repo=mock_product_repo)
        
        # Act
        result = await service.check_stock(product_id=99999, qty=1)
        
        # Assert
        assert result == False
