"""
ORM-модели GINO для телеграм-бота интернет-магазина.
Схема: shop_test
"""

from gino import Gino
from datetime import datetime
from decimal import Decimal

db = Gino()


class Category(db.Model):
    """Категория товаров"""
    __tablename__ = 'categories'

    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    sort_order = db.Column(db.Integer(), default=0)
    is_active = db.Column(db.Boolean(), default=True)
    created_at = db.Column(db.DateTime(), default=datetime.utcnow)


class Product(db.Model):
    """Товар в каталоге"""
    __tablename__ = 'products'

    id = db.Column(db.Integer(), primary_key=True)
    category_id = db.Column(db.Integer(), db.ForeignKey('categories.id'), nullable=False)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text(), default='')
    price = db.Column(db.Numeric(10, 2), nullable=False)
    stock = db.Column(db.Integer(), default=0)
    image_url = db.Column(db.String(500), default='')
    is_active = db.Column(db.Boolean(), default=True)
    created_at = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)


class User(db.Model):
    """Пользователь бота"""
    __tablename__ = 'users'

    id = db.Column(db.Integer(), primary_key=True)
    telegram_id = db.Column(db.BigInteger(), unique=True, nullable=False)
    name = db.Column(db.String(200), default='')
    phone = db.Column(db.String(20), default='')
    address = db.Column(db.Text(), default='')
    is_admin = db.Column(db.Boolean(), default=False)
    created_at = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)


class Cart(db.Model):
    """Позиция в корзине пользователя"""
    __tablename__ = 'carts'

    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer(), db.ForeignKey('products.id'), nullable=False)
    qty = db.Column(db.Integer(), default=1)
    created_at = db.Column(db.DateTime(), default=datetime.utcnow)

    _idx = db.Index('idx_cart_user_product', 'user_id', 'product_id', unique=True)


class Order(db.Model):
    """Заказ"""
    __tablename__ = 'orders'

    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id'), nullable=False)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    status = db.Column(db.String(20), default='created')
    total = db.Column(db.Numeric(10, 2), default=0)
    discount = db.Column(db.Numeric(10, 2), default=0)
    contact_name = db.Column(db.String(200), default='')
    contact_phone = db.Column(db.String(20), default='')
    contact_address = db.Column(db.Text(), default='')
    payment_method = db.Column(db.String(20), default='card')
    created_at = db.Column(db.DateTime(), default=datetime.utcnow)
    updated_at = db.Column(db.DateTime(), default=datetime.utcnow, onupdate=datetime.utcnow)


class OrderItem(db.Model):
    """Позиция заказа"""
    __tablename__ = 'order_items'

    id = db.Column(db.Integer(), primary_key=True)
    order_id = db.Column(db.Integer(), db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer(), db.ForeignKey('products.id'), nullable=False)
    product_name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    qty = db.Column(db.Integer(), default=1)


class Favorite(db.Model):
    """Избранный товар пользователя"""
    __tablename__ = 'favorites'

    id = db.Column(db.Integer(), primary_key=True)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer(), db.ForeignKey('products.id'), nullable=False)
    created_at = db.Column(db.DateTime(), default=datetime.utcnow)

    _idx = db.Index('idx_fav_user_product', 'user_id', 'product_id', unique=True)


class Promocode(db.Model):
    """Промокод"""
    __tablename__ = 'promocodes'

    id = db.Column(db.Integer(), primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False)
    discount_type = db.Column(db.String(20), default='percent')  # percent / fixed
    discount_value = db.Column(db.Numeric(10, 2), nullable=False)
    valid_from = db.Column(db.DateTime(), nullable=False)
    valid_to = db.Column(db.DateTime(), nullable=False)
    is_used = db.Column(db.Boolean(), default=False)
    max_uses = db.Column(db.Integer(), default=1)
    current_uses = db.Column(db.Integer(), default=0)
    created_at = db.Column(db.DateTime(), default=datetime.utcnow)


class PromocodeUsage(db.Model):
    """История использования промокодов"""
    __tablename__ = 'promocode_usage'

    id = db.Column(db.Integer(), primary_key=True)
    promocode_id = db.Column(db.Integer(), db.ForeignKey('promocodes.id'), nullable=False)
    user_id = db.Column(db.Integer(), db.ForeignKey('users.id'), nullable=False)
    order_id = db.Column(db.Integer(), db.ForeignKey('orders.id'), nullable=False)
    used_at = db.Column(db.DateTime(), default=datetime.utcnow)


class Payment(db.Model):
    """Платёжная сессия"""
    __tablename__ = 'payments'

    id = db.Column(db.Integer(), primary_key=True)
    order_id = db.Column(db.Integer(), db.ForeignKey('orders.id'), nullable=False)
    session_id = db.Column(db.String(100), unique=True, nullable=False)
    status = db.Column(db.String(20), default='pending')
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_url = db.Column(db.String(500), default='')
    created_at = db.Column(db.DateTime(), default=datetime.utcnow)
    expires_at = db.Column(db.DateTime())
