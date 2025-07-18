"""
Path utilities module for handling resource paths in PyInstaller applications.
Модуль утилит для работы с путями ресурсов в приложениях PyInstaller.
"""

import shutil
import sys
import os

from utils.constants import FFMPEG_EXE_PATH


def resource_path(relative_path: str) -> str:
    """
    Получает абсолютный путь к ресурсу, работает как в режиме разработки,
    так и в собранном PyInstaller приложении.
    
    В PyInstaller приложениях временные файлы извлекаются в папку,
    путь к которой хранится в sys._MEIPASS.
    
    Args:
        relative_path: Относительный путь к ресурсу
        
    Returns:
        Абсолютный путь к ресурсу
    """
    try:
        # PyInstaller создает временную папку и сохраняет путь в _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        # В режиме разработки используем текущую директорию
        base_path = os.path.abspath('.')
    except Exception:
        # Fallback на текущую директорию при любых других ошибках
        base_path = os.path.abspath('.')

    return os.path.join(base_path, relative_path)

# Поиск FFPMEG где рядом с исполняемым файлом или в системном PATH

def get_ffmpeg_path():
    local_path = resource_path(FFMPEG_EXE_PATH)
    if os.path.isfile(local_path):
        return local_path
    
    # Поиск в системном PATH
    system_path = shutil.which('ffmpeg')
    if system_path:
        return system_path
    
    raise FileNotFoundError("FFmpeg not found at local path or in system PATH.")

# Поиск YT_DLP где рядом с исполняемым файлом или в системном PATH

def get_ytdlp_path():
    local_path = resource_path('yt-dlp.exe')
    if os.path.isfile(local_path):
        return local_path
    
    # Поиск в системном PATH
    system_path = shutil.which('yt-dlp')
    if system_path:
        return system_path
    
    raise FileNotFoundError("yt-dlp not found at local path or in system PATH.")

# Дополнительные вспомогательные функции для работы с путями

def get_application_path() -> str:
    """
    Получает путь к директории приложения.
    
    Returns:
        Путь к директории, где находится исполняемый файл или скрипт
    """
    if getattr(sys, 'frozen', False):
        # Приложение запущено из PyInstaller bundle
        return os.path.dirname(sys.executable)
    else:
        # Приложение запущено из исходного кода
        return os.path.dirname(os.path.abspath(__file__))


def get_data_directory() -> str:
    """
    Получает путь к директории данных приложения.
    
    Returns:
        Путь к директории для хранения данных приложения
    """
    app_path = get_application_path()
    data_dir = os.path.join(app_path, 'data')
    
    # Создаем директорию если она не существует
    os.makedirs(data_dir, exist_ok=True)
    
    return data_dir


def get_config_directory() -> str:
    """
    Получает путь к директории конфигурации приложения.
    
    Returns:
        Путь к директории для хранения конфигурационных файлов
    """
    app_path = get_application_path()
    config_dir = os.path.join(app_path, 'config')
    
    # Создаем директорию если она не существует
    os.makedirs(config_dir, exist_ok=True)
    
    return config_dir


def get_temp_directory() -> str:
    """
    Получает путь к временной директории приложения.
    
    Returns:
        Путь к временной директории
    """
    app_path = get_application_path()
    temp_dir = os.path.join(app_path, 'temp')
    
    # Создаем директорию если она не существует
    os.makedirs(temp_dir, exist_ok=True)
    
    return temp_dir


def get_logs_directory() -> str:
    """
    Получает путь к директории логов приложения.
    
    Returns:
        Путь к директории для хранения файлов логов
    """
    app_path = get_application_path()
    logs_dir = os.path.join(app_path, 'logs')
    
    # Создаем директорию если она не существует
    os.makedirs(logs_dir, exist_ok=True)
    
    return logs_dir


def normalize_path(path: str) -> str:
    """
    Нормализует путь, заменяя разделители на подходящие для текущей ОС.
    
    Args:
        path: Исходный путь
        
    Returns:
        Нормализованный путь
    """
    return os.path.normpath(path)


