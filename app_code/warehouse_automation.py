from PyQt5.QtCore import QObject, pyqtSignal
import json
from datetime import datetime
class WarehouseAutomation(QObject):
    # Сигналы для уведомлений
    low_stock_alert = pyqtSignal(str, int)  # товар, текущее количество
    order_needed = pyqtSignal(str, int)     # товар, рекомендуемое количество
    stock_updated = pyqtSignal()            # обновление статистики

    def __init__(self, db):
        super().__init__()
        self.db = db
        self.settings = self.load_settings()

    def load_settings(self):
        import os
        settings_path = 'warehouse_automation_settings.json'
        if os.path.exists(settings_path):
            with open(settings_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'auto_order': False,
            'order_threshold': 0.5,
            'check_interval': 300,
            'notify_on_low': True
        }

    def update_settings(self, new_settings):
        self.settings.update(new_settings)
        with open('warehouse_automation_settings.json', 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, ensure_ascii=False, indent=2)

    def log_order_request(self, product_name, order_quantity, min_quantity):
        """Логирование запроса на заказ"""
        try:
            self.db.cursor.execute("""
                INSERT INTO changes_log (action, details, timestamp)
                VALUES (%s, %s, %s)
            """, (
                'order_request',
                json.dumps({
                    'product': product_name,
                    'order_quantity': order_quantity,
                    'min_quantity': min_quantity
                }),
                datetime.now()
            ))
            self.db.connection.commit()
        except Exception as e:
            print(f"Ошибка при логировании заказа: {e}")
            self.db.connection.rollback()

    def log_statistics_update(self, stats):
        """Логирование обновления статистики"""
        try:
            self.db.cursor.execute("""
                INSERT INTO changes_log (action, details, timestamp)
                VALUES (%s, %s, %s)
            """, (
                'statistics_update',
                json.dumps({
                    'total_products': stats[0],
                    'total_quantity': stats[1],
                    'low_stock_count': stats[2]
                }),
                datetime.now()
            ))
            self.db.connection.commit()
        except Exception as e:
            print(f"Ошибка при логировании статистики: {e}")
            self.db.connection.rollback()

    # Оставляем только ручные методы, если нужны
    # def manual_check_stock_levels(self): ...
    # def manual_update_statistics(self): ... 