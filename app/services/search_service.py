"""
SearchService - сервис поиска товаров по каталогу.
"""

from typing import List
from decimal import Decimal
import re

from app.dto import ProductHit


class SearchService:
    """Сервис поиска товаров с нечётким соответствием"""

    # Таблица транслитерации
    TRANSLIT_MAP = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        # Обратная транслитерация для поиска
        'samsung': 'самсунг', 'iphone': 'айфон', 'xiaomi': 'сяоми',
        'macbook': 'макбук', 'airpods': 'эирподс'
    }

    def __init__(self, product_repo=None):
        self.product_repo = product_repo

    def normalize_query(self, query: str) -> str:
        """
        Нормализация поискового запроса.
        """
        if not query:
            return ''
        
        # Приведение к нижнему регистру
        query = query.lower().strip()
        
        # Удаление лишних пробелов
        query = re.sub(r'\s+', ' ', query)
        
        # Удаление специальных символов (кроме букв, цифр и пробелов)
        query = re.sub(r'[^\w\s\u0400-\u04FF]', '', query)
        
        return query

    def levenshtein_distance(self, s1: str, s2: str) -> int:
        """
        Вычисление редакционного расстояния Левенштейна.
        """
        if len(s1) < len(s2):
            s1, s2 = s2, s1
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            
            for j, c2 in enumerate(s2):
                # Стоимость операций: вставка, удаление, замена
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                
                current_row.append(min(insertions, deletions, substitutions))
            
            previous_row = current_row
        
        return previous_row[-1]

    def fuzzy_match(self, word1: str, word2: str) -> float:
        """
        Оценка степени похожести двух слов (0.0 - 1.0).
        """
        if not word1 or not word2:
            return 0.0
        
        word1 = word1.lower()
        word2 = word2.lower()
        
        if word1 == word2:
            return 1.0
        
        distance = self.levenshtein_distance(word1, word2)
        max_len = max(len(word1), len(word2))
        
        if max_len == 0:
            return 1.0
        
        similarity = 1.0 - (distance / max_len)
        
        return max(0.0, similarity)

    def _get_max_distance(self, word_len: int) -> int:
        """
        Получение адаптивного порога расстояния Левенштейна.
        """
        if word_len <= 3:
            return 1
        elif word_len <= 5:
            return 2
        elif word_len <= 7:
            return 3
        else:
            return 4

    def _transliterate(self, text: str) -> str:
        """
        Транслитерация текста для сравнения.
        """
        result = text.lower()
        
        # Замена известных слов
        for ru, en in [('самсунг', 'samsung'), ('айфон', 'iphone'), 
                       ('сяоми', 'xiaomi'), ('макбук', 'macbook')]:
            result = result.replace(ru, en)
        
        # Посимвольная транслитерация
        transliterated = []
        for char in result:
            transliterated.append(self.TRANSLIT_MAP.get(char, char))
        
        return ''.join(transliterated)

    async def search_products(self, query: str, limit: int = 10) -> List[ProductHit]:
        """
        Поиск товаров с учётом опечаток и частичных совпадений.
        """
        query = self.normalize_query(query)
        
        if not query:
            return []
        
        # Получаем все активные товары
        all_products = await self.product_repo.search_products(query)
        
        # Если нет результатов по точному поиску, ищем нечётко
        if not all_products:
            all_products = await self.product_repo.fetch_all_active_products()
        
        results = []
        query_tokens = query.split()
        query_translit = self._transliterate(query)
        
        for product in all_products:
            product_name_lower = product.name.lower()
            product_name_translit = self._transliterate(product_name_lower)
            
            # Проверка точного совпадения
            if query in product_name_lower or query_translit in product_name_translit:
                results.append(ProductHit(
                    product_id=product.id,
                    product_name=product.name,
                    price=Decimal(str(product.price)),
                    score=1.0,
                    match_type='exact'
                ))
                continue
            
            # Нечёткий поиск по токенам
            best_score = 0.0
            name_tokens = product_name_lower.split()
            
            for q_token in query_tokens:
                q_token_translit = self._transliterate(q_token)
                max_dist = self._get_max_distance(len(q_token))
                
                for n_token in name_tokens:
                    n_token_translit = self._transliterate(n_token)
                    
                    # Сравнение оригиналов
                    score = self.fuzzy_match(q_token, n_token)
                    if score > best_score:
                        best_score = score
                    
                    # Сравнение транслитераций
                    score_translit = self.fuzzy_match(q_token_translit, n_token_translit)
                    if score_translit > best_score:
                        best_score = score_translit
            
            if best_score >= 0.6:
                match_type = 'fuzzy' if best_score < 0.9 else 'partial'
                results.append(ProductHit(
                    product_id=product.id,
                    product_name=product.name,
                    price=Decimal(str(product.price)),
                    score=best_score,
                    match_type=match_type
                ))
        
        # Сортировка по релевантности
        results.sort(key=lambda x: (-x.score, x.product_name))
        
        return results[:limit]
