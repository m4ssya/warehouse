from PyQt5.QtWidgets import (QFrame, QListWidget, QLabel, 
                            QVBoxLayout, QSizePolicy, QHBoxLayout, QPushButton, QWidget, QScrollArea)
from PyQt5.QtCore import (QRect, QPropertyAnimation, 
                         QEasingCurve, Qt, pyqtSignal, QPoint, QTimer)
from PyQt5.QtGui import QPainter, QPainterPath, QPixmap
from PyQt5.QtCore import pyqtSignal
from app_code.animations import SlideAnimation, HoverAnimation

class SlideMenu(QFrame):
    logout_requested = pyqtSignal()
    def __init__(self, parent=None, role="пользователь"):
        super().__init__(parent)
        self.role = role
        self.setup_ui()
        self.setup_animations()
        self.hidden = True
        self.setGeometry(-260, 0, 260, parent.height() if parent else 0)
        self.setVisible(True)
        self.leave_timer = QTimer(self)
        self.leave_timer.setSingleShot(True)
        self.leave_timer.timeout.connect(self._request_hide_menu)

    def setup_ui(self):
        self.setFixedWidth(260)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Expanding)
        self.setStyleSheet("""
            QFrame {
                background-color: #1e1f24;
                border: none;
            }
            QListWidget {
                background-color: transparent;
                border: none;
                font-size: 14px;
                padding: 4px 0;
            }
            QListWidget:focus {
                outline: none;
                border: none;
            }
            QListWidget::item {
                padding: 4px 10px;
                border-radius: 4px;
                margin: 1px 6px;
                color: white;
                min-height: 24px;
            }
            QListWidget::item:selected {
                background-color: #007bff;
                color: white;
            }
            QListWidget::item:hover {
                background-color: #3c3f56;
            }
        """)
        # Скролл-область теперь только если реально не хватает места
        self.list_widget = QListWidget()
        self.list_widget.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setup_menu()
        layout = QVBoxLayout(self)
        layout.addWidget(self.list_widget)
        # Кнопка выхода
        self.logout_btn = QPushButton("Выйти")
        self.logout_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 0;
                font-size: 15px;
                margin: 18px 16px 18px 16px;
            }
            QPushButton:hover {
                background-color: #bd2130;
            }
        """)
        self.logout_btn.clicked.connect(self.logout_requested.emit)
        layout.addWidget(self.logout_btn)
        layout.setContentsMargins(0, 0, 0, 0)

    def setup_animations(self):
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.OutQuad)

    def toggle(self):
        if self.hidden:
            self.show_menu()
        else:
            self.hide_menu()

    def show_menu(self):
        self.raise_()
        self.animation.stop()
        parent = self.parent()
        if parent:
            self.animation.setStartValue(self.geometry())
            self.animation.setEndValue(QRect(0, 0, self.width(), parent.height()))
        self.animation.start()
        self.hidden = False

    def hide_menu(self):
        self.animation.stop()
        self.animation.setStartValue(self.geometry())
        self.animation.setEndValue(QRect(-self.width(), 0, self.width(), self.height()))
        self.animation.start()
        self.hidden = True

    def enterEvent(self, event):
        self.leave_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.leave_timer.start(200)
        super().leaveEvent(event)

    def _request_hide_menu(self):
        if self.parent() and hasattr(self.parent(), "hide_menu"):
            self.parent().hide_menu()
        else:
            self.hide_menu()

    def setup_menu(self):
        # Добавляем пункты меню
        if self.role == "пользователь":
            menu_items = ["Каталог товаров", "История продаж", "Личный кабинет"]
        else:
            menu_items = ["Складской учет", "Управление пользователями", "Аналитика", "Минимальные количества", "История продаж"]
        self.list_widget.clear()
        for item in menu_items:
            self.list_widget.addItem(item)

class HoverFrame(QFrame):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hover_anim = HoverAnimation(self)
        self.original_geometry = None
        self.setStyleSheet("""
            QFrame {
                background-color: #3c3f56;
                border-radius: 12px;
            }
        """)

    def enterEvent(self, event):
        self.hover_anim.setup_animation(enlarge=True)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.hover_anim.setup_animation(enlarge=False)
        super().leaveEvent(event)

    def set_rounded_pixmap(self, pixmap, radius=8):
        if pixmap and not pixmap.isNull():
            rounded = QPixmap(pixmap.size())
            rounded.fill(Qt.transparent)
            
            painter = QPainter(rounded)
            painter.setRenderHint(QPainter.Antialiasing)
            
            path = QPainterPath()
            path.addRoundedRect(0, 0, pixmap.width(), pixmap.height(), radius, radius)
            
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, pixmap)
            painter.end()
            
            return rounded
        return None


class ProductCard(HoverFrame):
    # Сигналы для редактирования, удаления и добавления в корзину
    edit_requested = pyqtSignal(object)
    delete_requested = pyqtSignal(object)
    add_to_cart_requested = pyqtSignal(object)

    def __init__(self, product, role, parent=None):
        super().__init__(parent)
        self.product = product
        self.role = role
        self.setup_ui()
        
    def setup_ui(self):
        self.setMinimumWidth(270)
        self.setMaximumWidth(270)
        self.setFixedHeight(400)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Image Container
        self.setup_image_container(layout)
        
        # Product Info
        self.setup_product_info(layout)
        
        # Добавляем кнопки в зависимости от роли
        if self.role == "администратор":
            self.setup_admin_buttons()
        elif self.role == "пользователь":
            self.setup_user_button()
    
    def setup_image_container(self, layout):
        image_frame = QFrame()
        image_frame.setFixedHeight(150)
        # По умолчанию фон прозрачный, если есть изображение, иначе — #454862
        has_image = False
        if self.product["image"]:
            pixmap = QPixmap(self.product["image"])
            if not pixmap.isNull():
                has_image = True
        if has_image:
            image_frame.setStyleSheet("""
                QFrame {
                    background-color: transparent;
                    border-radius: 8px;
                }
            """)
        else:
            image_frame.setStyleSheet("""
                QFrame {
                    background-color: #454862;
                    border-radius: 8px;
                }
            """)

        image_layout = QVBoxLayout(image_frame)
        image_layout.setContentsMargins(0, 0, 0, 0)
        image_layout.setSpacing(0)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        if has_image:
            scaled_pixmap = pixmap.scaled(
                200, 130,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            rounded = self.set_rounded_pixmap(scaled_pixmap, 8)
            self.image_label.setPixmap(rounded)
        else:
            self.set_no_image_label()

        image_layout.addWidget(self.image_label)
        layout.addWidget(image_frame)

    def set_no_image_label(self):
        self.image_label.setText("Нет изображения")
        self.image_label.setStyleSheet("""
            QLabel {
                color: #888;
                font-size: 14px;
                background-color: transparent;
            }
        """)

    def setup_product_info(self, layout):
        name_label = QLabel(self.product["name"])
        name_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: bold;
                color: white;
                margin-bottom: 5px;
            }
        """)
        name_label.setWordWrap(True)
        layout.addWidget(name_label)
        
        category_label = QLabel(self.product["category"])
        category_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                color: #aaa;
                background-color: #454862;
                border-radius: 4px;
                padding: 2px 8px;
                margin-bottom: 8px;
            }
        """)
        category_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(category_label)
        
        details_frame = QFrame()
        details_layout = QVBoxLayout(details_frame)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setSpacing(2)
        # Закупочная цена
        if self.product.get('purchase_price'):
            purchase_label = QLabel(f"Закупочная: {self.product['purchase_price']} ₽")
            purchase_label.setStyleSheet("color: #aaa; font-size: 14px;")
            details_layout.addWidget(purchase_label)
        # Всегда приоритетно показываем retail_price, если есть
        if self.product.get('retail_price'):
            retail_label = QLabel(f"Розничная: {self.product['retail_price']} ₽")
            retail_label.setStyleSheet("color: #28a745; font-size: 16px; font-weight: bold;")
            details_layout.addWidget(retail_label)
        elif self.product.get('price'):
            price_label = QLabel(f"{self.product['price']} ₽")
            price_label.setStyleSheet("color: #28a745; font-size: 16px; font-weight: bold;")
            details_layout.addWidget(price_label)
        # Количество
        quantity_label = QLabel(f"{self.product['quantity']} шт.")
        quantity_label.setStyleSheet("font-size: 14px; color: #6c757d;")
        details_layout.addWidget(quantity_label)
        layout.addWidget(details_frame)
    
    def setup_admin_buttons(self):
        # Создаем контейнер для кнопок
        buttons_frame = QWidget(self)
        buttons_frame.setStyleSheet("background: transparent;")
        buttons_layout = QHBoxLayout(buttons_frame)
        buttons_layout.setContentsMargins(0, 0, 0, 0)
        buttons_layout.setSpacing(4)
        buttons_layout.addStretch()  # Сдвигает кнопки вправо

        edit_btn = QPushButton("✎")
        edit_btn.setFixedSize(24, 24)
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                font-size: 12px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #0069d9;
            }
        """)
        edit_btn.clicked.connect(self.on_edit_clicked)
        buttons_layout.addWidget(edit_btn)

        delete_btn = QPushButton("×")
        delete_btn.setFixedSize(24, 24)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                font-size: 12px;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #bd2130;
            }
        """)
        delete_btn.clicked.connect(self.on_delete_clicked)
        buttons_layout.addWidget(delete_btn)

        # Добавляем контейнер с кнопками в основной layout карточки (в самый верх)
        self.layout().insertWidget(0, buttons_frame, alignment=Qt.AlignRight | Qt.AlignTop)
    
    def setup_user_button(self):
        # Кнопка 'Добавить в корзину'
        add_btn = QPushButton("Добавить в корзину")
        add_btn.setFixedHeight(32)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #17a2b8;
                color: white;
                font-size: 14px;
                border: none;
                border-radius: 6px;
            }
            QPushButton:hover {
                background-color: #138496;
            }
        """)
        add_btn.clicked.connect(self.on_add_to_cart_clicked)
        add_btn.installEventFilter(self)
        self.layout().addWidget(add_btn)
        self._user_add_btn = add_btn
        # Кнопка 'Подробнее'
        details_btn = QPushButton("Подробнее")
        details_btn.setFixedHeight(32)
        details_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                font-size: 14px;
                border: none;
                border-radius: 6px;
                margin-top: 6px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        details_btn.clicked.connect(self.show_readonly_dialog)
        self.layout().addWidget(details_btn)
        self._user_details_btn = details_btn
    
    def on_edit_clicked(self):
        self.edit_requested.emit(self.product)

    def on_delete_clicked(self):
        self.delete_requested.emit(self.product)

    def on_add_to_cart_clicked(self):
        self.add_to_cart_requested.emit(self.product)

    def show_readonly_dialog(self):
        print('Открытие окна просмотра товара:', self.product)
        from app_code.dialogs import EditItemDialog
        dialog = EditItemDialog(self.parent() or self, product=self.product, categories=[self.product["category"]])
        if self.role == "пользователь":
            # Делаем все поля только для чтения
            dialog.name_input.setReadOnly(True)
            dialog.price_input.setReadOnly(True)
            dialog.quantity_input.setReadOnly(True)
            dialog.category_combo.setEnabled(False)
            if hasattr(dialog, 'barcode_input'):
                dialog.barcode_input.setReadOnly(True)
            if hasattr(dialog, 'image_preview'):
                dialog.image_preview.setEnabled(False)
            # Скрываем кнопку "Добавить"
            if hasattr(dialog, 'add_button'):
                dialog.add_button.hide()
            # Переименовываем кнопку "Отмена" в "Закрыть"
            if hasattr(dialog, 'cancel_button'):
                dialog.cancel_button.setText("Закрыть")
                dialog.cancel_button.setEnabled(True)
        print('Перед exec_()')
        dialog.exec_()
        print('После exec_()')

    def eventFilter(self, obj, event):
        # Не открывать просмотр при клике по кнопке
        if self.role == "пользователь" and hasattr(self, '_user_add_btn') and obj == self._user_add_btn:
            if event.type() == event.MouseButtonPress:
                return False  # кнопка работает как обычно
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if self.role == "пользователь":
            # Отключаем открытие по клику на карточку, только по кнопке 'Подробнее'
            return super().mousePressEvent(event)
        else:
            super().mousePressEvent(event)

