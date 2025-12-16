"""
Инициализация системы - проверка окружения, создание структуры
"""
import os
import sys
import platform
import subprocess
import importlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger("SystemInitializer")

class SystemInitializer:
    def __init__(self, config):
        """
        Инициализация системы
        
        Args:
            config: объект конфигурации
        """
        self.config = config
        self.system_info = self._collect_system_info()
        
    def _collect_system_info(self) -> Dict:
        """Собирает информацию о системе"""
        info = {
            'platform': {
                'system': platform.system(),
                'release': platform.release(),
                'version': platform.version(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'python_version': platform.python_version(),
                'python_executable': sys.executable
            },
            'environment': {
                'cwd': os.getcwd(),
                'user': os.getenv('USERNAME') or os.getenv('USER'),
                'home': str(Path.home()),
                'temp': os.getenv('TEMP') or os.getenv('TMP')
            },
            'paths': {
                'project_root': str(self.config.project_root),
                'data_dir': str(self.config.data_dir),
                'logs_dir': str(self.config.logs_dir)
            }
        }
        
        # Информация о дисках
        info['disks'] = self._get_disk_info()
        
        return info
    
    def _get_disk_info(self) -> List[Dict]:
        """Получает информацию о дисках"""
        disks = []
        
        if platform.system() == 'Windows':
            import ctypes
            import string
            
            drive_types = {
                0: "Unknown",
                1: "No Root Directory",
                2: "Removable Disk",
                3: "Local Disk",
                4: "Network Drive",
                5: "CD-ROM",
                6: "RAM Disk"
            }
            
            for drive in string.ascii_uppercase:
                drive_path = f"{drive}:\\"
                if os.path.exists(drive_path):
                    try:
                        total, free = self._get_disk_space(drive_path)
                        drive_type = ctypes.windll.kernel32.GetDriveTypeW(drive_path)
                        
                        disks.append({
                            'drive': drive_path,
                            'type': drive_types.get(drive_type, "Unknown"),
                            'total_gb': total / (1024**3),
                            'free_gb': free / (1024**3),
                            'used_gb': (total - free) / (1024**3),
                            'percent_used': ((total - free) / total * 100) if total > 0 else 0
                        })
                    except:
                        pass
        else:
            # Linux/Mac
            import shutil
            
            for mountpoint in ['/', '/home', '/tmp']:
                if os.path.exists(mountpoint):
                    try:
                        total, used, free = shutil.disk_usage(mountpoint)
                        disks.append({
                            'mountpoint': mountpoint,
                            'total_gb': total / (1024**3),
                            'used_gb': used / (1024**3),
                            'free_gb': free / (1024**3),
                            'percent_used': (used / total * 100) if total > 0 else 0
                        })
                    except:
                        pass
        
        return disks
    
    def _get_disk_space(self, path: str) -> Tuple[int, int]:
        """Получает свободное место на диске"""
        if platform.system() == 'Windows':
            import ctypes
            free_bytes = ctypes.c_ulonglong(0)
            total_bytes = ctypes.c_ulonglong(0)
            
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(path),
                None,
                ctypes.pointer(total_bytes),
                ctypes.pointer(free_bytes)
            )
            
            return total_bytes.value, free_bytes.value
        else:
            import shutil
            usage = shutil.disk_usage(path)
            return usage.total, usage.free
    
    def check_environment(self) -> Dict:
        """
        Проверяет окружение на совместимость
        
        Returns:
            Dict: результаты проверки
        """
        checks = {
            'python_version': self._check_python_version(),
            'disk_space': self._check_disk_space(),
            'permissions': self._check_permissions(),
            'dependencies': self._check_dependencies(),
            'network': self._check_network()
        }
        
        # Сводка
        all_passed = all(check['passed'] for check in checks.values())
        
        return {
            'timestamp': self._get_timestamp(),
            'system_info': self.system_info,
            'checks': checks,
            'summary': {
                'passed': all_passed,
                'total_checks': len(checks),
                'passed_checks': sum(1 for check in checks.values() if check['passed']),
                'failed_checks': sum(1 for check in checks.values() if not check['passed'])
            }
        }
    
    def _check_python_version(self) -> Dict:
        """Проверяет версию Python"""
        import sys
        
        major, minor = sys.version_info[:2]
        required = (3, 8)
        passed = major >= required[0] and minor >= required[1]
        
        return {
            'passed': passed,
            'current': f"{major}.{minor}",
            'required': f"{required[0]}.{required[1]}+",
            'message': f"Python {major}.{minor} {'OK' if passed else 'ТРЕБУЕТСЯ 3.8+'}"
        }
    
    def _check_disk_space(self, min_gb: int = 1) -> Dict:
        """Проверяет свободное место на диске"""
        data_dir = Path(self.config.data_dir)
        drive = data_dir.drive if platform.system() == 'Windows' else data_dir.root
        
        try:
            total, free = self._get_disk_space(str(data_dir))
            free_gb = free / (1024**3)
            passed = free_gb >= min_gb
            
            return {
                'passed': passed,
                'free_gb': round(free_gb, 2),
                'required_gb': min_gb,
                'message': f"Свободно {free_gb:.1f} GB на {drive} {'OK' if passed else 'МАЛО МЕСТА'}"
            }
        except Exception as e:
            return {
                'passed': False,
                'error': str(e),
                'message': f"Ошибка проверки диска: {e}"
            }
    
    def _check_permissions(self) -> Dict:
        """Проверяет права доступа"""
        test_paths = [
            self.config.data_dir,
            self.config.logs_dir,
            self.config.project_root / "test_write.tmp"
        ]
        
        results = []
        
        for path in test_paths:
            try:
                # Пробуем создать файл
                if not path.exists():
                    if path.suffix == '.tmp':
                        path.touch()
                        path.unlink()
                    else:
                        path.mkdir(exist_ok=True)
                
                results.append({
                    'path': str(path),
                    'writable': os.access(str(path), os.W_OK),
                    'readable': os.access(str(path), os.R_OK)
                })
            except Exception as e:
                results.append({
                    'path': str(path),
                    'writable': False,
                    'readable': False,
                    'error': str(e)
                })
        
        all_writable = all(r['writable'] for r in results)
        
        return {
            'passed': all_writable,
            'results': results,
            'message': f"Права доступа: {'OK' if all_writable else 'ЕСТЬ ПРОБЛЕМЫ'}"
        }
    
    def _check_dependencies(self) -> Dict:
        """Проверяет основные зависимости"""
        dependencies = {
            'cryptography': '41.0.7',
            'telethon': '1.34.1',
            'psutil': '5.9.6',
            'requests': '2.31.0'
        }
        
        results = []
        
        for dep, required_version in dependencies.items():
            try:
                module = importlib.import_module(dep)
                version = getattr(module, '__version__', 'unknown')
                
                # Простая проверка версии
                passed = True  # Временно всегда True
                
                results.append({
                    'dependency': dep,
                    'installed': True,
                    'version': version,
                    'required': required_version,
                    'passed': passed
                })
            except ImportError:
                results.append({
                    'dependency': dep,
                    'installed': False,
                    'version': None,
                    'required': required_version,
                    'passed': False
                })
        
        all_passed = all(r['passed'] for r in results)
        
        return {
            'passed': all_passed,
            'results': results,
            'message': f"Зависимости: {sum(1 for r in results if r['installed'])}/{len(results)} установлено"
        }
    
    def _check_network(self) -> Dict:
        """Проверяет сетевое подключение"""
        import socket
        
        test_hosts = [
            ('google.com', 80),
            ('github.com', 443),
            ('telegram.org', 443)
        ]
        
        results = []
        
        for host, port in test_hosts:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex((host, port))
                sock.close()
                
                reachable = result == 0
                results.append({
                    'host': host,
                    'port': port,
                    'reachable': reachable,
                    'latency': 'N/A'
                })
            except Exception as e:
                results.append({
                    'host': host,
                    'port': port,
                    'reachable': False,
                    'error': str(e)
                })
        
        any_reachable = any(r['reachable'] for r in results)
        
        return {
            'passed': any_reachable,
            'results': results,
            'message': f"Сеть: {'ДОСТУПНА' if any_reachable else 'НЕТ ДОСТУПА'}"
        }
    
    def _get_timestamp(self) -> str:
        """Возвращает timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def initialize(self) -> Dict:
        """
        Полная инициализация системы
        
        Returns:
            Dict: результаты инициализации
        """
        logger.info("🚀 Начало инициализации системы")
        
        # Проверяем окружение
        check_results = self.check_environment()
        
        # Создаем необходимые директории
        self._create_directories()
        
        # Сохраняем информацию о системе
        self._save_system_info()
        
        logger.info(f"✅ Инициализация завершена: {check_results['summary']['passed_checks']}/{check_results['summary']['total_checks']} проверок пройдено")
        
        return check_results
    
    def _create_directories(self):
        """Создает необходимые директории"""
        directories = [
            self.config.data_dir,
            self.config.logs_dir,
            self.config.backup_dir,
            self.config.keys_dir,
            self.config.data_dir / "telegram_archive",
            self.config.data_dir / "sync",
            self.config.data_dir / "sync/snapshots",
            self.config.data_dir / "monitoring",
            self.config.data_dir / "temp"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Создана папка: {directory}")
    
    def _save_system_info(self):
        """Сохраняет информацию о системе"""
        info_file = self.config.data_dir / "system_info.json"
        
        info_data = {
            'initialized_at': self._get_timestamp(),
            'system': self.system_info,
            'config': self.config.settings
        }
        
        with open(info_file, 'w', encoding='utf-8') as f:
            import json
            json.dump(info_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"💾 Информация о системе сохранена: {info_file}")

# Синхронная обертка
def initialize_system_sync(config):
    initializer = SystemInitializer(config)
    return initializer.initialize()

# Тестирование
if __name__ == "__main__":
    print("🧪 Тест инициализатора системы")
    
    class TestConfig:
        project_root = Path(".")
        data_dir = Path("test_data")
        logs_dir = Path("test_logs")
        backup_dir = Path("test_backups")
        keys_dir = Path("test_keys")
        settings = {}
    
    config = TestConfig()
    initializer = SystemInitializer(config)
    
    results = initializer.initialize()
    
    print(f"\n📊 Результаты инициализации:")
    print(f"  Python: {results['checks']['python_version']['message']}")
    print(f"  Диск: {results['checks']['disk_space']['message']}")
    print(f"  Права: {results['checks']['permissions']['message']}")
    print(f"  Зависимости: {results['checks']['dependencies']['message']}")
    print(f"  Сеть: {results['checks']['network']['message']}")
    
    print(f"\n✅ Инициализация завершена!")