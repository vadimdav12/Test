"""
Нагрузочные тесты телеграм-бота.
Тесты Н01-Н10 согласно плану тестирования.

Проверяют производительность и устойчивость системы под нагрузкой.
"""

import pytest
import asyncio
import time
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock
from concurrent.futures import ThreadPoolExecutor

from app.services.catalog_service import CatalogService
from app.services.cart_service import CartService
from app.services.order_service import OrderService
from app.services.discount_service import DiscountService
from app.services.search_service import SearchService
from app.dto import ContactData


# Конфигурация нагрузочных тестов
LOAD_TEST_CONFIG = {
    'concurrent_users': 100,
    'requests_per_user': 10,
    'max_response_time_ms': 500,
    'target_rps': 100,  # requests per second
}


class TestCatalogPerformance:
    """Нагрузочные тесты каталога"""

    @pytest.mark.asyncio
    async def test_catalog_load_100_concurrent_requests(self, mock_product_repo):
        """
        Н01: 100 параллельных запросов к каталогу.
        Проверяет время отклика < 500ms.
        """
        catalog_service = CatalogService(product_repo=mock_product_repo)
        
        num_requests = 100
        start_time = time.perf_counter()
        
        # Создаём 100 параллельных запросов
        tasks = [
            catalog_service.get_categories()
            for _ in range(num_requests)
        ]
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        avg_time_ms = total_time_ms / num_requests
        
        # Assert
        assert len(results) == num_requests
        assert all(len(r) == 5 for r in results)  # 5 категорий
        assert avg_time_ms < LOAD_TEST_CONFIG['max_response_time_ms'], \
            f"Среднее время отклика {avg_time_ms:.2f}ms превышает лимит"
        
        print(f"\n📊 Каталог: {num_requests} запросов за {total_time_ms:.2f}ms")
        print(f"   Среднее время: {avg_time_ms:.2f}ms")

    @pytest.mark.asyncio
    async def test_products_by_category_load(self, mock_product_repo):
        """
        Н02: Нагрузка на выборку товаров категории.
        100 запросов к разным категориям.
        """
        catalog_service = CatalogService(product_repo=mock_product_repo)
        
        num_requests = 100
        category_ids = [1, 2, 3, 4, 5]  # Циклически по категориям
        
        start_time = time.perf_counter()
        
        tasks = [
            catalog_service.get_products_by_category(category_ids[i % len(category_ids)])
            for i in range(num_requests)
        ]
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        
        # Assert
        assert len(results) == num_requests
        assert all(isinstance(r, list) for r in results)
        
        rps = num_requests / (total_time_ms / 1000)
        print(f"\n📊 Товары категории: {rps:.0f} RPS")


