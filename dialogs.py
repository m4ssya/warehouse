from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QLineEdit, QComboBox, QFileDialog, QMessageBox, QFrame, QWidget, QTableWidget, QHeaderView, QDateEdit, QTableWidgetItem
)
from PyQt5.QtCore import Qt, QPoint, QRectF, QPropertyAnimation, QDate
from PyQt5.QtGui import QPixmap, QPainter, QPainterPath, QIcon, QColor, QIntValidator, QDoubleValidator
from PyQt5.QtWidgets import QGraphicsOpacityEffect
import logging
import random
import time
import smtplib
from email.mime.text import MIMEText
import traceback
import bcrypt
from PyQt5.QtCore import QTimer

logging.basicConfig(filename="debug.log", level=logging.DEBUG, filemode="a")

class BaseDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.radius = 28
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setStyleSheet("""
            QDialog {
                background-color: #353a5c;
                color: #f5f6fa;
                border-radius: 28px;
                border: none;
                padding: 28px;
            }
            QLineEdit, QComboBox {
                background-color: #23243a;
                border: none;
                border-radius: 18px;
                padding: 10px 14px;
                color: white;
                font-size: 15px;
                margin-bottom: 10px;
            }
            QPushButton {
                border-radius: 18px;
            }
        """)
        # Анимация появления/исчезновения
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(300)
        self.fade_anim.finished.connect(self._on_fade_finished)
        self._is_closing = False

    def showEvent(self, event):
        self._is_closing = False
        self.opacity_effect.setOpacity(0)
        self.fade_anim.stop()
        self.fade_anim.setStartValue(0)
        self.fade_anim.setEndValue(1)
        self.fade_anim.start()
        super().showEvent(event)

    def closeEvent(self, event):
        if not self._is_closing:
            event.ignore()
            self._is_closing = True
            self.fade_anim.stop()
            self.fade_anim.setStartValue(1)
            self.fade_anim.setEndValue(0)
            self.fade_anim.start()
        else:
            super().closeEvent(event)

    def _on_fade_finished(self):
        if self._is_closing:
            super().close()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, self.radius, self.radius)
        painter.fillPath(path, QColor('#353a5c'))
        super().paintEvent(event)

    def mousePressEvent(self, event):
        # Если клик вне области окна — закрыть окно
        if not self.rect().contains(event.pos()):
            self.close()
        else:
            super().mousePressEvent(event)

