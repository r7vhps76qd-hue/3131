"""
Загрузчик плагинов - динамическая загрузка модулей
"""
import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Type
import logging

logger = logging.getLogger("PluginLoader")

class PluginLoader:
    def __init__(self, config):
        """
        Инициализация загрузчика плагинов
        
        Args:
            config: объект конфигурации
        """
        self.config = config
        self.plugins_dir = self.config.project_root / "plugins"
        self.plugins_dir.mkdir(exist_ok=True)
        
        self.loaded_plugins = {}
        
    def discover_plugins(self, base_package: str = "modules") -> List[str]:
        """
        Обнаруживает доступные плагины/модули
        
        Args:
            base_package: базовый пакет для поиска
            
        Returns:
            List: список найденных модулей
        """
        modules = []
        
        try:
            package = importlib.import_module(base_package)
            package_path = Path(package.__file__).parent
            
            # Ищем все .py файлы
            for py_file in package_path.glob("*.py"):
                if py_file.name != "__init__.py" and not py_file.name.startswith("_"):
                    module_name = f"{base_package}.{py_file.stem}"
                    modules.append(module_name)
            
            # Ищем подпакеты
            for item in package_path.iterdir():
                if item.is_dir() and not item.name.startswith("_"):
                    init_file = item / "__init__.py"
                    if init_file.exists():
                        submodules = self.discover_plugins(f"{base_package}.{item.name}")
                        modules.extend(submodules)
        
        except Exception as e:
            logger.error(f"Ошибка обнаружения плагинов: {e}")
        
        return modules
    
    def load_plugin(self, module_name: str) -> Optional[Any]:
        """
        Загружает плагин/модуль
        
        Args:
            module_name: имя модуля
            
        Returns:
            Any: загруженный модуль или None
        """
        if module_name in self.loaded_plugins:
            return self.loaded_plugins[module_name]
        
        try:
            logger.debug(f"Загрузка плагина: {module_name}")
            module = importlib.import_module(module_name)
            self.loaded_plugins[module_name] = module
            
            # Ищем основной класс в модуле
            plugin_class = self._find_main_class(module)
            
            return {
                'module': module,
                'class': plugin_class,
                'name': module_name,
                'success': True
            }
            
        except ImportError as e:
            logger.error(f"Ошибка импорта {module_name}: {e}")
            return {
                'module': None,
                'class': None,
                'name': module_name,
                'success': False,
                'error': str(e)
            }
        except Exception as e:
            logger.error(f"Ошибка загрузки плагина {module_name}: {e}")
            return {
                'module': None,
                'class': None,
                'name': module_name,
                'success': False,
                'error': str(e)
            }
    
    def _find_main_class(self, module) -> Optional[Type]:
        """
        Ищет основной класс в модуле
        
        Returns:
            Type: найденный класс или None
        """
        classes = []
        
        for name, obj in inspect.getmembers(module):
            if inspect.isclass(obj) and obj.__module__ == module.__name__:
                # Проверяем, что класс не является внутренним
                if not name.startswith('_'):
                    classes.append(obj)
        
        # Предпочитаем классы с именами, похожими на имя модуля
        module_name = module.__name__.split('.')[-1]
        for cls in classes:
            if module_name.lower() in cls.__name__.lower():
                return cls
        
        # Возвращаем первый найденный класс
        if classes:
            return classes[0]
        
        return None
    
    def load_all_plugins(self, base_package: str = "modules") -> Dict:
        """
        Загружает все доступные плагины
        
        Returns:
            Dict: результаты загрузки
        """
        modules = self.discover_plugins(base_package)
        results = []
        
        logger.info(f"Загрузка {len(modules)} плагинов")
        
        for module_name in modules:
            result = self.load_plugin(module_name)
            results.append(result)
        
        summary = {
            'total': len(results),
            'success': sum(1 for r in results if r['success']),
            'failed': sum(1 for r in results if not r['success']),
            'loaded': len(self.loaded_plugins)
        }
        
        return {
            'results': results,
            'summary': summary,
            'plugins': self.loaded_plugins
        }
    
    def get_plugin(self, plugin_name: str) -> Optional[Any]:
        """
        Получает загруженный плагин по имени
        
        Returns:
            Any: плагин или None
        """
        # Пробуем найти в загруженных
        if plugin_name in self.loaded_plugins:
            return self.loaded_plugins[plugin_name]
        
        # Пробуем загрузить
        result = self.load_plugin(plugin_name)
        if result and result['success']:
            return result['module']
        
        return None
    
    def create_plugin_instance(self, plugin_name: str, *args, **kwargs) -> Optional[Any]:
        """
        Создает экземпляр плагина
        
        Returns:
            Any: экземпляр класса или None
        """
        result = self.load_plugin(plugin_name)
        
        if not result or not result['success']:
            return None
        
        module = result['module']
        plugin_class = result['class']
        
        if not plugin_class:
            logger.error(f"Не найден класс в плагине {plugin_name}")
            return None
        
        try:
            # Создаем экземпляр с конфигом
            if 'config' in inspect.signature(plugin_class.__init__).parameters:
                instance = plugin_class(self.config, *args, **kwargs)
            else:
                instance = plugin_class(*args, **kwargs)
            
            return instance
            
        except Exception as e:
            logger.error(f"Ошибка создания экземпляра {plugin_name}: {e}")
            return None
    
    def reload_plugin(self, plugin_name: str) -> Dict:
        """
        Перезагружает плагин
        
        Returns:
            Dict: результат перезагрузки
        """
        try:
            if plugin_name in self.loaded_plugins:
                module = self.loaded_plugins[plugin_name]
                reloaded = importlib.reload(module)
                self.loaded_plugins[plugin_name] = reloaded
                
                return {
                    'plugin': plugin_name,
                    'success': True,
                    'message': 'Плагин перезагружен'
                }
            else:
                return self.load_plugin(plugin_name)
                
        except Exception as e:
            return {
                'plugin': plugin_name,
                'success': False,
                'error': str(e),
                'message': f'Ошибка перезагрузки: {e}'
            }
    
    def list_available_plugins(self) -> List[Dict]:
        """
        Возвращает список доступных плагинов с информацией
        
        Returns:
            List: информация о плагинах
        """
        plugins_info = []
        
        for module_name in self.discover_plugins():
            result = self.load_plugin(module_name)
            
            info = {
                'name': module_name,
                'loaded': result['success'] if result else False,
                'has_class': bool(result['class']) if result else False
            }
            
            if result and result['success'] and result['class']:
                cls = result['class']
                info.update({
                    'class_name': cls.__name__,
                    'docstring': cls.__doc__ or 'Нет описания',
                    'methods': [m for m in dir(cls) if not m.startswith('_')]
                })
            
            plugins_info.append(info)
        
        return plugins_info

