"""
Subtitle utilities module for generating subtitles using Whisper AI.
Модуль утилит для генерации субтитров с использованием Whisper AI.
"""

import os
import datetime
from utils.ffmpeg_utils import run_ffmpeg


def extract_audio(video_path: str, audio_path: str) -> None:
    """
    Извлекает аудиодорожку из видеофайла в формате WAV для обработки в Whisper.
    
    Args:
        video_path: Путь к входному видеофайлу
        audio_path: Путь для сохранения извлеченного аудиофайла
    """
    cmd = [
        '-y',                # Перезаписать выходной файл если существует
        '-i', video_path,    # Входной видеофайл
        '-vn',               # Отключить видео (только аудио)
        '-ar', '16000',      # Частота дискретизации 16kHz (оптимально для Whisper)
        '-ac', '1',          # Моно (1 канал)
        '-c:a', 'pcm_s16le', # Кодек PCM 16-bit little endian
        audio_path           # Выходной аудиофайл
    ]
    
    run_ffmpeg(cmd, video_path)


def _format_time(seconds: float) -> str:
    """
    Форматирует время в секундах в формат SRT (HH:MM:SS,mmm).
    
    Args:
        seconds: Время в секундах (может быть дробным)
        
    Returns:
        Отформатированная строка времени в формате SRT
    """
    # Разделяем на часы, минуты и секунды
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    
    # Вычисляем миллисекунды
    ms = int((s - int(s)) * 1000)
    
    # Форматируем в строку HH:MM:SS,mmm
    return f"{int(h):02}:{int(m):02}:{int(s):02},{ms:03}"


def generate_srt_from_whisper(
    audio_path: str,
    srt_path: str,
    model_name: str,
    language: str,
    words_per_line: int
) -> str:
    """
    Генерирует SRT файл субтитров из аудиофайла используя Whisper AI.
    
    Args:
        audio_path: Путь к аудиофайлу для транскрипции
        srt_path: Путь для сохранения SRT файла
        model_name: Название модели Whisper (tiny, base, small, medium, large)
        language: Язык для распознавания ("Auto-detect" для автоопределения)
        words_per_line: Количество слов в одной строке субтитров
        
    Returns:
        Путь к созданному SRT файлу
        
    Raises:
        RuntimeError: Если не удалось загрузить модель Whisper
    """
    # Импортируем Whisper динамически
    import whisper
    
    print(f"Loading Whisper model '{model_name}'...")
    
    try:
        # Загружаем модель Whisper
        model = whisper.load_model(model_name)
    except Exception as e:
        raise RuntimeError(
            f"Не удалось загрузить модель Whisper '{model_name}'. "
            f"Убедитесь, что она доступна. Ошибка: {e}"
        )
    
    print('Model loaded. Starting transcription...')
    
    # Определяем язык для транскрипции
    if language != 'Auto-detect':
        lang_code = language.lower()
    else:
        lang_code = None
    
    # Выполняем транскрипцию с временными метками для слов
    result = model.transcribe(
        audio_path,
        language=lang_code,
        verbose=True,
        fp16=False,        # Отключаем fp16 для совместимости
        word_timestamps=True  # Включаем временные метки для слов
    )
    
    print('Transcription finished. Generating SRT file...')
    
    # Генерируем содержимое SRT файла
    srt_content = ''
    sub_index = 1
    
    # Обрабатываем каждый сегмент транскрипции
    for segment in result['segments']:
        # Проверяем наличие временных меток для слов
        if 'words' not in segment:
            continue
        
        words = segment['words']
        num_words = len(words)
        
        # Разбиваем слова на группы по words_per_line
        for i in range(0, num_words, words_per_line):
            chunk = words[i:i + words_per_line]
            
            if not chunk:
                continue
            
            # Получаем время начала и конца для данной группы слов
            start_time = _format_time(chunk[0]['start'])
            end_time = _format_time(chunk[-1]['end'])
            
            # Объединяем слова в текст
            text = ' '.join([word['word'] for word in chunk]).strip()
            
            # Добавляем субтитр в SRT формате
            srt_content += f"{sub_index}\n"
            srt_content += f"{start_time} --> {end_time}\n"
            srt_content += f"{text}\n\n"
            
            sub_index += 1
    
    # Сохраняем SRT файл
    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write(srt_content)
    
    print(f'SRT file saved to {srt_path}')
    return srt_path


# Дополнительные вспомогательные функции

def validate_whisper_model(model_name: str) -> bool:
    """
    Проверяет, является ли название модели валидным для Whisper.
    
    Args:
        model_name: Название модели для проверки
        
    Returns:
        True если модель валидна, False в противном случае
    """
    valid_models = ['tiny', 'base', 'small', 'medium', 'large', 'large-v2', 'large-v3']
    return model_name in valid_models


def get_available_languages() -> list:
    """
    Получает список доступных языков для Whisper.
    
    Returns:
        Список кодов языков, поддерживаемых Whisper
    """
    try:
        import whisper
        return list(whisper.tokenizer.LANGUAGES.keys())
    except ImportError:
        # Базовый список, если Whisper недоступен
        return [
            'en', 'ru', 'es', 'fr', 'de', 'it', 'pt', 'pl', 'tr', 'ko',
            'zh', 'ja', 'hi', 'ar', 'th', 'vi', 'ms', 'uk', 'cs', 'ro'
        ]


