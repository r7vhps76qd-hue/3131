"""
Умная синхронизация файлов в стиле Rsync
"""
import os
import hashlib
import shutil
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import logging

logger = logging.getLogger("FileSync")

class FileSync:
    def __init__(self, config):
        """
        Инициализация системы синхронизации
        
        Args:
            config: объект конфигурации
        """
        self.config = config
        self.sync_dir = config.data_dir / "sync"
        self.sync_dir.mkdir(exist_ok=True)
        
        # Файл для хранения информации о синхронизации
        self.sync_state_file = self.sync_dir / "sync_state.json"
        self.sync_state = self._load_sync_state()
        
        # Размер блока для сравнения (по умолчанию 4KB)
        self.block_size = 4096
        
        logger.info("Система синхронизации инициализирована")
    
    def _load_sync_state(self) -> Dict:
        """Загружает состояние синхронизации"""
        if self.sync_state_file.exists():
            try:
                with open(self.sync_state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def _save_sync_state(self):
        """Сохраняет состояние синхронизации"""
        with open(self.sync_state_file, 'w', encoding='utf-8') as f:
            json.dump(self.sync_state, f, indent=2, ensure_ascii=False)
    
    def calculate_file_hash(self, file_path: Path, algorithm: str = 'sha256') -> str:
        """
        Вычисляет хеш файла
        
        Args:
            file_path: путь к файлу
            algorithm: алгоритм хеширования
            
        Returns:
            str: хеш файла
        """
        hash_func = hashlib.new(algorithm)
        
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(self.block_size), b""):
                hash_func.update(chunk)
        
        return hash_func.hexdigest()
    
    def sync_files(self, source_dir: str, target_dir: str, 
                   delete_missing: bool = False, 
                   dry_run: bool = False) -> Dict:
        """
        Синхронизация двух директорий
        
        Args:
            source_dir: исходная директория
            target_dir: целевая директория
            delete_missing: удалять ли файлы, которых нет в источнике
            dry_run: тестовый режим (без реальных изменений)
            
        Returns:
            Dict: статистика синхронизации
        """
        source_path = Path(source_dir)
        target_path = Path(target_dir)
        
        if not source_path.exists():
            return {'error': f'Исходная директория не существует: {source_dir}'}
        
        if not target_path.exists():
            if not dry_run:
                target_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"Создана целевая директория: {target_dir}")
        
        stats = {
            'total_files': 0,
            'copied': 0,
            'skipped': 0,
            'updated': 0,
            'deleted': 0,
            'errors': 0,
            'start_time': datetime.now().isoformat()
        }
        
        # Проходим по всем файлам в исходной директории
        for root, dirs, files in os.walk(source_path):
            # Создаем соответствующие поддиректории в целевой
            rel_path = Path(root).relative_to(source_path)
            target_subdir = target_path / rel_path
            
            if not dry_run:
                target_subdir.mkdir(parents=True, exist_ok=True)
            
            # Обрабатываем файлы
            for file in files:
                stats['total_files'] += 1
                
                source_file = Path(root) / file
                target_file = target_subdir / file
                
                try:
                    result = self._sync_single_file(source_file, target_file, dry_run)
                    
                    if result == 'copied':
                        stats['copied'] += 1
                    elif result == 'skipped':
                        stats['skipped'] += 1
                    elif result == 'updated':
                        stats['updated'] += 1
                
                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f"Ошибка синхронизации {source_file}: {e}")
        
        # Удаляем лишние файлы если нужно
        if delete_missing:
            deleted = self._delete_extra_files(source_path, target_path, dry_run)
            stats['deleted'] = deleted
        
        stats['end_time'] = datetime.now().isoformat()
        
        if not dry_run:
            self._save_sync_state()
        
        return stats
    
    def _sync_single_file(self, source_file: Path, target_file: Path, dry_run: bool) -> str:
        """
        Синхронизация одного файла
        
        Returns:
            str: результат - 'copied', 'skipped', 'updated'
        """
        # Проверяем, существует ли целевой файл
        if not target_file.exists():
            if not dry_run:
                shutil.copy2(source_file, target_file)
                logger.info(f"Скопирован: {source_file} -> {target_file}")
            return 'copied'
        
        # Сравниваем файлы
        source_hash = self.calculate_file_hash(source_file)
        target_hash = self.calculate_file_hash(target_file)
        
        # Файлы идентичны - пропускаем
        if source_hash == target_hash:
            logger.debug(f"Пропущен (без изменений): {source_file}")
            return 'skipped'
        
        # Файлы разные - обновляем
        if not dry_run:
            shutil.copy2(source_file, target_file)
            logger.info(f"Обновлен: {source_file}")
        
        return 'updated'
    
    def _delete_extra_files(self, source_path: Path, target_path: Path, dry_run: bool) -> int:
        """
        Удаляет файлы, которые есть в цели, но нет в источнике
        
        Returns:
            int: количество удаленных файлов
        """
        deleted_count = 0
        
        for root, dirs, files in os.walk(target_path):
            # Получаем соответствующий путь в исходной директории
            rel_path = Path(root).relative_to(target_path)
            source_subdir = source_path / rel_path
            
            # Проверяем файлы
            for file in files:
                target_file = Path(root) / file
                source_file = source_subdir / file
                
                if not source_file.exists():
                    if not dry_run:
                        try:
                            target_file.unlink()
                            logger.info(f"Удален (отсутствует в источнике): {target_file}")
                            deleted_count += 1
                        except Exception as e:
                            logger.error(f"Ошибка удаления {target_file}: {e}")
                    else:
                        logger.info(f"[DRY RUN] Будет удален: {target_file}")
                        deleted_count += 1
        
        return deleted_count
    
    def create_snapshot(self, directory: str, snapshot_name: str = None) -> Dict:
        """
        Создает снимок состояния директории
        
        Args:
            directory: директория для снимка
            snapshot_name: имя снимка (если None - генерируется автоматически)
            
        Returns:
            Dict: информация о снимке
        """
        dir_path = Path(directory)
        
        if not dir_path.exists():
            return {'error': f'Директория не существует: {directory}'}
        
        if snapshot_name is None:
            snapshot_name = f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        snapshot_data = {
            'name': snapshot_name,
            'directory': str(dir_path),
            'created_at': datetime.now().isoformat(),
            'files': {}
        }
        
        # Собираем информацию о файлах
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(dir_path)
                
                try:
                    file_hash = self.calculate_file_hash(file_path)
                    stat = file_path.stat()
                    
                    snapshot_data['files'][str(rel_path)] = {
                        'hash': file_hash,
                        'size': stat.st_size,
                        'modified': stat.st_mtime,
                        'created': stat.st_ctime
                    }
                except Exception as e:
                    logger.error(f"Ошибка обработки файла {file_path}: {e}")
        
        # Сохраняем снимок
        snapshots_dir = self.sync_dir / "snapshots"
        snapshots_dir.mkdir(exist_ok=True)
        
        snapshot_file = snapshots_dir / f"{snapshot_name}.json"
        with open(snapshot_file, 'w', encoding='utf-8') as f:
            json.dump(snapshot_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Создан снимок: {snapshot_name} ({len(snapshot_data['files'])} файлов)")
        
        return {
            'snapshot_name': snapshot_name,
            'file_count': len(snapshot_data['files']),
            'snapshot_file': str(snapshot_file)
        }
    
    def list_snapshots(self) -> List[Dict]:
        """
        Возвращает список доступных снимков
        
        Returns:
            List[Dict]: список снимков
        """
        snapshots_dir = self.sync_dir / "snapshots"
        
        if not snapshots_dir.exists():
            return []
        
        snapshots = []
        
        for snapshot_file in snapshots_dir.glob("*.json"):
            try:
                with open(snapshot_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                snapshots.append({
                    'name': data.get('name', snapshot_file.stem),
                    'created_at': data.get('created_at', ''),
                    'directory': data.get('directory', ''),
                    'file_count': len(data.get('files', {})),
                    'file': str(snapshot_file)
                })
            except:
                snapshots.append({
                    'name': snapshot_file.stem,
                    'created_at': '',
                    'directory': '',
                    'file_count': 0,
                    'file': str(snapshot_file)
                })
        
        return sorted(snapshots, key=lambda x: x['created_at'], reverse=True)
    
    def compare_with_snapshot(self, directory: str, snapshot_name: str) -> Dict:
        """
        Сравнивает текущее состояние директории со снимком
        
        Returns:
            Dict: различия
        """
        # Создаем временный снимок текущего состояния
        current_state = {}
        dir_path = Path(directory)
        
        if not dir_path.exists():
            return {'error': f'Директория не существует: {directory}'}
        
        for root, dirs, files in os.walk(dir_path):
            for file in files:
                file_path = Path(root) / file
                rel_path = file_path.relative_to(dir_path)
                
                try:
                    file_hash = self.calculate_file_hash(file_path)
                    current_state[str(rel_path)] = file_hash
                except:
                    pass
        
        # Загружаем снимок
        snapshot_file = self.sync_dir / "snapshots" / f"{snapshot_name}.json"
        
        if not snapshot_file.exists():
            return {'error': f'Снимок не найден: {snapshot_name}'}
        
        try:
            with open(snapshot_file, 'r', encoding='utf-8') as f:
                snapshot_data = json.load(f)
        except:
            return {'error': f'Ошибка загрузки снимка: {snapshot_name}'}
        
        snapshot_state = {path: info['hash'] for path, info in snapshot_data.get('files', {}).items()}
        
        # Сравниваем
        differences = {
            'added': [],
            'removed': [],
            'modified': [],
            'unchanged': []
        }
        
        all_files = set(current_state.keys()) | set(snapshot_state.keys())
        
        for file in all_files:
            current_hash = current_state.get(file)
            snapshot_hash = snapshot_state.get(file)
            
            if current_hash is None:
                differences['removed'].append(file)
            elif snapshot_hash is None:
                differences['added'].append(file)
            elif current_hash != snapshot_hash:
                differences['modified'].append(file)
            else:
                differences['unchanged'].append(file)
        
        return {
            'snapshot': snapshot_name,
            'directory': directory,
            'compared_at': datetime.now().isoformat(),
            'differences': differences,
            'summary': {
                'total_files': len(all_files),
                'added': len(differences['added']),
                'removed': len(differences['removed']),
                'modified': len(differences['modified']),
                'unchanged': len(differences['unchanged'])
            }
        }

# Синхронные обертки для удобства (ДОБАВЛЕНО)
def sync_files_sync(config, source_dir: str, target_dir: str, **kwargs):
    sync = FileSync(config)
    return sync.sync_files(source_dir, target_dir, **kwargs)

def create_snapshot_sync(config, directory: str, snapshot_name: str = None):
    sync = FileSync(config)
    return sync.create_snapshot(directory, snapshot_name)

def list_snapshots_sync(config):
    sync = FileSync(config)
    return sync.list_snapshots()

def compare_with_snapshot_sync(config, directory: str, snapshot_name: str):
    sync = FileSync(config)
    return sync.compare_with_snapshot(directory, snapshot_name)

# Тестирование
if __name__ == "__main__":
    print("🧪 Тест системы синхронизации")
    
    class TestConfig:
        data_dir = Path("test_data")
        data_dir.mkdir(exist_ok=True)
    
    config = TestConfig()
    sync = FileSync(config)
    
    # Создаем тестовые директории
    source_dir = config.data_dir / "source"
    target_dir = config.data_dir / "target"
    
    source_dir.mkdir(exist_ok=True)
    target_dir.mkdir(exist_ok=True)
    
    # Создаем тестовые файлы
    test_file1 = source_dir / "file1.txt"
    test_file2 = source_dir / "file2.txt"
    
    with open(test_file1, 'w') as f:
        f.write("Это тестовый файл 1")
    
    with open(test_file2, 'w') as f:
        f.write("Это тестовый файл 2")
    
    print(f"Созданы тестовые файлы в {source_dir}")
    
    # Тест синхронизации
    stats = sync.sync_files(str(source_dir), str(target_dir), dry_run=True)
    print(f"\n📊 Результаты синхронизации (dry run):")
    print(f"  Всего файлов: {stats['total_files']}")
    print(f"  Скопировано: {stats['copied']}")
    print(f"  Пропущено: {stats['skipped']}")
    
    # Тест снимка
    snapshot = sync.create_snapshot(str(source_dir), "test_snapshot")
    print(f"\n📸 Создан снимок: {snapshot['snapshot_name']}")
    print(f"  Файлов: {snapshot['file_count']}")
    
    # Список снимков
    snapshots = sync.list_snapshots()
    print(f"\n📁 Доступные снимки: {len(snapshots)}")
    
    print("\n✅ Тест завершен!")