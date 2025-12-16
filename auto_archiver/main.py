"""
Главный файл системы
"""
import sys
import argparse
from pathlib import Path

# Добавляем папки в путь Python
sys.path.insert(0, str(Path(__file__).parent))

from core.config import config
from utils.logger import logger
from core.security import EncryptionSystem, calculate_file_hash
from modules.telegram_archiver import (
    archive_channel_sync, 
    get_archives_sync,
    archive_chat_sync,
    archive_sync
)
from modules.file_sync import (
    sync_files_sync,
    create_snapshot_sync,
    list_snapshots_sync,
    compare_with_snapshot_sync
)
from modules.monitor import (
    get_system_info_sync,
    get_comprehensive_monitoring_sync,
    monitor_realtime_sync,
    save_report_sync
)

# Импорты нового ядра (ДОБАВЛЕНО)
from core.system_initializer import initialize_system_sync
from core.dependency_manager import check_dependencies_sync, install_dependencies_sync
from core.plugin_loader import load_plugins_sync, list_available_plugins_sync

def setup_encryption():
    """Настройка шифрования"""
    print("\n🔐 НАСТРОЙКА ШИФРОВАНИЯ")
    print("-" * 40)
    
    enc_system = EncryptionSystem(config)
    
    choice = input("1. Создать новый ключ из пароля\n2. Загрузить существующий ключ\nВыберите (1/2): ")
    
    if choice == "1":
        password = input("Введите мастер-пароль: ")
        password_confirm = input("Повторите пароль: ")
        
        if password != password_confirm:
            print("❌ Пароли не совпадают!")
            return None
        
        enc_system.generate_key_from_password(password, save_to_file=True)
        print("✅ Ключ создан и сохранен!")
    
    elif choice == "2":
        if enc_system.load_key_from_file():
            print("✅ Ключ загружен!")
        else:
            print("❌ Не удалось загрузить ключ")
            return None
    
    else:
        print("❌ Неверный выбор")
        return None
    
    return enc_system

def test_encryption():
    """Тестирование шифрования"""
    print("\n🧪 ТЕСТ ШИФРОВАНИЯ")
    print("-" * 40)
    
    # Создаем тестовый файл
    test_file = config.data_dir / "test_file.txt"
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write("Это тестовый файл для проверки шифрования.\nСекретные данные: 123-456-789")
    
    print(f"✓ Создан тестовый файл: {test_file}")
    
    # Вычисляем хеш
    original_hash = calculate_file_hash(test_file)
    print(f"✓ Хеш исходного файла: {original_hash[:16]}...")
    
    # Настраиваем шифрование
    enc_system = setup_encryption()
    if enc_system is None:
        return
    
    # Шифруем файл
    encrypted_file = enc_system.encrypt_file(test_file)
    
    # Расшифровываем файл
    decrypted_file = enc_system.decrypt_file(encrypted_file)
    
    # Проверяем хеш
    decrypted_hash = calculate_file_hash(decrypted_file)
    
    if original_hash == decrypted_hash:
        print("✅ ТЕСТ ПРОЙДЕН! Файл успешно зашифрован и расшифрован.")
    else:
        print("❌ ТЕСТ ПРОВАЛЕН! Хеши не совпадают.")
    
    # Тестируем шифрование строк
    test_string = "Секретное сообщение для шифрования"
    encrypted_string = enc_system.encrypt_string(test_string)
    decrypted_string = enc_system.decrypt_string(encrypted_string)
    
    print(f"\n📝 Тест шифрования строк:")
    print(f"   Исходное: {test_string}")
    print(f"   Зашифрованное: {encrypted_string[:30]}...")
    print(f"   Расшифрованное: {decrypted_string}")
    
    if test_string == decrypted_string:
        print("✅ Шифрование строк работает корректно!")
    
    # Удаляем тестовые файлы
    test_file.unlink()
    Path(encrypted_file).unlink()
    Path(decrypted_file).unlink()
    print("\n🧹 Тестовые файлы удалены")

