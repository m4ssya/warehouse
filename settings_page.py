from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                            QLabel, QCheckBox, QComboBox, QSpinBox,
                            QPushButton, QFrame, QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QScrollArea

class SettingsPage(QWidget):
    def __init__(self, categories=None, parent=None):
        super().__init__(parent)
        self.categories = categories or []
        self.db = None
        self.init_ui()
        
    def init_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #2a2b38;
                color: white;
            }
            QCheckBox {
                spacing: 8px;
            }
            QComboBox, QSpinBox {
                background-color: #3c3f56;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 5px;
                color: white;
            }
        """)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)
        layout.setAlignment(Qt.AlignTop)  # Прижимаем всё к верху
        
        # Заголовок
        title = QLabel("Настройки уведомлений")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title, alignment=Qt.AlignLeft)
        
        # Настройки уведомлений о товарах
        self.setup_product_notification_settings(layout)
        
        # Кнопки сохранения
        self.setup_action_buttons(layout)
        
        scroll.setWidget(main_widget)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        main_layout.addWidget(scroll)
    
    def setup_product_notification_settings(self, layout):
        """Настройки уведомлений о товарах"""
        product_frame = QFrame()
        product_frame.setStyleSheet("""
            QFrame {
                background-color: #3c3f56;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        product_layout = QVBoxLayout(product_frame)
        product_layout.setSpacing(8)
        product_layout.setAlignment(Qt.AlignTop)

        title = QLabel("Уведомления о товарах")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        product_layout.addWidget(title, alignment=Qt.AlignLeft)

        # Категория товара
        cat_layout = QHBoxLayout()
        cat_label = QLabel("Категория:")
        cat_label.setStyleSheet("font-size: 14px;")
        cat_layout.addWidget(cat_label)
        self.category_combo = QComboBox()
        self.category_combo.addItems(self.categories)
        cat_layout.addWidget(self.category_combo)
        product_layout.addLayout(cat_layout)

        # Минимальное количество
        min_layout = QHBoxLayout()
        min_label = QLabel("Минимальное количество:")
        min_label.setStyleSheet("font-size: 14px;")
        min_layout.addWidget(min_label)
        self.min_quantity_spin = QSpinBox()
        self.min_quantity_spin.setRange(1, 100000)
        self.min_quantity_spin.setValue(1)
        min_layout.addWidget(self.min_quantity_spin)
        product_layout.addLayout(min_layout)

        # Кнопка сохранения
        save_btn = QPushButton("Сохранить настройки")
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        save_btn.clicked.connect(self.save_low_stock_settings)
        product_layout.addWidget(save_btn)

        layout.addWidget(product_frame)
    
    def setup_action_buttons(self, layout):
        """Кнопки действий"""
        btn_layout = QHBoxLayout()
        btn_layout.setAlignment(Qt.AlignLeft)
        
        self.save_btn = QPushButton("Сохранить настройки")
        self.save_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        btn_layout.addWidget(self.save_btn)
        
        self.reset_btn = QPushButton("Сбросить настройки")
        self.reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)
        btn_layout.addWidget(self.reset_btn)
        
        self.delete_history_btn = QPushButton("Удалить историю продаж")
        self.delete_history_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        btn_layout.addWidget(self.delete_history_btn)

        self.delete_products_btn = QPushButton("Удалить все товары")
        self.delete_products_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                padding: 8px 15px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
        """)
        btn_layout.addWidget(self.delete_products_btn)
        
        layout.addLayout(btn_layout)

        # --- Новый обработчик сохранения ---
        self.save_btn.clicked.connect(self.save_low_stock_settings)
        self.delete_history_btn.clicked.connect(self.delete_sales_history)
        self.delete_products_btn.clicked.connect(self.delete_all_products)

    def delete_sales_history(self):
        """Удаляет всю историю продаж"""
        if self.db is None:
            QMessageBox.warning(self, "Ошибка", "Нет подключения к базе данных!")
            return

        reply = QMessageBox.question(
            self,
            'Подтверждение удаления истории',
            'Вы уверены, что хотите удалить всю историю продаж? Это действие нельзя отменить.',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self.db.clear_sales_history()
                QMessageBox.information(self, "Успех", "История продаж успешно удалена.")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить историю продаж: {str(e)}")

    def delete_all_products(self):
        """Удаляет все товары"""
        if self.db is None:
            QMessageBox.warning(self, "Ошибка", "Нет подключения к базе данных!")
            return

        reply = QMessageBox.question(
            self,
            'Подтверждение удаления товаров',
            'Вы уверены, что хотите удалить все товары? Это действие нельзя отменить.',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                self.db.delete_all_products()
                QMessageBox.information(self, "Успех", "Все товары успешно удалены.")
                # Возможно, потребуется обновить каталог или другие связанные виджеты
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось удалить товары: {str(e)}")

    def save_low_stock_settings(self):
        if self.db is None:
            QMessageBox.warning(self, "Ошибка", "Нет подключения к базе данных!")
            return

        try:
            category = self.category_combo.currentText()
            min_quantity = int(self.min_quantity_spin.value())
            
            # Сохраняем минимальное количество для категории
            if self.db.set_category_min_quantity(category, min_quantity):
                QMessageBox.information(
                    self, 
                    "Успех", 
                    f"Минимальное количество для категории '{category}' установлено: {min_quantity}"
                )
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось сохранить настройки!")
                
        except Exception as e:
            print(f"Ошибка при сохранении настроек: {str(e)}")
            QMessageBox.critical(self, "Ошибка", f"Произошла ошибка при сохранении настроек: {str(e)}")

    def set_db(self, db):
        self.db = db