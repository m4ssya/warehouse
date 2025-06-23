from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                            QSpinBox, QPushButton, QScrollArea, QFrame, QGridLayout, QSizePolicy)
from PyQt5.QtCore import (Qt, QPropertyAnimation, 
                         QEasingCurve, QPoint, QTimer)
from PyQt5.QtGui import QColor

class CategoryCard(QFrame):
    def __init__(self, category_name, min_quantity, parent=None):
        super().__init__(parent)
        self.category_name = category_name
        self.init_ui(min_quantity)
        self.setup_animation()
        # Удаляем установку горизонтальной политики размера на Expanding
        # self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
    def init_ui(self, min_quantity):
        self.setStyleSheet("""
            QFrame {
                background-color: #4a5066; /* Сделал фон светлее */
                border-radius: 12px;
                /* Добавляем тень */
                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
                padding: 12px;
            }
            QFrame:hover {
                background-color: #5a6076; /* Сделал фон при наведении светлее */
                /* Немного изменяем тень при наведении */
                box-shadow: 0 6px 12px rgba(0, 0, 0, 0.3);
            }
            QLabel {
                color: white;
                font-family: "Segoe UI", sans-serif; /* Современный шрифт */
            }
            QLabel#title { /* Стиль для заголовка категории */
                font-size: 18px;
                font-weight: bold;
                color: #ffffff;
                margin-bottom: 10px;
            }
            QLabel#min_label { /* Стиль для метки "Минимальное количество" */
                font-size: 13px;
                color: #bbbbbb;
                background-color: #454862;
                border-radius: 6px;
                padding: 4px 10px;
                margin-right: 8px;
            }
            QSpinBox {
                background-color: #3a3f4d; /* Фон спинбокса */
                color: #e0e0e0;
                border: 1px solid #555;
                border-radius: 6px;
                padding: 6px;
                font-size: 14px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                border-left: 1px solid #555;
                width: 20px;
            }
             QSpinBox::up-arrow, QSpinBox::down-arrow {
                width: 10px;
                height: 10px;
            }
            QPushButton {
                background-color: #1a8939; /* Более насыщенный зеленый */
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 15px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #156f2c; /* Темнее при наведении */
            }
             QPushButton:pressed {
                background-color: #0f501f; /* Еще темнее при нажатии */
            }
        """)
        
        # Удаляем фиксированную ширину, чтобы карточка могла растягиваться и заполнять доступное пространство
        # self.setMinimumWidth(270)
        # self.setMaximumWidth(270)
        # Устанавливаем фиксированную высоту как у ProductCard
        self.setFixedHeight(400) 
        
        # Раскомментируем установки минимальной и максимальной ширины
        self.setMinimumWidth(270)
        self.setMaximumWidth(300)
        
        layout = QVBoxLayout(self)
        # Устанавливаем такие же отступы и расстояние между элементами, как у ProductCard
        # Уменьшаем горизонтальные отступы и расстояние между элементами для лучшего размещения 6 карточек
        layout.setContentsMargins(5, 10, 5, 10) # Уменьшаем горизонтальные отступы до 5
        layout.setSpacing(3) # Уменьшаем расстояние между элементами до 3
        
        # Заголовок категории
        title = QLabel(self.category_name)
        # Устанавливаем Object Name для применения специфичных стилей
        title.setObjectName("title")
        layout.addWidget(title)
        
        # Контейнер для количества
        quantity_container = QVBoxLayout() # Изменяем на вертикальный макет
        quantity_container.setContentsMargins(0, 0, 0, 0)
        
        # Метка для минимального количества
        min_label = QLabel("Минимальное количество:")
        # Устанавливаем Object Name для применения специфичных стилей
        min_label.setObjectName("min_label")
        quantity_container.addWidget(min_label, alignment=Qt.AlignHCenter) # Выравнивание по центру по горизонтали
        
        # Поле ввода количества
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 100000)
        self.quantity_spin.setValue(min_quantity)
        self.quantity_spin.setStyleSheet("""
            QSpinBox {
                min-width: 80px;
            }
        """)
        quantity_container.addWidget(self.quantity_spin, alignment=Qt.AlignHCenter) # Выравнивание по центру по горизонтали
        
        # Кнопка сохранения
        self.save_btn = QPushButton("Сохранить")
        self.save_btn.setStyleSheet("""
            QPushButton {
                min-width: 80px;
            }
        """)
        quantity_container.addWidget(self.save_btn, alignment=Qt.AlignHCenter) # Выравнивание по центру по горизонтали
        
        layout.addLayout(quantity_container)
        layout.addStretch()
        
    def setup_animation(self):
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.setDuration(300)
        
    def enterEvent(self, event):
        if self.parent() and hasattr(self, 'animation'):
            self.animation.setStartValue(self.pos())
            self.animation.setEndValue(self.pos() + QPoint(0, -5))
            self.animation.start()
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        if self.parent() and hasattr(self, 'animation'):
            self.animation.setStartValue(self.pos())
            self.animation.setEndValue(self.pos() + QPoint(0, 5))
            self.animation.start()
        super().leaveEvent(event)