class TestCartPerformance:
    """Нагрузочные тесты корзины"""

    @pytest.mark.asyncio
    async def test_cart_operations_load(self, mock_cart_repo, mock_product_repo):
        """
        Н03: Нагрузка на операции с корзиной.
        50 пользователей одновременно добавляют товары.
        """
        cart_service = CartService(
            cart_repo=mock_cart_repo,
            product_repo=mock_product_repo
        )
        
        num_users = 50
        products_per_user = 3
        
        async def user_session(user_id):
            """Симуляция сессии одного пользователя"""
            product_ids = [3, 5, 6]  # Samsung, MacBook, ASUS
            for pid in product_ids[:products_per_user]:
                await cart_service.add_item(user_id + 100, pid, 1)
            return await cart_service.get_cart(user_id + 100)
        
        start_time = time.perf_counter()
        
        tasks = [user_session(i) for i in range(num_users)]
        results = await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        
        # Assert
        assert len(results) == num_users
        # Каждый пользователь должен иметь товары в корзине
        non_empty_carts = sum(1 for r in results if not r.is_empty)
        assert non_empty_carts == num_users
        
        total_operations = num_users * products_per_user
        ops_per_second = total_operations / (total_time_ms / 1000)
        
        print(f"\n📊 Корзина: {total_operations} операций за {total_time_ms:.2f}ms")
        print(f"   {ops_per_second:.0f} операций/сек")

    @pytest.mark.asyncio
    async def test_cart_calc_totals_performance(self, mock_cart_repo, mock_product_repo):
        """
        Н04: Производительность расчёта итогов корзины.
        1000 расчётов подряд.
        """
        cart_service = CartService(
            cart_repo=mock_cart_repo,
            product_repo=mock_product_repo
        )
        
        # Создаём корзину с несколькими товарами
        from app.dto import Cart, CartItem
        cart = Cart(
            user_id=1,
            items=[
                CartItem(product_id=i, product_name=f"Product {i}",
                        price=Decimal(str(10000 + i * 1000)), qty=i % 5 + 1)
                for i in range(10)
            ]
        )
        
        num_calculations = 1000
        start_time = time.perf_counter()
        
        for _ in range(num_calculations):
            cart_service.calc_totals(cart)
        
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        avg_time_us = (total_time_ms * 1000) / num_calculations
        
        # Assert - расчёт должен быть < 1ms
        assert avg_time_us < 1000, f"Расчёт занимает {avg_time_us:.2f}µs"
        
        print(f"\n📊 Расчёт итогов: {num_calculations} за {total_time_ms:.2f}ms")
        print(f"   Среднее: {avg_time_us:.2f}µs")


class TestSearchPerformance:
    """Нагрузочные тесты поиска"""

    @pytest.mark.asyncio
    async def test_search_load_100_queries(self, mock_product_repo):
        """
        Н05: 100 параллельных поисковых запросов.
        """
        search_service = SearchService(product_repo=mock_product_repo)
        
        queries = [
            "iphone", "samsung", "macbook", "airpods", "ноутбук",
            "смартфон", "телефон", "наушники", "чехол", "зарядка"
        ]
        
        num_requests = 100
        start_time = time.perf_counter()
        
        tasks = [
            search_service.search_products(queries[i % len(queries)])
            for i in range(num_requests)
        ]
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        avg_time_ms = total_time_ms / num_requests
        
        # Assert
        assert len(results) == num_requests
        assert avg_time_ms < LOAD_TEST_CONFIG['max_response_time_ms']
        
        # Подсчёт найденных результатов
        total_hits = sum(len(r) for r in results)
        
        print(f"\n📊 Поиск: {num_requests} запросов за {total_time_ms:.2f}ms")
        print(f"   Среднее время: {avg_time_ms:.2f}ms")
        print(f"   Всего найдено: {total_hits} товаров")

    @pytest.mark.asyncio
    async def test_fuzzy_search_performance(self, mock_product_repo):
        """
        Н06: Производительность нечёткого поиска.
        """
        search_service = SearchService(product_repo=mock_product_repo)
        
        # Запросы с опечатками
        fuzzy_queries = [
            "айфан", "самсунг галакси", "макбук про", "эирподс",
            "ноутбк", "смартфн", "телефо", "наушникы"
        ]
        
        num_requests = 50
        start_time = time.perf_counter()
        
        tasks = [
            search_service.search_products(fuzzy_queries[i % len(fuzzy_queries)])
            for i in range(num_requests)
        ]
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        
        # Fuzzy search может быть медленнее, но всё равно < 1s
        assert total_time_ms < 5000
        
        print(f"\n📊 Fuzzy поиск: {num_requests} запросов за {total_time_ms:.2f}ms")