def main():
    """Главная функция системы"""
    print("\n" + "="*50)
    print("АВТОНОМНАЯ СИСТЕМА АРХИВАЦИИ".center(50))
    print("="*50)
    
    logger.info("Инициализация системы...")
    
    # Загружаем конфиг
    if config.load():
        logger.info("Конфигурация загружена")
    else:
        logger.info("Используется конфигурация по умолчанию")
        config.save()
    
    # Парсим аргументы командной строки
    parser = argparse.ArgumentParser(description='AutoArchiver System')
    
    # Команды шифрования
    parser.add_argument('--test-encryption', action='store_true', help='Протестировать шифрование')
    parser.add_argument('--encrypt', type=str, help='Зашифровать файл')
    parser.add_argument('--decrypt', type=str, help='Расшифровать файл')
    parser.add_argument('--hash', type=str, help='Вычислить хеш файла')
    
    # Команды Telegram
    parser.add_argument('--archive-telegram', type=str, help='Архивировать Telegram канал/чат (ссылка или username)')
    parser.add_argument('--archive-chat', type=str, help='Архивировать приватный чат (username или ID)')
    parser.add_argument('--archive-type', type=str, default='auto', 
                       help='Тип архивации: auto, channel, chat, group')
    parser.add_argument('--list-archives', action='store_true', help='Показать список архивов')
    parser.add_argument('--telegram-limit', type=int, default=100, help='Лимит сообщений (по умолчанию: 100)')
    
    # Команды синхронизации
    parser.add_argument('--sync', nargs=2, metavar=('SOURCE', 'TARGET'), 
                       help='Синхронизировать две директории')
    parser.add_argument('--delete-missing', action='store_true', 
                       help='Удалять файлы, которых нет в источнике (только с --sync)')
    parser.add_argument('--dry-run', action='store_true', 
                       help='Тестовый режим без реальных изменений (только с --sync)')
    parser.add_argument('--create-snapshot', type=str, 
                       help='Создать снимок состояния директории')
    parser.add_argument('--snapshot-name', type=str, 
                       help='Имя снимка (только с --create-snapshot)')
    parser.add_argument('--list-snapshots', action='store_true', 
                       help='Показать список снимки')
    parser.add_argument('--compare-snapshot', nargs=2, metavar=('DIR', 'SNAPSHOT'), 
                       help='Сравнить директорию со снимком')
    
    # Команды мониторинга
    parser.add_argument('--monitor', action='store_true', 
                       help='Полная информация о системе')
    parser.add_argument('--monitor-realtime', action='store_true', 
                       help='Мониторинг в реальном времени')
    parser.add_argument('--monitor-interval', type=int, default=2,
                       help='Интервал обновления в секундах (только с --monitor-realtime)')
    parser.add_argument('--monitor-duration', type=int, default=30,
                       help='Продолжительность мониторинга в секундах (только с --monitor-realtime)')
    parser.add_argument('--save-report', action='store_true',
                       help='Сохранить отчет мониторинга в файл')
    parser.add_argument('--report-filename', type=str,
                       help='Имя файла отчета (только с --save-report)')
    
    # Команды ядра (ДОБАВЛЕНО)
    parser.add_argument('--init-system', action='store_true', 
                       help='Инициализировать систему (проверить окружение)')
    parser.add_argument('--check-deps', action='store_true', 
                       help='Проверить зависимости')
    parser.add_argument('--install-deps', action='store_true', 
                       help='Установить все зависимости')
    parser.add_argument('--list-plugins', action='store_true', 
                       help='Показать список плагинов/модулей')
    parser.add_argument('--force', action='store_true', 
                       help='Принудительная установка (только с --install-deps)')
    
    args = parser.parse_args()
    
    # Обрабатываем команды
    if args.test_encryption:
        test_encryption()
    
    elif args.encrypt:
        enc_system = EncryptionSystem(config)
        if enc_system.load_key_from_file():
            enc_system.encrypt_file(args.encrypt)
        else:
            print("❌ Не удалось загрузить ключ шифрования")
    
    elif args.decrypt:
        enc_system = EncryptionSystem(config)
        if enc_system.load_key_from_file():
            enc_system.decrypt_file(args.decrypt)
        else:
            print("❌ Не удалось загрузить ключ шифрования")
    
    elif args.hash:
        if Path(args.hash).exists():
            file_hash = calculate_file_hash(args.hash)
            print(f"Хеш файла {args.hash}:")
            print(f"SHA-256: {file_hash}")
        else:
            print(f"❌ Файл не найден: {args.hash}")
    
    elif args.archive_telegram:
        print(f"\n📥 Архивация Telegram: {args.archive_telegram}")
        print(f"Тип: {args.archive_type}, Лимит сообщений: {args.telegram_limit}")
        print("-" * 50)
        
        result = archive_sync(config, args.archive_telegram, args.telegram_limit, args.archive_type)
        
        if 'error' in result:
            print(f"❌ Ошибка: {result['error']}")
        else:
            # Определяем тип для вывода
            if 'channel_name' in result:
                print(f"\n✅ Архивация канала завершена!")
                print(f"Канал: {result.get('channel_name')}")
            elif 'chat_name' in result:
                print(f"\n✅ Архивация чата завершена!")
                print(f"Чат: {result.get('chat_name')}")
                print(f"Тип: {result.get('chat_type')}")
                print(f"Участников: {result.get('participants_count', 1)}")
            
            print(f"Сообщений: {result.get('total_messages')}")
            print(f"Медиафайлов: {result.get('media_files', 0)}")
            print(f"Документов: {result.get('documents', 0)}")
            
            if 'note' in result and 'telethon' in result['note']:
                print(f"\n⚠️  {result['note']}")
                print("Получите API ключи на: https://my.telegram.org")
                print("И добавьте в config.json:")
                print('  "telegram": {')
                print('    "api_id": "ВАШ_API_ID",')
                print('    "api_hash": "ВАШ_API_HASH"')
                print('  }')
    
    elif args.archive_chat:
        print(f"\n💬 Архивация приватного чата: {args.archive_chat}")
        print(f"Лимит сообщений: {args.telegram_limit}")
        print("-" * 50)
        
        result = archive_chat_sync(config, args.archive_chat, args.telegram_limit, "private")
        
        if 'error' in result:
            print(f"❌ Ошибка: {result['error']}")
        else:
            print(f"\n✅ Архивация чата завершена!")
            print(f"Чат: {result.get('chat_name')}")
            print(f"Тип: {result.get('chat_type')}")
            print(f"Сообщений: {result.get('total_messages')}")
            print(f"Участников: {result.get('participants_count', 1)}")
            print(f"Медиафайлов: {result.get('media_files', 0)}")
            print(f"Документов: {result.get('documents', 0)}")
            
            if 'note' in result and 'telethon' in result['note']:
                print(f"\n⚠️  {result['note']}")
                print("Для архивации приватных чатов нужна авторизация в Telegram!")
    
    elif args.list_archives:
        print(f"\n📁 ТЕЛЕГРАМ АРХИВЫ")
        print("-" * 50)
        
        archives = get_archives_sync(config)
        
        if not archives:
            print("Архивов пока нет")
            print("\nСоздайте архив командой:")
            print("python main.py --archive-telegram https://t.me/channel_name")
            print("python main.py --archive-chat username")
        else:
            total_messages = sum(a['messages'] for a in archives)
            print(f"Всего архивов: {len(archives)}")
            print(f"Всего сообщений: {total_messages}")
            print("\nСписок архивов:")
            
            for i, archive in enumerate(archives, 1):
                type_icon = "📢" if archive['type'] == 'channel' else "💬"
                print(f"\n  {i}. {type_icon} {archive['name']}")
                print(f"     Тип: {archive['type']}")
                print(f"     Сообщений: {archive['messages']}")
                print(f"     Дата: {archive['date'][:10] if archive['date'] else 'неизвестно'}")
                print(f"     Папка: {archive['path']}")
    
    elif args.sync:
        source_dir, target_dir = args.sync
        print(f"\n🔄 СИНХРОНИЗАЦИЯ ФАЙЛОВ")
        print("-" * 50)
        print(f"Источник: {source_dir}")
        print(f"Цель: {target_dir}")
        print(f"Удалять отсутствующие: {'Да' if args.delete_missing else 'Нет'}")
        print(f"Тестовый режим: {'Да' if args.dry_run else 'Нет'}")
        print("-" * 50)
        
        result = sync_files_sync(
            config, 
            source_dir, 
            target_dir, 
            delete_missing=args.delete_missing,
            dry_run=args.dry_run
        )
        
        if 'error' in result:
            print(f"❌ Ошибка: {result['error']}")
        else:
            print(f"\n📊 РЕЗУЛЬТАТЫ СИНХРОНИЗАЦИИ:")
            print(f"  Всего файлов: {result.get('total_files', 0)}")
            print(f"  Скопировано: {result.get('copied', 0)}")
            print(f"  Обновлено: {result.get('updated', 0)}")
            print(f"  Пропущено: {result.get('skipped', 0)}")
            print(f"  Удалено: {result.get('deleted', 0)}")
            print(f"  Ошибок: {result.get('errors', 0)}")
            
            if args.dry_run:
                print("\n⚠️  ТЕСТОВЫЙ РЕЖИМ: изменения не применены!")
    
    elif args.create_snapshot:
        print(f"\n📸 СОЗДАНИЕ СНИМКА ДИРЕКТОРИИ")
        print("-" * 50)
        print(f"Директория: {args.create_snapshot}")
        print(f"Имя снимка: {args.snapshot_name or 'автоматически'}")
        print("-" * 50)
        
        result = create_snapshot_sync(config, args.create_snapshot, args.snapshot_name)
        
        if 'error' in result:
            print(f"❌ Ошибка: {result['error']}")
        else:
            print(f"\n✅ Снимок создан!")
            print(f"Имя: {result.get('snapshot_name')}")
            print(f"Файлов: {result.get('file_count', 0)}")
            print(f"Файл снимка: {result.get('snapshot_file', '')}")
    
    elif args.list_snapshots:
        print(f"\n📁 СПИСОК СНИМКОВ")
        print("-" * 50)
        
        snapshots = list_snapshots_sync(config)
        
        if not snapshots:
            print("Снимков пока нет")
            print("\nСоздайте снимок командой:")
            print("python main.py --create-snapshot /путь/к/директории")
        else:
            print(f"Всего снимков: {len(snapshots)}")
            print("\nСписок снимков:")
            
            for i, snapshot in enumerate(snapshots, 1):
                print(f"\n  {i}. {snapshot['name']}")
                print(f"     Директория: {snapshot['directory']}")
                print(f"     Файлов: {snapshot['file_count']}")
                print(f"     Создан: {snapshot['created_at'][:19] if snapshot['created_at'] else 'неизвестно'}")
    
    elif args.compare_snapshot:
        directory, snapshot_name = args.compare_snapshot
        print(f"\n🔍 СРАВНЕНИЕ СО СНИМКОМ")
        print("-" * 50)
        print(f"Директория: {directory}")
        print(f"Снимок: {snapshot_name}")
        print("-" * 50)
        
        result = compare_with_snapshot_sync(config, directory, snapshot_name)
        
        if 'error' in result:
            print(f"❌ Ошибка: {result['error']}")
        else:
            summary = result.get('summary', {})
            print(f"\n📊 РЕЗУЛЬТАТЫ СРАВНЕНИЯ:")
            print(f"  Всего файлов: {summary.get('total_files', 0)}")
            print(f"  Добавлено: {summary.get('added', 0)}")
            print(f"  Удалено: {summary.get('removed', 0)}")
            print(f"  Изменено: {summary.get('modified', 0)}")
            print(f"  Без изменений: {summary.get('unchanged', 0)}")
            
            differences = result.get('differences', {})
            if differences.get('added'):
                print(f"\n➕ Добавленные файлы ({len(differences['added'])}):")
                for file in differences['added'][:5]:
                    print(f"  • {file}")
                if len(differences['added']) > 5:
                    print(f"  ... и ещё {len(differences['added']) - 5}")
            
            if differences.get('removed'):
                print(f"\n➖ Удаленные файлы ({len(differences['removed'])}):")
                for file in differences['removed'][:5]:
                    print(f"  • {file}")
                if len(differences['removed']) > 5:
                    print(f"  ... и ещё {len(differences['removed']) - 5}")
            
            if differences.get('modified'):
                print(f"\n✏️  Измененные файлы ({len(differences['modified'])}):")
                for file in differences['modified'][:5]:
                    print(f"  • {file}")
                if len(differences['modified']) > 5:
                    print(f"  ... и ещё {len(differences['modified']) - 5}")
    
    elif args.monitor:
        print(f"\n📊 МОНИТОРИНГ СИСТЕМЫ")
        print("=" * 60)
        
        data = get_comprehensive_monitoring_sync(config)
        
        if 'error' in data:
            print(f"❌ Ошибка: {data['error']}")
        else:
            # Общая информация
            print(f"\n📋 ОБЩАЯ ИНФОРМАЦИЯ:")
            sys_info = data.get('system', {})
            if 'platform' in sys_info:
                print(f"  Система: {sys_info['platform']['system']} {sys_info['platform']['release']}")
                print(f"  Процессор: {sys_info['platform']['processor'][:50]}...")
                print(f"  Хост: {sys_info['host']['name']} ({sys_info['host']['ip']})")
                print(f"  Время загрузки: {sys_info.get('boot_time', 'неизвестно')}")
            
            # CPU
            cpu_info = data.get('cpu', {})
            if 'usage_percent' in cpu_info:
                print(f"\n💻 ПРОЦЕССОР:")
                print(f"  Загрузка: {cpu_info['usage_percent']}%")
                print(f"  Ядер: {cpu_info['logical_cores']} ({cpu_info['physical_cores']} физических)")
                if cpu_info.get('frequency', {}).get('current'):
                    print(f"  Частота: {cpu_info['frequency']['current']:.0f} MHz")
            
            # Память
            mem_info = data.get('memory', {}).get('ram', {})
            if 'percent' in mem_info:
                print(f"\n🧠 ОПЕРАТИВНАЯ ПАМЯТЬ:")
                print(f"  Использовано: {mem_info['used_gb']:.1f}/{mem_info['total_gb']:.1f} GB ({mem_info['percent']}%)")
                print(f"  Доступно: {mem_info['available_gb']:.1f} GB")
            
            # Диск
            disk_info = data.get('disk', {}).get('partitions', [])
            if disk_info:
                print(f"\n💾 ДИСКИ:")
                for i, partition in enumerate(disk_info[:3], 1):
                    print(f"  {i}. {partition['mountpoint']}: {partition['used_gb']:.1f}/{partition['total_gb']:.1f} GB ({partition['percent']}%)")
            
            # Процессы
            processes_info = data.get('processes', {}).get('processes', [])
            if processes_info:
                print(f"\n🔝 ТОП-5 ПРОЦЕССОВ:")
                for i, proc in enumerate(processes_info[:5], 1):
                    name = proc.get('name', 'N/A')[:25]
                    cpu = proc.get('cpu_percent', 0)
                    mem = proc.get('memory_percent', 0)
                    print(f"  {i}. {name:25} CPU:{cpu:5.1f}% MEM:{mem:5.1f}%")
            
            # Сеть
            net_info = data.get('network', {})
            if 'io' in net_info:
                io = net_info['io']
                if 'bytes_sent' in io and 'bytes_recv' in io:
                    sent_mb = io['bytes_sent'] / (1024**2)
                    recv_mb = io['bytes_recv'] / (1024**2)
                    print(f"\n🌐 СЕТЬ:")
                    print(f"  Отправлено: {sent_mb:.1f} MB")
                    print(f"  Получено: {recv_mb:.1f} MB")
            
            print(f"\n🕐 Время сбора данных: {data.get('timestamp', 'неизвестно')}")
    
    elif args.monitor_realtime:
        monitor_realtime_sync(
            config, 
            interval=args.monitor_interval, 
            duration=args.monitor_duration
        )
    
    elif args.save_report:
        print(f"\n💾 СОХРАНЕНИЕ ОТЧЕТА МОНИТОРИНГА")
        print("=" * 60)
        
        report_file = save_report_sync(config, args.report_filename)
        
        print(f"✅ Отчет сохранен: {report_file}")
        print(f"\n📁 Папка с отчетами: {config.data_dir / 'monitoring'}")
    
    # Команды ядра (ДОБАВЛЕНО)
    elif args.init_system:
        print(f"\n🚀 ИНИЦИАЛИЗАЦИЯ СИСТЕМЫ")
        print("=" * 60)
        
        results = initialize_system_sync(config)
        
        if 'summary' in results:
            summary = results['summary']
            print(f"\n📊 РЕЗУЛЬТАТЫ ПРОВЕРКИ:")
            print(f"  Всего проверок: {summary['total_checks']}")
            print(f"  Пройдено: {summary['passed_checks']}")
            print(f"  Не пройдено: {summary['failed_checks']}")
            print(f"  Статус: {'✅ ВСЁ ОК' if summary['passed'] else '⚠️  ЕСТЬ ПРОБЛЕМЫ'}")
        
        # Детали проверок
        if 'checks' in results:
            checks = results['checks']
            print(f"\n🔍 ДЕТАЛИ ПРОВЕРОК:")
            
            for check_name, check_result in checks.items():
                status = "✅" if check_result.get('passed', False) else "❌"
                print(f"  {status} {check_name.upper()}: {check_result.get('message', '')}")
                
                # Показываем дополнительные детали для некоторых проверок
                if check_name == 'dependencies' and 'results' in check_result:
                    print(f"    📦 Зависимости:")
                    for dep in check_result['results']:
                        dep_status = "✓" if dep.get('installed', False) else "✗"
                        print(f"      {dep_status} {dep.get('package', '?')}: {dep.get('current', 'нет')}")
    
    elif args.check_deps:
        print(f"\n📦 ПРОВЕРКА ЗАВИСИМОСТЕЙ")
        print("=" * 60)
        
        results = check_dependencies_sync(config)
        
        if 'summary' in results:
            summary = results['summary']
            print(f"\n📊 СВОДКА:")
            print(f"  Всего зависимостей: {summary['total']}")
            print(f"  Установлено: {summary['installed']}")
            print(f"  Отсутствует: {summary['missing']}")
            print(f"  Несовместимые версии: {summary['wrong_version']}")
            print(f"  Статус: {'✅ ВСЁ ОК' if summary['all_ok'] else '⚠️  ТРЕБУЮТСЯ ДЕЙСТВИЯ'}")
        
        # Детали
        if 'dependencies' in results:
            print(f"\n🔍 ДЕТАЛИ:")
            
            for dep in results['dependencies']:
                if dep['status'] == 'OK':
                    status = "✅"
                elif dep['status'] == 'MISSING':
                    status = "❌"
                else:
                    status = "⚠️ "
                
                version_info = f"({dep['current']})" if dep['current'] else "не установлен"
                print(f"  {status} {dep['package']:20} {version_info}")
                
                if dep['status'] == 'MISSING':
                    print(f"     ⬇️  Установите: pip install {dep['package']}=={dep['required']}")
                elif dep['status'] == 'WRONG_VERSION':
                    print(f"     🔄 Обновите: pip install {dep['package']}=={dep['required']}")
    
    elif args.install_deps:
        print(f"\n⚡ УСТАНОВКА ЗАВИСИМОСТЕЙ")
        print("=" * 60)
        
        if args.force:
            print("⚠️  РЕЖИМ ПРИНУДИТЕЛЬНОЙ УСТАНОВКИ (будут переустановлены все)")
        
        results = install_dependencies_sync(config, force=args.force)
        
        if 'summary' in results:
            summary = results['summary']
            print(f"\n📊 РЕЗУЛЬТАТЫ УСТАНОВКИ:")
            print(f"  Всего: {summary['total']}")
            print(f"  Установлено: {summary['installed']}")
            print(f"  Пропущено: {summary['skipped']}")
            print(f"  Не удалось: {summary['failed']}")
            print(f"  Статус: {'✅ УСПЕШНО' if summary['success'] else '⚠️  ЕСТЬ ОШИБКИ'}")
        
        # Детали ошибок
        if not results.get('summary', {}).get('success', False):
            print(f"\n🔍 ОШИБКИ УСТАНОВКИ:")
            for result in results.get('results', []):
                if not result.get('success', False) and not result.get('skipped', False):
                    print(f"  ❌ {result.get('package', '?')}: {result.get('message', 'Ошибка')}")
                    if result.get('stderr'):
                        print(f"     {result['stderr'][:100]}...")
    
    elif args.list_plugins:
        print(f"\n🔌 СПИСОК ПЛАГИНОВ/МОДУЛЕЙ")
        print("=" * 60)
        
        results = load_plugins_sync(config)
        
        if 'summary' in results:
            summary = results['summary']
            print(f"\n📊 СВОДКА:")
            print(f"  Всего модулей: {summary['total']}")
            print(f"  Загружено успешно: {summary['success']}")
            print(f"  Не удалось загрузить: {summary['failed']}")
        
        # Детали
        if 'results' in results:
            print(f"\n🔍 ДЕТАЛИ:")
            
            for result in results['results']:
                if result.get('success', False):
                    status = "✅"
                    class_info = f" - {result['class'].__name__}" if result.get('class') else ""
                else:
                    status = "❌"
                    class_info = f" - {result.get('error', 'Ошибка')}"
                
                print(f"  {status} {result.get('name', '?')}{class_info}")
    
    else:
        # Режим по умолчанию - информация о системе
        print(f"\n📋 Информация о системе:")
        print(f"  Имя: {config.get('system.name')}")
        print(f"  Версия: {config.get('system.version')}")
        print(f"  Режим отладки: {config.get('system.debug')}")
        print(f"  Шифрование: {'ВКЛ' if config.get('encryption.enabled') else 'ВЫКЛ'}")
        
        print(f"\n📁 Папки:")
        print(f"  Данные: {config.data_dir}")
        print(f"  Логи: {config.logs_dir}")
        print(f"  Ключи: {config.keys_dir}")
        print(f"  Синхронизация: {config.data_dir / 'sync'}")
        print(f"  Мониторинг: {config.data_dir / 'monitoring'}")
        
        print(f"\n🚀 Доступные команды:")
        print("  ОСНОВНЫЕ:")
        print("    python main.py --test-encryption           # Тест шифрования")
        print("    python main.py --encrypt file.txt          # Зашифровать файл")
        print("    python main.py --archive-telegram URL      # Архивировать Telegram")
        print("    python main.py --sync ИСТОЧНИК ЦЕЛЬ        # Синхронизировать папки")
        print("    python main.py --monitor                   # Информация о системе")
        
        print("\n  ЯДРО СИСТЕМЫ:")
        print("    python main.py --init-system               # Инициализировать систему")
        print("    python main.py --check-deps                # Проверить зависимости")
        print("    python main.py --install-deps              # Установить зависимости")
        print("    python main.py --list-plugins              # Показать плагины")
        
        print("\n  ДОПОЛНИТЕЛЬНЫЕ:")
        print("    python main.py --create-snapshot ПУТЬ      # Создать снимок папки")
        print("    python main.py --monitor-realtime          # Мониторинг в реальном времени")
        print("    python main.py --save-report               # Сохранить отчет")
        
        print(f"\n✅ Система готова к работе!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Работа завершена пользователем")
    except Exception as e:
        logger.error(f"Ошибка при запуске: {e}")
        print(f"\n❌ Ошибка: {e}")