# Синхронные обертки
def load_plugins_sync(config, base_package: str = "modules"):
    loader = PluginLoader(config)
    return loader.load_all_plugins(base_package)

def get_plugin_sync(config, plugin_name: str):
    loader = PluginLoader(config)
    return loader.get_plugin(plugin_name)

def create_plugin_instance_sync(config, plugin_name: str, *args, **kwargs):
    loader = PluginLoader(config)
    return loader.create_plugin_instance(plugin_name, *args, **kwargs)

# Тестирование
if __name__ == "__main__":
    print("🧪 Тест загрузчика плагинов")
    
    class TestConfig:
        project_root = Path(".")
    
    config = TestConfig()
    loader = PluginLoader(config)
    
    # Обнаружение плагинов
    plugins = loader.discover_plugins()
    print(f"\n🔍 Обнаружено плагинов: {len(plugins)}")
    for plugin in plugins[:5]:  # Показываем первые 5
        print(f"  • {plugin}")
    
    if len(plugins) > 5:
        print(f"  ... и ещё {len(plugins) - 5}")
    
    # Загрузка всех плагинов
    results = loader.load_all_plugins()
    print(f"\n⚡ Загружено успешно: {results['summary']['success']}/{results['summary']['total']}")
    
    # Список плагинов с информацией
    plugins_info = loader.list_available_plugins()
    print(f"\n📋 Информация о плагинах:")
    for info in plugins_info[:3]:  # Показываем первые 3
        status = "✅" if info['loaded'] else "❌"
        print(f"  {status} {info['name']}")
        if info.get('class_name'):
            print(f"     Класс: {info['class_name']}")
    
    print("\n✅ Тест завершен!")