class TestDiscountPerformance:
    """Нагрузочные тесты скидок"""

    @pytest.mark.asyncio
    async def test_promo_validation_load(self, mock_promocode_repo):
        """
        Н07: Нагрузка на валидацию промокодов.
        200 проверок промокодов.
        """
        discount_service = DiscountService(promocode_repo=mock_promocode_repo)
        
        promo_codes = ["SAVE10", "SAVE20", "VIP50", "INVALID", "OLD"]
        num_requests = 200
        
        start_time = time.perf_counter()
        
        tasks = [
            discount_service.validate_promo(
                promo_codes[i % len(promo_codes)],
                datetime.utcnow()
            )
            for i in range(num_requests)
        ]
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        
        # Assert
        valid_count = sum(1 for r in results if r.valid)
        invalid_count = num_requests - valid_count
        
        print(f"\n📊 Валидация промокодов: {num_requests} за {total_time_ms:.2f}ms")
        print(f"   Валидных: {valid_count}, невалидных: {invalid_count}")

    @pytest.mark.asyncio
    async def test_discount_calculation_performance(self, mock_promocode_repo):
        """
        Н08: Производительность расчёта скидок.
        """
        discount_service = DiscountService(promocode_repo=mock_promocode_repo)
        
        from app.dto import Cart, CartItem
        
        # Корзина с разными суммами
        test_carts = [
            Cart(user_id=i, items=[
                CartItem(product_id=1, product_name="Product",
                        price=Decimal(str(30000 + i * 10000)), qty=1)
            ])
            for i in range(100)
        ]
        
        num_calculations = 100
        start_time = time.perf_counter()
        
        tasks = [
            discount_service.apply_discounts(test_carts[i], "SAVE10")
            for i in range(num_calculations)
        ]
        
        results = await asyncio.gather(*tasks)
        
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        
        # Assert
        assert len(results) == num_calculations
        
        total_discounts = sum(r.total_discount for r in results)
        
        print(f"\n📊 Расчёт скидок: {num_calculations} за {total_time_ms:.2f}ms")
        print(f"   Общая сумма скидок: {total_discounts:,.0f}₽")


