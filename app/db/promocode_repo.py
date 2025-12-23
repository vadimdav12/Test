"""
PromocodeRepo - репозиторий хранения промокодов.
"""

from typing import List, Optional
from datetime import datetime

from app.db.models import db, Promocode, PromocodeUsage


class PromocodeRepo:
    """Репозиторий для работы с промокодами"""

    async def get_promocode_by_code(self, code: str) -> Optional[Promocode]:
        """Получение промокода по коду (регистронезависимый поиск)"""
        return await Promocode.query.where(
            db.func.upper(Promocode.code) == code.upper()
        ).gino.first()

    async def validate_promocode(self, code: str, now: datetime) -> bool:
        """Проверка активности промокода"""
        promocode = await self.get_promocode_by_code(code)
        
        if not promocode:
            return False
        
        if promocode.valid_from > now or promocode.valid_to < now:
            return False
        
        if promocode.is_used or promocode.current_uses >= promocode.max_uses:
            return False
        
        return True

    async def list_active_promocodes(self) -> List[Promocode]:
        """Получение списка активных промокодов"""
        now = datetime.utcnow()
        return await Promocode.query.where(
            (Promocode.valid_from <= now) &
            (Promocode.valid_to >= now) &
            (Promocode.is_used == False)
        ).gino.all()

    async def record_usage(self, code: str, user_id: int, order_id: int) -> None:
        """Запись использования промокода"""
        promocode = await self.get_promocode_by_code(code)
        
        if not promocode:
            return
        
        # Создание записи об использовании
        await PromocodeUsage.create(
            promocode_id=promocode.id,
            user_id=user_id,
            order_id=order_id
        )
        
        # Обновление счётчика
        new_uses = promocode.current_uses + 1
        is_used = new_uses >= promocode.max_uses
        
        await promocode.update(
            current_uses=new_uses,
            is_used=is_used
        ).apply()

    async def check_user_usage(self, code: str, user_id: int) -> bool:
        """Проверка использования промокода пользователем"""
        promocode = await self.get_promocode_by_code(code)
        
        if not promocode:
            return False
        
        usage = await PromocodeUsage.query.where(
            (PromocodeUsage.promocode_id == promocode.id) &
            (PromocodeUsage.user_id == user_id)
        ).gino.first()
        
        return usage is not None