class AddItemDialog(BaseDialog):
    def __init__(self, parent=None, categories=None):
        logging.debug("AddItemDialog: init start")
        super().__init__(parent)
        self.setWindowTitle("Добавить товар")
        self.setFixedSize(540, 700)  # Ещё больше ширина и высота
        self.image_path = None
        self.setStyleSheet("""
            QDialog {
                background-color: #353a5c;
                color: #f5f6fa;
                border-radius: 28px;
                border: none;
                padding: 28px;
            }
            QLabel {
                color: white;
                font-size: 14px;
                margin-bottom: 10px;
            }
            QLineEdit {
                background-color: #23243a;
                border: none;
                border-radius: 14px;
                padding: 18px 20px;
                color: #f5f6fa;
                font-size: 18px;
                margin-bottom: 32px;
                min-height: 45px;
            }
            QLineEdit::placeholder {
                color: #bfc4d1;
            }
            QComboBox {
                margin-bottom: 32px;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #43e97b, stop:1 #38f9d7);
                color: #23243a;
                border-radius: 14px;
                padding: 10px 24px;
                font-size: 14px;
                border: none;
                margin: 0 8px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #38f9d7, stop:1 #43e97b);
            }
        """)
        self.setup_ui(categories)
        self.apply_styles()
        logging.debug("AddItemDialog: init end")

    def setup_ui(self, categories):
        logging.debug("AddItemDialog: setup_ui start")
        layout = QVBoxLayout(self)
        layout.setSpacing(28)  # Ещё больше вертикальный отступ между элементами

        # Поля ввода
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Название товара")
        self.name_input.setAlignment(Qt.AlignLeft)
        self.name_input.setCursorPosition(0)
        layout.addWidget(self.name_input)

        self.purchase_price_input = QLineEdit()
        self.purchase_price_input.setPlaceholderText("Закупочная цена")
        self.purchase_price_input.setValidator(QDoubleValidator(0, 9999999, 2, self.purchase_price_input))
        layout.addWidget(self.purchase_price_input)

        self.retail_price_input = QLineEdit()
        self.retail_price_input.setPlaceholderText("Розничная цена")
        self.retail_price_input.setValidator(QDoubleValidator(0, 9999999, 2, self.retail_price_input))
        layout.addWidget(self.retail_price_input)

        self.price_input = QLineEdit()
        self.price_input.setPlaceholderText("Цена (устарело, не заполняйте)")
        self.price_input.setValidator(QDoubleValidator(0, 9999999, 2, self.price_input))
        self.price_input.setVisible(False)
        layout.addWidget(self.price_input)

        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText("Количество")
        self.quantity_input.setValidator(QIntValidator(0, 9999999, self.quantity_input))
        layout.addWidget(self.quantity_input)

        # Новое поле для штрихкода
        self.barcode_input = QLineEdit()
        self.barcode_input.setPlaceholderText("Штрихкод (сканируйте или введите)")
        self.barcode_input.setAlignment(Qt.AlignLeft)
        layout.addWidget(self.barcode_input)
        # Чтобы автозаполнить штрихкод при открытии:
        # dialog.barcode_input.setText(штрихкод_или_значение)

        # Выбор категории
        self.category_combo = QComboBox()
        self.category_combo.setPlaceholderText("Выберите категорию")
        if categories:
            self.category_combo.addItems(categories)
        self.category_combo.setEditable(True)
        layout.addWidget(self.category_combo)

        # Кнопка выбора изображения + превью
        img_layout = QHBoxLayout()
        self.image_button = QPushButton(QIcon.fromTheme("image"), " Выбрать изображение")
        self.image_button.setObjectName("Image")
        self.image_button.clicked.connect(self.select_image)
        self.image_button.setStyleSheet("background: #007bff; color: white; border-radius: 14px; padding: 10px 24px; font-size: 16px; border: none; margin: 0 8px;")
        img_layout.addWidget(self.image_button)
        self.image_preview = QLabel()
        self.image_preview.setFixedSize(48, 48)
        self.image_preview.setStyleSheet("border: 1px solid #444; border-radius: 8px; background: #222;")
        img_layout.addWidget(self.image_preview)
        layout.addLayout(img_layout)

        # Кнопки действий
        button_layout = QHBoxLayout()
        self.add_button = QPushButton(QIcon.fromTheme("list-add"), "  Добавить")
        self.add_button.setObjectName("Add")
        self.add_button.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #43e97b, stop:1 #38f9d7); color: #23243a; border-radius: 14px; padding: 10px 24px; font-size: 16px; border: none; margin: 0 8px;")
        self.cancel_button = QPushButton(QIcon.fromTheme("window-close"), "  Отмена")
        self.cancel_button.setObjectName("Cancel")
        self.cancel_button.setStyleSheet("background: #6c757d; color: white; border-radius: 14px; padding: 10px 24px; font-size: 16px; border: none; margin: 0 8px;")
        self.add_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        logging.debug("AddItemDialog: setup_ui end")

    def apply_styles(self):
        self.setStyleSheet("""
            QDialog {
                background-color: #3e4266;
                color: white;
                border-radius: 28px;
                border: none;
                padding: 28px;
            }
            QLineEdit, QComboBox {
                background-color: #50547a;
                border: none;
                border-radius: 14px;
                padding: 16px 18px;
                color: white;
                font-size: 18px;
                margin-bottom: 10px;
                box-shadow: 0 2px 8px 0 rgba(31,38,135,0.10);
            }
            QLineEdit:focus, QComboBox:focus {
                background-color: #5e6390;
            }
            QPushButton {
                padding: 14px 28px;
                border-radius: 14px;
                font-size: 18px;
                border: none;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #6a82fb, stop:1 #fc5c7d);
                color: white;
                font-weight: 500;
                box-shadow: 0 2px 8px 0 rgba(31,38,135,0.10);
                margin: 0 8px;
            }
            QPushButton#Add {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #43e97b, stop:1 #38f9d7);
                color: #23243a;
            }
            QPushButton#Add:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #38f9d7, stop:1 #43e97b);
            }
            QPushButton#Delete {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff5858, stop:1 #f09819);
                color: white;
            }
            QPushButton#Delete:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f09819, stop:1 #ff5858);
            }
            QPushButton#Cancel {
                background: #6c757d;
                color: white;
            }
            QPushButton#Cancel:hover {
                background: #5a6268;
            }
            QPushButton#Image {
                background: #007bff;
                color: white;
            }
            QPushButton#Image:hover {
                background: #0069d9;
            }
        """)

    def select_image(self):
        image_path, _ = QFileDialog.getOpenFileName(
            self, "Выбрать изображение", "", "Image Files (*.png *.jpg *.bmp)"
        )
        if image_path:
            self.image_path = image_path
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                self.image_preview.setPixmap(pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.image_preview.clear()

    def get_item_data(self):
        return (
            self.name_input.text(),
            self.purchase_price_input.text(),
            self.retail_price_input.text(),
            self.quantity_input.text(),
            self.image_path,
            self.category_combo.currentText(),
            self.barcode_input.text()
        )

class EditItemDialog(AddItemDialog):
    def __init__(self, parent=None, product=None, categories=None):
        logging.debug("EditItemDialog: init start")
        super().__init__(parent, categories)
        self.setWindowTitle("Редактировать товар")
        self.product = product
        self.load_product_data()
        logging.debug("EditItemDialog: init end")

    def load_product_data(self):
        self.name_input.setText(self.product["name"])
        if "retail_price" in self.product:
            self.price_input.setText(self.product["retail_price"])
        else:
            self.price_input.setText(self.product["price"])
        self.quantity_input.setText(self.product["quantity"])
        if self.product["category"] != "Без категории":
            self.category_combo.setCurrentText(self.product["category"])
        self.image_path = self.product["image"]
        if "barcode" in self.product:
            self.barcode_input.setText(self.product["barcode"])
        if "purchase_price" in self.product:
            self.purchase_price_input.setText(self.product["purchase_price"])
        if "retail_price" in self.product:
            self.retail_price_input.setText(self.product["retail_price"])

    def get_updated_data(self):
        data = {
            "name": self.name_input.text().strip(),
            "purchase_price": self.purchase_price_input.text().strip(),
            "retail_price": self.retail_price_input.text().strip(),
            "quantity": self.quantity_input.text().strip(),
            "image": self.image_path,
            "category": self.category_combo.currentText(),
            "barcode": self.barcode_input.text().strip(),
        }
        # price всегда равен retail_price для совместимости
        data["price"] = data["retail_price"]
        return data

class AddCategoryDialog(BaseDialog):
    def __init__(self, parent=None):
        logging.debug("AddCategoryDialog: init start")
        super().__init__(parent)
        self.setWindowTitle("Добавить категорию")
        self.setFixedSize(400, 220)
        self.setup_ui()
        logging.debug("AddCategoryDialog: init end")

    def setup_ui(self):
        logging.debug("AddCategoryDialog: setup_ui start")
        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Название категории")
        self.name_input.setStyleSheet("background-color: #23243a; border: none; border-radius: 18px; padding: 10px 14px; color: white; font-size: 15px; margin-bottom: 10px;")
        layout.addWidget(self.name_input)
        button_layout = QHBoxLayout()
        self.add_button = QPushButton(QIcon.fromTheme("list-add"), "  Добавить")
        self.add_button.setObjectName("Add")
        self.add_button.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #43e97b, stop:1 #38f9d7); color: #23243a; border-radius: 18px; padding: 10px 24px; font-size: 16px; border: none; margin: 0 8px;")
        self.cancel_button = QPushButton(QIcon.fromTheme("window-close"), "  Отмена")
        self.cancel_button.setObjectName("Cancel")
        self.cancel_button.setStyleSheet("background: #6c757d; color: white; border-radius: 18px; padding: 10px 24px; font-size: 16px; border: none; margin: 0 8px;")
        self.add_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        logging.debug("AddCategoryDialog: setup_ui end")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, 28, 28)
        painter.fillPath(path, QColor('#353a5c'))
        super().paintEvent(event)

    def get_category_name(self):
        return self.name_input.text()

