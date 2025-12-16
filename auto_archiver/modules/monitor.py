"""
Мониторинг системы - CPU, RAM, диск, сеть, процессы
"""
import os
import sys
import time
import psutil
import platform
import socket
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger("SystemMonitor")

class SystemMonitor:
    def __init__(self, config):
        """
        Инициализация мониторинга системы
        
        Args:
            config: объект конфигурации
        """
        self.config = config
        self.monitor_dir = config.data_dir / "monitoring"
        self.monitor_dir.mkdir(exist_ok=True)
        
        # Файл для хранения истории мониторинга
        self.history_file = self.monitor_dir / "monitoring_history.json"
        self.history = self._load_history()
        
        logger.info("Мониторинг системы инициализирован")
    
    def _load_history(self) -> List[Dict]:
        """Загружает историю мониторинга"""
        if self.history_file.exists():
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []
    
    def _save_history(self):
        """Сохраняет историю мониторинга"""
        # Ограничиваем историю последними 1000 записей
        if len(self.history) > 1000:
            self.history = self.history[-1000:]
        
        with open(self.history_file, 'w', encoding='utf-8') as f:
            json.dump(self.history, f, indent=2, ensure_ascii=False)
    
    def get_system_info(self) -> Dict:
        """
        Получает общую информацию о системе
        
        Returns:
            Dict: информация о системе
        """
        try:
            info = {
                'timestamp': datetime.now().isoformat(),
                'platform': {
                    'system': platform.system(),
                    'release': platform.release(),
                    'version': platform.version(),
                    'machine': platform.machine(),
                    'processor': platform.processor(),
                    'python_version': platform.python_version()
                },
                'host': {
                    'name': socket.gethostname(),
                    'ip': socket.gethostbyname(socket.gethostname())
                },
                'boot_time': datetime.fromtimestamp(psutil.boot_time()).isoformat(),
                'users': [u.name for u in psutil.users()]
            }
            
            return info
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о системе: {e}")
            return {'error': str(e)}
    
    def get_cpu_info(self) -> Dict:
        """
        Получает информацию о CPU
        
        Returns:
            Dict: информация о процессоре
        """
        try:
            cpu_info = {
                'timestamp': datetime.now().isoformat(),
                'physical_cores': psutil.cpu_count(logical=False),
                'logical_cores': psutil.cpu_count(logical=True),
                'usage_percent': psutil.cpu_percent(interval=0.5),
                'per_core_usage': psutil.cpu_percent(interval=0.5, percpu=True),
                'frequency': {
                    'current': psutil.cpu_freq().current if hasattr(psutil.cpu_freq(), 'current') else None,
                    'min': psutil.cpu_freq().min if hasattr(psutil.cpu_freq(), 'min') else None,
                    'max': psutil.cpu_freq().max if hasattr(psutil.cpu_freq(), 'max') else None
                },
                'stats': psutil.cpu_stats()._asdict() if hasattr(psutil, 'cpu_stats') else {}
            }
            
            return cpu_info
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о CPU: {e}")
            return {'error': str(e)}
    
    def get_memory_info(self) -> Dict:
        """
        Получает информацию о памяти
        
        Returns:
            Dict: информация о RAM и swap
        """
        try:
            memory = psutil.virtual_memory()
            swap = psutil.swap_memory()
            
            memory_info = {
                'timestamp': datetime.now().isoformat(),
                'ram': {
                    'total': memory.total,
                    'available': memory.available,
                    'used': memory.used,
                    'free': memory.free,
                    'percent': memory.percent,
                    'total_gb': round(memory.total / (1024**3), 2),
                    'used_gb': round(memory.used / (1024**3), 2),
                    'available_gb': round(memory.available / (1024**3), 2)
                },
                'swap': {
                    'total': swap.total,
                    'used': swap.used,
                    'free': swap.free,
                    'percent': swap.percent,
                    'sin': swap.sin if hasattr(swap, 'sin') else None,
                    'sout': swap.sout if hasattr(swap, 'sout') else None
                }
            }
            
            return memory_info
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о памяти: {e}")
            return {'error': str(e)}
    
    def get_disk_info(self) -> Dict:
        """
        Получает информацию о дисках
        
        Returns:
            Dict: информация о дисковом пространстве
        """
        try:
            partitions = psutil.disk_partitions()
            disk_info = {
                'timestamp': datetime.now().isoformat(),
                'partitions': []
            }
            
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    
                    partition_info = {
                        'device': partition.device,
                        'mountpoint': partition.mountpoint,
                        'fstype': partition.fstype,
                        'total': usage.total,
                        'used': usage.used,
                        'free': usage.free,
                        'percent': usage.percent,
                        'total_gb': round(usage.total / (1024**3), 2),
                        'used_gb': round(usage.used / (1024**3), 2),
                        'free_gb': round(usage.free / (1024**3), 2)
                    }
                    
                    disk_info['partitions'].append(partition_info)
                    
                except Exception as e:
                    logger.warning(f"Ошибка получения информации о разделе {partition.mountpoint}: {e}")
            
            # Информация о IO
            try:
                disk_io = psutil.disk_io_counters()
                disk_info['io'] = disk_io._asdict() if disk_io else {}
            except:
                disk_info['io'] = {}
            
            return disk_info
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о дисках: {e}")
            return {'error': str(e)}
    
    def get_network_info(self) -> Dict:
        """
        Получает информацию о сети
        
        Returns:
            Dict: сетевая информация
        """
        try:
            network_info = {
                'timestamp': datetime.now().isoformat(),
                'interfaces': [],
                'connections': [],
                'io': {}
            }
            
            # Информация о сетевых интерфейсах
            interfaces = psutil.net_if_addrs()
            for interface_name, interface_addresses in interfaces.items():
                interface_info = {
                    'name': interface_name,
                    'addresses': []
                }
                
                for address in interface_addresses:
                    interface_info['addresses'].append({
                        'family': str(address.family),
                        'address': address.address,
                        'netmask': address.netmask if address.netmask else None,
                        'broadcast': address.broadcast if address.broadcast else None
                    })
                
                network_info['interfaces'].append(interface_info)
            
            # Активные соединения
            try:
                connections = psutil.net_connections(kind='inet')
                for conn in connections[:20]:  # Ограничиваем первыми 20 соединениями
                    if conn.laddr and conn.raddr:
                        conn_info = {
                            'local_address': f"{conn.laddr.ip}:{conn.laddr.port}",
                            'remote_address': f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None,
                            'status': conn.status,
                            'pid': conn.pid
                        }
                        network_info['connections'].append(conn_info)
            except:
                pass  # На некоторых системах могут быть проблемы с правами
            
            # Статистика IO
            try:
                net_io = psutil.net_io_counters()
                network_info['io'] = net_io._asdict() if net_io else {}
            except:
                network_info['io'] = {}
            
            return network_info
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о сети: {e}")
            return {'error': str(e)}
    
    def get_processes_info(self, limit: int = 20) -> Dict:
        """
        Получает информацию о процессах
        
        Args:
            limit: максимальное количество процессов
            
        Returns:
            Dict: информация о процессах
        """
        try:
            processes_info = {
                'timestamp': datetime.now().isoformat(),
                'total_processes': len(psutil.pids()),
                'processes': []
            }
            
            # Получаем самые ресурсоемкие процессы
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    processes.append(proc.info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            # Сортируем по использованию CPU
            processes.sort(key=lambda x: x.get('cpu_percent', 0), reverse=True)
            
            # Ограничиваем количество
            for proc in processes[:limit]:
                try:
                    p = psutil.Process(proc['pid'])
                    with p.oneshot():
                        proc_info = {
                            'pid': proc['pid'],
                            'name': proc.get('name', 'N/A'),
                            'cpu_percent': proc.get('cpu_percent', 0),
                            'memory_percent': round(proc.get('memory_percent', 0), 2),
                            'memory_rss': p.memory_info().rss,
                            'memory_vms': p.memory_info().vms,
                            'status': proc.get('status', 'N/A'),
                            'create_time': datetime.fromtimestamp(p.create_time()).isoformat() if p.create_time() else None,
                            'username': p.username() if hasattr(p, 'username') else None,
                            'cmdline': ' '.join(p.cmdline()[:3]) + ('...' if len(p.cmdline()) > 3 else '')
                        }
                        processes_info['processes'].append(proc_info)
                except:
                    continue
            
            return processes_info
            
        except Exception as e:
            logger.error(f"Ошибка получения информации о процессах: {e}")
            return {'error': str(e)}
    
    def get_sensors_info(self) -> Dict:
        """
        Получает информацию с датчиков (температура, вентиляторы)
        
        Returns:
            Dict: информация с датчиков
        """
        try:
            sensors_info = {
                'timestamp': datetime.now().isoformat(),
                'temperatures': [],
                'fans': [],
                'battery': None
            }
            
            # Температура
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        for entry in entries:
                            sensors_info['temperatures'].append({
                                'sensor': name,
                                'label': entry.label or name,
                                'current': entry.current,
                                'high': entry.high,
                                'critical': entry.critical
                            })
            except:
                pass
            
            # Вентиляторы
            try:
                fans = psutil.sensors_fans()
                if fans:
                    for name, entries in fans.items():
                        for entry in entries:
                            sensors_info['fans'].append({
                                'sensor': name,
                                'label': entry.label or name,
                                'current': entry.current
                            })
            except:
                pass
            
            # Батарея
            try:
                battery = psutil.sensors_battery()
                if battery:
                    sensors_info['battery'] = {
                        'percent': battery.percent,
                        'power_plugged': battery.power_plugged,
                        'secsleft': battery.secsleft
                    }
            except:
                pass
            
            return sensors_info
            
        except Exception as e:
            logger.error(f"Ошибка получения информации с датчиков: {e}")
            return {'error': str(e)}
    
    def get_comprehensive_monitoring(self) -> Dict:
        """
        Получает полную информацию о системе
        
        Returns:
            Dict: полная информация мониторинга
        """
        monitoring_data = {
            'timestamp': datetime.now().isoformat(),
            'system': self.get_system_info(),
            'cpu': self.get_cpu_info(),
            'memory': self.get_memory_info(),
            'disk': self.get_disk_info(),
            'network': self.get_network_info(),
            'processes': self.get_processes_info(limit=10),
            'sensors': self.get_sensors_info()
        }
        
        # Сохраняем в историю
        self.history.append({
            'timestamp': monitoring_data['timestamp'],
            'summary': {
                'cpu_usage': monitoring_data['cpu'].get('usage_percent', 0),
                'memory_usage': monitoring_data['memory']['ram'].get('percent', 0) if 'ram' in monitoring_data['memory'] else 0,
                'disk_usage': monitoring_data['disk']['partitions'][0].get('percent', 0) if monitoring_data['disk'].get('partitions') else 0
            }
        })
        
        self._save_history()
        
        return monitoring_data
    
    def get_monitoring_history(self, limit: int = 50) -> List[Dict]:
        """
        Получает историю мониторинга
        
        Args:
            limit: максимальное количество записей
            
        Returns:
            List[Dict]: история мониторинга
        """
        return self.history[-limit:] if self.history else []
    
    def monitor_in_realtime(self, interval: int = 2, duration: int = 30):
        """
        Режим реального времени мониторинга
        
        Args:
            interval: интервал обновления в секундах
            duration: продолжительность мониторинга в секундах
        """
        print(f"\n📊 РЕАЛЬНОЕ ВРЕМЯ МОНИТОРИНГА")
        print(f"Интервал: {interval} сек, Продолжительность: {duration} сек")
        print("=" * 60)
        
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                # Очищаем экран (работает на большинстве систем)
                os.system('cls' if os.name == 'nt' else 'clear')
                
                # Получаем текущие данные
                data = self.get_comprehensive_monitoring()
                
                # Выводим информацию
                print(f"⏱️  Время: {datetime.now().strftime('%H:%M:%S')}")
                print("-" * 60)
                
                # CPU
                cpu = data.get('cpu', {})
                if 'usage_percent' in cpu:
                    cpu_usage = cpu['usage_percent']
                    bar = "█" * int(cpu_usage / 5) + "░" * (20 - int(cpu_usage / 5))
                    print(f"💻 CPU: {cpu_usage:5.1f}% [{bar}]")
                
                # Память
                memory = data.get('memory', {}).get('ram', {})
                if 'percent' in memory and 'used_gb' in memory and 'total_gb' in memory:
                    mem_usage = memory['percent']
                    bar = "█" * int(mem_usage / 5) + "░" * (20 - int(mem_usage / 5))
                    print(f"🧠 RAM: {mem_usage:5.1f}% [{bar}] {memory['used_gb']:.1f}/{memory['total_gb']:.1f} GB")
                
                # Диск
                disk = data.get('disk', {}).get('partitions', [])
                if disk:
                    disk_usage = disk[0].get('percent', 0)
                    bar = "█" * int(disk_usage / 5) + "░" * (20 - int(disk_usage / 5))
                    print(f"💾 Диск: {disk_usage:5.1f}% [{bar}]")
                
                # Процессы
                processes = data.get('processes', {}).get('processes', [])
                if processes:
                    print(f"\n🔝 Топ процессов:")
                    for i, proc in enumerate(processes[:5], 1):
                        name = proc.get('name', 'N/A')[:20]
                        cpu = proc.get('cpu_percent', 0)
                        mem = proc.get('memory_percent', 0)
                        print(f"  {i}. {name:20} CPU:{cpu:5.1f}% MEM:{mem:5.1f}%")
                
                # Сеть
                net_io = data.get('network', {}).get('io', {})
                if 'bytes_sent' in net_io and 'bytes_recv' in net_io:
                    sent_mb = net_io['bytes_sent'] / (1024**2)
                    recv_mb = net_io['bytes_recv'] / (1024**2)
                    print(f"\n🌐 Сеть: ↑ {sent_mb:.1f} MB ↓ {recv_mb:.1f} MB")
                
                print("-" * 60)
                print("Нажмите Ctrl+C для остановки")
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n⏹️  Мониторинг остановлен пользователем")
        except Exception as e:
            logger.error(f"Ошибка в режиме реального времени: {e}")
            print(f"\n❌ Ошибка: {e}")
    
    def save_monitoring_report(self, filename: str = None) -> str:
        """
        Сохраняет отчет мониторинга в файл
        
        Args:
            filename: имя файла (если None - генерируется автоматически)
            
        Returns:
            str: путь к файлу отчета
        """
        if filename is None:
            filename = f"monitoring_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report_file = self.monitor_dir / filename
        
        data = self.get_comprehensive_monitoring()
        
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Отчет сохранен: {report_file}")
        
        return str(report_file)

# Синхронные обертки для удобства
def get_system_info_sync(config):
    monitor = SystemMonitor(config)
    return monitor.get_system_info()

def get_comprehensive_monitoring_sync(config):
    monitor = SystemMonitor(config)
    return monitor.get_comprehensive_monitoring()

def monitor_realtime_sync(config, interval: int = 2, duration: int = 30):
    monitor = SystemMonitor(config)
    monitor.monitor_in_realtime(interval, duration)

def save_report_sync(config, filename: str = None):
    monitor = SystemMonitor(config)
    return monitor.save_monitoring_report(filename)

# Тестирование
if __name__ == "__main__":
    print("🧪 Тест системы мониторинга")
    
    class TestConfig:
        data_dir = Path("test_data")
        data_dir.mkdir(exist_ok=True)
    
    config = TestConfig()
    monitor = SystemMonitor(config)
    
    # Тест получения информации
    print("\n📋 Информация о системе:")
    sys_info = monitor.get_system_info()
    if 'platform' in sys_info:
        print(f"  Система: {sys_info['platform']['system']} {sys_info['platform']['release']}")
        print(f"  Хост: {sys_info['host']['name']}")
    
    print("\n💻 Информация о CPU:")
    cpu_info = monitor.get_cpu_info()
    if 'usage_percent' in cpu_info:
        print(f"  Загрузка CPU: {cpu_info['usage_percent']}%")
        print(f"  Ядер: {cpu_info['logical_cores']}")
    
    print("\n🧠 Информация о памяти:")
    mem_info = monitor.get_memory_info()
    if 'ram' in mem_info:
        ram = mem_info['ram']
        print(f"  RAM: {ram['used_gb']:.1f}/{ram['total_gb']:.1f} GB ({ram['percent']}%)")
    
    print("\n✅ Тест завершен!")