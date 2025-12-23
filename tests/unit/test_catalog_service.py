"""
Блочные тесты модуля каталога (CatalogService).
Тесты Б01-Б14 согласно плану тестирования.
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock

from app.services.catalog_service import CatalogService
from app.dto import ProductCreate, ProductUpdate
from app.exceptions import (
    ProductNotFoundError,
    CategoryNotEmptyError,
    DuplicateCategoryError,
    ValidationError
)


class TestCatalogServiceCategories:
    """Тесты работы с категориями"""

    @pytest.mark.asyncio
    async def test_get_categories_returns_active_only(self, mock_product_repo, test_categories):
        """
        Б01: Получение списка категорий.
        Проверяет, что возвращаются только активные категории.
        """
        # Arrange
        service = CatalogService(product_repo=mock_product_repo)
        
        # Act
        result = await service.get_categories()
        
        # Assert
        assert len(result) == 5  # 5 активных категорий
        assert all(c.is_active for c in result)
        assert result[0].name == "Смартфоны"  # Первая по sort_order
        
        # Проверяем сортировку
        sort_orders = [c.sort_order for c in result]
        assert sort_orders == sorted(sort_orders)

    @pytest.mark.asyncio
    async def test_create_category_success(self, mock_product_repo):
        """
        Б11: Создание категории.
        Проверяет успешное создание новой категории.
        """
        # Arrange
        service = CatalogService(product_repo=mock_product_repo)
        
        # Act
        result = await service.create_category("Новая категория")
        
        # Assert
        assert result is not None
        assert result.name == "Новая категория"
        assert result.is_active == True
        assert result.id > 0

    @pytest.mark.asyncio
    async def test_create_category_duplicate_raises_error(self, mock_product_repo):
        """
        Б12: Создание дублирующей категории.
        Проверяет, что при попытке создать категорию с существующим именем 
        генерируется исключение DuplicateCategoryError.
        """
        # Arrange
        service = CatalogService(product_repo=mock_product_repo)
        
        # Act & Assert
        with pytest.raises(DuplicateCategoryError) as exc_info:
            await service.create_category("Смартфоны")  # Уже существует
        
        assert "Смартфоны" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_create_category_empty_name_raises_error(self, mock_product_repo):
        """
        Тест валидации: пустое название категории.
        """
        # Arrange
        service = CatalogService(product_repo=mock_product_repo)
        
        # Act & Assert
        with pytest.raises(ValidationError):
            await service.create_category("")
        
        with pytest.raises(ValidationError):
            await service.create_category("   ")

    @pytest.mark.asyncio
    async def test_delete_category_empty_success(self, mock_product_repo):
        """
        Б13: Удаление пустой категории.
        Проверяет успешное удаление категории без товаров.
        """
        # Arrange
        service = CatalogService(product_repo=mock_product_repo)
        
        # Создаём пустую категорию
        new_category = await service.create_category("Пустая категория")
        
        # Мокируем возврат пустого списка товаров для этой категории
        original_fetch = mock_product_repo.fetch_products_by_category
        async def mock_fetch(cat_id):
            if cat_id == new_category.id:
                return []
            return await original_fetch(cat_id)
        mock_product_repo.fetch_products_by_category = mock_fetch
        
        # Act
        result = await service.delete_category(new_category.id)
        
        # Assert
        assert result == True

    @pytest.mark.asyncio
    async def test_delete_category_with_products_raises_error(self, mock_product_repo):
        """
        Б14: Удаление непустой категории.
        Проверяет, что при удалении категории с товарами генерируется 
        исключение CategoryNotEmptyError.
        """
        # Arrange
        service = CatalogService(product_repo=mock_product_repo)
        
        # Act & Assert - категория 1 (Смартфоны) содержит товары
        with pytest.raises(CategoryNotEmptyError) as exc_info:
            await service.delete_category(1)
        
        assert exc_info.value.category_id == 1
        assert exc_info.value.products_count > 0


class TestCatalogServiceProducts:
    """Тесты работы с товарами"""

    @pytest.mark.asyncio
    async def test_get_products_by_category(self, mock_product_repo):
        """
        Б02: Получение товаров категории.
        Проверяет выборку товаров категории «Смартфоны» (id=1).
        """
        # Arrange
        service = CatalogService(product_repo=mock_product_repo)
        
        # Act
        result = await service.get_products_by_category(1)
        
        # Assert
        assert len(result) == 4  # 4 активных товара в категории Смартфоны
        assert all(p.category_id == 1 for p in result)
        assert all(p.is_active for p in result)

    @pytest.mark.asyncio
    async def test_get_products_by_nonexistent_category(self, mock_product_repo):
        """
        Б03: Получение товаров несуществующей категории.
        Проверяет, что возвращается пустой список без исключений.
        """
        # Arrange
        service = CatalogService(product_repo=mock_product_repo)
        
        # Act
        result = await service.get_products_by_category(999)
        
        # Assert
        assert result == []

    @pytest.mark.asyncio
    async def test_get_product_by_id(self, mock_product_repo):
        """
        Б04: Получение товара по ID.
        Проверяет загрузку карточки товара.
        """
        # Arrange
        service = CatalogService(product_repo=mock_product_repo)
        
        # Act
        result = await service.get_product(3)  # Samsung Galaxy S24
        
        # Assert
        assert result is not None
        assert result.id == 3
        assert result.name == "Samsung Galaxy S24"
        assert result.price == Decimal('79990')
        assert result.stock == 10

    @pytest.mark.asyncio
    async def test_get_product_nonexistent_returns_none(self, mock_product_repo):
        """
        Б05: Получение несуществующего товара.
        Проверяет, что возвращается None.
        """
        # Arrange
        service = CatalogService(product_repo=mock_product_repo)
        
        # Act
        result = await service.get_product(99999)
        
        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_product_inactive_returns_none(self, mock_product_repo):
        """
        Дополнительный тест: неактивный товар не возвращается.
        """
        # Arrange
        service = CatalogService(product_repo=mock_product_repo)
        
        # Act - id=99 это архивный товар
        result = await service.get_product(99)
        
        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_product_stock(self, mock_product_repo):
        """
        Б06: Получение остатка товара.
        Проверяет метод get_product_stock.
        """
        # Arrange
        service = CatalogService(product_repo=mock_product_repo)
        
        # Act
        stock = await service.get_product_stock(3)  # Samsung Galaxy S24, stock=10
        
        # Assert
        assert stock == 10

    @pytest.mark.asyncio
    async def test_get_product_stock_nonexistent_returns_zero(self, mock_product_repo):
        """
        Тест: остаток несуществующего товара равен 0.
        """
        # Arrange
        service = CatalogService(product_repo=mock_product_repo)
        
        # Act
        stock = await service.get_product_stock(99999)
        
        # Assert
        assert stock == 0

    @pytest.mark.asyncio
    async def test_create_product_success(self, mock_product_repo):
        """
        Б07: Создание товара (админ).
        Проверяет добавление нового товара.
        """
        # Arrange
        service = CatalogService(product_repo=mock_product_repo)
        data = ProductCreate(
            name="Тестовый товар NEW",
            description="Описание тестового товара",
            price=Decimal('19990'),
            stock=25,
            category_id=1
        )
        
        # Act
        result = await service.create_product(data)
        
        # Assert
        assert result is not None
        assert result.id > 0
        assert result.name == "Тестовый товар NEW"
        assert result.price == Decimal('19990')
        assert result.stock == 25
        assert result.is_active == True

    @pytest.mark.asyncio
    async def test_create_product_invalid_data_raises_error(self, mock_product_repo):
        """
        Б08: Создание товара с невалидными данными.
        Проверяет валидацию обязательных полей.
        """
        # Arrange
        service = CatalogService(product_repo=mock_product_repo)
        
        # Act & Assert - пустое название
        with pytest.raises(ValidationError):
            await service.create_product(ProductCreate(
                name="",
                price=Decimal('100'),
                category_id=1
            ))
        
        # Act & Assert - отрицательная цена
        with pytest.raises(ValidationError):
            await service.create_product(ProductCreate(
                name="Товар",
                price=Decimal('-100'),
                category_id=1
            ))
        
        # Act & Assert - несуществующая категория
        with pytest.raises(ValidationError):
            await service.create_product(ProductCreate(
                name="Товар",
                price=Decimal('100'),
                category_id=999
            ))

    @pytest.mark.asyncio
    async def test_update_product_success(self, mock_product_repo):
        """
        Б09: Обновление товара.
        Проверяет изменение цены и остатка.
        """
        # Arrange
        service = CatalogService(product_repo=mock_product_repo)
        
        # Act
        result = await service.update_product(3, ProductUpdate(
            price=Decimal('69990'),
            stock=15
        ))
        
        # Assert
        assert result is not None
        assert result.price == Decimal('69990')
        assert result.stock == 15

    @pytest.mark.asyncio
    async def test_update_product_nonexistent_raises_error(self, mock_product_repo):
        """
        Тест: обновление несуществующего товара.
        """
        # Arrange
        service = CatalogService(product_repo=mock_product_repo)
        
        # Act & Assert
        with pytest.raises(ProductNotFoundError):
            await service.update_product(99999, ProductUpdate(price=Decimal('100')))

    @pytest.mark.asyncio
    async def test_delete_product_success(self, mock_product_repo):
        """
        Б10: Мягкое удаление товара.
        Проверяет деактивацию товара.
        """
        # Arrange
        service = CatalogService(product_repo=mock_product_repo)
        
        # Act
        result = await service.delete_product(50)  # Тестовый товар
        
        # Assert
        assert result == True
        
        # Проверяем, что товар теперь не виден
        product = await service.get_product(50)
        assert product is None

    @pytest.mark.asyncio
    async def test_delete_product_nonexistent_returns_false(self, mock_product_repo):
        """
        Тест: удаление несуществующего товара возвращает False.
        """
        # Arrange
        service = CatalogService(product_repo=mock_product_repo)
        
        # Act
        result = await service.delete_product(99999)
        
        # Assert
        assert result == False

    @pytest.mark.asyncio
    async def test_delete_product_already_deleted_returns_false(self, mock_product_repo):
        """
        Тест: повторное удаление возвращает False.
        """
        # Arrange
        service = CatalogService(product_repo=mock_product_repo)
        
        # Act - товар id=99 уже неактивен
        result = await service.delete_product(99)
        
        # Assert
        assert result == False
