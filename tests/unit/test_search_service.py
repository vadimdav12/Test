"""
Блочные тесты модуля поиска (SearchService).
Тесты Б49-Б56 согласно плану тестирования.
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock

from app.services.search_service import SearchService


class TestSearchServiceNormalize:
    """Тесты нормализации поисковых запросов"""

    def test_normalize_query_basic(self, mock_product_repo):
        """
        Б49: Нормализация поискового запроса.
        Проверяет приведение к нижнему регистру и удаление пробелов.
        """
        # Arrange
        service = SearchService(product_repo=mock_product_repo)
        
        # Act
        result = service.normalize_query("  АйФон 16  PRO  ")
        
        # Assert
        assert result == "айфон 16 pro"

    def test_normalize_query_removes_special_chars(self, mock_product_repo):
        """
        Тест: удаление специальных символов.
        """
        # Arrange
        service = SearchService(product_repo=mock_product_repo)
        
        # Act
        result = service.normalize_query("iPhone!!! @#$%^&*() 15")
        
        # Assert
        assert "!" not in result
        assert "@" not in result
        assert "iphone" in result
        assert "15" in result

    def test_normalize_query_empty(self, mock_product_repo):
        """
        Тест: нормализация пустой строки.
        """
        # Arrange
        service = SearchService(product_repo=mock_product_repo)
        
        # Act
        result = service.normalize_query("")
        
        # Assert
        assert result == ""

    def test_normalize_query_preserves_cyrillic(self, mock_product_repo):
        """
        Тест: сохранение кириллицы.
        """
        # Arrange
        service = SearchService(product_repo=mock_product_repo)
        
        # Act
        result = service.normalize_query("Самсунг Галакси")
        
        # Assert
        assert result == "самсунг галакси"


class TestSearchServiceLevenshtein:
    """Тесты расстояния Левенштейна"""

    def test_levenshtein_distance_one_char(self, mock_product_repo):
        """
        Б50: Расстояние Левенштейна (1 символ).
        Проверяет расстояние между "айфон" и "айфан".
        """
        # Arrange
        service = SearchService(product_repo=mock_product_repo)
        
        # Act
        distance = service.levenshtein_distance("айфон", "айфан")
        
        # Assert
        assert distance == 1

    def test_levenshtein_distance_same_strings(self, mock_product_repo):
        """
        Тест: расстояние между одинаковыми строками.
        """
        # Arrange
        service = SearchService(product_repo=mock_product_repo)
        
        # Act
        distance = service.levenshtein_distance("iphone", "iphone")
        
        # Assert
        assert distance == 0

    def test_levenshtein_distance_empty_string(self, mock_product_repo):
        """
        Тест: расстояние до пустой строки.
        """
        # Arrange
        service = SearchService(product_repo=mock_product_repo)
        
        # Act
        distance = service.levenshtein_distance("test", "")
        
        # Assert
        assert distance == 4  # Длина "test"

    def test_levenshtein_distance_multiple_changes(self, mock_product_repo):
        """
        Тест: несколько изменений.
        """
        # Arrange
        service = SearchService(product_repo=mock_product_repo)
        
        # Act
        distance = service.levenshtein_distance("samsung", "samsang")  # u -> a
        
        # Assert
        assert distance == 1


class TestSearchServiceFuzzyMatch:
    """Тесты нечёткого сопоставления"""

    def test_fuzzy_match_high_similarity(self, mock_product_repo):
        """
        Б51: Нечёткое сопоставление (высокое сходство).
        Проверяет fuzzy_match для "iphone" и "iphon".
        """
        # Arrange
        service = SearchService(product_repo=mock_product_repo)
        
        # Act
        score = service.fuzzy_match("iphone", "iphon")
        
        # Assert
        assert score >= 0.8  # Высокое сходство

    def test_fuzzy_match_exact(self, mock_product_repo):
        """
        Тест: точное совпадение.
        """
        # Arrange
        service = SearchService(product_repo=mock_product_repo)
        
        # Act
        score = service.fuzzy_match("samsung", "samsung")
        
        # Assert
        assert score == 1.0

    def test_fuzzy_match_no_similarity(self, mock_product_repo):
        """
        Тест: отсутствие сходства.
        """
        # Arrange
        service = SearchService(product_repo=mock_product_repo)
        
        # Act
        score = service.fuzzy_match("apple", "xyz")
        
        # Assert
        assert score < 0.5

    def test_fuzzy_match_empty_string(self, mock_product_repo):
        """
        Тест: пустая строка.
        """
        # Arrange
        service = SearchService(product_repo=mock_product_repo)
        
        # Act
        score = service.fuzzy_match("test", "")
        
        # Assert
        assert score == 0.0


class TestSearchServiceSearchProducts:
    """Тесты поиска товаров"""

    @pytest.mark.asyncio
    async def test_search_products_exact_match(self, mock_product_repo):
        """
        Б52: Поиск по точному названию.
        Проверяет поиск "iPhone 15" → product id=2.
        """
        # Arrange
        service = SearchService(product_repo=mock_product_repo)
        
        # Act
        results = await service.search_products("iPhone 15")
        
        # Assert
        assert len(results) > 0
        # Точное совпадение должно быть в топе
        assert any(r.product_id == 2 for r in results)
        exact_match = next((r for r in results if r.product_id == 2), None)
        if exact_match:
            assert exact_match.score == 1.0
            assert exact_match.match_type == 'exact'

    @pytest.mark.asyncio
    async def test_search_products_fuzzy_match(self, mock_product_repo):
        """
        Б53: Нечёткий поиск с опечатками.
        Проверяет поиск "samsun galax s24" → Samsung Galaxy S24.
        """
        # Arrange
        service = SearchService(product_repo=mock_product_repo)
        
        # Act
        results = await service.search_products("samsun galax s24")
        
        # Assert
        # Samsung Galaxy S24 (id=3) должен быть в результатах
        assert len(results) > 0
        found = any(r.product_id == 3 for r in results[:5])  # В топ-5
        assert found, "Samsung Galaxy S24 должен найтись по нечёткому запросу"

    @pytest.mark.asyncio
    async def test_search_products_cyrillic(self, mock_product_repo):
        """
        Б54: Поиск на кириллице с транслитерацией.
        Проверяет поиск "Самсунг" → Samsung Galaxy S24.
        """
        # Arrange
        service = SearchService(product_repo=mock_product_repo)
        
        # Act
        results = await service.search_products("Самсунг")
        
        # Assert
        assert len(results) > 0
        # Samsung должен найтись через транслитерацию
        samsung_found = any("samsung" in r.product_name.lower() or 
                          "самсунг" in r.product_name.lower() 
                          for r in results)
        assert samsung_found

    @pytest.mark.asyncio
    async def test_search_products_empty_query(self, mock_product_repo):
        """
        Б55: Поиск с пустым запросом.
        Проверяет, что возвращается пустой список.
        """
        # Arrange
        service = SearchService(product_repo=mock_product_repo)
        
        # Act
        results = await service.search_products("")
        
        # Assert
        assert results == []

    @pytest.mark.asyncio
    async def test_search_products_no_results(self, mock_product_repo):
        """
        Б56: Поиск несуществующего товара.
        Проверяет, что возвращается пустой список.
        """
        # Arrange
        service = SearchService(product_repo=mock_product_repo)
        
        # Act
        results = await service.search_products("xyznonexistent123")
        
        # Assert
        assert results == []

    @pytest.mark.asyncio
    async def test_search_products_respects_limit(self, mock_product_repo):
        """
        Тест: ограничение количества результатов.
        """
        # Arrange
        service = SearchService(product_repo=mock_product_repo)
        
        # Act
        results = await service.search_products("phone", limit=3)
        
        # Assert
        assert len(results) <= 3

    @pytest.mark.asyncio
    async def test_search_products_sorted_by_score(self, mock_product_repo):
        """
        Тест: результаты отсортированы по релевантности.
        """
        # Arrange
        service = SearchService(product_repo=mock_product_repo)
        
        # Act
        results = await service.search_products("iPhone")
        
        # Assert
        if len(results) > 1:
            scores = [r.score for r in results]
            assert scores == sorted(scores, reverse=True)


class TestSearchServiceTransliteration:
    """Тесты транслитерации"""

    def test_transliterate_russian(self, mock_product_repo):
        """
        Тест: транслитерация кириллицы.
        """
        # Arrange
        service = SearchService(product_repo=mock_product_repo)
        
        # Act
        result = service._transliterate("самсунг")
        
        # Assert
        assert "samsung" in result.lower()

    def test_transliterate_english(self, mock_product_repo):
        """
        Тест: английский текст не меняется.
        """
        # Arrange
        service = SearchService(product_repo=mock_product_repo)
        
        # Act
        result = service._transliterate("iphone")
        
        # Assert
        assert result == "iphone"


class TestSearchServiceAdaptiveThreshold:
    """Тесты адаптивного порога"""

    def test_get_max_distance_short_word(self, mock_product_repo):
        """
        Тест: порог для короткого слова.
        """
        # Arrange
        service = SearchService(product_repo=mock_product_repo)
        
        # Act
        threshold = service._get_max_distance(3)  # 3 символа
        
        # Assert
        assert threshold == 1

    def test_get_max_distance_medium_word(self, mock_product_repo):
        """
        Тест: порог для среднего слова.
        """
        # Arrange
        service = SearchService(product_repo=mock_product_repo)
        
        # Act
        threshold = service._get_max_distance(6)  # 6 символов
        
        # Assert
        assert threshold == 3

    def test_get_max_distance_long_word(self, mock_product_repo):
        """
        Тест: порог для длинного слова.
        """
        # Arrange
        service = SearchService(product_repo=mock_product_repo)
        
        # Act
        threshold = service._get_max_distance(10)  # 10 символов
        
        # Assert
        assert threshold == 4
