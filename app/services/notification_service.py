"""
NotificationService - сервис отправки уведомлений.
"""

from typing import List

from app.db.models import Order


# Тексты уведомлений по статусам
STATUS_MESSAGES = {
    'created': '📦 Ваш заказ {order_number} создан и ожидает оплаты.\nСумма к оплате: {total} ₽',
    'confirmed': '✅ Заказ {order_number} подтверждён и готовится к отправке.',
    'paid': '💳 Оплата заказа {order_number} получена. Спасибо за покупку!',
    'shipped': '🚚 Заказ {order_number} отправлен. Ожидайте доставку.',
    'delivered': '✨ Заказ {order_number} доставлен. Благодарим за покупку!',
    'cancelled': '❌ Заказ {order_number} отменён.'
}


class NotificationService:
    """Сервис отправки уведомлений через Telegram"""

    def __init__(self, bot=None, user_repo=None, config=None):
        self.bot = bot
        self.user_repo = user_repo
        self.config = config or {}

    def _get_admin_ids(self) -> List[int]:
        """Получение списка ID администраторов"""
        return self.config.get('admin_ids', [])

    def _format_price(self, amount) -> str:
        """Форматирование цены"""
        return f"{int(amount):,}".replace(',', ' ')

    async def notify_order_created(self, order: Order) -> None:
        """
        Уведомление пользователю о создании заказа.
        """
        try:
            user = await self.user_repo.get_user_by_id(order.user_id)
            if not user:
                return
            
            message = (
                f"📦 Ваш заказ {order.order_number} успешно создан!\n\n"
                f"💰 Сумма к оплате: {self._format_price(order.total)} ₽\n"
                f"📍 Адрес доставки: {order.contact_address}\n\n"
                f"Для оплаты нажмите кнопку ниже."
            )
            
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=message
            )
        except Exception as e:
            # Логируем ошибку, но не прерываем основной процесс
            print(f"Ошибка отправки уведомления о создании заказа: {e}")

    async def notify_status_changed(self, order: Order) -> None:
        """
        Уведомление пользователю об изменении статуса заказа.
        """
        try:
            user = await self.user_repo.get_user_by_id(order.user_id)
            if not user:
                return
            
            template = STATUS_MESSAGES.get(order.status)
            if not template:
                return
            
            message = template.format(
                order_number=order.order_number,
                total=self._format_price(order.total)
            )
            
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=message
            )
        except Exception as e:
            print(f"Ошибка отправки уведомления о статусе: {e}")

    async def notify_payment_success(self, order: Order) -> None:
        """
        Уведомление пользователю об успешной оплате.
        """
        try:
            user = await self.user_repo.get_user_by_id(order.user_id)
            if not user:
                return
            
            message = (
                f"✅ Оплата заказа {order.order_number} успешно получена!\n\n"
                f"💰 Сумма: {self._format_price(order.total)} ₽\n\n"
                f"Ваш электронный чек будет отправлен следующим сообщением.\n"
                f"Благодарим за покупку! 🎉"
            )
            
            await self.bot.send_message(
                chat_id=user.telegram_id,
                text=message
            )
        except Exception as e:
            print(f"Ошибка отправки уведомления об оплате: {e}")

    async def notify_admin_new_order(self, order: Order) -> None:
        """
        Уведомление администраторов о новом заказе.
        """
        admin_ids = self._get_admin_ids()
        
        if not admin_ids:
            return
        
        message = (
            f"🆕 Новый заказ {order.order_number}\n\n"
            f"👤 Клиент: {order.contact_name}\n"
            f"📱 Телефон: {order.contact_phone}\n"
            f"📍 Адрес: {order.contact_address}\n\n"
            f"💰 Сумма: {self._format_price(order.total)} ₽"
        )
        
        for admin_id in admin_ids:
            try:
                await self.bot.send_message(
                    chat_id=admin_id,
                    text=message
                )
            except Exception as e:
                print(f"Ошибка отправки уведомления админу {admin_id}: {e}")
