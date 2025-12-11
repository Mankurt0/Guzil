# add_test_data.py - Утилита для добавления тестовых данных
import sqlite3
from datetime import datetime

def add_test_products():
    """Добавление тестовых товаров в базу"""
    conn = sqlite3.connect('trade_enterprise.db')
    cursor = conn.cursor()
    
    # Проверяем, есть ли уже товары
    cursor.execute("SELECT COUNT(*) as count FROM products WHERE is_active = 1")
    count = cursor.fetchone()[0]
    
    if count == 0:
        print("Добавляем тестовые товары...")
        
        test_products = [
            ("SKU001", "Ноутбук Dell XPS 13", "Электроника", 89999.99, 10, 2, 50, "Dell Inc.", "123456789012"),
            ("SKU002", "Мышь беспроводная Logitech MX", "Аксессуары", 4999.99, 25, 5, 100, "Logitech", "234567890123"),
            ("SKU003", "Клавиатура механическая", "Аксессуары", 7999.99, 15, 3, 80, "Razer", "345678901234"),
            ("SKU004", "Монитор 27 дюймов 4K", "Электроника", 34999.99, 8, 2, 30, "LG", "456789012345"),
            ("SKU005", "Наушники Sony WH-1000XM4", "Аудио", 29999.99, 12, 3, 60, "Sony", "567890123456"),
            ("SKU006", "Смартфон iPhone 14", "Электроника", 89999.99, 5, 1, 25, "Apple", "678901234567"),
            ("SKU007", "Планшет Samsung Tab S8", "Электроника", 54999.99, 7, 2, 35, "Samsung", "789012345678"),
            ("SKU008", "Внешний жесткий диск 2TB", "Хранение данных", 6999.99, 20, 5, 100, "WD", "890123456789"),
            ("SKU009", "Флешка 128GB USB 3.0", "Хранение данных", 1999.99, 50, 10, 200, "SanDisk", "901234567890"),
            ("SKU010", "Веб-камера Full HD", "Аксессуары", 3999.99, 18, 5, 80, "Logitech", "012345678901"),
        ]
        
        for product in test_products:
            cursor.execute('''
                INSERT OR IGNORE INTO products 
                (sku, name, category, unit_price, quantity, min_quantity, max_quantity, supplier, barcode, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            ''', product)
        
        conn.commit()
        print(f"Добавлено {len(test_products)} тестовых товаров")
    else:
        print(f"В базе уже есть {count} активных товаров")
    
    conn.close()

def add_test_clients():
    """Добавление тестовых клиентов"""
    conn = sqlite3.connect('trade_enterprise.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as count FROM clients WHERE is_active = 1")
    count = cursor.fetchone()[0]
    
    if count == 0:
        print("Добавляем тестовых клиентов...")
        
        test_clients = [
            ("Иванов Иван Иванович", "+79161234567", "ivanov@example.com", "ул. Ленина, д. 10, кв. 5", "Постоянный клиент"),
            ("Петров Петр Петрович", "+79162345678", "petrov@example.com", "пр. Мира, д. 25, кв. 12", "Корпоративный клиент"),
            ("Сидорова Анна Сергеевна", "+79163456789", "sidorova@example.com", "ул. Пушкина, д. 7, кв. 3", "VIP клиент"),
            ("Кузнецов Алексей Владимирович", "+79164567890", "kuznetsov@example.com", "ул. Гагарина, д. 15, кв. 8", "Новый клиент"),
            ("Смирнова Ольга Дмитриевна", "+79165678901", "smirnova@example.com", "ул. Чехова, д. 3, кв. 21", "Частый покупатель"),
        ]
        
        for i, client in enumerate(test_clients, 1):
            client_code = f"C{datetime.now().strftime('%Y%m%d')}{i:03d}"
            cursor.execute('''
                INSERT OR IGNORE INTO clients 
                (client_code, full_name, phone, email, address, notes, personal_data_consent, is_active, created_by)
                VALUES (?, ?, ?, ?, ?, ?, 1, 1, 1)
            ''', (client_code, *client))
        
        conn.commit()
        print(f"Добавлено {len(test_clients)} тестовых клиентов")
    else:
        print(f"В базе уже есть {count} активных клиентов")
    
    conn.close()

if __name__ == "__main__":
    print("Добавление тестовых данных в базу...")
    add_test_products()
    add_test_clients()
    print("Готово!")