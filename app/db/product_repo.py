"""
ProductRepo - репозиторий доступа к данным каталога товаров.
"""

from typing import List, Optional
from decimal import Decimal

from app.db.models import db, Product, Category
from app.dto import ProductCreate


class ProductRepo:
    """Репозиторий для работы с товарами и категориями"""

    async def fetch_categories(self) -> List[Category]:
        """Загрузка всех активных категорий"""
        return await Category.query.where(
            Category.is_active == True
        ).order_by(Category.sort_order).gino.all()

    async def fetch_category_by_id(self, category_id: int) -> Optional[Category]:
        """Получение категории по ID"""
        return await Category.get(category_id)

    async def fetch_category_by_name(self, name: str) -> Optional[Category]:
        """Получение категории по имени"""
        return await Category.query.where(
            Category.name == name
        ).gino.first()

    async def insert_category(self, name: str) -> Category:
        """Создание новой категории"""
        max_order = await db.scalar(
            db.select([db.func.max(Category.sort_order)])
        ) or 0
        
        return await Category.create(
            name=name,
            sort_order=max_order + 1,
            is_active=True
        )

    async def delete_category(self, category_id: int) -> bool:
        """Удаление категории"""
        result = await Category.delete.where(
            Category.id == category_id
        ).gino.status()
        return result[0] == 'DELETE 1'

    async def fetch_products_by_category(self, category_id: int) -> List[Product]:
        """Получение товаров по категории"""
        return await Product.query.where(
            (Product.category_id == category_id) &
            (Product.is_active == True)
        ).gino.all()

    async def fetch_product_by_id(self, product_id: int) -> Optional[Product]:
        """Получение товара по ID"""
        return await Product.get(product_id)

    async def fetch_all_active_products(self) -> List[Product]:
        """Получение всех активных товаров"""
        return await Product.query.where(
            Product.is_active == True
        ).gino.all()

    async def insert_product(self, data: ProductCreate) -> Product:
        """Создание нового товара"""
        return await Product.create(
            name=data.name,
            description=data.description,
            price=Decimal(str(data.price)),
            stock=data.stock,
            category_id=data.category_id,
            image_url=data.image_url,
            is_active=True
        )

    async def update_product(self, product_id: int, data: dict) -> Product:
        """Обновление товара"""
        product = await Product.get(product_id)
        await product.update(**data).apply()
        return product

    async def delete_product(self, product_id: int) -> bool:
        """Мягкое удаление товара"""
        product = await Product.get(product_id)
        if not product:
            return False
        await product.update(is_active=False).apply()
        return True

    async def update_stock(self, product_id: int, delta: int) -> int:
        """Атомарное изменение остатка товара"""
        await db.status(
            db.text(
                "UPDATE products SET stock = stock + :delta WHERE id = :id"
            ).bindparams(delta=delta, id=product_id)
        )
        product = await Product.get(product_id)
        return product.stock

    async def search_products(self, query: str) -> List[Product]:
        """Поиск товаров по названию"""
        search_pattern = f"%{query}%"
        return await Product.query.where(
            (Product.is_active == True) &
            (db.func.lower(Product.name).like(search_pattern.lower()) |
             db.func.lower(Product.description).like(search_pattern.lower()))
        ).gino.all()
