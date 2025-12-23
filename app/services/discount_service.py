"""
DiscountService - сервис управления скидками и промокодами.
"""

from typing import Optional
from decimal import Decimal
from datetime import datetime

from app.dto import Cart, PromoCheckResult, DiscountResult
from app.exceptions import PromocodeNotFoundError, PromocodeExpiredError, PromocodeAlreadyUsedError


# Правила автоматических скидок
AUTO_DISCOUNT_RULES = [
    {'min_amount': Decimal('50000'), 'discount_percent': 5, 'name': 'Скидка 5% при заказе от 50 000₽'},
    {'min_amount': Decimal('100000'), 'discount_percent': 10, 'name': 'Скидка 10% при заказе от 100 000₽'},
]


class DiscountService:
    """Сервис управления скидками и промокодами"""

    def __init__(self, promocode_repo=None):
        self.promocode_repo = promocode_repo

    async def validate_promo(self, code: str, now: datetime = None) -> PromoCheckResult:
        """
        Проверка корректности и актуальности промокода.
        """
        if now is None:
            now = datetime.utcnow()
        
        code = code.strip().upper()
        
        # Получение промокода из БД
        promocode = await self.promocode_repo.get_promocode_by_code(code)
        
        if not promocode:
            return PromoCheckResult(
                valid=False,
                error_message="Промокод не найден"
            )
        
        # Проверка срока действия
        if promocode.valid_from > now:
            return PromoCheckResult(
                valid=False,
                error_message="Промокод ещё не активен"
            )
        
        if promocode.valid_to < now:
            return PromoCheckResult(
                valid=False,
                error_message="Промокод истёк"
            )
        
        # Проверка использования
        if promocode.is_used or promocode.current_uses >= promocode.max_uses:
            return PromoCheckResult(
                valid=False,
                error_message="Промокод уже использован"
            )
        
        return PromoCheckResult(
            valid=True,
            discount_type=promocode.discount_type,
            discount_value=Decimal(str(promocode.discount_value))
        )

    async def apply_discounts(self, cart: Cart, promo_code: Optional[str] = None) -> DiscountResult:
        """
        Применение всех доступных скидок к корзине.
        """
        # Расчёт суммы корзины
        subtotal = Decimal('0')
        for item in cart.items:
            subtotal += item.price * item.qty
        
        # Автоматическая скидка
        auto_discount = self.calculate_auto_discount(subtotal)
        
        # Скидка по промокоду
        promo_discount = Decimal('0')
        applied_rules = []
        
        if auto_discount > 0:
            # Находим применённое правило
            for rule in sorted(AUTO_DISCOUNT_RULES, key=lambda x: x['min_amount'], reverse=True):
                if subtotal >= rule['min_amount']:
                    applied_rules.append(rule['name'])
                    break
        
        if promo_code:
            promo_result = await self.validate_promo(promo_code)
            if promo_result.valid:
                if promo_result.discount_type == 'percent':
                    promo_discount = subtotal * promo_result.discount_value / 100
                else:  # fixed
                    promo_discount = promo_result.discount_value
                
                applied_rules.append(f"Промокод {promo_code}")
        
        # Итоговая скидка (берём максимальную из автоматической и промокода)
        total_discount = max(auto_discount, promo_discount)
        
        # Ограничение скидки суммой заказа
        if total_discount > subtotal:
            total_discount = subtotal
        
        return DiscountResult(
            auto_discount=auto_discount,
            promo_discount=promo_discount,
            total_discount=total_discount,
            applied_rules=applied_rules
        )

    def calculate_auto_discount(self, subtotal: Decimal) -> Decimal:
        """
        Расчёт суммы автоматических скидок по правилам.
        """
        discount = Decimal('0')
        
        # Применяем самое выгодное правило
        for rule in sorted(AUTO_DISCOUNT_RULES, key=lambda x: x['min_amount'], reverse=True):
            if subtotal >= rule['min_amount']:
                discount = subtotal * Decimal(str(rule['discount_percent'])) / 100
                break
        
        return discount

    async def check_promo_usage(self, code: str, user_id: int) -> bool:
        """
        Проверка, использовал ли пользователь промокод ранее.
        """
        code = code.strip().upper()
        return await self.promocode_repo.check_user_usage(code, user_id)
