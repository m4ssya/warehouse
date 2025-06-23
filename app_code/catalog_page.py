from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLineEdit, 
    QComboBox, QScrollArea, QGridLayout, QLabel, QPushButton,
    QMessageBox, QSizePolicy, QCompleter
)
from PyQt5.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QPoint, QTimer, QSortFilterProxyModel, QStringListModel
from PyQt5.QtGui import QPixmap, QPainter, QPainterPath, QIcon, QColor
from app_code.dialogs import EditItemDialog 
from app_code.widgets import HoverFrame, ProductCard
from app_code.dialogs import AddItemDialog, AddCategoryDialog, DeleteCategoryDialog
from app_code.database import DatabaseManager
from PyQt5.QtWidgets import QDialog
from app_code.cart_page import CartPage

class StockPage(QWidget):
    def __init__(self, db, role, username, parent=None):
        super().__init__(parent)
        self.db = db
        self.role = role
        self.username = username
        self.products = []
        self.filtered_products = []
        self.categories = []
        self.cart_items = []
        self.current_page = 1
        self.products_per_page = 18
        self.total_pages = 1
        self.pagination_buttons = []
        
        self.init_ui()
        self.load_data()
        self.setup_connections()
        self.update_cart()  # Гарантируем корректное состояние кнопки корзины при запуске
        
        # Добавляем таймер для автоматического обновления
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.load_data)
        self.refresh_timer.start(5000)  # Обновление каждые 5 секунд
        
    def __del__(self):
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
        
    def init_ui(self):
        """Инициализация пользовательского интерфейса"""
        self.setStyleSheet("background-color: #2a2b38;")
        
        # Основной layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Панель фильтров и управления
        self.setup_filter_panel(layout)
        
        # Область отображения товаров
        self.setup_products_area(layout)
        
        # Инициализация корзины
        if self.role == "пользователь":
            self.cart_page = CartPage(on_cart_changed=self.update_cart, db=self.db, on_order_success=self.load_data, username=self.username)
            self.cart_initialized = False
        
    def setup_filter_panel(self, layout):
        """Настройка панели фильтров и управления"""
        filter_frame = QFrame()
        filter_frame.setStyleSheet("""
            QFrame {
                background-color: #3c3f56;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(10, 0, 10, 0)
        filter_layout.setSpacing(10)
        
        # Поле поиска
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск по названию...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #3c3f56;
                border: none;
                border-radius: 6px;
                padding: 10px 16px;
                color: white;
                font-size: 15px;
                min-width: 260px;
            }
        """)
        filter_layout.addWidget(self.search_input)
        
        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setStyleSheet("color: #555;")
        filter_layout.addWidget(separator)
        
        # Сортировка
        sort_label = QLabel("Сортировка:")
        sort_label.setStyleSheet("color: #ccc; font-size: 14px; margin-left: 12px;")
        filter_layout.addWidget(sort_label)
        
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["По имени", "По цене", "По количеству"])
        self.sort_combo.setStyleSheet("""
            QComboBox {
                background-color: #454862;
                color: #fff;
                border: none;
                border-radius: 14px;
                padding: 12px 24px;
                font-size: 16px;
                min-width: 170px;
                box-shadow: 0 2px 8px 0 rgba(31,38,135,0.10);
                margin-right: 18px;
            }
            QComboBox:focus {
                background: #50547a;
                border: 1.5px solid #43e97b;
            }
            QComboBox QAbstractItemView {
                background: #23243a;
                color: #fff;
                border-radius: 14px;
                selection-background-color: #38f9d7;
                font-size: 15px;
            }
            QComboBox::drop-down {
                border: none;
                background: transparent;
            }
        """)
        filter_layout.addWidget(self.sort_combo)
        
        # Категории: поле поиска и выпадающий список
        category_label = QLabel("Категория:")
        category_label.setStyleSheet("color: #ccc; font-size: 14px; margin-left: 12px;")
        filter_layout.addWidget(category_label)
        # Выпадающий список категорий
        self.category_combo = QComboBox()
        self.category_combo.setEditable(False)
        self.category_combo.setStyleSheet("""
            QComboBox {
                background-color: #454862;
                color: #fff;
                border: none;
                border-radius: 14px;
                padding: 12px 24px;
                font-size: 16px;
                min-width: 170px;
                box-shadow: 0 2px 8px 0 rgba(31,38,135,0.10);
                margin-right: 18px;
            }
            QComboBox:focus {
                background: #50547a;
                border: 1.5px solid #43e97b;
            }
            QComboBox QAbstractItemView {
                background: #23243a;
                color: #fff;
                border-radius: 14px;
                selection-background-color: #38f9d7;
                font-size: 15px;
            }
            QComboBox::drop-down {
                border: none;
                background: transparent;
            }
        """)
        filter_layout.addWidget(self.category_combo)
        self.category_combo.currentIndexChanged.connect(self.apply_filters)
        
        filter_layout.addStretch()
        # Кнопки управления (для администратора)
        if self.role == "администратор":
            # Кнопка добавления товара
            self.add_product_btn = QPushButton("Добавить товар")
            self.add_product_btn.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    padding: 10px 18px;
                    border: none;
                    border-radius: 8px;
                    font-size: 14px;
                    margin-left: 8px;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
            """)
            filter_layout.addWidget(self.add_product_btn, alignment=Qt.AlignRight)

            # Кнопка добавления по штрихкоду для склада
            self.add_by_barcode_btn = QPushButton("Добавить по штрихкоду")
            self.add_by_barcode_btn.setStyleSheet("""
                QPushButton {
                    background-color: #17a2b8;
                    color: white;
                    padding: 10px 18px;
                    border: none;
                    border-radius: 8px;
                    font-size: 14px;
                    margin-left: 8px;
                }
                QPushButton:hover {
                    background-color: #138496;
                }
            """)
            filter_layout.addWidget(self.add_by_barcode_btn, alignment=Qt.AlignRight)

            # Кнопка добавления категории
            self.add_category_btn = QPushButton("Добавить категорию")
            self.add_category_btn.setStyleSheet("""
                QPushButton {
                    background-color: #6f42c1;
                    color: white;
                    padding: 10px 18px;
                    border: none;
                    border-radius: 8px;
                    font-size: 14px;
                    margin-left: 8px;
                }
                QPushButton:hover {
                    background-color: #5a32a3;
                }
            """)
            filter_layout.addWidget(self.add_category_btn, alignment=Qt.AlignRight)
            
            # Кнопка удаления категории
            self.delete_category_btn = QPushButton("Удалить категорию")
            self.delete_category_btn.setStyleSheet("""
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    padding: 10px 18px;
                    border: none;
                    border-radius: 8px;
                    font-size: 14px;
                    margin-left: 8px;
                }
                QPushButton:hover {
                    background-color: #bd2130;
                }
            """)
            filter_layout.addWidget(self.delete_category_btn, alignment=Qt.AlignRight)
        elif self.role == "пользователь":
            self.cart_btn = QPushButton()
            self.cart_btn.setText("Корзина")
            self.cart_btn.setIcon(QIcon.fromTheme("shopping-cart"))
            self.cart_btn.setStyleSheet("""
                QPushButton {
                    background-color: #007bff;
                    color: white;
                    padding: 10px 22px;
                    border: none;
                    border-radius: 6px;
                    font-size: 15px;
                    margin-left: 8px;
                    font-weight: 500;
                }
                QPushButton:hover {
                    background-color: #0056b3;
                }
            """)
            self.cart_btn.clicked.connect(self.toggle_cart)
            filter_layout.addWidget(self.cart_btn, alignment=Qt.AlignRight)
            # --- Новое: кнопка добавления по штрихкоду для пользователя ---
            self.add_by_barcode_btn = QPushButton("Добавить по штрихкоду")
            self.add_by_barcode_btn.setStyleSheet("""
                QPushButton {
                    background-color: #17a2b8;
                    color: white;
                    padding: 10px 18px;
                    border: none;
                    border-radius: 8px;
                    font-size: 14px;
                    margin-left: 8px;
                }
                QPushButton:hover {
                    background-color: #138496;
                }
            """)
            self.add_by_barcode_btn.clicked.connect(self.show_add_by_barcode_dialog)
            filter_layout.addWidget(self.add_by_barcode_btn, alignment=Qt.AlignRight)
        layout.addWidget(filter_frame)

        # Добавляем лейбл для общего количества товаров
        self.total_count_label = QLabel()
        self.total_count_label.setStyleSheet("color: #43e97b; font-size: 16px; margin-top: 2px;")
        layout.addWidget(self.total_count_label, alignment=Qt.AlignLeft)
    
    def setup_products_area(self, layout):
        """Настройка области отображения товаров"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background: #23242a;
                width: 12px;
                margin: 4px 0 4px 0;
                border-radius: 6px;
            }
            QScrollBar::handle:vertical {
                background: #3c3f56;
                min-height: 40px;
                border-radius: 6px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
                border: none;
                background: none;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
        """)
        
        self.scroll_widget = QWidget()
        self.products_layout = QGridLayout(self.scroll_widget)
        self.products_layout.setSpacing(20)
        self.products_layout.setAlignment(Qt.AlignTop)
        
        scroll_area.setWidget(self.scroll_widget)
        layout.addWidget(scroll_area)
        
        # Пагинация
        self.pagination_frame = QFrame()
        self.pagination_frame.setStyleSheet("background: transparent;")
        self.pagination_layout = QHBoxLayout(self.pagination_frame)
        self.pagination_layout.setContentsMargins(0, 10, 0, 0)
        self.pagination_layout.setSpacing(2)
        layout.addWidget(self.pagination_frame, alignment=Qt.AlignHCenter)
    
    def setup_connections(self):
        """Настройка сигналов и слотов"""
        self.search_input.textChanged.connect(self.apply_filters)
        self.sort_combo.currentIndexChanged.connect(self.apply_filters)
        
        if self.role == "администратор":
            self.add_product_btn.clicked.connect(self.show_add_product_dialog)
            self.add_category_btn.clicked.connect(self.show_add_category_dialog)
            self.delete_category_btn.clicked.connect(self.show_delete_category_dialog)
            if hasattr(self, 'add_by_barcode_btn'):
                self.add_by_barcode_btn.clicked.connect(self.show_add_by_barcode_dialog)
    
    def load_data(self):
        """Загрузка данных из базы"""
        # Сохраняем текущие значения фильтров
        current_search = self.search_input.text()
        current_category = self.category_combo.currentText()
        current_sort = self.sort_combo.currentText()
        
        # Загружаем новые данные
        self.products = self.db.get_all_products()
        self.categories = self.db.get_all_categories()
        self.filtered_products = self.products.copy()
        self.filtered_categories = self.categories.copy()
        
        # Восстанавливаем фильтры
        self.search_input.setText(current_search)
        self.update_category_combo()
        self.category_combo.setCurrentText(current_category)
        self.sort_combo.setCurrentText(current_sort)
        
        # Применяем сохраненные фильтры
        self.apply_filters()
    
    def apply_filters(self):
        """Применение фильтров и сортировки"""
        search_text = self.search_input.text().lower()
        selected_category = self.category_combo.currentText()
        # Фильтрация
        if search_text:
            self.filtered_products = [
                p for p in self.products 
                if search_text in p["name"].lower()
            ]
        else:
            self.filtered_products = self.products.copy()
        # Фильтрация по категории
        if selected_category and selected_category != "Все категории":
            self.filtered_products = [p for p in self.filtered_products if p["category"] == selected_category]
        # Сортировка
        sort_option = self.sort_combo.currentText()
        if sort_option == "По имени":
            self.filtered_products.sort(key=lambda x: x["name"].lower())
        elif sort_option == "По цене":
            self.filtered_products.sort(key=lambda x: float(x["price"]))
        elif sort_option == "По количеству":
            self.filtered_products.sort(key=lambda x: int(x["quantity"]))
        # По умолчанию — без сортировки
        self.update_products_grid()
        self.update_total_count_label()
    
    def update_products_grid(self):
        """Обновление сетки товаров (без анимации)"""
        # Очистка текущих виджетов
        for i in reversed(range(self.products_layout.count())):
            widget = self.products_layout.itemAt(i).widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        # Пагинация
        total_products = len(self.filtered_products)
        self.total_pages = max(1, (total_products + self.products_per_page - 1) // self.products_per_page)
        self.current_page = min(self.current_page, self.total_pages)
        start_idx = (self.current_page - 1) * self.products_per_page
        end_idx = start_idx + self.products_per_page
        page_products = self.filtered_products[start_idx:end_idx]
        # Динамический расчет ширины карточки
        columns = 6
        spacing = 20
        total_spacing = spacing * (columns - 1)
        available_width = (self.parent().width() if self.parent() else self.width()) - 40
        card_width = (available_width - total_spacing) // columns
        for i, product in enumerate(page_products):
            row = i // columns
            col = i % columns
            card = ProductCard(product, self.role)
            card.setFixedWidth(card_width)
            if self.role == "администратор":
                card.edit_requested.connect(self.edit_product)
                card.delete_requested.connect(self.delete_product)
            elif self.role == "пользователь":
                card.add_to_cart_requested.connect(self.add_to_cart)
            self.products_layout.addWidget(card, row, col)
        self.update_pagination()
    
    def show_add_product_dialog(self):
        """Показать диалог добавления товара"""
        dialog = AddItemDialog(self, self.categories)
        if dialog.exec_() == QDialog.Accepted:
            name, purchase_price, retail_price, quantity, image, category, barcode = dialog.get_item_data()
            if not name or not purchase_price or not retail_price or not quantity:
                QMessageBox.warning(self, "Ошибка", "Заполните все обязательные поля")
                return
            # Проверка уникальности имени
            if any(p["name"].lower() == name.lower() for p in self.products):
                QMessageBox.warning(self, "Ошибка", "Товар с таким названием уже существует")
                return
            # Добавление в базу
            product_data = {
                "name": name,
                "purchase_price": purchase_price,
                "retail_price": retail_price,
                "quantity": quantity,
                "image": image,
                "category": category,
                "barcode": barcode,
                # Для совместимости с устаревшим полем price:
                "price": retail_price
            }
            if self.db.add_product(product_data):
                # Получаем id только что добавленного товара по имени
                products = self.db.get_all_products()
                new_product = next((p for p in products if p["name"] == name), None)
                if new_product:
                    self.db.log_initial_product_movement(
                        product_id=new_product["id"],
                        quantity=int(quantity),
                        username=self.username,
                        comment='Первоначальное поступление товара'
                    )
                self.load_data()  # Перезагружаем данные
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось добавить товар")
    
    def edit_product(self, product):
        """Редактирование товара"""
        dialog = EditItemDialog(self, product, self.categories)
        if dialog.exec_() == QDialog.Accepted:
            updated_data = dialog.get_updated_data()
            if not updated_data["name"]:
                QMessageBox.warning(self, "Ошибка", "Название товара не может быть пустым")
                return
            # Проверка уникальности имени
            if (updated_data["name"] != product["name"] and 
                any(p["name"].lower() == updated_data["name"].lower() 
                    for p in self.products)):
                QMessageBox.warning(self, "Ошибка", "Товар с таким названием уже существует")
                return
            updated_data["price"] = updated_data.get("retail_price", updated_data.get("price", ""))
            old_quantity = int(product["quantity"])
            try:
                new_quantity = int(updated_data["quantity"])
            except Exception:
                QMessageBox.warning(self, "Ошибка", "Некорректное количество!")
                return
            if new_quantity < 0:
                QMessageBox.warning(self, "Ошибка", "Количество не может быть отрицательным!")
                return
            quantity_diff = new_quantity - old_quantity
            if self.db.update_product(product["name"], updated_data):
                if quantity_diff != 0:
                    self.db.add_product_movement(
                        product_id=product["id"],
                        movement_type='IN' if quantity_diff > 0 else 'OUT',
                        quantity=abs(quantity_diff),
                        username=self.username,
                        comment=f'Ручное изменение количества с {old_quantity} на {new_quantity}'
                    )
                self.load_data()
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось обновить товар")
    
    def delete_product(self, product):
        """Удаление товара"""
        reply = QMessageBox.question(
            self, 
            "Подтверждение", 
            f"Вы уверены, что хотите удалить товар '{product['name']}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if self.db.delete_product(product["id"]):
                self.load_data()  # Перезагружаем данные
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось удалить товар")
    
    def show_add_category_dialog(self):
        """Показать диалог добавления категории"""
        dialog = AddCategoryDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            category_name = dialog.get_category_name()
            
            if not category_name:
                QMessageBox.warning(self, "Ошибка", "Название категории не может быть пустым")
                return
                
            if category_name in self.categories:
                QMessageBox.warning(self, "Ошибка", "Категория с таким названием уже существует")
                return
                
            if self.db.add_category(category_name):
                self.load_data()  # Перезагружаем данные
                QMessageBox.information(self, "Успех", "Категория успешно добавлена")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось добавить категорию")
    
    def show_delete_category_dialog(self):
        """Показать диалог удаления категории"""
        if not self.categories:
            QMessageBox.warning(self, "Ошибка", "Нет категорий для удаления")
            return
            
        dialog = DeleteCategoryDialog(self, self.categories)
        if dialog.exec_() == QDialog.Accepted:
            category_name = dialog.get_selected_category()
            
            reply = QMessageBox.question(
                self,
                "Подтверждение",
                f"Удалить категорию '{category_name}'? Все товары будут перемещены в 'Без категории'",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                if self.db.delete_category(category_name):
                    self.load_data()  # Перезагружаем данные
                    QMessageBox.information(self, "Успех", "Категория успешно удалена")
                else:
                    QMessageBox.warning(self, "Ошибка", "Не удалось удалить категорию")
    
    def resizeEvent(self, event):
        """Обработчик изменения размера окна"""
        super().resizeEvent(event)
        self.update_products_grid()

    def setup_user_button(self):
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
        self.layout().addWidget(add_btn)

    def on_add_to_cart_clicked(self):
        product = self.product
        price = product.get('price') or product.get('retail_price')
        try:
            price = float(price)
        except (TypeError, ValueError):
            QMessageBox.warning(self, "Ошибка", "У товара не указана цена!")
            return
        for item in self.cart_items:
            if item.get('id') == product['id']:
                item['quantity'] += 1
                self.update_cart()
                return
        self.cart_items.append({
            'id': product['id'],
            'name': product['name'],
            'price': price,
            'quantity': 1
        })
        self.update_cart()
        main_window = self.parent().parent()
        if main_window and hasattr(main_window, 'cart_drawer'):
            main_window.cart_drawer.show_drawer()

    def update_cart(self):
        if hasattr(self, 'cart_page'):
            print('update_cart called, items:', self.cart_items)  # Для отладки
            self.cart_page.update_cart(self.cart_items)
            # Обновляем общую сумму
            total = sum(float(item['price']) * item['quantity'] for item in self.cart_items)
            self.cart_page.total_amount.setText(f"{total:.2f} ₽")
            # Делаем кнопку корзины неактивной и серой, если корзина пуста
            if hasattr(self, 'cart_btn'):
                if len(self.cart_items) == 0:
                    self.cart_btn.setEnabled(False)
                    self.cart_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #888;
                            color: #eee;
                            padding: 10px 22px;
                            border: none;
                            border-radius: 6px;
                            font-size: 15px;
                            margin-left: 8px;
                            font-weight: 500;
                        }
                    """)
                    # Автоматически закрывать корзину, если она открыта
                    main_window = self.window()
                    if main_window and hasattr(main_window, 'cart_drawer') and not main_window.cart_drawer.hidden:
                        main_window.hide_cart()
                else:
                    self.cart_btn.setEnabled(True)
                    self.cart_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #007bff;
                            color: white;
                            padding: 10px 22px;
                            border: none;
                            border-radius: 6px;
                            font-size: 15px;
                            margin-left: 8px;
                            font-weight: 500;
                        }
                        QPushButton:hover {
                            background-color: #0056b3;
                        }
                    """)

    def toggle_cart(self):
        main_window = self.window()
        if main_window and hasattr(main_window, 'cart_drawer'):
            if main_window.cart_drawer.hidden:
                main_window.show_cart()
            else:
                main_window.hide_cart()

    def showEvent(self, event):
        """Обработчик события показа виджета"""
        super().showEvent(event)
        # Инициализируем корзину только когда виджет уже добавлен в иерархию
        if self.role == "пользователь" and not getattr(self, 'cart_initialized', False):
            main_window = self.window()
            if main_window and hasattr(main_window, 'cart_drawer'):
                main_window.cart_drawer.set_content(self.cart_page)
                self.cart_initialized = True

    def add_to_cart(self, product):
        price = product.get('price') or product.get('retail_price')
        try:
            price = float(price)
        except (TypeError, ValueError):
            QMessageBox.warning(self, "Ошибка", "У товара не указана цена!")
            return
        for item in self.cart_items:
            if item.get('id') == product['id']:
                item['quantity'] += 1
                break
        else:
            self.cart_items.append({
                'id': product['id'],
                'name': product['name'],
                'price': price,
                'quantity': 1
            })
        print('cart_items:', self.cart_items)  # Для отладки
        self.update_cart()

    def update_pagination(self):
        # Очистка старых кнопок
        for i in reversed(range(self.pagination_layout.count())):
            item = self.pagination_layout.itemAt(i)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        # Кнопка "Назад"
        prev_btn = QPushButton("←")
        prev_btn.setFixedSize(38, 38)
        prev_btn.setStyleSheet(self.pagination_button_style(active=False))
        prev_btn.clicked.connect(self.prev_page)
        prev_btn.setEnabled(self.current_page > 1)
        self.pagination_layout.addWidget(prev_btn)
        # Кнопки с номерами страниц (максимум 5)
        max_buttons = 5
        start_page = max(1, self.current_page - 2)
        end_page = min(self.total_pages, start_page + max_buttons - 1)
        if end_page - start_page < max_buttons - 1:
            start_page = max(1, end_page - max_buttons + 1)
        for page in range(start_page, end_page + 1):
            btn = QPushButton(str(page))
            btn.setFixedSize(38, 38)
            btn.setStyleSheet(self.pagination_button_style(active=(page == self.current_page)))
            btn.clicked.connect(lambda checked, p=page: self.goto_page(p))
            self.pagination_layout.addWidget(btn)
        # Кнопка "Вперёд"
        next_btn = QPushButton("→")
        next_btn.setFixedSize(38, 38)
        next_btn.setStyleSheet(self.pagination_button_style(active=False))
        next_btn.clicked.connect(self.next_page)
        next_btn.setEnabled(self.current_page < self.total_pages)
        self.pagination_layout.addWidget(next_btn)

    def pagination_button_style(self, active=False):
        if active:
            return '''
                QPushButton {
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #43e97b, stop:1 #38f9d7);
                    color: #23243a;
                    border: none;
                    border-radius: 12px;
                    font-size: 16px;
                    font-weight: bold;
                }
            '''
        else:
            return '''
                QPushButton {
                    background: #353a5c;
                    color: #fff;
                    border: none;
                    border-radius: 12px;
                    font-size: 16px;
                }
                QPushButton:disabled {
                    background: #23243a;
                    color: #888;
                }
                QPushButton:hover {
                    background: #50547a;
                }
            '''

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.update_products_grid()

    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1
            self.update_products_grid()

    def goto_page(self, page):
        if 1 <= page <= self.total_pages:
            self.current_page = page
            self.update_products_grid()

    def update_category_combo(self):
        self.category_combo.blockSignals(True)
        self.category_combo.clear()
        self.category_combo.addItem("Все категории")
        for cat in self.filtered_categories:
            self.category_combo.addItem(cat)
        self.category_combo.blockSignals(False)

    def update_total_count_label(self):
        total = sum(int(p["quantity"]) for p in self.filtered_products)
        self.total_count_label.setText(f"Общее количество товаров: <b>{total}</b>")

    def show_add_by_barcode_dialog(self):
        """Диалог для добавления товара в корзину по штрихкоду для пользователя"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QLabel, QMessageBox
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить в корзину по штрихкоду")
        dialog.setFixedSize(340, 140)
        layout = QVBoxLayout(dialog)
        label = QLabel("Отсканируйте или введите штрихкод товара:")
        layout.addWidget(label)
        barcode_input = QLineEdit()
        barcode_input.setPlaceholderText("Штрихкод (13 цифр)")
        barcode_input.setStyleSheet("font-size: 18px; padding: 12px; border-radius: 10px;")
        layout.addWidget(barcode_input)
        qty_input = QLineEdit()
        qty_input.setPlaceholderText("Количество (по умолчанию 1)")
        qty_input.setStyleSheet("font-size: 16px; padding: 10px; border-radius: 8px;")
        layout.addWidget(qty_input)
        barcode_input.setFocus()
        busy = {"flag": False}
        def try_add():
            if busy["flag"]:
                return
            barcode = barcode_input.text().strip()
            qty = qty_input.text().strip()
            qty = int(qty) if qty.isdigit() and int(qty) > 0 else 1
            if len(barcode) != 13 or not barcode.isdigit():
                return  # Ждём 13 цифр
            busy["flag"] = True
            product = next((p for p in self.products if p.get("barcode") == barcode), None)
            if not product:
                QMessageBox.warning(dialog, "Ошибка", "Товар с таким штрихкодом не найден!")
                barcode_input.clear()
                barcode_input.setFocus()
                busy["flag"] = False
                return
            price = product.get('price') or product.get('retail_price')
            try:
                price = float(price)
            except (TypeError, ValueError):
                QMessageBox.warning(dialog, "Ошибка", "У товара не указана цена!")
                barcode_input.clear()
                barcode_input.setFocus()
                busy["flag"] = False
                return
            for item in self.cart_items:
                if item.get('id') == product['id']:
                    item['quantity'] += qty
                    break
            else:
                self.cart_items.append({
                    'id': product['id'],
                    'name': product['name'],
                    'price': price,
                    'quantity': qty
                })
            self.update_cart()
            barcode_input.clear()
            qty_input.clear()
            barcode_input.setFocus()
            busy["flag"] = False
        barcode_input.textChanged.connect(try_add)
        qty_input.returnPressed.connect(try_add)
        dialog.exec_()