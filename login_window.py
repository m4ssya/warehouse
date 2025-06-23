import sys
import os
import bcrypt
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from PyQt5.QtCore import Qt, QSettings, QPropertyAnimation, QEasingCurve, QPoint, QSize, QTimer
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, 
                            QLineEdit, QPushButton, QFrame, QMessageBox, QComboBox, 
                            QToolTip, QCheckBox, QGraphicsOpacityEffect)
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter, QPainterPath, QColor, QLinearGradient
from app_code.database import DatabaseManager
from app_code.dialogs import PasswordResetDialog

def register_user(username, password, role, email, db=None):
    if db is None:
        db = DatabaseManager()
        should_close = True
    else:
        should_close = False
        
    try:
        print("\n=== Регистрация нового пользователя ===")
        print(f"Логин: {username}")
        print(f"Email: {email}")
        print(f"Роль: {role}")
        
        users = db.get_all_users()
        if any(user['username'] == username for user in users):
            print("Ошибка: Пользователь с таким логином уже существует")
            return 'username'
        if any(user.get('email') == email for user in users):
            print("Ошибка: Пользователь с таким email уже существует")
            return 'email'
        
        # Хешируем пароль
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
        print(f"Сгенерированная соль: {salt}")
        print(f"Хеш пароля: {hashed_password.decode('utf-8')}")
        
        db.cursor.execute(
            "INSERT INTO users (username, password, role, email) VALUES (%s, %s, %s, %s)",
            (username, hashed_password.decode('utf-8'), role.lower(), email)
        )
        db.connection.commit()
        print("Пользователь успешно зарегистрирован!")
        return True
    except Exception as e:
        print(f"Ошибка при регистрации пользователя: {e}")
        return False
    finally:
        if should_close:
            db.close()

def authenticate_user(login_or_email, password, db=None):
    if db is None:
        db = DatabaseManager()
        should_close = True
    else:
        should_close = False
        
    try:
        print("\n=== Попытка входа ===")
        print(f"Логин/Email: {login_or_email}")
        
        # Получаем пользователя по логину или email
        db.cursor.execute( 
            "SELECT username, password, role FROM users WHERE username = %s OR email = %s",
            (login_or_email, login_or_email)
        )
        user = db.cursor.fetchone()
        
        if user:
            print(f"Найден пользователь: {user[0]}")
            print(f"Хеш пароля в БД: {user[1]}")
            
            # Проверяем пароль
            password_check = bcrypt.checkpw(password.encode('utf-8'), user[1].encode('utf-8'))
            print(f"Результат проверки пароля: {password_check}")
            
            if password_check:
                print("Аутентификация успешна!")
                return (user[0], user[2])  # username, role
            else:
                print("Неверный пароль")
        else:
            print("Пользователь не найден")
        return None
    finally:
        if should_close:
            db.close()

