import sys
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QFrame, QPushButton, QScrollArea,
    QMessageBox, QStackedWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QCalendarWidget, QDateEdit, QGridLayout
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QColor
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import numpy as np
import mplcursors
from collections import defaultdict
from matplotlib.transforms import blended_transform_factory

class AnalyticsPage(QWidget):
    def __init__(self, db, username=None, role=None):
        super().__init__()
        self.db = db
        self.username = username
        self.role = role
        self.sort_column = 0
        self.sort_order = Qt.AscendingOrder
        self.period_history = []  # Стек истории выбранных периодов
        self.init_ui()

    def init_ui(self):
        self.setStyleSheet("background-color: #2a2b38; color: white;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # --- Кнопки для переключения страниц ---
        page_btn_layout = QHBoxLayout()
        self.page1_btn = QPushButton("Страница 1")
        self.page2_btn = QPushButton("Страница 2")
        self.page3_btn = QPushButton("Страница 3")
        for btn in (self.page1_btn, self.page2_btn, self.page3_btn):
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #454862;
                    color: white;
                    border: none;
                    border-radius: 8px;
                    padding: 8px 24px;
                    font-size: 15px;
                }
                QPushButton:checked {
                    background-color: #007bff;
                }
                QPushButton:hover {
                    background-color: #50547a;
                }
            """)
            btn.setCheckable(True)
        self.page1_btn.setChecked(True)
        self.page1_btn.clicked.connect(lambda: self.switch_page(0))
        self.page2_btn.clicked.connect(lambda: self.switch_page(1))
        self.page3_btn.clicked.connect(lambda: self.switch_page(2))
        page_btn_layout.addWidget(self.page1_btn)
        page_btn_layout.addWidget(self.page2_btn)
        page_btn_layout.addWidget(self.page3_btn)
        page_btn_layout.addStretch()
        layout.addLayout(page_btn_layout)

        # --- Страницы ---
        self.stacked = QStackedWidget()
        # Страница 1 — текущая аналитика
        analytics_widget = QWidget()
        analytics_layout = QVBoxLayout(analytics_widget)
        analytics_layout.setContentsMargins(0, 0, 0, 0)
        analytics_layout.setSpacing(20)
        # --- всё, что было в layout до этого, теперь в analytics_layout ---
        # Заголовок
        title = QLabel("Аналитика продаж")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        analytics_layout.addWidget(title)
        # --- Кнопка "Назад" для возврата к исходному периоду ---
        self.back_btn = QPushButton("← Назад")
        self.back_btn.setStyleSheet("""
            QPushButton {
                background-color: #454862;
                color: #43e97b;
                border: none;
                border-radius: 8px;
                padding: 4px 18px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #50547a;
            }
        """)
        self.back_btn.clicked.connect(self.restore_full_period)
        self.back_btn.hide()
        analytics_layout.addWidget(self.back_btn, alignment=Qt.AlignLeft)
        # Панель управления
        control_panel = QFrame()
        control_panel.setStyleSheet("""
            QFrame {
                background-color: #3c3f56;
                border-radius: 10px;
                padding: 10px;
            }
        """)
        control_layout = QHBoxLayout(control_panel)

        # Добавляем выбор периода по календарю
        date_layout = QHBoxLayout()
        self.date_from = QDateEdit()
        self.date_to = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_to.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-1))
        self.date_to.setDate(QDate.currentDate())
        
        # Стилизация календарей
        calendar_style = """
            QDateEdit {
                background-color: #454862;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 5px;
                color: white;
                min-width: 120px;
            }
            QDateEdit::drop-down {
                border: none;
                width: 20px;
            }
            QDateEdit::down-arrow {
                image: url(:/icons/calendar.png);
                width: 12px;
                height: 12px;
            }
            QCalendarWidget {
                background-color: #2a2b38;
                color: white;
            }
            QCalendarWidget QToolButton {
                color: white;
                background-color: #454862;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }
            QCalendarWidget QMenu {
                background-color: #2a2b38;
                color: white;
            }
            QCalendarWidget QSpinBox {
                background-color: #454862;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px;
            }
        """
        self.date_from.setStyleSheet(calendar_style)
        self.date_to.setStyleSheet(calendar_style)
        
        date_layout.addWidget(QLabel("От:"))
        date_layout.addWidget(self.date_from)
        date_layout.addWidget(QLabel("До:"))
        date_layout.addWidget(self.date_to)
        control_layout.addLayout(date_layout)

        # Добавляем кнопку применения периода
        apply_period_btn = QPushButton("Применить период")
        apply_period_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        apply_period_btn.clicked.connect(self.load_data)
        control_layout.addWidget(apply_period_btn)

        # Добавляем кнопки быстрого выбора периода
        quick_periods_layout = QHBoxLayout()
        
        year_btn = QPushButton("За год")
        year_btn.setStyleSheet("""
            QPushButton {
                background-color: #454862;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #50547a;
            }
        """)
        year_btn.clicked.connect(self.set_year_period)
        quick_periods_layout.addWidget(year_btn)
        
        all_time_btn = QPushButton("Вся история")
        all_time_btn.setStyleSheet("""
            QPushButton {
                background-color: #454862;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #50547a;
            }
        """)
        all_time_btn.clicked.connect(self.set_all_time_period)
        quick_periods_layout.addWidget(all_time_btn)
        
        control_layout.addLayout(quick_periods_layout)

        # Добавляем разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.VLine)
        separator.setStyleSheet("background-color: #555;")
        control_layout.addWidget(separator)

        # Существующие элементы управления
        self.graph_type_combo = QComboBox()
        self.graph_type_combo.addItems(["Линейный", "Столбчатый", "Круговой"])
        self.graph_type_combo.setStyleSheet("""
            QComboBox {
                background-color: #454862;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 5px;
                color: white;
                min-width: 100px;
            }
            QComboBox:hover {
                border: 1px solid #666;
            }
        """)
        self.graph_type_combo.currentTextChanged.connect(self.update_graphs)
        control_layout.addWidget(QLabel("Тип графика:"))
        control_layout.addWidget(self.graph_type_combo)

        refresh_btn = QPushButton("Обновить")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #007bff;
                color: white;
                border: none;
                padding: 5px 15px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
        """)
        refresh_btn.clicked.connect(self.load_data)
        control_layout.addWidget(refresh_btn)

        if self.role == "администратор":
            clear_btn = QPushButton("Очистить аналитику")
            clear_btn.setStyleSheet("""
                QPushButton {
                    background-color: #dc3545;
                    color: white;
                    border: none;
                    padding: 5px 15px;
                    border-radius: 5px;
                }
                QPushButton:hover {
                    background-color: #c82333;
                }
            """)
            clear_btn.clicked.connect(self.clear_analytics)
            control_layout.addWidget(clear_btn)

        # --- Новый выпадающий список для агрегации ---
        self.aggregation_combo = QComboBox()
        self.aggregation_combo.addItems(["Общие продажи", "По продавцам"])
        self.aggregation_combo.setStyleSheet('''
            QComboBox { background-color: #454862; border: 1px solid #555; padding: 5px; border-radius: 5px; color: #43e97b; min-width: 120px; }
        ''')
        self.aggregation_combo.currentTextChanged.connect(self.update_graphs)
        control_layout.addWidget(QLabel("Агрегация:"))
        control_layout.addWidget(self.aggregation_combo)

        control_layout.addStretch()
        analytics_layout.addWidget(control_panel)
        # Область с графиками
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        self.graphs_container = QWidget()
        self.graphs_layout = QVBoxLayout(self.graphs_container)
        self.graphs_layout.setSpacing(20)
        scroll.setWidget(self.graphs_container)
        analytics_layout.addWidget(scroll)
        self.analytics_widget = analytics_widget
        self.stacked.addWidget(self.analytics_widget)
        # Страница 2 — список товаров
        self.page2 = QWidget()
        grid_layout = QGridLayout(self.page2)
        grid_layout.setSpacing(32)
        grid_layout.setContentsMargins(24, 24, 24, 24)

        card_style = '''
            QFrame {
                background: #3c3f56;
                border-radius: 18px;
                border: 2px solid #23243a;
            }
        '''

        # 1. Левый верхний — ТОП-5 товаров (горизонтальный bar chart)
        card1 = QFrame()
        card1.setStyleSheet(card_style)
        card1_layout = QVBoxLayout(card1)
        card1_layout.setContentsMargins(18, 18, 18, 18)
        card1_label = QLabel('ТОП-5 товаров')
        card1_label.setStyleSheet('font-size: 16px; font-weight: bold; color: #43e97b;')
        card1_layout.addWidget(card1_label, alignment=Qt.AlignLeft)
        self.toptov_fig = Figure(figsize=(4, 3), dpi=100)
        self.toptov_fig.patch.set_facecolor('#3c3f56')
        self.toptov_canvas = FigureCanvas(self.toptov_fig)
        card1_layout.addWidget(self.toptov_canvas)
        grid_layout.addWidget(card1, 0, 0)

        # 2. Правый верхний — ТОП дней недели по средним продажам
        card2 = QFrame()
        card2.setStyleSheet(card_style)
        card2_layout = QVBoxLayout(card2)
        card2_layout.setContentsMargins(18, 18, 18, 18)
        card2_label = QLabel('ТОП дней недели')
        card2_label.setStyleSheet('font-size: 16px; font-weight: bold; color: #43e97b;')
        card2_layout.addWidget(card2_label, alignment=Qt.AlignLeft)
        self.weekday_fig = Figure(figsize=(4, 3), dpi=100)
        self.weekday_fig.patch.set_facecolor('#3c3f56')
        self.weekday_canvas = FigureCanvas(self.weekday_fig)
        card2_layout.addWidget(self.weekday_canvas)
        grid_layout.addWidget(card2, 0, 1)

        # 3. Левый нижний — ТОП-5 категорий
        card3 = QFrame()
        card3.setStyleSheet(card_style)
        card3_layout = QVBoxLayout(card3)
        card3_layout.setContentsMargins(18, 18, 18, 18)
        card3_label = QLabel('ТОП-5 категорий')
        card3_label.setStyleSheet('font-size: 16px; font-weight: bold; color: #43e97b;')
        card3_layout.addWidget(card3_label, alignment=Qt.AlignLeft)
        self.topcat_fig = Figure(figsize=(4, 3), dpi=100)
        self.topcat_fig.patch.set_facecolor('#3c3f56')
        self.topcat_canvas = FigureCanvas(self.topcat_fig)
        card3_layout.addWidget(self.topcat_canvas)
        grid_layout.addWidget(card3, 1, 0)

        # 4. Правый нижний — товары с наибольшим ростом продаж за месяц
        card4 = QFrame()
        card4.setStyleSheet(card_style)
        card4_layout = QVBoxLayout(card4)
        card4_layout.setContentsMargins(18, 18, 18, 18)
        card4_label = QLabel('Топ-5 прироста продаж за месяц')
        card4_label.setStyleSheet('font-size: 16px; font-weight: bold; color: #43e97b;')
        card4_layout.addWidget(card4_label, alignment=Qt.AlignLeft)
        self.growth_list_widget = QWidget()
        self.growth_list_layout = QVBoxLayout(self.growth_list_widget)
        self.growth_list_layout.setContentsMargins(0, 0, 0, 0)
        self.growth_list_layout.setSpacing(8)
        card4_layout.addWidget(self.growth_list_widget)
        grid_layout.addWidget(card4, 1, 1)

        # Равномерное растяжение
        grid_layout.setRowStretch(0, 1)
        grid_layout.setRowStretch(1, 1)
        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)

        self.stacked.addWidget(self.page2)
        # Страница 3 — товары с низким остатком
        low_stock_widget = QWidget()
        low_stock_layout = QVBoxLayout(low_stock_widget)
        low_stock_layout.setContentsMargins(0, 0, 0, 0)
        low_stock_layout.setSpacing(20)

        # Заголовок
        low_stock_title = QLabel("<span style='font-size:22px; font-weight:bold; vertical-align:middle;'>⚠️ Товары с низким остатком</span>")
        low_stock_title.setStyleSheet("margin-bottom: 8px;")
        low_stock_layout.addWidget(low_stock_title)

        # Таблица товаров
        self.low_stock_table = QTableWidget()
        self.low_stock_table.setColumnCount(4)
        self.low_stock_table.setHorizontalHeaderLabels(["Товар", "Категория", "Текущее количество", "Минимальное количество"])
        self.low_stock_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.low_stock_table.setStyleSheet("""
            QTableWidget {
                background-color: #35374a;
                border: none;
                border-radius: 18px;
                color: #f5f6fa;
                font-size: 17px;
                selection-background-color: #23243a;
                selection-color: #43e97b;
                gridline-color: #444;
            }
            QTableWidget::item {
                padding: 10px;
                border-bottom: 1.5px solid #444;
            }
            QTableWidget::item:selected {
                background-color: #23243a;
                color: #43e97b;
            }
            QHeaderView::section {
                background-color: #23243a;
                color: #43e97b;
                padding: 12px;
                border: none;
                font-size: 18px;
                font-weight: bold;
                border-top-left-radius: 18px;
                border-top-right-radius: 18px;
            }
            QTableCornerButton::section {
                background: #23243a;
                border-top-left-radius: 18px;
            }
            QTableWidget::item:focus, QTableView::item:focus, QAbstractItemView::item:focus, QTableWidget:focus, QTableView:focus, QAbstractItemView:focus { outline: none; border: none; background: transparent; }
        """)
        self.low_stock_table.setAlternatingRowColors(True)
        self.low_stock_table.setStyleSheet(self.low_stock_table.styleSheet() + "QTableWidget { alternate-background-color: #2a2b38; }")
        self.low_stock_table.setShowGrid(False)
        self.low_stock_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.low_stock_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.low_stock_table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
        self.low_stock_table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
        self.low_stock_table.setFocusPolicy(Qt.NoFocus)
        self.low_stock_table.setFrameStyle(QTableWidget.NoFrame)
        self.low_stock_table.verticalHeader().setVisible(True)
        self.low_stock_table.verticalHeader().setStyleSheet("""
            QHeaderView::section {
                background-color: #23243a;
                color: #43e97b;
                font-size: 16px;
                font-weight: bold;
                border: none;
                border-radius: 12px;
                padding: 8px 0;
                min-width: 36px;
                max-width: 48px;
                qproperty-alignment: 'AlignCenter';
            }
        """)
        self.low_stock_table.verticalHeader().setDefaultSectionSize(36)
        self.low_stock_table.verticalHeader().setMinimumSectionSize(28)
        low_stock_layout.addWidget(self.low_stock_table)

        # Кнопка обновления
        refresh_btn = QPushButton("⟳ Обновить")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #43e97b;
                color: #23243a;
                border: none;
                border-radius: 10px;
                padding: 10px 32px;
                font-size: 17px;
                font-weight: bold;
                box-shadow: 0 2px 8px rgba(67,233,123,0.12);
                transition: background 0.2s, color 0.2s, box-shadow 0.2s;
            }
            QPushButton:hover {
                background-color: #2fd97b;
                color: #fff;
                box-shadow: 0 4px 16px rgba(67,233,123,0.22);
            }
        """)
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.clicked.connect(self.update_low_stock_table)
        low_stock_layout.addWidget(refresh_btn, alignment=Qt.AlignRight)

        # Добавляем все страницы в стек
        self.stacked.addWidget(self.analytics_widget)  # Страница 1
        self.stacked.addWidget(self.page2)             # Страница 2
        self.stacked.addWidget(low_stock_widget)       # Страница 3

        layout.addWidget(self.stacked)
        self.update_weekday_bar_chart()
        self.update_topcat_bar_chart()
        self.update_growth_list()
        self.update_low_stock_table()
        self.update_toptov_bar_chart()

    def switch_page(self, idx):
        self.stacked.setCurrentIndex(idx)
        self.page1_btn.setChecked(idx == 0)
        self.page2_btn.setChecked(idx == 1)
        self.page3_btn.setChecked(idx == 2)
        if idx == 1:
            self.update_weekday_bar_chart()
            self.update_topcat_bar_chart()
            self.update_growth_list()

    def update_graphs(self):
        """Обновляет графики при изменении параметров"""
        self.load_data()

    def load_data(self):
        # Сохраняем историю выбранных периодов
        date_from = self.date_from.date().toString("yyyy-MM-dd")
        date_to = self.date_to.date().toString("yyyy-MM-dd")
        if not hasattr(self, '_full_period') or self._full_period is None:
            self._full_period = (date_from, date_to)
        # Добавляем в историю, если это новый шаг
        if not self.period_history or self.period_history[-1] != (date_from, date_to):
            self.period_history.append((date_from, date_to))
        # Очищаем старые графики
        while self.graphs_layout.count():
            item = self.graphs_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        graph_type = self.graph_type_combo.currentText()
        # Получаем данные о продажах
        username_for_filter = self.username if self.role in ("user", "пользователь") else None
        sales_data = self.db.get_sales_data_for_period(
            date_from, 
            date_to,
            None,
            username_for_filter
        )
        
        if sales_data:
            self.create_graph(sales_data, graph_type)
        else:
            # Показываем сообщение, если данных нет
            no_data_label = QLabel("Нет данных для отображения")
            no_data_label.setStyleSheet("""
                QLabel {
                    color: #aaa;
                    font-size: 16px;
                    padding: 20px;
                }
            """)
            no_data_label.setAlignment(Qt.AlignCenter)
            self.graphs_layout.addWidget(no_data_label)

        # Показываем или скрываем кнопку "Назад"
        if len(self.period_history) > 1:
            self.back_btn.show()
        else:
            self.back_btn.hide()

    def create_graph(self, sales_data, graph_type):
        # Создаем фрейм для графика
        graph_frame = QFrame()
        graph_frame.setStyleSheet("""
            QFrame {
                background-color: #3c3f56;
                border-radius: 10px;
                padding: 15px;
            }
        """)
        graph_layout = QVBoxLayout(graph_frame)

        # Заголовок графика
        title = QLabel("Аналитика продаж")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        graph_layout.addWidget(title)

        # Создаем график
        fig = Figure(figsize=(18, 6), dpi=100)  # Увеличиваем ширину графика
        fig.patch.set_facecolor('#3c3f56')
        canvas = FigureCanvas(fig)
        if graph_type == "Круговой":
            ax = fig.add_axes([0, 0, 1, 1], frameon=False)
        else:
            ax = fig.add_subplot(111)
            ax.set_facecolor('#3c3f56')
        
        # Подготовка данных
        dates = [item[0] for item in sales_data]
        total_sales = [item[1] for item in sales_data]
        total_amount = [float(item[2]) if item[2] else 0 for item in sales_data]
        total_quantity = [item[3] for item in sales_data]

        # --- Новый блок: если выбрана агрегация по продавцам ---
        aggregation_mode = self.aggregation_combo.currentText() if hasattr(self, 'aggregation_combo') else "Общие продажи"
        if aggregation_mode == "По продавцам" and graph_type == "Линейный":
            users = [u for u in self.db.get_all_users() if u.get('role') in ('user', 'пользователь')]
            usernames = [u['username'] for u in users]
            username_to_name = {u['username']: (u['name'] if u.get('name') else u['username']) for u in users}
            date_from = self.date_from.date().toString("yyyy-MM-dd")
            date_to = self.date_to.date().toString("yyyy-MM-dd")
            from datetime import datetime, timedelta
            date_from_dt = datetime.strptime(date_from, "%Y-%m-%d")
            date_to_dt = datetime.strptime(date_to, "%Y-%m-%d")
            all_dates = [(date_from_dt + timedelta(days=i)).strftime("%Y-%m-%d") for i in range((date_to_dt-date_from_dt).days+1)]
            import matplotlib.cm as cm
            import matplotlib.colors as mcolors
            color_map = cm.get_cmap('tab10', len(usernames))
            for idx, username in enumerate(usernames):
                user_sales_data = self.db.get_sales_data_for_period(date_from, date_to, None, username)
                user_dates = [item[0] for item in user_sales_data]
                user_qty = [item[3] for item in user_sales_data]
                user_dates_fmt = []
                for d in user_dates:
                    if '.' in d:
                        try:
                            dt_obj = datetime.strptime(d, "%d.%m.%Y")
                            user_dates_fmt.append(dt_obj.strftime("%Y-%m-%d"))
                        except Exception:
                            user_dates_fmt.append(d)
                    else:
                        user_dates_fmt.append(d)
                user_sales_by_date = dict(zip(user_dates_fmt, user_qty))
                y = [user_sales_by_date.get(d, 0) for d in all_dates]
                display_name = username_to_name.get(username, username)
                ax.plot(all_dates, y, marker='s', label=display_name, color=mcolors.to_hex(color_map(idx)), linewidth=2)
            ax.set_xlabel('Период', color='white')
            ax.set_ylabel('Количество', color='white')
            ax.legend(title='Продавец', fontsize=10, title_fontsize=11)
            ax.tick_params(colors='white')
            days_count = (date_to_dt - date_from_dt).days + 1
            show_days = days_count <= 31 or (date_from_dt.month == date_to_dt.month and date_from_dt.year == date_to_dt.year)
            months_ru = [
                'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
            ]
            x = np.arange(len(all_dates))
            month_brackets = []
            if show_days:
                xtick_idx = list(range(0, len(all_dates), max(1, len(all_dates)//10)))
                day_year_labels = []
                for d in all_dates:
                    try:
                        if '-' in d:
                            parts = d.split('-')
                            day = parts[2]
                            year = parts[0]
                        else:
                            day = d
                            year = ''
                    except Exception:
                        day = d
                        year = ''
                    day_year_labels.append(f"{day} {year}")
                ax.set_xticks([all_dates[i] for i in xtick_idx])
                ax.set_xticklabels([day_year_labels[i] for i in xtick_idx], rotation=90, fontsize=8, color='white')
                fig.subplots_adjust(bottom=0.22)
            else:
                ax.set_xticks(x)
                ax.set_xticklabels([''] * len(all_dates))
                from collections import defaultdict
                month_indices = defaultdict(list)
                for i, d in enumerate(all_dates):
                    try:
                        if '.' in d:
                            m = int(d[3:5])
                            y = int(d[6:])
                        elif '-' in d:
                            m = int(d[5:7])
                            y = int(d[:4])
                        else:
                            m = 1
                            y = 2000
                    except Exception:
                        m = 1
                        y = 2000
                    month_indices[(y, m)].append(i)
                # --- Вертикальная сетка по дням ---
                ax.xaxis.grid(True, which='major', linestyle=':', color='#888', alpha=0.25, zorder=0)
                # --- Скобки и подписи месяцев ---
                y_min, y_max = ax.get_ylim()
                # Рассчитываем позицию скобки в координатах данных, привязываясь к низу осей в координатах осей
                y_pos_axes = -0.12 # Позиция в координатах осей (0 - низ, 1 - верх)
                y_bracket = ax.get_ylim()[0] + y_pos_axes * (ax.get_ylim()[1] - ax.get_ylim()[0])

                for (y, m), idxs in month_indices.items():
                    start, end = idxs[0], idxs[-1]
                    # Рисуем горизонтальную линию скобки в координатах данных
                    bracket_line, = ax.plot([start, end], [y_bracket, y_bracket], color='white', lw=2, clip_on=False, picker=10, transform=ax.transData)
                    # Рисуем вертикальные засечки скобки в координатах данных
                    ax.plot([start, start], [y_bracket, y_bracket + (y_max - y_min) * 0.01], color='white', lw=2, clip_on=False, transform=ax.transData)
                    ax.plot([end, end], [y_bracket, y_bracket + (y_max - y_min) * 0.01], color='white', lw=2, clip_on=False, transform=ax.transData)
                    # Добавляем подпись месяца
                    month_name = months_ru[m-1]
                    # Используем координаты осей для позиционирования текста
                    ax.text((start+end)/2, y_pos_axes - 0.02, month_name, ha='center', va='top', color='white', fontsize=10, fontweight='bold', clip_on=False, zorder=10, transform=blended_transform_factory(ax.transData, ax.transAxes))
                    # Сохраняем координаты и месяц для интерактивности
                    month_brackets.append({'line': bracket_line, 'year': y, 'month': m})
                    def on_bracket_click(event):
                        for bracket in month_brackets:
                            if event.artist == bracket['line']:
                                from PyQt5.QtCore import QDate
                                year, month = bracket['year'], bracket['month']
                                qdate_from = QDate(year, month, 1)
                                if month == 12:
                                    qdate_to = QDate(year+1, 1, 1).addDays(-1)
                                else:
                                    qdate_to = QDate(year, month+1, 1).addDays(-1)
                                self.date_from.setDate(qdate_from)
                                self.date_to.setDate(qdate_to)
                                self.load_data()
                                break
                    fig.canvas.mpl_connect('pick_event', on_bracket_click)
            if days_count <= 31:
                ax.grid(True, linestyle='--', alpha=0.3)
            else:
                ax.grid(False)
            fig.patch.set_facecolor('#3c3f56')
            ax.set_facecolor('#3c3f56')
            fig.subplots_adjust(bottom=0.22)
            graph_layout.addWidget(canvas)
            self.graphs_layout.addWidget(graph_frame)
            return

        # Настройка стиля графика
        plt.style.use('dark_background')
        ax.tick_params(colors='white')
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.title.set_color('white')
        
        # Добавляем сетку
        days_count = (self.date_to.date().toPyDate() - self.date_from.date().toPyDate()).days + 1
        if days_count <= 31:
            ax.grid(True, linestyle='--', alpha=0.3)
        else:
            # --- Добавляем редкую вертикальную сетку по месяцам ---
            from collections import defaultdict
            month_indices = defaultdict(list)
            for i, d in enumerate(dates):
                try:
                    if '.' in d:
                        m = int(d[3:5])
                        y = int(d[6:])
                    elif '-' in d:
                        m = int(d[5:7])
                        y = int(d[:4])
                    else:
                        m = 1
                        y = 2000
                except Exception:
                    m = 1
                    y = 2000
                month_indices[(y, m)].append(i)
            for (y, m), idxs in month_indices.items():
                # Ставим вертикальную линию по первому дню месяца (кроме самого первого месяца)
                if idxs[0] != 0:
                    ax.axvline(idxs[0] - 0.5, color='#888', linestyle=':', linewidth=1, alpha=0.35, zorder=0)
            # Можно добавить подписи месяцев, если нужно

        # Переместить подпись 'Период' наверх
        # Формируем красивый заголовок периода
        months_ru = [
            'январь', 'февраль', 'март', 'апрель', 'май', 'июнь',
            'июль', 'август', 'сентябрь', 'октябрь', 'ноябрь', 'декабрь'
        ]
        date_from = self.date_from.date().toPyDate()
        date_to = self.date_to.date().toPyDate()
        if date_from == date_to:
            # Один день
            title_period = f"Период {date_from.day} {months_ru[date_from.month-1]} {date_from.year}"
        elif date_from.year == date_to.year:
            if date_from.month == date_to.month:
                # Один месяц
                title_period = f"Период {months_ru[date_from.month-1]} {date_from.year}"
            else:
                # Несколько месяцев в одном году
                title_period = f"Период {months_ru[date_from.month-1]}–{months_ru[date_to.month-1]} {date_from.year}"
        else:
            # Диапазон на несколько лет
            title_period = f"Период {months_ru[date_from.month-1]} {date_from.year} – {months_ru[date_to.month-1]} {date_to.year}"
        fig.suptitle(title_period, fontsize=12, color='white', y=0.98, fontweight='normal')
        # --- Новый блок: настройка подписей оси X и скобок ---
        from datetime import datetime as dt
        date_from = self.date_from.date().toPyDate()
        date_to = self.date_to.date().toPyDate()
        days_count = (date_to - date_from).days + 1
        x = np.arange(len(dates))
        months_ru = [
            'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
            'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь'
        ]
        show_days = days_count <= 31 or (date_from.month == date_to.month and date_from.year == date_to.year)
        month_brackets = []  # Для хранения координат скобок и месяцев
        if show_days or graph_type == "Круговой":
            # Формируем подписи только из числа и года
            day_year_labels = []
            for d in dates:
                try:
                    if '.' in d:
                        parts = d.split('.')
                        day = parts[0]
                        year = parts[2]
                    elif '-' in d:
                        parts = d.split('-')
                        day = parts[2]
                        year = parts[0]
                    else:
                        day = d
                        year = ''
                except Exception:
                    day = d
                    year = ''
                day_year_labels.append(f"{day} {year}")
            ax.set_xticks(x)
            ax.set_xticklabels(day_year_labels, rotation=90, fontsize=8)
            fig.subplots_adjust(bottom=0.22)
        else:
            ax.set_xticks(x)
            ax.set_xticklabels([''] * len(dates))
            from collections import defaultdict
            month_indices = defaultdict(list)
            for i, d in enumerate(dates):
                try:
                    if '.' in d:
                        m = int(d[3:5])
                        y = int(d[6:])
                    elif '-' in d:
                        m = int(d[5:7])
                        y = int(d[:4])
                    else:
                        m = 1
                        y = 2000
                except Exception:
                    m = 1
                    y = 2000
                month_indices[(y, m)].append(i)
            for (y, m), idxs in month_indices.items():
                start, end = idxs[0], idxs[-1]
                # Фиксированная позиция в координатах осей (0 - низ, 1 - верх)
                y_pos_axes = -0.08 # Позиция для скобки
                y_text_axes = y_pos_axes # Позиция для текста месяца (верх текста у линии)
                
                # Рассчитываем позицию в координатах данных для рисования линий
                y_bracket_data = ax.get_ylim()[0] + y_pos_axes * (ax.get_ylim()[1] - ax.get_ylim()[0])

                # Рисуем горизонтальную линию скобки в координатах данных
                bracket_line, = ax.plot([start, end], [y_bracket_data, y_bracket_data], color='white', lw=2, clip_on=False, picker=10, transform=ax.transData)
                # Рисуем вертикальные засечки скобки в координатах данных
                ax.plot([start, start], [y_bracket_data, y_bracket_data - (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.01], color='white', lw=2, clip_on=False, transform=ax.transData)
                ax.plot([end, end], [y_bracket_data, y_bracket_data - (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.01], color='white', lw=2, clip_on=False, transform=ax.transData)
                
                # Добавляем подпись месяца в координатах осей (ось X - данные, ось Y - оси)
                month_name = months_ru[m-1]
                ax.text((start+end)/2, y_text_axes, month_name, ha='center', va='top', color='white', fontsize=10, fontweight='bold', clip_on=False, transform=blended_transform_factory(ax.transData, ax.transAxes))
                
                # Сохраняем линию скобки и данные для интерактивности
                month_brackets.append({'line': bracket_line, 'year': y, 'month': m})
                
            # --- Добавляем обработчик клика по скобкам ---
            def on_bracket_click(event):
                for bracket in month_brackets:
                    if event.artist == bracket['line']:
                        # Устанавливаем период календаря на месяц скобки
                        from PyQt5.QtCore import QDate
                        year, month = bracket['year'], bracket['month']
                        qdate_from = QDate(year, month, 1)
                        if month == 12:
                            qdate_to = QDate(year+1, 1, 1).addDays(-1)
                        else:
                            qdate_to = QDate(year, month+1, 1).addDays(-1)
                        self.date_from.setDate(qdate_from)
                        self.date_to.setDate(qdate_to)
                        self.load_data()
                        break
            fig.canvas.mpl_connect('pick_event', on_bracket_click)
        # --- конец блока ---

        # Создание графика в зависимости от выбранного типа
        if graph_type == "Линейный":
            ax.plot(dates, total_quantity, marker='o', label='Количество', color='#43e97b', linewidth=2)
            ax.legend()
            ax.set_xlabel('Период')
            ax.set_ylabel('Значение')
            ax.set_title(f'Аналитика продаж - Период {title_period}')

            # Добавляем интерактивность с подсказками
            cursor = mplcursors.cursor(ax, hover=mplcursors.HoverMode.Transient)

            @cursor.connect("add")
            def on_add(sel):
                idx = int(sel.index)  # Convert numpy.float64 to int
                value = total_quantity[idx]
                sel.annotation.set_text(f"Количество: {value}")
                sel.annotation.get_bbox_patch().set(fc="rgba(255, 255, 255, 0.8)", lw=0)
                sel.annotation.set_color("#23243a")

            # Добавляем возможность клика по точке для перехода к более детальному периоду
            def on_point_click(event):
                if event.inaxes == ax:
                    idx = ax.get_closest_index(event.x, event.y)
                    if idx >= 0 and idx < len(dates):
                        clicked_date_str = dates[idx]
                        # Пытаемся определить формат даты и установить соответствующий период
                        try:
                            # Формат ДД.ММ.ГГГГ
                            from datetime import datetime
                            clicked_date = datetime.strptime(clicked_date_str, "%d.%m.%Y")
                            self.date_from.setDate(clicked_date)
                            self.date_to.setDate(clicked_date)
                            self.load_data() # Перезагружаем данные с выбранной датой
                        except ValueError:
                            try:
                                # Формат ГГГГ-НН (неделя)
                                year, week = map(int, clicked_date_str.split('-'))
                                # Рассчитываем даты начала и конца недели
                                first_day_of_year = datetime(year, 1, 1)
                                # Находим первый понедельник года (или сам 1 января, если он понедельник)
                                if first_day_of_year.weekday() <= 3: # 0=Пн, 6=Вс. Если 1-4, то это первая неделя ISO
                                    start_of_first_week = first_day_of_year - timedelta(days=first_day_of_year.weekday())
                                else:
                                    start_of_first_week = first_day_of_year + timedelta(days=(7 - first_day_of_year.weekday()))
                                start_of_week = start_of_first_week + timedelta(weeks=week-1)
                                end_of_week = start_of_week + timedelta(days=6)
                                self.date_from.setDate(start_of_week.date())
                                self.date_to.setDate(end_of_week.date())
                                self.load_data() # Перезагружаем данные с выбранной неделей
                            except ValueError:
                                try:
                                    # Формат ММ.ГГГГ
                                    month, year = map(int, clicked_date_str.split('.'))
                                    from datetime import datetime
                                    start_of_month = datetime(year, month, 1)
                                    if month == 12:
                                        end_of_month = datetime(year + 1, 1, 1) - timedelta(days=1)
                                    else:
                                        end_of_month = datetime(year, month + 1, 1) - timedelta(days=1)
                                    self.date_from.setDate(start_of_month.date())
                                    self.date_to.setDate(end_of_month.date())
                                    self.load_data() # Перезагружаем данные с выбранным месяцем
                                except ValueError:
                                    # Если формат не распознан, ничего не делаем
                                    pass
        elif graph_type == "Столбчатый":
            x = np.arange(len(dates))
            width = 0.35
            rects2 = ax.bar(x, total_quantity, width, label='Количество', color='#43e97b')
            ax.set_ylabel('Значение')
            ax.set_title(f'Аналитика продаж - Период {title_period}')
            ax.set_xticks(x)
            ax.set_xticklabels(dates, rotation=45, ha="right")
            ax.legend()

            # Добавляем значения над столбцами
            def autolabel(rects):
                for rect in rects:
                    height = rect.get_height()
                    ax.text(rect.get_x() + rect.get_width()/2, height,
                            f'{height:.2f}',
                            ha='center', va='bottom', fontsize=10, color='#43e97b')
            autolabel(rects2)
        else:  # Круговой
            # Для кругового графика отображаем только количество
            ax.pie(total_quantity, labels=dates, autopct='%1.1f%%', startangle=140, colors=plt.cm.viridis(np.linspace(0, 1, len(dates))))
            ax.set_title(f'Распределение продаж - Период {title_period}')
            # Добавляем интерактивность
            cursor_pie = mplcursors.cursor(hover=mplcursors.HoverMode.Transient)

            @cursor_pie.connect("add")
            def on_add_pie(sel):
                # Получаем индекс выбранного сегмента
                index = sel.index
                # Форматируем информацию для отображения
                period = dates[index]
                quantity = total_quantity[index]
                sel.annotation.set_text(f'{period}:\n Количество: {quantity}')
                sel.annotation.get_bbox_patch().set(fc="rgba(255, 255, 255, 0.8)", lw=0)
                sel.annotation.set_color("#23243a")

            # Добавляем возможность клика по сегменту для перехода к более детальному периоду
            for i, date in enumerate(dates):
                wedge = ax.patches[i]
                wedge.set_picker(True) # Включаем возможность "кликабельности" для каждого сегмента

            def on_pie_click(event):
                if event.artist in ax.patches:
                    index = ax.patches.index(event.artist)
                    clicked_date_str = dates[index]
                    # Пытаемся определить формат даты и установить соответствующий период
                    try:
                        # Формат ДД.ММ.ГГГГ
                        from datetime import datetime
                        clicked_date = datetime.strptime(clicked_date_str, "%d.%m.%Y")
                        self.date_from.setDate(clicked_date)
                        self.date_to.setDate(clicked_date)
                        self.load_data() # Перезагружаем данные с выбранной датой
                    except ValueError:
                        try:
                            # Формат ГГГГ-НН (неделя)
                            year, week = map(int, clicked_date_str.split('-'))
                            # Рассчитываем даты начала и конца недели
                            first_day_of_year = datetime(year, 1, 1)
                            # Находим первый понедельник года (или сам 1 января, если он понедельник)
                            if first_day_of_year.weekday() <= 3: # 0=Пн, 6=Вс. Если 1-4, то это первая неделя ISO
                                start_of_first_week = first_day_of_year - timedelta(days=first_day_of_year.weekday())
                            else:
                                start_of_first_week = first_day_of_year + timedelta(days=(7 - first_day_of_year.weekday()))
                            start_of_week = start_of_first_week + timedelta(weeks=week-1)
                            end_of_week = start_of_week + timedelta(days=6)
                            self.date_from.setDate(start_of_week.date())
                            self.date_to.setDate(end_of_week.date())
                            self.load_data() # Перезагружаем данные с выбранной неделей
                        except ValueError:
                            try:
                                # Формат ММ.ГГГГ
                                month, year = map(int, clicked_date_str.split('.'))
                                from datetime import datetime
                                start_of_month = datetime(year, month, 1)
                                if month == 12:
                                    end_of_month = datetime(year + 1, 1, 1) - timedelta(days=1)
                                else:
                                    end_of_month = datetime(year, month + 1, 1) - timedelta(days=1)
                                self.date_from.setDate(start_of_month.date())
                                self.date_to.setDate(end_of_month.date())
                                self.load_data() # Перезагружаем данные с выбранным месяцем
                            except ValueError:
                                # Если формат не распознан, ничего не делаем
                                pass

        # Настройка отображения
        fig.tight_layout()
        graph_layout.addWidget(canvas)
        self.graphs_layout.addWidget(graph_frame)

    def clear_analytics(self):
        """Очищает историю продаж"""
        if self.role != "администратор":
            QMessageBox.warning(self, "Ошибка", "У вас нет прав для выполнения этого действия.")
            return

        reply = QMessageBox.question(
            self,
            'Подтверждение',
            'Вы уверены, что хотите очистить всю историю продаж? Это действие нельзя отменить.',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self.db.clear_sales_history()
                QMessageBox.information(self, "Успех", "История продаж успешно очищена.")
                self.load_data()  # Обновляем графики
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось очистить историю продаж: {str(e)}")

    def update_weekday_bar_chart(self):
        self.weekday_fig.clear()
        ax = self.weekday_fig.add_subplot(111)
        ax.set_facecolor('#3c3f56')
        # Получаем все продажи
        self.db.cursor.execute("SELECT sale_date, quantity FROM sales_history")
        sales = self.db.cursor.fetchall()
        print('DEBUG: первые 10 дат и количеств из sales_history:', sales[:10])
        # Считаем продажи по дням недели
        import datetime
        from collections import defaultdict
        weekday_sums = defaultdict(int)
        weekday_counts = defaultdict(int)
        for date_val, qty in sales:
            try:
                if isinstance(date_val, (datetime.date, datetime.datetime)):
                    dt_obj = date_val
                elif isinstance(date_val, str):
                    if '-' in date_val:
                        dt_obj = datetime.datetime.strptime(date_val, "%Y-%m-%d")
                    elif '.' in date_val:
                        dt_obj = datetime.datetime.strptime(date_val, "%d.%m.%Y")
                else:
                    continue
                qty = int(qty)
                weekday = dt_obj.weekday()  # 0=Пн, 6=Вс
                weekday_sums[weekday] += qty
                weekday_counts[weekday] += 1
            except Exception:
                continue
        # Среднее по каждому дню недели
        weekdays = [0,1,2,3,4,5,6]
        weekday_labels = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
        weekday_means = [weekday_sums[w]/weekday_counts[w] if weekday_counts[w] else 0 for w in weekdays]
        # Современный стиль: выделить max, подписи
        import matplotlib.colors as mcolors
        import numpy as np
        from matplotlib import cm
        if weekday_means:
            max_val = max(weekday_means)
            norm = mcolors.Normalize(vmin=min(weekday_means), vmax=max_val)
            cmap = cm.get_cmap('summer')
            bar_colors = [cmap(norm(q)) for q in weekday_means]
            max_idx = weekday_means.index(max_val)
            bar_colors[max_idx] = '#43ff7b'
        else:
            bar_colors = ['#43e97b']*7
        bars = ax.barh(weekday_labels, weekday_means, color=bar_colors, zorder=3, edgecolor="#23243a", linewidth=1.5, height=0.6)
        for rect, val in zip(bars, weekday_means):
            ax.text(rect.get_width() + max(weekday_means)*0.03, rect.get_y() + rect.get_height()/2, f'{val:.1f}',
                    ha='left', va='center', fontsize=13, fontweight='bold', color='#43e97b', zorder=10)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#888')
        ax.spines['bottom'].set_color('#888')
        ax.tick_params(axis='x', colors='white', labelsize=12)
        ax.tick_params(axis='y', colors='white', labelsize=13)
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.set_xlabel('Среднее количество продаж', color='white', fontsize=14, fontweight='bold')
        ax.set_ylabel('День недели', color='white', fontsize=14, fontweight='bold')
        ax.xaxis.grid(True, linestyle='--', color='#43e97b', alpha=0.18, zorder=1)
        ax.yaxis.grid(False)
        self.weekday_fig.tight_layout()
        self.weekday_canvas.draw() 

    def update_topcat_bar_chart(self):
        self.topcat_fig.clear()
        ax = self.topcat_fig.add_subplot(111)
        ax.set_facecolor('#3c3f56')
        # Получаем топ-5 категорий по продажам
        self.db.cursor.execute('''
            SELECT COALESCE(p.category, 'Без категории') as category, SUM(s.quantity) as total_qty
            FROM sales_history s
            JOIN products p ON s.product_name = p.name
            GROUP BY category
            ORDER BY total_qty DESC
            LIMIT 5
        ''')
        data = self.db.cursor.fetchall()
        categories = [row[0] for row in data]
        qtys = [row[1] for row in data]
        import matplotlib.colors as mcolors
        import numpy as np
        from matplotlib import cm
        if qtys:
            max_val = max(qtys)
            min_val = min(qtys)
            norm = mcolors.Normalize(vmin=min_val, vmax=max_val)
            cmap = cm.get_cmap('summer')
            bar_colors = [cmap(norm(q)) for q in qtys]
            max_idx = qtys.index(max_val)
            
            bar_colors[max_idx] = '#43ff7b'
        else:
            bar_colors = ['#43e97b']*5
        bars = ax.barh(categories, qtys, color=bar_colors, zorder=3, edgecolor="#23243a", linewidth=1.5, height=0.6)
        for rect, val in zip(bars, qtys):
            ax.text(rect.get_width() + max(qtys)*0.03, rect.get_y() + rect.get_height()/2, str(val),
                    ha='left', va='center', fontsize=13, fontweight='bold', color='#43e97b', zorder=10)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#888')
        ax.spines['bottom'].set_color('#888')
        ax.tick_params(axis='x', colors='white', labelsize=12)
        ax.tick_params(axis='y', colors='white', labelsize=13)
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.set_xlabel('Продано, шт.', color='white', fontsize=14, fontweight='bold')
        ax.set_ylabel('Категория', color='white', fontsize=14, fontweight='bold')
        ax.xaxis.grid(True, linestyle='--', color='#43e97b', alpha=0.18, zorder=1)
        ax.yaxis.grid(False)
        self.topcat_fig.tight_layout()
        self.topcat_canvas.draw() 

    def update_growth_list(self):
        # Очищаем старые элементы
        for i in reversed(range(self.growth_list_layout.count())):
            widget = self.growth_list_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        import datetime
        today = datetime.date.today()
        first_day_this_month = today.replace(day=1)
        last_month = (first_day_this_month - datetime.timedelta(days=1)).replace(day=1)
        # Получаем продажи по товарам за текущий и предыдущий месяц
        self.db.cursor.execute('''
            SELECT product_name, SUM(quantity) as qty
            FROM sales_history
            WHERE sale_date >= %s AND sale_date < %s
            GROUP BY product_name
        ''', (first_day_this_month.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')))
        this_month_sales = {row[0]: row[1] for row in self.db.cursor.fetchall()}
        self.db.cursor.execute('''
            SELECT product_name, SUM(quantity) as qty
            FROM sales_history
            WHERE sale_date >= %s AND sale_date < %s
            GROUP BY product_name
        ''', (last_month.strftime('%Y-%m-%d'), first_day_this_month.strftime('%Y-%m-%d')))
        last_month_sales = {row[0]: row[1] for row in self.db.cursor.fetchall()}
        # Считаем прирост
        all_products = set(this_month_sales.keys()) | set(last_month_sales.keys())
        growth = []
        for name in all_products:
            qty_now = this_month_sales.get(name, 0)
            qty_prev = last_month_sales.get(name, 0)
            diff = qty_now - qty_prev
            growth.append((name, qty_now, qty_prev, diff))
        growth.sort(key=lambda x: x[3], reverse=True)
        top5 = growth[:5]
        from PyQt5.QtWidgets import QLabel, QHBoxLayout, QWidget
        for name, qty_now, qty_prev, diff in top5:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(10)
            name_lbl = QLabel(f"<b>{name}</b>")
            name_lbl.setStyleSheet("color: #43e97b; font-size: 15px;")
            now_lbl = QLabel(f"{qty_now} шт.")
            now_lbl.setStyleSheet("color: #fff; font-size: 15px;")
            diff_lbl = QLabel(f"+{diff}" if diff > 0 else str(diff))
            diff_lbl.setStyleSheet(f"color: {'#43e97b' if diff > 0 else '#ff5555'}; font-size: 15px; font-weight: bold;")
            row_layout.addWidget(name_lbl, 2)
            row_layout.addWidget(now_lbl, 1)
            row_layout.addWidget(diff_lbl, 1)
            self.growth_list_layout.addWidget(row)
        if not top5:
            empty_lbl = QLabel("Нет данных для анализа прироста.")
            empty_lbl.setStyleSheet("color: #888; font-size: 15px;")
            self.growth_list_layout.addWidget(empty_lbl) 

    def update_low_stock_table(self):
        """Обновляет таблицу товаров с низким остатком"""
        try:
            low_stock_products = self.db.get_low_stock_products()
            self.low_stock_table.setRowCount(len(low_stock_products))
            
            for row, product in enumerate(low_stock_products):
                # Товар
                name_item = QTableWidgetItem(product['name'])
                name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                self.low_stock_table.setItem(row, 0, name_item)
                
                # Категория
                category_item = QTableWidgetItem(product['category'])
                category_item.setFlags(category_item.flags() & ~Qt.ItemIsEditable)
                self.low_stock_table.setItem(row, 1, category_item)
                
                # Текущее количество
                quantity_item = QTableWidgetItem(str(product['quantity']))
                quantity_item.setFlags(quantity_item.flags() & ~Qt.ItemIsEditable)
                if product['quantity'] < product['min_quantity']:
                    quantity_item.setForeground(QColor('#ff4444'))  # Красный цвет для низкого остатка
                self.low_stock_table.setItem(row, 2, quantity_item)
                
                # Минимальное количество
                min_quantity_item = QTableWidgetItem(str(product['min_quantity']))
                min_quantity_item.setFlags(min_quantity_item.flags() & ~Qt.ItemIsEditable)
                self.low_stock_table.setItem(row, 3, min_quantity_item)
                
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить данные: {str(e)}") 

    def restore_full_period(self):
        """Откатить на один шаг назад по истории периодов"""
        if hasattr(self, 'period_history') and len(self.period_history) > 1:
            self.period_history.pop()  # Удаляем текущий период
            prev_from, prev_to = self.period_history[-1]
            from PyQt5.QtCore import QDate
            self.date_from.setDate(QDate.fromString(prev_from, "yyyy-MM-dd"))
            self.date_to.setDate(QDate.fromString(prev_to, "yyyy-MM-dd"))
            self.load_data()

    def set_year_period(self):
        """Установить период за последний год"""
        from PyQt5.QtCore import QDate
        today = QDate.currentDate()
        self.date_from.setDate(today.addYears(-1))
        self.date_to.setDate(today)
        self.load_data()

    def set_all_time_period(self):
        """Установить период за всю историю"""
        from PyQt5.QtCore import QDate
        today = QDate.currentDate()
        
        # Получаем дату первой продажи
        first_sale_date = self.db.get_first_sale_date(self.username if self.role == "пользователь" else None)
        
        if first_sale_date:
            # Если есть продажи, используем дату первой продажи
            self.date_from.setDate(QDate.fromString(first_sale_date, "yyyy-MM-dd"))
        else:
            # Если продаж нет, используем дату 10 лет назад
            self.date_from.setDate(today.addYears(-10))
            
        self.date_to.setDate(today)
        self.load_data()

    def update_weekday_bar_chart(self):
        self.weekday_fig.clear()
        ax = self.weekday_fig.add_subplot(111)
        ax.set_facecolor('#3c3f56')
        # Получаем все продажи
        self.db.cursor.execute("SELECT sale_date, quantity FROM sales_history")
        sales = self.db.cursor.fetchall()
        print('DEBUG: первые 10 дат и количеств из sales_history:', sales[:10])
        # Считаем продажи по дням недели
        import datetime
        from collections import defaultdict
        weekday_sums = defaultdict(int)
        weekday_counts = defaultdict(int)
        for date_val, qty in sales:
            try:
                if isinstance(date_val, (datetime.date, datetime.datetime)):
                    dt_obj = date_val
                elif isinstance(date_val, str):
                    if '-' in date_val:
                        dt_obj = datetime.datetime.strptime(date_val, "%Y-%m-%d")
                    elif '.' in date_val:
                        dt_obj = datetime.datetime.strptime(date_val, "%d.%m.%Y")
                else:
                    continue
                qty = int(qty)
                weekday = dt_obj.weekday()  # 0=Пн, 6=Вс
                weekday_sums[weekday] += qty
                weekday_counts[weekday] += 1
            except Exception:
                continue
        # Среднее по каждому дню недели
        weekdays = [0,1,2,3,4,5,6]
        weekday_labels = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']
        weekday_means = [weekday_sums[w]/weekday_counts[w] if weekday_counts[w] else 0 for w in weekdays]
        # Современный стиль: выделить max, подписи
        import matplotlib.colors as mcolors
        import numpy as np
        from matplotlib import cm
        if weekday_means:
            max_val = max(weekday_means)
            norm = mcolors.Normalize(vmin=min(weekday_means), vmax=max_val)
            cmap = cm.get_cmap('summer')
            bar_colors = [cmap(norm(q)) for q in weekday_means]
            max_idx = weekday_means.index(max_val)
            bar_colors[max_idx] = '#43ff7b'
        else:
            bar_colors = ['#43e97b']*7
        bars = ax.barh(weekday_labels, weekday_means, color=bar_colors, zorder=3, edgecolor="#23243a", linewidth=1.5, height=0.6)
        for rect, val in zip(bars, weekday_means):
            ax.text(rect.get_width() + max(weekday_means)*0.03, rect.get_y() + rect.get_height()/2, f'{val:.1f}',
                    ha='left', va='center', fontsize=13, fontweight='bold', color='#43e97b', zorder=10)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#888')
        ax.spines['bottom'].set_color('#888')
        ax.tick_params(axis='x', colors='white', labelsize=12)
        ax.tick_params(axis='y', colors='white', labelsize=13)
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.set_xlabel('Среднее количество продаж', color='white', fontsize=14, fontweight='bold')
        ax.set_ylabel('День недели', color='white', fontsize=14, fontweight='bold')
        ax.xaxis.grid(True, linestyle='--', color='#43e97b', alpha=0.18, zorder=1)
        ax.yaxis.grid(False)
        self.weekday_fig.tight_layout()
        self.weekday_canvas.draw() 

    def update_topcat_bar_chart(self):
        self.topcat_fig.clear()
        ax = self.topcat_fig.add_subplot(111)
        ax.set_facecolor('#3c3f56')
        # Получаем топ-5 категорий по продажам
        self.db.cursor.execute('''
            SELECT COALESCE(p.category, 'Без категории') as category, SUM(s.quantity) as total_qty
            FROM sales_history s
            JOIN products p ON s.product_name = p.name
            GROUP BY category
            ORDER BY total_qty DESC
            LIMIT 5
        ''')
        data = self.db.cursor.fetchall()
        categories = [row[0] for row in data]
        qtys = [row[1] for row in data]
        import matplotlib.colors as mcolors
        import numpy as np
        from matplotlib import cm
        if qtys:
            max_val = max(qtys)
            min_val = min(qtys)
            norm = mcolors.Normalize(vmin=min_val, vmax=max_val)
            cmap = cm.get_cmap('summer')
            bar_colors = [cmap(norm(q)) for q in qtys]
            max_idx = qtys.index(max_val)
            
            bar_colors[max_idx] = '#43ff7b'
        else:
            bar_colors = ['#43e97b']*5
        bars = ax.barh(categories, qtys, color=bar_colors, zorder=3, edgecolor="#23243a", linewidth=1.5, height=0.6)
        for rect, val in zip(bars, qtys):
            ax.text(rect.get_width() + max(qtys)*0.03, rect.get_y() + rect.get_height()/2, str(val),
                    ha='left', va='center', fontsize=13, fontweight='bold', color='#43e97b', zorder=10)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#888')
        ax.spines['bottom'].set_color('#888')
        ax.tick_params(axis='x', colors='white', labelsize=12)
        ax.tick_params(axis='y', colors='white', labelsize=13)
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.set_xlabel('Продано, шт.', color='white', fontsize=14, fontweight='bold')
        ax.set_ylabel('Категория', color='white', fontsize=14, fontweight='bold')
        ax.xaxis.grid(True, linestyle='--', color='#43e97b', alpha=0.18, zorder=1)
        ax.yaxis.grid(False)
        self.topcat_fig.tight_layout()
        self.topcat_canvas.draw() 

    def update_growth_list(self):
        # Очищаем старые элементы
        for i in reversed(range(self.growth_list_layout.count())):
            widget = self.growth_list_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        import datetime
        today = datetime.date.today()
        first_day_this_month = today.replace(day=1)
        last_month = (first_day_this_month - datetime.timedelta(days=1)).replace(day=1)
        # Получаем продажи по товарам за текущий и предыдущий месяц
        self.db.cursor.execute('''
            SELECT product_name, SUM(quantity) as qty
            FROM sales_history
            WHERE sale_date >= %s AND sale_date < %s
            GROUP BY product_name
        ''', (first_day_this_month.strftime('%Y-%m-%d'), today.strftime('%Y-%m-%d')))
        this_month_sales = {row[0]: row[1] for row in self.db.cursor.fetchall()}
        self.db.cursor.execute('''
            SELECT product_name, SUM(quantity) as qty
            FROM sales_history
            WHERE sale_date >= %s AND sale_date < %s
            GROUP BY product_name
        ''', (last_month.strftime('%Y-%m-%d'), first_day_this_month.strftime('%Y-%m-%d')))
        last_month_sales = {row[0]: row[1] for row in self.db.cursor.fetchall()}
        # Считаем прирост
        all_products = set(this_month_sales.keys()) | set(last_month_sales.keys())
        growth = []
        for name in all_products:
            qty_now = this_month_sales.get(name, 0)
            qty_prev = last_month_sales.get(name, 0)
            diff = qty_now - qty_prev
            growth.append((name, qty_now, qty_prev, diff))
        growth.sort(key=lambda x: x[3], reverse=True)
        top5 = growth[:5]
        from PyQt5.QtWidgets import QLabel, QHBoxLayout, QWidget
        for name, qty_now, qty_prev, diff in top5:
            row = QWidget()
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(10)
            name_lbl = QLabel(f"<b>{name}</b>")
            name_lbl.setStyleSheet("color: #43e97b; font-size: 15px;")
            now_lbl = QLabel(f"{qty_now} шт.")
            now_lbl.setStyleSheet("color: #fff; font-size: 15px;")
            diff_lbl = QLabel(f"+{diff}" if diff > 0 else str(diff))
            diff_lbl.setStyleSheet(f"color: {'#43e97b' if diff > 0 else '#ff5555'}; font-size: 15px; font-weight: bold;")
            row_layout.addWidget(name_lbl, 2)
            row_layout.addWidget(now_lbl, 1)
            row_layout.addWidget(diff_lbl, 1)
            self.growth_list_layout.addWidget(row)
        if not top5:
            empty_lbl = QLabel("Нет данных для анализа прироста.")
            empty_lbl.setStyleSheet("color: #888; font-size: 15px;")
            self.growth_list_layout.addWidget(empty_lbl) 

    def update_low_stock_table(self):
        """Обновляет таблицу товаров с низким остатком"""
        try:
            low_stock_products = self.db.get_low_stock_products()
            self.low_stock_table.setRowCount(len(low_stock_products))
            
            for row, product in enumerate(low_stock_products):
                # Товар
                name_item = QTableWidgetItem(product['name'])
                name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
                self.low_stock_table.setItem(row, 0, name_item)
                
                # Категория
                category_item = QTableWidgetItem(product['category'])
                category_item.setFlags(category_item.flags() & ~Qt.ItemIsEditable)
                self.low_stock_table.setItem(row, 1, category_item)
                
                # Текущее количество
                quantity_item = QTableWidgetItem(str(product['quantity']))
                quantity_item.setFlags(quantity_item.flags() & ~Qt.ItemIsEditable)
                if product['quantity'] < product['min_quantity']:
                    quantity_item.setForeground(QColor('#ff4444'))  # Красный цвет для низкого остатка
                self.low_stock_table.setItem(row, 2, quantity_item)
                
                # Минимальное количество
                min_quantity_item = QTableWidgetItem(str(product['min_quantity']))
                min_quantity_item.setFlags(min_quantity_item.flags() & ~Qt.ItemIsEditable)
                self.low_stock_table.setItem(row, 3, min_quantity_item)
                
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить данные: {str(e)}") 

    def update_toptov_bar_chart(self):
        self.toptov_fig.clear()
        ax = self.toptov_fig.add_subplot(111)
        ax.set_facecolor('#3c3f56')
        # Получаем топ-5 товаров по продажам
        self.db.cursor.execute('''
            SELECT s.product_name, SUM(s.quantity) as total_qty
            FROM sales_history s
            GROUP BY s.product_name
            HAVING SUM(s.quantity) > 0
            ORDER BY total_qty DESC
            LIMIT 5
        ''')
        data = self.db.cursor.fetchall()
        products = [row[0] for row in data]
        qtys = [row[1] for row in data]
        # Формируем инициалы для подписей
        def get_initials(name):
            parts = name.split()
            if len(parts) >= 2:
                return (parts[0][0] + parts[1][0]).upper()
            elif len(parts) == 1:
                return parts[0][:2].upper()
            return name[:2].upper()
        initials = [get_initials(p) for p in products]
        import matplotlib.colors as mcolors
        import numpy as np
        from matplotlib import cm
        if qtys:
            max_val = max(qtys)
            min_val = min(qtys)
            norm = mcolors.Normalize(vmin=min_val, vmax=max_val)
            cmap = cm.get_cmap('summer')
            bar_colors = [cmap(norm(q)) for q in qtys]
            max_idx = qtys.index(max_val)
            bar_colors[max_idx] = '#43ff7b'
        else:
            bar_colors = ['#43e97b']*5
        bars = ax.barh(initials, qtys, color=bar_colors, zorder=3, edgecolor="#23243a", linewidth=1.5, height=0.6)
        for rect, val in zip(bars, qtys):
            ax.text(rect.get_width() + max(qtys)*0.03, rect.get_y() + rect.get_height()/2, str(val),
                    ha='left', va='center', fontsize=13, fontweight='bold', color='#43e97b', zorder=10)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#888')
        ax.spines['bottom'].set_color('#888')
        ax.tick_params(axis='x', colors='white', labelsize=12)
        ax.tick_params(axis='y', colors='white', labelsize=13)
        ax.xaxis.label.set_color('white')
        ax.yaxis.label.set_color('white')
        ax.set_xlabel('Продано, шт.', color='white', fontsize=14, fontweight='bold')
        ax.set_ylabel('Товар', color='white', fontsize=14, fontweight='bold')
        ax.xaxis.grid(True, linestyle='--', color='#43e97b', alpha=0.18, zorder=1)
        ax.yaxis.grid(False)
        self.toptov_fig.tight_layout()
        # Добавляем тултипы с полным названием товара
        import mplcursors
        cursor = mplcursors.cursor(bars, hover=True)
        @cursor.connect("add")
        def on_add(sel):
            idx = sel.target.index
            sel.annotation.set_text(products[idx])
            sel.annotation.get_bbox_patch().set(fc="#23243a", alpha=0.95)
            sel.annotation.get_bbox_patch().set_boxstyle("round,pad=0.5")
            sel.annotation.set_color("#43e97b")
        self.toptov_canvas.draw()