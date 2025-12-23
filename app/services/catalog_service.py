"""
CatalogService - сервис работы с каталогом товаров.
"""

from typing import List, Optional
from decimal import Decimal

from app.db.models import Category, Product
from app.dto import ProductCreate, ProductUpdate
from app.exceptions import (
    ProductNotFoundError,
    CategoryNotFoundError,
    CategoryNotEmptyError,
    DuplicateCategoryError,
    ValidationError
)


class CatalogService:
    """Сервис управления каталогом товаров"""

    def __init__(self, product_repo=None, category_repo=None):
        self.product_repo = product_repo
        self.category_repo = category_repo

    async def get_categories(self) -> List[Category]:
        """
        Получение полного списка активных категорий товаров.
        Категории возвращаются в порядке sort_order.
        """
        return await self.product_repo.fetch_categories()

    async def get_products_by_category(self, category_id: int) -> List[Product]:
        """
        Получение списка товаров указанной категории.
        Возвращаются только активные товары.
        """
        return await self.product_repo.fetch_products_by_category(category_id)

    async def get_product(self, product_id: int) -> Optional[Product]:
        """
        Получение полной информации о товаре по его ID.
        """
        product = await self.product_repo.fetch_product_by_id(product_id)
        if product and not product.is_active:
            return None
        return product

    async def get_product_stock(self, product_id: int) -> int:
        """
        Получение текущего доступного остатка товара.
        Возвращает 0, если товар не найден.
        """
        product = await self.product_repo.fetch_product_by_id(product_id)
        if not product:
            return 0
        return product.stock

    async def create_product(self, data: ProductCreate) -> Product:
        """
        Создание нового товара в каталоге.
        """
        # Валидация данных
        if not data.name or len(data.name.strip()) == 0:
            raise ValidationError("Название товара не может быть пустым")
        
        if data.price <= 0:
            raise ValidationError("Цена должна быть положительным числом")
        
        # Проверка существования категории
        category = await self.product_repo.fetch_category_by_id(data.category_id)
        if not category:
            raise ValidationError(f"Категория с id={data.category_id} не существует")

        return await self.product_repo.insert_product(data)

    async def update_product(self, product_id: int, data: ProductUpdate) -> Product:
        """
        Обновление информации о существующем товаре.
        """
        product = await self.product_repo.fetch_product_by_id(product_id)
        if not product:
            raise ProductNotFoundError(product_id)

        update_data = {}
        if data.name is not None:
            update_data['name'] = data.name
        if data.price is not None:
            update_data['price'] = data.price
        if data.category_id is not None:
            update_data['category_id'] = data.category_id
        if data.description is not None:
            update_data['description'] = data.description
        if data.stock is not None:
            update_data['stock'] = data.stock
        if data.image_url is not None:
            update_data['image_url'] = data.image_url

        return await self.product_repo.update_product(product_id, update_data)

    async def delete_product(self, product_id: int) -> bool:
        """
        Мягкое удаление товара (установка is_active=False).
        """
        product = await self.product_repo.fetch_product_by_id(product_id)
        if not product or not product.is_active:
            return False
        
        return await self.product_repo.delete_product(product_id)

    async def create_category(self, name: str) -> Category:
        """
        Создание новой категории товаров.
        """
        name = name.strip()
        if not name:
            raise ValidationError("Название категории не может быть пустым")
        
        if len(name) > 100:
            raise ValidationError("Название категории слишком длинное")
        
        # Проверка уникальности
        existing = await self.product_repo.fetch_category_by_name(name)
        if existing:
            raise DuplicateCategoryError(name)

        return await self.product_repo.insert_category(name)

    async def delete_category(self, category_id: int) -> bool:
        """
        Удаление категории. Требует отсутствия товаров в категории.
        """
        category = await self.product_repo.fetch_category_by_id(category_id)
        if not category:
            return False
        
        # Проверка наличия товаров
        products = await self.product_repo.fetch_products_by_category(category_id)
        active_products = [p for p in products if p.is_active]
        
        if active_products:
            raise CategoryNotEmptyError(category_id, len(active_products))
        
        return await self.product_repo.delete_category(category_id)
