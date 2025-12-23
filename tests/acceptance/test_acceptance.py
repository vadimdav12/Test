"""
Приёмочные тесты телеграм-бота.
Тесты А01-А12 согласно плану тестирования.

Проверяют пользовательские сценарии end-to-end:
User → Bot → Full System → Response
"""

import pytest
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from app.services.catalog_service import CatalogService
from app.services.cart_service import CartService
from app.services.order_service import OrderService
from app.services.discount_service import DiscountService
from app.services.search_service import SearchService
from app.services.favorites_service import FavoritesService
from app.services.payment_service import PaymentService
from app.services.receipt_service import ReceiptService
from app.services.notification_service import NotificationService
from app.services.profile_service import ProfileService
from app.dto import ContactData, ProfileUpdate


class TestUserJourneyNewCustomer:
    """Приёмочные тесты: путь нового покупателя"""

    @pytest.fixture
    def full_system(
        self, mock_product_repo, mock_cart_repo, mock_order_repo,
        mock_promocode_repo, mock_user_repo, mock_favorites_repo,
        mock_payment_gateway, mock_bot, tmp_path
    ):
        """Полная система со всеми сервисами"""
        cart_service = CartService(
            cart_repo=mock_cart_repo,
            product_repo=mock_product_repo
        )
        
        discount_service = DiscountService(
            promocode_repo=mock_promocode_repo
        )
        
        notification_service = NotificationService(
            bot=mock_bot,
            user_repo=mock_user_repo,
            config={'admin_ids': [100008, 100009]}
        )
        
        receipt_service = ReceiptService(
            order_repo=mock_order_repo,
            bot=mock_bot,
            receipts_dir=str(tmp_path / "receipts")
        )
        
        order_service = OrderService(
            order_repo=mock_order_repo,
            cart_service=cart_service,
            product_repo=mock_product_repo,
            discount_service=discount_service,
            notification_service=notification_service
        )
        
        payment_service = PaymentService(
            order_repo=mock_order_repo,
            payment_gateway=mock_payment_gateway,
            receipt_service=receipt_service,
            notification_service=notification_service
        )
        
        catalog_service = CatalogService(product_repo=mock_product_repo)
        
        search_service = SearchService(product_repo=mock_product_repo)
        
        favorites_service = FavoritesService(
            favorites_repo=mock_favorites_repo,
            product_repo=mock_product_repo
        )
        
        profile_service = ProfileService(
            user_repo=mock_user_repo,
            order_repo=mock_order_repo,
            cart_service=cart_service
        )
        
        return {
            'cart': cart_service,
            'order': order_service,
            'discount': discount_service,
            'notification': notification_service,
            'receipt': receipt_service,
            'payment': payment_service,
            'catalog': catalog_service,
            'search': search_service,
            'favorites': favorites_service,
            'profile': profile_service,
            'bot': mock_bot
        }

    @pytest.mark.asyncio
    async def test_new_customer_full_purchase_journey(
        self, full_system, mock_cart_repo, test_products
    ):
        """
        А01: Полный путь нового покупателя.
        /start → каталог → выбор товара → корзина → оформление → оплата
        """
        user_id = 4  # Новый пользователь
        bot = full_system['bot']
        
        # Шаг 1: /start - приветствие
        welcome_text = (
            "👋 Добро пожаловать в наш магазин!\n\n"
            "Выберите действие из меню ниже."
        )
        await bot.send_message(chat_id=100004, text=welcome_text)
        
        # Шаг 2: Просмотр каталога
        categories = await full_system['catalog'].get_categories()
        assert len(categories) == 5
        
        # Шаг 3: Выбор категории "Смартфоны"
        products = await full_system['catalog'].get_products_by_category(1)
        assert len(products) == 4
        
        # Шаг 4: Добавление Samsung Galaxy S24 в корзину
        product_id = 3  # Samsung Galaxy S24
        initial_stock = test_products[2].stock
        
        await full_system['cart'].add_item(user_id, product_id, 1)
        
        # Шаг 5: Просмотр корзины
        cart = await full_system['cart'].get_cart(user_id)
        assert not cart.is_empty
        assert cart.items[0].product_id == product_id
        
        # Шаг 6: Оформление заказа
        contact = ContactData(
            name="Новый Покупатель",
            phone="+7 999 000-00-00",
            address="г. Москва, ул. Новая, д. 1, кв. 1"
        )
        
        order = await full_system['order'].create_order(
            user_id=user_id,
            contact=contact,
            payment_method='card'
        )
        
        assert order is not None
        assert order.status == 'created'
        assert order.total == Decimal('79990')
        
        # Шаг 7: Корзина очищена
        cart_after = await full_system['cart'].get_cart(user_id)
        assert cart_after.is_empty
        
        # Шаг 8: Товар зарезервирован
        assert test_products[2].stock == initial_stock - 1
        
        # Шаг 9: Уведомления отправлены
        assert len(bot.sent_messages) >= 2  # Приветствие + уведомление о заказе

    @pytest.mark.asyncio
    async def test_customer_search_and_purchase(self, full_system, mock_cart_repo):
        """
        А02: Поиск товара и покупка.
        Поиск "айфон" → выбор → корзина → заказ
        """
        user_id = 4
        
        # Шаг 1: Поиск товара
        results = await full_system['search'].search_products("айфон")
        assert len(results) > 0
        
        # Находим iPhone 15 (stock > 0)
        iphone = next((r for r in results if r.product_id == 2), None)
        assert iphone is not None
        
        # Шаг 2: Добавление в корзину
        await full_system['cart'].add_item(user_id, iphone.product_id, 1)
        
        # Шаг 3: Проверка корзины
        cart = await full_system['cart'].get_cart(user_id)
        totals = full_system['cart'].calc_totals(cart)
        
        assert totals.subtotal == Decimal('89990')
        assert totals.items_count == 1

    @pytest.mark.asyncio
    async def test_customer_with_promocode(self, full_system, mock_cart_repo):
        """
        А03: Покупка с промокодом.
        Корзина → промокод SAVE10 → скидка 10% → заказ
        """
        user_id = 4
        
        # Добавляем товар
        mock_cart_repo._data[user_id] = [
            {'product_id': 5, 'qty': 1, 'name': 'MacBook Pro 14',
             'price': Decimal('199990'), 'stock': 2, 'is_active': True}
        ]
        
        # Применяем промокод
        cart = await full_system['cart'].get_cart(user_id)
        discount_result = await full_system['discount'].apply_discounts(cart, "SAVE10")
        
        # Проверяем скидку
        assert discount_result.promo_discount == Decimal('19999')  # 10% от 199990
        
        # Итого с учётом скидки
        totals = full_system['cart'].calc_totals(cart, discount_result.total_discount)
        assert totals.total == Decimal('179991')  # 199990 - 19999


