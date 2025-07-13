"""
YouTube utilities module for downloading videos using yt-dlp.
Модуль утилит для скачивания видео с YouTube используя yt-dlp.
"""

import subprocess
import platform
import shlex
import os
from utils.path_utils import get_ytdlp_path, resource_path


def download_video(url: str, out_path: str) -> bool:
    """
    Downloads a video from a URL using a bundled youtube-dlp.
    
    Args:
        url: URL видео для скачивания
        out_path: Путь для сохранения видео
        
    Returns:
        True если скачивание прошло успешно, False в противном случае
        
    Raises:
        FileNotFoundError: Если yt-dlp не найден
        subprocess.CalledProcessError: Если yt-dlp завершился с ошибкой
        RuntimeError: При других ошибках выполнения
    """
    # Путь к исполняемому файлу yt-dlp
    yt_dlp_exe_path = get_ytdlp_path()
    
    # Команда для скачивания видео с лучшим качеством в формате MP4
    command = [
        yt_dlp_exe_path,
        '-f', 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',  # Формат видео
        '--merge-output-format', 'mp4',  # Объединить в MP4
        '--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 YaBrowser/25.6.0.0 Safari/537.36',  # User-Agent
        '--force-ipv4',  # (опционально) форс IPv4
        '-o', out_path,  # Выходной файл
        url  # URL для скачивания
    ]

    # Логирование команды
    print(f'Running youtube-dlp command: {" ".join(shlex.quote(c) for c in command)}')
    
    # Настройка для Windows (скрытие окна консоли)
    creationflags = 0
    startupinfo = None
    
    if platform.system() == 'Windows':
        creationflags = subprocess.CREATE_NO_WINDOW
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
    
    try:
        # Запуск процесса с захватом вывода
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace',
            creationflags=creationflags,
            startupinfo=startupinfo
        )
        
        output_lines = []
        
        # Чтение вывода в реальном времени
        while True:
            line = process.stdout.readline()
            if not line:
                break
                
            line = line.strip()
            if line:
                print(f'youtube-dlp: {line}')
                output_lines.append(line)
        
        # Закрытие потока и ожидание завершения
        process.stdout.close()
        return_code = process.wait()
        
        # Проверка кода возврата
        if return_code != 0:
            error_message = (
                f'youtube-dlp failed with exit code {return_code} for URL \'{url}\'.\n'
                f'Command: {" ".join(shlex.quote(c) for c in command)}\n'
                f'Last lines of output:\n' + '\n'.join(output_lines[-15:])
            )
            raise subprocess.CalledProcessError(
                return_code, 
                command, 
                output='\n'.join(output_lines)
            )
        
        print(f"youtube-dlp successfully downloaded video to '{out_path}'")
        return True
        
    except FileNotFoundError:
        raise FileNotFoundError(
            f'youtube-dlp not found at the specified path: {yt_dlp_exe_path}. '
            "Please ensure it's included in the package."
        )
    except Exception as e:
        raise RuntimeError(f"An error occurred while running youtube-dlp for URL '{url}': {e}")


# Дополнительные вспомогательные функции

