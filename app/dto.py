"""
Data Transfer Objects для телеграм-бота интернет-магазина.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime
from typing import Optional, List


@dataclass
class ProductCreate:
    """DTO для создания товара"""
    name: str
    price: Decimal
    category_id: int
    description: str = ''
    stock: int = 0
    image_url: str = ''


@dataclass
class ProductUpdate:
    """DTO для обновления товара"""
    name: Optional[str] = None
    price: Optional[Decimal] = None
    category_id: Optional[int] = None
    description: Optional[str] = None
    stock: Optional[int] = None
    image_url: Optional[str] = None


@dataclass
class ContactData:
    """Контактные данные для заказа"""
    name: str
    phone: str
    address: str


@dataclass
class ProfileUpdate:
    """DTO для обновления профиля"""
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None


@dataclass
class CartItem:
    """Позиция корзины"""
    product_id: int
    product_name: str
    price: Decimal
    qty: int
    stock: int = 0
    
    @property
    def subtotal(self) -> Decimal:
        return self.price * self.qty


@dataclass
class Cart:
    """Корзина пользователя"""
    user_id: int
    items: List[CartItem] = field(default_factory=list)
    promocode: Optional[str] = None
    
    @property
    def is_empty(self) -> bool:
        return len(self.items) == 0


@dataclass
class CartTotals:
    """Итоговые суммы корзины"""
    subtotal: Decimal
    discount: Decimal
    total: Decimal
    items_count: int
    positions_count: int


@dataclass
class PromoCheckResult:
    """Результат проверки промокода"""
    valid: bool
    discount_type: Optional[str] = None  # 'percent' или 'fixed'
    discount_value: Optional[Decimal] = None
    error_message: Optional[str] = None


@dataclass
class DiscountResult:
    """Результат применения скидок"""
    auto_discount: Decimal
    promo_discount: Decimal
    total_discount: Decimal
    applied_rules: List[str] = field(default_factory=list)


@dataclass
class ProductHit:
    """Результат поиска товара"""
    product_id: int
    product_name: str
    price: Decimal
    score: float
    match_type: str  # 'exact', 'fuzzy', 'partial'


@dataclass
class Profile:
    """Профиль пользователя"""
    user_id: int
    telegram_id: int
    name: str
    phone: str
    address: str
    orders_count: int
    total_spent: Decimal
    registered_at: datetime


@dataclass
class ReceiptData:
    """Данные для генерации чека"""
    order_number: str
    order_date: datetime
    customer_name: str
    customer_phone: str
    customer_address: str
    items: List[dict]
    subtotal: Decimal
    discount: Decimal
    total: Decimal
    payment_method: str


@dataclass
class PaymentSession:
    """Платёжная сессия"""
    session_id: str
    payment_url: str
    expires_at: datetime
    amount: Decimal


@dataclass
class PaymentResult:
    """Результат обработки платежа"""
    success: bool
    order_id: Optional[int] = None
    error_message: Optional[str] = None


@dataclass
class OrderData:
    """Данные для создания заказа"""
    user_id: int
    items: List[CartItem]
    contact: ContactData
    payment_method: str
    subtotal: Decimal
    discount: Decimal
    total: Decimal
    promocode: Optional[str] = None
