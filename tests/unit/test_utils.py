"""
Блочные тесты вспомогательных функций (Utils).
Тесты Б80-Б82 согласно плану тестирования.
"""

import pytest
from decimal import Decimal

from app.utils.helpers import (
    format_price,
    validate_phone,
    normalize_phone,
    truncate_text,
    sanitize_html,
    plural_form
)


class TestFormatPrice:
    """Тесты форматирования цены"""

    def test_format_price_basic(self):
        """
        Б80: Форматирование цены.
        Проверяет добавление разделителей и символа рубля.
        """
        # Act
        result = format_price(15000)
        
        # Assert
        assert result == "15 000 ₽"

    def test_format_price_million(self):
        """
        Тест: форматирование миллиона.
        """
        # Act
        result = format_price(1000000)
        
        # Assert
        assert result == "1 000 000 ₽"

    def test_format_price_small(self):
        """
        Тест: форматирование небольшой суммы.
        """
        # Act
        result = format_price(99)
        
        # Assert
        assert result == "99 ₽"

    def test_format_price_zero(self):
        """
        Тест: форматирование нуля.
        """
        # Act
        result = format_price(0)
        
        # Assert
        assert result == "0 ₽"

    def test_format_price_decimal(self):
        """
        Тест: форматирование Decimal.
        """
        # Act
        result = format_price(Decimal('129990'))
        
        # Assert
        assert result == "129 990 ₽"

    def test_format_price_float(self):
        """
        Тест: форматирование float.
        """
        # Act
        result = format_price(15000.50)
        
        # Assert
        assert result == "15 000 ₽"  # Отбрасываем копейки

    def test_format_price_none(self):
        """
        Тест: форматирование None.
        """
        # Act
        result = format_price(None)
        
        # Assert
        assert result == "0 ₽"


class TestValidatePhone:
    """Тесты валидации телефона"""

    def test_validate_phone_plus_seven_spaces(self):
        """
        Б81: Валидация телефона +7 с пробелами.
        """
        # Act & Assert
        assert validate_phone("+7 999 123-45-67") == True

    def test_validate_phone_plus_seven_no_spaces(self):
        """
        Тест: валидация +7 без пробелов.
        """
        # Act & Assert
        assert validate_phone("+79991234567") == True

    def test_validate_phone_eight_spaces(self):
        """
        Тест: валидация 8 с пробелами.
        """
        # Act & Assert
        assert validate_phone("8 999 123 45 67") == True

    def test_validate_phone_eight_no_spaces(self):
        """
        Тест: валидация 8 без пробелов.
        """
        # Act & Assert
        assert validate_phone("89991234567") == True

    def test_validate_phone_invalid_short(self):
        """
        Б82: Валидация невалидного телефона (короткий).
        """
        # Act & Assert
        assert validate_phone("59991234567") == False

    def test_validate_phone_invalid_format(self):
        """
        Тест: невалидный формат.
        """
        # Act & Assert
        assert validate_phone("123456") == False
        assert validate_phone("abcdefghij") == False

    def test_validate_phone_international(self):
        """
        Тест: международный формат (не поддерживается).
        """
        # Act & Assert
        assert validate_phone("+1 234 567 8900") == False

    def test_validate_phone_empty(self):
        """
        Тест: пустая строка.
        """
        # Act & Assert
        assert validate_phone("") == False

    def test_validate_phone_with_parentheses(self):
        """
        Тест: телефон с скобками.
        """
        # Act & Assert
        assert validate_phone("+7 (999) 123-45-67") == True
        assert validate_phone("8(999)1234567") == True


class TestNormalizePhone:
    """Тесты нормализации телефона"""

    def test_normalize_phone_eight_to_plus_seven(self):
        """
        Тест: преобразование 8 в +7.
        """
        # Act
        result = normalize_phone("89991234567")
        
        # Assert
        assert result == "+79991234567"

    def test_normalize_phone_plus_seven(self):
        """
        Тест: телефон уже в формате +7.
        """
        # Act
        result = normalize_phone("+79991234567")
        
        # Assert
        assert result == "+79991234567"

    def test_normalize_phone_with_spaces(self):
        """
        Тест: нормализация телефона с пробелами.
        """
        # Act
        result = normalize_phone("+7 999 123-45-67")
        
        # Assert
        assert result == "+79991234567"

    def test_normalize_phone_empty(self):
        """
        Тест: пустая строка.
        """
        # Act
        result = normalize_phone("")
        
        # Assert
        assert result == ""


