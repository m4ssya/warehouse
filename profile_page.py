from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QPushButton, 
                            QFormLayout, QFrame, QScrollArea, QFileDialog,
                            QMessageBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QIcon, QPainter, QPainterPath
import os
from PIL import Image, ImageQt
from app_code.database import DatabaseManager

class ProfilePage(QWidget):
    def __init__(self, username, role, parent=None):
        super().__init__(parent)
        self.username = username
        self.role = role
        self.db = DatabaseManager()
        self.photo_path = None
        self.init_ui()
        self.load_profile()
        
    def init_ui(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #2a2b38;
                color: white;
            }
            QLineEdit {
                background-color: #3c3f56;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 8px;
                color: white;
            }
            QPushButton {
                background-color: #007bff;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #0056b3;
            }
            QPushButton#deleteButton {
                background-color: #dc3545;
            }
            QPushButton#deleteButton:hover {
                background-color: #bd2130;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 2, 20, 8)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignTop)
        
        # Заголовок
        title = QLabel("Личный кабинет")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        # Профиль пользователя
        self.setup_profile_section(layout)
        
        # Настройки безопасности
        self.setup_security_section(layout)
        
        self.setLayout(layout)
    
    def setup_profile_section(self, layout):
        """Настройка секции профиля"""
        profile_frame = QFrame()
        profile_frame.setStyleSheet("""
            QFrame {
                background-color: #3c3f56;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        
        profile_layout = QVBoxLayout(profile_frame)
        profile_layout.setContentsMargins(15, 15, 15, 15)
        profile_layout.setSpacing(15)
        
        # Аватар и основная информация
        top_layout = QHBoxLayout()
        
        # Аватар
        AVATAR_SIZE = 120
        self.avatar_frame = QFrame()
        self.avatar_frame.setFixedSize(AVATAR_SIZE, AVATAR_SIZE)
        self.avatar_frame.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                border-radius: {AVATAR_SIZE//2}px;
                /* border: 2px solid #555; */
            }}
        """)
        self.avatar_label = QLabel(self.avatar_frame)
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self.avatar_label.setGeometry(0, 0, AVATAR_SIZE, AVATAR_SIZE)
        self.avatar_label.setStyleSheet("background: transparent; border: none;")
        self.avatar_size = AVATAR_SIZE
        self.update_avatar()
        top_layout.addWidget(self.avatar_frame)
        
        # Основная информация
        info_layout = QVBoxLayout()
        
        # Имя пользователя
        name_layout = QHBoxLayout()
        name_label = QLabel("Имя:")
        name_label.setStyleSheet("font-size: 14px;")
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Введите ваше имя")
        self.name_edit.setStyleSheet("""
            QLineEdit {
                background-color: #454862;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px;
                color: white;
                font-size: 14px;
            }
        """)
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_edit)
        info_layout.addLayout(name_layout)
        
        # Email
        email_layout = QHBoxLayout()
        email_label = QLabel("Email:")
        email_label.setStyleSheet("font-size: 14px;")
        self.email_edit = QLineEdit()
        self.email_edit.setPlaceholderText("Введите ваш email")
        self.email_edit.setStyleSheet("""
            QLineEdit {
                background-color: #454862;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px;
                color: white;
                font-size: 14px;
            }
        """)
        email_layout.addWidget(email_label)
        email_layout.addWidget(self.email_edit)
        info_layout.addLayout(email_layout)
        
        # Логин
        login_label = QLabel(f"Логин: {self.username}")
        login_label.setStyleSheet("color: #aaa; font-size: 14px;")
        info_layout.addWidget(login_label)
        
        # Роль
        role_label = QLabel(f"Роль: {self.role}")
        role_label.setStyleSheet("color: #aaa; font-size: 14px;")
        info_layout.addWidget(role_label)
        
        top_layout.addLayout(info_layout)
        top_layout.addStretch()
        profile_layout.addLayout(top_layout)
        
        # Кнопки управления фото
        photo_buttons_layout = QHBoxLayout()
        
        upload_btn = QPushButton("Загрузить фото")
        upload_btn.clicked.connect(self.choose_photo)
        photo_buttons_layout.addWidget(upload_btn)
        
        delete_photo_btn = QPushButton("Удалить фото")
        delete_photo_btn.setObjectName("deleteButton")
        delete_photo_btn.clicked.connect(self.delete_photo)
        photo_buttons_layout.addWidget(delete_photo_btn)
        
        profile_layout.addLayout(photo_buttons_layout)
        
        # Кнопка сохранения
        save_btn = QPushButton("Сохранить изменения")
        save_btn.clicked.connect(self.save_profile)
        profile_layout.addWidget(save_btn)
        
        layout.addWidget(profile_frame)

    def setup_security_section(self, layout):
        """Настройка секции безопасности"""
        security_frame = QFrame()
        security_frame.setStyleSheet("""
            QFrame {
                background-color: #3c3f56;
                border-radius: 8px;
                padding: 15px;
            }
        """)
        
        security_layout = QVBoxLayout(security_frame)
        security_layout.setContentsMargins(15, 15, 15, 15)
        security_layout.setSpacing(15)
        
        title = QLabel("Безопасность")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        security_layout.addWidget(title)
        
        # Форма смены пароля
        form_layout = QFormLayout()
        form_layout.setHorizontalSpacing(20)
        form_layout.setVerticalSpacing(10)
        
        self.current_pass_edit = QLineEdit()
        self.current_pass_edit.setPlaceholderText("Текущий пароль")
        self.current_pass_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Текущий пароль:", self.current_pass_edit)
        
        self.new_pass_edit = QLineEdit()
        self.new_pass_edit.setPlaceholderText("Новый пароль")
        self.new_pass_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Новый пароль:", self.new_pass_edit)
        
        self.confirm_pass_edit = QLineEdit()
        self.confirm_pass_edit.setPlaceholderText("Подтверждение")
        self.confirm_pass_edit.setEchoMode(QLineEdit.Password)
        form_layout.addRow("Подтверждение:", self.confirm_pass_edit)
        
        security_layout.addLayout(form_layout)
        
        # Кнопка смены пароля
        change_pass_btn = QPushButton("Изменить пароль")
        change_pass_btn.clicked.connect(self.change_password)
        security_layout.addWidget(change_pass_btn)
        
        layout.addWidget(security_frame)

    def load_profile(self):
        """Загрузка данных профиля"""
        profile = self.db.get_user_profile(self.username)
        if profile:
            if profile["name"]:
                self.name_edit.setText(profile["name"])
            if profile["email"]:
                self.email_edit.setText(profile["email"])
            if profile["photo_path"]:
                self.photo_path = profile["photo_path"]
                self.update_avatar()

    def save_profile(self):
        """Сохранение изменений профиля"""
        name = self.name_edit.text().strip()
        email = self.email_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Ошибка", "Имя не может быть пустым.")
            return
        if email and ("@" not in email or "." not in email):
            QMessageBox.warning(self, "Ошибка", "Некорректный email.")
            return
        if self.db.update_user_profile(self.username, name=name, photo_path=self.photo_path, email=email):
            QMessageBox.information(self, "Успех", "Профиль успешно обновлен")
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось обновить профиль")

    def change_password(self):
        """Изменение пароля"""
        current_pass = self.current_pass_edit.text()
        new_pass = self.new_pass_edit.text()
        confirm_pass = self.confirm_pass_edit.text()
        
        if not current_pass or not new_pass or not confirm_pass:
            QMessageBox.warning(self, "Ошибка", "Все поля должны быть заполнены")
            return
        
        if new_pass != confirm_pass:
            QMessageBox.warning(self, "Ошибка", "Новые пароли не совпадают")
            return
        
        # Проверяем текущий пароль
        if not self.db.authenticate_user(self.username, current_pass):
            QMessageBox.warning(self, "Ошибка", "Неверный текущий пароль")
            return
        
        if self.db.update_user_password(self.username, new_pass):
            QMessageBox.information(self, "Успех", "Пароль успешно изменен")
            self.current_pass_edit.clear()
            self.new_pass_edit.clear()
            self.confirm_pass_edit.clear()
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось изменить пароль")

    def update_avatar(self):
        """Обновление отображения аватара"""
        size = getattr(self, 'avatar_size', 120)
        self.avatar_label.setFixedSize(size, size)
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self.avatar_label.setStyleSheet("background: transparent; border: none;")
        if self.photo_path and os.path.exists(self.photo_path):
            try:
                pil_img = Image.open(self.photo_path).convert('RGBA')
                qt_img = ImageQt.ImageQt(pil_img)
                src = QPixmap.fromImage(qt_img)
            except Exception:
                src = QPixmap(self.photo_path)
            # Масштабируем с заполнением круга
            scaled = src.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            # Центрируем и обрезаем по кругу
            x = (scaled.width() - size) // 2
            y = (scaled.height() - size) // 2
            cropped = scaled.copy(x, y, size, size)
            mask = QPixmap(size, size)
            mask.fill(Qt.transparent)
            painter = QPainter(mask)
            painter.setRenderHint(QPainter.Antialiasing)
            path = QPainterPath()
            path.addEllipse(0, 0, size, size)
            painter.setClipPath(path)
            painter.drawPixmap(0, 0, cropped)
            painter.end()
            self.avatar_label.setPixmap(mask)
            self.avatar_label.setText("")
            self.avatar_label.repaint()
        else:
            # Показываем только круг с иконкой или текстом внутри
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            # Круг
            pen = painter.pen()
            pen.setWidth(3)
            pen.setColor(Qt.gray)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(0, 0, size-1, size-1)
            # Текст по центру круга
            painter.setPen(Qt.gray)
            font = painter.font()
            font.setPointSize(13)
            painter.setFont(font)
            painter.drawText(pixmap.rect(), Qt.AlignCenter, "Нет\nфото")
            painter.end()
            self.avatar_label.setPixmap(pixmap)
            self.avatar_label.setText("")

    def choose_photo(self):
        """Выбор фотографии"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выбрать фото",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if file_path:
            self.photo_path = file_path
            # Сохраняем фото в БД
            try:
                with open(file_path, 'rb') as f:
                    image_bytes = f.read()
                self.db.update_user_photo(self.username, image_bytes)
            except Exception as e:
                print(f"Ошибка при сохранении фото в БД: {e}")
            self.update_avatar()

    def delete_photo(self):
        """Удаление фотографии"""
        if self.photo_path:
            self.photo_path = None
            # Удаляем фото из БД
            try:
                self.db.update_user_photo(self.username, None)
            except Exception as e:
                print(f"Ошибка при удалении фото из БД: {e}")
            self.update_avatar()