def is_frozen() -> bool:
    """
    Проверяет, запущено ли приложение из PyInstaller bundle.
    
    Returns:
        True если приложение "заморожено" (собрано PyInstaller), False в противном случае
    """
    return getattr(sys, 'frozen', False)


def get_executable_name() -> str:
    """
    Получает имя исполняемого файла приложения.
    
    Returns:
        Имя исполняемого файла без расширения
    """
    if is_frozen():
        executable = os.path.basename(sys.executable)
    else:
        executable = os.path.basename(sys.argv[0]) if sys.argv else 'python'
    
    # Убираем расширение .exe на Windows
    name, ext = os.path.splitext(executable)
    return name


def resolve_relative_path(base_path: str, relative_path: str) -> str:
    """
    Разрешает относительный путь относительно базового пути.
    
    Args:
        base_path: Базовый путь
        relative_path: Относительный путь
        
    Returns:
        Абсолютный путь
    """
    if os.path.isabs(relative_path):
        return relative_path
    
    return os.path.abspath(os.path.join(base_path, relative_path))


def ensure_path_exists(path: str, is_file: bool = False) -> bool:
    """
    Убеждается, что путь существует, создавая директории при необходимости.
    
    Args:
        path: Путь для проверки/создания
        is_file: True если path указывает на файл, False если на директорию
        
    Returns:
        True если путь существует или был создан, False при ошибке
    """
    try:
        if is_file:
            # Если это файл, создаем родительскую директорию
            directory = os.path.dirname(path)
            if directory:
                os.makedirs(directory, exist_ok=True)
        else:
            # Если это директория, создаем её
            os.makedirs(path, exist_ok=True)
        
        return True
    except Exception as e:
        print(f"Error ensuring path exists '{path}': {e}")
        return False


def get_relative_path(base_path: str, target_path: str) -> str:
    """
    Получает относительный путь от базового пути к целевому пути.
    
    Args:
        base_path: Базовый путь
        target_path: Целевой путь
        
    Returns:
        Относительный путь от base_path к target_path
    """
    try:
        return os.path.relpath(target_path, base_path)
    except ValueError:
        # Если пути на разных дисках (Windows), возвращаем абсолютный путь
        return os.path.abspath(target_path)


def safe_join(*paths: str) -> str:
    """
    Безопасно объединяет пути, предотвращая выход за пределы базовой директории.
    
    Args:
        *paths: Компоненты пути для объединения
        
    Returns:
        Безопасно объединенный путь
    """
    result = os.path.join(*paths)
    
    # Нормализуем путь для удаления .. и .
    normalized = os.path.normpath(result)
    
    return normalized


def get_file_paths_in_directory(directory: str, extensions: list = None, recursive: bool = False) -> list:
    """
    Получает список файлов в директории с возможной фильтрацией по расширениям.
    
    Args:
        directory: Путь к директории
        extensions: Список расширений для фильтрации (например, ['.txt', '.py'])
        recursive: Рекурсивно обходить поддиректории
        
    Returns:
        Список путей к файлам
    """
    files = []
    
    if not os.path.isdir(directory):
        return files
    
    try:
        if recursive:
            for root, dirs, filenames in os.walk(directory):
                for filename in filenames:
                    file_path = os.path.join(root, filename)
                    
                    if extensions:
                        file_ext = os.path.splitext(filename)[1].lower()
                        if file_ext in [ext.lower() for ext in extensions]:
                            files.append(file_path)
                    else:
                        files.append(file_path)
        else:
            for item in os.listdir(directory):
                item_path = os.path.join(directory, item)
                
                if os.path.isfile(item_path):
                    if extensions:
                        file_ext = os.path.splitext(item)[1].lower()
                        if file_ext in [ext.lower() for ext in extensions]:
                            files.append(item_path)
                    else:
                        files.append(item_path)
    
    except Exception as e:
        print(f"Error reading directory '{directory}': {e}")
    
    return files