class DeleteCategoryDialog(BaseDialog):
    def __init__(self, parent=None, categories=None):
        logging.debug("DeleteCategoryDialog: init start")
        super().__init__(parent)
        self.setWindowTitle("Удалить категорию")
        self.setFixedSize(400, 260)
        self.setup_ui(categories)
        logging.debug("DeleteCategoryDialog: init end")

    def setup_ui(self, categories):
        logging.debug("DeleteCategoryDialog: setup_ui start")
        layout = QVBoxLayout(self)
        layout.setSpacing(18)
        self.label = QLabel("<b>Выберите категорию для удаления:</b>")
        layout.addWidget(self.label)
        self.category_combo = QComboBox()
        if categories:
            self.category_combo.addItems(categories)
        self.category_combo.setStyleSheet("background-color: #23243a; border: none; border-radius: 18px; padding: 10px 14px; color: white; font-size: 15px; margin-bottom: 10px;")
        layout.addWidget(self.category_combo)
        self.warning_label = QLabel(
            "<span style='color:#ffc107;'>Внимание: Все товары этой категории будут перемещены в 'Без категории'</span>"
        )
        self.warning_label.setWordWrap(True)
        layout.addWidget(self.warning_label)
        button_layout = QHBoxLayout()
        self.delete_button = QPushButton(QIcon.fromTheme("edit-delete"), "  Удалить")
        self.delete_button.setObjectName("Delete")
        self.delete_button.setStyleSheet("background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #ff5858, stop:1 #f09819); color: white; border-radius: 18px; padding: 10px 24px; font-size: 16px; border: none; margin: 0 8px;")
        self.cancel_button = QPushButton(QIcon.fromTheme("window-close"), "  Отмена")
        self.cancel_button.setObjectName("Cancel")
        self.cancel_button.setStyleSheet("background: #6c757d; color: white; border-radius: 18px; padding: 10px 24px; font-size: 16px; border: none; margin: 0 8px;")
        self.delete_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.delete_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)
        logging.debug("DeleteCategoryDialog: setup_ui end")

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, 28, 28)
        painter.fillPath(path, QColor('#353a5c'))
        super().paintEvent(event)

    def get_selected_category(self):
        return self.category_combo.currentText()