class CartDrawer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.hidden = True
        self.setup_ui()
        self.setup_animations()
        self.leave_timer = QTimer(self)
        self.leave_timer.setSingleShot(True)
        self.leave_timer.timeout.connect(self._request_hide_drawer)

    def setup_animations(self):
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.OutQuad)

    def show_drawer(self):
        self.hidden = False
        self.animation.stop()
        self.animation.setStartValue(self.pos())
        self.animation.setEndValue(QPoint(self.parent.width() - 340, 0))
        self.animation.start()
        self.setVisible(True)

    def hide_drawer(self):
        self.hidden = True
        self.animation.stop()
        self.animation.setStartValue(self.pos())
        self.animation.setEndValue(QPoint(self.parent.width(), 0))
        self.animation.start()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self.hidden:
            self.setGeometry(self.parent.width() - 340, 0, 340, self.parent.height())
        else:
            self.setGeometry(self.parent.width(), 0, 340, self.parent.height())

    def setup_ui(self):
        self.setFixedWidth(340)
        self.setStyleSheet("""
            QWidget {
                background-color: #1e1f24;
                border-top-left-radius: 18px;
                border-bottom-left-radius: 18px;
            }
        """)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.setVisible(False)

    def set_content(self, widget):
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.layout.addWidget(widget)

    def enterEvent(self, event):
        self.leave_timer.stop()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.leave_timer.start(200)
        super().leaveEvent(event)

    def _request_hide_drawer(self):
        if self.parent and hasattr(self.parent, "hide_cart"):
            self.parent.hide_cart()
        else:
            self.hide_drawer()
