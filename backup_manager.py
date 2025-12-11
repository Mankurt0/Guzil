# backup_manager.py - Менеджер резервного копирования
import shutil
import sqlite3
from datetime import datetime, timedelta
import zipfile
import os
import json

class BackupManager:
    def __init__(self, db_path: str, backup_dir: str = 'backups'):
        self.db_path = db_path
        self.backup_dir = backup_dir
        
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
    
    def create_backup(self) -> str:
        """Создание резервной копии базы данных"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"backup_{timestamp}.db"
            backup_path = os.path.join(self.backup_dir, backup_name)
            
            # Копируем файл БД
            shutil.copy2(self.db_path, backup_path)
            
            # Создаем метаданные бэкапа
            metadata = {
                'timestamp': timestamp,
                'filename': backup_name,
                'size': os.path.getsize(backup_path),
                'database': self.db_path
            }
            
            # Сохраняем метаданные
            meta_path = os.path.join(self.backup_dir, f"metadata_{timestamp}.json")
            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            # Создаем zip-архив
            zip_name = f"backup_{timestamp}.zip"
            zip_path = os.path.join(self.backup_dir, zip_name)
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(backup_path, arcname=backup_name)
                zipf.write(meta_path, arcname=f"metadata_{timestamp}.json")
            
            # Удаляем несжатые файлы
            os.remove(backup_path)
            os.remove(meta_path)
            
            print(f"✓ Создан бэкап: {zip_path}")
            
            # Очищаем старые бэкапы
            self.cleanup_old_backups()
            
            return zip_path
        except Exception as e:
            print(f"✗ Ошибка при создании бэкапа: {e}")
            return None
    
    def cleanup_old_backups(self, days_to_keep: int = 30):
        """Удаление старых резервных копий"""
        try:
            cutoff = datetime.now() - timedelta(days=days_to_keep)
            
            for filename in os.listdir(self.backup_dir):
                if not filename.endswith('.zip'):
                    continue
                    
                filepath = os.path.join(self.backup_dir, filename)
                if os.path.isfile(filepath):
                    file_time = datetime.fromtimestamp(os.path.getmtime(filepath))
                    if file_time < cutoff:
                        os.remove(filepath)
                        print(f"✓ Удален старый бэкап: {filename}")
        except Exception as e:
            print(f"✗ Ошибка при очистке бэкапов: {e}")
    
    def restore_backup(self, backup_path: str) -> bool:
        """Восстановление из резервной копии"""
        try:
            # Создаем резервную копию текущей БД перед восстановлением
            temp_backup = self.create_backup()
            print(f"✓ Создана резервная копия перед восстановлением: {temp_backup}")
            
            # Распаковываем архив
            temp_dir = 'temp_restore'
            os.makedirs(temp_dir, exist_ok=True)
            
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(temp_dir)
            
            # Ищем файл БД в распакованных файлах
            db_file = None
            for file in os.listdir(temp_dir):
                if file.endswith('.db'):
                    db_file = os.path.join(temp_dir, file)
                    break
            
            if not db_file:
                print("✗ Файл базы данных не найден в архиве")
                return False
            
            # Заменяем текущую БД
            shutil.copy2(db_file, self.db_path)
            
            # Очищаем временные файлы
            shutil.rmtree(temp_dir)
            
            print(f"✓ Восстановление завершено из: {backup_path}")
            return True
        except Exception as e:
            print(f"✗ Ошибка при восстановлении: {e}")
            return False
    
    def list_backups(self) -> list:
        """Список доступных резервных копий"""
        backups = []
        
        try:
            for filename in os.listdir(self.backup_dir):
                if filename.endswith('.zip'):
                    filepath = os.path.join(self.backup_dir, filename)
                    stat = os.stat(filepath)
                    
                    backup_info = {
                        'filename': filename,
                        'path': filepath,
                        'size': stat.st_size,
                        'created': datetime.fromtimestamp(stat.st_mtime),
                        'age_days': (datetime.now() - datetime.fromtimestamp(stat.st_mtime)).days
                    }
                    
                    backups.append(backup_info)
            
            # Сортируем по дате создания (новые сначала)
            backups.sort(key=lambda x: x['created'], reverse=True)
            
            return backups
        except Exception as e:
            print(f"✗ Ошибка при получении списка бэкапов: {e}")
            return []