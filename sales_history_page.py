from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout, QScrollArea, QPushButton, QMessageBox, QComboBox, QLineEdit
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon

class SalesHistoryPage(QWidget):
    def __init__(self, db, username, parent=None, is_admin=False):
        super().__init__(parent)
        self.db = db
        self.username = username
        self.is_admin = is_admin
        self.selected_seller = None
        self.init_ui()
        self.load_history()

    def init_ui(self):
        self.setStyleSheet("background-color: #23242a;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(18)

        # Верхняя панель с заголовком, сортировкой, выбором продавца и кнопкой очистки
        top_panel = QHBoxLayout()
        # Центрированный заголовок
        self.title = QLabel("История продаж")
        self.title.setFont(QFont("Arial", 20, QFont.Bold))
        self.title.setStyleSheet("color: #fff; margin-bottom: 10px; border: none;")
        self.title.setAlignment(Qt.AlignCenter)
        top_panel.addStretch()
        top_panel.addWidget(self.title)
        top_panel.addStretch()

        # --- Новый блок: Поле поиска товара ---
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск товара...")
        self.search_input.setStyleSheet('''
            QLineEdit {
                background: #353a5c;
                color: #fff;
                border: none;
                border-radius: 14px;
                padding: 12px 24px;
                font-size: 16px;
                min-width: 200px;
                box-shadow: 0 2px 8px 0 rgba(31,38,135,0.10);
                margin-right: 18px;
            }
            QLineEdit:focus {
                background: #50547a;
                border: 1.5px solid #43e97b;
            }
        ''')
        self.search_input.textChanged.connect(self.load_history) # Привязываем загрузку при изменении текста
        top_panel.addWidget(self.search_input)
        # --- Конец блока Поиск ---

        # --- Новый блок: выпадающий список продавцов для админа ---
        if self.is_admin:
            self.seller_combo = QComboBox()
            self.seller_combo.setStyleSheet('''
                QComboBox {
                    background: #353a5c;
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
                QComboBox::down-arrow {
                    image: url(:/icons/arrow-down.svg);
                    width: 18px;
                    height: 18px;
                }
            ''')
            self.seller_combo.setPlaceholderText("Продавец...")
            self.seller_combo.addItem("Все продавцы", None)
            # Получаем всех пользователей
            users = self.db.get_all_users()
            for user in users:
                if user.get('role') in ('user', 'пользователь'):
                    display_name = user.get('name') or user.get('username')
                    self.seller_combo.addItem(display_name, user.get('username'))
            self.seller_combo.currentIndexChanged.connect(self.on_seller_changed)
            top_panel.addWidget(self.seller_combo)
            self.selected_seller = None

        # Сортировка по периоду
        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["По дням", "По неделям", "По месяцам"])
        self.sort_combo.setEditable(False)
        self.sort_combo.setStyleSheet('''
            QComboBox {
                background: #353a5c;
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
            QComboBox::down-arrow {
                image: url(:/icons/arrow-down.svg);
                width: 18px;
                height: 18px;
            }
        ''')
        self.sort_combo.setPlaceholderText("Сортировка...")
        self.sort_combo.currentIndexChanged.connect(self.load_history)
        top_panel.addWidget(self.sort_combo)

        # Кнопка очистки (только для админа)
        if self.is_admin:
            clear_btn = QPushButton("Очистить историю")
            clear_btn.setStyleSheet('''
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 8px 18px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #bd2130;
                }
            ''')
            clear_btn.clicked.connect(self.clear_history)
            top_panel.addWidget(clear_btn)

        layout.addLayout(top_panel)

        # Область прокрутки
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")
        self.container = QWidget()
        self.vbox = QVBoxLayout(self.container)
        self.vbox.setSpacing(12)
        self.vbox.setAlignment(Qt.AlignTop)
        scroll.setWidget(self.container)
        layout.addWidget(scroll)

        self.setLayout(layout)

    def on_seller_changed(self):
        if self.is_admin:
            idx = self.seller_combo.currentIndex()
            self.selected_seller = self.seller_combo.itemData(idx)
            self.load_history()

    def load_history(self):
        # Очищаем старые виджеты
        while self.vbox.count():
            item = self.vbox.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        # Определяем тип сортировки
        period = self.sort_combo.currentText() if hasattr(self, 'sort_combo') else "По дням"
        # --- Новый блок: фильтрация по продавцу для админа ---
        username = self.username
        if self.is_admin:
            username = self.selected_seller
        # --- Новый блок: Получаем текст из поля поиска ---
        search_term = self.search_input.text().strip() if hasattr(self, 'search_input') else ""

        if period == "По дням":
            if self.is_admin and username is None:
                # Все продавцы
                history = self.db.get_sales_history_for_period(username=None, period="day")
            else:
                history = self.db.get_sales_history_for_period(username, period="day")
        elif period == "По неделям":
            if self.is_admin and username is None:
                history = self.db.get_sales_history_for_period(username=None, period="week")
            else:
                history = self.db.get_sales_history_for_period(username, period="week")
        elif period == "По месяцам":
            if self.is_admin and username is None:
                history = self.db.get_sales_history_for_period(username=None, period="month")
            else:
                history = self.db.get_sales_history_for_period(username, period="month")
        else:
            history = self.db.get_sales_history_for_period(username, period="day")
        # --- Новый блок: Добавляем фильтрацию по названию товара ---
        if search_term:
            history = [sale for sale in history if search_term.lower() in sale.get("product_name", "").lower()]
        # --- Конец блока Фильтрация ---
        if not history:
            empty = QLabel("Пока нет продаж.")
            empty.setStyleSheet("color: #aaa; font-size: 16px; padding: 30px;")
            self.vbox.addWidget(empty)
            return
        # --- Новый блок: расчет общей суммы, количества и выручки ---
        total_qty = 0
        total_price = 0.0
        total_profit = 0.0
        products = {p['name']: p for p in self.db.get_all_products()}
        missing_purchase = set()
        for sale in history:
            qty = int(sale['quantity'])
            total_qty += qty
            price = float(sale['sale_price']) if sale.get('sale_price') else 0.0
            total_price += price * qty
            prod = products.get(sale['product_name'])
            if prod and prod.get('purchase_price') not in (None, '', 'None'):
                try:
                    purchase = float(prod['purchase_price'])
                    total_profit += (price - purchase) * qty
                except Exception:
                    missing_purchase.add(sale['product_name'])
            else:
                missing_purchase.add(sale['product_name'])
        # --- Блок с итогами ---
        summary_layout = QHBoxLayout()
        summary_lbl = QLabel(f"<b>Всего продано:</b> {total_qty} шт.   <b>На сумму:</b> {total_price:.2f} ₽")
        summary_lbl.setStyleSheet("color: #43e97b; font-size: 17px; padding: 8px 0 18px 0;")
        summary_layout.addWidget(summary_lbl)
        profit_lbl = QLabel(f"<b>Выручка:</b> {total_profit:.2f} ₽")
        profit_lbl.setStyleSheet("color: #ffc107; font-size: 17px; padding: 8px 0 18px 18px;")
        summary_layout.addWidget(profit_lbl)
        if missing_purchase:
            warn_btn = QPushButton()
            warn_btn.setIcon(QIcon.fromTheme("dialog-warning"))
            warn_btn.setStyleSheet("background: transparent; border: none; color: #ffc107; font-size: 18px;")
            warn_btn.setToolTip("Не у всех товаров указана закупочная цена")
            warn_lbl = QLabel("<span style='color:#ffc107; font-size:15px;'>! Не у всех товаров есть закупочная цена</span>")
            warn_lbl.setStyleSheet("padding-left: 4px;")
            def show_missing():
                msg = QMessageBox(self)
                msg.setWindowTitle("Товары без закупочной цены")
                msg.setIcon(QMessageBox.Warning)
                msg.setText("<b>Следующие товары не учитываются в выручке, так как у них не указана закупочная цена:</b><br><br>" + "<br>".join(sorted(missing_purchase)))
                msg.exec_()
            warn_btn.clicked.connect(show_missing)
            summary_layout.addWidget(warn_btn)
            summary_layout.addWidget(warn_lbl)
        summary_layout.addStretch()
        summary_widget = QWidget()
        summary_widget.setLayout(summary_layout)
        self.vbox.addWidget(summary_widget)
        # --- Конец блока ---
        for sale in history:
            card = QFrame()
            card.setStyleSheet('''
                QFrame {
                    background: #2a2b38;
                    border-radius: 12px;
                    padding: 16px 18px;
                    border: 1px solid #34354a;
                }
            ''')
            hbox = QHBoxLayout(card)
            hbox.setContentsMargins(0, 0, 0, 0)
            hbox.setSpacing(18)
            name = QLabel(sale.get("product_name", ""))
            name.setStyleSheet("color: #28a745; font-size: 16px; font-weight: bold;")
            hbox.addWidget(name, 2)
            qty = QLabel(f"{sale['quantity']} шт.")
            qty.setStyleSheet("color: #fff; font-size: 15px; background: #23242a; border-radius: 6px; padding: 4px 12px;")
            hbox.addWidget(qty, 1)
            # Дата всегда в формате дд.мм.гггг
            date_val = sale.get("sale_date", "—")
            if isinstance(date_val, str):
                date_str = date_val
                if len(date_str) == 10 and date_str[4] == '-' and date_str[7] == '-':
                    from datetime import datetime
                    try:
                        date_str = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
                    except Exception:
                        pass
            elif hasattr(date_val, 'strftime'):
                date_str = date_val.strftime("%d.%m.%Y")
            else:
                date_str = str(date_val)
            date = QLabel(date_str)
            date.setStyleSheet("color: #aaa; font-size: 14px;")
            hbox.addWidget(date, 2)
            # --- Для админа: показываем имя продавца, если выбраны все продавцы ---
            if self.is_admin and self.selected_seller is None:
                seller_lbl = QLabel(sale.get("username", "—"))
                seller_lbl.setStyleSheet("color: #43e97b; font-size: 15px; font-weight: bold; padding-left: 12px;")
                hbox.addWidget(seller_lbl, 2)
            hbox.addStretch()
            self.vbox.addWidget(card)

    def clear_history(self):
        reply = QMessageBox.question(self, "Очистить историю", "Вы уверены, что хотите удалить всю историю продаж?", QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.db.cursor.execute("DELETE FROM sales_history WHERE username = %s", (self.username,))
            self.db.connection.commit()
            self.load_history() 