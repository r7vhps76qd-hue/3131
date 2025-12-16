"""
Детекция виртуальных машин, песочниц и окружений анализа
"""
import os
import sys
import platform
import subprocess
import ctypes
import winreg  # Только для Windows
from typing import Dict, List, Optional
import logging

logger = logging.getLogger("VMDetector")

class VMDetector:
    def __init__(self):
        """Инициализация детектора VM"""
        self.is_windows = platform.system() == 'Windows'
        self.is_linux = platform.system() == 'Linux'
        self.is_macos = platform.system() == 'Darwin'
        
        self.detection_methods = []
        self.vm_indicators = []
        
    def detect_all(self) -> Dict:
        """
        Запускает все методы детекции
        
        Returns:
            Dict: результаты детекции
        """
        results = {
            'is_vm': False,
            'is_sandbox': False,
            'is_debugged': False,
            'vm_type': None,
            'confidence': 0,
            'detections': [],
            'indicators': []
        }
        
        # Собираем все методы детекции
        detection_methods = [
            self.detect_by_cpu,
            self.detect_by_mac,
            self.detect_by_processes,
            self.detect_by_files,
            self.detect_by_registry,
            self.detect_by_memory,
            self.detect_by_hardware,
            self.detect_by_network,
            self.detect_by_system,
            self.detect_debugger
        ]
        
        # Запускаем методы
        for method in detection_methods:
            try:
                result = method()
                if result:
                    results['detections'].append(result)
                    if result.get('detected', False):
                        results['indicators'].append(result)
                        
                        if result.get('type') == 'vm':
                            results['is_vm'] = True
                            if not results['vm_type']:
                                results['vm_type'] = result.get('vm_type')
                        elif result.get('type') == 'sandbox':
                            results['is_sandbox'] = True
                        elif result.get('type') == 'debugger':
                            results['is_debugged'] = True
            except Exception as e:
                logger.debug(f"Ошибка в методе детекции: {e}")
        
        # Рассчитываем уверенность
        total_weight = sum(ind.get('weight', 1) for ind in results['indicators'])
        max_weight = len(results['indicators']) * 10
        if max_weight > 0:
            results['confidence'] = min(100, int((total_weight / max_weight) * 100))
        
        # Логируем результат
        status = []
        if results['is_vm']:
            status.append(f"ВМ ({results['vm_type'] or 'unknown'})")
        if results['is_sandbox']:
            status.append("Песочница")
        if results['is_debugged']:
            status.append("Отладка")
        
        if status:
            logger.warning(f"⚠️ Обнаружено: {', '.join(status)} (уверенность: {results['confidence']}%)")
        else:
            logger.info("✅ Окружение выглядит чистым")
        
        return results
    
    def detect_by_cpu(self) -> Optional[Dict]:
        """Детекция по характеристикам CPU"""
        indicators = []
        
        try:
            import cpuinfo  # Нужно установить: pip install py-cpuinfo
            
            cpu_info = cpuinfo.get_cpu_info()
            brand = cpu_info.get('brand_raw', '').lower()
            
            # Известные VM CPU
            vm_cpu_indicators = [
                'virtualbox', 'vmware', 'qemu', 'kvm', 
                'hyper-v', 'xen', 'parallels', 'virtual',
                'hvm', 'cloud', 'amazon ec2', 'google compute engine'
            ]
            
            for indicator in vm_cpu_indicators:
                if indicator in brand:
                    indicators.append({
                        'method': 'cpu_brand',
                        'indicator': indicator,
                        'weight': 8
                    })
            
            # Проверка количества ядер (VM часто имеют круглые числа)
            cores = cpu_info.get('count', 0)
            if cores in [1, 2, 4, 8, 16, 32, 64]:
                indicators.append({
                    'method': 'cpu_cores_round',
                    'indicator': f'{cores} cores',
                    'weight': 2
                })
            
        except ImportError:
            # Альтернативные методы без cpuinfo
            try:
                if self.is_windows:
                    import wmi
                    c = wmi.WMI()
                    for processor in c.Win32_Processor():
                        name = processor.Name.lower()
                        for indicator in ['virtual', 'vmware', 'virtualbox']:
                            if indicator in name:
                                indicators.append({
                                    'method': 'wmi_cpu',
                                    'indicator': indicator,
                                    'weight': 7
                                })
            except:
                pass
        
        if indicators:
            return {
                'type': 'vm',
                'method': 'cpu',
                'detected': True,
                'indicators': indicators,
                'vm_type': self._guess_vm_type(indicators)
            }
        
        return None
    
    def detect_by_mac(self) -> Optional[Dict]:
        """Детекция по MAC-адресу"""
        if not self.is_windows and not self.is_linux:
            return None
        
        indicators = []
        
        try:
            import uuid
            mac = ':'.join(['{:02x}'.format((uuid.getnode() >> ele) & 0xff) 
                           for ele in range(0, 8*6, 8)][::-1]).lower()
            
            # Известные VM MAC адреса
            vm_mac_prefixes = [
                '00:05:69',  # VMware
                '00:0c:29',  # VMware
                '00:1c:14',  # VMware
                '00:50:56',  # VMware
                '08:00:27',  # VirtualBox
                '0a:00:27',  # VirtualBox
                '00:16:3e',  # Xen
                '00:1c:42',  # Parallels
                '00:0f:4b',  # Virtual Iron
                '00:15:5d',  # Hyper-V
            ]
            
            for prefix in vm_mac_prefixes:
                if mac.startswith(prefix):
                    indicators.append({
                        'method': 'mac_prefix',
                        'indicator': prefix,
                        'weight': 9
                    })
                    
                    # Определяем тип VM
                    if 'vmware' in prefix:
                        vm_type = 'VMware'
                    elif 'virtualbox' in prefix:
                        vm_type = 'VirtualBox'
                    elif 'xen' in prefix:
                        vm_type = 'Xen'
                    elif 'parallels' in prefix:
                        vm_type = 'Parallels'
                    elif 'hyper-v' in prefix:
                        vm_type = 'Hyper-V'
                    else:
                        vm_type = 'Unknown VM'
                    
                    return {
                        'type': 'vm',
                        'method': 'mac',
                        'detected': True,
                        'indicators': indicators,
                        'vm_type': vm_type,
                        'mac': mac
                    }
        
        except Exception as e:
            logger.debug(f"Ошибка детекции по MAC: {e}")
        
        return None
    
    def detect_by_processes(self) -> Optional[Dict]:
        """Детекция по запущенным процессам"""
        indicators = []
        
        # Процессы характерные для VM/песочниц
        vm_processes = [
            'vbox', 'vmware', 'vmtools', 'vmrawdsk', 'vmmemctl',
            'vmusr', 'vmacthlp', 'vmsrvc', 'vboxtray',
            'xenservice', 'prl_cc', 'prl_tools', 'qemu-ga',
            'vdagent', 'vgauthservice'
        ]
        
        sandbox_processes = [
            'cuckoo', 'sandbox', 'anubis', 'joebox',
            'threat', 'malware', 'analyse', 'detect'
        ]
        
        debugger_processes = [
            'ollydbg', 'windbg', 'x64dbg', 'ida', 'immunity',
            'ghidra', 'radare', 'cheatengine', 'processhacker',
            'procmon', 'wireshark', 'fiddler', 'burp'
        ]
        
        try:
            if self.is_windows:
                import wmi
                c = wmi.WMI()
                processes = [p.Name.lower() for p in c.Win32_Process()]
            elif self.is_linux:
                processes = []
                for pid in os.listdir('/proc'):
                    if pid.isdigit():
                        try:
                            with open(f'/proc/{pid}/comm', 'r') as f:
                                processes.append(f.read().strip().lower())
                        except:
                            pass
            else:
                processes = []
            
            # Проверяем процессы
            detected_type = None
            
            for proc in processes:
                for vm_proc in vm_processes:
                    if vm_proc in proc:
                        indicators.append({
                            'method': 'vm_process',
                            'indicator': proc,
                            'weight': 7
                        })
                        detected_type = 'vm'
                
                for sb_proc in sandbox_processes:
                    if sb_proc in proc:
                        indicators.append({
                            'method': 'sandbox_process',
                            'indicator': proc,
                            'weight': 8
                        })
                        detected_type = 'sandbox'
                
                for dbg_proc in debugger_processes:
                    if dbg_proc in proc:
                        indicators.append({
                            'method': 'debugger_process',
                            'indicator': proc,
                            'weight': 9
                        })
                        detected_type = 'debugger'
        
        except Exception as e:
            logger.debug(f"Ошибка детекции процессов: {e}")
        
        if indicators:
            return {
                'type': detected_type or 'unknown',
                'method': 'processes',
                'detected': True,
                'indicators': indicators
            }
        
        return None
    
    def detect_by_files(self) -> Optional[Dict]:
        """Детекция по наличию VM файлов"""
        if not self.is_windows:
            return None
        
        indicators = []
        vm_files = [
            # VMware
            r'C:\Windows\System32\drivers\vmmouse.sys',
            r'C:\Windows\System32\drivers\vmhgfs.sys',
            r'C:\Windows\System32\drivers\vm3dmp.sys',
            r'C:\Windows\System32\drivers\vmci.sys',
            r'C:\Program Files\VMware\',
            # VirtualBox
            r'C:\Windows\System32\drivers\VBoxMouse.sys',
            r'C:\Windows\System32\drivers\VBoxGuest.sys',
            r'C:\Windows\System32\drivers\VBoxSF.sys',
            r'C:\Windows\System32\drivers\VBoxVideo.sys',
            r'C:\Program Files\Oracle\VirtualBox\',
            # Parallels
            r'C:\Windows\System32\drivers\prl_eth.sys',
            r'C:\Windows\System32\drivers\prl_mou.sys',
            r'C:\Windows\System32\drivers\prl_tg.sys',
            r'C:\Program Files (x86)\Parallels\',
            # Sandboxie
            r'C:\Program Files\Sandboxie\',
            r'C:\Windows\System32\drivers\SbieDrv.sys'
        ]
        
        for file_path in vm_files:
            if os.path.exists(file_path):
                indicators.append({
                    'method': 'vm_file',
                    'indicator': file_path,
                    'weight': 6
                })
        
        if indicators:
            return {
                'type': 'vm',
                'method': 'files',
                'detected': True,
                'indicators': indicators
            }
        
        return None
    
    def detect_by_registry(self) -> Optional[Dict]:
        """Детекция по реестру Windows"""
        if not self.is_windows:
            return None
        
        indicators = []
        vm_registry_keys = [
            (winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Services\VBoxGuest'),
            (winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Services\VBoxMouse'),
            (winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Services\VBoxService'),
            (winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Services\VBoxSF'),
            (winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Services\VBoxVideo'),
            (winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Services\vmdebug'),
            (winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Services\vmci'),
            (winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Services\vmmouse'),
            (winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Services\vmrawdsk'),
            (winreg.HKEY_LOCAL_MACHINE, r'SYSTEM\CurrentControlSet\Services\VMTools'),
            (winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\ACPI\DSDT\VBOX__'),
            (winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\ACPI\FADT\VBOX__'),
            (winreg.HKEY_LOCAL_MACHINE, r'HARDWARE\ACPI\RSDT\VBOX__'),
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Oracle\VirtualBox Guest Additions'),
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\VMware, Inc.\VMware Tools'),
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Parallels\Parallels Tools'),
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Sandboxie')
        ]
        
        for hive, key_path in vm_registry_keys:
            try:
                winreg.OpenKey(hive, key_path)
                indicators.append({
                    'method': 'registry_key',
                    'indicator': key_path,
                    'weight': 7
                })
            except WindowsError:
                continue
        
        if indicators:
            return {
                'type': 'vm',
                'method': 'registry',
                'detected': True,
                'indicators': indicators
            }
        
        return None
    
    def detect_by_memory(self) -> Optional[Dict]:
        """Детекция по характеристикам памяти"""
        indicators = []
        
        try:
            if self.is_windows:
                import psutil
                memory = psutil.virtual_memory()
                
                # VM часто имеют круглые значения памяти
                total_gb = memory.total / (1024**3)
                if total_gb.is_integer():
                    indicators.append({
                        'method': 'memory_round',
                        'indicator': f'{int(total_gb)} GB',
                        'weight': 3
                    })
                
                # Мало памяти для песочниц
                if total_gb < 2:  # Меньше 2 GB
                    indicators.append({
                        'method': 'memory_low',
                        'indicator': f'{total_gb:.1f} GB',
                        'weight': 4
                    })
        
        except Exception as e:
            logger.debug(f"Ошибка детекции памяти: {e}")
        
        if indicators:
            return {
                'type': 'sandbox',
                'method': 'memory',
                'detected': True,
                'indicators': indicators
            }
        
        return None
    
    def detect_by_hardware(self) -> Optional[Dict]:
        """Детекция по оборудованию"""
        indicators = []
        
        try:
            if self.is_windows:
                import wmi
                c = wmi.WMI()
                
                # Проверка дисков
                for disk in c.Win32_DiskDrive():
                    model = disk.Model.lower()
                    if any(x in model for x in ['virtual', 'vmware', 'vbox']):
                        indicators.append({
                            'method': 'disk_model',
                            'indicator': model,
                            'weight': 6
                        })
                
                # Проверка BIOS
                for bios in c.Win32_BIOS():
                    manufacturer = bios.Manufacturer.lower()
                    if any(x in manufacturer for x in ['vmware', 'virtual', 'innotek', 'qemu']):
                        indicators.append({
                            'method': 'bios_manufacturer',
                            'indicator': manufacturer,
                            'weight': 7
                        })
        
        except Exception as e:
            logger.debug(f"Ошибка детекции оборудования: {e}")
        
        if indicators:
            return {
                'type': 'vm',
                'method': 'hardware',
                'detected': True,
                'indicators': indicators
            }
        
        return None
    
    def detect_by_network(self) -> Optional[Dict]:
        """Детекция по сетевым характеристикам"""
        indicators = []
        
        try:
            import socket
            import netifaces
            
            # Проверка DNS
            hostname = socket.gethostname()
            if any(x in hostname.lower() for x in ['vm', 'sandbox', 'malware', 'analysis']):
                indicators.append({
                    'method': 'hostname',
                    'indicator': hostname,
                    'weight': 5
                })
            
            # Проверка сетевых интерфейсов
            interfaces = netifaces.interfaces()
            if len(interfaces) < 2:  # Мало интерфейсов
                indicators.append({
                    'method': 'few_interfaces',
                    'indicator': f'{len(interfaces)} interfaces',
                    'weight': 3
                })
        
        except Exception as e:
            logger.debug(f"Ошибка сетевой детекции: {e}")
        
        if indicators:
            return {
                'type': 'sandbox',
                'method': 'network',
                'detected': True,
                'indicators': indicators
            }
        
        return None
    
    def detect_by_system(self) -> Optional[Dict]:
        """Детекция по системным характеристикам"""
        indicators = []
        
        # Время работы системы (песочницы часто перезагружаются)
        try:
            if self.is_windows:
                import psutil
                boot_time = psutil.boot_time()
                import time
                uptime = time.time() - boot_time
                
                if uptime < 3600:  # Меньше часа
                    indicators.append({
                        'method': 'uptime_short',
                        'indicator': f'{int(uptime/60)} minutes',
                        'weight': 4
                    })
        except:
            pass
        
        # Имя пользователя (стандартные имена VM)
        username = os.getenv('USERNAME', '').lower()
        vm_usernames = ['user', 'admin', 'administrator', 'test', 'sandbox']
        if username in vm_usernames:
            indicators.append({
                'method': 'username_generic',
                'indicator': username,
                'weight': 3
            })
        
        if indicators:
            return {
                'type': 'sandbox',
                'method': 'system',
                'detected': True,
                'indicators': indicators
            }
        
        return None
    
    def detect_debugger(self) -> Optional[Dict]:
        """Детекция отладчика"""
        indicators = []
        
        try:
            # Проверка флага BeingDebugged
            if self.is_windows:
                kernel32 = ctypes.windll.kernel32
                is_debugger_present = kernel32.IsDebuggerPresent()
                
                if is_debugger_present:
                    indicators.append({
                        'method': 'IsDebuggerPresent',
                        'indicator': 'Debugger present',
                        'weight': 10
                    })
                
                # Проверка через NtQueryInformationProcess
                from ctypes import wintypes
                
                ProcessDebugPort = 7
                h_process = kernel32.GetCurrentProcess()
                
                class PROCESS_BASIC_INFORMATION(ctypes.Structure):
                    _fields_ = [
                        ("Reserved1", wintypes.PVOID),
                        ("PebBaseAddress", wintypes.PVOID),
                        ("Reserved2", wintypes.PVOID * 2),
                        ("UniqueProcessId", wintypes.ULONG),
                        ("Reserved3", wintypes.PVOID)
                    ]
                
                ntdll = ctypes.windll.ntdll
                pbi = PROCESS_BASIC_INFORMATION()
                return_length = wintypes.ULONG()
                
                status = ntdll.NtQueryInformationProcess(
                    h_process,
                    ProcessDebugPort,
                    ctypes.byref(pbi),
                    ctypes.sizeof(pbi),
                    ctypes.byref(return_length)
                )
                
                if status == 0 and pbi.PebBaseAddress:
                    peb_base = pbi.PebBaseAddress
                    debug_port = ctypes.c_ulong()
                    
                    if kernel32.ReadProcessMemory(
                        h_process,
                        peb_base + 0x68,  # BeingDebugged offset
                        ctypes.byref(debug_port),
                        ctypes.sizeof(debug_port),
                        None
                    ):
                        if debug_port.value != 0:
                            indicators.append({
                                'method': 'NtQueryInformationProcess',
                                'indicator': 'Process debug port set',
                                'weight': 10
                            })
            
            # Проверка времени выполнения (отладчик замедляет)
            import time
            start = time.perf_counter()
            # Выполняем некоторую работу
            for _ in range(1000000):
                pass
            elapsed = time.perf_counter() - start
            
            if elapsed > 0.1:  # Слишком долго для простого цикла
                indicators.append({
                    'method': 'execution_time',
                    'indicator': f'{elapsed:.3f} seconds',
                    'weight': 6
                })
        
        except Exception as e:
            logger.debug(f"Ошибка детекции отладчика: {e}")
        
        if indicators:
            return {
                'type': 'debugger',
                'method': 'debugger',
                'detected': True,
                'indicators': indicators
            }
        
        return None
    
    def _guess_vm_type(self, indicators: List[Dict]) -> str:
        """Определяет тип VM по индикаторам"""
        vm_type_map = {
            'vmware': ['vmware', 'vmtools'],
            'virtualbox': ['virtualbox', 'vbox'],
            'parallels': ['parallels', 'prl_'],
            'xen': ['xen'],
            'hyper-v': ['hyper-v'],
            'qemu': ['qemu'],
            'kvm': ['kvm']
        }
        
        for indicator in indicators:
            indicator_str = str(indicator.get('indicator', '')).lower()
            for vm_type, keywords in vm_type_map.items():
                for keyword in keywords:
                    if keyword in indicator_str:
                        return vm_type.capitalize()
        
        return "Unknown VM"

# Синхронные обертки
def detect_vm_sync() -> Dict:
    detector = VMDetector()
    return detector.detect_all()

def is_virtual_machine_sync() -> bool:
    detector = VMDetector()
    results = detector.detect_all()
    return results.get('is_vm', False) or results.get('is_sandbox', False)

# Тестирование
if __name__ == "__main__":
    print("🧪 Тест детектора VM/песочниц")
    
    results = detect_vm_sync()
    
    print(f"\n📊 Результаты детекции:")
    print(f"  Виртуальная машина: {'✅ ДА' if results['is_vm'] else '❌ НЕТ'}")
    print(f"  Песочница: {'✅ ДА' if results['is_sandbox'] else '❌ НЕТ'}")
    print(f"  Отладчик: {'✅ ДА' if results['is_debugged'] else '❌ НЕТ'}")
    print(f"  Тип VM: {results['vm_type'] or 'Не обнаружена'}")
    print(f"  Уверенность: {results['confidence']}%")
    
    if results['indicators']:
        print(f"\n🔍 Обнаруженные индикаторы:")
        for indicator in results['indicators'][:5]:  # Показываем первые 5
            print(f"  • {indicator['method']}: {indicator['indicator']} (вес: {indicator.get('weight', 1)})")
    
    if results['is_vm'] or results['is_sandbox']:
        print(f"\n⚠️  Внимание! Возможно, вы находитесь в виртуальной среде!")
    else:
        print(f"\n✅ Окружение выглядит чистым")