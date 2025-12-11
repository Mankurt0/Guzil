# main.py - Главный запускаемый файл
import sys
import os
import threading
import time
import schedule
from database import Database
from main_gui import TradingAppGUI
from backup_manager import BackupManager
from config import Config

def run_backup_scheduler():
    """Планировщик резервного копирования"""
    backup_manager = BackupManager(Config.DATABASE_PATH, Config.BACKUP_PATH)
    
    # Создаем бэкап каждый день в 2:00
    schedule.every().day.at("02:00").do(backup_manager.create_backup)
    
    # Создаем бэкап при запуске
    backup_manager.create_backup()
    
    while True:
        schedule.run_pending()
        time.sleep(3600)  # Проверка каждый час

def main():
    """Основная функция запуска"""
    print("=" * 60)
    print(f"Запуск системы: {Config.APP_NAME}")
    print("=" * 60)
    
    # Инициализация приложения
    Config.init_app()
    
    # Инициализация базы данных
    try:
        db = Database(Config.DATABASE_PATH)
        print("✓ База данных инициализирована")
    except Exception as e:
        print(f"✗ Ошибка инициализации БД: {e}")
        sys.exit(1)
    
    # Запуск планировщика бэкапов в отдельном потоке
    try:
        backup_thread = threading.Thread(target=run_backup_scheduler, daemon=True)
        backup_thread.start()
        print("✓ Планировщик резервного копирования запущен")
    except Exception as e:
        print(f"✗ Ошибка запуска планировщика: {e}")
    
    # Запуск GUI приложения
    try:
        print("Запуск графического интерфейса...")
        app = TradingAppGUI()
        app.run()
    except Exception as e:
        print(f"✗ Ошибка запуска GUI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()