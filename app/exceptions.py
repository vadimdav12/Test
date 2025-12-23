"""
Пользовательские исключения для телеграм-бота интернет-магазина.
"""


class ShopBotException(Exception):
    """Базовое исключение приложения"""
    pass


class ValidationError(ShopBotException):
    """Ошибка валидации данных"""
    pass


class InsufficientStockError(ShopBotException):
    """Недостаточно товара на складе"""
    def __init__(self, product_id: int, available: int, requested: int):
        self.product_id = product_id
        self.available = available
        self.requested = requested
        super().__init__(f"Недостаточно товара. Доступно: {available}, запрошено: {requested}")


class ProductNotFoundError(ShopBotException):
    """Товар не найден"""
    def __init__(self, product_id: int):
        self.product_id = product_id
        super().__init__(f"Товар с id={product_id} не найден")


class CategoryNotFoundError(ShopBotException):
    """Категория не найдена"""
    def __init__(self, category_id: int):
        self.category_id = category_id
        super().__init__(f"Категория с id={category_id} не найдена")


class CategoryNotEmptyError(ShopBotException):
    """Категория содержит товары и не может быть удалена"""
    def __init__(self, category_id: int, products_count: int):
        self.category_id = category_id
        self.products_count = products_count
        super().__init__(f"Категория содержит {products_count} товаров и не может быть удалена")


class DuplicateCategoryError(ShopBotException):
    """Категория с таким именем уже существует"""
    def __init__(self, name: str):
        self.name = name
        super().__init__(f"Категория '{name}' уже существует")


class CartItemNotFoundError(ShopBotException):
    """Позиция не найдена в корзине"""
    def __init__(self, user_id: int, product_id: int):
        self.user_id = user_id
        self.product_id = product_id
        super().__init__(f"Позиция product_id={product_id} не найдена в корзине пользователя {user_id}")


class EmptyCartError(ShopBotException):
    """Корзина пуста"""
    def __init__(self, user_id: int):
        self.user_id = user_id
        super().__init__("Невозможно оформить заказ: корзина пуста")


class OrderNotFoundError(ShopBotException):
    """Заказ не найден"""
    def __init__(self, order_id: int):
        self.order_id = order_id
        super().__init__(f"Заказ с id={order_id} не найден")


class OrderNotPaidError(ShopBotException):
    """Заказ не оплачен"""
    def __init__(self, order_id: int):
        self.order_id = order_id
        super().__init__(f"Заказ {order_id} не оплачен. Чек недоступен")


class OrderCannotBeCancelledError(ShopBotException):
    """Заказ не может быть отменён"""
    def __init__(self, order_id: int, status: str):
        self.order_id = order_id
        self.status = status
        super().__init__(f"Заказ {order_id} в статусе '{status}' не может быть отменён")


class InvalidStatusTransitionError(ShopBotException):
    """Недопустимый переход статуса заказа"""
    def __init__(self, order_id: int, current_status: str, new_status: str):
        self.order_id = order_id
        self.current_status = current_status
        self.new_status = new_status
        super().__init__(
            f"Недопустимый переход статуса заказа {order_id}: "
            f"'{current_status}' -> '{new_status}'"
        )


class PromocodeNotFoundError(ShopBotException):
    """Промокод не найден"""
    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Промокод '{code}' не найден")


class PromocodeExpiredError(ShopBotException):
    """Промокод истёк"""
    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Промокод '{code}' истёк")


class PromocodeAlreadyUsedError(ShopBotException):
    """Промокод уже использован"""
    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Промокод '{code}' уже использован")


class PaymentGatewayError(ShopBotException):
    """Ошибка платёжного шлюза"""
    def __init__(self, message: str):
        super().__init__(f"Ошибка платёжного шлюза: {message}")


class InvalidSignatureError(ShopBotException):
    """Неверная подпись платёжного callback"""
    pass


class UserNotFoundError(ShopBotException):
    """Пользователь не найден"""
    def __init__(self, user_id: int):
        self.user_id = user_id
        super().__init__(f"Пользователь с id={user_id} не найден")


class AccessDeniedError(ShopBotException):
    """Доступ запрещён"""
    def __init__(self, user_id: int, resource: str):
        self.user_id = user_id
        self.resource = resource
        super().__init__(f"Пользователь {user_id} не имеет доступа к {resource}")
