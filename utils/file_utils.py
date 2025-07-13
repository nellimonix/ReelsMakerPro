"""
File utilities module for handling video files and folders.
Модуль утилит для работы с видеофайлами и папками.
"""

import os
import mimetypes
from typing import List

# Импорт констант расширений файлов
try:
    from utils.constants import VIDEO_EXTENSIONS, GIF_EXTENSIONS, VALID_INPUT_EXTENSIONS
except ImportError:
    # Fallback значения если модуль constants недоступен
    VIDEO_EXTENSIONS = ['.mp4', '.avi', '.mov', '.mkv', '.wmv', '.flv', '.webm', '.m4v']
    GIF_EXTENSIONS = ['.gif']
    VALID_INPUT_EXTENSIONS = VIDEO_EXTENSIONS + GIF_EXTENSIONS

# Инициализация mimetypes для корректной работы
mimetypes.init()


def is_video_file(path: str) -> bool:
    """
    Проверяет, является ли файл видеофайлом.
    
    Проверка производится двумя способами:
    1. По расширению файла (быстрая проверка)
    2. По MIME-типу файла (более точная проверка)
    
    Args:
        path: Путь к файлу для проверки
        
    Returns:
        True если файл является видеофайлом, False в противном случае
    """
    # Проверяем, что файл существует
    if not os.path.isfile(path):
        return False
    
    # Получаем расширение файла в нижнем регистре
    ext = os.path.splitext(path)[1].lower()
    
    # Быстрая проверка по расширению
    if ext in VIDEO_EXTENSIONS:
        return True
    
    # Дополнительная проверка по MIME-типу
    try:
        mime_type, _ = mimetypes.guess_type(path)
        if mime_type is not None and mime_type.startswith('video'):
            return True
    except Exception as e:
        print(f'Warning: Could not guess mime type for {path}: {e}')
        return False
    
    return False


def is_gif_file(path: str) -> bool:
    """
    Проверяет, является ли файл GIF-файлом.
    
    Args:
        path: Путь к файлу для проверки
        
    Returns:
        True если файл является GIF-файлом, False в противном случае
    """
    # Проверяем, что файл существует
    if not os.path.isfile(path):
        return False
    
    # Получаем расширение файла в нижнем регистре
    ext = os.path.splitext(path)[1].lower()
    
    # Проверяем, находится ли расширение в списке GIF расширений
    return ext in GIF_EXTENSIONS


def find_videos_in_folder(folder: str, include_gifs: bool = False) -> List[str]:
    """
    Рекурсивно ищет все видеофайлы в указанной папке и её подпапках.
    
    Args:
        folder: Путь к папке для поиска
        include_gifs: Включать ли GIF файлы в результаты поиска
        
    Returns:
        Список путей к найденным видеофайлам
    """
    found = []
    
    # Определяем список допустимых расширений
    if include_gifs:
        valid_extensions = VIDEO_EXTENSIONS + GIF_EXTENSIONS
    else:
        valid_extensions = VIDEO_EXTENSIONS
    
    # Проверяем, что папка существует
    if not os.path.isdir(folder):
        print(f'Error: Folder not found: {folder}')
        return found
    
    try:
        # Рекурсивно обходим все файлы в папке
        for root, dirs, files in os.walk(folder):
            for name in files:
                # Получаем полный путь к файлу
                fp = os.path.join(root, name)
                
                # Получаем расширение файла в нижнем регистре
                ext = os.path.splitext(name)[1].lower()
                
                # Проверяем, подходит ли расширение
                if ext in valid_extensions:
                    try:
                        # Проверяем доступность файла для чтения
                        if os.access(fp, os.R_OK):
                            found.append(fp)
                        else:
                            print(f'Warning: No read access to file: {fp}')
                    except Exception as e:
                        print(f'Warning: Could not access file {fp}: {e}')
                        
    except Exception as e:
        print(f'Error walking directory {folder}: {e}')
    
    return found