class PasswordResetDialog(BaseDialog):
    def __init__(self, db, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("Восстановление пароля")
        self.setFixedSize(400, 600)  # Увеличиваем высоту окна для больших отступов
        self.setStyleSheet("""
            QDialog {
                background-color: #353a5c;
                color: #f5f6fa;
                border-radius: 28px;
                border: none;
                padding: 28px;
            }
            QLabel {
                color: white;
                font-size: 16px;
                margin-bottom: 10px;
            }
            QLineEdit {
                background-color: #23243a;
                border: none;
                border-radius: 14px;
                padding: 14px 20px;
                color: #f5f6fa;
                font-size: 18px;
                margin-bottom: 35px;  /* Значительно увеличиваем отступ между полями */
                min-height: 45px;
            }
            QLineEdit::placeholder {
                color: #bfc4d1;
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #43e97b, stop:1 #38f9d7);
                color: #23243a;
                border-radius: 14px;
                padding: 10px 20px;
                font-size: 16px;
                border: none;
                margin: 8px;
                min-height: 38px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #38f9d7, stop:1 #43e97b);
            }
        """)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)

        # Заголовок
        title = QLabel("Восстановление пароля")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: white; margin-bottom: 40px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Поля ввода
        self.username_edit = QLineEdit()
        self.username_edit.setPlaceholderText("Введите логин")
        layout.addWidget(self.username_edit)

        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("Введите email")
        layout.addWidget(self.email_edit)

        self.new_password_edit = QLineEdit()
        self.new_password_edit.setPlaceholderText("Новый пароль")
        self.new_password_edit.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.new_password_edit)

        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("Подтвердите пароль")
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.confirm_password_input)

        layout.addSpacing(25)

        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.reset_button = QPushButton("Изменить пароль")
        self.reset_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #43e97b, stop:1 #38f9d7);
                color: #23243a;
                border-radius: 14px;
                padding: 12px 24px;
                font-size: 16px;
                border: none;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #38f9d7, stop:1 #43e97b);
            }
        """)
        self.reset_button.clicked.connect(self.reset_password)
        button_layout.addWidget(self.reset_button)

        button_layout.addSpacing(20) # Добавляем отступ между кнопками

        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background: #6c757d;
                color: white;
                border-radius: 14px;
                padding: 12px 24px;
                font-size: 16px;
                border: none;
            }
            QPushButton:hover {
                background: #5a6268;
            }
        """)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        button_layout.addStretch()

        layout.addLayout(button_layout)

        # Статус
        self.status_label = QLabel()
        self.status_label.setStyleSheet("color: #ffc107; font-size: 14px; margin-top: 15px;")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def reset_password(self):
        username = self.username_edit.text().strip()
        email = self.email_edit.text().strip()
        new_password = self.new_password_edit.text()
        confirm_password = self.confirm_password_input.text()

        if not all([username, email, new_password, confirm_password]):
            self.status_label.setText("Заполните все поля")
            return

        if new_password != confirm_password:
            self.status_label.setText("Пароли не совпадают")
            return

        # Проверяем существование пользователя с таким логином и email
        self.db.cursor.execute(
            "SELECT username FROM users WHERE username = %s AND email = %s",
            (username, email)
        )
        user = self.db.cursor.fetchone()
        
        if not user:
            self.status_label.setText("Неверный логин или email")
            return

        # Хешируем новый пароль
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), salt)
        
        try:
            # Обновляем пароль в базе
            self.db.cursor.execute(
                "UPDATE users SET password = %s WHERE username = %s AND email = %s",
                (hashed_password.decode('utf-8'), username, email)
            )
            self.db.connection.commit()

            self.status_label.setText("Пароль успешно изменен")
            self.status_label.setStyleSheet("color: #28a745;")
            self.reset_button.setEnabled(False)
            
            # Закрываем окно через 3 секунды
            QTimer.singleShot(3000, self.accept)
            
        except Exception as e:
            self.status_label.setText(f"Ошибка: {str(e)}")
            self.db.connection.rollback()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)

