"""
Вспомогательные функции для телеграм-бота.
"""

import re
from decimal import Decimal
from typing import Union


def format_price(amount: Union[int, float, Decimal]) -> str:
    """
    Форматирование цены с разделителями тысяч и символом рубля.
    
    Примеры:
        15000 -> "15 000 ₽"
        1000000 -> "1 000 000 ₽"
        99 -> "99 ₽"
        0 -> "0 ₽"
    """
    if amount is None:
        return "0 ₽"
    
    # Преобразуем в целое число
    value = int(amount)
    
    # Форматируем с разделителями тысяч
    formatted = f"{value:,}".replace(',', ' ')
    
    return f"{formatted} ₽"


def validate_phone(phone: str) -> bool:
    """
    Валидация российского номера телефона.
    
    Поддерживаемые форматы:
        +7 999 123-45-67
        +79991234567
        8 999 123 45 67
        89991234567
    
    Возвращает:
        True если формат корректный
        False в противном случае
    """
    if not phone:
        return False
    
    # Убираем все символы кроме цифр и +
    clean_phone = re.sub(r'[^\d+]', '', phone)
    
    # Проверяем формат с +7
    if clean_phone.startswith('+7'):
        return len(clean_phone) == 12
    
    # Проверяем формат с 8
    if clean_phone.startswith('8'):
        return len(clean_phone) == 11
    
    # Проверяем формат с 7 (без плюса)
    if clean_phone.startswith('7'):
        return len(clean_phone) == 11
    
    return False


def normalize_phone(phone: str) -> str:
    """
    Нормализация номера телефона к формату +7XXXXXXXXXX.
    """
    if not phone:
        return ''
    
    # Убираем все кроме цифр
    digits = re.sub(r'\D', '', phone)
    
    # Приводим к формату с 7
    if len(digits) == 11 and digits.startswith('8'):
        digits = '7' + digits[1:]
    
    if len(digits) == 11 and digits.startswith('7'):
        return f"+{digits}"
    
    if len(digits) == 10:
        return f"+7{digits}"
    
    return phone  # Возвращаем как есть, если не удалось нормализовать


def truncate_text(text: str, max_length: int = 50, suffix: str = '...') -> str:
    """
    Обрезка текста до указанной длины с добавлением суффикса.
    """
    if not text:
        return ''
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def sanitize_html(text: str) -> str:
    """
    Экранирование HTML-спецсимволов для безопасного отображения в Telegram.
    """
    if not text:
        return ''
    
    return (
        text
        .replace('&', '&amp;')
        .replace('<', '&lt;')
        .replace('>', '&gt;')
    )


def plural_form(n: int, forms: tuple) -> str:
    """
    Выбор правильной формы слова в зависимости от числа.
    
    Примеры:
        plural_form(1, ('товар', 'товара', 'товаров')) -> 'товар'
        plural_form(2, ('товар', 'товара', 'товаров')) -> 'товара'
        plural_form(5, ('товар', 'товара', 'товаров')) -> 'товаров'
    """
    n = abs(n)
    
    if n % 10 == 1 and n % 100 != 11:
        return forms[0]
    
    if 2 <= n % 10 <= 4 and (n % 100 < 10 or n % 100 >= 20):
        return forms[1]
    
    return forms[2]
