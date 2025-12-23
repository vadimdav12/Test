"""
FavoritesService - сервис управления списком избранных товаров.
"""

from typing import List

from app.db.models import Product
from app.exceptions import ProductNotFoundError


class FavoritesService:
    """Сервис управления избранным"""

    def __init__(self, favorites_repo=None, product_repo=None):
        self.favorites_repo = favorites_repo
        self.product_repo = product_repo

    async def add_favorite(self, user_id: int, product_id: int) -> None:
        """
        Добавление товара в избранное.
        Операция идемпотентна - повторное добавление не создаёт дубликатов.
        """
        # Проверка существования товара
        product = await self.product_repo.fetch_product_by_id(product_id)
        if not product or not product.is_active:
            raise ProductNotFoundError(product_id)
        
        # Добавление (с ON CONFLICT DO NOTHING)
        await self.favorites_repo.add_favorite(user_id, product_id)

    async def remove_favorite(self, user_id: int, product_id: int) -> None:
        """
        Удаление товара из избранного.
        Операция идемпотентна.
        """
        await self.favorites_repo.remove_favorite(user_id, product_id)

    async def list_favorites(self, user_id: int) -> List[Product]:
        """
        Получение списка избранных товаров пользователя.
        Возвращаются только активные товары.
        """
        favorites = await self.favorites_repo.get_favorites(user_id)
        
        products = []
        for fav in favorites:
            product = await self.product_repo.fetch_product_by_id(fav.product_id)
            if product and product.is_active:
                products.append(product)
        
        return products

    async def is_favorite(self, user_id: int, product_id: int) -> bool:
        """
        Проверка наличия товара в избранном.
        """
        return await self.favorites_repo.exists_favorite(user_id, product_id)