class MinQuantityPage(QWidget):
    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.cards = []
        self.init_ui()
        
    def init_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #2a2b38;
            }
        """)
        
        # Создаем скролл-область
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        
        # Создаем контейнер для карточек
        container = QWidget()
        self.grid_layout = QGridLayout(container)
        self.grid_layout.setSpacing(15)
        self.grid_layout.setContentsMargins(20, 20, 20, 20)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        # Удаляем установку растяжения для каждой колонки
        # for i in range(6):
        #     self.grid_layout.setColumnStretch(i, 1)
        
        # Заголовок
        title = QLabel("Управление минимальными количествами")
        title.setStyleSheet("""
            font-size: 20px;
            font-weight: bold;
            color: white;
            margin-bottom: 20px;
        """)
        self.grid_layout.addWidget(title, 0, 0, 1, -1)
        
        # Добавляем карточки категорий
        self.add_category_cards()
        
        self.scroll.setWidget(container)
        
        # Основной layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.scroll)
        
    def add_category_cards(self):
        if not self.db:
            return
            
        # Очищаем существующие карточки
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        self.cards = []
        
        # Получаем все категории
        categories = self.db.get_all_categories()
        
        row = 0
        col = 0
        max_cols = 6 # Устанавливаем, что в ряду должно быть 6 колонок
        
        # Создаем карточку для каждой категории
        for category in categories:
            # Получаем текущее минимальное количество для категории
            min_quantity = self.db.get_category_min_quantity(category)
            
            # Создаем карточку
            card = CategoryCard(category, min_quantity)
            card.save_btn.clicked.connect(
                lambda checked, c=category, card=card: self.save_min_quantity(c, card)
            )
            
            self.cards.append(card)
            self.grid_layout.addWidget(card, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
                
    def save_min_quantity(self, category, card):
        if not self.db:
            return
            
        min_quantity = card.quantity_spin.value()
        if self.db.set_category_min_quantity(category, min_quantity):
            # Анимация успешного сохранения
            card.setStyleSheet("""
                QFrame {
                    background-color: #28a745;
                    border-radius: 10px;
                    padding: 15px;
                }
                QLabel {
                    color: white;
                }
                QSpinBox {
                    background-color: #2a2b38;
                    color: white;
                    border: 1px solid #444;
                    border-radius: 5px;
                    padding: 5px;
                }
                QPushButton {
                    background-color: #218838;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 8px;
                }
            """)
            
            # Возвращаем исходный стиль через 1 секунду
            QTimer.singleShot(1000, lambda: card.setStyleSheet("""
                QFrame {
                    background-color: #3c3f56;
                    border-radius: 10px;
                    padding: 15px;
                }
                QFrame:hover {
                    background-color: #454b6b;
                }
                QLabel {
                    color: white;
                }
                QSpinBox {
                    background-color: #2a2b38;
                    color: white;
                    border: 1px solid #444;
                    border-radius: 5px;
                    padding: 5px;
                }
                QPushButton {
                    background-color: #28a745;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 8px;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
            """)) 

    # Переопределяем resizeEvent для обновления макета при изменении размера окна
    # Теперь только вызываем add_category_cards, так как max_cols фиксирован
    def resizeEvent(self, event):
        super().resizeEvent(event)

        pass # Удаляем вызов add_category_cards, так как он здесь не нужен для адаптации ширины 