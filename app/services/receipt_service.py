"""
ReceiptService - сервис генерации электронных чеков.
"""

from pathlib import Path
from decimal import Decimal
from datetime import datetime

from app.dto import ReceiptData
from app.exceptions import OrderNotFoundError, OrderNotPaidError


class ReceiptService:
    """Сервис генерации и отправки PDF-чеков"""

    def __init__(self, order_repo=None, bot=None, receipts_dir: str = './tmp/receipts'):
        self.order_repo = order_repo
        self.bot = bot
        self.receipts_dir = receipts_dir

    async def get_receipt_data(self, order_id: int) -> ReceiptData:
        """
        Подготовка данных для формирования чека.
        """
        order = await self.order_repo.get_order_by_id(order_id)
        
        if not order:
            raise OrderNotFoundError(order_id)
        
        order_items = await self.order_repo.get_order_items(order_id)
        
        items = []
        for item in order_items:
            items.append({
                'name': item.product_name,
                'price': Decimal(str(item.price)),
                'qty': item.qty,
                'subtotal': Decimal(str(item.price)) * item.qty
            })
        
        subtotal = sum(item['subtotal'] for item in items)
        
        return ReceiptData(
            order_number=order.order_number,
            order_date=order.created_at,
            customer_name=order.contact_name,
            customer_phone=order.contact_phone,
            customer_address=order.contact_address,
            items=items,
            subtotal=subtotal,
            discount=Decimal(str(order.discount)),
            total=Decimal(str(order.total)),
            payment_method=order.payment_method
        )

    async def generate_receipt_pdf(self, order_id: int) -> str:
        """
        Генерация PDF-файла чека.
        """
        order = await self.order_repo.get_order_by_id(order_id)
        
        if not order:
            raise OrderNotFoundError(order_id)
        
        if order.status not in ('paid', 'shipped', 'delivered'):
            raise OrderNotPaidError(order_id)
        
        # Создание директории
        receipts_path = Path(self.receipts_dir)
        receipts_path.mkdir(parents=True, exist_ok=True)
        
        # Получение данных чека
        receipt_data = await self.get_receipt_data(order_id)
        
        # Генерация PDF с помощью ReportLab
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        
        filename = f"{receipt_data.order_number}.pdf"
        filepath = receipts_path / filename
        
        c = canvas.Canvas(str(filepath), pagesize=A4)
        width, height = A4
        
        # Заголовок
        c.setFont("Helvetica-Bold", 16)
        c.drawString(2*cm, height - 2*cm, "ЭЛЕКТРОННЫЙ ЧЕК")
        
        # Номер и дата заказа
        c.setFont("Helvetica", 12)
        c.drawString(2*cm, height - 3*cm, f"Заказ: {receipt_data.order_number}")
        c.drawString(2*cm, height - 3.5*cm, 
                    f"Дата: {receipt_data.order_date.strftime('%d.%m.%Y %H:%M')}")
        
        # Информация о покупателе
        c.drawString(2*cm, height - 4.5*cm, f"Покупатель: {receipt_data.customer_name}")
        c.drawString(2*cm, height - 5*cm, f"Телефон: {receipt_data.customer_phone}")
        
        # Таблица товаров
        y = height - 6.5*cm
        c.setFont("Helvetica-Bold", 10)
        c.drawString(2*cm, y, "Наименование")
        c.drawString(10*cm, y, "Кол-во")
        c.drawString(12*cm, y, "Цена")
        c.drawString(15*cm, y, "Сумма")
        
        y -= 0.5*cm
        c.line(2*cm, y, 19*cm, y)
        
        c.setFont("Helvetica", 10)
        for item in receipt_data.items:
            y -= 0.6*cm
            name = item['name'][:40]  # Обрезаем длинные названия
            c.drawString(2*cm, y, name)
            c.drawString(10*cm, y, str(item['qty']))
            c.drawString(12*cm, y, f"{item['price']:,.0f} ₽")
            c.drawString(15*cm, y, f"{item['subtotal']:,.0f} ₽")
        
        # Итоги
        y -= 1*cm
        c.line(2*cm, y, 19*cm, y)
        y -= 0.5*cm
        
        c.drawString(12*cm, y, f"Подитог: {receipt_data.subtotal:,.0f} ₽")
        
        if receipt_data.discount > 0:
            y -= 0.5*cm
            c.drawString(12*cm, y, f"Скидка: -{receipt_data.discount:,.0f} ₽")
        
        y -= 0.7*cm
        c.setFont("Helvetica-Bold", 12)
        c.drawString(12*cm, y, f"ИТОГО: {receipt_data.total:,.0f} ₽")
        
        # Способ оплаты
        y -= 1*cm
        c.setFont("Helvetica", 10)
        payment_text = "Банковская карта" if receipt_data.payment_method == 'card' else "Наличные"
        c.drawString(2*cm, y, f"Способ оплаты: {payment_text}")
        
        c.save()
        
        return str(filepath)

    async def send_receipt(self, user_id: int, receipt_path: str) -> bool:
        """
        Отправка PDF-чека пользователю через Telegram.
        """
        try:
            from aiogram.types import InputFile
            
            receipt_file = InputFile(receipt_path)
            filename = Path(receipt_path).name
            
            await self.bot.send_document(
                chat_id=user_id,
                document=receipt_file,
                caption=f"📄 Ваш электронный чек: {filename}"
            )
            
            return True
        except Exception as e:
            # Логируем ошибку, но не прерываем процесс
            print(f"Ошибка отправки чека: {e}")
            return False
