"""
Блочные тесты модуля скидок (DiscountService).
Тесты Б41-Б48 согласно плану тестирования.
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

from app.services.discount_service import DiscountService, AUTO_DISCOUNT_RULES
from app.dto import Cart, CartItem, PromoCheckResult


class TestDiscountServiceValidatePromo:
    """Тесты проверки промокодов"""

    @pytest.mark.asyncio
    async def test_validate_promo_active_percent(self, mock_promocode_repo):
        """
        Б41: Проверка активного процентного промокода.
        Проверяет валидацию промокода SAVE10 (10%).
        """
        # Arrange
        service = DiscountService(promocode_repo=mock_promocode_repo)
        now = datetime.utcnow()
        
        # Act
        result = await service.validate_promo("SAVE10", now)
        
        # Assert
        assert result.valid == True
        assert result.discount_type == "percent"
        assert result.discount_value == Decimal('10')
        assert result.error_message is None

    @pytest.mark.asyncio
    async def test_validate_promo_expired(self, mock_promocode_repo):
        """
        Б42: Проверка истёкшего промокода.
        Проверяет, что OLD (valid_to в прошлом) возвращает valid=False.
        """
        # Arrange
        service = DiscountService(promocode_repo=mock_promocode_repo)
        now = datetime.utcnow()
        
        # Act
        result = await service.validate_promo("OLD", now)
        
        # Assert
        assert result.valid == False
        assert result.error_message == "Промокод истёк"

    @pytest.mark.asyncio
    async def test_validate_promo_already_used(self, mock_promocode_repo):
        """
        Б43: Проверка использованного промокода.
        Проверяет, что USED (is_used=true) возвращает valid=False.
        """
        # Arrange
        service = DiscountService(promocode_repo=mock_promocode_repo)
        now = datetime.utcnow()
        
        # Act
        result = await service.validate_promo("USED", now)
        
        # Assert
        assert result.valid == False
        assert result.error_message == "Промокод уже использован"

    @pytest.mark.asyncio
    async def test_validate_promo_not_found(self, mock_promocode_repo):
        """
        Б44: Проверка несуществующего промокода.
        Проверяет, что INVALID возвращает valid=False.
        """
        # Arrange
        service = DiscountService(promocode_repo=mock_promocode_repo)
        now = datetime.utcnow()
        
        # Act
        result = await service.validate_promo("INVALID_CODE_123", now)
        
        # Assert
        assert result.valid == False
        assert result.error_message == "Промокод не найден"

    @pytest.mark.asyncio
    async def test_validate_promo_case_insensitive(self, mock_promocode_repo):
        """
        Тест: промокод регистронезависим.
        """
        # Arrange
        service = DiscountService(promocode_repo=mock_promocode_repo)
        now = datetime.utcnow()
        
        # Act
        result1 = await service.validate_promo("save10", now)
        result2 = await service.validate_promo("SAVE10", now)
        result3 = await service.validate_promo("Save10", now)
        
        # Assert
        assert result1.valid == True
        assert result2.valid == True
        assert result3.valid == True

    @pytest.mark.asyncio
    async def test_validate_promo_with_spaces(self, mock_promocode_repo):
        """
        Тест: промокод с пробелами (trim).
        """
        # Arrange
        service = DiscountService(promocode_repo=mock_promocode_repo)
        now = datetime.utcnow()
        
        # Act
        result = await service.validate_promo("  SAVE10  ", now)
        
        # Assert
        assert result.valid == True


class TestDiscountServiceApplyDiscounts:
    """Тесты применения скидок"""

    @pytest.mark.asyncio
    async def test_apply_discounts_with_promo_percent(self, mock_promocode_repo):
        """
        Б45: Применение процентной скидки.
        Проверяет расчёт скидки 10% на сумму 100 000₽.
        """
        # Arrange
        service = DiscountService(promocode_repo=mock_promocode_repo)
        
        cart = Cart(
            user_id=1,
            items=[
                CartItem(product_id=1, product_name="Товар", 
                        price=Decimal('100000'), qty=1)
            ]
        )
        
        # Act
        result = await service.apply_discounts(cart, "SAVE10")
        
        # Assert
        assert result.promo_discount == Decimal('10000')  # 10% от 100000
        assert "Промокод SAVE10" in result.applied_rules

    @pytest.mark.asyncio
    async def test_apply_discounts_with_promo_fixed(self, mock_promocode_repo):
        """
        Б46: Применение фиксированной скидки.
        Проверяет скидку FIXED5000 (5000₽).
        """
        # Arrange
        service = DiscountService(promocode_repo=mock_promocode_repo)
        
        cart = Cart(
            user_id=1,
            items=[
                CartItem(product_id=1, product_name="Товар", 
                        price=Decimal('50000'), qty=1)
            ]
        )
        
        # Act
        result = await service.apply_discounts(cart, "FIXED5000")
        
        # Assert
        assert result.promo_discount == Decimal('5000')

    @pytest.mark.asyncio
    async def test_apply_discounts_invalid_promo_ignored(self, mock_promocode_repo):
        """
        Тест: невалидный промокод не применяется.
        """
        # Arrange
        service = DiscountService(promocode_repo=mock_promocode_repo)
        
        cart = Cart(
            user_id=1,
            items=[
                CartItem(product_id=1, product_name="Товар", 
                        price=Decimal('50000'), qty=1)
            ]
        )
        
        # Act
        result = await service.apply_discounts(cart, "INVALID")
        
        # Assert
        assert result.promo_discount == Decimal('0')


class TestDiscountServiceAutoDiscount:
    """Тесты автоматических скидок"""

    @pytest.mark.asyncio
    async def test_calculate_auto_discount_over_50k(self, mock_promocode_repo):
        """
        Б47: Автоскидка при сумме >= 50 000₽.
        Проверяет расчёт 5% скидки.
        """
        # Arrange
        service = DiscountService(promocode_repo=mock_promocode_repo)
        
        # Act
        discount = service.calculate_auto_discount(Decimal('50000'))
        
        # Assert
        assert discount == Decimal('2500')  # 5% от 50000

    @pytest.mark.asyncio
    async def test_calculate_auto_discount_over_100k(self, mock_promocode_repo):
        """
        Тест: автоскидка при сумме >= 100 000₽ (10%).
        """
        # Arrange
        service = DiscountService(promocode_repo=mock_promocode_repo)
        
        # Act
        discount = service.calculate_auto_discount(Decimal('100000'))
        
        # Assert
        assert discount == Decimal('10000')  # 10% от 100000

    @pytest.mark.asyncio
    async def test_calculate_auto_discount_under_threshold(self, mock_promocode_repo):
        """
        Тест: автоскидка при сумме < 50 000₽ (нет скидки).
        """
        # Arrange
        service = DiscountService(promocode_repo=mock_promocode_repo)
        
        # Act
        discount = service.calculate_auto_discount(Decimal('30000'))
        
        # Assert
        assert discount == Decimal('0')

    @pytest.mark.asyncio
    async def test_calculate_auto_discount_applies_best_rule(self, mock_promocode_repo):
        """
        Тест: применяется наиболее выгодное правило.
        """
        # Arrange
        service = DiscountService(promocode_repo=mock_promocode_repo)
        
        # Act
        discount = service.calculate_auto_discount(Decimal('150000'))
        
        # Assert
        assert discount == Decimal('15000')  # 10% от 150000


class TestDiscountServicePromoUsage:
    """Тесты проверки использования промокодов"""

    @pytest.mark.asyncio
    async def test_check_promo_usage_not_used(self, mock_promocode_repo):
        """
        Б48: Проверка использования промокода - не использован.
        """
        # Arrange
        service = DiscountService(promocode_repo=mock_promocode_repo)
        
        # Act
        result = await service.check_promo_usage("SAVE10", user_id=1)
        
        # Assert
        assert result == False

    @pytest.mark.asyncio
    async def test_check_promo_usage_already_used(self, mock_promocode_repo):
        """
        Тест: проверка использованного промокода.
        """
        # Arrange
        service = DiscountService(promocode_repo=mock_promocode_repo)
        
        # Регистрируем использование
        await mock_promocode_repo.record_usage("SAVE10", 1, 1)
        
        # Act
        result = await service.check_promo_usage("SAVE10", user_id=1)
        
        # Assert
        assert result == True
