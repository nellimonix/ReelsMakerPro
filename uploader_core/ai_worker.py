import os
from PyQt5.QtCore import QObject, pyqtSignal, QRunnable
import json


class AIWorkerSignals(QObject):
    """Сигналы для AI Worker"""
    finished = pyqtSignal(dict)  # Сигнал с результатом в виде словаря
    error = pyqtSignal(str)      # Сигнал с ошибкой в виде строки
    status_update = pyqtSignal(str)  # Сигнал статуса выполнения


class AIWorker(QRunnable):
    """Воркер для обработки видео с помощью AI"""
    
    def __init__(self, video_path):
        super().__init__()
        self.video_path = video_path
        self.signals = AIWorkerSignals()
    
    def run(self):
        """Основная функция выполнения AI обработки"""
        try:
            # Импортируем необходимые библиотеки
            import g4f
            import whisper
            
            # Проверяем существование видеофайла
            if not os.path.exists(self.video_path):
                raise FileNotFoundError(f'Видеофайл не найден: {self.video_path}')
            
            # Загружаем модель Whisper для распознавания речи
            model = whisper.load_model('base')
            
            # Транскрибируем видео (извлекаем текст из речи)
            result = model.transcribe(self.video_path, fp16=False)
            transcription = result['text']
            
            # Проверяем, что удалось получить текст
            if not transcription.strip():
                raise ValueError('Не удалось получить текст из видео. Возможно, в нем нет речи.')
            
            # Формируем промпт для AI
            prompt = (
                f"На основе следующей расшифровки видео, пожалуйста, создай краткий, цепляющий "
                f"заголовок (до 100 символов), подробное описание (2-3 абзаца) и 10-15 релевантных "
                f"тегов через запятую. Ответ дай в формате JSON с ключами 'title', 'description' и 'tags'.\n\n"
                f'Расшифровка: "{transcription}"'
            )
            
            # Отправляем запрос к AI
            response = g4f.ChatCompletion.create(
                model=g4f.models.default,
                messages=[{
                    'role': 'user',
                    'content': prompt
                }]
            )
            
            # Извлекаем JSON из ответа AI
            json_response_str = response[response.find('{'):response.rfind('}') + 1]
            
            if not json_response_str:
                raise ValueError('Не удалось извлечь JSON из ответа AI.')
            
            # Парсим JSON ответ
            metadata = json.loads(json_response_str)
            
            # Отправляем сигнал об успешном завершении
            self.signals.finished.emit(metadata)
            
        except Exception as e:
            # Отправляем сигнал об ошибке
            self.signals.error.emit(str(e))