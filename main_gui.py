# main_gui.py - Графический интерфейс (Tkinter)
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
from tkinter import filedialog
import json
from datetime import datetime
from database import Database
from auth import AuthManager
from config import Config

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
        
        # Верхняя панель
        top_frame = ttk.Frame(self.root)
        top_frame.pack(fill=tk.X, padx=10, pady=5)
        
        user_info = f"{self.current_user['full_name']} ({self.current_user['role']})"
        user_label = ttk.Label(top_frame, text=user_info, font=('Arial', 10, 'bold'))
        user_label.pack(side=tk.LEFT)
        
        logout_button = ttk.Button(top_frame, text="Выход", command=self.logout)
        logout_button.pack(side=tk.RIGHT)
        
        # Панель вкладок
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Создаем вкладки в зависимости от роли
        if self.auth.has_permission(self.current_user['role'], 'viewer'):
            self.create_clients_tab(notebook)
            self.create_products_tab(notebook)
        
        if self.auth.has_permission(self.current_user['role'], 'cashier'):
            self.create_orders_tab(notebook)
        
        if self.auth.has_permission(self.current_user['role'], 'manager'):
            self.create_reports_tab(notebook)
        
        if self.current_user['role'] == 'admin':
            self.create_admin_tab(notebook)
            self.create_audit_tab(notebook)
    
    def create_clients_tab(self, notebook):
        """Вкладка управления клиентами"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Клиенты")
        
        # Панель инструментов
        toolbar = ttk.Frame(frame)
        toolbar.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(toolbar, text="Добавить", command=self.add_client_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Редактировать", command=self.edit_client_dialog).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Удалить", command=self.delete_client_dialog, style='Danger.TButton').pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="Обновить", command=self.load_clients).pack(side=tk.LEFT, padx=2)
        
        # Поиск
        search_frame = ttk.Frame(toolbar)
        search_frame.pack(side=tk.RIGHT)
        ttk.Label(search_frame, text="Поиск:").pack(side=tk.LEFT)
        self.client_search_entry = ttk.Entry(search_frame, width=20)
        self.client_search_entry.pack(side=tk.LEFT, padx=5)
        ttk.Button(search_frame, text="Найти", command=self.search_clients).pack(side=tk.LEFT)
        
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
        dialog.geometry("500x600")
        
        # Поля формы
        fields = [
            ("ФИО*", "full_name"),
            ("Телефон", "phone"),
            ("Email", "email"),
            ("Адрес", "address"),
            ("Примечания", "notes")
        ]
        
        entries = {}
        
        for i, (label_text, field_name) in enumerate(fields):
            ttk.Label(dialog, text=label_text).grid(row=i, column=0, sticky=tk.W, padx=10, pady=5)
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
            client_data = {
                'full_name': entries['full_name'].get().strip(),
                'phone': entries['phone'].get().strip(),
                'email': entries['email'].get().strip(),
                'address': entries['address'].get().strip(),
                'notes': entries['notes'].get().strip(),
                'personal_data_consent': consent_var.get()
            }
            
            if not client_data['full_name']:
                messagebox.showerror("Ошибка", "ФИО обязательно для заполнения")
                return
            
            client_id = self.db.create_client(client_data, self.current_user['id'])
            if client_id:
                messagebox.showinfo("Успех", "Клиент успешно добавлен")
                self.load_clients()
                dialog.destroy()
            else:
                messagebox.showerror("Ошибка", "Не удалось добавить клиента")
        
        ttk.Button(dialog, text="Сохранить", command=save_client).grid(
            row=len(fields)+1, column=0, columnspan=2, pady=20
        )
    
    def create_products_tab(self, notebook):
        """Вкладка управления товарами"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Товары")
        
        # ... (аналогично вкладке клиентов)
    
    def create_orders_tab(self, notebook):
        """Вкладка создания заказов"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Заказы")
        
        # ... (реализация вкладки заказов)
    
    def create_reports_tab(self, notebook):
        """Вкладка отчетов"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Отчеты")
        
        # ... (реализация вкладки отчетов)
    
    def create_admin_tab(self, notebook):
        """Вкладка администратора"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Администрирование")
        
        # ... (реализация админ-панели)
    
    def create_audit_tab(self, notebook):
        """Вкладка аудита"""
        frame = ttk.Frame(notebook)
        notebook.add(frame, text="Аудит")
        
        # ... (реализация просмотра логов)
    
    def search_clients(self):
        """Поиск клиентов"""
        search_term = self.client_search_entry.get().strip().lower()
        if not search_term:
            self.load_clients()
            return
        
        for item in self.clients_tree.get_children():
            self.clients_tree.delete(item)
        
        clients = self.db.get_clients(limit=1000)  # Получаем больше записей для поиска
        for client in clients:
            # Проверяем совпадение по разным полям
            if (search_term in client['full_name'].lower() or
                search_term in (client['phone'] or '').lower() or
                search_term in (client['email'] or '').lower() or
                search_term in (client['client_code'] or '').lower()):
                
                self.clients_tree.insert('', tk.END, values=(
                    client['id'],
                    client['client_code'],
                    client['full_name'],
                    client['phone'] or '',
                    client['email'] or '',
                    client['address'] or '',
                    client['registration_date']
                ))
    
    def edit_client_dialog(self):
        """Редактирование клиента"""
        selection = self.clients_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите клиента для редактирования")
            return
        
        # Получаем ID клиента
        item = self.clients_tree.item(selection[0])
        client_id = item['values'][0]
        
        # ... (реализация формы редактирования)
    
    def delete_client_dialog(self):
        """Удаление клиента"""
        selection = self.clients_tree.selection()
        if not selection:
            messagebox.showwarning("Внимание", "Выберите клиента для удаления")
            return
        
        item = self.clients_tree.item(selection[0])
        client_name = item['values'][2]
        
        if messagebox.askyesno("Подтверждение", f"Удалить клиента {client_name}?"):
            # ... (реализация удаления)
            self.load_clients()
    
    def logout(self):
        """Выход из системы"""
        if self.current_user:
            self.auth.logout(self.current_user['id'], self.current_user.get('token'))
        self.current_user = None
        self.show_login_screen()
    
    def run(self):
        """Запуск приложения"""
        self.root.mainloop()