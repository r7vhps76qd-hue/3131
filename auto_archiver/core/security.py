"""
Базовое шифрование системы
"""
import os
import base64
import hashlib
from pathlib import Path

class EncryptionSystem:
    def __init__(self, config):
        """
        Инициализация системы шифрования
        
        Args:
            config: объект конфигурации
        """
        self.config = config
        self.key = None
        print("✓ Система шифрования инициализирована (режим заглушки)")
    
    def generate_key_from_password(self, password, save_to_file=False):
        """
        Генерация ключа из пароля
        
        Args:
            password: пароль пользователя
            save_to_file: сохранить ли ключ в файл
            
        Returns:
            bytes: сгенерированный ключ
        """
        print(f"✓ Заглушка: Ключ создан из пароля '{password[:3]}...'")
        
        # Простой фейковый ключ для теста
        self.key = b"fake_key_for_testing_1234567890"
        
        if save_to_file:
            key_file = self.config.keys_dir / "master.key"
            with open(key_file, 'w') as f:
                f.write("fake_key_for_testing_1234567890")
            print(f"✓ Файл ключа создан: {key_file}")
        
        return self.key
    
    def load_key_from_file(self):
        """
        Загрузка ключа из файла
        
        Returns:
            bool: успешно ли загружен ключ
        """
        key_file = self.config.keys_dir / "master.key"
        
        if not key_file.exists():
            print("⚠️  Файл ключа не найден. Создайте ключ сначала.")
            return False
        
        with open(key_file, 'r') as f:
            self.key = f.read().encode()
        
        print(f"✓ Ключ загружен из: {key_file}")
        return True
    
    def encrypt_file(self, input_file, output_file=None):
        """
        Шифрование файла (заглушка)
        """
        print(f"✓ Заглушка: Файл '{input_file}' был бы зашифрован")
        
        input_path = Path(input_file)
        if output_file is None:
            output_path = input_path.with_suffix(input_path.suffix + '.enc')
        else:
            output_path = Path(output_file)
        
        # Просто копируем файл с новым расширением
        if input_path.exists():
            with open(input_path, 'rb') as f_in:
                content = f_in.read()
            with open(output_path, 'wb') as f_out:
                f_out.write(content)
        
        return str(output_path)
    
    def decrypt_file(self, input_file, output_file=None):
        """
        Расшифрование файла (заглушка)
        """
        print(f"✓ Заглушка: Файл '{input_file}' был бы расшифрован")
        
        input_path = Path(input_file)
        if output_file is None:
            if input_path.suffix == '.enc':
                output_path = input_path.with_suffix('')
            else:
                output_path = input_path.with_suffix('.decrypted')
        else:
            output_path = Path(output_file)
        
        # Просто копируем файл с другим расширением
        if input_path.exists():
            with open(input_path, 'rb') as f_in:
                content = f_in.read()
            with open(output_path, 'wb') as f_out:
                f_out.write(content)
        
        return str(output_path)
    
    def encrypt_string(self, text):
        """
        Шифрование строки (заглушка - base64)
        """
        # Простая обфускация base64 вместо реального шифрования
        return base64.b64encode(text.encode()).decode()
    
    def decrypt_string(self, encrypted_text):
        """
        Расшифрование строки (заглушка - base64)
        """
        # Деобфускация base64
        return base64.b64decode(encrypted_text).decode()

def calculate_file_hash(file_path, algorithm='sha256'):
    """
    Вычисление хеша файла (реальная функция - работает без библиотек)
    """
    hash_func = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        # Читаем файл частями для больших файлов
        for chunk in iter(lambda: f.read(4096), b""):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()

def simple_obfuscate(text):
    """
    Простая обфускация текста (не безопасно, только для базового скрытия)
    """
    return base64.b64encode(text.encode()).decode()

def simple_deobfuscate(obfuscated_text):
    """
    Деобфускация текста
    """
    return base64.b64decode(obfuscated_text).decode()

# Тестирование
if __name__ == "__main__":
    print("🧪 Тест модуля безопасности:")
    
    # Создаем фейковый config
    class FakeConfig:
        keys_dir = Path("keys_test")
        keys_dir.mkdir(exist_ok=True)
    
    config = FakeConfig()
    enc = EncryptionSystem(config)
    
    # Тест строки
    text = "Секретное сообщение"
    encrypted = enc.encrypt_string(text)
    decrypted = enc.decrypt_string(encrypted)
    
    print(f"Текст: {text}")
    print(f"Зашифрованный: {encrypted[:30]}...")
    print(f"Расшифрованный: {decrypted}")
    
    if text == decrypted:
        print("✅ Тест пройден!")
    else:
        print("❌ Тест не пройден!")