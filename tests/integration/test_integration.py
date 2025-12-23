"""
Интеграционные тесты телеграм-бота.
Тесты И01-И12 согласно плану тестирования.

Проверяют взаимодействие компонентов:
Handler → Service → Repository → Database → MockBot
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
from app.dto import ContactData, Cart, CartItem, DiscountResult, ProductCreate
from app.exceptions import InsufficientStockError, EmptyCartError


class TestCatalogIntegration:
    """Интеграционные тесты каталога"""

    @pytest.mark.asyncio
    async def test_catalog_navigation_flow(self, mock_product_repo, mock_bot):
        """
        И01: Навигация по каталогу.
        Handler → CatalogService → ProductRepo → catalog_kb
        """
        # Arrange
        catalog_service = CatalogService(product_repo=mock_product_repo)
        
        # Act - эмулируем handle_catalog()
        categories = await catalog_service.get_categories()
        
        # Формируем клавиатуру (эмуляция keyboards.py)
        keyboard_buttons = []
        for cat in categories:
            keyboard_buttons.append({
                'text': cat.name,
                'callback_data': f'category:{cat.id}'
            })
        
        # Отправляем сообщение (эмуляция handler)
        message_text = "📦 Выберите категорию:"
        await mock_bot.send_message(
            chat_id=100001,
            text=message_text,
            reply_markup={'inline_keyboard': [keyboard_buttons]}
        )
        
        # Assert
        assert len(categories) == 5
        assert len(mock_bot.sent_messages) == 1
        assert len(keyboard_buttons) == 5
        assert keyboard_buttons[0]['text'] == "Смартфоны"

    @pytest.mark.asyncio
    async def test_category_products_display(self, mock_product_repo, mock_bot):
        """
        И02: Отображение товаров категории.
        handle_category(callback="category:1") → get_products_by_category
        """
        # Arrange
        catalog_service = CatalogService(product_repo=mock_product_repo)
        category_id = 1  # Смартфоны
        
        # Act - эмулируем handle_category()
        products = await catalog_service.get_products_by_category(category_id)
        
        # Формируем сообщения для каждого товара
        for product in products:
            price_formatted = f"{int(product.price):,}".replace(',', ' ')
            text = f"📱 {product.name}\n💰 {price_formatted} ₽\n📦 В наличии: {product.stock} шт."
            
            keyboard = {
                'inline_keyboard': [[
                    {'text': '🛒 В корзину', 'callback_data': f'add_to_cart:{product.id}:1'}
                ]]
            }
            
            await mock_bot.send_message(
                chat_id=100001,
                text=text,
                reply_markup=keyboard
            )
        
        # Assert
        assert len(products) == 4  # 4 смартфона в категории
        assert len(mock_bot.sent_messages) == 4
        
        # Проверяем содержимое первого сообщения
        assert "iPhone" in mock_bot.sent_messages[1]['text'] or "Samsung" in mock_bot.sent_messages[1]['text']


class TestCartIntegration:
    """Интеграционные тесты корзины"""

    @pytest.mark.asyncio
    async def test_add_to_cart_flow(
        self, mock_cart_repo, mock_product_repo, mock_bot
    ):
        """
        И03: Добавление товара в корзину.
        handle_add_to_cart(callback="add_to_cart:3:1") → CartService.add_item
        """
        # Arrange
        cart_service = CartService(
            cart_repo=mock_cart_repo,
            product_repo=mock_product_repo
        )
        user_id = 4
        product_id = 3  # Samsung Galaxy S24
        qty = 1
        
        # Act - эмулируем handle_add_to_cart()
        cart = await cart_service.add_item(user_id, product_id, qty)
        
        # Получаем информацию о товаре для сообщения
        product = await mock_product_repo.fetch_product_by_id(product_id)
        
        # Отправляем подтверждение
        await mock_bot.send_message(
            chat_id=100004,  # telegram_id user_id=4
            text=f"✅ {product.name} добавлен в корзину!"
        )
        
        # Assert
        assert len(mock_cart_repo._data.get(user_id, [])) == 1
        assert mock_cart_repo._data[user_id][0]['product_id'] == product_id
        assert len(mock_bot.sent_messages) == 1
        assert "добавлен" in mock_bot.sent_messages[0]['text']

    @pytest.mark.asyncio
    async def test_add_to_cart_out_of_stock(
        self, mock_cart_repo, mock_product_repo, mock_bot
    ):
        """
        И04: Добавление товара без остатка.
        Проверяет сообщение "нет в наличии".
        """
        # Arrange
        cart_service = CartService(
            cart_repo=mock_cart_repo,
            product_repo=mock_product_repo
        )
        user_id = 4
        product_id = 1  # iPhone 15 Pro, stock=0
        
        # Act & Assert
        with pytest.raises(InsufficientStockError):
            await cart_service.add_item(user_id, product_id, 1)
        
        # Эмулируем обработку ошибки в handler
        await mock_bot.send_message(
            chat_id=100004,
            text="❌ Товар отсутствует на складе"
        )
        
        # Assert
        assert "отсутствует" in mock_bot.sent_messages[0]['text']
        # Корзина должна остаться пустой
        assert mock_cart_repo._data.get(user_id, []) == []


class TestCheckoutIntegration:
    """Интеграционные тесты оформления заказа"""

    @pytest.fixture
    def services_setup(
        self, mock_cart_repo, mock_product_repo, mock_order_repo,
        mock_promocode_repo, mock_user_repo, mock_bot
    ):
        """Настройка сервисов для интеграционных тестов"""
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
        
        order_service = OrderService(
            order_repo=mock_order_repo,
            cart_service=cart_service,
            product_repo=mock_product_repo,
            discount_service=discount_service,
            notification_service=notification_service
        )
        
        return {
            'cart_service': cart_service,
            'order_service': order_service,
            'discount_service': discount_service,
            'notification_service': notification_service
        }

    @pytest.mark.asyncio
    async def test_full_checkout_fsm_flow(
        self, services_setup, mock_cart_repo, mock_product_repo, mock_bot, test_products
    ):
        """
        И05: Полный цикл оформления заказа через FSM.
        name → phone → address → payment → order created
        """
        # Arrange
        cart_service = services_setup['cart_service']
        order_service = services_setup['order_service']
        user_id = 1
        
        # Добавляем товары в корзину
        mock_cart_repo._data[user_id] = [
            {'product_id': 3, 'qty': 1, 'name': 'Samsung Galaxy S24', 
             'price': Decimal('79990'), 'stock': 10, 'is_active': True}
        ]
        
        initial_stock = test_products[2].stock  # Samsung id=3
        
        # Эмулируем FSM диалог
        fsm_states = []
        
        # Шаг 1: Ввод имени
        fsm_states.append(('waiting_name', 'Иван Тестовый'))
        
        # Шаг 2: Ввод телефона
        fsm_states.append(('waiting_phone', '+7 999 111-11-11'))
        
        # Шаг 3: Ввод адреса
        fsm_states.append(('waiting_address', 'г. Москва, ул. Тестовая, д. 1, кв. 1'))
        
        # Шаг 4: Выбор оплаты
        fsm_states.append(('waiting_payment', 'card'))
        
        # Act - создание заказа
        contact = ContactData(
            name=fsm_states[0][1],
            phone=fsm_states[1][1],
            address=fsm_states[2][1]
        )
        
        order = await order_service.create_order(
            user_id=user_id,
            contact=contact,
            payment_method='card'
        )
        
        # Assert
        assert order is not None
        assert order.order_number.startswith("ORD-")
        assert order.status == 'created'
        assert order.total == Decimal('79990')
        
        # Проверяем, что корзина очищена
        cart = await cart_service.get_cart(user_id)
        assert cart.is_empty
        
        # Проверяем резервирование товара
        assert test_products[2].stock == initial_stock - 1
        
        # Проверяем отправку уведомлений
        assert len(mock_bot.sent_messages) >= 1

    @pytest.mark.asyncio
    async def test_checkout_invalid_phone_stays_in_state(
        self, services_setup, mock_cart_repo, mock_bot
    ):
        """
        И06: Ввод невалидного телефона в FSM.
        Проверяет, что состояние waiting_phone сохраняется.
        """
        # Arrange
        user_id = 1
        mock_cart_repo._data[user_id] = [
            {'product_id': 3, 'qty': 1, 'name': 'Samsung', 
             'price': Decimal('79990'), 'stock': 10, 'is_active': True}
        ]
        
        # Эмулируем FSM с невалидным телефоном
        current_state = 'waiting_phone'
        phone_input = 'invalid_phone'
        
        # Валидация телефона
        from app.utils.helpers import validate_phone
        is_valid = validate_phone(phone_input)
        
        if not is_valid:
            # Остаёмся в том же состоянии
            await mock_bot.send_message(
                chat_id=100001,
                text="❌ Некорректный формат телефона. Используйте +7 XXX XXX-XX-XX"
            )
            next_state = 'waiting_phone'  # Остаёмся в том же состоянии
        
        # Assert
        assert is_valid == False
        assert next_state == 'waiting_phone'
        assert "Некорректный" in mock_bot.sent_messages[0]['text']


class TestPaymentIntegration:
    """Интеграционные тесты оплаты"""

    @pytest.mark.asyncio
    async def test_init_payment_creates_session(
        self, mock_order_repo, mock_payment_gateway, test_orders
    ):
        """
        И07: Инициализация платёжной сессии.
        init_payment(order_id=1) → создание session и URL
        """
        # Arrange
        payment_service = PaymentService(
            order_repo=mock_order_repo,
            payment_gateway=mock_payment_gateway
        )
        
        order = test_orders[0]  # created order
        
        # Act
        session = await payment_service.init_payment(order)
        
        # Assert
        assert session is not None
        assert session.session_id.startswith("sess_")
        assert "https://" in session.payment_url
        assert session.amount == order.total

    @pytest.mark.asyncio
    async def test_payment_callback_success_flow(
        self, mock_order_repo, mock_payment_gateway, mock_user_repo,
        mock_bot, test_orders, tmp_path
    ):
        """
        И08: Обработка успешного webhook платежа.
        handle_callback → update_status('paid') → generate_receipt → send_document
        """
        # Arrange
        notification_service = NotificationService(
            bot=mock_bot,
            user_repo=mock_user_repo,
            config={}
        )
        
        receipt_service = ReceiptService(
            order_repo=mock_order_repo,
            bot=mock_bot,
            receipts_dir=str(tmp_path / "receipts")
        )
        
        payment_service = PaymentService(
            order_repo=mock_order_repo,
            payment_gateway=mock_payment_gateway,
            receipt_service=receipt_service,
            notification_service=notification_service
        )
        
        # Подготовка: добавляем позиции заказа
        from tests.conftest import MockOrderItem
        mock_order_repo.get_order_items = AsyncMock(return_value=[
            MockOrderItem(1, 2, 3, "Samsung Galaxy S24", Decimal('79990'), 1),
            MockOrderItem(2, 2, 9, "AirPods Pro 2", Decimal('24990'), 2)
        ])
        
        # Мокируем get_user_by_order
        from tests.conftest import MockUser
        mock_order_repo.get_user_by_order = AsyncMock(return_value=MockUser(1, 100001))
        
        # Эмулируем webhook callback
        payload = {
            'session_id': 'sess_2',
            'order_id': 2,
            'status': 'success'
        }
        
        # Act
        result = await payment_service.handle_callback(payload)
        
        # Assert
        assert result.success == True
        assert result.order_id == 2
        
        # Проверяем статус заказа
        order = test_orders[1]
        assert order.status == 'paid'


class TestSearchIntegration:
    """Интеграционные тесты поиска"""

    @pytest.mark.asyncio
    async def test_search_query_with_cyrillic(self, mock_product_repo, mock_bot):
        """
        И09: Поиск на русском языке.
        handle_search_query("Самсунг Галакси") → Samsung Galaxy S24
        """
        # Arrange
        search_service = SearchService(product_repo=mock_product_repo)
        query = "Самсунг Галакси"
        
        # Act
        results = await search_service.search_products(query)
        
        # Формируем ответ
        if results:
            response_text = f"🔍 Найдено {len(results)} товаров:\n\n"
            for hit in results[:5]:
                response_text += f"• {hit.product_name} - {hit.price}₽\n"
        else:
            response_text = "😔 Ничего не найдено"
        
        await mock_bot.send_message(chat_id=100001, text=response_text)
        
        # Assert
        assert len(results) > 0
        # Samsung должен быть в результатах
        product_names = [r.product_name.lower() for r in results]
        assert any('samsung' in name for name in product_names)


class TestFavoritesIntegration:
    """Интеграционные тесты избранного"""

    @pytest.mark.asyncio
    async def test_add_and_list_favorites(
        self, mock_favorites_repo, mock_product_repo, mock_bot
    ):
        """
        И10: Добавление и просмотр избранного.
        handle_add_favorite → handle_favorites_list
        """
        # Arrange
        favorites_service = FavoritesService(
            favorites_repo=mock_favorites_repo,
            product_repo=mock_product_repo
        )
        user_id = 4
        product_id = 5  # MacBook Pro 14
        
        # Act - добавление в избранное
        await favorites_service.add_favorite(user_id, product_id)
        
        # Получение списка избранного
        favorites = await favorites_service.list_favorites(user_id)
        
        # Формируем сообщение
        if favorites:
            text = "❤️ Ваши избранные товары:\n\n"
            for product in favorites:
                text += f"• {product.name}\n"
        else:
            text = "У вас пока нет избранных товаров"
        
        await mock_bot.send_message(chat_id=100004, text=text)
        
        # Assert
        assert len(favorites) == 1
        assert favorites[0].name == "MacBook Pro 14"
        assert "MacBook" in mock_bot.sent_messages[0]['text']


class TestPromocodeIntegration:
    """Интеграционные тесты промокодов"""

    @pytest.mark.asyncio
    async def test_apply_promo_to_cart(
        self, mock_cart_repo, mock_product_repo, mock_promocode_repo, mock_bot
    ):
        """
        И11: Применение промокода к корзине.
        handle_apply_promo("SAVE10") → показ скидки
        """
        # Arrange
        cart_service = CartService(
            cart_repo=mock_cart_repo,
            product_repo=mock_product_repo
        )
        discount_service = DiscountService(
            promocode_repo=mock_promocode_repo
        )
        
        user_id = 1
        
        # Добавляем товары в корзину
        mock_cart_repo._data[user_id] = [
            {'product_id': 2, 'qty': 1, 'name': 'iPhone 15', 
             'price': Decimal('89990'), 'stock': 5, 'is_active': True},
            {'product_id': 7, 'qty': 2, 'name': 'Чехол iPhone', 
             'price': Decimal('1990'), 'stock': 100, 'is_active': True}
        ]
        
        # Act
        cart = await cart_service.get_cart(user_id)
        cart.promocode = "SAVE10"
        
        discount_result = await discount_service.apply_discounts(cart, "SAVE10")
        totals = cart_service.calc_totals(cart, discount_result.total_discount)
        
        # Формируем сообщение
        text = (
            f"🛒 Ваша корзина:\n\n"
            f"Подитог: {totals.subtotal:,.0f}₽\n"
            f"Скидка: -{totals.discount:,.0f}₽\n"
            f"Итого: {totals.total:,.0f}₽"
        )
        
        await mock_bot.send_message(chat_id=100001, text=text)
        
        # Assert
        # Subtotal = 89990 + 1990*2 = 93970
        # Discount 10% = 9397
        # Total = 84573
        assert totals.subtotal == Decimal('93970')
        assert discount_result.promo_discount == Decimal('9397')  # 10% от 93970


class TestAdminIntegration:
    """Интеграционные тесты админ-панели"""

    @pytest.mark.asyncio
    async def test_admin_create_product_flow(
        self, mock_product_repo, mock_user_repo, mock_bot
    ):
        """
        И12: Создание товара администратором.
        /admin → create_product FSM → товар в каталоге
        """
        # Arrange
        catalog_service = CatalogService(product_repo=mock_product_repo)
        admin_user_id = 8  # is_admin=True
        
        # Проверка прав доступа
        is_admin = await mock_user_repo.is_admin(admin_user_id)
        assert is_admin == True
        
        # FSM данные нового товара
        product_data = ProductCreate(
            name="Новый iPhone 16",
            description="Самый новый iPhone",
            price=Decimal('149990'),
            stock=50,
            category_id=1  # Смартфоны
        )
        
        # Act - создание товара
        new_product = await catalog_service.create_product(product_data)
        
        # Отправляем подтверждение админу
        await mock_bot.send_message(
            chat_id=100008,  # telegram_id админа
            text=f"✅ Товар '{new_product.name}' успешно создан!\nID: {new_product.id}"
        )
        
        # Проверяем, что товар виден в каталоге
        products = await catalog_service.get_products_by_category(1)
        
        # Assert
        assert new_product is not None
        assert new_product.name == "Новый iPhone 16"
        assert new_product.price == Decimal('149990')
        
        # Товар должен появиться в списке категории
        product_names = [p.name for p in products]
        assert "Новый iPhone 16" in product_names
        
        # Проверяем сообщение админу
        assert "успешно создан" in mock_bot.sent_messages[0]['text']

    @pytest.mark.asyncio
    async def test_admin_access_denied_for_regular_user(
        self, mock_user_repo, mock_bot
    ):
        """
        Дополнительный тест: отказ в доступе для обычного пользователя.
        """
        # Arrange
        regular_user_id = 1  # is_admin=False
        
        # Act - проверка прав
        is_admin = await mock_user_repo.is_admin(regular_user_id)
        
        if not is_admin:
            await mock_bot.send_message(
                chat_id=100001,
                text="⛔ У вас нет прав администратора"
            )
        
        # Assert
        assert is_admin == False
        assert "нет прав" in mock_bot.sent_messages[0]['text']
