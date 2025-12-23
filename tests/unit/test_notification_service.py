"""
Блочные тесты модуля уведомлений (NotificationService).
Тесты Б76-Б79 согласно плану тестирования.
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from app.services.notification_service import NotificationService
from tests.conftest import MockOrder, MockUser


@pytest.fixture
def notification_service(mock_bot, mock_user_repo, test_users):
    """Сервис уведомлений с моками"""
    config = {
        'admin_ids': [100008, 100009]  # Telegram ID админов
    }
    return NotificationService(
        bot=mock_bot,
        user_repo=mock_user_repo,
        config=config
    )


@pytest.fixture
def sample_order():
    """Тестовый заказ"""
    return MockOrder(
        id=1,
        user_id=1,
        order_number="ORD-20241201-0001",
        total=Decimal('89990'),
        status='created',
        contact_name="Иван Тестовый",
        contact_phone="+7 999 111-11-11",
        contact_address="г. Москва, ул. Тестовая, д. 1"
    )


class TestNotificationServiceOrderCreated:
    """Тесты уведомления о создании заказа"""

    @pytest.mark.asyncio
    async def test_notify_order_created_success(
        self, notification_service, sample_order, mock_bot
    ):
        """
        Б76: Уведомление о создании заказа.
        Проверяет отправку сообщения пользователю.
        """
        # Act
        await notification_service.notify_order_created(sample_order)
        
        # Assert
        assert len(mock_bot.sent_messages) == 1
        
        message = mock_bot.sent_messages[0]
        assert message['chat_id'] == 100001  # telegram_id пользователя 1
        assert "ORD-20241201-0001" in message['text']
        assert "89 990" in message['text'] or "89990" in message['text']

    @pytest.mark.asyncio
    async def test_notify_order_created_contains_address(
        self, notification_service, sample_order, mock_bot
    ):
        """
        Тест: уведомление содержит адрес доставки.
        """
        # Act
        await notification_service.notify_order_created(sample_order)
        
        # Assert
        message = mock_bot.sent_messages[0]
        assert "Тестовая" in message['text']


class TestNotificationServiceStatusChanged:
    """Тесты уведомления об изменении статуса"""

    @pytest.mark.asyncio
    async def test_notify_status_changed_shipped(
        self, notification_service, mock_bot
    ):
        """
        Б77: Уведомление об отправке заказа.
        Проверяет текст уведомления для статуса shipped.
        """
        # Arrange
        order = MockOrder(
            id=3,
            user_id=1,
            order_number="ORD-20241202-0001",
            total=Decimal('49990'),
            status='shipped'
        )
        
        # Act
        await notification_service.notify_status_changed(order)
        
        # Assert
        assert len(mock_bot.sent_messages) == 1
        message = mock_bot.sent_messages[0]
        assert "отправлен" in message['text'].lower() or "🚚" in message['text']

    @pytest.mark.asyncio
    async def test_notify_status_changed_paid(
        self, notification_service, mock_bot
    ):
        """
        Тест: уведомление об оплате.
        """
        # Arrange
        order = MockOrder(
            id=2,
            user_id=1,
            order_number="ORD-20241201-0002",
            total=Decimal('129990'),
            status='paid'
        )
        
        # Act
        await notification_service.notify_status_changed(order)
        
        # Assert
        message = mock_bot.sent_messages[0]
        assert "оплат" in message['text'].lower() or "💳" in message['text']

    @pytest.mark.asyncio
    async def test_notify_status_changed_delivered(
        self, notification_service, mock_bot
    ):
        """
        Тест: уведомление о доставке.
        """
        # Arrange
        order = MockOrder(
            id=4,
            user_id=1,
            order_number="ORD-20241203-0001",
            total=Decimal('24990'),
            status='delivered'
        )
        
        # Act
        await notification_service.notify_status_changed(order)
        
        # Assert
        message = mock_bot.sent_messages[0]
        assert "доставлен" in message['text'].lower() or "✨" in message['text']

    @pytest.mark.asyncio
    async def test_notify_status_changed_cancelled(
        self, notification_service, mock_bot
    ):
        """
        Тест: уведомление об отмене.
        """
        # Arrange
        order = MockOrder(
            id=5,
            user_id=1,
            order_number="ORD-20241203-0002",
            total=Decimal('19990'),
            status='cancelled'
        )
        
        # Act
        await notification_service.notify_status_changed(order)
        
        # Assert
        message = mock_bot.sent_messages[0]
        assert "отменён" in message['text'].lower() or "❌" in message['text']


class TestNotificationServicePaymentSuccess:
    """Тесты уведомления об успешной оплате"""

    @pytest.mark.asyncio
    async def test_notify_payment_success(
        self, notification_service, mock_bot
    ):
        """
        Б78: Уведомление об успешной оплате.
        Проверяет текст уведомления.
        """
        # Arrange
        order = MockOrder(
            id=2,
            user_id=1,
            order_number="ORD-20241201-0002",
            total=Decimal('129990'),
            status='paid'
        )
        
        # Act
        await notification_service.notify_payment_success(order)
        
        # Assert
        assert len(mock_bot.sent_messages) == 1
        message = mock_bot.sent_messages[0]
        assert "оплат" in message['text'].lower()
        assert "ORD-20241201-0002" in message['text']
        assert "129 990" in message['text'] or "129990" in message['text']

    @pytest.mark.asyncio
    async def test_notify_payment_success_mentions_receipt(
        self, notification_service, mock_bot
    ):
        """
        Тест: уведомление упоминает чек.
        """
        # Arrange
        order = MockOrder(
            id=2,
            user_id=1,
            order_number="ORD-20241201-0002",
            total=Decimal('129990'),
            status='paid'
        )
        
        # Act
        await notification_service.notify_payment_success(order)
        
        # Assert
        message = mock_bot.sent_messages[0]
        assert "чек" in message['text'].lower()


class TestNotificationServiceAdminNotify:
    """Тесты уведомления администраторов"""

    @pytest.mark.asyncio
    async def test_notify_admin_new_order(
        self, notification_service, sample_order, mock_bot
    ):
        """
        Б79: Уведомление админов о новом заказе.
        Проверяет отправку сообщения всем админам.
        """
        # Act
        await notification_service.notify_admin_new_order(sample_order)
        
        # Assert - должно быть отправлено 2 сообщения (2 админа)
        assert len(mock_bot.sent_messages) == 2
        
        admin_chat_ids = {msg['chat_id'] for msg in mock_bot.sent_messages}
        assert 100008 in admin_chat_ids
        assert 100009 in admin_chat_ids

    @pytest.mark.asyncio
    async def test_notify_admin_contains_customer_info(
        self, notification_service, sample_order, mock_bot
    ):
        """
        Тест: уведомление админу содержит данные клиента.
        """
        # Act
        await notification_service.notify_admin_new_order(sample_order)
        
        # Assert
        message = mock_bot.sent_messages[0]
        assert "Иван Тестовый" in message['text']
        assert "+7 999 111-11-11" in message['text']

    @pytest.mark.asyncio
    async def test_notify_admin_no_admins_configured(
        self, mock_bot, mock_user_repo
    ):
        """
        Тест: нет настроенных админов.
        """
        # Arrange
        service = NotificationService(
            bot=mock_bot,
            user_repo=mock_user_repo,
            config={}  # Нет admin_ids
        )
        
        order = MockOrder(
            id=1,
            user_id=1,
            order_number="ORD-20241201-0001",
            total=Decimal('89990')
        )
        
        # Act
        await service.notify_admin_new_order(order)
        
        # Assert - сообщения не отправлены
        assert len(mock_bot.sent_messages) == 0


class TestNotificationServiceErrorHandling:
    """Тесты обработки ошибок"""

    @pytest.mark.asyncio
    async def test_notification_handles_bot_error(
        self, mock_user_repo
    ):
        """
        Тест: обработка ошибки отправки.
        """
        # Arrange
        mock_bot = AsyncMock()
        mock_bot.send_message = AsyncMock(side_effect=Exception("Network error"))
        
        service = NotificationService(
            bot=mock_bot,
            user_repo=mock_user_repo,
            config={'admin_ids': [100008]}
        )
        
        order = MockOrder(
            id=1,
            user_id=1,
            order_number="ORD-20241201-0001",
            total=Decimal('89990')
        )
        
        # Act - не должно быть исключения
        await service.notify_order_created(order)
        
        # Assert
        assert True

    @pytest.mark.asyncio
    async def test_notification_user_not_found(
        self, mock_bot, mock_user_repo
    ):
        """
        Тест: пользователь не найден.
        """
        # Arrange
        service = NotificationService(
            bot=mock_bot,
            user_repo=mock_user_repo,
            config={}
        )
        
        order = MockOrder(
            id=1,
            user_id=999,  # Несуществующий пользователь
            order_number="ORD-20241201-0001",
            total=Decimal('89990')
        )
        
        # Act - не должно быть исключения
        await service.notify_order_created(order)
        
        # Assert - сообщение не отправлено
        assert len(mock_bot.sent_messages) == 0


class TestNotificationServicePriceFormat:
    """Тесты форматирования цен"""

    def test_format_price_with_thousands(self, notification_service):
        """
        Тест: форматирование цены с разделителями.
        """
        # Act
        result = notification_service._format_price(Decimal('129990'))
        
        # Assert
        assert "129" in result
        assert "990" in result

    def test_format_price_small_amount(self, notification_service):
        """
        Тест: форматирование небольшой суммы.
        """
        # Act
        result = notification_service._format_price(Decimal('990'))
        
        # Assert
        assert result == "990"
