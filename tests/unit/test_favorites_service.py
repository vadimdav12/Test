"""
Блочные тесты модуля избранного (FavoritesService).
Тесты Б57-Б64 согласно плану тестирования.
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock

from app.services.favorites_service import FavoritesService
from app.exceptions import ProductNotFoundError


class TestFavoritesServiceAdd:
    """Тесты добавления в избранное"""

    @pytest.mark.asyncio
    async def test_add_favorite_success(self, mock_favorites_repo, mock_product_repo):
        """
        Б57: Добавление товара в избранное.
        Проверяет успешное добавление.
        """
        # Arrange
        service = FavoritesService(
            favorites_repo=mock_favorites_repo,
            product_repo=mock_product_repo
        )
        
        # Act
        await service.add_favorite(user_id=4, product_id=5)
        
        # Assert
        assert 5 in mock_favorites_repo._data.get(4, [])

    @pytest.mark.asyncio
    async def test_add_favorite_idempotent(self, mock_favorites_repo, mock_product_repo):
        """
        Б58: Повторное добавление в избранное (идемпотентность).
        Проверяет, что дубликаты не создаются.
        """
        # Arrange
        service = FavoritesService(
            favorites_repo=mock_favorites_repo,
            product_repo=mock_product_repo
        )
        
        # Act - добавляем дважды
        await service.add_favorite(user_id=4, product_id=5)
        await service.add_favorite(user_id=4, product_id=5)
        
        # Assert - должна быть только одна запись
        count = mock_favorites_repo._data.get(4, []).count(5)
        assert count == 1

    @pytest.mark.asyncio
    async def test_add_favorite_nonexistent_product_raises_error(
        self, mock_favorites_repo, mock_product_repo
    ):
        """
        Б59: Добавление несуществующего товара.
        Проверяет генерацию исключения ProductNotFoundError.
        """
        # Arrange
        service = FavoritesService(
            favorites_repo=mock_favorites_repo,
            product_repo=mock_product_repo
        )
        
        # Act & Assert
        with pytest.raises(ProductNotFoundError) as exc_info:
            await service.add_favorite(user_id=4, product_id=99999)
        
        assert exc_info.value.product_id == 99999

    @pytest.mark.asyncio
    async def test_add_favorite_inactive_product_raises_error(
        self, mock_favorites_repo, mock_product_repo
    ):
        """
        Тест: добавление неактивного товара.
        """
        # Arrange
        service = FavoritesService(
            favorites_repo=mock_favorites_repo,
            product_repo=mock_product_repo
        )
        
        # Act & Assert - product_id=99 неактивен
        with pytest.raises(ProductNotFoundError):
            await service.add_favorite(user_id=4, product_id=99)


class TestFavoritesServiceRemove:
    """Тесты удаления из избранного"""

    @pytest.mark.asyncio
    async def test_remove_favorite_success(self, mock_favorites_repo, mock_product_repo):
        """
        Б60: Удаление товара из избранного.
        Проверяет успешное удаление.
        """
        # Arrange
        service = FavoritesService(
            favorites_repo=mock_favorites_repo,
            product_repo=mock_product_repo
        )
        
        # Добавляем товар
        mock_favorites_repo._data[1] = [5]
        
        # Act
        await service.remove_favorite(user_id=1, product_id=5)
        
        # Assert
        assert 5 not in mock_favorites_repo._data.get(1, [])

    @pytest.mark.asyncio
    async def test_remove_favorite_idempotent(self, mock_favorites_repo, mock_product_repo):
        """
        Б61: Удаление несуществующей записи (идемпотентность).
        Проверяет, что ошибка не генерируется.
        """
        # Arrange
        service = FavoritesService(
            favorites_repo=mock_favorites_repo,
            product_repo=mock_product_repo
        )
        
        # Act - удаляем несуществующую запись
        await service.remove_favorite(user_id=4, product_id=999)
        
        # Assert - не должно быть исключений
        assert True


class TestFavoritesServiceList:
    """Тесты получения списка избранного"""

    @pytest.mark.asyncio
    async def test_list_favorites_success(self, mock_favorites_repo, mock_product_repo):
        """
        Б62: Получение списка избранного.
        Проверяет выборку товаров из избранного.
        """
        # Arrange
        service = FavoritesService(
            favorites_repo=mock_favorites_repo,
            product_repo=mock_product_repo
        )
        
        # Добавляем товары в избранное
        mock_favorites_repo._data[1] = [2, 3, 5]  # iPhone 15, Samsung, MacBook
        
        # Act
        products = await service.list_favorites(user_id=1)
        
        # Assert
        assert len(products) == 3
        product_ids = [p.id for p in products]
        assert 2 in product_ids
        assert 3 in product_ids
        assert 5 in product_ids

    @pytest.mark.asyncio
    async def test_list_favorites_empty(self, mock_favorites_repo, mock_product_repo):
        """
        Тест: пустой список избранного.
        """
        # Arrange
        service = FavoritesService(
            favorites_repo=mock_favorites_repo,
            product_repo=mock_product_repo
        )
        
        # Act
        products = await service.list_favorites(user_id=4)  # Новый пользователь
        
        # Assert
        assert products == []

    @pytest.mark.asyncio
    async def test_list_favorites_filters_inactive(self, mock_favorites_repo, mock_product_repo):
        """
        Тест: неактивные товары исключаются из списка.
        """
        # Arrange
        service = FavoritesService(
            favorites_repo=mock_favorites_repo,
            product_repo=mock_product_repo
        )
        
        # Добавляем активный и неактивный товары
        mock_favorites_repo._data[1] = [2, 99]  # 2 - активный, 99 - неактивный
        
        # Act
        products = await service.list_favorites(user_id=1)
        
        # Assert
        product_ids = [p.id for p in products]
        assert 2 in product_ids
        assert 99 not in product_ids


class TestFavoritesServiceIsFavorite:
    """Тесты проверки наличия в избранном"""

    @pytest.mark.asyncio
    async def test_is_favorite_true(self, mock_favorites_repo, mock_product_repo):
        """
        Б63: Проверка наличия в избранном (есть).
        """
        # Arrange
        service = FavoritesService(
            favorites_repo=mock_favorites_repo,
            product_repo=mock_product_repo
        )
        
        mock_favorites_repo._data[1] = [5]
        
        # Act
        result = await service.is_favorite(user_id=1, product_id=5)
        
        # Assert
        assert result == True

    @pytest.mark.asyncio
    async def test_is_favorite_false(self, mock_favorites_repo, mock_product_repo):
        """
        Б64: Проверка наличия в избранном (нет).
        """
        # Arrange
        service = FavoritesService(
            favorites_repo=mock_favorites_repo,
            product_repo=mock_product_repo
        )
        
        # Act
        result = await service.is_favorite(user_id=4, product_id=5)
        
        # Assert
        assert result == False

    @pytest.mark.asyncio
    async def test_is_favorite_different_user(self, mock_favorites_repo, mock_product_repo):
        """
        Тест: товар в избранном у другого пользователя.
        """
        # Arrange
        service = FavoritesService(
            favorites_repo=mock_favorites_repo,
            product_repo=mock_product_repo
        )
        
        # Товар 5 в избранном у пользователя 1
        mock_favorites_repo._data[1] = [5]
        
        # Act - проверяем для пользователя 2
        result = await service.is_favorite(user_id=2, product_id=5)
        
        # Assert
        assert result == False
