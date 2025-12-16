"""
Конфигурация системы - настройки по умолчанию
"""
import json
import os
from pathlib import Path

class Config:
    def __init__(self):
        # Базовые пути
        self.project_root = Path(__file__).parent.parent
        self.data_dir = self.project_root / "data"
        self.logs_dir = self.project_root / "logs"
        self.backup_dir = self.project_root / "backups"
        
        # Создаем необходимые папки
        self._create_directories()
        
        # ДОБАВЛЯЕМ ПУТЬ ДЛЯ КЛЮЧЕЙ
        self.keys_dir = self.project_root / "keys"
        self.keys_dir.mkdir(exist_ok=True)
        
        # Настройки по умолчанию
        self.settings = {
            "system": {
                "name": "AutoArchiver",
                "version": "0.1.0",
                "debug": True
            },
            # ДОБАВЛЕНО: НАСТРОЙКИ ШИФРОВАНИЯ
            "encryption": {
                "enabled": True,
                "algorithm": "AES-256",
                "key_size": 32,  # 256 бит
                "salt_size": 16,
                "iterations": 100000  # для PBKDF2
            },
            "logging": {
                "level": "INFO",
                "max_size_mb": 10,
                "backup_count": 5
            },
            "storage": {
                "max_disk_usage_percent": 80,
                "compression_enabled": True,
                "encryption_enabled": False  # Пока выключим для простоты
            },
            "telegram": {
                "session_name": "my_session",
                "api_id": None,  # Заполнить позже
                "api_hash": None  # Заполнить позже
            }
        }
    
    def _create_directories(self):
        """Создает все необходимые папки"""
        directories = [self.data_dir, self.logs_dir, self.backup_dir]
        for directory in directories:
            directory.mkdir(exist_ok=True)
            print(f"✓ Создана папка: {directory}")
    
    def save(self):
        """Сохраняет конфиг в файл"""
        config_file = self.project_root / "config.json"
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=4, ensure_ascii=False)
        print(f"✓ Конфиг сохранен: {config_file}")
    
    def load(self):
        """Загружает конфиг из файла"""
        config_file = self.project_root / "config.json"
        if config_file.exists():
            with open(config_file, 'r', encoding='utf-8') as f:
                self.settings.update(json.load(f))
            print(f"✓ Конфиг загружен: {config_file}")
            return True
        return False
    
    def get(self, key_path, default=None):
        """Получает значение из конфига по пути (например: 'system.name')"""
        keys = key_path.split('.')
        value = self.settings
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set(self, key_path, value):
        """Устанавливает значение в конфиг"""
        keys = key_path.split('.')
        current = self.settings
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
        print(f"✓ Настройка обновлена: {key_path} = {value}")

# Глобальный экземпляр конфигурации
config = Config()

# Тестируем конфиг
if __name__ == "__main__":
    print(f"Имя системы: {config.get('system.name')}")
    print(f"Версия: {config.get('system.version')}")
    print(f"Шифрование включено: {config.get('encryption.enabled')}")
    print(f"Алгоритм: {config.get('encryption.algorithm')}")
    print(f"Папка ключей: {config.keys_dir}")
    config.save()