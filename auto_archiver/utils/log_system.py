"""
Система логирования
"""
import logging
import sys
from pathlib import Path
from datetime import datetime

class Logger:
    def __init__(self, name="AutoArchiver"):
        self.logger = logging.getLogger(name)
        self.logger.setLevel(logging.DEBUG)
        
        # Формат логов
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Консольный вывод
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        
        # Файловый вывод
        log_file = Path(__file__).parent.parent / "logs" / f"system_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        
        # Добавляем обработчики
        self.logger.addHandler(console_handler)
        self.logger.addHandler(file_handler)
    
    def get_logger(self):
        return self.logger
    
    def info(self, message):
        self.logger.info(message)
    
    def error(self, message):
        self.logger.error(message)
    
    def warning(self, message):
        self.logger.warning(message)
    
    def debug(self, message):
        self.logger.debug(message)

# Глобальный логгер
logger = Logger().get_logger()

# Тестируем
if __name__ == "__main__":
    logger.info("Тест логгера: информация")
    logger.error("Тест логгера: ошибка")
    logger.warning("Тест логгера: предупреждение")
    print(f"✓ Логи записываются в папку logs/")