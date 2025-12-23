"""
Блочные тесты модуля профиля (ProfileService).
Тесты Б65-Б70 согласно плану тестирования.
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.services.profile_service import ProfileService
from app.services.cart_service import CartService
from app.dto import ProfileUpdate, Cart, CartItem
from app.exceptions import ValidationError, OrderNotFoundError


class TestProfileServiceGetProfile:
    """Тесты получения профиля"""

    @pytest.mark.asyncio
    async def test_get_profile_success(self, mock_user_repo, mock_order_repo):
        """
        Б65: Получение профиля пользователя.
        Проверяет загрузку данных профиля с подсчётом заказов.
        """
        # Arrange
        service = ProfileService(
            user_repo=mock_user_repo,
            order_repo=mock_order_repo
        )
        
        # Act
        profile = await service.get_profile(user_id=1)
        
        # Assert
        assert profile.user_id == 1
        assert profile.telegram_id == 100001
        assert profile.name == "Иван Тестовый"
        assert profile.phone == "+7 999 111-11-11"
        assert profile.orders_count == 3  # У пользователя 1 три заказа
        assert profile.total_spent > Decimal('0')

    @pytest.mark.asyncio
    async def test_get_profile_new_user(self, mock_user_repo, mock_order_repo):
        """
        Тест: получение профиля нового пользователя.
        """
        # Arrange
        service = ProfileService(
            user_repo=mock_user_repo,
            order_repo=mock_order_repo
        )
        
        # Act
        profile = await service.get_profile(user_id=4)
        
        # Assert
        assert profile.user_id == 4
        assert profile.name == "Новый Пользователь"
        assert profile.phone == ""

    @pytest.mark.asyncio
    async def test_get_profile_total_spent_only_paid_orders(
        self, mock_user_repo, mock_order_repo
    ):
        """
        Тест: total_spent учитывает только оплаченные заказы.
        """
        # Arrange
        service = ProfileService(
            user_repo=mock_user_repo,
            order_repo=mock_order_repo
        )
        
        # Act
        profile = await service.get_profile(user_id=1)
        
        # Assert
        # У пользователя 1: created(89990), paid(129990), shipped(49990)
        # Должны учитываться только paid и shipped
        expected_spent = Decimal('129990') + Decimal('49990')
        assert profile.total_spent == expected_spent


class TestProfileServiceUpdateProfile:
    """Тесты обновления профиля"""

    @pytest.mark.asyncio
    async def test_update_profile_success(self, mock_user_repo, mock_order_repo):
        """
        Б66: Обновление данных профиля.
        Проверяет изменение имени.
        """
        # Arrange
        service = ProfileService(
            user_repo=mock_user_repo,
            order_repo=mock_order_repo
        )
        
        data = ProfileUpdate(name="Иван Новый")
        
        # Act
        profile = await service.update_profile(user_id=1, data=data)
        
        # Assert
        assert profile.name == "Иван Новый"

    @pytest.mark.asyncio
    async def test_update_profile_invalid_phone_raises_error(
        self, mock_user_repo, mock_order_repo
    ):
        """
        Б67: Обновление с невалидным телефоном.
        Проверяет валидацию формата телефона.
        """
        # Arrange
        service = ProfileService(
            user_repo=mock_user_repo,
            order_repo=mock_order_repo
        )
        
        data = ProfileUpdate(phone="invalid_phone")
        
        # Act & Assert
        with pytest.raises(ValidationError) as exc_info:
            await service.update_profile(user_id=1, data=data)
        
        assert "телефон" in str(exc_info.value).lower()

    @pytest.mark.asyncio
    async def test_update_profile_valid_phone(self, mock_user_repo, mock_order_repo):
        """
        Тест: обновление с валидным телефоном.
        """
        # Arrange
        service = ProfileService(
            user_repo=mock_user_repo,
            order_repo=mock_order_repo
        )
        
        data = ProfileUpdate(phone="+7 999 999-99-99")
        
        # Act
        profile = await service.update_profile(user_id=1, data=data)
        
        # Assert
        assert profile is not None

    @pytest.mark.asyncio
    async def test_update_profile_partial_update(self, mock_user_repo, mock_order_repo):
        """
        Тест: частичное обновление профиля.
        """
        # Arrange
        service = ProfileService(
            user_repo=mock_user_repo,
            order_repo=mock_order_repo
        )
        
        # Обновляем только адрес
        data = ProfileUpdate(address="Новый адрес, д. 1")
        
        # Act
        profile = await service.update_profile(user_id=1, data=data)
        
        # Assert - имя должно остаться прежним
        assert profile.name == "Иван Тестовый"


class TestProfileServiceOrderHistory:
    """Тесты истории заказов"""

    @pytest.mark.asyncio
    async def test_get_order_history_success(self, mock_user_repo, mock_order_repo):
        """
        Б68: Получение истории заказов.
        Проверяет выборку заказов отсортированных по дате.
        """
        # Arrange
        service = ProfileService(
            user_repo=mock_user_repo,
            order_repo=mock_order_repo
        )
        
        # Act
        orders = await service.get_order_history(user_id=1, limit=10)
        
        # Assert
        assert len(orders) == 3
        # Проверяем сортировку по дате (новые первыми)
        if len(orders) > 1:
            dates = [o.created_at for o in orders]
            assert dates == sorted(dates, reverse=True)

    @pytest.mark.asyncio
    async def test_get_order_history_respects_limit(
        self, mock_user_repo, mock_order_repo
    ):
        """
        Тест: ограничение количества заказов.
        """
        # Arrange
        service = ProfileService(
            user_repo=mock_user_repo,
            order_repo=mock_order_repo
        )
        
        # Act
        orders = await service.get_order_history(user_id=1, limit=2)
        
        # Assert
        assert len(orders) <= 2

    @pytest.mark.asyncio
    async def test_get_order_history_empty(self, mock_user_repo, mock_order_repo):
        """
        Тест: пустая история заказов.
        """
        # Arrange
        service = ProfileService(
            user_repo=mock_user_repo,
            order_repo=mock_order_repo
        )
        
        # Мокируем пустой список
        mock_order_repo.list_orders_by_user = AsyncMock(return_value=[])
        
        # Act
        orders = await service.get_order_history(user_id=99)
        
        # Assert
        assert orders == []


class TestProfileServiceRepeatOrder:
    """Тесты повторения заказа"""

    @pytest.mark.asyncio
    async def test_repeat_order_success(
        self, mock_user_repo, mock_order_repo, mock_cart_repo, mock_product_repo
    ):
        """
        Б69: Повторение заказа.
        Проверяет создание корзины на основе предыдущего заказа.
        """
        # Arrange
        cart_service = CartService(
            cart_repo=mock_cart_repo,
            product_repo=mock_product_repo
        )
        service = ProfileService(
            user_repo=mock_user_repo,
            order_repo=mock_order_repo,
            cart_service=cart_service
        )
        
        # Мокируем позиции заказа
        from tests.conftest import MockOrderItem
        mock_order_repo.get_order_items = AsyncMock(return_value=[
            MockOrderItem(1, 2, 3, "Samsung Galaxy S24", Decimal('79990'), 1)
        ])
        
        # Act
        cart = await service.repeat_order(user_id=1, order_id=2)
        
        # Assert
        assert cart is not None
        assert cart.user_id == 1

    @pytest.mark.asyncio
    async def test_repeat_order_wrong_user_raises_error(
        self, mock_user_repo, mock_order_repo, mock_cart_repo, mock_product_repo
    ):
        """
        Б70: Повторение чужого заказа.
        Проверяет запрет повторения заказа другого пользователя.
        """
        # Arrange
        cart_service = CartService(
            cart_repo=mock_cart_repo,
            product_repo=mock_product_repo
        )
        service = ProfileService(
            user_repo=mock_user_repo,
            order_repo=mock_order_repo,
            cart_service=cart_service
        )
        
        # Act & Assert - заказ 4 принадлежит user_id=2
        with pytest.raises(OrderNotFoundError):
            await service.repeat_order(user_id=1, order_id=4)

    @pytest.mark.asyncio
    async def test_repeat_order_nonexistent_raises_error(
        self, mock_user_repo, mock_order_repo, mock_cart_repo, mock_product_repo
    ):
        """
        Тест: повторение несуществующего заказа.
        """
        # Arrange
        cart_service = CartService(
            cart_repo=mock_cart_repo,
            product_repo=mock_product_repo
        )
        service = ProfileService(
            user_repo=mock_user_repo,
            order_repo=mock_order_repo,
            cart_service=cart_service
        )
        
        # Act & Assert
        with pytest.raises(OrderNotFoundError):
            await service.repeat_order(user_id=1, order_id=99999)


class TestProfileServicePhoneValidation:
    """Тесты валидации телефона"""

    def test_validate_phone_plus_seven(self, mock_user_repo, mock_order_repo):
        """
        Тест: формат +7 XXX XXX-XX-XX.
        """
        # Arrange
        service = ProfileService(user_repo=mock_user_repo, order_repo=mock_order_repo)
        
        # Act & Assert
        assert service._validate_phone("+7 999 123-45-67") == True
        assert service._validate_phone("+79991234567") == True

    def test_validate_phone_eight(self, mock_user_repo, mock_order_repo):
        """
        Тест: формат 8 XXX XXX-XX-XX.
        """
        # Arrange
        service = ProfileService(user_repo=mock_user_repo, order_repo=mock_order_repo)
        
        # Act & Assert
        assert service._validate_phone("8 999 123-45-67") == True
        assert service._validate_phone("89991234567") == True

    def test_validate_phone_invalid(self, mock_user_repo, mock_order_repo):
        """
        Тест: невалидные форматы.
        """
        # Arrange
        service = ProfileService(user_repo=mock_user_repo, order_repo=mock_order_repo)
        
        # Act & Assert
        assert service._validate_phone("123456") == False
        assert service._validate_phone("abcdefghij") == False
        assert service._validate_phone("+1 234 567 8900") == False

    def test_validate_phone_empty_allowed(self, mock_user_repo, mock_order_repo):
        """
        Тест: пустой телефон допустим.
        """
        # Arrange
        service = ProfileService(user_repo=mock_user_repo, order_repo=mock_order_repo)
        
        # Act & Assert
        assert service._validate_phone("") == True
        assert service._validate_phone(None) == True
