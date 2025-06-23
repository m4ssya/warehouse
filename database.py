import psycopg2
from psycopg2 import pool
from typing import List, Dict, Optional, Union
from pathlib import Path
from datetime import datetime, timedelta
import threading
import time

class DatabaseManager:
    def __init__(self):
        self.connection = None
        self.cursor = None
        self.get_connection()

    def get_connection(self):
        """Получение соединения с базой данных"""
        try:
            if self.connection is None or self.connection.closed:
                print("Попытка подключения к базе данных...")
                
                # Явно кодируем все параметры подключения
                connection_params = {
                    'dbname': 'warehouse',
                    'user': 'm4ssya',
                    'password': 'Vthty123',
                    'host': 'localhost',
                    'port': '5432'
                }
                
                # Преобразуем все строковые параметры в байты и обратно для очистки от некорректных символов
                for key, value in connection_params.items():
                    if isinstance(value, str):
                        connection_params[key] = value.encode('ascii', 'ignore').decode('ascii')
                
                self.connection = psycopg2.connect(**connection_params)
                print("Соединение установлено успешно")
                
                # Устанавливаем кодировку после подключения
                self.connection.set_client_encoding('UTF8')
                print("Кодировка установлена: UTF8")
                
                self.cursor = self.connection.cursor()
                print("Курсор создан успешно")
                
                # Проверяем кодировку
                self.cursor.execute("SHOW client_encoding")
                encoding = self.cursor.fetchone()[0]
                print(f"Текущая кодировка клиента: {encoding}")
                
                # Создаем таблицы, если они не существуют
                self.create_tables()
                
            return True
        except Exception as e:
            print(f"Ошибка при подключении к базе данных: {str(e)}")
            print(f"Тип ошибки: {type(e)}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
            self.connection = None
            self.cursor = None
            return False

    def close(self):
        """Закрытие соединения с базой данных"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.connection:
                self.connection.close()
        except Exception as e:
            print(f"Ошибка при закрытии соединения: {e}")
        finally:
            self.cursor = None
            self.connection = None

    def __del__(self):
        self.close()

    def _execute_with_retry(self, query, params=None, max_retries=3):
        """Выполнение запроса с повторными попытками при ошибках"""
        last_error = None
        for attempt in range(max_retries):
            try:
                if not self.get_connection():
                    raise Exception("Не удалось установить соединение с базой данных")
                
                # Подготавливаем параметры
                if params:
                    if isinstance(params, (list, tuple)):
                        params = [str(p).encode('ascii', 'ignore').decode('ascii') 
                                if p is not None else None for p in params]
                    elif isinstance(params, dict):
                        params = {k: str(v).encode('ascii', 'ignore').decode('ascii') 
                                if v is not None else None for k, v in params.items()}
                
                # Выполняем запрос
                if params:
                    self.cursor.execute(query, params)
                else:
                    self.cursor.execute(query)
                return True
                
            except (psycopg2.OperationalError, psycopg2.InterfaceError) as e:
                last_error = e
                print(f"Попытка {attempt + 1} из {max_retries} не удалась: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(0.1 * (attempt + 1))
                    self.close()
                else:
                    raise last_error
            except Exception as e:
                print(f"Непредвиденная ошибка при выполнении запроса: {str(e)}")
                print(f"Тип ошибки: {type(e)}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")
                raise
        return False

    def _initialize_database(self):
        """Создает таблицы, если они не существуют"""
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                name TEXT,
                photo_path TEXT,
                photo_data BYTEA,
                email TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                price TEXT NOT NULL,
                quantity TEXT NOT NULL,
                barcode TEXT,
                image TEXT,
                category TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS categories (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE NOT NULL
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sales_history (
                id SERIAL PRIMARY KEY,
                product_name TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                sale_date TEXT NOT NULL,
                username TEXT NOT NULL,
                sale_price FLOAT NOT NULL
            )
        """)
        
        # Создаем таблицу для минимальных количеств по категориям
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS category_min_quantities (
                id SERIAL PRIMARY KEY,
                category TEXT UNIQUE NOT NULL,
                min_quantity INTEGER NOT NULL
            )
        """)
        
        self.cursor.execute("SELECT COUNT(*) FROM categories")
        if self.cursor.fetchone()[0] == 0:
            self.cursor.execute("INSERT INTO categories (name) VALUES (%s)", ("Без категории",))
            
        # Создаем функцию для очистки старых записей
        self.cursor.execute("""
            CREATE OR REPLACE FUNCTION clean_old_sales_history()
            RETURNS trigger AS $$
            BEGIN
                DELETE FROM sales_history 
                WHERE sale_date::date < CURRENT_DATE - INTERVAL '1 year';
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
        """)
        
        # Создаем триггер для автоматической очистки
        self.cursor.execute("""
            DROP TRIGGER IF EXISTS clean_sales_history_trigger ON sales_history;
            CREATE TRIGGER clean_sales_history_trigger
            AFTER INSERT ON sales_history
            FOR EACH ROW
            EXECUTE FUNCTION clean_old_sales_history();
        """)
        
        # Создаем таблицу движения товаров
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS product_movement (
                id SERIAL PRIMARY KEY,
                product_id INTEGER REFERENCES products(id),
                movement_type VARCHAR(50) NOT NULL,
                quantity INTEGER NOT NULL,
                previous_quantity INTEGER NOT NULL,
                new_quantity INTEGER NOT NULL,
                movement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                username TEXT NOT NULL,
                reference_id INTEGER,
                reference_type VARCHAR(50),
                comment TEXT
            )
        """)
        
        self.connection.commit()

    def ensure_price_fields(self):
        self.get_connection()
        try:
            self.cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='products'")
            columns = [row[0] for row in self.cursor.fetchall()]
            if 'purchase_price' not in columns:
                self.cursor.execute("ALTER TABLE products ADD COLUMN purchase_price TEXT")
            if 'retail_price' not in columns:
                self.cursor.execute("ALTER TABLE products ADD COLUMN retail_price TEXT")
            self.connection.commit()
        except Exception as e:
            print(f"Ошибка при добавлении полей цен: {e}")
            self.connection.rollback()

    def add_product(self, product_data: Dict[str, Union[str, None]]) -> bool:
        self.ensure_price_fields()
        try:
            # Проверяем существование таблицы changes_log
            self.cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'changes_log'
                );
            """)
            
            if not self.cursor.fetchone()[0]:
                # Создаем таблицу changes_log если её нет
                self.cursor.execute("""
                    CREATE TABLE IF NOT EXISTS changes_log (
                        id SERIAL PRIMARY KEY,
                        table_name TEXT NOT NULL,
                        action TEXT NOT NULL,
                        record_id INTEGER NOT NULL,
                        change_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        username TEXT
                    )
                """)
            else:
                # Проверяем наличие колонки action
                self.cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'changes_log' AND column_name = 'action'
                    );
                """)
                if not self.cursor.fetchone()[0]:
                    # Добавляем колонку action если её нет
                    self.cursor.execute("""
                        ALTER TABLE changes_log 
                        ADD COLUMN action TEXT NOT NULL DEFAULT 'INSERT';
                    """)
                
                # Проверяем наличие колонки table_name
                self.cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'changes_log' AND column_name = 'table_name'
                    );
                """)
                if not self.cursor.fetchone()[0]:
                    # Добавляем колонку table_name если её нет
                    self.cursor.execute("""
                        ALTER TABLE changes_log 
                        ADD COLUMN table_name TEXT NOT NULL DEFAULT 'products';
                    """)
                
                # Проверяем наличие колонки record_id
                self.cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'changes_log' AND column_name = 'record_id'
                    );
                """)
                if not self.cursor.fetchone()[0]:
                    # Добавляем колонку record_id если её нет
                    self.cursor.execute("""
                        ALTER TABLE changes_log 
                        ADD COLUMN record_id INTEGER NOT NULL DEFAULT 0;
                    """)
                
                self.connection.commit()
                
                # Создаем или обновляем функцию для логирования изменений
                self.cursor.execute("""
                    CREATE OR REPLACE FUNCTION log_change()
                    RETURNS TRIGGER AS $$
                    BEGIN
                        INSERT INTO changes_log (table_name, action, record_id)
                        VALUES (TG_TABLE_NAME, TG_OP, NEW.id);
                        RETURN NEW;
                    END;
                    $$ LANGUAGE plpgsql;
                """)
                
                # Создаем или обновляем триггер
                self.cursor.execute("""
                    DROP TRIGGER IF EXISTS products_log_trigger ON products;
                    CREATE TRIGGER products_log_trigger
                    AFTER INSERT OR UPDATE OR DELETE ON products
                    FOR EACH ROW
                    EXECUTE FUNCTION log_change();
                """)
                
                self.connection.commit()

            # Начинаем транзакцию
            self.connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE)
            
            # Проверяем существование товара
            self.cursor.execute("SELECT id FROM products WHERE name = %s FOR UPDATE", (product_data['name'],))
            if self.cursor.fetchone():
                self.connection.rollback()
                return False

            self.cursor.execute(
                """INSERT INTO products (name, price, quantity, barcode, image, category, purchase_price, retail_price) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    product_data['name'],
                    product_data['price'],
                    product_data['quantity'],
                    product_data.get('barcode'),
                    product_data['image'],
                    product_data['category'] if product_data['category'] else None,
                    product_data.get('purchase_price'),
                    product_data.get('retail_price')
                )
            )
            self.connection.commit()
            return True
        except psycopg2.Error as e:
            print(f"Ошибка при добавлении товара: {e}")
            self.connection.rollback()
            return False
        finally:
            self.connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)

    def update_product(self, product_name: str, update_data: Dict[str, str]) -> bool:
        try:
            self.cursor.execute(
                "SELECT id, quantity FROM products WHERE name = %s",
                (product_name,)
            )
            current = self.cursor.fetchone()
            if not current:
                return False

            product_id, current_quantity = current

            # Если категория пустая или None, подставляем 'Без категории'
            if 'category' in update_data and (not update_data['category'] or update_data['category'].strip() == ''):
                update_data['category'] = "Без категории"

            update_fields = []
            update_values = []
            if 'retail_price' in update_data:
                update_fields.append("retail_price = %s")
                update_values.append(update_data['retail_price'])
                update_fields.append("price = %s")
                update_values.append(update_data['retail_price'])
            if 'purchase_price' in update_data:
                update_fields.append("purchase_price = %s")
                update_values.append(update_data['purchase_price'])
            if 'quantity' in update_data:
                update_fields.append("quantity = %s")
                update_values.append(update_data['quantity'])
            if 'category' in update_data:
                update_fields.append("category = %s")
                update_values.append(update_data['category'])
            if 'barcode' in update_data:
                update_fields.append("barcode = %s")
                update_values.append(update_data['barcode'])
            if 'image' in update_data:
                update_fields.append("image = %s")
                update_values.append(update_data['image'])

            if update_fields:
                query = f"UPDATE products SET {', '.join(update_fields)} WHERE name = %s"
                update_values.append(product_name)
                self.cursor.execute(query, update_values)

            self.connection.commit()
            return True
        except Exception as e:
            print(f"Ошибка при обновлении товара: {e}")
            self.connection.rollback()
            return False

    def update_low_stock_quantity(self, product_name, new_quantity):
        self.cursor.execute(
            "UPDATE low_stock_products SET quantity = %s WHERE product_name = %s",
            (new_quantity, product_name)
        )
        self.connection.commit()

    def delete_product(self, product_id: int) -> bool:
        """Удаление товара по ID с проверкой зависимостей"""
        try:
            # Начинаем транзакцию
            self.connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE)
            # Проверяем наличие продаж (убрал FOR UPDATE)
            self.cursor.execute("SELECT COUNT(*) FROM sales_history WHERE product_id = %s", (product_id,))
            if self.cursor.fetchone()[0] > 0:
                self.connection.rollback()
                return False
            # Удаляем товар
            self.cursor.execute("DELETE FROM products WHERE id = %s", (product_id,))
            self.connection.commit()
            return True
        except psycopg2.Error as e:
            print(f"Ошибка при удалении товара: {e}")
            self.connection.rollback()
            return False
        finally:
            self.connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)

    def get_all_products(self) -> List[Dict[str, Union[str, None]]]:
        self.ensure_price_fields()
        try:
            if not self.cursor or self.cursor.closed:
                self.get_connection()
            self.cursor.execute("SELECT id, name, price, quantity, barcode, image, category, purchase_price, retail_price FROM products")
            return [{
                "id": row[0],
                "name": row[1],
                "price": row[2],
                "quantity": row[3],
                "barcode": row[4],
                "image": row[5],
                "category": row[6] if row[6] else "Без категории",
                "purchase_price": row[7],
                "retail_price": row[8]
            } for row in self.cursor.fetchall()]
        except Exception as e:
            print(f"Ошибка при получении списка товаров: {e}")
            self.get_connection()
            return []

    def get_products_by_category(self, category: str) -> List[Dict[str, Union[str, None]]]:
        """Получение товаров по категории с обработкой ошибок"""
        try:
            if not self.cursor or self.cursor.closed:
                self.get_connection()
                
            if category == "Без категории":
                self.cursor.execute("SELECT name, price, quantity, barcode, image, category FROM products WHERE category IS NULL")
            else:
                self.cursor.execute("SELECT name, price, quantity, barcode, image, category FROM products WHERE category = %s", (category,))
                
            return [{
                "name": row[0],
                "price": row[1],
                "quantity": row[2],
                "barcode": row[3],
                "image": row[4],
                "category": row[5] if row[5] else "Без категории"
            } for row in self.cursor.fetchall()]
        except Exception as e:
            print(f"Ошибка при получении товаров по категории: {e}")
            self.get_connection()
            return []

    def add_category(self, category_name: str) -> bool:
        try:
            self.cursor.execute("INSERT INTO categories (name) VALUES (%s)", (category_name,))
            self.connection.commit()
            return True
        except psycopg2.Error as e:
            print(f"Ошибка при добавлении категории: {e}")
            self.connection.rollback()
            return False

    def delete_category(self, category_name: str) -> bool:
        try:
            self.cursor.execute("DELETE FROM categories WHERE name = %s", (category_name,))
            self.cursor.execute("UPDATE products SET category = NULL WHERE category = %s", (category_name,))
            self.connection.commit()
            return True
        except psycopg2.Error as e:
            print(f"Ошибка при удалении категории: {e}")
            self.connection.rollback()
            return False

    def get_all_categories(self) -> List[str]:
        self.cursor.execute("SELECT name FROM categories")
        return [row[0] for row in self.cursor.fetchall()]

    def search_products(self, search_term: str) -> List[Dict[str, Union[str, None]]]:
        """Поиск товаров с обработкой ошибок"""
        try:
            if not self.cursor or self.cursor.closed:
                self.get_connection()
                
            search_term = f"%{search_term}%"
            self.cursor.execute(
                "SELECT name, price, quantity, image, category FROM products WHERE name ILIKE %s OR category ILIKE %s",
                (search_term, search_term)
            )
            return [{
                "name": row[0],
                "price": row[1],
                "quantity": row[2],
                "image": row[3],
                "category": row[4] if row[4] else "Без категории"
            } for row in self.cursor.fetchall()]
        except Exception as e:
            print(f"Ошибка при поиске товаров: {e}")
            self.get_connection()
            return []

    def get_all_users(self):
        self.cursor.execute("SELECT username, role, name, photo_data, email FROM users")
        return [{
            "username": row[0],
            "role": row[1],
            "name": row[2] if row[2] else row[0],
            "photo_data": row[3],
            "email": row[4]
        } for row in self.cursor.fetchall()]

    def get_product_by_name(self, name: str) -> Optional[Dict[str, Union[str, None]]]:
        try:
            self.cursor.execute("SELECT id, name, price, quantity, barcode, image, category FROM products WHERE name = %s", (name,))
            row = self.cursor.fetchone()
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "price": row[2],
                    "quantity": row[3],
                    "barcode": row[4],
                    "image": row[5],
                    "category": row[6] if row[6] else "Без категории"
                }
            return None
        except psycopg2.Error as e:
            print(f"Ошибка при получении товара: {e}")
            return None

    def delete_user(self, username):
        try:
            # Удаляем все продажи пользователя
            self.cursor.execute("DELETE FROM sales_history WHERE username = %s", (username,))
            # Здесь можно добавить удаление других связанных данных, если появятся
            # Удаляем самого пользователя
            self.cursor.execute("DELETE FROM users WHERE username = %s", (username,))
            self.connection.commit()
            return self.cursor.rowcount > 0
        except Exception as e:
            print(f"Ошибка при удалении пользователя: {e}")
            self.connection.rollback()
            return False

    def add_sale(self, product_id: int, quantity: int, sale_date: str, username: str, sale_price: float) -> bool:
        try:
            # Начинаем транзакцию
            self.connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_SERIALIZABLE)
            # Получаем товар по id
            self.cursor.execute(
                "SELECT name, quantity FROM products WHERE id = %s FOR UPDATE",
                (product_id,)
            )
            result = self.cursor.fetchone()
            if not result:
                self.connection.rollback()
                return False
            product_name, current_quantity = result
            current_quantity = int(current_quantity)
            if current_quantity < quantity:
                self.connection.rollback()
                return False
            # Обновляем количество товара
            new_quantity = current_quantity - quantity
            self.cursor.execute(
                "UPDATE products SET quantity = %s WHERE id = %s",
                (str(new_quantity), product_id)
            )
            # Добавляем запись о продаже
            self.cursor.execute(
                """INSERT INTO sales_history 
                   (product_id, product_name, quantity, sale_date, username, sale_price) 
                   VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                (product_id, product_name, quantity, sale_date, username, sale_price)
            )
            sale_id = self.cursor.fetchone()[0]
            # Записываем движение товара
            self.cursor.execute("""
                INSERT INTO product_movement 
                (product_id, movement_type, quantity, previous_quantity, new_quantity, 
                 username, reference_id, reference_type, comment)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                product_id, 'OUT', quantity, current_quantity, new_quantity,
                username, sale_id, 'Продажа', f'Продажа по цене {sale_price}'
            ))
            # Проверяем, не нужно ли добавить товар в low_stock_products
            self.cursor.execute(
                "SELECT min_quantity FROM category_min_quantities WHERE category = (SELECT category FROM products WHERE id = %s)",
                (product_id,)
            )
            min_quantity_result = self.cursor.fetchone()
            if min_quantity_result and new_quantity <= min_quantity_result[0]:
                self.cursor.execute(
                    """INSERT INTO low_stock_products (product_name, category, quantity, min_quantity)
                       SELECT name, category, quantity, %s
                       FROM products
                       WHERE id = %s
                       ON CONFLICT (product_name) DO UPDATE
                       SET quantity = EXCLUDED.quantity""",
                    (min_quantity_result[0], product_id)
                )
            self.connection.commit()
            return True
        except Exception as e:
            print(f"[add_sale] Ошибка при добавлении продажи: {e}")
            self.connection.rollback()
            return False
        finally:
            self.connection.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_READ_COMMITTED)

    def get_sales_history(self, username: str) -> List[Dict[str, str]]:
        self.cursor.execute(
            "SELECT product_name, SUM(quantity) as total_qty, sale_date, sale_price FROM sales_history WHERE username = %s GROUP BY product_name, sale_date, sale_price ORDER BY sale_date DESC",
            (username,)
        )
        return [
            {"product_name": row[0], "quantity": row[1], "sale_date": row[2], "sale_price": row[3]}
            for row in self.cursor.fetchall()
        ]

    def clear_sales_history(self):
        """Удаляет всю историю продаж"""
        try:
            self.cursor.execute("DELETE FROM sales_history")
            self.connection.commit()
            return True
        except psycopg2.Error as e:
            print(f"Ошибка при очистке истории продаж: {e}")
            self.connection.rollback()
            return False

    def get_sales_history_by_period(self, username: str, period: str = "week") -> list:
        if period == "week":
            self.cursor.execute(
                """
                SELECT product_name, SUM(quantity) as total_qty, 
                       EXTRACT(YEAR FROM sale_date::date) as year, EXTRACT(WEEK FROM sale_date::date) as week,
                       MIN(sale_date) as week_start, MAX(sale_date) as week_end
                FROM sales_history 
                WHERE username = %s
                GROUP BY product_name, year, week
                ORDER BY year DESC, week DESC
                """,
                (username,)
            )
            result = []
            for row in self.cursor.fetchall():
                try:
                    start = datetime.strptime(row[4], "%Y-%m-%d").strftime("%d.%m.%Y")
                    end = datetime.strptime(row[5], "%Y-%m-%d").strftime("%d.%m.%Y")
                    period_str = f"{start} — {end}"
                except Exception:
                    period_str = f"Неделя {row[3]}, {row[2]}"
                result.append({
                    "product_name": row[0],
                    "quantity": row[1],
                    "period": period_str
                })
            return result
        elif period == "month":
            self.cursor.execute(
                """
                SELECT product_name, SUM(quantity) as total_qty, 
                       EXTRACT(YEAR FROM sale_date::date) as year, EXTRACT(MONTH FROM sale_date::date) as month,
                       MIN(sale_date) as month_start
                FROM sales_history 
                WHERE username = %s
                GROUP BY product_name, year, month
                ORDER BY year DESC, month DESC
                """,
                (username,)
            )
            result = []
            for row in self.cursor.fetchall():
                try:
                    month_name = datetime.strptime(row[4], "%Y-%m-%d").strftime("%B %Y")
                except Exception:
                    month_name = f"{row[3]}.{row[2]}"
                result.append({
                    "product_name": row[0],
                    "quantity": row[1],
                    "period": month_name
                })
            return result
        else:
            return self.get_sales_history(username)

    def get_sales_history_for_period(self, username: str = None, period: str = "day") -> list:
        try:
            today = datetime.now()
            if period == "day":
                date_str = today.strftime("%Y-%m-%d")
                query = "SELECT product_name, SUM(quantity), sale_date, sale_price, username FROM sales_history WHERE sale_date = %s"
                params = [date_str]
            elif period == "week":
                start_of_week = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
                end_of_week = (today + timedelta(days=6-today.weekday())).strftime("%Y-%m-%d")
                query = "SELECT product_name, SUM(quantity), sale_date, sale_price, username FROM sales_history WHERE sale_date BETWEEN %s AND %s"
                params = [start_of_week, end_of_week]
            elif period == "month":
                start_of_month = today.replace(day=1).strftime("%Y-%m-%d")
                if today.month == 12:
                    next_month = today.replace(year=today.year+1, month=1, day=1)
                else:
                    next_month = today.replace(month=today.month+1, day=1)
                end_of_month = (next_month - timedelta(days=1)).strftime("%Y-%m-%d")
                query = "SELECT product_name, SUM(quantity), sale_date, sale_price, username FROM sales_history WHERE sale_date BETWEEN %s AND %s"
                params = [start_of_month, end_of_month]
            else:
                return []

            # Добавляем фильтр по пользователю, если он указан
            if username:
                query += " AND username = %s"
                params.append(username)

            query += " GROUP BY product_name, sale_date, sale_price, username ORDER BY sale_date DESC"
            self.cursor.execute(query, params)

            result = [
                {"product_name": row[0], "quantity": row[1], "sale_date": row[2], "sale_price": row[3], "username": row[4]} 
                for row in self.cursor.fetchall()
            ]
            self.connection.commit()
            return result

        except Exception as e:
            print(f"Ошибка при получении истории продаж: {e}")
            self.connection.rollback()
            return []

    def get_sales_data(self, period='day', username=None):
        try:
            if period == 'day':
                interval = '1 day'
                group_by = "sale_date"
                date_format = "DD.MM.YYYY"
            elif period == 'week':
                interval = '7 days'
                group_by = "sale_date"
                date_format = "DD.MM.YYYY"
            elif period == 'month':
                interval = '30 days'
                group_by = "sale_date"
                date_format = "DD.MM.YYYY"
            else:  # year
                interval = '365 days'
                group_by = "sale_date"
                date_format = "DD.MM.YYYY"

            query = f'''
                SELECT 
                    TO_CHAR({group_by}, '{date_format}') as date,
                    COUNT(*) as total_sales,
                    SUM(quantity) as total_amount,
                    SUM(quantity) as total_quantity
                FROM sales_history
                WHERE sale_date >= CURRENT_DATE - INTERVAL '{interval}'
            '''
            params = []
            if username:
                query += " AND username = %s"
                params.append(username)
            query += f" GROUP BY {group_by} ORDER BY {group_by}"

            self.cursor.execute(query, params)
            result = self.cursor.fetchall()
            self.connection.commit()
            return result

        except Exception as e:
            print(f"Ошибка при получении данных о продажах: {e}")
            self.connection.rollback()
            return []

    def update_user_profile(self, username: str, name: str = None, photo_path: str = None, email: str = None) -> bool:
        try:
            self.cursor.execute(
                "UPDATE users SET name = %s, photo_path = %s, email = %s WHERE username = %s",
                (name, photo_path, email, username)
            )
            self.connection.commit()
            return True
        except psycopg2.Error as e:
            print(f"Ошибка при обновлении профиля: {e}")
            self.connection.rollback()
            return False

    def update_user_password(self, username: str, new_password: str) -> bool:
        try:
            self.cursor.execute(
                "UPDATE users SET password = %s WHERE username = %s",
                (new_password, username)
            )
            self.connection.commit()
            return True
        except psycopg2.Error as e:
            print(f"Ошибка при обновлении пароля: {e}")
            self.connection.rollback()
            return False

    def get_user_profile(self, username: str) -> dict:
        self.cursor.execute("SELECT username, name, role, photo_path, photo_data, email FROM users WHERE username = %s", (username,))
        row = self.cursor.fetchone()
        if row:
            return {
                "username": row[0],
                "name": row[1],
                "role": row[2],
                "photo_path": row[3],
                "photo_data": row[4],
                "email": row[5]
            }
        return {}

    def authenticate_user(self, login_or_email: str, password: str):
        try:
            self.cursor.execute(
                "SELECT username, role FROM users WHERE (username = %s OR email = %s) AND password = %s",
                (login_or_email, login_or_email, password)
            )
            user = self.cursor.fetchone()
            if user:
                return user  # (username, role)
            return None
        except psycopg2.Error as e:
            print(f"Ошибка при аутентификации пользователя: {e}")
            return None

    def add_test_products(self, count=1000):
        for i in range(1, count+1):
            name = str(i)
            price = '100'
            quantity = '100'
            image = None
            category = 'Тест'
            try:
                self.cursor.execute(
                    "INSERT INTO products (name, price, quantity, image, category) VALUES (%s, %s, %s, %s, %s)",
                    (name, price, quantity, image, category)
                )
            except Exception as e:
                print(f"Ошибка при добавлении товара {name}: {e}")
                self.connection.rollback()
        self.connection.commit()

    def update_user_photo(self, username: str, image_bytes: bytes) -> bool:
        try:
            self.cursor.execute(
                "UPDATE users SET photo_data = %s WHERE username = %s",
                (psycopg2.Binary(image_bytes), username)
            )
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Ошибка при сохранении фото пользователя: {e}")
            self.connection.rollback()
            return False

    def get_user_photo(self, username: str) -> Optional[bytes]:
        try:
            self.cursor.execute(
                "SELECT photo_data FROM users WHERE username = %s",
                (username,)
            )
            row = self.cursor.fetchone()
            return row[0] if row and row[0] else None
        except Exception as e:
            print(f"Ошибка при получении фото пользователя: {e}")
            return None

    def get_top_products(self, period='day', username=None):
        # Определяем границы периода
        if period == 'день' or period == 'day':
            interval = '1 day'
        elif period == 'неделя' or period == 'week':
            interval = '7 days'
        elif period == 'месяц' or period == 'month':
            interval = '30 days'
        elif period == 'год' or period == 'year':
            interval = '365 days'
        else:
            interval = '1 day'
        query = '''
            SELECT product_name, SUM(quantity) as total_qty
            FROM sales_history
            WHERE sale_date >= CURRENT_DATE - INTERVAL '%s'
        ''' % interval
        params = []
        if username:
            query += ' AND username = %s'
            params.append(username)
        query += ' GROUP BY product_name ORDER BY total_qty DESC LIMIT 5'
        self.cursor.execute(query, params)
        return self.cursor.fetchall()

    def get_sales_data_for_period(self, date_from, date_to, group_by='По дням', username=None):
        try:
            if group_by == 'По дням':
                group_sql = "sale_date::date"
                date_format = "DD.MM.YYYY"
            elif group_by == 'По неделям':
                group_sql = "DATE_TRUNC('week', sale_date::date)"
                date_format = "IYYY-IW"  # Год-неделя
            elif group_by == 'По месяцам':
                group_sql = "DATE_TRUNC('month', sale_date::date)"
                date_format = "MM.YYYY"
            else:
                group_sql = "sale_date::date"
                date_format = "DD.MM.YYYY"

            query = f'''
                SELECT 
                    TO_CHAR({group_sql}, '{date_format}') as date,
                    COUNT(*) as total_sales,
                    SUM(quantity) as total_amount,
                    SUM(quantity) as total_quantity
                FROM sales_history
                WHERE sale_date BETWEEN %s AND %s
            '''
            params = [date_from, date_to]
            if username:
                query += " AND username = %s"
                params.append(username)
            query += f" GROUP BY {group_sql} ORDER BY {group_sql}"
            self.cursor.execute(query, params)
            result = self.cursor.fetchall()
            self.connection.commit()
            return result
        except Exception as e:
            print(f"Ошибка при получении данных о продажах: {e}")
            self.connection.rollback()
            return []

    def get_top_products_for_period(self, date_from, date_to, group_by='По дням', username=None):
        try:
            query = '''
                SELECT product_name, SUM(quantity) as total_qty
                FROM sales_history
                WHERE sale_date BETWEEN %s AND %s
            '''
            params = [date_from, date_to]
            if username:
                query += ' AND username = %s'
                params.append(username)
            query += ' GROUP BY product_name ORDER BY total_qty DESC LIMIT 5'
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Exception as e:
            print(f"Ошибка при получении топ-5 товаров: {e}")
            return []

    def get_first_sale_date(self, username=None):
        """Получить дату первой продажи"""
        try:
            query = "SELECT MIN(sale_date) FROM sales_history"
            params = []
            if username:
                query += " WHERE username = %s"
                params.append(username)
            self.cursor.execute(query, params)
            result = self.cursor.fetchone()
            self.connection.commit()
            return result[0] if result and result[0] else None
        except Exception as e:
            print(f"Ошибка при получении даты первой продажи: {e}")
            self.connection.rollback()
            return None

    def add_low_stock_product(self, product_name, category, quantity, min_quantity):
        try:
            print(f"\nПопытка добавления товара в low_stock_products:")
            print(f"product_name: {product_name}")
            print(f"category: {category}")
            print(f"quantity: {quantity}")
            print(f"min_quantity: {min_quantity}")
            
            # Сначала проверяем, существует ли товар в таблице products
            self.cursor.execute("SELECT name FROM products WHERE name = %s", (product_name,))
            if not self.cursor.fetchone():
                print(f"Ошибка: Товар '{product_name}' не существует в таблице products")
                return False

            # Проверяем, существует ли уже запись для этого товара
            self.cursor.execute("SELECT id FROM low_stock_products WHERE product_name = %s", (product_name,))
            existing = self.cursor.fetchone()
            
            if existing:
                # Обновляем существующую запись
                print(f"Обновление существующей записи для товара {product_name}")
                self.cursor.execute("""
                    UPDATE low_stock_products 
                    SET category = %s, quantity = %s, min_quantity = %s, notified = FALSE
                    WHERE product_name = %s
                """, (category, quantity, min_quantity, product_name))
            else:
                # Создаем новую запись
                print(f"Создание новой записи для товара {product_name}")
                self.cursor.execute("""
                    INSERT INTO low_stock_products (product_name, category, quantity, min_quantity, notified)
                    VALUES (%s, %s, %s, %s, FALSE)
                """, (product_name, category, quantity, min_quantity))
            
            self.connection.commit()
            print(f"Успешно сохранено для товара: {product_name}")
            return True
            
        except Exception as e:
            print(f"Ошибка при добавлении товара с низким запасом: {e}")
            self.connection.rollback()
            return False

    def get_low_stock_products(self):
        """Получает список товаров с количеством ниже минимального для их категории"""
        try:
            query = """
                SELECT p.name, p.quantity, p.category, cmq.min_quantity
                FROM products p
                JOIN category_min_quantities cmq ON p.category = cmq.category
                WHERE CAST(p.quantity AS INTEGER) < cmq.min_quantity
                ORDER BY p.category, p.name
            """
            self.cursor.execute(query)
            results = self.cursor.fetchall()
            return [{
                'name': row[0],
                'quantity': int(row[1]),
                'category': row[2],
                'min_quantity': row[3]
            } for row in results]
        except Exception as e:
            print(f"Ошибка при получении товаров с низким остатком: {str(e)}")
            return []

    def delete_all_products(self):
        """Удаляет все товары из таблицы products"""
        try:
            self.cursor.execute("DELETE FROM products")
            self.connection.commit()
            return True
        except psycopg2.Error as e:
            print(f"Ошибка при удалении всех товаров: {e}")
            self.connection.rollback()
            return False

    def clean_old_sales_history(self):
        """Очищает записи продаж старше 1 года"""
        try:
            self.cursor.execute("SELECT clean_old_sales_history()")
            self.connection.commit()
            return True
        except psycopg2.Error as e:
            print(f"Ошибка при очистке старых записей продаж: {e}")
            self.connection.rollback()
            return False

    def set_category_min_quantity(self, category: str, min_quantity: int) -> bool:
        """Устанавливает минимальное количество для категории"""
        try:
            self.cursor.execute("""
                INSERT INTO category_min_quantities (category, min_quantity)
                VALUES (%s, %s)
                ON CONFLICT (category) 
                DO UPDATE SET min_quantity = EXCLUDED.min_quantity
            """, (category, min_quantity))
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Ошибка при установке минимального количества для категории: {e}")
            self.connection.rollback()
            return False

    def get_category_min_quantity(self, category: str) -> int:
        """Получает минимальное количество для категории"""
        self.cursor.execute("""
            SELECT min_quantity FROM category_min_quantities WHERE category = %s
        """, (category,))
        result = self.cursor.fetchone()
        return result[0] if result else 0

    def update_user_role(self, username: str, new_role: str) -> bool:
        try:
            self.cursor.execute("UPDATE users SET role = %s WHERE username = %s", (new_role, username))
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Ошибка при обновлении роли пользователя '{username}': {e}")
            return False

    def create_tables(self):
        try:
            # Создаем таблицу пользователей
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id SERIAL PRIMARY KEY,
                    username VARCHAR(50) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL,
                    role VARCHAR(20) NOT NULL,
                    name VARCHAR(100),
                    photo_path VARCHAR(255),
                    photo_data BYTEA,
                    email VARCHAR(100)
                )
            """)

            # Создаем таблицу категорий
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS categories (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(50) UNIQUE NOT NULL
                )
            """)

            # Создаем таблицу товаров
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS products (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 0,
                    category VARCHAR(50) REFERENCES categories(name),
                    image_path VARCHAR(255),
                    image_data BYTEA,
                    barcode TEXT
                )
            """)

            # Создаем таблицу истории продаж
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS sales_history (
                    id SERIAL PRIMARY KEY,
                    product_name TEXT NOT NULL,
                    quantity INTEGER NOT NULL,
                    sale_date TEXT NOT NULL,
                    username TEXT NOT NULL,
                    sale_price FLOAT NOT NULL
                )
            """)

            # Создаем таблицу минимальных количеств для категорий
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS category_min_quantities (
                    category VARCHAR(50) PRIMARY KEY REFERENCES categories(name),
                    min_quantity INTEGER NOT NULL
                )
            """)

            # Создаем таблицу логов изменений
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS changes_log (
                    id SERIAL PRIMARY KEY,
                    action VARCHAR(50) NOT NULL,
                    details JSONB,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Создаем таблицу ожидающих заказов
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS pending_orders (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    price DECIMAL(10,2) NOT NULL,
                    category VARCHAR(50) REFERENCES categories(name),
                    quantity INTEGER NOT NULL,
                    status VARCHAR(50) NOT NULL,
                    order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    supplier VARCHAR(100),
                    expected_delivery_date TIMESTAMP
                )
            """)

            # Создаем таблицу поставщиков
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS suppliers (
                    id SERIAL PRIMARY KEY,
                    name VARCHAR(100) NOT NULL,
                    phone VARCHAR(50),
                    email VARCHAR(100),
                    comment TEXT
                )
            """)

            # Создаем таблицу движения товаров
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS product_movement (
                    id SERIAL PRIMARY KEY,
                    product_id INTEGER REFERENCES products(id),
                    movement_type VARCHAR(50) NOT NULL,
                    quantity INTEGER NOT NULL,
                    previous_quantity INTEGER NOT NULL,
                    new_quantity INTEGER NOT NULL,
                    movement_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    username TEXT NOT NULL,
                    reference_id INTEGER,
                    reference_type VARCHAR(50),
                    comment TEXT
                )
            """)

            self.connection.commit()
            print("Таблицы успешно созданы")
        except Exception as e:
            print(f"Ошибка при создании таблиц: {e}")
            self.connection.rollback()

    def add_supplier(self, supplier_data):
        try:
            self.cursor.execute(
                """INSERT INTO suppliers (name, phone, email, comment) VALUES (%s, %s, %s, %s)""",
                (
                    supplier_data['name'],
                    supplier_data['phone'],
                    supplier_data['email'],
                    supplier_data['comment']
                )
            )
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Ошибка при добавлении поставщика: {e}")
            self.connection.rollback()
            return False

    def add_product_movement(self, product_id: int, movement_type: str, quantity: int, username: str, comment: str) -> bool:
        """Добавляет запись о движении товара (без reference_id и reference_type)"""
        try:
            # Получаем текущее количество товара
            self.cursor.execute("SELECT quantity FROM products WHERE id = %s", (product_id,))
            result = self.cursor.fetchone()
            if not result:
                return False
            previous_quantity = int(result[0])
            new_quantity = previous_quantity + quantity if movement_type == 'IN' else previous_quantity - quantity
            # Добавляем запись о движении
            self.cursor.execute("""
                INSERT INTO product_movement 
                (product_id, movement_type, quantity, previous_quantity, new_quantity, username, comment)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (product_id, movement_type, quantity, previous_quantity, new_quantity, username, comment))
            # Обновляем количество товара
            self.cursor.execute("""
                UPDATE products SET quantity = %s WHERE id = %s
            """, (str(new_quantity), product_id))
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Ошибка при добавлении движения товара: {e}")
            self.connection.rollback()
            return False

    def get_product_movement_history(self, product_id: int = None, 
                                   start_date: str = None, 
                                   end_date: str = None) -> List[Dict]:
        """Получает историю движения товаров с возможностью фильтрации"""
        try:
            query = """
                SELECT 
                    pm.id,
                    p.name as product_name,
                    p.category as product_category,
                    pm.movement_type,
                    pm.quantity,
                    pm.previous_quantity,
                    pm.new_quantity,
                    pm.movement_date,
                    pm.username,
                    pm.reference_type,
                    pm.comment
                FROM product_movement pm
                JOIN products p ON p.id = pm.product_id
                WHERE 1=1
            """
            params = []
            
            if product_id:
                query += " AND pm.product_id = %s"
                params.append(product_id)
            
            if start_date:
                query += " AND pm.movement_date >= %s"
                params.append(start_date)
            
            if end_date:
                query += " AND pm.movement_date <= %s"
                params.append(end_date)
            
            query += " ORDER BY pm.movement_date DESC"
            
            self.cursor.execute(query, params)
            results = self.cursor.fetchall()
            
            return [{
                'id': row[0],
                'product_name': row[1],
                'product_category': row[2],
                'movement_type': row[3],
                'quantity': row[4],
                'previous_quantity': row[5],
                'new_quantity': row[6],
                'movement_date': row[7],
                'username': row[8],
                'reference_type': row[9],
                'comment': row[10]
            } for row in results]
        except Exception as e:
            print(f"Ошибка при получении истории движения товаров: {e}")
            return []

    def log_initial_product_movement(self, product_id: int, quantity: int, username: str, comment: str = None):
        """Добавляет запись о первоначальном поступлении товара без изменения количества"""
        try:
            self.cursor.execute(
                "INSERT INTO product_movement (product_id, movement_type, quantity, previous_quantity, new_quantity, username, reference_type, comment) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (product_id, 'IN', quantity, 0, quantity, username, 'Первичное добавление', comment)
            )
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Ошибка при логировании первоначального поступления: {e}")
            self.connection.rollback()
            return False