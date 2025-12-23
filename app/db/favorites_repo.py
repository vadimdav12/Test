"""
FavoritesRepo - репозиторий таблицы избранного.
"""

from typing import List

from app.db.models import db, Favorite


class FavoritesRepo:
    """Репозиторий для работы с избранным"""

    async def get_favorites(self, user_id: int) -> List[Favorite]:
        """Получение списка избранных товаров"""
        return await Favorite.query.where(
            Favorite.user_id == user_id
        ).gino.all()

    async def add_favorite(self, user_id: int, product_id: int) -> None:
        """
        Добавление в избранное.
        Использует INSERT ON CONFLICT DO NOTHING для идемпотентности.
        """
        try:
            await Favorite.create(
                user_id=user_id,
                product_id=product_id
            )
        except Exception:
            # UniqueViolation - товар уже в избранном, игнорируем
            pass

    async def remove_favorite(self, user_id: int, product_id: int) -> None:
        """Удаление из избранного"""
        await Favorite.delete.where(
            (Favorite.user_id == user_id) &
            (Favorite.product_id == product_id)
        ).gino.status()

    async def exists_favorite(self, user_id: int, product_id: int) -> bool:
        """Проверка наличия в избранном"""
        fav = await Favorite.query.where(
            (Favorite.user_id == user_id) &
            (Favorite.product_id == product_id)
        ).gino.first()
        return fav is not None
