from PyQt5.QtCore import QThread, pyqtSignal
import os
import random
import subprocess
import uuid
from typing import List, Optional, Dict

from utils.ffmpeg_utils import process_single, detect_crop_dimensions
from utils.subtitle_utils import extract_audio, generate_srt_from_whisper


class Worker(QThread):
    # Сигналы для обратной связи с UI
    progress = pyqtSignal(int, int)  # (текущий файл, общее количество)
    file_progress = pyqtSignal(int)  # прогресс обработки одного файла
    finished = pyqtSignal()  # завершение работы
    error = pyqtSignal(str)  # ошибка
    file_processing = pyqtSignal(str)  # имя обрабатываемого файла
    status_update = pyqtSignal(str)  # обновление статуса
    
    def __init__(
        self,
        files: List[str],
        filters: List[str],
        zoom_mode: str,
        zoom_static: int,
        zoom_min: int,
        zoom_max: int,
        speed_mode: str,
        speed_static: int,
        speed_min: int,
        speed_max: int,
        overlay_file: Optional[str],
        overlay_pos: str,
        out_dir: str,
        mute_audio: bool,
        output_format: str,
        blur_background: bool,
        strip_metadata: bool,
        codec: str,
        subtitle_settings: Dict,
        auto_crop: bool,
        overlay_audio: Optional[str],
        original_volume: int,
        overlay_volume: int
    ):
        super().__init__()
        
        # Сохранение параметров обработки
        self.files = list(files)
        self.filters = list(filters)
        self.zoom_mode = zoom_mode
        self.zoom_static = zoom_static
        self.zoom_min = zoom_min
        self.zoom_max = zoom_max
        self.speed_mode = speed_mode
        self.speed_static = speed_static
        self.speed_min = speed_min
        self.speed_max = speed_max
        self.overlay_file = overlay_file
        self.overlay_pos = overlay_pos
        self.out_dir = out_dir
        self.mute_audio = mute_audio
        self.output_format = output_format
        self.blur_background = blur_background
        self.strip_metadata = strip_metadata
        self.codec = codec
        self.subtitle_settings = subtitle_settings
        self.auto_crop = auto_crop
        self.overlay_audio = overlay_audio
        
        # Конвертация процентов в десятичные значения
        self.original_volume = original_volume / 100
        self.overlay_volume = overlay_volume / 100
        
        # Флаг работы и результаты
        self._is_running = True
        self.output_paths = []
    
    def pick_zoom(self) -> int:
        """Выбирает значение zoom в зависимости от режима"""
        if self.zoom_mode == 'dynamic' and self.zoom_max >= self.zoom_min:
            try:
                return random.randint(self.zoom_min, self.zoom_max)
            except ValueError:
                return self.zoom_min
        return self.zoom_static
    
    def pick_speed(self) -> int:
        """Выбирает значение скорости в зависимости от режима"""
        if self.speed_mode == 'dynamic' and self.speed_max >= self.speed_min:
            try:
                return random.randint(self.speed_min, self.speed_max)
            except ValueError:
                return self.speed_min
        return self.speed_static
    
    def stop(self):
        """Остановка работы worker'а"""
        self._is_running = False
        print('Worker stop requested.')
    
    def run(self):
        """Основной метод обработки файлов"""
        total_files = len(self.files)
        
        # Проверка наличия файлов
        if total_files == 0:
            self.finished.emit()
            return
        
        # Создание выходной директории
        try:
            os.makedirs(self.out_dir, exist_ok=True)
        except OSError as e:
            self.error.emit(f'Не удалось создать выходную папку: {self.out_dir}\nОшибка: {e}')
            return
        
        # Обработка каждого файла
        for i, in_file_path in enumerate(self.files):
            # Проверка флага остановки
            if not self._is_running:
                print('Worker stopped.')
                break
            
            # Подготовка имен файлов
            base_name = os.path.basename(in_file_path)
            name_part, _ = os.path.splitext(base_name)
            
            # Определение суффикса в зависимости от формата
            suffix = '_reels' if self.output_format != 'Оригинальный' else '_processed'
            out_file_name = f'{name_part}{suffix}.mp4'
            out_file_path = os.path.join(self.out_dir, out_file_name)
            
            # Проверка на совпадение входного и выходного пути
            if os.path.abspath(in_file_path) == os.path.abspath(out_file_path):
                alt_out_file_name = f'{name_part}{suffix}_output.mp4'
                out_file_path = os.path.join(self.out_dir, alt_out_file_name)
                print(f'Warning: Output path is same as input. Saving to: {alt_out_file_name}')
            
            # Уведомление о начале обработки файла
            self.file_processing.emit(base_name)
            self.file_progress.emit(0)
            
            # Инициализация переменных
            srt_path = None
            temp_audio_path = None
            crop_filter = None
            
            try:
                try:
                    # Анализ черных полос если включен auto_crop
                    if self.auto_crop:
                        self.status_update.emit('Анализ черных полос...')
                        crop_filter = detect_crop_dimensions(in_file_path)
                        self.status_update.emit('Обработка...')
                    
                    # Обработка субтитров
                    subtitle_mode = self.subtitle_settings.get('mode')
                    
                    if subtitle_mode == 'whisper':
                        # Генерация субтитров через Whisper
                        temp_dir = self.out_dir
                        temp_audio_path = os.path.join(temp_dir, f'{uuid.uuid4()}.wav')
                        srt_path = os.path.join(temp_dir, f'{uuid.uuid4()}.srt')
                        
                        self.status_update.emit(f"Извлечение аудио из '{base_name}'...")
                        extract_audio(in_file_path, temp_audio_path)
                        
                        self.status_update.emit('Распознавание речи... (может занять много времени)')
                        generate_srt_from_whisper(
                            audio_path=temp_audio_path,
                            srt_path=srt_path,
                            model_name=self.subtitle_settings.get('model'),
                            language=self.subtitle_settings.get('language'),
                            words_per_line=self.subtitle_settings.get('words_per_line')
                        )
                        
                        self.file_processing.emit(base_name)
                        
                    elif subtitle_mode == 'srt_file':
                        # Использование готового SRT файла
                        srt_path = self.subtitle_settings.get('srt_path')
                        if not srt_path or not os.path.exists(srt_path):
                            raise FileNotFoundError(f'Файл субтитров не найден: {srt_path}')
                    
                    # Выбор параметров zoom и speed
                    current_zoom = self.pick_zoom()
                    current_speed = self.pick_speed()
                    
                    # Вызов основной функции обработки
                    process_single(
                        in_path=in_file_path,
                        out_path=out_file_path,
                        filters=self.filters,
                        zoom_p=current_zoom,
                        speed_p=current_speed,
                        overlay_file=self.overlay_file,
                        overlay_pos=self.overlay_pos,
                        output_format=self.output_format,
                        blur_background=self.blur_background,
                        mute_audio=self.mute_audio,
                        strip_metadata=self.strip_metadata,
                        codec=self.codec,
                        srt_path=srt_path,
                        subtitle_style=self.subtitle_settings.get('style', {}),
                        crop_filter=crop_filter,
                        overlay_audio_path=self.overlay_audio,
                        original_volume=self.original_volume,
                        overlay_volume=self.overlay_volume,
                        progress_callback=self.file_progress.emit
                    )
                    
                    # Добавление пути к результатам
                    self.output_paths.append(out_file_path)
                    
                    # Обновление общего прогресса
                    self.progress.emit(i + 1, total_files)
                    
                except Exception as e:
                    # Обработка ошибок
                    error_msg = f"Ошибка при обработке файла '{base_name}':\n{type(e).__name__}: {e}"
                    
                    # Дополнительная информация для ошибок subprocess
                    if isinstance(e, subprocess.CalledProcessError) and e.output:
                        error_msg += f'\n\nFFmpeg output:\n{e.output[-500:]}'
                    
                    print(f'Error in worker thread: {error_msg}')
                    self.error.emit(error_msg)
                    
            finally:
                # Очистка временных файлов
                if temp_audio_path and os.path.exists(temp_audio_path):
                    os.remove(temp_audio_path)
                
                if srt_path and subtitle_mode == 'whisper' and os.path.exists(srt_path):
                    os.remove(srt_path)
        
        # Завершение работы
        if self._is_running:
            print('Worker finished processing all files.')
            self.finished.emit()
        else:
            print('Worker finished due to stop request.')