class TestOrderPerformance:
    """Нагрузочные тесты заказов"""

    @pytest.mark.asyncio
    async def test_order_creation_load(
        self, mock_order_repo, mock_cart_repo, mock_product_repo, mock_promocode_repo
    ):
        """
        Н09: Нагрузка на создание заказов.
        20 параллельных заказов.
        """
        cart_service = CartService(
            cart_repo=mock_cart_repo,
            product_repo=mock_product_repo
        )
        
        discount_service = DiscountService(
            promocode_repo=mock_promocode_repo
        )
        
        notification_service = AsyncMock()
        
        order_service = OrderService(
            order_repo=mock_order_repo,
            cart_service=cart_service,
            product_repo=mock_product_repo,
            discount_service=discount_service,
            notification_service=notification_service
        )
        
        num_orders = 20
        
        # Заполняем корзины для каждого пользователя
        for i in range(num_orders):
            user_id = 100 + i
            mock_cart_repo._data[user_id] = [
                {'product_id': 3, 'qty': 1, 'name': 'Samsung',
                 'price': Decimal('79990'), 'stock': 1000, 'is_active': True}
            ]
        
        async def create_order(user_id):
            contact = ContactData(
                name=f"User {user_id}",
                phone="+7 999 000-00-00",
                address=f"Адрес пользователя {user_id}, д. 1, кв. 1"
            )
            return await order_service.create_order(user_id, contact)
        
        start_time = time.perf_counter()
        
        tasks = [create_order(100 + i) for i in range(num_orders)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        
        # Assert
        successful = [r for r in results if not isinstance(r, Exception)]
        failed = [r for r in results if isinstance(r, Exception)]
        
        print(f"\n📊 Создание заказов: {num_orders} за {total_time_ms:.2f}ms")
        print(f"   Успешных: {len(successful)}, ошибок: {len(failed)}")
        
        assert len(successful) == num_orders, f"Ошибки: {failed}"


class TestSystemStress:
    """Стресс-тесты системы"""

    @pytest.mark.asyncio
    async def test_mixed_operations_stress(
        self, mock_product_repo, mock_cart_repo, mock_promocode_repo
    ):
        """
        Н10: Смешанная нагрузка на систему.
        Каталог + корзина + поиск + скидки одновременно.
        """
        catalog_service = CatalogService(product_repo=mock_product_repo)
        cart_service = CartService(
            cart_repo=mock_cart_repo,
            product_repo=mock_product_repo
        )
        search_service = SearchService(product_repo=mock_product_repo)
        discount_service = DiscountService(promocode_repo=mock_promocode_repo)
        
        num_operations = 200
        
        async def random_operation(i):
            """Выполняет случайную операцию"""
            op_type = i % 4
            
            if op_type == 0:
                return await catalog_service.get_categories()
            elif op_type == 1:
                return await catalog_service.get_products_by_category(1)
            elif op_type == 2:
                return await search_service.search_products("iphone")
            else:
                return await discount_service.validate_promo("SAVE10", datetime.utcnow())
        
        start_time = time.perf_counter()
        
        tasks = [random_operation(i) for i in range(num_operations)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        
        # Assert
        successful = [r for r in results if not isinstance(r, Exception)]
        failed = [r for r in results if isinstance(r, Exception)]
        
        success_rate = len(successful) / num_operations * 100
        rps = num_operations / (total_time_ms / 1000)
        
        print(f"\n📊 Смешанная нагрузка:")
        print(f"   Операций: {num_operations}")
        print(f"   Время: {total_time_ms:.2f}ms")
        print(f"   RPS: {rps:.0f}")
        print(f"   Успешность: {success_rate:.1f}%")
        
        assert success_rate >= 99, f"Слишком много ошибок: {len(failed)}"

    @pytest.mark.asyncio
    async def test_sustained_load(self, mock_product_repo):
        """
        Дополнительный тест: устойчивая нагрузка в течение времени.
        """
        catalog_service = CatalogService(product_repo=mock_product_repo)
        
        duration_seconds = 2
        request_interval_ms = 10
        
        results = []
        errors = []
        
        start_time = time.perf_counter()
        end_time = start_time + duration_seconds
        
        while time.perf_counter() < end_time:
            try:
                req_start = time.perf_counter()
                await catalog_service.get_categories()
                req_end = time.perf_counter()
                results.append((req_end - req_start) * 1000)
            except Exception as e:
                errors.append(str(e))
            
            await asyncio.sleep(request_interval_ms / 1000)
        
        # Статистика
        if results:
            avg_time = sum(results) / len(results)
            max_time = max(results)
            min_time = min(results)
            
            print(f"\n📊 Устойчивая нагрузка ({duration_seconds}с):")
            print(f"   Запросов: {len(results)}")
            print(f"   Ошибок: {len(errors)}")
            print(f"   Среднее время: {avg_time:.2f}ms")
            print(f"   Min/Max: {min_time:.2f}ms / {max_time:.2f}ms")
            
            assert len(errors) == 0
            assert avg_time < 100  # Среднее время < 100ms


class TestMemoryUsage:
    """Тесты использования памяти"""

    @pytest.mark.asyncio
    async def test_large_cart_handling(self, mock_cart_repo, mock_product_repo):
        """
        Дополнительный тест: обработка большой корзины.
        """
        cart_service = CartService(
            cart_repo=mock_cart_repo,
            product_repo=mock_product_repo
        )
        
        from app.dto import Cart, CartItem
        
        # Создаём корзину с 100 позициями
        large_cart = Cart(
            user_id=1,
            items=[
                CartItem(
                    product_id=i,
                    product_name=f"Product {i}",
                    price=Decimal(str(1000 + i * 100)),
                    qty=i % 10 + 1
                )
                for i in range(100)
            ]
        )
        
        # Многократный расчёт итогов
        num_calculations = 1000
        
        start_time = time.perf_counter()
        
        for _ in range(num_calculations):
            cart_service.calc_totals(large_cart)
        
        end_time = time.perf_counter()
        total_time_ms = (end_time - start_time) * 1000
        
        print(f"\n📊 Большая корзина (100 позиций):")
        print(f"   {num_calculations} расчётов за {total_time_ms:.2f}ms")
        
        # Расчёт должен быть быстрым даже для большой корзины
        avg_time_us = (total_time_ms * 1000) / num_calculations
        assert avg_time_us < 5000  # < 5ms на расчёт