class TestUserJourneyReturningCustomer:
    """Приёмочные тесты: путь постоянного покупателя"""

    @pytest.fixture
    def returning_user_system(
        self, mock_product_repo, mock_cart_repo, mock_order_repo,
        mock_user_repo, mock_favorites_repo, mock_bot
    ):
        """Система для постоянного покупателя"""
        cart_service = CartService(
            cart_repo=mock_cart_repo,
            product_repo=mock_product_repo
        )
        
        favorites_service = FavoritesService(
            favorites_repo=mock_favorites_repo,
            product_repo=mock_product_repo
        )
        
        profile_service = ProfileService(
            user_repo=mock_user_repo,
            order_repo=mock_order_repo,
            cart_service=cart_service
        )
        
        return {
            'cart': cart_service,
            'favorites': favorites_service,
            'profile': profile_service,
            'bot': mock_bot
        }

    @pytest.mark.asyncio
    async def test_returning_customer_repeat_order(
        self, returning_user_system, mock_order_repo, mock_cart_repo
    ):
        """
        А04: Повторение предыдущего заказа.
        История заказов → повторить заказ #2 → корзина заполнена
        """
        user_id = 1  # Постоянный покупатель
        
        # Шаг 1: Просмотр истории заказов
        orders = await returning_user_system['profile'].get_order_history(user_id)
        assert len(orders) == 3
        
        # Шаг 2: Выбор заказа для повторения
        order_to_repeat = orders[1]  # Заказ #2
        
        # Мокируем позиции заказа
        from tests.conftest import MockOrderItem
        mock_order_repo.get_order_items = AsyncMock(return_value=[
            MockOrderItem(1, 2, 3, "Samsung Galaxy S24", Decimal('79990'), 1)
        ])
        
        # Шаг 3: Повторение заказа
        cart = await returning_user_system['profile'].repeat_order(user_id, order_to_repeat.id)
        
        # Шаг 4: Проверка корзины
        assert cart is not None

    @pytest.mark.asyncio
    async def test_returning_customer_favorites_to_cart(
        self, returning_user_system, mock_favorites_repo, mock_cart_repo
    ):
        """
        А05: Покупка из избранного.
        Избранное → добавить в корзину → оформить
        """
        user_id = 1
        
        # Шаг 1: Добавляем товары в избранное
        await returning_user_system['favorites'].add_favorite(user_id, 3)  # Samsung
        await returning_user_system['favorites'].add_favorite(user_id, 9)  # AirPods
        
        # Шаг 2: Получаем список избранного
        favorites = await returning_user_system['favorites'].list_favorites(user_id)
        assert len(favorites) == 2
        
        # Шаг 3: Добавляем все избранные в корзину
        for product in favorites:
            await returning_user_system['cart'].add_item(user_id, product.id, 1)
        
        # Шаг 4: Проверяем корзину
        cart = await returning_user_system['cart'].get_cart(user_id)
        assert len(cart.items) == 2

    @pytest.mark.asyncio
    async def test_customer_update_profile(self, returning_user_system):
        """
        А06: Обновление профиля.
        Профиль → изменить телефон → сохранить
        """
        user_id = 1
        
        # Шаг 1: Получение текущего профиля
        profile = await returning_user_system['profile'].get_profile(user_id)
        old_phone = profile.phone
        
        # Шаг 2: Обновление телефона
        update_data = ProfileUpdate(phone="+7 999 999-99-99")
        updated_profile = await returning_user_system['profile'].update_profile(user_id, update_data)
        
        # Шаг 3: Проверка обновления
        assert updated_profile is not None


