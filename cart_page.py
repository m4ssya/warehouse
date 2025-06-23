from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QScrollArea, QFrame, QSizePolicy, QLineEdit, QMessageBox, QInputDialog, QDialog
)
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QIcon, QFontMetrics
import datetime
from PyQt5.QtGui import QDoubleValidator

class CartProductDetailWidget(QWidget):
    def __init__(self, item, on_apply_discount, parent=None):
        super().__init__(parent)
        self.item = item
        self.on_apply_discount = on_apply_discount
        self.setStyleSheet('''
            QWidget {
                background-color: #23242a;
                border-radius: 12px;
                border: 2px solid #28a745;
            }
            QLabel {
                color: white;
                font-size: 15px;
            }
            QLineEdit {
                background-color: #23242a;
                color: #43e97b;
                border: 1px solid #28a745;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 15px;
                min-width: 80px;
            }
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 18px;
                font-size: 15px;
            }
            QPushButton#closeBtn {
                background-color: #6c757d;
            }
            QPushButton#closeBtn:hover {
                background-color: #495057;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        ''')
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)
        # Фото
        if self.item.get('image'):
            from PyQt5.QtGui import QPixmap
            pixmap = QPixmap(self.item['image'])
            if not pixmap.isNull():
                img_label = QLabel()
                img_label.setPixmap(pixmap.scaled(120, 90, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                img_label.setAlignment(Qt.AlignCenter)
                layout.addWidget(img_label)
        # Название
        name_label = QLabel(f"<b>{self.item['name']}</b>")
        name_label.setStyleSheet("font-size: 18px; color: #43e97b;")
        layout.addWidget(name_label)
        # Категория
        if self.item.get('category'):
            cat_label = QLabel(f"Категория: {self.item['category']}")
            cat_label.setStyleSheet("color: #aaa; font-size: 14px;")
            layout.addWidget(cat_label)
        # Количество
        qty_label = QLabel(f"В корзине: {self.item['quantity']} шт.")
        qty_label.setStyleSheet("color: #aaa; font-size: 14px;")
        layout.addWidget(qty_label)
        # Цена
        price_label = QLabel(f"Текущая цена: <b>{float(self.item['price']):.2f} ₽</b>")
        price_label.setStyleSheet("color: #28a745; font-size: 16px;")
        layout.addWidget(price_label)
        # Поле для скидки
        self.price_edit = QLineEdit(f"{float(self.item['price']):.2f}")
        self.price_edit.setValidator(QDoubleValidator(0, 1000000, 2, self.price_edit))
        layout.addWidget(self.price_edit)
        # Кнопки
        btn_layout = QHBoxLayout()
        apply_btn = QPushButton("Применить")
        apply_btn.clicked.connect(self.apply_discount)
        close_btn = QPushButton("Закрыть")
        close_btn.setObjectName("closeBtn")
        close_btn.clicked.connect(self.close_detail)
        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(close_btn)
        layout.addLayout(btn_layout)
    def apply_discount(self):
        try:
            new_price = float(self.price_edit.text())
            self.on_apply_discount(self.item, new_price)
        except Exception:
            pass
    def close_detail(self):
        self.setParent(None)
        self.deleteLater()
        CartItemWidget.detail_widget = None

class CartItemWidget(QWidget):
    detail_widget = None  # Класс-атрибут, чтобы показывать только одну карточку
    def __init__(self, item, on_increase, on_decrease, on_set_quantity=None, parent=None):
        super().__init__(parent)
        self.item = item
        self.on_increase = on_increase
        self.on_decrease = on_decrease
        self.on_set_quantity = on_set_quantity
        self.tooltip = None
        self.tooltip_timer = QTimer(self)
        self.tooltip_timer.setSingleShot(True)
        self.tooltip_timer.timeout.connect(self.show_custom_tooltip)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        self.name = QLabel(item['name'])
        self.name.setStyleSheet("font-size: 14px; color: #43e97b; text-decoration: underline; cursor: pointer;")
        self.name.setWordWrap(True)
        self.name.setMaximumWidth(140)
        layout.addWidget(self.name)
        self.name.mousePressEvent = self.show_detail
        self.name.installEventFilter(self)
        btn_minus = QPushButton("−")
        btn_minus.setFixedSize(24, 24)
        btn_minus.setStyleSheet("background-color: #444; color: white; border-radius: 6px;")
        btn_minus.clicked.connect(self.decrease)
        layout.addWidget(btn_minus)
        self.qty_label = QLabel(f"{item['quantity']} шт.")
        self.qty_label.setStyleSheet("font-size: 14px; color: #28a745; background: transparent;")
        self.qty_label.setCursor(Qt.PointingHandCursor)
        self.qty_label.mousePressEvent = self.show_qty_editor
        layout.addWidget(self.qty_label)
        self.qty_edit = QLineEdit(str(item['quantity']))
        self.qty_edit.setFixedWidth(40)
        self.qty_edit.setStyleSheet("font-size: 14px; color: #28a745; background: #222; border: 1px solid #28a745; border-radius: 4px;")
        self.qty_edit.setAlignment(Qt.AlignCenter)
        self.qty_edit.hide()
        self.qty_edit.editingFinished.connect(self.set_quantity)
        layout.addWidget(self.qty_edit)
        btn_plus = QPushButton("+")
        btn_plus.setFixedSize(24, 24)
        btn_plus.setStyleSheet("background-color: #444; color: white; border-radius: 6px;")
        btn_plus.clicked.connect(self.increase)
        layout.addWidget(btn_plus)
        price = QLabel(f"{float(item['price']):.2f} ₽")
        price.setStyleSheet("font-size: 14px; color: #aaa;")
        layout.addWidget(price)
        layout.addStretch()
        self.price_label = price  # Сохраняем для обновления
    def show_detail(self, event):
        # Закрыть предыдущую открытую карточку, если есть
        if CartItemWidget.detail_widget:
            try:
                CartItemWidget.detail_widget.close_detail()
            except RuntimeError:
                pass
            CartItemWidget.detail_widget = None
        def on_apply_discount(item, new_price):
            item['price'] = new_price
            self.price_label.setText(f"{new_price:.2f} ₽")
            # Обновить сумму сразу после применения скидки
            parent = self.parent()
            while parent is not None:
                if hasattr(parent, 'update_total'):
                    parent.update_total()
                    break
                parent = parent.parent() if hasattr(parent, 'parent') else None
        detail = CartProductDetailWidget(self.item, on_apply_discount, parent=self.parent())
        self.parent().layout().insertWidget(self.parent().layout().indexOf(self) + 1, detail)
        CartItemWidget.detail_widget = detail

    def eventFilter(self, obj, event):
        if obj == self.name:
            if event.type() == event.Enter:
                self.tooltip_timer.start(500)
            elif event.type() == event.Leave:
                self.tooltip_timer.stop()
                self.hide_custom_tooltip()
        return super().eventFilter(obj, event)

    def show_custom_tooltip(self):
        if self.tooltip:
            self.tooltip.hide()
            self.tooltip.deleteLater()
        self.tooltip = QLabel(self.item['name'], self)
        self.tooltip.setStyleSheet("""
            QLabel {
                background-color: #23242a;
                color: #f5f6fa;
                border: 1px solid #28a745;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
            }
        """)
        self.tooltip.setWordWrap(True)
        self.tooltip.setMaximumWidth(300)
        self.tooltip.setWindowFlags(Qt.ToolTip)
        self.tooltip.adjustSize()
        global_pos = self.name.mapToGlobal(QPoint(0, self.name.height()))
        self.tooltip.move(global_pos)
        self.tooltip.show()

    def hide_custom_tooltip(self):
        if self.tooltip:
            self.tooltip.hide()
            self.tooltip.deleteLater()
            self.tooltip = None

    def increase(self):
        if self.on_increase:
            self.on_increase(self.item)

    def decrease(self):
        if self.on_decrease:
            self.on_decrease(self.item)

    def show_qty_editor(self, event):
        self.qty_label.hide()
        self.qty_edit.setText(str(self.item['quantity']))
        self.qty_edit.show()
        self.qty_edit.setFocus()
        self.qty_edit.selectAll()

    def set_quantity(self):
        text = self.qty_edit.text()
        try:
            value = int(text)
            if value < 1:
                value = 1
        except ValueError:
            value = self.item['quantity']
        if self.on_set_quantity:
            self.on_set_quantity(self.item, value)
        self.qty_edit.hide()
        self.qty_label.setText(f"{value} шт.")
        self.qty_label.show()

class CartPage(QWidget):
    def __init__(self, parent=None, on_cart_changed=None, db=None, on_order_success=None, username=None, sales_history_page=None):
        super().__init__(parent)
        self.cart_items = []  # Здесь будут храниться товары
        self.on_cart_changed = on_cart_changed
        self.db = db  # Добавляем ссылку на базу данных
        self.on_order_success = on_order_success  # Новый callback
        self.username = username
        self.sales_history_page = sales_history_page
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        # Заголовок
        header = QFrame()
        header.setStyleSheet("""
            QFrame {
                background-color: #2a2b38;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        header_layout = QHBoxLayout(header)
        
        title = QLabel("Корзина")
        title.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: white;
            }
        """)
        header_layout.addWidget(title)
        
        clear_btn = QPushButton("Очистить")
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 15px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #bd2130;
            }
        """)
        header_layout.addWidget(clear_btn)
        
        layout.addWidget(header)
        
        # Область прокрутки для товаров
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        self.items_container = QWidget()
        self.items_layout = QVBoxLayout(self.items_container)
        self.items_layout.setSpacing(10)
        self.items_layout.setAlignment(Qt.AlignTop)
        
        scroll.setWidget(self.items_container)
        layout.addWidget(scroll)
        
        # Итого
        total_frame = QFrame()
        total_frame.setStyleSheet("""
            QFrame {
                background-color: #2a2b38;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        total_layout = QHBoxLayout(total_frame)
        
        total_label = QLabel("Итого:")
        total_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: white;
            }
        """)
        total_layout.addWidget(total_label)
        
        self.total_amount = QLabel("0 ₽")
        self.total_amount.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: #28a745;
            }
        """)
        total_layout.addWidget(self.total_amount)
        
        layout.addWidget(total_frame)
        
        # Кнопка оформления заказа
        self.checkout_btn = QPushButton("Оформить заказ")
        self.checkout_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #6c757d;
                cursor: not-allowed;
            }
        """)
        self.checkout_btn.clicked.connect(self.process_order)
        layout.addWidget(self.checkout_btn)
        
        self.setLayout(layout)

        self.clear_button = clear_btn
        self.clear_button.clicked.connect(self.clear_cart)

    def update_cart(self, items):
        self.cart_items = items
        while self.items_layout.count():
            item = self.items_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        for item in items:
            self.items_layout.addWidget(
                CartItemWidget(item, self.increase_quantity, self.decrease_quantity, self.set_quantity_for_item)
            )
        self.update_total()
        # Обновляем состояние кнопки оформления заказа
        self.checkout_btn.setEnabled(len(items) > 0)

    def process_order(self):
        """Обработка оформления заказа"""
        if not self.cart_items:
            return
        try:
            # Проверяем наличие всех товаров и их количество
            for item in self.cart_items:
                product = self.db.get_product_by_name(item["name"])
                if not product:
                    QMessageBox.warning(self, "Ошибка", f"Товар '{item['name']}' не найден в базе данных")
                    return
                if int(product["quantity"]) < item["quantity"]:
                    QMessageBox.warning(self, "Ошибка", 
                        f"Недостаточно товара '{item['name']}'. Доступно: {product['quantity']}, запрошено: {item['quantity']}")
                    return

            try:
                # Записываем продажу и уменьшаем количество для каждого товара через add_sale
                sale_date = datetime.datetime.now().strftime("%Y-%m-%d")
                for item in self.cart_items:
                    product = self.db.get_product_by_name(item["name"])
                    self.db.add_sale(product["id"], item["quantity"], sale_date, self.username, float(item["price"]))
                self.db.connection.commit()
                # Очищаем корзину
                self.clear_cart()
                # Вызываем обновление каталога
                if self.on_order_success:
                    self.on_order_success()
                # --- Новое: обновляем историю продаж, если она есть ---
                if self.sales_history_page:
                    self.sales_history_page.load_history()
                QMessageBox.information(self, "Успех", "Заказ успешно оформлен!")
            except Exception as e:
                self.db.connection.rollback()
                raise e
        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Не удалось оформить заказ: {str(e)}")

    def increase_quantity(self, item):
        item['quantity'] += 1
        self.update_cart(self.cart_items)
        if self.on_cart_changed:
            self.on_cart_changed()

    def decrease_quantity(self, item):
        item['quantity'] -= 1
        if item['quantity'] <= 0:
            self.cart_items.remove(item)
        self.update_cart(self.cart_items)
        if self.on_cart_changed:
            self.on_cart_changed()

    def set_quantity_for_item(self, item, value):
        item['quantity'] = value
        self.update_cart(self.cart_items)
        if self.on_cart_changed:
            self.on_cart_changed()

    def update_total(self):
        total = sum(float(item['price']) * item['quantity'] for item in self.cart_items)
        self.total_amount.setText(f"{total:.2f} ₽")

    def clear_cart(self):
        self.cart_items.clear()
        while self.items_layout.count():
            item = self.items_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self.update_total()
        if self.on_cart_changed:
            self.on_cart_changed()
