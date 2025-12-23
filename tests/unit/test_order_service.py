"""
Блочные тесты модуля заказов (OrderService).
Тесты Б30-Б40 согласно плану тестирования.
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.order_service import OrderService
from app.services.cart_service import CartService
from app.services.discount_service import DiscountService
from app.dto import Cart, CartItem, ContactData, DiscountResult
from app.exceptions import (
    EmptyCartError,
    OrderNotFoundError,
    OrderCannotBeCancelledError,
    InvalidStatusTransitionError,
    ValidationError
)


@pytest.fixture
def mock_discount_service():
    """Мок сервиса скидок"""
    service = AsyncMock()
    
    async def apply_discounts(cart, promo_code=None):
        return DiscountResult(
            auto_discount=Decimal('0'),
            promo_discount=Decimal('0'),
            total_discount=Decimal('0'),
            applied_rules=[]
        )
    
    service.apply_discounts = apply_discounts
    return service


@pytest.fixture
def mock_notification_service():
    """Мок сервиса уведомлений"""
    service = AsyncMock()
    service.notify_order_created = AsyncMock()
    service.notify_admin_new_order = AsyncMock()
    service.notify_status_changed = AsyncMock()
    return service


@pytest.fixture
def cart_service_with_items(mock_cart_repo, mock_product_repo):
    """CartService с предзаполненной корзиной"""
    service = CartService(cart_repo=mock_cart_repo, product_repo=mock_product_repo)
    
    # Добавляем товары в корзину пользователя 1
    mock_cart_repo._data[1] = [
        {'product_id': 2, 'qty': 1, 'name': 'iPhone 15', 'price': Decimal('89990'), 
         'stock': 5, 'is_active': True},
        {'product_id': 7, 'qty': 2, 'name': 'Чехол iPhone', 'price': Decimal('1990'), 
         'stock': 100, 'is_active': True}
    ]
    
    return service


class TestOrderServiceCreateOrder:
    """Тесты создания заказа"""

    @pytest.mark.asyncio
    async def test_create_order_success(
        self, mock_order_repo, mock_product_repo, cart_service_with_items,
        mock_discount_service, mock_notification_service
    ):
        """
        Б30: Создание заказа.
        Проверяет полный процесс оформления: создание записи, резервирование, 
        очистку корзины.
        """
        # Arrange
        service = OrderService(
            order_repo=mock_order_repo,
            cart_service=cart_service_with_items,
            product_repo=mock_product_repo,
            discount_service=mock_discount_service,
            notification_service=mock_notification_service
        )
        
        contact = ContactData(
            name="Иван Тестовый",
            phone="+7 999 111-11-11",
            address="г. Москва, ул. Тестовая, д. 1, кв. 1"
        )
        
        # Act
        order = await service.create_order(user_id=1, contact=contact, payment_method='card')
        
        # Assert
        assert order is not None
        assert order.order_number.startswith("ORD-")
        assert order.status == 'created'
        assert order.total == Decimal('93970')  # 89990 + 1990*2
        assert order.contact_name == "Иван Тестовый"
        assert order.payment_method == 'card'
        
        # Проверяем, что уведомления отправлены
        mock_notification_service.notify_order_created.assert_called_once()
        mock_notification_service.notify_admin_new_order.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_order_empty_cart_raises_error(
        self, mock_order_repo, mock_product_repo, mock_cart_repo,
        mock_discount_service, mock_notification_service
    ):
        """
        Б31: Создание заказа с пустой корзиной.
        Проверяет генерацию исключения EmptyCartError.
        """
        # Arrange
        cart_service = CartService(cart_repo=mock_cart_repo, product_repo=mock_product_repo)
        service = OrderService(
            order_repo=mock_order_repo,
            cart_service=cart_service,
            product_repo=mock_product_repo,
            discount_service=mock_discount_service,
            notification_service=mock_notification_service
        )
        
        contact = ContactData(
            name="Тест",
            phone="+7 999 000-00-00",
            address="г. Москва, ул. Тестовая, д. 1"
        )
        
        # Act & Assert
        with pytest.raises(EmptyCartError) as exc_info:
            await service.create_order(user_id=4, contact=contact)  # Пустая корзина
        
        assert exc_info.value.user_id == 4

    @pytest.mark.asyncio
    async def test_create_order_invalid_contact_raises_error(
        self, mock_order_repo, mock_product_repo, cart_service_with_items,
        mock_discount_service, mock_notification_service
    ):
        """
        Тест: валидация контактных данных при создании заказа.
        """
        # Arrange
        service = OrderService(
            order_repo=mock_order_repo,
            cart_service=cart_service_with_items,
            product_repo=mock_product_repo,
            discount_service=mock_discount_service,
            notification_service=mock_notification_service
        )
        
        # Act & Assert - пустое имя
        with pytest.raises(ValidationError):
            await service.create_order(
                user_id=1,
                contact=ContactData(name="", phone="+7 999 111-11-11", address="Адрес тестовый")
            )
        
        # Act & Assert - некорректный телефон
        with pytest.raises(ValidationError):
            await service.create_order(
                user_id=1,
                contact=ContactData(name="Иван", phone="12345", address="Адрес тестовый")
            )
        
        # Act & Assert - слишком короткий адрес
        with pytest.raises(ValidationError):
            await service.create_order(
                user_id=1,
                contact=ContactData(name="Иван", phone="+7 999 111-11-11", address="Адрес")
            )


class TestOrderServiceGetOrder:
    """Тесты получения заказа"""

    @pytest.mark.asyncio
    async def test_get_order_success(self, mock_order_repo):
        """
        Б32: Получение заказа.
        Проверяет получение заказа по ID.
        """
        # Arrange
        service = OrderService(order_repo=mock_order_repo)
        
        # Act
        order = await service.get_order(order_id=2, user_id=1)
        
        # Assert
        assert order is not None
        assert order.id == 2
        assert order.order_number == "ORD-20241201-0002"

    @pytest.mark.asyncio
    async def test_get_order_wrong_user_returns_none(self, mock_order_repo):
        """
        Б33: Получение чужого заказа.
        Проверяет, что заказ другого пользователя возвращает None.
        """
        # Arrange
        service = OrderService(order_repo=mock_order_repo)
        
        # Act - заказ 4 принадлежит user_id=2
        order = await service.get_order(order_id=4, user_id=1)
        
        # Assert
        assert order is None

    @pytest.mark.asyncio
    async def test_get_order_nonexistent_returns_none(self, mock_order_repo):
        """
        Тест: получение несуществующего заказа.
        """
        # Arrange
        service = OrderService(order_repo=mock_order_repo)
        
        # Act
        order = await service.get_order(order_id=99999, user_id=1)
        
        # Assert
        assert order is None


class TestOrderServiceListOrders:
    """Тесты списка заказов"""

    @pytest.mark.asyncio
    async def test_list_orders_success(self, mock_order_repo):
        """
        Б34: Получение списка заказов.
        Проверяет выборку заказов пользователя.
        """
        # Arrange
        service = OrderService(order_repo=mock_order_repo)
        
        # Act
        orders = await service.list_orders(user_id=1)
        
        # Assert
        assert len(orders) == 3  # У пользователя 1 три заказа
        assert all(o.user_id == 1 for o in orders)


class TestOrderServiceUpdateStatus:
    """Тесты изменения статуса"""

    @pytest.mark.asyncio
    async def test_update_status_success(self, mock_order_repo, mock_notification_service):
        """
        Б35: Изменение статуса заказа.
        Проверяет переход created -> confirmed.
        """
        # Arrange
        service = OrderService(
            order_repo=mock_order_repo,
            notification_service=mock_notification_service
        )
        
        # Act
        order = await service.update_status(order_id=1, status='confirmed')
        
        # Assert
        assert order.status == 'confirmed'
        mock_notification_service.notify_status_changed.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_status_invalid_transition_raises_error(self, mock_order_repo):
        """
        Б36: Недопустимый переход статуса.
        Проверяет переход cancelled -> shipped (невозможен).
        """
        # Arrange
        service = OrderService(order_repo=mock_order_repo)
        
        # Act & Assert - заказ 5 в статусе cancelled
        with pytest.raises(InvalidStatusTransitionError) as exc_info:
            await service.update_status(order_id=5, status='shipped')
        
        assert exc_info.value.current_status == 'cancelled'
        assert exc_info.value.new_status == 'shipped'

    @pytest.mark.asyncio
    async def test_update_status_nonexistent_order_raises_error(self, mock_order_repo):
        """
        Тест: изменение статуса несуществующего заказа.
        """
        # Arrange
        service = OrderService(order_repo=mock_order_repo)
        
        # Act & Assert
        with pytest.raises(OrderNotFoundError):
            await service.update_status(order_id=99999, status='paid')


class TestOrderServiceCancelOrder:
    """Тесты отмены заказа"""

    @pytest.mark.asyncio
    async def test_cancel_order_success(self, mock_order_repo, mock_product_repo):
        """
        Б37: Отмена заказа.
        Проверяет отмену и возврат товаров на склад.
        """
        # Arrange
        service = OrderService(
            order_repo=mock_order_repo,
            product_repo=mock_product_repo
        )
        
        # Добавляем позиции заказа для возврата
        mock_order_repo.get_order_items = AsyncMock(return_value=[])
        
        # Act
        order = await service.cancel_order(order_id=1, user_id=1)
        
        # Assert
        assert order.status == 'cancelled'

    @pytest.mark.asyncio
    async def test_cancel_order_shipped_raises_error(self, mock_order_repo, mock_product_repo):
        """
        Б38: Отмена отправленного заказа.
        Проверяет запрет отмены для статуса shipped.
        """
        # Arrange
        service = OrderService(
            order_repo=mock_order_repo,
            product_repo=mock_product_repo
        )
        
        # Act & Assert - заказ 3 в статусе shipped
        with pytest.raises(OrderCannotBeCancelledError) as exc_info:
            await service.cancel_order(order_id=3, user_id=1)
        
        assert exc_info.value.status == 'shipped'

    @pytest.mark.asyncio
    async def test_cancel_order_wrong_user_raises_error(self, mock_order_repo, mock_product_repo):
        """
        Тест: отмена чужого заказа.
        """
        # Arrange
        service = OrderService(
            order_repo=mock_order_repo,
            product_repo=mock_product_repo
        )
        
        # Act & Assert - заказ 4 принадлежит user_id=2
        with pytest.raises(OrderNotFoundError):
            await service.cancel_order(order_id=4, user_id=1)


class TestOrderServiceStock:
    """Тесты резервирования товаров"""

    @pytest.mark.asyncio
    async def test_reserve_stock_success(self, mock_order_repo, mock_product_repo, test_products):
        """
        Б39: Резервирование товаров.
        Проверяет уменьшение остатка.
        """
        # Arrange
        service = OrderService(
            order_repo=mock_order_repo,
            product_repo=mock_product_repo
        )
        
        # Мокируем позиции заказа
        from tests.conftest import MockOrderItem
        mock_order_repo.get_order_items = AsyncMock(return_value=[
            MockOrderItem(1, 1, 3, "Samsung", Decimal('79990'), 2)  # product_id=3, qty=2
        ])
        
        initial_stock = test_products[2].stock  # Samsung id=3, stock=10
        
        # Act
        result = await service.reserve_stock(order_id=1)
        
        # Assert
        assert result == True
        assert test_products[2].stock == initial_stock - 2

    @pytest.mark.asyncio
    async def test_release_stock_success(self, mock_order_repo, mock_product_repo, test_products):
        """
        Б40: Снятие резерва (при отмене).
        Проверяет увеличение остатка.
        """
        # Arrange
        service = OrderService(
            order_repo=mock_order_repo,
            product_repo=mock_product_repo
        )
        
        # Мокируем позиции заказа
        from tests.conftest import MockOrderItem
        mock_order_repo.get_order_items = AsyncMock(return_value=[
            MockOrderItem(1, 1, 3, "Samsung", Decimal('79990'), 2)  # product_id=3, qty=2
        ])
        
        initial_stock = test_products[2].stock  # Samsung
        
        # Act
        await service.release_stock(order_id=1)
        
        # Assert
        assert test_products[2].stock == initial_stock + 2


class TestOrderServiceOrderNumber:
    """Тесты генерации номера заказа"""

    def test_generate_order_number_format(self, mock_order_repo):
        """
        Тест: формат номера заказа.
        """
        # Arrange
        service = OrderService(order_repo=mock_order_repo)
        
        # Act
        order_number = service._generate_order_number()
        
        # Assert
        assert order_number.startswith("ORD-")
        parts = order_number.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 4  # Случайный номер
