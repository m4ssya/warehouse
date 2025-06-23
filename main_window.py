import os
import sys
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QStackedWidget, QGridLayout,
    QPushButton, QFrame, QSizePolicy, QLabel, QListWidget, QListWidgetItem, QMessageBox, QHBoxLayout,
    QScrollArea, QComboBox
)
from PyQt5.QtCore import Qt, QPoint, QPropertyAnimation, QEasingCurve, QRect, QTimer
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QPainterPath, QColor
from PIL import Image, ImageQt
from PyQt5.QtCore import pyqtSignal

from app_code.widgets import SlideMenu, CartDrawer
from app_code.profile_page import ProfilePage
from app_code.settings_page import SettingsPage
from app_code.database import DatabaseManager
from app_code.animations import SlideAnimation
from app_code.catalog_page import StockPage  # Импорт новой страницы
from app_code.sales_history_page import SalesHistoryPage
from app_code.analytics_page import AnalyticsPage  # Добавляем импорт
from app_code.min_quantity_page import MinQuantityPage
from app_code.warehouse_page import WarehousePage
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class CustomTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(38)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setStyleSheet("""
            background-color: #23242a;
            border-top-left-radius: 14px;
            border-top-right-radius: 14px;
        """)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 0, 0, 0)
        # Кнопка меню с иконкой-гамбургером
        self.menu_button = QPushButton()
        self.menu_button.setFixedSize(40, 36)
        self.menu_button.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 0;
            }
            QPushButton:hover {
                background-color: #3c3f56;
                border-radius: 4px;
            }
        """)
        # Рисуем иконку-гамбургер вручную
        pixmap = QPixmap(28, 28)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        pen_color = QColor('#f5f6fa')
        pen_width = 3
        y_offsets = [6, 14, 22]
        for y in y_offsets:
            painter.setPen(QColor('#f5f6fa'))
            painter.setBrush(QColor('#f5f6fa'))
            painter.drawRect(4, y, 20, pen_width)
        painter.end()
        self.menu_button.setIcon(QIcon(pixmap))
        self.menu_button.setIconSize(pixmap.size())
        self.menu_button.clicked.connect(parent.toggle_menu)
        layout.addWidget(self.menu_button)

        # Добавляем QLabel для заголовка
        self.title = QLabel()
        self.title.setStyleSheet("color: #f5f6fa; font-size: 16px; font-weight: bold;")
        self.title.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.title)

        layout.addStretch()

        self.btn_min = QPushButton("—")
        self.btn_min.setFixedSize(28, 28)
        self.btn_min.setStyleSheet("background: none; color: #aaa; border: none; font-size: 18px;")
        self.btn_min.clicked.connect(parent.showMinimized)
        layout.addWidget(self.btn_min)
        self.btn_close = QPushButton("×")
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.setStyleSheet("background: none; color: #f55; border: none; font-size: 18px;")
        self.btn_close.clicked.connect(parent.close)
        layout.addWidget(self.btn_close)
        self._mouse_pos = None

    def mousePressEvent(self, event):
        pass

    def mouseMoveEvent(self, event):
        pass

    def mouseReleaseEvent(self, event):
        pass

class UserCard(QFrame):
    # Сигналы для редактирования, удаления и добавления в корзину
    edit_requested = pyqtSignal(object)
    delete_requested = pyqtSignal(object)
    add_to_cart_requested = pyqtSignal(object)

    def __init__(self, user_data, on_delete, parent=None, on_role_change=None, current_username=None):
        super().__init__(parent)
        self.user_data = user_data
        self.on_delete = on_delete
        self.on_role_change = on_role_change # Store the callback
        self.current_username = current_username
        from app_code.database import DatabaseManager
        self.db = DatabaseManager()
        self.AVATAR_SIZE = 110  # Было 220
        self.setup_ui()
        
    def setup_ui(self):
        self.setStyleSheet("""
            QFrame {
                background-color: #3c3f56;
                border-radius: 16px;
                padding: 12px;
            }
            QFrame:hover {
                background-color: #454862;
            }
        """)
        self.setMinimumWidth(200)
        self.setMaximumWidth(200)
        self.setFixedHeight(400)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(14)
        
        # Аватар
        AVATAR_SIZE = self.AVATAR_SIZE
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(AVATAR_SIZE, AVATAR_SIZE)
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self.avatar_label.setStyleSheet("background: transparent; border: none;")
        self.update_avatar()
        main_layout.addWidget(self.avatar_label, alignment=Qt.AlignCenter)
        main_layout.addSpacing(10)
        
        # Имя пользователя
        name_label = QLabel(self.user_data['name'])
        name_label.setStyleSheet("""
            font-size: 15px;
            font-weight: bold;
            color: white;
        """)
        name_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(name_label)
        
        # Логин
        login_label = QLabel(f"Логин: {self.user_data['username']}")
        login_label.setStyleSheet("font-size: 13px; color: #aaa;")
        login_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(login_label)
        
        # Роль
        role_layout = QHBoxLayout()
        role_label = QLabel("Роль:")
        role_label.setStyleSheet("font-size: 13px; color: #aaa;")
        role_layout.addWidget(role_label)
        
        self.role_combo = QComboBox()
        self.role_combo.addItems(["пользователь", "администратор"])
        self.role_combo.setCurrentText(self.user_data['role'])
        self.role_combo.setStyleSheet("""
            QComboBox {
                background-color: #454862;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 13px;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        role_layout.addWidget(self.role_combo)
        role_layout.addStretch()
        main_layout.addLayout(role_layout)
        
        # Кнопка сохранения роли
        self.save_role_btn = QPushButton("Сохранить роль")
        self.save_role_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 4px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        self.save_role_btn.clicked.connect(self.save_role_clicked)
        main_layout.addWidget(self.save_role_btn)
        
        # Кнопка удаления
        delete_btn = QPushButton("Удалить пользователя")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #bd2130;
            }
        """)
        delete_btn.clicked.connect(lambda: self.on_delete(self.user_data['username']))
        main_layout.addWidget(delete_btn)
        main_layout.addStretch()
        
        # Disable role change for the current user
        if self.current_username and self.user_data['username'] == self.current_username:
            self.role_combo.setEnabled(False)
            self.save_role_btn.setEnabled(False)
        
    def update_avatar(self):
        from PyQt5.QtGui import QPixmap, QPainter, QPainterPath
        from PIL import Image, ImageQt
        import io
        AVATAR_SIZE = self.AVATAR_SIZE
        # Используем photo_data из user_data, если есть
        photo_bytes = self.user_data.get('photo_data')
        print(f"[UserCard] {self.user_data.get('username')}: photo_data type: {type(photo_bytes)}, length: {len(photo_bytes) if photo_bytes else 0}")
        if isinstance(photo_bytes, memoryview):
            photo_bytes = photo_bytes.tobytes()
        if not photo_bytes and hasattr(self, 'db'):
            try:
                photo_bytes = self.db.get_user_photo(self.user_data['username'])
                if isinstance(photo_bytes, memoryview):
                    photo_bytes = photo_bytes.tobytes()
            except Exception:
                photo_bytes = None
        if photo_bytes:
            size = AVATAR_SIZE
            try:
                image = Image.open(io.BytesIO(photo_bytes)).convert('RGBA')
                # Масштабируем с cover
                w, h = image.size
                scale = max(size / w, size / h)
                new_w, new_h = int(w * scale), int(h * scale)
                image = image.resize((new_w, new_h), Image.LANCZOS)
                # Обрезаем центральный квадрат
                left = (new_w - size) // 2
                top = (new_h - size) // 2
                image = image.crop((left, top, left + size, top + size))
                qt_img = ImageQt.ImageQt(image)
                src = QPixmap.fromImage(qt_img)
                # Обрезаем QPixmap по кругу
                final = QPixmap(size, size)
                final.fill(Qt.transparent)
                painter = QPainter(final)
                painter.setRenderHint(QPainter.Antialiasing)
                path = QPainterPath()
                path.addEllipse(0, 0, size, size)
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, src)
                painter.end()
                self.avatar_label.setPixmap(final)
                self.avatar_label.setText("")
                return
            except Exception as e:
                print(f"[UserCard] Ошибка открытия изображения через Pillow: {e}")
                # Пробуем открыть напрямую через QPixmap
                try:
                    src = QPixmap()
                    src.loadFromData(photo_bytes)
                    if not src.isNull():
                        print(f"[UserCard] Изображение открыто через QPixmap: размер={src.width()}x{src.height()}")
                    else:
                        print("[UserCard] QPixmap не смог загрузить изображение")
                except Exception as qp_e:
                    print(f"[UserCard] Ошибка открытия через QPixmap: {qp_e}")
                    src = QPixmap()
            scaled = src.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
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
        elif self.user_data.get('photo_path') and os.path.exists(self.user_data['photo_path']):
            size = AVATAR_SIZE
            try:
                pil_img = Image.open(self.user_data['photo_path']).convert('RGBA')
                bbox = pil_img.getbbox()
                if bbox:
                    pil_img = pil_img.crop(bbox)
                qt_img = ImageQt.ImageQt(pil_img)
                src = QPixmap.fromImage(qt_img)
            except Exception:
                src = QPixmap(self.user_data['photo_path'])
            scale_factor = size / min(src.width(), src.height())
            new_width = int(src.width() * scale_factor)
            new_height = int(src.height() * scale_factor)
            scaled = src.scaled(new_width, new_height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
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
        else:
            # Рисуем только круг и текст внутри него
            size = AVATAR_SIZE
            pixmap = QPixmap(size, size)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            # Круг
            pen = painter.pen()
            pen.setWidth(3)
            pen.setColor(QColor('#888'))
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawEllipse(0, 0, size-1, size-1)
            # Текст
            painter.setPen(QColor('#aaa'))
            font = painter.font()
            font.setPointSize(13)
            painter.setFont(font)
            text = "Нет фото"
            rect = pixmap.rect()
            painter.drawText(rect, Qt.AlignCenter, text)
            painter.end()
            self.avatar_label.setPixmap(pixmap)
            self.avatar_label.setText("")

    def save_role_clicked(self):
        selected_role = self.role_combo.currentText()
        if self.on_role_change:
            self.on_role_change(self.user_data['username'], selected_role)

class UserManagePage(QWidget):
    def __init__(self, db, current_username, parent=None):
        super().__init__(parent)
        self.db = db
        self.current_username = current_username # Store current username
        self.init_ui()
        self.load_users()

    def init_ui(self):
        self.setStyleSheet("background-color: #2a2b38; color: white;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Заголовок
        title = QLabel("Управление пользователями")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)
        
        # Создаем скролл-область
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        # Создаем виджет для сетки карточек
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(20)
        self.grid_layout.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        
        scroll.setWidget(self.grid_widget)
        layout.addWidget(scroll)

    def load_users(self):
        # Очищаем старые карточки
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        users = self.db.get_all_users()
        print(f"Получено пользователей: {len(users)}")  # Отладочная информация
        print(f"Список пользователей: {users}")  # Отладочная информация
        
        # Добавляем карточки пользователей в сетку
        row = 0
        col = 0
        max_cols = 5  # Было 3, теперь 5 карточек в ряду
        
        for user in users:
            card = UserCard(user, self.delete_user, on_role_change=self.update_user_role_in_db, current_username=self.current_username)
            self.grid_layout.addWidget(card, row, col)
            col += 1
            if col >= max_cols:
                col = 0
                row += 1

    def delete_user(self, username):
        reply = QMessageBox.question(
            self,
            "Удалить пользователя",
            f"Вы уверены, что хотите удалить пользователя '{username}'?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if hasattr(self.db, 'delete_user') and self.db.delete_user(username):
                self.load_users()
                QMessageBox.information(self, "Успех", "Пользователь успешно удален")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось удалить пользователя")

    def update_user_role_in_db(self, username, new_role):
        if self.db.update_user_role(username, new_role):
            QMessageBox.information(self, "Успех", f"Роль пользователя {username} успешно обновлена на {new_role}")
            self.load_users() # Reload users to reflect changes
        else:
            QMessageBox.warning(self, "Ошибка", f"Не удалось обновить роль пользователя {username}")

class MainWindow(QWidget):
    def __init__(self, username: str, role: str):
        super().__init__()
        self.username = username
        self.role = role
        self.db = DatabaseManager()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("""
            QWidget {
                background-color: #2a2b38;
                color: white;
            }
        """)
        self.setMinimumSize(800, 600)
        self.setup_slide_menu()
        self.setup_content_container()
        self.setup_pages()
        self.setup_animations()
        self.setup_connections()
        self.setup_cart_drawer()
        self.slide_menu.hide_menu()
        self.slide_menu.list_widget.setCurrentRow(0)
        self.slide_menu.animation.valueChanged.connect(self.on_menu_width_changed)
        self.update_layouts()
        self.showMaximized()

    def setup_slide_menu(self):
        self.slide_menu = SlideMenu(self, role=self.role)
        self.slide_menu.setParent(self)
        self.slide_menu.setGeometry(-260, 0, 260, self.height())
        self.slide_menu.setVisible(True)
        # Корректируем пункты меню для не-админов
        if self.role != 'администратор':
            # Удаляем пункт 'Аналитика' из меню
            for i in range(self.slide_menu.list_widget.count() - 1, -1, -1):
                item = self.slide_menu.list_widget.item(i)
                if item.text().lower().startswith('аналитика'):
                    self.slide_menu.list_widget.takeItem(i)
        else:
            # Добавляем пункт "История продаж" для администратора
            self.slide_menu.list_widget.addItem("История продаж")

    def setup_content_container(self):
        self.content_container = QFrame(self)
        self.content_container.setStyleSheet("")
        self.content_layout = QVBoxLayout(self.content_container)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(0)
        self.setup_title_bar()
        self.content_container.setGeometry(0, 0, self.width(), self.height())
        self.content_container.setVisible(True)
        # Устанавливаем фильтр событий
        self.content_container.installEventFilter(self)

    def setup_title_bar(self):
        self.title_bar = CustomTitleBar(self)
        self.content_layout.addWidget(self.title_bar)
        self.title_bar.setStyleSheet("""
            QWidget {
                background-color: #2c2e3e;
                color: #f5f6fa;
            }
        """)

    def setup_pages(self):
        self.pages = QStackedWidget()
        if self.role == "пользователь":
            self.sales_history_page = SalesHistoryPage(self.db, self.username)
            self.catalog_page = StockPage(self.db, self.role, self.username)
            if hasattr(self.catalog_page, 'cart_page'):
                self.catalog_page.cart_page.sales_history_page = self.sales_history_page
            self.pages.addWidget(self.catalog_page)
        elif self.role == "администратор":
            self.warehouse_page = WarehousePage(self.db, self.username)
            self.pages.addWidget(self.warehouse_page)
        # Остальные страницы
        if self.role == "пользователь":
            self.pages.addWidget(self.sales_history_page)
            self.profile_page = ProfilePage(self.username, self.role)
            self.pages.addWidget(self.profile_page)
        elif self.role == "администратор":
            self.user_manage_page = UserManagePage(self.db, current_username=self.username)
            self.pages.addWidget(self.user_manage_page)
            self.analytics_page = AnalyticsPage(self.db, username=self.username, role=self.role)
            self.pages.addWidget(self.analytics_page)
            categories = self.db.get_all_categories()
            self.min_quantity_page = MinQuantityPage(self.db)
            self.pages.addWidget(self.min_quantity_page)
            self.sales_history_page = SalesHistoryPage(self.db, username=None, is_admin=True)
            self.pages.addWidget(self.sales_history_page)
        self.content_layout.addWidget(self.pages)

    def setup_animations(self):
        self.content_shift_animation = QPropertyAnimation(self.content_container, b"pos")
        self.content_shift_animation.setDuration(300)
        self.content_shift_animation.setEasingCurve(QEasingCurve.OutQuad)

    def setup_connections(self):
        self.slide_menu.list_widget.currentRowChanged.connect(self.switch_page)
        self.pages.currentChanged.connect(self.update_page_title)
        if hasattr(self.title_bar, 'menu_button'):
            self.title_bar.menu_button.clicked.disconnect()
            self.title_bar.menu_button.clicked.connect(self.toggle_menu)
        # Кнопка выхода
        if hasattr(self.slide_menu, 'logout_requested'):
            self.slide_menu.logout_requested.connect(self.logout)

    def setup_cart_drawer(self):
        """Настройка выдвижной панели корзины"""
        self.cart_drawer = CartDrawer(self)
        self.cart_drawer.setParent(self)
        self.cart_drawer.setGeometry(self.width(), 0, 340, self.height())
        self.cart_drawer.setVisible(False)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "slide_menu"):
            if not self.slide_menu.hidden:
                self.content_container.setGeometry(260, 0, self.width() - 260, self.height())
            else:
                self.content_container.setGeometry(0, 0, self.width(), self.height())
        if hasattr(self, "cart_drawer"):
            self.cart_drawer.resizeEvent(event)

    def update_layouts(self):
        if not hasattr(self, "slide_menu"):
            return
        w = self.width()
        h = self.height()
        if hasattr(self, "cart_drawer"):
            self.cart_drawer.setGeometry(w, 0, 340, h)

    def on_menu_width_changed(self):
        self.update_layouts()

    def switch_page(self, index):
        if self.role == 'администратор':
            self.pages.setCurrentIndex(index)
            if hasattr(self, 'sales_history_page') and index == self.pages.indexOf(self.sales_history_page):
                self.sales_history_page.load_history()
        else:
            self.pages.setCurrentIndex(index)
        if self.role == "пользователь" and index == 0 and hasattr(self, 'catalog_page'):
            self.catalog_page.update_products_grid()
        if self.role == "пользователь" and index == 1 and hasattr(self, 'sales_history_page'):
            self.sales_history_page.load_history()

    def update_page_title(self, index):
        if self.role == "пользователь":
            titles = {0: "Каталог товаров", 1: "История продаж", 2: "Личный кабинет"}
        else:
            titles = {0: "Складской учет", 1: "Управление пользователями", 2: "Аналитика", 3: "Настройки", 4: "История продаж"}
        self.title_bar.title.setText(titles.get(index, ""))

    def closeEvent(self, event):
        self.db.close()
        event.accept()

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QPainterPath, QColor
        from PyQt5.QtCore import QRectF
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = QRectF(self.rect())
        path = QPainterPath()
        path.addRoundedRect(rect, 14, 14)
        painter.fillPath(path, QColor('#2a2b38'))

    def toggle_menu(self):
        if self.slide_menu.hidden:
            self.show_menu()
        else:
            self.hide_menu()

    def show_menu(self):
        self.slide_menu.show_menu()
        self.content_shift_animation.stop()
        self.content_shift_animation.setStartValue(self.content_container.pos())
        self.content_shift_animation.setEndValue(QPoint(260, 0))
        self.content_shift_animation.start()

    def hide_menu(self):
        self.slide_menu.hide_menu()
        self.content_shift_animation.stop()
        self.content_shift_animation.setStartValue(self.content_container.pos())
        self.content_shift_animation.setEndValue(QPoint(0, 0))
        self.content_shift_animation.start()

    def toggle_cart(self):
        if hasattr(self, 'cart_drawer'):
            if self.cart_drawer.hidden:
                self.show_cart()
            else:
                self.hide_cart()

    def show_cart(self):
        self.cart_drawer.show_drawer()
        self.content_shift_animation.stop()
        self.content_shift_animation.setStartValue(self.content_container.pos())
        self.content_shift_animation.setEndValue(QPoint(-340, 0))
        self.content_shift_animation.start()

    def hide_cart(self):
        self.cart_drawer.hide_drawer()
        self.content_shift_animation.stop()
        self.content_shift_animation.setStartValue(self.content_container.pos())
        self.content_shift_animation.setEndValue(QPoint(0, 0))
        self.content_shift_animation.start()

    def eventFilter(self, obj, event):
        if obj == self.content_container:
            if event.type() == event.MouseButtonPress:
                # Проверяем, не является ли объект, на который нажали, кнопкой
                if isinstance(event.source(), QPushButton):
                    return False
                # Если это не кнопка, пропускаем событие дальше
                return super().eventFilter(obj, event)
        return super().eventFilter(obj, event)

    def logout(self):
        self.close()
        # Импортируем и открываем окно авторизации
        from login_window import LoginWindow
        self.login_win = LoginWindow()
        self.login_win.show()

    def show_min_quantity_page(self):
        self.pages.setCurrentIndex(self.pages.count() - 1)

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication

    app = QApplication(sys.argv)
    window = MainWindow(username="test_user", role="администратор")
    window.show()
    sys.exit(app.exec_())
