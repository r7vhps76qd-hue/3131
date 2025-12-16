"""
Telegram архиватор - скачивание каналов и чатов
"""
import asyncio
import json
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import logging

logger = logging.getLogger("TelegramArchiver")

class TelegramArchiver:
    def __init__(self, config):
        """
        Инициализация архиватора
        
        Args:
            config: объект конфигурации
        """
        self.config = config
        self.session_file = config.data_dir / "telegram_session.session"
        self.archive_dir = config.data_dir / "telegram_archive"
        self.archive_dir.mkdir(exist_ok=True)
        
        # Настройки из конфига
        self.api_id = config.get('telegram.api_id')
        self.api_hash = config.get('telegram.api_hash')
        self.session_name = config.get('telegram.session_name', 'my_session')
        
        # Клиент Telegram (пока None)
        self.client = None
        
        logger.info(f"Telegram архиватор инициализирован")
        logger.info(f"Папка архива: {self.archive_dir}")
    
    async def init_client(self):
        """
        Инициализация клиента Telegram
        
        Returns:
            bool: успешно ли инициализирован клиент
        """
        try:
            # Пытаемся импортировать Telethon
            from telethon import TelegramClient
            from telethon.errors import SessionPasswordNeededError
            
            if not self.api_id or not self.api_hash:
                logger.error("API ID или API Hash не установлены!")
                logger.info("Получите API ключи на https://my.telegram.org")
                return False
            
            self.client = TelegramClient(
                str(self.session_file),
                self.api_id,
                self.api_hash
            )
            
            await self.client.start()
            logger.info("✅ Клиент Telegram успешно подключен")
            return True
            
        except ImportError:
            logger.warning("⚠️  Библиотека Telethon не установлена. Режим заглушки.")
            self.client = None
            return True  # Возвращаем True для работы в режиме заглушки
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Telegram: {e}")
            return False
    
    async def archive_channel(self, channel_link: str, limit: int = 100):
        """
        Архивация канала/чата
        
        Args:
            channel_link: ссылка на канал или чат
            limit: максимальное количество сообщений
            
        Returns:
            Dict: информация о результатах архивации
        """
        logger.info(f"Начинаю архивацию: {channel_link}")
        
        # Режим заглушки, если нет библиотеки
        if self.client is None:
            return await self._mock_archive(channel_link, limit)
        
        try:
            # Получаем информацию о канале
            entity = await self.client.get_entity(channel_link)
            channel_name = getattr(entity, 'title', str(entity.id))
            
            # Создаем папку для канала
            channel_dir = self.archive_dir / self._safe_filename(f"channel_{channel_name}")
            channel_dir.mkdir(exist_ok=True)
            
            # Папки для медиа
            media_dir = channel_dir / "media"
            media_dir.mkdir(exist_ok=True)
            docs_dir = channel_dir / "documents"
            docs_dir.mkdir(exist_ok=True)
            
            # Собираем сообщения
            messages_data = []
            media_count = 0
            doc_count = 0
            
            async for message in self.client.iter_messages(entity, limit=limit):
                message_info = {
                    'id': message.id,
                    'date': message.date.isoformat() if message.date else None,
                    'sender_id': message.sender_id,
                    'text': message.text or '',
                    'media': bool(message.media)
                }
                
                messages_data.append(message_info)
                
                # Скачиваем медиа
                if message.media:
                    try:
                        if hasattr(message.media, 'photo'):
                            filename = f"photo_{message.id}.jpg"
                            filepath = media_dir / filename
                            await message.download_media(file=str(filepath))
                            media_count += 1
                            message_info['photo'] = filename
                            
                        elif hasattr(message.media, 'document'):
                            filename = f"doc_{message.id}"
                            filepath = docs_dir / filename
                            await message.download_media(file=str(filepath))
                            doc_count += 1
                            message_info['document'] = filename
                    except Exception as e:
                        logger.warning(f"Ошибка скачивания медиа: {e}")
            
            # Сохраняем метаданные
            metadata = {
                'channel_name': channel_name,
                'channel_link': channel_link,
                'archive_date': datetime.now().isoformat(),
                'total_messages': len(messages_data),
                'media_files': media_count,
                'documents': doc_count,
                'messages': messages_data
            }
            
            metadata_file = channel_dir / "metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Архивация завершена: {channel_name}")
            logger.info(f"   Сообщений: {len(messages_data)}")
            logger.info(f"   Медиафайлов: {media_count}")
            logger.info(f"   Документов: {doc_count}")
            
            return metadata
            
        except Exception as e:
            logger.error(f"❌ Ошибка архивации: {e}")
            return {'error': str(e)}
    
    async def archive_chat(self, chat_identifier, limit: int = 100, chat_type: str = "private"):
        """
        Архивация чата (личного или группового)
        
        Args:
            chat_identifier: username, phone number или ID чата
            limit: максимальное количество сообщений
            chat_type: тип чата ("private", "group", "channel")
            
        Returns:
            Dict: информация о результатах архивации
        """
        logger.info(f"Начинаю архивацию чата: {chat_identifier} (тип: {chat_type})")
        
        # Режим заглушки, если нет библиотеки
        if self.client is None:
            return await self._mock_archive_chat(chat_identifier, limit, chat_type)
        
        try:
            # Получаем информацию о чате
            entity = await self.client.get_entity(chat_identifier)
            
            # Определяем тип и имя
            if hasattr(entity, 'title'):
                chat_name = entity.title
                chat_type = "group" if entity.megagroup else "channel"
            elif hasattr(entity, 'first_name') or hasattr(entity, 'username'):
                chat_name = f"{entity.first_name or ''} {entity.last_name or ''}".strip()
                if entity.username:
                    chat_name = f"@{entity.username} ({chat_name})"
                chat_type = "private"
            else:
                chat_name = str(entity.id)
            
            # Создаем папку для чата
            chat_dir = self.archive_dir / self._safe_filename(f"{chat_type}_{chat_name}")
            chat_dir.mkdir(exist_ok=True)
            
            # Папки для медиа
            media_dir = chat_dir / "media"
            media_dir.mkdir(exist_ok=True)
            docs_dir = chat_dir / "documents"
            docs_dir.mkdir(exist_ok=True)
            
            # Собираем сообщения
            messages_data = []
            media_count = 0
            doc_count = 0
            
            async for message in self.client.iter_messages(entity, limit=limit):
                message_info = {
                    'id': message.id,
                    'date': message.date.isoformat() if message.date else None,
                    'sender_id': message.sender_id,
                    'text': message.text or '',
                    'media': bool(message.media),
                    'out': message.out  # Исходящее или входящее
                }
                
                # Добавляем информацию об отправителе
                if message.sender:
                    sender_info = {
                        'id': message.sender_id,
                        'name': getattr(message.sender, 'first_name', '') + ' ' + 
                               getattr(message.sender, 'last_name', ''),
                        'username': getattr(message.sender, 'username', '')
                    }
                    message_info['sender'] = sender_info
                
                messages_data.append(message_info)
                
                # Скачиваем медиа
                if message.media:
                    try:
                        if hasattr(message.media, 'photo'):
                            filename = f"photo_{message.id}.jpg"
                            filepath = media_dir / filename
                            await message.download_media(file=str(filepath))
                            media_count += 1
                            message_info['photo'] = filename
                            
                        elif hasattr(message.media, 'document'):
                            filename = f"doc_{message.id}"
                            filepath = docs_dir / filename
                            await message.download_media(file=str(filepath))
                            doc_count += 1
                            message_info['document'] = filename
                    except Exception as e:
                        logger.warning(f"Ошибка скачивания медиа: {e}")
            
            # Сохраняем метаданные
            metadata = {
                'chat_name': chat_name,
                'chat_id': entity.id,
                'chat_type': chat_type,
                'archive_date': datetime.now().isoformat(),
                'total_messages': len(messages_data),
                'media_files': media_count,
                'documents': doc_count,
                'participants_count': getattr(entity, 'participants_count', 1),
                'messages': messages_data
            }
            
            metadata_file = chat_dir / "metadata.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            logger.info(f"✅ Архивация чата завершена: {chat_name}")
            logger.info(f"   Тип: {chat_type}")
            logger.info(f"   Сообщений: {len(messages_data)}")
            logger.info(f"   Медиафайлов: {media_count}")
            logger.info(f"   Документов: {doc_count}")
            
            return metadata
            
        except Exception as e:
            logger.error(f"❌ Ошибка архивации чата: {e}")
            return {'error': str(e)}
    
    async def archive(self, target, limit: int = 100, archive_type: str = "auto"):
        """
        Универсальный метод архивации (автоопределение типа)
        
        Args:
            target: ссылка, username или ID
            limit: лимит сообщений
            archive_type: "auto", "channel", "chat", "group"
            
        Returns:
            Dict: результаты архивации
        """
        # Автоопределение типа
        if archive_type == "auto":
            if isinstance(target, str):
                if target.startswith("https://t.me/+"):
                    archive_type = "group"
                elif target.startswith("https://t.me/"):
                    if any(keyword in target.lower() for keyword in ['/c/', 'channel']):
                        archive_type = "channel"
                    else:
                        archive_type = "chat"
                else:
                    archive_type = "chat"
            else:
                archive_type = "chat"
        
        logger.info(f"Архивация типа: {archive_type}, цель: {target}")
        
        if archive_type in ["channel", "group"]:
            return await self.archive_channel(target, limit)
        else:
            return await self.archive_chat(target, limit, archive_type)
    
    async def _mock_archive(self, channel_link: str, limit: int):
        """
        Заглушка для архивации (если Telethon не установлен)
        """
        logger.info("📝 РЕЖИМ ЗАГЛУШКИ: Имитация архивации")
        
        channel_name = channel_link.split('/')[-1] or "test_channel"
        channel_dir = self.archive_dir / self._safe_filename(f"channel_{channel_name}")
        channel_dir.mkdir(exist_ok=True)
        
        # Создаем тестовые данные
        messages_data = []
        for i in range(min(limit, 10)):
            messages_data.append({
                'id': i + 1,
                'date': datetime.now().isoformat(),
                'sender_id': 123456789,
                'text': f'Тестовое сообщение #{i+1} из канала {channel_name}',
                'media': i % 3 == 0
            })
        
        metadata = {
            'channel_name': channel_name,
            'channel_link': channel_link,
            'archive_date': datetime.now().isoformat(),
            'total_messages': len(messages_data),
            'media_files': 3,
            'documents': 2,
            'messages': messages_data,
            'note': '📌 Это тестовые данные. Установите telethon для реальной архивации.'
        }
        
        metadata_file = channel_dir / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        # Создаем тестовые файлы
        (channel_dir / "media").mkdir(exist_ok=True)
        (channel_dir / "documents").mkdir(exist_ok=True)
        
        test_file = channel_dir / "info.txt"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(f"Канал: {channel_name}\n")
            f.write(f"Ссылка: {channel_link}\n")
            f.write(f"Дата архивации: {datetime.now()}\n")
            f.write(f"Сообщений: {len(messages_data)}\n\n")
            f.write("⚠️  Для реальной архивации установите:\n")
            f.write("pip install telethon==1.34.1\n")
            f.write("И настройте API ключи в config.json\n")
        
        logger.info(f"✅ Созданы тестовые данные для: {channel_name}")
        logger.info(f"📁 Папка: {channel_dir}")
        
        return metadata
    
    async def _mock_archive_chat(self, chat_identifier, limit: int, chat_type: str):
        """
        Заглушка для архивации чата
        """
        logger.info("📝 РЕЖИМ ЗАГЛУШКИ: Имитация архивации чата")
        
        chat_name = chat_identifier.split('/')[-1] or f"{chat_type}_chat"
        chat_dir = self.archive_dir / self._safe_filename(f"{chat_type}_{chat_name}")
        chat_dir.mkdir(exist_ok=True)
        
        # Создаем тестовые данные для чата
        messages_data = []
        for i in range(min(limit, 10)):
            is_outgoing = i % 2 == 0
            messages_data.append({
                'id': i + 1,
                'date': datetime.now().isoformat(),
                'sender_id': 123456789 if is_outgoing else 987654321,
                'text': f'Тестовое сообщение #{i+1} в чате {chat_name}',
                'media': i % 4 == 0,
                'out': is_outgoing,
                'sender': {
                    'id': 123456789 if is_outgoing else 987654321,
                    'name': 'Вы' if is_outgoing else 'Собеседник',
                    'username': 'you' if is_outgoing else 'friend'
                }
            })
        
        metadata = {
            'chat_name': chat_name,
            'chat_id': 123456789,
            'chat_type': chat_type,
            'archive_date': datetime.now().isoformat(),
            'total_messages': len(messages_data),
            'media_files': 2,
            'documents': 1,
            'participants_count': 2 if chat_type == 'private' else 10,
            'messages': messages_data,
            'note': '📌 Это тестовые данные чата. Установите telethon для реальной архивации.'
        }
        
        metadata_file = chat_dir / "metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        
        # Создаем тестовые файлы
        (chat_dir / "media").mkdir(exist_ok=True)
        (chat_dir / "documents").mkdir(exist_ok=True)
        
        test_file = chat_dir / "chat_info.txt"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(f"Чат: {chat_name}\n")
            f.write(f"Тип: {chat_type}\n")
            f.write(f"Идентификатор: {chat_identifier}\n")
            f.write(f"Дата архивации: {datetime.now()}\n")
            f.write(f"Сообщений: {len(messages_data)}\n")
            f.write(f"Участников: {metadata['participants_count']}\n\n")
            f.write("⚠️  Для реальной архивации чатов установите:\n")
            f.write("pip install telethon==1.34.1\n")
            f.write("И настройте API ключи в config.json\n")
        
        logger.info(f"✅ Созданы тестовые данные чата: {chat_name}")
        logger.info(f"📁 Папка: {chat_dir}")
        
        return metadata
    
    def _safe_filename(self, filename: str) -> str:
        """
        Преобразует строку в безопасное имя файла
        
        Args:
            filename: исходное имя
            
        Returns:
            str: безопасное имя файла
        """
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        filename = filename.strip('. ')
        
        if len(filename) > 100:
            filename = filename[:50] + "..." + filename[-47:]
        
        return filename
    
    def get_archive_info(self):
        """
        Получает информацию о существующих архивах
        
        Returns:
            List: список архивов
        """
        archives = []
        
        if self.archive_dir.exists():
            for channel_dir in self.archive_dir.iterdir():
                if channel_dir.is_dir():
                    metadata_file = channel_dir / "metadata.json"
                    if metadata_file.exists():
                        try:
                            with open(metadata_file, 'r', encoding='utf-8') as f:
                                metadata = json.load(f)
                            
                            # Определяем тип архива
                            if 'channel_name' in metadata:
                                archive_type = 'channel'
                                name = metadata.get('channel_name', channel_dir.name)
                            elif 'chat_name' in metadata:
                                archive_type = metadata.get('chat_type', 'chat')
                                name = metadata.get('chat_name', channel_dir.name)
                            else:
                                archive_type = 'unknown'
                                name = channel_dir.name
                            
                            archives.append({
                                'type': archive_type,
                                'name': name,
                                'path': str(channel_dir),
                                'messages': metadata.get('total_messages', 0),
                                'date': metadata.get('archive_date', ''),
                                'link': metadata.get('channel_link', metadata.get('chat_id', ''))
                            })
                        except:
                            archives.append({
                                'type': 'unknown',
                                'name': channel_dir.name,
                                'path': str(channel_dir),
                                'messages': 0,
                                'date': '',
                                'link': ''
                            })
        
        return archives
    
    async def close(self):
        """Закрытие клиента"""
        if self.client:
            await self.client.disconnect()
            logger.info("Клиент Telegram отключен")