class TestEdgeCases:
    """Приёмочные тесты: граничные случаи"""

    @pytest.mark.asyncio
    async def test_out_of_stock_handling(
        self, mock_product_repo, mock_cart_repo, mock_bot
    ):
        """
        А07: Попытка купить товар без остатка.
        Выбор iPhone 15 Pro (stock=0) → сообщение "нет в наличии"
        """
        cart_service = CartService(
            cart_repo=mock_cart_repo,
            product_repo=mock_product_repo
        )
        
        user_id = 4
        product_id = 1  # iPhone 15 Pro, stock=0
        
        # Попытка добавления
        from app.exceptions import InsufficientStockError
        
        try:
            await cart_service.add_item(user_id, product_id, 1)
            assert False, "Должно быть исключение"
        except InsufficientStockError as e:
            # Отправляем сообщение пользователю
            await mock_bot.send_message(
                chat_id=100004,
                text=f"❌ Товар '{e.product_name}' временно отсутствует на складе"
            )
        
        # Проверяем сообщение
        assert len(mock_bot.sent_messages) == 1
        assert "отсутствует" in mock_bot.sent_messages[0]['text']

    @pytest.mark.asyncio
    async def test_expired_promocode(self, mock_promocode_repo, mock_bot):
        """
        А08: Использование истёкшего промокода.
        Ввод OLD → сообщение "промокод истёк"
        """
        discount_service = DiscountService(promocode_repo=mock_promocode_repo)
        
        # Проверка промокода
        result = await discount_service.validate_promo("OLD", datetime.utcnow())
        
        assert result.valid == False
        assert "истёк" in result.error_message
        
        # Отправляем сообщение
        await mock_bot.send_message(
            chat_id=100001,
            text=f"❌ {result.error_message}"
        )
        
        assert "истёк" in mock_bot.sent_messages[0]['text']

    @pytest.mark.asyncio
    async def test_empty_cart_checkout(self, mock_cart_repo, mock_order_repo, mock_bot):
        """
        А09: Оформление пустой корзины.
        Корзина пуста → "Добавьте товары"
        """
        from app.exceptions import EmptyCartError
        
        cart_service = CartService(cart_repo=mock_cart_repo, product_repo=AsyncMock())
        order_service = OrderService(
            order_repo=mock_order_repo,
            cart_service=cart_service
        )
        
        user_id = 4  # Пустая корзина
        
        contact = ContactData(
            name="Тест",
            phone="+7 999 000-00-00",
            address="Адрес тестовый длинный"
        )
        
        try:
            await order_service.create_order(user_id, contact)
            assert False, "Должно быть исключение"
        except EmptyCartError:
            await mock_bot.send_message(
                chat_id=100004,
                text="🛒 Ваша корзина пуста. Добавьте товары перед оформлением."
            )
        
        assert "пуста" in mock_bot.sent_messages[0]['text']

    @pytest.mark.asyncio
    async def test_search_no_results(self, mock_product_repo, mock_bot):
        """
        А10: Поиск без результатов.
        Поиск "xyznonexistent" → "Ничего не найдено"
        """
        search_service = SearchService(product_repo=mock_product_repo)
        
        results = await search_service.search_products("xyznonexistent123")
        
        if not results:
            await mock_bot.send_message(
                chat_id=100001,
                text="😔 По вашему запросу ничего не найдено.\n\nПопробуйте изменить запрос."
            )
        
        assert len(results) == 0
        assert "не найдено" in mock_bot.sent_messages[0]['text']