class ModernLineEdit(QLineEdit):
    def __init__(self, placeholder="", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setStyleSheet("""
            QLineEdit {
                background-color: rgba(59, 60, 79, 0.8);
                border: 2px solid rgba(85, 85, 85, 0.3);
                border-radius: 8px;
                padding: 12px;
                color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #28a745;
                background-color: rgba(59, 60, 79, 0.9);
            }
        """)
        self.setMinimumHeight(45)

class ModernButton(QPushButton):
    def __init__(self, text, color="#28a745", parent=None):
        super().__init__(text, parent)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self._adjust_color(color, -20)};
            }}
            QPushButton:pressed {{
                background-color: {self._adjust_color(color, -30)};
            }}
        """)
        self.setMinimumHeight(45)
        self.setCursor(Qt.PointingHandCursor)

    def _adjust_color(self, color, amount):
        # Преобразуем цвет в RGB и корректируем яркость
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        r = max(0, min(255, r + amount))
        g = max(0, min(255, g + amount))
        b = max(0, min(255, b + amount))
        return f"#{r:02x}{g:02x}{b:02x}"

class RegisterWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Регистрация")
        self.setFixedSize(400, 450)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.db = DatabaseManager()  # Создаем одно соединение для всего окна
        self.setup_ui()
        self.setup_animations()

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

    def setup_animations(self):
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(300)
        self.fade_anim.setStartValue(0)
        self.fade_anim.setEndValue(1)
        self.fade_anim.start()

    def setup_ui(self):
        from PyQt5.QtCore import QTimer
        self._msg_timer = QTimer(self)
        self._msg_timer.setSingleShot(True)
        self._msg_timer.timeout.connect(self.hide_message)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.container = QFrame()
        self.container.setStyleSheet("""
            QFrame {
                background-color: #2a2b38;
                border-radius: 12px;
            }
        """)
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(40, 40, 40, 40)
        container_layout.setSpacing(20)

        title = QLabel("Регистрация")
        title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: white;
            margin-bottom: 10px;
        """)
        title.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(title)

        self.username = ModernLineEdit("Логин")
        container_layout.addWidget(self.username)

        self.password = ModernLineEdit("Пароль")
        self.password.setEchoMode(QLineEdit.Password)
        container_layout.addWidget(self.password)

        self.email = ModernLineEdit("Email")
        container_layout.addWidget(self.email)

        self.role_combo = QComboBox()
        self.role_combo.addItem("Пользователь")
        self.role_combo.addItem("Администратор")
        self.role_combo.setStyleSheet("""
            QComboBox {
                background-color: rgba(59, 60, 79, 0.8);
                border: 2px solid rgba(85, 85, 85, 0.3);
                border-radius: 8px;
                padding: 12px;
                color: white;
                font-size: 14px;
                min-height: 45px;
            }
            QComboBox:focus {
                border: 2px solid #28a745;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: url(down_arrow.png);
                width: 12px;
                height: 12px;
            }
        """)
        container_layout.addWidget(self.role_combo)

        self.register_btn = ModernButton("Зарегистрировать", "#007bff")
        self.register_btn.clicked.connect(self.register_user)
        container_layout.addWidget(self.register_btn)

        self.back_btn = ModernButton("Назад", "#6c757d")
        self.back_btn.clicked.connect(self.close)
        container_layout.addWidget(self.back_btn)

        # Сообщение об ошибке/успехе
        self.message_label = QLabel()
        self.message_label.setStyleSheet("font-size: 13px; color: #ff5555; margin-top: 4px;")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setVisible(False)
        container_layout.addWidget(self.message_label)

        main_layout.addStretch()
        main_layout.addWidget(self.container)
        main_layout.addStretch()

    def show_message(self, text, success=False):
        self.message_label.setText(text)
        self.message_label.setStyleSheet(f"font-size: 13px; color: {'#28a745' if success else '#ff5555'}; margin-top: 4px;")
        self.message_label.setVisible(True)
        self._msg_timer.start(3000)

    def hide_message(self):
        self.message_label.setVisible(False)

    def register_user(self):
        username = self.username.text().strip()
        password = self.password.text().strip()
        email = self.email.text().strip()
        role = self.role_combo.currentText()
        if not username or not password or not email:
            self.show_message("Логин, пароль и email не могут быть пустыми.")
            return
        if "@" not in email or "." not in email:
            self.show_message("Некорректный email.")
            return
        result = register_user(username, password, role.lower(), email, self.db)
        if result is True:
            self.show_message("Пользователь успешно зарегистрирован!", success=True)
            self._msg_timer.timeout.connect(self.close)
            self._msg_timer.start(1200)
        elif result == 'username':
            self.show_message("Пользователь с таким логином уже существует.")
        elif result == 'email':
            self.show_message("Пользователь с таким email уже существует.")
        else:
            self.show_message("Ошибка регистрации.")

    def show_info(self, title, message):
        self.show_message(message, success=True)

    def show_error(self, title, message):
        self.show_message(message)

class LoginWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(600, 500)
        self.db = DatabaseManager()  # Создаем одно соединение для всего окна
        self.setup_ui()
        self.setup_animations()
        self.load_remembered()

    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()

    def setup_animations(self):
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.fade_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_anim.setDuration(300)
        self.fade_anim.setStartValue(0)
        self.fade_anim.setEndValue(1)
        self.fade_anim.start()

    def setup_ui(self):
        from PyQt5.QtCore import QTimer
        self._msg_timer = QTimer(self)
        self._msg_timer.setSingleShot(True)
        self._msg_timer.timeout.connect(self.hide_message)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.title_bar = QFrame()
        self.title_bar.setFixedHeight(40)
        self.title_bar.setStyleSheet("""
            background-color: #2a2b38;
            border-top-left-radius: 12px;
            border-top-right-radius: 12px;
        """)

        title_layout = QHBoxLayout(self.title_bar)
        title_layout.setContentsMargins(15, 0, 10, 0)

        self.title_label = QLabel("📦 Складской учёт")
        self.title_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        title_layout.addWidget(self.title_label)

        title_layout.addStretch()

        for btn_text, btn_color in [("—", "#aaa"), ("□", "#aaa"), ("✕", "#ff5555")]:
            btn = QPushButton(btn_text)
            btn.setFixedSize(30, 30)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    border: none;
                    color: {btn_color};
                    font-size: 14px;
                }}
                QPushButton:hover {{
                    background-color: rgba(255, 255, 255, 0.1);
                    border-radius: 4px;
                }}
            """)
            if btn_text == "—":
                btn.clicked.connect(self.showMinimized)
            elif btn_text == "□":
                btn.clicked.connect(self.toggle_max_restore)
            else:
                btn.clicked.connect(self.close)
            title_layout.addWidget(btn)

        main_layout.addWidget(self.title_bar)

        self.container = QFrame()
        self.container.setStyleSheet("""
            QFrame {
                background-color: #2a2b38;
                border-bottom-left-radius: 12px;
                border-bottom-right-radius: 12px;
            }
        """)
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(40, 40, 40, 40)
        container_layout.setSpacing(20)

        title = QLabel("Авторизация")
        title.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: white;
            margin-bottom: 10px;
        """)
        title.setAlignment(Qt.AlignCenter)
        container_layout.addWidget(title)

        self.username_input = ModernLineEdit("Логин или Email")
        container_layout.addWidget(self.username_input)

        self.password_input = ModernLineEdit("Пароль")
        self.password_input.setEchoMode(QLineEdit.Password)
        container_layout.addWidget(self.password_input)

        # Кнопка 'Забыл пароль'
        self.forgot_button = ModernButton("Забыли пароль?", "#ffc107")
        self.forgot_button.clicked.connect(self.forgot_password)
        container_layout.addWidget(self.forgot_button)

        self.remember_checkbox = QCheckBox("Запомнить меня")
        self.remember_checkbox.setStyleSheet("""
            QCheckBox {
                color: #aaa;
                font-size: 13px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #555;
                border-radius: 4px;
            }
            QCheckBox::indicator:checked {
                background-color: #28a745;
                border: 2px solid #28a745;
            }
        """)
        container_layout.addWidget(self.remember_checkbox)

        self.login_button = ModernButton("Войти", "#28a745")
        self.login_button.clicked.connect(self.login_user)
        container_layout.addWidget(self.login_button)

        self.register_button = ModernButton("Регистрация", "#007bff")
        self.register_button.clicked.connect(self.open_register_window)
        container_layout.addWidget(self.register_button)

        # Сообщение об ошибке/успехе
        self.message_label = QLabel()
        self.message_label.setStyleSheet("font-size: 13px; color: #ff5555; margin-top: 4px;")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setVisible(False)
        container_layout.addWidget(self.message_label)

        main_layout.addWidget(self.container)

    def show_message(self, text, success=False):
        self.message_label.setText(text)
        self.message_label.setStyleSheet(f"font-size: 13px; color: {'#28a745' if success else '#ff5555'}; margin-top: 4px;")
        self.message_label.setVisible(True)
        self._msg_timer.start(3000)

    def hide_message(self):
        self.message_label.setVisible(False)

    def toggle_max_restore(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()

    def open_register_window(self):
        self.register_win = RegisterWindow()
        self.register_win.show()

    def load_remembered(self):
        # Используем фиксированный ключ для настроек
        settings = QSettings("diplom", "warehouse_login")
        username = settings.value("username", "")
        password = settings.value("password", "")
        remember = settings.value("remember", False, type=bool)
        self.username_input.setText(username)
        self.password_input.setText(password)
        self.remember_checkbox.setChecked(remember)

    def login_user(self):
        login_or_email = self.username_input.text().strip()
        password = self.password_input.text().strip()
        remember = self.remember_checkbox.isChecked()
        if not login_or_email or not password:
            self.show_message("Поля логина/email и пароля не могут быть пустыми.")
            return
        result = authenticate_user(login_or_email, password, self.db)
        if result:
            username, role = result
            # Используем фиксированный ключ для сохранения настроек
            settings = QSettings("diplom", "warehouse_login")
            if remember:
                settings.setValue("username", login_or_email)
                settings.setValue("password", password)
                settings.setValue("remember", True)
            else:
                settings.remove("username")
                settings.remove("password")
                settings.setValue("remember", False)
            self.show_message("Авторизация успешна!", success=True)
            self._msg_timer.timeout.connect(lambda: self.open_main_window(username, role))
            self._msg_timer.start(1200)
        else:
            self.show_message("Неверные данные для входа.")

    def show_info(self, title, message):
        self.show_message(message, success=True)

    def show_error(self, title, message):
        self.show_message(message)

    def open_main_window(self, username, role):
        from app_code.main_window import MainWindow
        self.main_win = MainWindow(username, role)
        self.main_win.show()
        self.close()

    def forgot_password(self):
        dlg = PasswordResetDialog(self.db, self)  # Передаем существующее соединение
        dlg.setWindowModality(Qt.ApplicationModal)
        dlg.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        dlg.move(self.x() + (self.width() - dlg.width()) // 2,
                self.y() + (self.height() - dlg.height()) // 2)
        dlg.exec_()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    QToolTip.setFont(QFont("Segoe UI", 11))
    window = LoginWindow()
    window.show()
    sys.exit(app.exec_())