# Синхронные обертки
def archive_channel_sync(config, channel_link: str, limit: int = 100):
    archiver = TelegramArchiver(config)
    
    async def _run():
        await archiver.init_client()
        result = await archiver.archive_channel(channel_link, limit)
        await archiver.close()
        return result
    
    return asyncio.run(_run())

def archive_chat_sync(config, chat_identifier: str, limit: int = 100, chat_type: str = "private"):
    archiver = TelegramArchiver(config)
    
    async def _run():
        await archiver.init_client()
        result = await archiver.archive_chat(chat_identifier, limit, chat_type)
        await archiver.close()
        return result
    
    return asyncio.run(_run())

def archive_sync(config, target: str, limit: int = 100, archive_type: str = "auto"):
    archiver = TelegramArchiver(config)
    
    async def _run():
        await archiver.init_client()
        result = await archiver.archive(target, limit, archive_type)
        await archiver.close()
        return result
    
    return asyncio.run(_run())

def get_archives_sync(config):
    archiver = TelegramArchiver(config)
    return archiver.get_archive_info()

# Тестирование
if __name__ == "__main__":
    print("🧪 Тест Telegram архиватора")
    
    class TestConfig:
        data_dir = Path("data_test")
        data_dir.mkdir(exist_ok=True)
        def get(self, key, default=None):
            return default
    
    config = TestConfig()
    
    # Тест канала
    print("\n📢 Тест архивации канала:")
    result = archive_channel_sync(config, "test_channel", limit=3)
    print(f"Канал: {result.get('channel_name')}")
    
    # Тест чата
    print("\n💬 Тест архивации чата:")
    result = archive_chat_sync(config, "test_user", limit=3)
    print(f"Чат: {result.get('chat_name')}")
    print(f"Тип: {result.get('chat_type')}")
    
    # Список архивов
    archives = get_archives_sync(config)
    print(f"\n📁 Всего архивов: {len(archives)}")