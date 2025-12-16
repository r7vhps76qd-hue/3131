"""
Управление зависимостями - установка, обновление, проверка
"""
import subprocess
import sys
import importlib
import pkg_resources
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger("DependencyManager")

class DependencyManager:
    def __init__(self, config):
        """
        Инициализация менеджера зависимостей
        
        Args:
            config: объект конфигурации
        """
        self.config = config
        self.dependencies_file = self.config.project_root / "requirements.txt"
        
    def load_dependencies(self) -> Dict[str, str]:
        """
        Загружает зависимости из requirements.txt
        
        Returns:
            Dict: зависимости {имя: версия}
        """
        dependencies = {}
        
        if not self.dependencies_file.exists():
            logger.warning(f"Файл зависимостей не найден: {self.dependencies_file}")
            return dependencies
        
        try:
            with open(self.dependencies_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    
                    # Пропускаем комментарии и пустые строки
                    if not line or line.startswith('#'):
                        continue
                    
                    # Парсим зависимость
                    parts = line.split('==')
                    if len(parts) == 2:
                        name, version = parts[0].strip(), parts[1].strip()
                        dependencies[name] = version
                    else:
                        # Без версии
                        dependencies[line.strip()] = 'any'
            
            logger.info(f"Загружено {len(dependencies)} зависимостей")
            return dependencies
            
        except Exception as e:
            logger.error(f"Ошибка загрузки зависимостей: {e}")
            return {}
    
    def check_installed(self, package_name: str) -> Tuple[bool, Optional[str]]:
        """
        Проверяет, установлен ли пакет
        
        Returns:
            Tuple: (установлен, версия)
        """
        try:
            # Пробуем через pkg_resources
            version = pkg_resources.get_distribution(package_name).version
            return True, version
        except pkg_resources.DistributionNotFound:
            # Пробуем через importlib
            try:
                module = importlib.import_module(package_name)
                version = getattr(module, '__version__', None)
                if version:
                    return True, version
                else:
                    return True, 'unknown'
            except ImportError:
                return False, None
        except Exception as e:
            logger.debug(f"Ошибка проверки пакета {package_name}: {e}")
            return False, None
    
    def check_all_dependencies(self) -> Dict:
        """
        Проверяет все зависимости
        
        Returns:
            Dict: статус зависимостей
        """
        dependencies = self.load_dependencies()
        results = []
        
        for package, required_version in dependencies.items():
            installed, current_version = self.check_installed(package)
            
            # Проверяем совместимость версий
            compatible = True
            if installed and required_version != 'any' and current_version != 'unknown':
                # Простая проверка - можно улучшить
                try:
                    if current_version != required_version:
                        compatible = False
                except:
                    compatible = True
            
            results.append({
                'package': package,
                'required': required_version,
                'installed': installed,
                'current': current_version,
                'compatible': compatible,
                'status': 'OK' if installed and compatible else 'MISSING' if not installed else 'WRONG_VERSION'
            })
        
        summary = {
            'total': len(results),
            'installed': sum(1 for r in results if r['installed']),
            'compatible': sum(1 for r in results if r['compatible']),
            'missing': sum(1 for r in results if not r['installed']),
            'wrong_version': sum(1 for r in results if r['installed'] and not r['compatible'])
        }
        
        return {
            'dependencies': results,
            'summary': summary,
            'all_ok': summary['missing'] == 0 and summary['wrong_version'] == 0
        }
    
    def install_dependency(self, package_name: str, version: str = None) -> Dict:
        """
        Устанавливает одну зависимость
        
        Returns:
            Dict: результат установки
        """
        try:
            if version and version != 'any':
                package_spec = f"{package_name}=={version}"
            else:
                package_spec = package_name
            
            logger.info(f"Установка: {package_spec}")
            
            # Запускаем pip install
            cmd = [sys.executable, "-m", "pip", "install", package_spec]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5 минут
            )
            
            success = result.returncode == 0
            
            return {
                'package': package_name,
                'success': success,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'message': f"Установка {'успешна' if success else 'не удалась'}"
            }
            
        except subprocess.TimeoutExpired:
            return {
                'package': package_name,
                'success': False,
                'error': 'TIMEOUT',
                'message': 'Таймаут установки'
            }
        except Exception as e:
            return {
                'package': package_name,
                'success': False,
                'error': str(e),
                'message': f'Ошибка: {e}'
            }
    
    def install_all_dependencies(self, force: bool = False) -> Dict:
        """
        Устанавливает все зависимости
        
        Args:
            force: переустановить даже если уже установлены
            
        Returns:
            Dict: результаты установки
        """
        dependencies = self.load_dependencies()
        results = []
        
        logger.info(f"Установка {len(dependencies)} зависимостей")
        
        for package, version in dependencies.items():
            # Проверяем, нужно ли устанавливать
            if not force:
                installed, current_version = self.check_installed(package)
                if installed:
                    logger.info(f"Пропуск: {package} уже установлен")
                    results.append({
                        'package': package,
                        'skipped': True,
                        'reason': 'already_installed',
                        'current_version': current_version
                    })
                    continue
            
            # Устанавливаем
            result = self.install_dependency(package, version)
            results.append(result)
            
            # Пауза между установками
            import time
            time.sleep(1)
        
        # Сводка
        total = len(results)
        installed = sum(1 for r in results if r.get('success', False))
        skipped = sum(1 for r in results if r.get('skipped', False))
        failed = total - installed - skipped
        
        return {
            'results': results,
            'summary': {
                'total': total,
                'installed': installed,
                'skipped': skipped,
                'failed': failed,
                'success': failed == 0
            }
        }
    
    def update_dependency(self, package_name: str) -> Dict:
        """
        Обновляет зависимость
        
        Returns:
            Dict: результат обновления
        """
        try:
            logger.info(f"Обновление: {package_name}")
            
            cmd = [sys.executable, "-m", "pip", "install", "--upgrade", package_name]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            success = result.returncode == 0
            
            # Получаем новую версию
            installed, new_version = self.check_installed(package_name)
            
            return {
                'package': package_name,
                'success': success,
                'new_version': new_version,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'message': f"Обновление {'успешно' if success else 'не удалось'}"
            }
            
        except Exception as e:
            return {
                'package': package_name,
                'success': False,
                'error': str(e),
                'message': f'Ошибка: {e}'
            }
    
    def uninstall_dependency(self, package_name: str) -> Dict:
        """
        Удаляет зависимость
        
        Returns:
            Dict: результат удаления
        """
        try:
            logger.info(f"Удаление: {package_name}")
            
            cmd = [sys.executable, "-m", "pip", "uninstall", "-y", package_name]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            success = result.returncode == 0
            
            return {
                'package': package_name,
                'success': success,
                'returncode': result.returncode,
                'stdout': result.stdout,
                'stderr': result.stderr,
                'message': f"Удаление {'успешно' if success else 'не удалось'}"
            }
            
        except Exception as e:
            return {
                'package': package_name,
                'success': False,
                'error': str(e),
                'message': f'Ошибка: {e}'
            }
    
    def create_requirements_file(self, dependencies: Dict[str, str] = None):
        """
        Создает/обновляет requirements.txt
        
        Args:
            dependencies: зависимости {имя: версия}
        """
        if dependencies is None:
            # Получаем текущие установленные пакеты
            dependencies = self._get_installed_packages()
        
        try:
            with open(self.dependencies_file, 'w', encoding='utf-8') as f:
                f.write("# Зависимости AutoArchiver\n")
                f.write("# Сгенерировано автоматически\n\n")
                
                for package, version in sorted(dependencies.items()):
                    if version and version != 'unknown':
                        f.write(f"{package}=={version}\n")
                    else:
                        f.write(f"{package}\n")
            
            logger.info(f"Файл зависимостей создан: {self.dependencies_file}")
            
        except Exception as e:
            logger.error(f"Ошибка создания файла зависимостей: {e}")
    
    def _get_installed_packages(self) -> Dict[str, str]:
        """Получает список установленных пакетов"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "freeze"],
                capture_output=True,
                text=True
            )
            
            packages = {}
            for line in result.stdout.strip().split('\n'):
                if line and '==' in line:
                    parts = line.split('==')
                    if len(parts) == 2:
                        packages[parts[0]] = parts[1]
            
            return packages
            
        except Exception as e:
            logger.error(f"Ошибка получения установленных пакетов: {e}")
            return {}

# Синхронные обертки
def check_dependencies_sync(config):
    manager = DependencyManager(config)
    return manager.check_all_dependencies()

def install_dependencies_sync(config, force: bool = False):
    manager = DependencyManager(config)
    return manager.install_all_dependencies(force)

def update_dependency_sync(config, package_name: str):
    manager = DependencyManager(config)
    return manager.update_dependency(package_name)

# Тестирование
if __name__ == "__main__":
    print("🧪 Тест менеджера зависимостей")
    
    class TestConfig:
        project_root = Path(".")
    
    config = TestConfig()
    manager = DependencyManager(config)
    
    # Проверка зависимостей
    check_result = manager.check_all_dependencies()
    
    print(f"\n📦 Проверка зависимостей:")
    print(f"  Всего: {check_result['summary']['total']}")
    print(f"  Установлено: {check_result['summary']['installed']}")
    print(f"  Отсутствует: {check_result['summary']['missing']}")
    
    # Пример установки (закомментировано)
    # print("\n⚡ Установка тестовой зависимости:")
    # result = manager.install_dependency("colorama")
    # print(f"  Результат: {result['message']}")
    
    print("\n✅ Тест завершен!")