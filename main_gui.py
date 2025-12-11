# main_gui.py - Графический интерфейс (Tkinter)
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from tkinter import filedialog
from datetime import datetime, timedelta
import json
import csv
import os
from database import Database
from auth import AuthManager
from config import Config
import sqlite3

class TradingAppGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title(Config.APP_NAME)
        self.root.geometry("1200x700")
        
        # Инициализация компонентов
        self.db = Database()
        self.auth = AuthManager(self.db, Config.SECRET_KEY)
        self.current_user = None
        
        self.setup_styles()
        self.show_login_screen()
    
    def setup_styles(self):
        """Настройка стилей интерфейса"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Настраиваем цвета
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'))
        style.configure('Heading.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Success.TButton', foreground='green')
        style.configure('Danger.TButton', foreground='red')
        style.configure('Warning.TButton', foreground='orange')
    
    def clear_window(self):
        """Очистка окна"""
        for widget in self.root.winfo_children():
            widget.destroy()
    
    def show_login_screen(self):
        """Экран входа в систему"""
        self.clear_window()
        
        # Основной фрейм
        main_frame = ttk.Frame(self.root, padding="40")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Заголовок
        title_label = ttk.Label(main_frame, text="Вход в систему", style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 30))
        
        # Поля ввода
        ttk.Label(main_frame, text="Логин:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.login_entry = ttk.Entry(main_frame, width=30)
        self.login_entry.grid(row=1, column=1, pady=5, padx=(10, 0))
        self.login_entry.focus()
        
        ttk.Label(main_frame, text="Пароль:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.password_entry = ttk.Entry(main_frame, width=30, show="*")
        self.password_entry.grid(row=2, column=1, pady=5, padx=(10, 0))
        
        # Кнопка входа
        login_button = ttk.Button(main_frame, text="Войти", command=self.do_login, width=20)
        login_button.grid(row=3, column=0, columnspan=2, pady=20)
        
        # Привязка клавиши Enter
        self.root.bind('<Return>', lambda e: self.do_login())
    
    def do_login(self):
        """Обработка входа"""
        # Получаем значения перед любыми возможными изменениями интерфейса
        username = self.login_entry.get().strip()
        password = self.password_entry.get()
        
        if not username or not password:
            messagebox.showerror("Ошибка", "Введите логин и пароль")
            return
        
        self.current_user = self.auth.login(username, password)
        
        if self.current_user:
            messagebox.showinfo("Успех", f"Добро пожаловать, {self.current_user['full_name']}!")
            
            # Проверяем, нужно ли сменить пароль
            if self.current_user.get('must_change_password'):
                self.show_change_password_dialog()
            else:
                self.show_main_menu()
        else:
            messagebox.showerror("Ошибка", "Неверный логин или пароль")
            # Очищаем поле пароля при неудачной попытке
            self.password_entry.delete(0, tk.END)
    
    def show_change_password_dialog(self):
        """Диалог смены пароля"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Смена пароля")
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Требуется сменить пароль", style='Title.TLabel').pack(pady=10)
        
        ttk.Label(dialog, text="Новый пароль:").pack(anchor=tk.W, padx=20, pady=(10, 0))
        new_pass_entry = ttk.Entry(dialog, width=30, show="*")
        new_pass_entry.pack(padx=20, pady=5)
        
        ttk.Label(dialog, text="Повторите пароль:").pack(anchor=tk.W, padx=20, pady=(10, 0))
        confirm_pass_entry = ttk.Entry(dialog, width=30, show="*")
        confirm_pass_entry.pack(padx=20, pady=5)
        
        def change_password():
            new_pass = new_pass_entry.get()
            confirm_pass = confirm_pass_entry.get()
            
            if not new_pass or not confirm_pass:
                messagebox.showerror("Ошибка", "Заполните все поля")
                return
            
            if new_pass != confirm_pass:
                messagebox.showerror("Ошибка", "Пароли не совпадают")
                return
            
            if len(new_pass) < Config.PASSWORD_MIN_LENGTH:
                messagebox.showerror("Ошибка", f"Пароль должен быть не менее {Config.PASSWORD_MIN_LENGTH} символов")
                return
            
            if self.db.update_password(self.current_user['id'], new_pass):
                messagebox.showinfo("Успех", "Пароль успешно изменен")
                self.current_user['must_change_password'] = 0
                dialog.destroy()
                self.show_main_menu()
            else:
                messagebox.showerror("Ошибка", "Не удалось изменить пароль")
        
        ttk.Button(dialog, text="Сменить пароль", command=change_password).pack(pady=20)
    
    def show_main_menu(self):
        """Главное меню приложения"""
        self.clear_window()
        
        # Отвязываем старые привязки клавиш
        self.root.unbind('<Return>')
        
        # Верхняя панель
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=5)
        
        user_info = f"{self.current_user['full_name']} ({self.current_user['role']})"
        user_label = ttk.Label(top_frame, text=user_info, font=('Arial', 10, 'bold'))
        user_label.pack(side=tk.LEFT)
        
        logout_button = ttk.Button(top_frame, text="Выход", command=self.logout)
        logout_button.pack(side=tk.RIGHT)
        
        # Панель вкладок
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Создаем вкладки в зависимости от роли
        if self.auth.has_permission(self.current_user['role'], 'viewer'):
            self.create_clients_tab()
            self.create_products_tab()
        
        if self.auth.has_permission(self.current_user['role'], 'cashier'):
            self.create_orders_tab()
        
        if self.auth.has_permission(self.current_user['role'], 'manager'):
            self.create_reports_tab()
        
        if self.current_user['role'] == 'admin':
            self.create_admin_tab()
            self.create_audit_tab()
        
        # Кнопка обновления всех вкладок
        refresh_button = ttk.Button(self.root, text="Обновить все", command=self.refresh_all_tabs)
        refresh_button.pack(pady=5)
    
    def refresh_all_tabs(self):
        """Обновление всех вкладок"""
        current_tab = self.notebook.index(self.notebook.select())
        
        if hasattr(self, 'clients_tree'):
            self.load_clients()
        if hasattr(self, 'products_tree'):
            self.load_products()
        if hasattr(self, 'orders_tree'):
            self.load_orders()
        if hasattr(self, 'audit_tree'):
            self.load_audit_logs()
        
        # Возвращаемся на текущую вкладку
        self.notebook.select(current_tab)
    
    def create_clients_tab(self):
        """Вкладка управления клиентами"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Клиенты")
        
        # Панель инструментов
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Добавить", command=self.add_client_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Редактировать", command=self.edit_client_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Удалить", command=self.delete_client_dialog, style='Danger.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Экспорт в CSV", command=self.export_clients_csv).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Обновить", command=self.load_clients).pack(side=tk.LEFT, padx=2)
        
        # Поиск
        search_frame = ttk.Frame(toolbar)
        search_frame.pack(side=tk.RIGHT)
        ttk.Label(search_frame, text="Поиск:").pack(side=tk.LEFT)
        self.client_search_entry = ttk.Entry(search_frame, width=20)
        self.client_search_entry.pack(side=tk.LEFT, padx=5)
        self.client_search_entry.bind('<KeyRelease>', lambda e: self.search_clients())
        ttk.Button(search_frame, text="Очистить", command=self.clear_client_search).pack(side=tk.LEFT)
        
        # Таблица клиентов
        columns = ("ID", "Код", "ФИО", "Телефон", "Email", "Адрес", "Дата регистрации")
        self.clients_tree = ttk.Treeview(frame, columns=columns, show="headings", height=20)
        
        for col in columns:
            self.clients_tree.heading(col, text=col)
            self.clients_tree.column(col, width=100, minwidth=50)
        
        # Полоса прокрутки
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.clients_tree.yview)
        self.clients_tree.configure(yscrollcommand=scrollbar.set)
        
        self.clients_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Загружаем данные
        self.load_clients()
    
    def load_clients(self):
        """Загрузка клиентов из БД"""
        if not hasattr(self, 'clients_tree'):
            return
            
        for item in self.clients_tree.get_children():
            self.clients_tree.delete(item)
        
        clients = self.db.get_clients()
        for client in clients:
            self.clients_tree.insert('', tk.END, values=(
                client['id'],
                client['client_code'],
                client['full_name'],
                client['phone'] or '',
                client['email'] or '',
                client['address'] or '',
                client['registration_date']
            ))
    
    def add_client_dialog(self):
        """Диалог добавления клиента"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить клиента")
        dialog.geometry("500x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Поля формы
        fields = [
            ("ФИО*", "full_name", True),
            ("Телефон", "phone", False),
            ("Email", "email", False),
            ("Адрес", "address", False),
            ("Примечания", "notes", False)
        ]
        
        entries = {}
        
        for i, (label_text, field_name, required) in enumerate(fields):
            ttk.Label(dialog, text=label_text).grid(row=i, column=0, sticky=tk.W, padx=10, pady=5)
            if field_name == 'notes':
                entry = scrolledtext.ScrolledText(dialog, width=40, height=4)
                entry.grid(row=i, column=1, padx=10, pady=5, sticky='nsew')
            else:
                entry = ttk.Entry(dialog, width=40)
                entry.grid(row=i, column=1, padx=10, pady=5)
            entries[field_name] = entry
        
        # Согласие на обработку данных
        consent_var = tk.BooleanVar(value=True)
        consent_check = ttk.Checkbutton(
            dialog, 
            text="Согласие на обработку персональных данных (ФЗ-152)",
            variable=consent_var
        )
        consent_check.grid(row=len(fields), column=0, columnspan=2, padx=10, pady=10, sticky=tk.W)
        
        def save_client():
            # Получаем данные из формы
            client_data = {}
            
            # Для текстовых полей
            for field in ['full_name', 'phone', 'email', 'address']:
                if field in entries:
                    client_data[field] = entries[field].get().strip()
            
            # Для текстовой области
            if 'notes' in entries:
                if hasattr(entries['notes'], 'get'):
                    client_data['notes'] = entries['notes'].get("1.0", tk.END).strip()
                else:
                    client_data['notes'] = entries['notes'].get().strip()
            
            client_data['personal_data_consent'] = consent_var.get()
            
            if not client_data['full_name']:
                messagebox.showerror("Ошибка", "ФИО обязательно для заполнения")
                return
            
            client_id = self.db.create_client(client_data, self.current_user['id'])
            if client_id:
                messagebox.showinfo("Успех", "Клиент успешно добавлен")
                self.load_clients()
                dialog.destroy()
                
                # Обновляем список клиентов для заказов, если он существует
                if hasattr(self, 'client_search_combo'):
                    self.load_clients_for_combo()
            else:
                messagebox.showerror("Ошибка", "Не удалось добавить клиента")
        
        ttk.Button(dialog, text="Сохранить", command=save_client).grid(
            row=len(fields)+1, column=0, columnspan=2, pady=20
        )
    
    def edit_client_dialog(self):
        """Редактирование клиента"""
        selection = self.clients_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите клиента для редактирования")
            return
        
        item = self.clients_tree.item(selection[0])
        client_id = item['values'][0]
        
        # Получаем данные клиента
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
        client = cursor.fetchone()
        conn.close()
        
        if not client:
            messagebox.showerror("Ошибка", "Клиент не найден")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Редактирование клиента: {client['full_name']}")
        dialog.geometry("500x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Поля формы
        fields = [
            ("Код клиента", "client_code", False),
            ("ФИО*", "full_name", True),
            ("Телефон", "phone", False),
            ("Email", "email", False),
            ("Адрес", "address", False),
            ("Примечания", "notes", False)
        ]
        
        entries = {}
        
        for i, (label_text, field_name, required) in enumerate(fields):
            ttk.Label(dialog, text=label_text).grid(row=i, column=0, sticky=tk.W, padx=10, pady=5)
            
            current_value = client[field_name] if client[field_name] else ""
            
            if field_name == 'client_code':
                # Код клиента только для чтения
                entry = ttk.Entry(dialog, width=40, state='readonly')
                entry.insert(0, current_value)
            elif field_name == 'notes':
                entry = scrolledtext.ScrolledText(dialog, width=40, height=4)
                entry.insert("1.0", current_value)
            else:
                entry = ttk.Entry(dialog, width=40)
                entry.insert(0, current_value)
            
            entry.grid(row=i, column=1, padx=10, pady=5)
            entries[field_name] = entry
        
        def save_changes():
            client_data = {
                'full_name': entries['full_name'].get().strip(),
                'phone': entries['phone'].get().strip(),
                'email': entries['email'].get().strip(),
                'address': entries['address'].get().strip()
            }
            
            # Получаем заметки
            if hasattr(entries['notes'], 'get'):
                client_data['notes'] = entries['notes'].get("1.0", tk.END).strip()
            else:
                client_data['notes'] = entries['notes'].get().strip()
            
            if not client_data['full_name']:
                messagebox.showerror("Ошибка", "ФИО обязательно для заполнения")
                return
            
            # Обновляем данные в БД
            conn = self.db.get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    UPDATE clients 
                    SET full_name = ?, phone = ?, email = ?, address = ?, notes = ?
                    WHERE id = ?
                ''', (
                    client_data['full_name'],
                    client_data['phone'],
                    client_data['email'],
                    client_data['address'],
                    client_data['notes'],
                    client_id
                ))
                
                conn.commit()
                
                # Логируем действие
                self.db.log_audit(
                    self.current_user['id'],
                    'UPDATE_CLIENT',
                    'clients',
                    client_id,
                    old_values=dict(client),
                    new_values=client_data
                )
                
                messagebox.showinfo("Успех", "Данные клиента обновлены")
                self.load_clients()
                dialog.destroy()
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Ошибка", f"Не удалось обновить данные: {e}")
            finally:
                conn.close()
        
        ttk.Button(dialog, text="Сохранить", command=save_changes).grid(
            row=len(fields)+1, column=0, columnspan=2, pady=20
        )
    
    def delete_client_dialog(self):
        """Удаление клиента"""
        selection = self.clients_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите клиента для удаления")
            return
        
        item = self.clients_tree.item(selection[0])
        client_id = item['values'][0]
        client_name = item['values'][2]
        
        # Проверяем, есть ли у клиента заказы
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM orders WHERE client_id = ?", (client_id,))
        order_count = cursor.fetchone()['count']
        conn.close()
        
        if order_count > 0:
            messagebox.showerror("Ошибка", 
                f"Нельзя удалить клиента с существующими заказами ({order_count} заказов).\n"
                "Сначала удалите или перепривяжите заказы.")
            return
        
        if messagebox.askyesno("Подтверждение", 
                               f"Вы уверены, что хотите удалить клиента '{client_name}'?\n"
                               "Это действие нельзя отменить."):
            
            conn = self.db.get_connection()
            cursor = conn.cursor()
            try:
                # Получаем старые данные для лога
                cursor.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
                old_data = dict(cursor.fetchone())
                
                # Мягкое удаление (установка is_active = 0)
                cursor.execute("UPDATE clients SET is_active = 0 WHERE id = ?", (client_id,))
                conn.commit()
                
                # Логируем действие
                self.db.log_audit(
                    self.current_user['id'],
                    'DELETE_CLIENT',
                    'clients',
                    client_id,
                    old_values=old_data
                )
                
                messagebox.showinfo("Успех", "Клиент удален")
                self.load_clients()
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Ошибка", f"Не удалось удалить клиента: {e}")
            finally:
                conn.close()
    
    def export_clients_csv(self):
        """Экспорт клиентов в CSV"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Сохранить клиентов как CSV"
        )
        
        if not file_path:
            return
        
        try:
            clients = self.db.get_clients(limit=10000)
            
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['ID', 'Код', 'ФИО', 'Телефон', 'Email', 'Адрес', 'Дата регистрации', 'Согласие на обработку']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for client in clients:
                    writer.writerow({
                        'ID': client['id'],
                        'Код': client['client_code'],
                        'ФИО': client['full_name'],
                        'Телефон': client['phone'] or '',
                        'Email': client['email'] or '',
                        'Адрес': client['address'] or '',
                        'Дата регистрации': client['registration_date'],
                        'Согласие на обработку': 'Да' if client['personal_data_consent'] else 'Нет'
                    })
            
            messagebox.showinfo("Успех", f"Клиенты экспортированы в {file_path}")
            
            # Логируем экспорт
            self.db.log_audit(
                self.current_user['id'],
                'EXPORT_CLIENTS_CSV',
                table_name='clients',
                new_values={'file_path': file_path, 'count': len(clients)}
            )
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось экспортировать данные: {e}")
    
    def search_clients(self):
        """Поиск клиентов"""
        search_term = self.client_search_entry.get().strip().lower()
        if not search_term:
            self.load_clients()
            return
        
        for item in self.clients_tree.get_children():
            self.clients_tree.delete(item)
        
        clients = self.db.get_clients(limit=1000)
        for client in clients:
            # Проверяем совпадение по разным полям
            if (search_term in client['full_name'].lower() or
                search_term in (client['phone'] or '').lower() or
                search_term in (client['email'] or '').lower() or
                search_term in (client['client_code'] or '').lower() or
                search_term in (client['address'] or '').lower()):
                
                self.clients_tree.insert('', tk.END, values=(
                    client['id'],
                    client['client_code'],
                    client['full_name'],
                    client['phone'] or '',
                    client['email'] or '',
                    client['address'] or '',
                    client['registration_date']
                ))
    
    def clear_client_search(self):
        """Очистка поиска клиентов"""
        self.client_search_entry.delete(0, tk.END)
        self.load_clients()
    
    def create_products_tab(self):
        """Вкладка управления товарами"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Товары")
        
        # Панель инструментов
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Добавить", command=self.add_product_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Редактировать", command=self.edit_product_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Удалить", command=self.delete_product_dialog, style='Danger.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Обновить", command=self.load_products).pack(side=tk.LEFT, padx=2)
        
        # Фильтры
        filter_frame = ttk.Frame(toolbar)
        filter_frame.pack(side=tk.RIGHT)
        
        ttk.Label(filter_frame, text="Категория:").pack(side=tk.LEFT)
        self.category_filter = ttk.Combobox(filter_frame, width=15, state='readonly')
        self.category_filter.pack(side=tk.LEFT, padx=5)
        self.category_filter.bind('<<ComboboxSelected>>', lambda e: self.load_products())
        
        ttk.Label(filter_frame, text="Поиск:").pack(side=tk.LEFT)
        self.product_search_entry = ttk.Entry(filter_frame, width=20)
        self.product_search_entry.pack(side=tk.LEFT, padx=5)
        self.product_search_entry.bind('<KeyRelease>', lambda e: self.search_products())
        
        # Таблица товаров
        columns = ("ID", "Артикул", "Название", "Категория", "Цена", "Кол-во", "Мин", "Макс", "Поставщик")
        self.products_tree = ttk.Treeview(frame, columns=columns, show="headings", height=20)
        
        for col in columns:
            self.products_tree.heading(col, text=col)
            self.products_tree.column(col, width=80, minwidth=50)
        
        # Полоса прокрутки
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.products_tree.yview)
        self.products_tree.configure(yscrollcommand=scrollbar.set)
        
        self.products_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Загружаем категории и данные
        self.load_product_categories()
        self.load_products()
    
    def load_product_categories(self):
        """Загрузка списка категорий товаров"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT category FROM products WHERE category IS NOT NULL ORDER BY category")
        categories = ['Все'] + [row['category'] for row in cursor.fetchall()]
        conn.close()
        
        self.category_filter['values'] = categories
        self.category_filter.set('Все')
    
    def load_products(self):
        """Загрузка товаров из БД"""
        if not hasattr(self, 'products_tree'):
            return
            
        for item in self.products_tree.get_children():
            self.products_tree.delete(item)
        
        category = None if self.category_filter.get() == 'Все' else self.category_filter.get()
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        if category:
            cursor.execute("SELECT * FROM products WHERE is_active = 1 AND category = ? ORDER BY name", (category,))
        else:
            cursor.execute("SELECT * FROM products WHERE is_active = 1 ORDER BY name")
        
        products = cursor.fetchall()
        conn.close()
        
        for product in products:
            self.products_tree.insert('', tk.END, values=(
                product['id'],
                product['sku'],
                product['name'],
                product['category'] or '',
                f"{product['unit_price']:.2f}",
                product['quantity'],
                product['min_quantity'],
                product['max_quantity'],
                product['supplier'] or ''
            ))
            
            # Подсветка товаров с низким запасом
            if product['quantity'] < product['min_quantity']:
                self.products_tree.item(self.products_tree.get_children()[-1], tags=('low_stock',))
        
        # Настройка тегов для подсветки
        self.products_tree.tag_configure('low_stock', background='#ffcccc')
    
    def add_product_dialog(self):
        """Диалог добавления товара"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить товар")
        dialog.geometry("500x600")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Поля формы
        fields = [
            ("Артикул*", "sku"),
            ("Название*", "name"),
            ("Категория", "category"),
            ("Цена*", "unit_price"),
            ("Начальное количество", "quantity"),
            ("Мин. запас", "min_quantity"),
            ("Макс. запас", "max_quantity"),
            ("Поставщик", "supplier"),
            ("Штрих-код", "barcode"),
            ("Описание", "description")
        ]
        
        entries = {}
        
        for i, (label_text, field_name) in enumerate(fields):
            ttk.Label(dialog, text=label_text).grid(row=i, column=0, sticky=tk.W, padx=10, pady=5)
            
            if field_name == 'description':
                entry = scrolledtext.ScrolledText(dialog, width=40, height=6)
                entry.grid(row=i, column=1, padx=10, pady=5, sticky='nsew')
            else:
                entry = ttk.Entry(dialog, width=40)
                entry.grid(row=i, column=1, padx=10, pady=5)
            
            # Устанавливаем значения по умолчанию
            if field_name == 'min_quantity':
                entry.insert(0, '10')
            elif field_name == 'max_quantity':
                entry.insert(0, '100')
            elif field_name == 'quantity':
                entry.insert(0, '0')
            elif field_name == 'unit_price':
                entry.insert(0, '0.00')
            
            entries[field_name] = entry
        
        def save_product():
            product_data = {
                'sku': entries['sku'].get().strip().upper(),
                'name': entries['name'].get().strip(),
                'category': entries['category'].get().strip(),
                'unit_price': entries['unit_price'].get().strip(),
                'quantity': entries['quantity'].get().strip(),
                'min_quantity': entries['min_quantity'].get().strip(),
                'max_quantity': entries['max_quantity'].get().strip(),
                'supplier': entries['supplier'].get().strip(),
                'barcode': entries['barcode'].get().strip(),
                'description': entries['description'].get("1.0", tk.END).strip()
            }
            
            # Валидация
            if not product_data['sku'] or not product_data['name']:
                messagebox.showerror("Ошибка", "Артикул и название обязательны для заполнения")
                return
            
            try:
                product_data['unit_price'] = float(product_data['unit_price'])
                product_data['quantity'] = int(product_data['quantity'])
                product_data['min_quantity'] = int(product_data['min_quantity'])
                product_data['max_quantity'] = int(product_data['max_quantity'])
                
                if product_data['unit_price'] < 0:
                    raise ValueError("Цена не может быть отрицательной")
                if product_data['quantity'] < 0:
                    raise ValueError("Количество не может быть отрицательным")
                
            except ValueError as e:
                messagebox.showerror("Ошибка", f"Неверный формат числа: {e}")
                return
            
            # Сохраняем товар в БД
            conn = self.db.get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO products 
                    (sku, name, description, category, unit_price, quantity, 
                     min_quantity, max_quantity, supplier, barcode)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    product_data['sku'],
                    product_data['name'],
                    product_data['description'],
                    product_data['category'],
                    product_data['unit_price'],
                    product_data['quantity'],
                    product_data['min_quantity'],
                    product_data['max_quantity'],
                    product_data['supplier'],
                    product_data['barcode']
                ))
                
                product_id = cursor.lastrowid
                conn.commit()
                
                # Логируем действие
                self.db.log_audit(
                    self.current_user['id'],
                    'CREATE_PRODUCT',
                    'products',
                    product_id,
                    new_values=product_data
                )
                
                messagebox.showinfo("Успех", "Товар успешно добавлен")
                self.load_product_categories()
                self.load_products()
                dialog.destroy()
                
                # Обновляем список товаров для заказов
                if hasattr(self, 'product_combo'):
                    self.load_products_for_combo()
            except sqlite3.IntegrityError:
                messagebox.showerror("Ошибка", "Товар с таким артикулом уже существует")
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Ошибка", f"Не удалось добавить товар: {e}")
            finally:
                conn.close()
        
        ttk.Button(dialog, text="Сохранить", command=save_product).grid(
            row=len(fields)+1, column=0, columnspan=2, pady=20
        )
    
    def edit_product_dialog(self):
        """Редактирование товара"""
        selection = self.products_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите товар для редактирования")
            return
        
        item = self.products_tree.item(selection[0])
        product_id = item['values'][0]
        
        # Получаем данные товара
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
        product = cursor.fetchone()
        conn.close()
        
        if not product:
            messagebox.showerror("Ошибка", "Товар не найден")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Редактирование товара: {product['name']}")
        dialog.geometry("500x600")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Поля формы
        fields = [
            ("Артикул*", "sku"),
            ("Название*", "name"),
            ("Категория", "category"),
            ("Цена*", "unit_price"),
            ("Количество", "quantity"),
            ("Мин. запас", "min_quantity"),
            ("Макс. запас", "max_quantity"),
            ("Поставщик", "supplier"),
            ("Штрих-код", "barcode"),
            ("Описание", "description")
        ]
        
        entries = {}
        
        for i, (label_text, field_name) in enumerate(fields):
            ttk.Label(dialog, text=label_text).grid(row=i, column=0, sticky=tk.W, padx=10, pady=5)
            
            current_value = product[field_name] if product[field_name] is not None else ""
            
            if field_name == 'description':
                entry = scrolledtext.ScrolledText(dialog, width=40, height=6)
                entry.insert("1.0", current_value)
                entry.grid(row=i, column=1, padx=10, pady=5, sticky='nsew')
            else:
                entry = ttk.Entry(dialog, width=40)
                if field_name == 'unit_price':
                    entry.insert(0, f"{current_value:.2f}")
                else:
                    entry.insert(0, str(current_value))
                entry.grid(row=i, column=1, padx=10, pady=5)
            
            if field_name == 'sku':
                entry.config(state='readonly')
            
            entries[field_name] = entry
        
        def save_changes():
            product_data = {
                'name': entries['name'].get().strip(),
                'category': entries['category'].get().strip(),
                'unit_price': entries['unit_price'].get().strip(),
                'quantity': entries['quantity'].get().strip(),
                'min_quantity': entries['min_quantity'].get().strip(),
                'max_quantity': entries['max_quantity'].get().strip(),
                'supplier': entries['supplier'].get().strip(),
                'barcode': entries['barcode'].get().strip(),
                'description': entries['description'].get("1.0", tk.END).strip()
            }
            
            # Валидация
            if not product_data['name']:
                messagebox.showerror("Ошибка", "Название обязательно для заполнения")
                return
            
            try:
                product_data['unit_price'] = float(product_data['unit_price'])
                product_data['quantity'] = int(product_data['quantity'])
                product_data['min_quantity'] = int(product_data['min_quantity'])
                product_data['max_quantity'] = int(product_data['max_quantity'])
                
                if product_data['unit_price'] < 0:
                    raise ValueError("Цена не может быть отрицательной")
                if product_data['quantity'] < 0:
                    raise ValueError("Количество не может быть отрицательным")
                
            except ValueError as e:
                messagebox.showerror("Ошибка", f"Неверный формат числа: {e}")
                return
            
            # Обновляем данные в БД
            conn = self.db.get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    UPDATE products 
                    SET name = ?, description = ?, category = ?, unit_price = ?, 
                        quantity = ?, min_quantity = ?, max_quantity = ?, 
                        supplier = ?, barcode = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (
                    product_data['name'],
                    product_data['description'],
                    product_data['category'],
                    product_data['unit_price'],
                    product_data['quantity'],
                    product_data['min_quantity'],
                    product_data['max_quantity'],
                    product_data['supplier'],
                    product_data['barcode'],
                    product_id
                ))
                
                conn.commit()
                
                # Логируем действие
                self.db.log_audit(
                    self.current_user['id'],
                    'UPDATE_PRODUCT',
                    'products',
                    product_id,
                    old_values=dict(product),
                    new_values=product_data
                )
                
                messagebox.showinfo("Успех", "Данные товара обновлены")
                self.load_product_categories()
                self.load_products()
                dialog.destroy()
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Ошибка", f"Не удалось обновить данные: {e}")
            finally:
                conn.close()
        
        ttk.Button(dialog, text="Сохранить", command=save_changes).grid(
            row=len(fields)+1, column=0, columnspan=2, pady=20
        )
    
    def delete_product_dialog(self):
        """Удаление товара"""
        selection = self.products_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите товар для удаления")
            return
        
        item = self.products_tree.item(selection[0])
        product_id = item['values'][0]
        product_name = item['values'][2]
        
        # Проверяем, есть ли товар в заказах
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM order_items WHERE product_id = ?", (product_id,))
        order_count = cursor.fetchone()['count']
        conn.close()
        
        if order_count > 0:
            messagebox.showerror("Ошибка", 
                f"Нельзя удалить товар, который есть в заказах ({order_count} позиций).\n"
                "Сначала удалите связанные заказы.")
            return
        
        if messagebox.askyesno("Подтверждение", 
                               f"Вы уверены, что хотите удалить товар '{product_name}'?\n"
                               "Это действие нельзя отменить."):
            
            conn = self.db.get_connection()
            cursor = conn.cursor()
            try:
                # Получаем старые данные для лога
                cursor.execute("SELECT * FROM products WHERE id = ?", (product_id,))
                old_data = dict(cursor.fetchone())
                
                # Мягкое удаление
                cursor.execute("UPDATE products SET is_active = 0 WHERE id = ?", (product_id,))
                conn.commit()
                
                # Логируем действие
                self.db.log_audit(
                    self.current_user['id'],
                    'DELETE_PRODUCT',
                    'products',
                    product_id,
                    old_values=old_data
                )
                
                messagebox.showinfo("Успех", "Товар удален")
                self.load_product_categories()
                self.load_products()
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Ошибка", f"Не удалось удалить товар: {e}")
            finally:
                conn.close()
    
    def search_products(self):
        """Поиск товаров"""
        search_term = self.product_search_entry.get().strip().lower()
        if not search_term:
            self.load_products()
            return
        
        for item in self.products_tree.get_children():
            self.products_tree.delete(item)
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        category = None if self.category_filter.get() == 'Все' else self.category_filter.get()
        
        if category:
            cursor.execute("SELECT * FROM products WHERE is_active = 1 AND category = ? ORDER BY name", (category,))
        else:
            cursor.execute("SELECT * FROM products WHERE is_active = 1 ORDER BY name")
        
        products = cursor.fetchall()
        conn.close()
        
        for product in products:
            if (search_term in product['name'].lower() or
                search_term in (product['sku'] or '').lower() or
                search_term in (product['description'] or '').lower() or
                search_term in (product['supplier'] or '').lower() or
                search_term in (product['category'] or '').lower()):
                
                self.products_tree.insert('', tk.END, values=(
                    product['id'],
                    product['sku'],
                    product['name'],
                    product['category'] or '',
                    f"{product['unit_price']:.2f}",
                    product['quantity'],
                    product['min_quantity'],
                    product['max_quantity'],
                    product['supplier'] or ''
                ))
    
    def create_orders_tab(self):
        """Вкладка создания заказов"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Заказы")
        
        # Разделяем окно на две части
        paned_window = ttk.PanedWindow(frame, orient=tk.HORIZONTAL)
        paned_window.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Левая панель - создание заказа
        left_frame = ttk.Frame(paned_window)
        paned_window.add(left_frame, weight=1)
        
        # Правая панель - список заказов
        right_frame = ttk.Frame(paned_window)
        paned_window.add(right_frame, weight=1)
        
        # Левая панель: форма создания заказа
        ttk.Label(left_frame, text="Новый заказ", style='Heading.TLabel').pack(anchor=tk.W, padx=5, pady=5)
        
        # Выбор клиента
        client_frame = ttk.LabelFrame(left_frame, text="Клиент", padding=10)
        client_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Создаем Combobox для поиска клиента
        ttk.Label(client_frame, text="Поиск клиента:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.client_search_combo = ttk.Combobox(client_frame, width=30, state='normal')
        self.client_search_combo.grid(row=0, column=1, padx=5, pady=5)
        
        # Кнопка выбора клиента
        self.select_client_btn = ttk.Button(client_frame, text="Выбрать", command=self.select_client_for_order)
        self.select_client_btn.grid(row=0, column=2, padx=5)
        
        # Кнопка нового клиента
        ttk.Button(client_frame, text="Новый клиент", command=self.add_client_for_order).grid(row=0, column=3, padx=5)
        
        # Информация о выбранном клиенте
        self.selected_client_info = ttk.Label(client_frame, text="Клиент не выбран", foreground='gray')
        self.selected_client_info.grid(row=1, column=0, columnspan=4, sticky=tk.W, pady=5)
        self.selected_client_id = None
        
        # Загружаем список клиентов для автодополнения
        self.load_clients_for_combo()
        
        # Список товаров в заказе
        items_frame = ttk.LabelFrame(left_frame, text="Товары в заказе", padding=10)
        items_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Таблица товаров в заказе
        columns = ("Товар", "Кол-во", "Цена", "Сумма")
        self.order_items_tree = ttk.Treeview(items_frame, columns=columns, show="headings", height=8)
        
        for col in columns:
            self.order_items_tree.heading(col, text=col)
            self.order_items_tree.column(col, width=100)
        
        scrollbar = ttk.Scrollbar(items_frame, orient=tk.VERTICAL, command=self.order_items_tree.yview)
        self.order_items_tree.configure(yscrollcommand=scrollbar.set)
        
        self.order_items_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Панель добавления товара
        add_item_frame = ttk.Frame(items_frame)
        add_item_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(add_item_frame, text="Товар:").pack(side=tk.LEFT, padx=2)
        self.product_combo = ttk.Combobox(add_item_frame, width=25, state='readonly')
        self.product_combo.pack(side=tk.LEFT, padx=2)
        
        ttk.Label(add_item_frame, text="Кол-во:").pack(side=tk.LEFT, padx=2)
        self.quantity_spinbox = tk.Spinbox(add_item_frame, from_=1, to=1000, width=10)
        self.quantity_spinbox.pack(side=tk.LEFT, padx=2)
        
        ttk.Button(add_item_frame, text="Добавить", command=self.add_item_to_order).pack(side=tk.LEFT, padx=5)
        ttk.Button(add_item_frame, text="Удалить", command=self.remove_item_from_order, style='Danger.TButton').pack(side=tk.LEFT)
        
        # Загружаем список товаров
        self.load_products_for_combo()
        
        # Итого
        total_frame = ttk.Frame(left_frame)
        total_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.total_label = ttk.Label(total_frame, text="Итого: 0.00 руб.", font=('Arial', 12, 'bold'))
        self.total_label.pack(side=tk.RIGHT)
        
        # Примечания
        notes_frame = ttk.LabelFrame(left_frame, text="Примечания", padding=10)
        notes_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.order_notes_text = scrolledtext.ScrolledText(notes_frame, height=4)
        self.order_notes_text.pack(fill=tk.BOTH, expand=True)
        
        # Кнопки создания заказа
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, padx=5, pady=10)
        
        ttk.Button(button_frame, text="Создать заказ", command=self.create_order).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Очистить форму", command=self.clear_order_form).pack(side=tk.RIGHT)
        
        # Правая панель: список заказов
        ttk.Label(right_frame, text="История заказов", style='Heading.TLabel').pack(anchor=tk.W, padx=5, pady=5)
        
        # Панель инструментов для заказов
        orders_toolbar = ttk.Frame(right_frame)
        orders_toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(orders_toolbar, text="Обновить", command=self.load_orders).pack(side=tk.LEFT, padx=2)
        ttk.Button(orders_toolbar, text="Просмотр", command=self.view_order_details).pack(side=tk.LEFT, padx=2)
        ttk.Button(orders_toolbar, text="Отменить", command=self.cancel_order, style='Warning.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(orders_toolbar, text="Завершить", command=self.complete_order, style='Success.TButton').pack(side=tk.LEFT, padx=2)
        
        # Фильтры заказов
        filter_frame = ttk.Frame(orders_toolbar)
        filter_frame.pack(side=tk.RIGHT)
        
        ttk.Label(filter_frame, text="Статус:").pack(side=tk.LEFT)
        self.order_status_filter = ttk.Combobox(filter_frame, 
                                               values=['Все', 'pending', 'processing', 'completed', 'cancelled'], 
                                               width=12, state='readonly')
        self.order_status_filter.pack(side=tk.LEFT, padx=5)
        self.order_status_filter.set('Все')
        self.order_status_filter.bind('<<ComboboxSelected>>', lambda e: self.load_orders())
        
        # Таблица заказов
        columns = ("ID", "Номер", "Клиент", "Сумма", "Статус", "Дата")
        self.orders_tree = ttk.Treeview(right_frame, columns=columns, show="headings", height=20)
        
        for col in columns:
            self.orders_tree.heading(col, text=col)
            self.orders_tree.column(col, width=100, minwidth=50)
        
        orders_scrollbar = ttk.Scrollbar(right_frame, orient=tk.VERTICAL, command=self.orders_tree.yview)
        self.orders_tree.configure(yscrollcommand=orders_scrollbar.set)
        
        self.orders_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        orders_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Загружаем заказы
        self.load_orders()
    
    def load_clients_for_combo(self):
        """Загрузка клиентов для автодополнения"""
        if not hasattr(self, 'client_search_combo'):
            return
            
        clients = self.db.get_clients(limit=1000)
        # Создаем список для отображения: ФИО + телефон (если есть)
        client_display = []
        self.clients_for_order = []  # Сохраняем полные данные
        
        for client in clients:
            display_text = f"{client['full_name']}"
            if client['phone']:
                display_text += f" ({client['phone']})"
            client_display.append(display_text)
            self.clients_for_order.append(client)
        
        self.client_search_combo['values'] = client_display
        
        # Настраиваем автодополнение
        def autocomplete(event):
            typed = self.client_search_combo.get().lower()
            if not typed:
                self.client_search_combo['values'] = client_display
                return
            
            # Фильтруем клиентов по введенному тексту
            matching = [name for name in client_display if typed in name.lower()]
            self.client_search_combo['values'] = matching if matching else client_display
        
        self.client_search_combo.bind('<KeyRelease>', autocomplete)
    
    def load_products_for_combo(self):
        """Загрузка товаров для выпадающего списка"""
        if not hasattr(self, 'product_combo'):
            return
            
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, sku, name, unit_price, quantity FROM products WHERE is_active = 1 AND quantity > 0 ORDER BY name")
        products = cursor.fetchall()
        conn.close()
        
        self.products_list = []
        product_names = []
        for product in products:
            display = f"{product['name']} ({product['sku']}) - {product['unit_price']:.2f} руб. (остаток: {product['quantity']})"
            product_names.append(display)
            self.products_list.append({
                'id': product['id'],
                'sku': product['sku'],
                'name': product['name'],
                'price': product['unit_price'],
                'quantity': product['quantity']
            })
        
        self.product_combo['values'] = product_names
        if product_names:
            self.product_combo.current(0)
    
    def select_client_for_order(self):
        """Выбор клиента для заказа"""
        selected_text = self.client_search_combo.get().strip()
        if not selected_text:
            messagebox.showwarning("Внимание", "Введите или выберите клиента")
            return
        
        # Ищем клиента в списке
        selected_client = None
        for client in self.clients_for_order:
            display_text = f"{client['full_name']}"
            if client['phone']:
                display_text += f" ({client['phone']})"
            
            if selected_text == display_text:
                selected_client = client
                break
        
        if selected_client:
            self.selected_client_id = selected_client['id']
            self.selected_client_info.config(
                text=f"{selected_client['full_name']} (ID: {selected_client['id']})",
                foreground='black'
            )
            messagebox.showinfo("Успех", f"Выбран клиент: {selected_client['full_name']}")
        else:
            messagebox.showerror("Ошибка", "Клиент не найден. Пожалуйста, выберите клиента из списка.")
    
    def add_client_for_order(self):
        """Добавление нового клиента из формы заказа"""
        self.add_client_dialog()
    
    def add_item_to_order(self):
        """Добавление товара в заказ"""
        selected_index = self.product_combo.current()
        if selected_index == -1:
            messagebox.showwarning("Внимание", "Выберите товар")
            return
        
        try:
            quantity = int(self.quantity_spinbox.get())
            if quantity <= 0:
                messagebox.showerror("Ошибка", "Количество должно быть положительным")
                return
        except ValueError:
            messagebox.showerror("Ошибка", "Введите корректное количество")
            return
        
        product = self.products_list[selected_index]
        
        # Проверяем доступное количество
        if quantity > product['quantity']:
            messagebox.showerror("Ошибка", 
                f"Недостаточно товара на складе. Доступно: {product['quantity']}")
            return
        
        # Добавляем в таблицу
        total = product['price'] * quantity
        item_id = len(self.order_items_tree.get_children()) + 1
        self.order_items_tree.insert('', tk.END, iid=item_id, values=(
            product['name'],
            quantity,
            f"{product['price']:.2f}",
            f"{total:.2f}"
        ), tags=(str(product['id']),))
        
        # Обновляем итого
        self.update_order_total()
    
    def remove_item_from_order(self):
        """Удаление товара из заказа"""
        selection = self.order_items_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите товар для удаления")
            return
        
        for item in selection:
            self.order_items_tree.delete(item)
        
        self.update_order_total()
    
    def update_order_total(self):
        """Обновление общей суммы заказа"""
        total = 0.0
        for item in self.order_items_tree.get_children():
            values = self.order_items_tree.item(item)['values']
            if len(values) >= 4:
                try:
                    total += float(values[3])
                except ValueError:
                    pass
        
        self.total_label.config(text=f"Итого: {total:.2f} руб.")
    
    def clear_order_form(self):
        """Очистка формы заказа"""
        self.selected_client_id = None
        self.selected_client_info.config(text="Клиент не выбран", foreground='gray')
        self.client_search_combo.set('')
        
        for item in self.order_items_tree.get_children():
            self.order_items_tree.delete(item)
        
        self.order_notes_text.delete("1.0", tk.END)
        self.update_order_total()
    
    def create_order(self):
        """Создание нового заказа"""
        # Проверяем клиента
        if not self.selected_client_id:
            messagebox.showerror("Ошибка", "Выберите клиента")
            return
        
        # Проверяем товары
        items = []
        for item in self.order_items_tree.get_children():
            values = self.order_items_tree.item(item)['values']
            tags = self.order_items_tree.item(item)['tags']
            if tags:
                try:
                    product_id = int(tags[0])
                    quantity = int(values[1])
                    items.append({
                        'product_id': product_id,
                        'quantity': quantity
                    })
                except (ValueError, IndexError):
                    continue
        
        if not items:
            messagebox.showerror("Ошибка", "Добавьте хотя бы один товар в заказ")
            return
        
        # Создаем заказ
        order_data = {
            'client_id': self.selected_client_id,
            'items': items,
            'notes': self.order_notes_text.get("1.0", tk.END).strip()
        }
        
        order_id = self.db.create_order(order_data, self.current_user['id'])
        if order_id:
            messagebox.showinfo("Успех", f"Заказ №{order_id} успешно создан")
            self.clear_order_form()
            self.load_orders()
            self.load_products_for_combo()  # Обновляем остатки товаров
        else:
            messagebox.showerror("Ошибка", "Не удалось создать заказ")
    
    def load_orders(self):
        """Загрузка заказов из БД"""
        if not hasattr(self, 'orders_tree'):
            return
            
        for item in self.orders_tree.get_children():
            self.orders_tree.delete(item)
        
        status_filter = None if self.order_status_filter.get() == 'Все' else self.order_status_filter.get()
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        if status_filter:
            cursor.execute('''
                SELECT o.*, c.full_name as client_name 
                FROM orders o
                LEFT JOIN clients c ON o.client_id = c.id
                WHERE o.status = ?
                ORDER BY o.created_at DESC
                LIMIT 100
            ''', (status_filter,))
        else:
            cursor.execute('''
                SELECT o.*, c.full_name as client_name 
                FROM orders o
                LEFT JOIN clients c ON o.client_id = c.id
                ORDER BY o.created_at DESC
                LIMIT 100
            ''')
        
        orders = cursor.fetchall()
        conn.close()
        
        for order in orders:
            client_name = order['client_name'] or 'Без клиента'
            
            # Цвет в зависимости от статуса
            tags = ()
            if order['status'] == 'completed':
                tags = ('completed',)
            elif order['status'] == 'cancelled':
                tags = ('cancelled',)
            elif order['status'] == 'processing':
                tags = ('processing',)
            
            self.orders_tree.insert('', tk.END, values=(
                order['id'],
                order['order_number'],
                client_name,
                f"{order['total_amount']:.2f}",
                order['status'],
                order['created_at']
            ), tags=tags)
        
        # Настройка цветов
        self.orders_tree.tag_configure('completed', background='#d4edda')
        self.orders_tree.tag_configure('cancelled', background='#f8d7da')
        self.orders_tree.tag_configure('processing', background='#fff3cd')
    
    def view_order_details(self):
        """Просмотр деталей заказа"""
        selection = self.orders_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите заказ для просмотра")
            return
        
        item = self.orders_tree.item(selection[0])
        order_id = item['values'][0]
        
        # Получаем детали заказа
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Информация о заказе
        cursor.execute('''
            SELECT o.*, c.full_name as client_name, c.phone, c.email,
                   e.full_name as employee_name
            FROM orders o
            LEFT JOIN clients c ON o.client_id = c.id
            LEFT JOIN employees e ON o.employee_id = e.id
            WHERE o.id = ?
        ''', (order_id,))
        
        order = cursor.fetchone()
        
        # Товары в заказе
        cursor.execute('''
            SELECT oi.*, p.name, p.sku
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = ?
        ''', (order_id,))
        
        items = cursor.fetchall()
        conn.close()
        
        # Создаем диалоговое окно
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Детали заказа №{order['order_number']}")
        dialog.geometry("700x500")
        dialog.transient(self.root)
        
        # Информация о заказе
        info_frame = ttk.LabelFrame(dialog, text="Информация о заказе", padding=10)
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        info_text = f"""
Номер заказа: {order['order_number']}
Дата создания: {order['created_at']}
Статус: {order['status']}
Общая сумма: {order['total_amount']:.2f} руб.

Клиент: {order['client_name'] or 'Не указан'}
Телефон: {order['phone'] or 'Не указан'}
Email: {order['email'] or 'Не указан'}

Сотрудник: {order['employee_name']}

Примечания: {order['notes'] or 'Нет'}
"""
        
        info_label = ttk.Label(info_frame, text=info_text, justify=tk.LEFT)
        info_label.pack(anchor=tk.W)
        
        # Товары в заказе
        items_frame = ttk.LabelFrame(dialog, text="Товары в заказе", padding=10)
        items_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Таблица товаров
        columns = ("Товар", "Артикул", "Кол-во", "Цена", "Сумма")
        items_tree = ttk.Treeview(items_frame, columns=columns, show="headings", height=8)
        
        for col in columns:
            items_tree.heading(col, text=col)
            items_tree.column(col, width=120)
        
        scrollbar = ttk.Scrollbar(items_frame, orient=tk.VERTICAL, command=items_tree.yview)
        items_tree.configure(yscrollcommand=scrollbar.set)
        
        items_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Заполняем таблицу
        for item in items:
            items_tree.insert('', tk.END, values=(
                item['name'],
                item['sku'],
                item['quantity'],
                f"{item['unit_price']:.2f}",
                f"{item['total_price']:.2f}"
            ))
        
        # Кнопки
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        if order['status'] == 'pending' and self.auth.has_permission(self.current_user['role'], 'cashier'):
            ttk.Button(button_frame, text="В обработку", 
                      command=lambda: self.update_order_status(order_id, 'processing')).pack(side=tk.LEFT, padx=5)
        
        if order['status'] == 'processing' and self.auth.has_permission(self.current_user['role'], 'cashier'):
            ttk.Button(button_frame, text="Завершить", style='Success.TButton',
                      command=lambda: self.update_order_status(order_id, 'completed')).pack(side=tk.LEFT, padx=5)
        
        if order['status'] in ['pending', 'processing'] and self.auth.has_permission(self.current_user['role'], 'manager'):
            ttk.Button(button_frame, text="Отменить", style='Danger.TButton',
                      command=lambda: self.update_order_status(order_id, 'cancelled')).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(button_frame, text="Закрыть", command=dialog.destroy).pack(side=tk.RIGHT)
    
    def update_order_status(self, order_id, new_status):
        """Обновление статуса заказа"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            # Получаем текущий статус и данные
            cursor.execute("SELECT status, total_amount FROM orders WHERE id = ?", (order_id,))
            order = cursor.fetchone()
            
            if not order:
                messagebox.showerror("Ошибка", "Заказ не найден")
                return
            
            # Обновляем статус
            cursor.execute('''
                UPDATE orders 
                SET status = ?, 
                    completed_at = CASE WHEN ? = 'completed' THEN CURRENT_TIMESTAMP ELSE completed_at END
                WHERE id = ?
            ''', (new_status, new_status, order_id))
            
            conn.commit()
            
            # Логируем действие
            self.db.log_audit(
                self.current_user['id'],
                f'UPDATE_ORDER_STATUS',
                'orders',
                order_id,
                old_values={'status': order['status']},
                new_values={'status': new_status}
            )
            
            messagebox.showinfo("Успех", f"Статус заказа обновлен на '{new_status}'")
            
            # Если отмена заказа, возвращаем товары на склад
            if new_status == 'cancelled' and order['status'] != 'cancelled':
                self.return_order_items_to_stock(order_id)
            
            # Обновляем список заказов
            self.load_orders()
            
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Ошибка", f"Не удалось обновить статус: {e}")
        finally:
            conn.close()
    
    def return_order_items_to_stock(self, order_id):
        """Возврат товаров на склад при отмене заказа"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        try:
            # Получаем товары из заказа
            cursor.execute("SELECT product_id, quantity FROM order_items WHERE order_id = ?", (order_id,))
            items = cursor.fetchall()
            
            # Возвращаем каждый товар на склад
            for item in items:
                cursor.execute('''
                    UPDATE products 
                    SET quantity = quantity + ?, 
                        last_updated = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (item['quantity'], item['product_id']))
            
            conn.commit()
            
        except Exception as e:
            conn.rollback()
            print(f"Ошибка при возврате товаров: {e}")
        finally:
            conn.close()
    
    def cancel_order(self):
        """Отмена заказа"""
        selection = self.orders_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите заказ для отмены")
            return
        
        item = self.orders_tree.item(selection[0])
        order_id = item['values'][0]
        order_status = item['values'][4]
        
        if order_status in ['completed', 'cancelled']:
            messagebox.showwarning("Внимание", "Нельзя отменить завершенный или уже отмененный заказ")
            return
        
        if messagebox.askyesno("Подтверждение", 
                               f"Вы уверены, что хотите отменить заказ №{item['values'][1]}?\n"
                               "Товары будут возвращены на склад."):
            self.update_order_status(order_id, 'cancelled')
    
    def complete_order(self):
        """Завершение заказа"""
        selection = self.orders_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите заказ для завершения")
            return
        
        item = self.orders_tree.item(selection[0])
        order_id = item['values'][0]
        order_status = item['values'][4]
        
        if order_status != 'processing':
            messagebox.showwarning("Внимание", "Можно завершить только заказы в статусе 'processing'")
            return
        
        if messagebox.askyesno("Подтверждение", 
                               f"Вы уверены, что хотите завершить заказ №{item['values'][1]}?"):
            self.update_order_status(order_id, 'completed')
    
    # Остальные методы (create_reports_tab, create_admin_tab, create_audit_tab и т.д.)
    # остаются без изменений, как в предыдущей версии
    
    def create_reports_tab(self):
        """Вкладка отчетов"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Отчеты")
        
        # Панель инструментов
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Продажи за сегодня", command=self.generate_today_sales_report).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Продажи за месяц", command=self.generate_monthly_sales_report).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Товарный отчет", command=self.generate_inventory_report).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Клиентский отчет", command=self.generate_client_report).pack(side=tk.LEFT, padx=2)
        
        # Область отчета
        report_frame = ttk.LabelFrame(frame, text="Отчет", padding=10)
        report_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.report_text = scrolledtext.ScrolledText(report_frame, height=25, wrap=tk.WORD)
        self.report_text.pack(fill=tk.BOTH, expand=True)
        
        # Статистика внизу
        stats_frame = ttk.Frame(frame)
        stats_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.stats_label = ttk.Label(stats_frame, text="Выберите отчет для генерации", font=('Arial', 10))
        self.stats_label.pack()
    
    def generate_today_sales_report(self):
        """Генерация отчета по продажам за сегодня"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as order_count,
                SUM(total_amount) as total_sales,
                AVG(total_amount) as avg_order
            FROM orders 
            WHERE DATE(created_at) = DATE('now') 
                AND status = 'completed'
        ''')
        
        stats = cursor.fetchone()
        
        cursor.execute('''
            SELECT 
                o.order_number,
                c.full_name as client_name,
                o.total_amount,
                o.created_at,
                COUNT(oi.id) as item_count
            FROM orders o
            LEFT JOIN clients c ON o.client_id = c.id
            LEFT JOIN order_items oi ON o.id = oi.order_id
            WHERE DATE(o.created_at) = DATE('now') 
                AND o.status = 'completed'
            GROUP BY o.id
            ORDER BY o.created_at DESC
        ''')
        
        orders = cursor.fetchall()
        conn.close()
        
        report = "=" * 60 + "\n"
        report += "ОТЧЕТ О ПРОДАЖАХ ЗА СЕГОДНЯ\n"
        report += "=" * 60 + "\n\n"
        
        report += f"Всего заказов: {stats['order_count'] or 0}\n"
        report += f"Общая сумма продаж: {stats['total_sales'] or 0:.2f} руб.\n"
        report += f"Средний чек: {stats['avg_order'] or 0:.2f} руб.\n\n"
        
        report += "ДЕТАЛИ ЗАКАЗОВ:\n"
        report += "-" * 60 + "\n"
        
        for order in orders:
            report += f"Заказ: {order['order_number']}\n"
            report += f"Клиент: {order['client_name'] or 'Без клиента'}\n"
            report += f"Сумма: {order['total_amount']:.2f} руб.\n"
            report += f"Товаров: {order['item_count']}\n"
            report += f"Время: {order['created_at']}\n"
            report += "-" * 40 + "\n"
        
        self.report_text.delete("1.0", tk.END)
        self.report_text.insert("1.0", report)
        
        self.stats_label.config(text=f"Отчет сгенерирован: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Логируем генерацию отчета
        self.db.log_audit(
            self.current_user['id'],
            'GENERATE_TODAY_SALES_REPORT',
            new_values={'order_count': stats['order_count'] or 0, 'total_sales': stats['total_sales'] or 0}
        )
    
    def generate_monthly_sales_report(self):
        """Генерация отчета по продажам за месяц"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                strftime('%Y-%m', created_at) as month,
                COUNT(*) as order_count,
                SUM(total_amount) as total_sales,
                AVG(total_amount) as avg_order
            FROM orders 
            WHERE status = 'completed'
                AND created_at >= date('now', '-6 months')
            GROUP BY strftime('%Y-%m', created_at)
            ORDER BY month DESC
        ''')
        
        monthly_stats = cursor.fetchall()
        
        cursor.execute('''
            SELECT 
                p.name,
                p.sku,
                p.category,
                SUM(oi.quantity) as total_sold,
                SUM(oi.total_price) as total_revenue
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            JOIN orders o ON oi.order_id = o.id
            WHERE o.status = 'completed'
                AND o.created_at >= date('now', '-30 days')
            GROUP BY p.id
            ORDER BY total_revenue DESC
            LIMIT 10
        ''')
        
        top_products = cursor.fetchall()
        conn.close()
        
        report = "=" * 60 + "\n"
        report += "ОТЧЕТ О ПРОДАЖАХ ЗА ПОСЛЕДНИЕ 6 МЕСЯЦЕВ\n"
        report += "=" * 60 + "\n\n"
        
        report += "МЕСЯЧНАЯ СТАТИСТИКА:\n"
        report += "-" * 60 + "\n"
        
        total_orders = 0
        total_sales = 0
        
        for stat in monthly_stats:
            report += f"Месяц: {stat['month']}\n"
            report += f"  Заказов: {stat['order_count']}\n"
            report += f"  Продажи: {stat['total_sales']:.2f} руб.\n"
            report += f"  Средний чек: {stat['avg_order']:.2f} руб.\n"
            report += "-" * 40 + "\n"
            
            total_orders += stat['order_count']
            total_sales += stat['total_sales'] or 0
        
        report += f"\nИТОГО за 6 месяцев:\n"
        report += f"Заказов: {total_orders}\n"
        report += f"Продажи: {total_sales:.2f} руб.\n"
        report += f"Среднемесячные продажи: {total_sales / len(monthly_stats) if monthly_stats else 0:.2f} руб.\n\n"
        
        report += "ТОП-10 ТОВАРОВ ЗА ПОСЛЕДНИЙ МЕСЯЦ:\n"
        report += "-" * 60 + "\n"
        
        for product in top_products:
            report += f"Товар: {product['name']}\n"
            report += f"  Артикул: {product['sku']}\n"
            report += f"  Категория: {product['category'] or 'Без категории'}\n"
            report += f"  Продано: {product['total_sold']} шт.\n"
            report += f"  Выручка: {product['total_revenue']:.2f} руб.\n"
            report += "-" * 40 + "\n"
        
        self.report_text.delete("1.0", tk.END)
        self.report_text.insert("1.0", report)
        
        self.stats_label.config(text=f"Отчет сгенерирован: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Логируем генерацию отчета
        self.db.log_audit(
            self.current_user['id'],
            'GENERATE_MONTHLY_SALES_REPORT',
            new_values={'total_orders': total_orders, 'total_sales': total_sales}
        )
    
    def generate_inventory_report(self):
        """Генерация товарного отчета"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Статистика по товарам
        cursor.execute('''
            SELECT 
                COUNT(*) as total_products,
                SUM(quantity) as total_stock,
                SUM(unit_price * quantity) as total_value,
                AVG(unit_price) as avg_price
            FROM products 
            WHERE is_active = 1
        ''')
        
        stats = cursor.fetchone()
        
        # Товары с низким запасом
        cursor.execute('''
            SELECT 
                name,
                sku,
                category,
                quantity,
                min_quantity,
                unit_price,
                (min_quantity - quantity) as deficit
            FROM products 
            WHERE is_active = 1 
                AND quantity < min_quantity
            ORDER BY deficit DESC
            LIMIT 20
        ''')
        
        low_stock = cursor.fetchall()
        
        # Самые дорогие товары
        cursor.execute('''
            SELECT 
                name,
                sku,
                category,
                quantity,
                unit_price,
                (unit_price * quantity) as stock_value
            FROM products 
            WHERE is_active = 1
            ORDER BY stock_value DESC
            LIMIT 10
        ''')
        
        valuable = cursor.fetchall()
        conn.close()
        
        report = "=" * 60 + "\n"
        report += "ТОВАРНЫЙ ОТЧЕТ\n"
        report += "=" * 60 + "\n\n"
        
        report += "ОБЩАЯ СТАТИСТИКА:\n"
        report += "-" * 60 + "\n"
        report += f"Всего товаров: {stats['total_products'] or 0}\n"
        report += f"Общее количество на складе: {stats['total_stock'] or 0} шт.\n"
        report += f"Общая стоимость запасов: {stats['total_value'] or 0:.2f} руб.\n"
        report += f"Средняя цена товара: {stats['avg_price'] or 0:.2f} руб.\n\n"
        
        report += "ТОВАРЫ С НИЗКИМ ЗАПАСОМ:\n"
        report += "-" * 60 + "\n"
        
        if low_stock:
            for product in low_stock:
                report += f"Товар: {product['name']}\n"
                report += f"  Артикул: {product['sku']}\n"
                report += f"  На складе: {product['quantity']} шт. (мин: {product['min_quantity']})\n"
                report += f"  Дефицит: {product['deficit']} шт.\n"
                report += f"  Цена: {product['unit_price']:.2f} руб.\n"
                report += "-" * 40 + "\n"
        else:
            report += "Нет товаров с низким запасом\n\n"
        
        report += "САМЫЕ ЦЕННЫЕ ЗАПАСЫ:\n"
        report += "-" * 60 + "\n"
        
        for product in valuable:
            report += f"Товар: {product['name']}\n"
            report += f"  Артикул: {product['sku']}\n"
            report += f"  Категория: {product['category'] or 'Без категории'}\n"
            report += f"  Количество: {product['quantity']} шт.\n"
            report += f"  Цена за единицу: {product['unit_price']:.2f} руб.\n"
            report += f"  Стоимость запаса: {product['stock_value']:.2f} руб.\n"
            report += "-" * 40 + "\n"
        
        self.report_text.delete("1.0", tk.END)
        self.report_text.insert("1.0", report)
        
        self.stats_label.config(text=f"Отчет сгенерирован: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Логируем генерацию отчета
        self.db.log_audit(
            self.current_user['id'],
            'GENERATE_INVENTORY_REPORT',
            new_values={'total_products': stats['total_products'] or 0, 'total_value': stats['total_value'] or 0}
        )
    
    def generate_client_report(self):
        """Генерация клиентского отчета"""
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Статистика по клиентам
        cursor.execute('''
            SELECT 
                COUNT(*) as total_clients,
                COUNT(CASE WHEN personal_data_consent = 1 THEN 1 END) as consented_clients,
                COUNT(CASE WHEN DATE(registration_date) = DATE('now') THEN 1 END) as new_today
            FROM clients 
            WHERE is_active = 1
        ''')
        
        stats = cursor.fetchone()
        
        # Самые активные клиенты
        cursor.execute('''
            SELECT 
                c.full_name,
                c.phone,
                c.email,
                COUNT(o.id) as order_count,
                SUM(o.total_amount) as total_spent,
                MAX(o.created_at) as last_order_date
            FROM clients c
            LEFT JOIN orders o ON c.id = o.client_id
            WHERE c.is_active = 1
                AND o.status = 'completed'
            GROUP BY c.id
            HAVING order_count > 0
            ORDER BY total_spent DESC
            LIMIT 10
        ''')
        
        top_clients = cursor.fetchall()
        
        # Новые клиенты за месяц
        cursor.execute('''
            SELECT 
                full_name,
                phone,
                email,
                registration_date
            FROM clients 
            WHERE is_active = 1
                AND registration_date >= date('now', '-30 days')
            ORDER BY registration_date DESC
            LIMIT 10
        ''')
        
        new_clients = cursor.fetchall()
        conn.close()
        
        report = "=" * 60 + "\n"
        report += "КЛИЕНТСКИЙ ОТЧЕТ\n"
        report += "=" * 60 + "\n\n"
        
        report += "ОБЩАЯ СТАТИСТИКА:\n"
        report += "-" * 60 + "\n"
        report += f"Всего клиентов: {stats['total_clients'] or 0}\n"
        report += f"С согласием на обработку данных: {stats['consented_clients'] or 0}\n"
        report += f"Новых клиентов сегодня: {stats['new_today'] or 0}\n\n"
        
        report += "ТОП-10 КЛИЕНТОВ ПО СУММЕ ПОКУПОК:\n"
        report += "-" * 60 + "\n"
        
        if top_clients:
            for client in top_clients:
                report += f"Клиент: {client['full_name']}\n"
                report += f"  Телефон: {client['phone'] or 'Не указан'}\n"
                report += f"  Email: {client['email'] or 'Не указан'}\n"
                report += f"  Заказов: {client['order_count']}\n"
                report += f"  Потрачено: {client['total_spent'] or 0:.2f} руб.\n"
                report += f"  Последний заказ: {client['last_order_date'] or 'Нет заказов'}\n"
                report += "-" * 40 + "\n"
        else:
            report += "Нет данных о покупках клиентов\n\n"
        
        report += "НОВЫЕ КЛИЕНТЫ ЗА ПОСЛЕДНИЙ МЕСЯЦ:\n"
        report += "-" * 60 + "\n"
        
        if new_clients:
            for client in new_clients:
                report += f"Клиент: {client['full_name']}\n"
                report += f"  Телефон: {client['phone'] or 'Не указан'}\n"
                report += f"  Email: {client['email'] or 'Не указан'}\n"
                report += f"  Дата регистрации: {client['registration_date']}\n"
                report += "-" * 40 + "\n"
        else:
            report += "Нет новых клиентов за последний месяц\n"
        
        self.report_text.delete("1.0", tk.END)
        self.report_text.insert("1.0", report)
        
        self.stats_label.config(text=f"Отчет сгенерирован: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Логируем генерацию отчета
        self.db.log_audit(
            self.current_user['id'],
            'GENERATE_CLIENT_REPORT',
            new_values={'total_clients': stats['total_clients'] or 0}
        )
    
    def create_admin_tab(self):
        """Вкладка администрирования"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Администрирование")
        
        # Панель инструментов
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Добавить пользователя", command=self.add_user_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Редактировать", command=self.edit_user_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Блокировать", command=self.toggle_user_status, style='Warning.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Сбросить пароль", command=self.reset_user_password).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Обновить", command=self.load_users).pack(side=tk.LEFT, padx=2)
        
        # Таблица пользователей
        columns = ("ID", "Логин", "ФИО", "Должность", "Роль", "Активен", "Последний вход")
        self.users_tree = ttk.Treeview(frame, columns=columns, show="headings", height=20)
        
        for col in columns:
            self.users_tree.heading(col, text=col)
            self.users_tree.column(col, width=100, minwidth=50)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.users_tree.yview)
        self.users_tree.configure(yscrollcommand=scrollbar.set)
        
        self.users_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Загружаем пользователей
        self.load_users()
    
    def load_users(self):
        """Загрузка пользователей из БД"""
        if not hasattr(self, 'users_tree'):
            return
            
        for item in self.users_tree.get_children():
            self.users_tree.delete(item)
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employees ORDER BY role, username")
        users = cursor.fetchall()
        conn.close()
        
        for user in users:
            is_active = "Да" if user['is_active'] else "Нет"
            last_login = user['last_login'] or "Никогда"
            
            self.users_tree.insert('', tk.END, values=(
                user['id'],
                user['username'],
                user['full_name'],
                user['position'] or '',
                user['role'],
                is_active,
                last_login
            ), tags=('inactive' if not user['is_active'] else ''))
        
        # Настройка цветов для неактивных пользователей
        self.users_tree.tag_configure('inactive', background='#f5f5f5', foreground='gray')
    
    def add_user_dialog(self):
        """Диалог добавления пользователя"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Добавить пользователя")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Поля формы
        fields = [
            ("Логин*", "username"),
            ("Пароль*", "password"),
            ("ФИО*", "full_name"),
            ("Email", "email"),
            ("Телефон", "phone"),
            ("Должность", "position")
        ]
        
        entries = {}
        
        for i, (label_text, field_name) in enumerate(fields):
            ttk.Label(dialog, text=label_text).grid(row=i, column=0, sticky=tk.W, padx=10, pady=5)
            
            if field_name == 'password':
                entry = ttk.Entry(dialog, width=40, show="*")
            else:
                entry = ttk.Entry(dialog, width=40)
            
            entry.grid(row=i, column=1, padx=10, pady=5)
            entries[field_name] = entry
        
        # Роль
        ttk.Label(dialog, text="Роль*").grid(row=len(fields), column=0, sticky=tk.W, padx=10, pady=5)
        role_var = tk.StringVar(value='viewer')
        role_combo = ttk.Combobox(dialog, textvariable=role_var, width=37, state='readonly')
        role_combo['values'] = ('admin', 'manager', 'content_manager', 'cashier', 'viewer')
        role_combo.grid(row=len(fields), column=1, padx=10, pady=5)
        
        # Активен
        active_var = tk.BooleanVar(value=True)
        active_check = ttk.Checkbutton(dialog, text="Активен", variable=active_var)
        active_check.grid(row=len(fields)+1, column=0, columnspan=2, padx=10, pady=10, sticky=tk.W)
        
        def save_user():
            user_data = {
                'username': entries['username'].get().strip(),
                'password': entries['password'].get(),
                'full_name': entries['full_name'].get().strip(),
                'email': entries['email'].get().strip(),
                'phone': entries['phone'].get().strip(),
                'position': entries['position'].get().strip(),
                'role': role_var.get(),
                'is_active': active_var.get()
            }
            
            # Валидация
            if not user_data['username'] or not user_data['password'] or not user_data['full_name']:
                messagebox.showerror("Ошибка", "Логин, пароль и ФИО обязательны для заполнения")
                return
            
            if len(user_data['password']) < Config.PASSWORD_MIN_LENGTH:
                messagebox.showerror("Ошибка", f"Пароль должен быть не менее {Config.PASSWORD_MIN_LENGTH} символов")
                return
            
            # Сохраняем пользователя в БД
            conn = self.db.get_connection()
            cursor = conn.cursor()
            try:
                password_hash = self.db._hash_password(user_data['password'])
                
                cursor.execute('''
                    INSERT INTO employees 
                    (username, password_hash, full_name, email, phone, position, role, is_active, must_change_password)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_data['username'],
                    password_hash,
                    user_data['full_name'],
                    user_data['email'],
                    user_data['phone'],
                    user_data['position'],
                    user_data['role'],
                    1 if user_data['is_active'] else 0,
                    1  # Требовать смену пароля при первом входе
                ))
                
                user_id = cursor.lastrowid
                conn.commit()
                
                # Логируем действие
                self.db.log_audit(
                    self.current_user['id'],
                    'CREATE_USER',
                    'employees',
                    user_id,
                    new_values={k: v for k, v in user_data.items() if k != 'password'}
                )
                
                messagebox.showinfo("Успех", "Пользователь успешно добавлен")
                self.load_users()
                dialog.destroy()
            except sqlite3.IntegrityError:
                messagebox.showerror("Ошибка", "Пользователь с таким логином уже существует")
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Ошибка", f"Не удалось добавить пользователя: {e}")
            finally:
                conn.close()
        
        ttk.Button(dialog, text="Сохранить", command=save_user).grid(
            row=len(fields)+2, column=0, columnspan=2, pady=20
        )
    
    def edit_user_dialog(self):
        """Редактирование пользователя"""
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите пользователя для редактирования")
            return
        
        item = self.users_tree.item(selection[0])
        user_id = item['values'][0]
        
        # Получаем данные пользователя
        conn = self.db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM employees WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        conn.close()
        
        if not user:
            messagebox.showerror("Ошибка", "Пользователь не найден")
            return
        
        # Нельзя редактировать самого себя (админ может через смену пароля)
        if user['id'] == self.current_user['id']:
            messagebox.showwarning("Внимание", "Для изменения своих данных используйте смену пароля")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Редактирование пользователя: {user['username']}")
        dialog.geometry("500x350")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Поля формы
        fields = [
            ("Логин", "username"),
            ("ФИО*", "full_name"),
            ("Email", "email"),
            ("Телефон", "phone"),
            ("Должность", "position")
        ]
        
        entries = {}
        
        for i, (label_text, field_name) in enumerate(fields):
            ttk.Label(dialog, text=label_text).grid(row=i, column=0, sticky=tk.W, padx=10, pady=5)
            
            current_value = user[field_name] if user[field_name] is not None else ""
            
            entry = ttk.Entry(dialog, width=40)
            entry.insert(0, str(current_value))
            entry.grid(row=i, column=1, padx=10, pady=5)
            
            if field_name == 'username':
                entry.config(state='readonly')
            
            entries[field_name] = entry
        
        # Роль
        ttk.Label(dialog, text="Роль*").grid(row=len(fields), column=0, sticky=tk.W, padx=10, pady=5)
        role_var = tk.StringVar(value=user['role'])
        role_combo = ttk.Combobox(dialog, textvariable=role_var, width=37, state='readonly')
        role_combo['values'] = ('admin', 'manager', 'content_manager', 'cashier', 'viewer')
        role_combo.grid(row=len(fields), column=1, padx=10, pady=5)
        
        # Активен
        active_var = tk.BooleanVar(value=bool(user['is_active']))
        active_check = ttk.Checkbutton(dialog, text="Активен", variable=active_var)
        active_check.grid(row=len(fields)+1, column=0, columnspan=2, padx=10, pady=10, sticky=tk.W)
        
        def save_changes():
            user_data = {
                'full_name': entries['full_name'].get().strip(),
                'email': entries['email'].get().strip(),
                'phone': entries['phone'].get().strip(),
                'position': entries['position'].get().strip(),
                'role': role_var.get(),
                'is_active': active_var.get()
            }
            
            # Валидация
            if not user_data['full_name']:
                messagebox.showerror("Ошибка", "ФИО обязательно для заполнения")
                return
            
            # Обновляем данные в БД
            conn = self.db.get_connection()
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    UPDATE employees 
                    SET full_name = ?, email = ?, phone = ?, position = ?, 
                        role = ?, is_active = ?
                    WHERE id = ?
                ''', (
                    user_data['full_name'],
                    user_data['email'],
                    user_data['phone'],
                    user_data['position'],
                    user_data['role'],
                    1 if user_data['is_active'] else 0,
                    user_id
                ))
                
                conn.commit()
                
                # Логируем действие
                self.db.log_audit(
                    self.current_user['id'],
                    'UPDATE_USER',
                    'employees',
                    user_id,
                    old_values=dict(user),
                    new_values=user_data
                )
                
                messagebox.showinfo("Успех", "Данные пользователя обновлены")
                self.load_users()
                dialog.destroy()
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Ошибка", f"Не удалось обновить данные: {e}")
            finally:
                conn.close()
        
        ttk.Button(dialog, text="Сохранить", command=save_changes).grid(
            row=len(fields)+2, column=0, columnspan=2, pady=20
        )
    
    def toggle_user_status(self):
        """Блокировка/разблокировка пользователя"""
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите пользователя")
            return
        
        item = self.users_tree.item(selection[0])
        user_id = item['values'][0]
        username = item['values'][1]
        current_status = item['values'][5] == "Да"
        
        # Нельзя блокировать самого себя
        if user_id == self.current_user['id']:
            messagebox.showwarning("Внимание", "Вы не можете заблокировать себя")
            return
        
        action = "разблокировать" if not current_status else "заблокировать"
        if messagebox.askyesno("Подтверждение", 
                               f"Вы уверены, что хотите {action} пользователя '{username}'?"):
            
            conn = self.db.get_connection()
            cursor = conn.cursor()
            try:
                new_status = 0 if current_status else 1
                cursor.execute("UPDATE employees SET is_active = ? WHERE id = ?", (new_status, user_id))
                conn.commit()
                
                # Логируем действие
                self.db.log_audit(
                    self.current_user['id'],
                    'TOGGLE_USER_STATUS',
                    'employees',
                    user_id,
                    old_values={'is_active': current_status},
                    new_values={'is_active': bool(new_status)}
                )
                
                messagebox.showinfo("Успех", f"Пользователь {action}")
                self.load_users()
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Ошибка", f"Не удалось изменить статус: {e}")
            finally:
                conn.close()
    
    def reset_user_password(self):
        """Сброс пароля пользователя"""
        selection = self.users_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите пользователя")
            return
        
        item = self.users_tree.item(selection[0])
        user_id = item['values'][0]
        username = item['values'][1]
        
        # Нельзя сбросить пароль самому себе
        if user_id == self.current_user['id']:
            messagebox.showwarning("Внимание", "Для смены своего пароля используйте соответствующий пункт")
            return
        
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Сброс пароля для {username}")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="Новый пароль:").pack(anchor=tk.W, padx=20, pady=(20, 5))
        new_pass_entry = ttk.Entry(dialog, width=30, show="*")
        new_pass_entry.pack(padx=20, pady=5)
        
        ttk.Label(dialog, text="Повторите пароль:").pack(anchor=tk.W, padx=20, pady=(10, 5))
        confirm_pass_entry = ttk.Entry(dialog, width=30, show="*")
        confirm_pass_entry.pack(padx=20, pady=5)
        
        def reset_password():
            new_pass = new_pass_entry.get()
            confirm_pass = confirm_pass_entry.get()
            
            if not new_pass or not confirm_pass:
                messagebox.showerror("Ошибка", "Заполните все поля")
                return
            
            if new_pass != confirm_pass:
                messagebox.showerror("Ошибка", "Пароли не совпадают")
                return
            
            if len(new_pass) < Config.PASSWORD_MIN_LENGTH:
                messagebox.showerror("Ошибка", f"Пароль должен быть не менее {Config.PASSWORD_MIN_LENGTH} символов")
                return
            
            if self.db.update_password(user_id, new_pass):
                messagebox.showinfo("Успех", "Пароль успешно сброшен")
                dialog.destroy()
                
                # Логируем сброс пароля
                self.db.log_audit(
                    self.current_user['id'],
                    'RESET_USER_PASSWORD',
                    'employees',
                    user_id
                )
            else:
                messagebox.showerror("Ошибка", "Не удалось сбросить пароль")
        
        ttk.Button(dialog, text="Сбросить пароль", command=reset_password).pack(pady=20)
    
    def create_audit_tab(self):
        """Вкладка аудита"""
        frame = ttk.Frame(self.notebook)
        self.notebook.add(frame, text="Аудит")
        
        # Панель инструментов
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Обновить", command=self.load_audit_logs).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Очистить старые", command=self.clear_old_audit_logs).pack(side=tk.LEFT, padx=2)
        
        # Фильтры
        filter_frame = ttk.Frame(toolbar)
        filter_frame.pack(side=tk.RIGHT)
        
        ttk.Label(filter_frame, text="Дней:").pack(side=tk.LEFT)
        self.audit_days_filter = tk.Spinbox(filter_frame, from_=1, to=365, width=10)
        self.audit_days_filter.pack(side=tk.LEFT, padx=5)
        self.audit_days_filter.delete(0, tk.END)
        self.audit_days_filter.insert(0, "7")
        
        ttk.Button(filter_frame, text="Применить", command=self.load_audit_logs).pack(side=tk.LEFT)
        
        # Таблица аудита
        columns = ("ID", "Дата", "Пользователь", "Действие", "Таблица", "Запись", "IP")
        self.audit_tree = ttk.Treeview(frame, columns=columns, show="headings", height=20)
        
        for col in columns:
            self.audit_tree.heading(col, text=col)
            self.audit_tree.column(col, width=100, minwidth=50)
        
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.audit_tree.yview)
        self.audit_tree.configure(yscrollcommand=scrollbar.set)
        
        self.audit_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Загружаем логи
        self.load_audit_logs()
    
    def load_audit_logs(self):
        """Загрузка логов аудита"""
        if not hasattr(self, 'audit_tree'):
            return
            
        for item in self.audit_tree.get_children():
            self.audit_tree.delete(item)
        
        try:
            days = int(self.audit_days_filter.get())
        except ValueError:
            days = 7
        
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                a.*,
                e.username as employee_username
            FROM audit_log a
            LEFT JOIN employees e ON a.employee_id = e.id
            WHERE a.created_at >= date('now', ?)
            ORDER BY a.created_at DESC
            LIMIT 1000
        ''', (f'-{days} days',))
        
        logs = cursor.fetchall()
        conn.close()
        
        for log in logs:
            employee = log['employee_username'] or 'Система'
            table_name = log['table_name'] or ''
            record_id = log['record_id'] or ''
            
            self.audit_tree.insert('', tk.END, values=(
                log['id'],
                log['created_at'],
                employee,
                log['action'],
                table_name,
                record_id,
                log['ip_address'] or ''
            ))
    
    def clear_old_audit_logs(self):
        """Очистка старых логов аудита"""
        if messagebox.askyesno("Подтверждение", 
                               "Удалить логи аудита старше 30 дней?\n"
                               "Это действие нельзя отменить."):
            
            conn = self.db.get_connection()
            cursor = conn.cursor()
            
            try:
                cursor.execute("DELETE FROM audit_log WHERE created_at < date('now', '-30 days')")
                deleted_count = cursor.rowcount
                conn.commit()
                
                messagebox.showinfo("Успех", f"Удалено {deleted_count} записей аудита")
                self.load_audit_logs()
                
                # Логируем очистку
                self.db.log_audit(
                    self.current_user['id'],
                    'CLEAR_AUDIT_LOGS',
                    new_values={'deleted_count': deleted_count}
                )
            except Exception as e:
                conn.rollback()
                messagebox.showerror("Ошибка", f"Не удалось очистить логи: {e}")
            finally:
                conn.close()
    
    def logout(self):
        """Выход из системы"""
        if self.current_user:
            self.auth.logout(self.current_user['id'], self.current_user.get('token'))
        self.current_user = None
        self.show_login_screen()
    
    def run(self):
        """Запуск приложения"""
        self.root.mainloop()

# Запуск приложения
if __name__ == "__main__":
    app = TradingAppGUI()
    app.run()