def get_video_info(url: str) -> dict:
    """
    Получает информацию о видео без его скачивания.
    
    Args:
        url: URL видео
        
    Returns:
        Словарь с информацией о видео
        
    Raises:
        FileNotFoundError: Если yt-dlp не найден
        RuntimeError: При ошибках выполнения
    """
    yt_dlp_exe_path = get_ytdlp_path()
    
    command = [
        yt_dlp_exe_path,
        '--dump-json',  # Вывод информации в JSON
        '--no-download',  # Не скачивать видео
        url
    ]
    
    # Настройка для Windows
    creationflags = 0
    startupinfo = None
    
    if platform.system() == 'Windows':
        creationflags = subprocess.CREATE_NO_WINDOW
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            creationflags=creationflags,
            startupinfo=startupinfo,
            check=True
        )
        
        import json
        return json.loads(result.stdout)
        
    except FileNotFoundError:
        raise FileNotFoundError(
            f'youtube-dlp not found at the specified path: {yt_dlp_exe_path}. '
            "Please ensure it's included in the package."
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to get video info for URL '{url}': {e.stderr}")
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse video info JSON: {e}")
    except Exception as e:
        raise RuntimeError(f"An error occurred while getting video info for URL '{url}': {e}")


def download_audio_only(url: str, out_path: str, format: str = 'mp3') -> bool:
    """
    Скачивает только аудиодорожку из видео.
    
    Args:
        url: URL видео
        out_path: Путь для сохранения аудио
        format: Формат аудио (mp3, m4a, wav, etc.)
        
    Returns:
        True если скачивание прошло успешно
        
    Raises:
        FileNotFoundError: Если yt-dlp не найден
        RuntimeError: При ошибках выполнения
    """
    yt_dlp_exe_path = get_ytdlp_path()
    
    command = [
        yt_dlp_exe_path,
        '-f', 'bestaudio',  # Лучшее качество аудио
        '--extract-audio',  # Извлечь аудио
        '--audio-format', format,  # Формат аудио
        '-o', out_path,
        url
    ]
    
    print(f'Running youtube-dlp audio download: {" ".join(shlex.quote(c) for c in command)}')
    
    # Настройка для Windows
    creationflags = 0
    startupinfo = None
    
    if platform.system() == 'Windows':
        creationflags = subprocess.CREATE_NO_WINDOW
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            creationflags=creationflags,
            startupinfo=startupinfo,
            check=True
        )
        
        print(f"youtube-dlp successfully downloaded audio to '{out_path}'")
        return True
        
    except FileNotFoundError:
        raise FileNotFoundError(
            f'youtube-dlp not found at the specified path: {yt_dlp_exe_path}. '
            "Please ensure it's included in the package."
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to download audio for URL '{url}': {e.stderr}")
    except Exception as e:
        raise RuntimeError(f"An error occurred while downloading audio for URL '{url}': {e}")


def get_available_formats(url: str) -> list:
    """
    Получает список доступных форматов для видео.
    
    Args:
        url: URL видео
        
    Returns:
        Список доступных форматов
        
    Raises:
        FileNotFoundError: Если yt-dlp не найден
        RuntimeError: При ошибках выполнения
    """
    yt_dlp_exe_path = get_ytdlp_path()
    
    command = [
        yt_dlp_exe_path,
        '--list-formats',  # Список форматов
        '--no-download',   # Не скачивать
        url
    ]
    
    # Настройка для Windows
    creationflags = 0
    startupinfo = None
    
    if platform.system() == 'Windows':
        creationflags = subprocess.CREATE_NO_WINDOW
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            creationflags=creationflags,
            startupinfo=startupinfo,
            check=True
        )
        
        # Парсим вывод форматов
        formats = []
        lines = result.stdout.split('\n')
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('[') and 'format code' not in line.lower():
                # Простое извлечение информации о формате
                if ' ' in line:
                    formats.append(line)
        
        return formats
        
    except FileNotFoundError:
        raise FileNotFoundError(
            f'youtube-dlp not found at the specified path: {yt_dlp_exe_path}. '
            "Please ensure it's included in the package."
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to get formats for URL '{url}': {e.stderr}")
    except Exception as e:
        raise RuntimeError(f"An error occurred while getting formats for URL '{url}': {e}")


def download_with_custom_format(url: str, out_path: str, format_selector: str) -> bool:
    """
    Скачивает видео с пользовательским селектором формата.
    
    Args:
        url: URL видео
        out_path: Путь для сохранения
        format_selector: Селектор формата для yt-dlp (например, "720p", "worst", "best[height<=480]")
        
    Returns:
        True если скачивание прошло успешно
        
    Raises:
        FileNotFoundError: Если yt-dlp не найден
        RuntimeError: При ошибках выполнения
    """
    yt_dlp_exe_path = get_ytdlp_path()
    
    command = [
        yt_dlp_exe_path,
        '-f', format_selector,
        '--merge-output-format', 'mp4',
        '-o', out_path,
        url
    ]
    
    print(f'Running youtube-dlp with custom format: {" ".join(shlex.quote(c) for c in command)}')
    
    # Настройка для Windows
    creationflags = 0
    startupinfo = None
    
    if platform.system() == 'Windows':
        creationflags = subprocess.CREATE_NO_WINDOW
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            creationflags=creationflags,
            startupinfo=startupinfo,
            check=True
        )
        
        print(f"youtube-dlp successfully downloaded video to '{out_path}'")
        return True
        
    except FileNotFoundError:
        raise FileNotFoundError(
            f'youtube-dlp not found at the specified path: {yt_dlp_exe_path}. '
            "Please ensure it's included in the package."
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to download video with format '{format_selector}' for URL '{url}': {e.stderr}")
    except Exception as e:
        raise RuntimeError(f"An error occurred while downloading video for URL '{url}': {e}")


def validate_url(url: str) -> bool:
    """
    Проверяет, является ли URL валидным для скачивания.
    
    Args:
        url: URL для проверки
        
    Returns:
        True если URL валиден для скачивания
    """
    yt_dlp_exe_path = get_ytdlp_path()
    
    command = [
        yt_dlp_exe_path,
        '--simulate',  # Симуляция без скачивания
        '--quiet',     # Тихий режим
        url
    ]
    
    # Настройка для Windows
    creationflags = 0
    startupinfo = None
    
    if platform.system() == 'Windows':
        creationflags = subprocess.CREATE_NO_WINDOW
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='replace',
            creationflags=creationflags,
            startupinfo=startupinfo,
            timeout=30  # Таймаут 30 секунд
        )
        
        return result.returncode == 0
        
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        return False


def get_video_title(url: str) -> str:
    """
    Получает название видео по URL.
    
    Args:
        url: URL видео
        
    Returns:
        Название видео или пустую строку при ошибке
    """
    try:
        info = get_video_info(url)
        return info.get('title', 'Unknown Title')
    except Exception:
        return 'Unknown Title'


def get_video_duration(url: str) -> int:
    """
    Получает продолжительность видео в секундах.
    
    Args:
        url: URL видео
        
    Returns:
        Продолжительность в секундах или 0 при ошибке
    """
    try:
        info = get_video_info(url)
        return info.get('duration', 0)
    except Exception:
        return 0


def is_yt_dlp_available() -> bool:
    """
    Проверяет доступность yt-dlp.
    
    Returns:
        True если yt-dlp доступен
    """
    try:
        yt_dlp_exe_path = get_ytdlp_path()
        return os.path.isfile(yt_dlp_exe_path)
    except Exception:
        return False