class TestTruncateText:
    """Тесты обрезки текста"""

    def test_truncate_text_long(self):
        """
        Тест: обрезка длинного текста.
        """
        # Arrange
        text = "A" * 100
        
        # Act
        result = truncate_text(text, max_length=50)
        
        # Assert
        assert len(result) == 50
        assert result.endswith("...")

    def test_truncate_text_short(self):
        """
        Тест: короткий текст не обрезается.
        """
        # Arrange
        text = "Короткий текст"
        
        # Act
        result = truncate_text(text, max_length=50)
        
        # Assert
        assert result == text

    def test_truncate_text_empty(self):
        """
        Тест: пустая строка.
        """
        # Act
        result = truncate_text("")
        
        # Assert
        assert result == ""

    def test_truncate_text_custom_suffix(self):
        """
        Тест: пользовательский суффикс.
        """
        # Act
        result = truncate_text("A" * 100, max_length=50, suffix="…")
        
        # Assert
        assert result.endswith("…")


class TestSanitizeHtml:
    """Тесты экранирования HTML"""

    def test_sanitize_html_ampersand(self):
        """
        Тест: экранирование &.
        """
        # Act
        result = sanitize_html("A & B")
        
        # Assert
        assert result == "A &amp; B"

    def test_sanitize_html_tags(self):
        """
        Тест: экранирование тегов.
        """
        # Act
        result = sanitize_html("<script>alert('XSS')</script>")
        
        # Assert
        assert "<" not in result
        assert ">" not in result
        assert "&lt;" in result
        assert "&gt;" in result

    def test_sanitize_html_empty(self):
        """
        Тест: пустая строка.
        """
        # Act
        result = sanitize_html("")
        
        # Assert
        assert result == ""

    def test_sanitize_html_safe_text(self):
        """
        Тест: безопасный текст не меняется.
        """
        # Act
        result = sanitize_html("Обычный текст без спецсимволов")
        
        # Assert
        assert result == "Обычный текст без спецсимволов"


class TestPluralForm:
    """Тесты склонения существительных"""

    def test_plural_form_one(self):
        """
        Тест: единственное число.
        """
        # Act
        result = plural_form(1, ('товар', 'товара', 'товаров'))
        
        # Assert
        assert result == 'товар'

    def test_plural_form_two(self):
        """
        Тест: два.
        """
        # Act
        result = plural_form(2, ('товар', 'товара', 'товаров'))
        
        # Assert
        assert result == 'товара'

    def test_plural_form_five(self):
        """
        Тест: пять.
        """
        # Act
        result = plural_form(5, ('товар', 'товара', 'товаров'))
        
        # Assert
        assert result == 'товаров'

    def test_plural_form_eleven(self):
        """
        Тест: одиннадцать (исключение).
        """
        # Act
        result = plural_form(11, ('товар', 'товара', 'товаров'))
        
        # Assert
        assert result == 'товаров'

    def test_plural_form_twenty_one(self):
        """
        Тест: двадцать один.
        """
        # Act
        result = plural_form(21, ('товар', 'товара', 'товаров'))
        
        # Assert
        assert result == 'товар'

    def test_plural_form_twenty_two(self):
        """
        Тест: двадцать два.
        """
        # Act
        result = plural_form(22, ('товар', 'товара', 'товаров'))
        
        # Assert
        assert result == 'товара'

    def test_plural_form_zero(self):
        """
        Тест: ноль.
        """
        # Act
        result = plural_form(0, ('товар', 'товара', 'товаров'))
        
        # Assert
        assert result == 'товаров'

    def test_plural_form_negative(self):
        """
        Тест: отрицательное число.
        """
        # Act
        result = plural_form(-5, ('товар', 'товара', 'товаров'))
        
        # Assert
        assert result == 'товаров'