class TestAdminScenarios:
    """Приёмочные тесты: сценарии администратора"""

    @pytest.mark.asyncio
    async def test_admin_receives_new_order_notification(
        self, mock_user_repo, mock_bot
    ):
        """
        А11: Уведомление админа о новом заказе.
        Новый заказ → уведомление всем админам
        """
        notification_service = NotificationService(
            bot=mock_bot,
            user_repo=mock_user_repo,
            config={'admin_ids': [100008, 100009]}
        )
        
        from tests.conftest import MockOrder
        order = MockOrder(
            id=100,
            user_id=4,
            order_number="ORD-20241220-0100",
            total=Decimal('79990'),
            status='created',
            contact_name="Новый Покупатель",
            contact_phone="+7 999 000-00-00",
            contact_address="г. Москва, ул. Новая, д. 1"
        )
        
        # Отправляем уведомление админам
        await notification_service.notify_admin_new_order(order)
        
        # Проверяем, что оба админа получили уведомление
        assert len(mock_bot.sent_messages) == 2
        
        admin_ids = {msg['chat_id'] for msg in mock_bot.sent_messages}
        assert 100008 in admin_ids
        assert 100009 in admin_ids
        
        # Проверяем содержимое
        for msg in mock_bot.sent_messages:
            assert "ORD-20241220-0100" in msg['text']
            assert "Новый Покупатель" in msg['text']

    @pytest.mark.asyncio
    async def test_admin_updates_order_status(
        self, mock_order_repo, mock_user_repo, mock_bot
    ):
        """
        А12: Админ меняет статус заказа.
        Заказ #2 → статус "shipped" → уведомление покупателю
        """
        notification_service = NotificationService(
            bot=mock_bot,
            user_repo=mock_user_repo,
            config={}
        )
        
        order_service = OrderService(
            order_repo=mock_order_repo,
            notification_service=notification_service
        )
        
        # Админ меняет статус заказа
        # Сначала переводим в paid (допустимый переход)
        order = await order_service.update_status(order_id=2, status='shipped')
        
        # Проверяем статус
        assert order.status == 'shipped'
        
        # Проверяем уведомление покупателю
        assert len(mock_bot.sent_messages) >= 1
        
        # Ищем сообщение покупателю (user_id=1 -> telegram_id=100001)
        customer_messages = [m for m in mock_bot.sent_messages if m['chat_id'] == 100001]
        assert len(customer_messages) >= 1


class TestConcurrentOperations:
    """Приёмочные тесты: параллельные операции"""

    @pytest.mark.asyncio
    async def test_concurrent_add_to_cart(self, mock_cart_repo, mock_product_repo):
        """
        Дополнительный тест: параллельное добавление в корзину.
        """
        import asyncio
        
        cart_service = CartService(
            cart_repo=mock_cart_repo,
            product_repo=mock_product_repo
        )
        
        user_id = 4
        
        # Параллельно добавляем несколько товаров
        tasks = [
            cart_service.add_item(user_id, 3, 1),  # Samsung
            cart_service.add_item(user_id, 5, 1),  # MacBook
            cart_service.add_item(user_id, 9, 1),  # AirPods
        ]
        
        await asyncio.gather(*tasks)
        
        # Проверяем корзину
        cart = await cart_service.get_cart(user_id)
        assert len(cart.items) == 3

    @pytest.mark.asyncio
    async def test_session_isolation(self, mock_cart_repo, mock_product_repo):
        """
        Дополнительный тест: изоляция корзин разных пользователей.
        """
        cart_service = CartService(
            cart_repo=mock_cart_repo,
            product_repo=mock_product_repo
        )
        
        # Пользователь 1 добавляет товар
        await cart_service.add_item(user_id=1, product_id=3, qty=2)
        
        # Пользователь 2 добавляет другой товар
        await cart_service.add_item(user_id=2, product_id=5, qty=1)
        
        # Проверяем изоляцию
        cart1 = await cart_service.get_cart(user_id=1)
        cart2 = await cart_service.get_cart(user_id=2)
        
        assert len(cart1.items) >= 1
        assert len(cart2.items) >= 1
        
        # Корзины не должны пересекаться
        cart1_products = {item.product_id for item in cart1.items}
        cart2_products = {item.product_id for item in cart2.items}
        
        # У пользователя 1 должен быть продукт 3
        assert 3 in cart1_products
        # У пользователя 2 должен быть продукт 5
        assert 5 in cart2_products