class ProductMovementHistoryDialog(QDialog):
    def __init__(self, db, product_id=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.product_id = product_id
        self.setWindowTitle("История движения товара")
        self.setModal(True)
        self.setMinimumSize(800, 600)
        self.setup_ui()
        self.load_history()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Фильтры
        filter_layout = QHBoxLayout()
        
        # Выбор товара
        self.product_combo = QComboBox()
        self.product_combo.setMinimumWidth(200)
        self.load_products()
        if self.product_id:
            self.product_combo.setCurrentIndex(self.product_combo.findData(self.product_id))
        filter_layout.addWidget(QLabel("Товар:"))
        filter_layout.addWidget(self.product_combo)

        # Период
        self.start_date = QDateEdit()
        self.start_date.setCalendarPopup(True)
        self.start_date.setDate(QDate.currentDate().addMonths(-1))
        self.end_date = QDateEdit()
        self.end_date.setCalendarPopup(True)
        self.end_date.setDate(QDate.currentDate())
        
        filter_layout.addWidget(QLabel("С:"))
        filter_layout.addWidget(self.start_date)
        filter_layout.addWidget(QLabel("По:"))
        filter_layout.addWidget(self.end_date)

        # Кнопка обновления
        self.refresh_btn = QPushButton("Обновить")
        self.refresh_btn.clicked.connect(self.load_history)
        filter_layout.addWidget(self.refresh_btn)

        # Фейковая кнопка 'Составить отчёт'
        self.fake_report_btn = QPushButton("Составить отчёт")
        self.fake_report_btn.setEnabled(False)
        filter_layout.addWidget(self.fake_report_btn)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Таблица истории
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(9)
        self.history_table.setHorizontalHeaderLabels([
            "Дата", "Название товара", "Категория", "Тип операции", "Количество", "Было", "Стало",
            "Пользователь", "Комментарий"
        ])
        header = self.history_table.horizontalHeader()
        for i in range(9):
            if i == 8:
                header.setSectionResizeMode(i, QHeaderView.Stretch)
            else:
                header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        
        layout.addWidget(self.history_table)

        # Кнопки
        button_layout = QHBoxLayout()
        self.close_btn = QPushButton("Закрыть")
        self.close_btn.clicked.connect(self.accept)
        button_layout.addStretch()
        button_layout.addWidget(self.close_btn)
        layout.addLayout(button_layout)

    def load_products(self):
        self.db.cursor.execute("SELECT id, name FROM products ORDER BY name")
        products = self.db.cursor.fetchall()
        self.product_combo.clear()
        self.product_combo.addItem("Все товары", None)
        for product_id, name in products:
            self.product_combo.addItem(name, product_id)

    def load_history(self):
        self.refresh_btn.setEnabled(False)
        try:
            product_id = self.product_combo.currentData()
            start_date = self.start_date.date().toString("yyyy-MM-dd")
            end_date = self.end_date.date().toString("yyyy-MM-dd")
            history = self.db.get_product_movement_history(
                product_id=product_id,
                start_date=start_date,
                end_date=end_date
            )
            self.history_table.setRowCount(len(history))
            for row, movement in enumerate(history):
                # Форматируем дату: только дата и часы:минуты
                raw_dt = str(movement['movement_date'])
                try:
                    # Если это datetime-объект
                    from datetime import datetime
                    if isinstance(movement['movement_date'], datetime):
                        dt_str = movement['movement_date'].strftime('%Y-%m-%d %H:%M')
                    else:
                        dt_str = raw_dt[:16] if len(raw_dt) >= 16 else raw_dt
                except Exception:
                    dt_str = raw_dt[:16] if len(raw_dt) >= 16 else raw_dt
                self.history_table.setItem(row, 0, QTableWidgetItem(dt_str))
                self.history_table.setItem(row, 1, QTableWidgetItem(movement.get('product_name', '')))
                self.history_table.setItem(row, 2, QTableWidgetItem(movement.get('product_category', '')))
                type_text = "Поступление" if movement['movement_type'] == 'IN' else "Списание"
                self.history_table.setItem(row, 3, QTableWidgetItem(type_text))
                self.history_table.setItem(row, 4, QTableWidgetItem(str(movement['quantity'])))
                self.history_table.setItem(row, 5, QTableWidgetItem(str(movement['previous_quantity'])))
                self.history_table.setItem(row, 6, QTableWidgetItem(str(movement['new_quantity'])))
                self.history_table.setItem(row, 7, QTableWidgetItem(movement['username']))
                self.history_table.setItem(row, 8, QTableWidgetItem(movement['comment'] or ""))
        finally:
            self.refresh_btn.setEnabled(True)