def estimate_transcription_time(audio_duration: float, model_name: str) -> float:
    """
    Оценивает примерное время транскрипции на основе длительности аудио и модели.
    
    Args:
        audio_duration: Длительность аудио в секундах
        model_name: Название модели Whisper
        
    Returns:
        Оценочное время транскрипции в секундах
    """
    # Примерные коэффициенты скорости для разных моделей
    # (время транскрипции / время аудио)
    speed_factors = {
        'tiny': 0.1,
        'base': 0.2,
        'small': 0.4,
        'medium': 0.8,
        'large': 1.5,
        'large-v2': 1.5,
        'large-v3': 1.5
    }
    
    factor = speed_factors.get(model_name, 1.0)
    return audio_duration * factor


def clean_subtitle_text(text: str) -> str:
    """
    Очищает текст субтитров от нежелательных символов и форматирует его.
    
    Args:
        text: Исходный текст субтитра
        
    Returns:
        Очищенный текст субтитра
    """
    # Убираем лишние пробелы
    text = ' '.join(text.split())
    
    # Убираем повторяющуюся пунктуацию
    import re
    text = re.sub(r'([.!?])\1+', r'\1', text)
    
    # Капитализируем первую букву
    if text:
        text = text[0].upper() + text[1:]
    
    return text


def split_long_subtitles(srt_path: str, max_chars: int = 80) -> str:
    """
    Разбивает длинные субтитры на более короткие строки.
    
    Args:
        srt_path: Путь к SRT файлу
        max_chars: Максимальное количество символов в строке
        
    Returns:
        Путь к обновленному SRT файлу
    """
    with open(srt_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.strip().split('\n')
    new_lines = []
    
    i = 0
    while i < len(lines):
        if lines[i].strip().isdigit():  # Номер субтитра
            new_lines.append(lines[i])
            i += 1
            
            if i < len(lines) and '-->' in lines[i]:  # Временная метка
                new_lines.append(lines[i])
                i += 1
                
                # Текст субтитра
                subtitle_text = ''
                while i < len(lines) and lines[i].strip() and not lines[i].strip().isdigit():
                    subtitle_text += lines[i] + ' '
                    i += 1
                
                # Разбиваем длинный текст
                subtitle_text = subtitle_text.strip()
                if len(subtitle_text) > max_chars:
                    words = subtitle_text.split()
                    current_line = ''
                    
                    for word in words:
                        if len(current_line + ' ' + word) <= max_chars:
                            current_line += (' ' + word) if current_line else word
                        else:
                            if current_line:
                                new_lines.append(current_line)
                                current_line = word
                            else:
                                new_lines.append(word)
                    
                    if current_line:
                        new_lines.append(current_line)
                else:
                    new_lines.append(subtitle_text)
                
                new_lines.append('')  # Пустая строка после субтитра
        else:
            i += 1
    
    # Сохраняем обновленный файл
    with open(srt_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(new_lines))
    
    return srt_path


def convert_srt_to_vtt(srt_path: str, vtt_path: str) -> str:
    """
    Конвертирует SRT файл в WebVTT формат.
    
    Args:
        srt_path: Путь к исходному SRT файлу
        vtt_path: Путь для сохранения VTT файла
        
    Returns:
        Путь к созданному VTT файлу
    """
    with open(srt_path, 'r', encoding='utf-8') as f:
        srt_content = f.read()
    
    # Заменяем запятые на точки в временных метках (SRT -> VTT)
    vtt_content = 'WEBVTT\n\n'
    vtt_content += srt_content.replace(',', '.')
    
    with open(vtt_path, 'w', encoding='utf-8') as f:
        f.write(vtt_content)
    
    return vtt_path


def merge_subtitle_files(srt_files: list, output_path: str) -> str:
    """
    Объединяет несколько SRT файлов в один.
    
    Args:
        srt_files: Список путей к SRT файлам для объединения
        output_path: Путь для сохранения объединенного файла
        
    Returns:
        Путь к объединенному SRT файлу
    """
    merged_content = ''
    subtitle_index = 1
    
    for srt_file in srt_files:
        if not os.path.exists(srt_file):
            continue
            
        with open(srt_file, 'r', encoding='utf-8') as f:
            content = f.read().strip()
        
        if not content:
            continue
        
        # Перенумеровываем субтитры
        lines = content.split('\n')
        current_subtitle = []
        
        for line in lines:
            if line.strip().isdigit():
                if current_subtitle:
                    # Добавляем предыдущий субтитр
                    current_subtitle[0] = str(subtitle_index)
                    merged_content += '\n'.join(current_subtitle) + '\n\n'
                    subtitle_index += 1
                    current_subtitle = []
                current_subtitle.append(str(subtitle_index))
            else:
                current_subtitle.append(line)
        
        # Добавляем последний субтитр
        if current_subtitle:
            current_subtitle[0] = str(subtitle_index)
            merged_content += '\n'.join(current_subtitle) + '\n\n'
            subtitle_index += 1
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(merged_content.strip())
    
    return output_path