# Дополнительные вспомогательные функции

def get_file_extension(path: str) -> str:
    """
    Получает расширение файла в нижнем регистре.
    
    Args:
        path: Путь к файлу
        
    Returns:
        Расширение файла (включая точку) в нижнем регистре
    """
    return os.path.splitext(path)[1].lower()


def is_valid_input_file(path: str) -> bool:
    """
    Проверяет, является ли файл допустимым входным файлом для обработки.
    
    Args:
        path: Путь к файлу
        
    Returns:
        True если файл можно использовать как входной, False в противном случае
    """
    return is_video_file(path) or is_gif_file(path)


def get_file_size(path: str) -> int:
    """
    Получает размер файла в байтах.
    
    Args:
        path: Путь к файлу
        
    Returns:
        Размер файла в байтах, 0 если файл не найден или недоступен
    """
    try:
        return os.path.getsize(path)
    except (OSError, FileNotFoundError):
        return 0


def format_file_size(size_bytes: int) -> str:
    """
    Форматирует размер файла в человекочитаемый вид.
    
    Args:
        size_bytes: Размер в байтах
        
    Returns:
        Отформатированная строка с размером файла
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"


def validate_file_path(path: str) -> tuple[bool, str]:
    """
    Валидирует путь к файлу и возвращает результат с описанием ошибки.
    
    Args:
        path: Путь к файлу для валидации
        
    Returns:
        Кортеж (валидность, сообщение об ошибке)
    """
    if not path:
        return False, "Путь к файлу не указан"
    
    if not os.path.exists(path):
        return False, f"Файл не найден: {path}"
    
    if not os.path.isfile(path):
        return False, f"Указанный путь не является файлом: {path}"
    
    if not os.access(path, os.R_OK):
        return False, f"Нет доступа на чтение файла: {path}"
    
    if not is_valid_input_file(path):
        return False, f"Неподдерживаемый тип файла: {path}"
    
    return True, "Файл валиден"


def ensure_directory_exists(directory: str) -> bool:
    """
    Создает директорию если она не существует.
    
    Args:
        directory: Путь к директории
        
    Returns:
        True если директория существует или была создана, False при ошибке
    """
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception as e:
        print(f'Error creating directory {directory}: {e}')
        return False


def safe_filename(filename: str) -> str:
    """
    Очищает имя файла от недопустимых символов.
    
    Args:
        filename: Исходное имя файла
        
    Returns:
        Безопасное имя файла
    """
    # Символы, недопустимые в именах файлов
    invalid_chars = '<>:"/\\|?*'
    
    # Заменяем недопустимые символы на подчеркивания
    safe_name = filename
    for char in invalid_chars:
        safe_name = safe_name.replace(char, '_')
    
    # Убираем лишние пробелы и точки в начале и конце
    safe_name = safe_name.strip(' .')
    
    # Ограничиваем длину имени файла
    if len(safe_name) > 255:
        name, ext = os.path.splitext(safe_name)
        safe_name = name[:255-len(ext)] + ext
    
    return safe_name or "unnamed"


def get_unique_filename(base_path: str) -> str:
    """
    Генерирует уникальное имя файла, добавляя суффикс если файл уже существует.
    
    Args:
        base_path: Базовый путь к файлу
        
    Returns:
        Уникальный путь к файлу
    """
    if not os.path.exists(base_path):
        return base_path
    
    directory = os.path.dirname(base_path)
    name, ext = os.path.splitext(os.path.basename(base_path))
    
    counter = 1
    while True:
        new_name = f"{name}_{counter}{ext}"
        new_path = os.path.join(directory, new_name)
        
        if not os.path.exists(new_path):
            return new_path
        
        counter += 1
        
        # Защита от бесконечного цикла
        if counter > 10000:
            import time
            timestamp = int(time.time())
            new_name = f"{name}_{timestamp}{ext}"
            return os.path.join(directory, new_name)