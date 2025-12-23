"""
PaymentService - сервис обработки платежей.
"""

from datetime import datetime, timedelta
from decimal import Decimal
import hashlib
import hmac

from app.db.models import Order
from app.dto import PaymentSession, PaymentResult
from app.exceptions import PaymentGatewayError, InvalidSignatureError, OrderNotFoundError


class PaymentStatus:
    """Статусы платежа"""
    PENDING = 'pending'
    PROCESSING = 'processing'
    SUCCESS = 'success'
    FAILED = 'failed'
    REFUNDED = 'refunded'


class PaymentService:
    """Сервис обработки платежей"""

    def __init__(self, order_repo=None, payment_gateway=None, 
                 receipt_service=None, notification_service=None):
        self.order_repo = order_repo
        self.payment_gateway = payment_gateway
        self.receipt_service = receipt_service
        self.notification_service = notification_service

    async def init_payment(self, order: Order) -> PaymentSession:
        """
        Инициализация платёжной сессии.
        """
        if order.status != 'created':
            raise PaymentGatewayError(f"Заказ {order.id} не может быть оплачен в статусе '{order.status}'")
        
        try:
            session = await self.payment_gateway.create_session(order)
            return session
        except Exception as e:
            raise PaymentGatewayError(str(e))

    async def handle_callback(self, payload: dict) -> PaymentResult:
        """
        Обработка webhook-уведомления от платёжного провайдера.
        """
        # Проверка обязательных полей
        required_fields = ['session_id', 'status', 'order_id']
        for field in required_fields:
            if field not in payload:
                return PaymentResult(
                    success=False,
                    error_message=f"Отсутствует обязательное поле: {field}"
                )
        
        # Проверка подписи (если есть)
        if 'signature' in payload:
            if not self._verify_signature(payload):
                raise InvalidSignatureError("Неверная подпись callback")
        
        order_id = payload['order_id']
        status = payload['status']
        
        # Получение заказа
        order = await self.order_repo.get_order_by_id(order_id)
        if not order:
            return PaymentResult(
                success=False,
                error_message=f"Заказ {order_id} не найден"
            )
        
        # Обработка успешной оплаты
        if status == 'success':
            await self.order_repo.update_order_status(order_id, 'paid')
            
            # Отправка уведомления
            if self.notification_service:
                order = await self.order_repo.get_order_by_id(order_id)
                await self.notification_service.notify_payment_success(order)
            
            # Генерация и отправка чека
            if self.receipt_service:
                try:
                    receipt_path = await self.receipt_service.generate_receipt_pdf(order_id)
                    user = await self.order_repo.get_user_by_order(order_id)
                    if user:
                        await self.receipt_service.send_receipt(user.telegram_id, receipt_path)
                except Exception as e:
                    print(f"Ошибка генерации чека: {e}")
            
            return PaymentResult(success=True, order_id=order_id)
        
        elif status == 'failed':
            return PaymentResult(
                success=False,
                order_id=order_id,
                error_message="Платёж отклонён"
            )
        
        return PaymentResult(
            success=False,
            error_message=f"Неизвестный статус платежа: {status}"
        )

    async def get_payment_status(self, order_id: int) -> str:
        """
        Получение текущего статуса платежа.
        """
        status = await self.payment_gateway.get_status(order_id)
        return status

    def get_payment_url(self, session: PaymentSession) -> str:
        """
        Формирование URL для перенаправления на страницу оплаты.
        """
        return session.payment_url

    def _verify_signature(self, payload: dict) -> bool:
        """
        Проверка подписи callback.
        """
        signature = payload.get('signature', '')
        
        # Формируем строку для проверки
        check_string = f"{payload['session_id']}:{payload['order_id']}:{payload['status']}"
        
        # Получаем секретный ключ
        secret_key = self.payment_gateway.get_secret_key() if self.payment_gateway else 'test_secret'
        
        # Вычисляем ожидаемую подпись
        expected = hmac.new(
            secret_key.encode(),
            check_string.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(signature, expected)
