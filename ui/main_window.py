import os
import sys
import random
import tempfile
import uuid
import shutil
import logging

from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QThread
from PyQt5.QtGui import QFontMetrics, QIcon, QPixmap
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QAbstractItemView, QFileDialog, QSpinBox, QLineEdit,
    QMessageBox, QProgressBar, QComboBox, QGroupBox, QRadioButton,
    QButtonGroup, QCheckBox, QSplitter, QListWidgetItem, QTabWidget,
    QMenu, QFrame, QStackedWidget, QInputDialog, QPlainTextEdit,
    QSlider, QApplication
)

import qtawesome as qta
from workers.worker import Worker
from utils.file_utils import is_video_file, find_videos_in_folder
from utils.constants import (
    FILTERS, OVERLAY_POSITIONS, REELS_FORMAT_NAME, OUTPUT_FORMATS,
    CODECS, WHISPER_MODELS, WHISPER_LANGUAGES, APP_NAME, APP_VERSION
)
from utils.ffmpeg_utils import generate_preview, get_video_duration, detect_crop_dimensions
from utils.youtube_utils import download_video
from uploader_ui.uploader_widget import UploaderWidget
from utils.path_utils import resource_path


class YoutubeDownloader(QThread):
    finished_signal = pyqtSignal(str, str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, url, temp_dir, crop_bars):
        super().__init__()
        self.url = url
        self.temp_dir = temp_dir
        self.crop_bars = crop_bars
        self.temp_file_path = ''
        self.cropped_file_path = ''
    
    def run(self):
        try:
            temp_filename = f'yt_{uuid.uuid4()}.mp4'
            self.temp_file_path = os.path.join(self.temp_dir, temp_filename)
            
            download_video(self.url, self.temp_file_path)
            
            if not os.path.exists(self.temp_file_path):
                raise IOError(f'Файл не был создан после скачивания: {self.temp_file_path}')
            
            final_path = self.temp_file_path
            self.finished_signal.emit(final_path, self.url)
            
        except Exception as e:
            self.error_signal.emit(str(e))


class PreviewWorker(QThread):
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)
    
    def __init__(self, params):
        super().__init__()
        self.params = params
    
    def run(self):
        try:
            generate_preview(**self.params)
            self.finished_signal.emit(self.params['out_path'])
        except Exception as e:
            self.error_signal.emit(str(e))


class DropListWidget(QListWidget):
    files_dropped = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(False)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setContextMenuPolicy(Qt.CustomContextMenu)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            added_files = False
            
            for url in event.mimeData().urls():
                fp = url.toLocalFile()
                
                if os.path.isdir(fp):
                    vids = find_videos_in_folder(fp)
                    for v in vids:
                        if is_video_file(v) and not self.is_already_added(v):
                            it = QListWidgetItem(v)
                            it.setData(Qt.UserRole, v)
                            self.addItem(it)
                            added_files = True
                elif is_video_file(fp) or fp.lower().endswith('.gif'):
                    if not self.is_already_added(fp):
                        it = QListWidgetItem(fp)
                        it.setData(Qt.UserRole, fp)
                        self.addItem(it)
                        added_files = True
            
            if added_files:
                self.files_dropped.emit()
        else:
            event.ignore()
    
    def is_already_added(self, file_path):
        for i in range(self.count()):
            if self.item(i).data(Qt.UserRole) == file_path:
                return True
        return False


class ProcessingWidgetContent(QWidget):
    video_processed = pyqtSignal(str)
    
    def __init__(self, parent_window):
        super().__init__(parent_window)
        self.parent_window = parent_window
        self.downloader_thread = None
        self.preview_thread = None
        self.processing_thread = None
        self.last_output_path = None
        self.init_ui()
    
    def init_ui(self):
        # Основной layout
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Сплиттер для разделения левой и правой панели
        main_splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(main_splitter)
        
        # Левая панель
        left_widget = QWidget()
        self.left_panel = QVBoxLayout(left_widget)
        self.left_panel.setSpacing(10)
        
        # Правая панель
        right_widget = QWidget()
        self.right_panel = QVBoxLayout(right_widget)
        self.right_panel.setSpacing(10)
        
        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_widget)
        main_splitter.setSizes([350, 750])
        
        # Кнопки добавления файлов
        add_buttons_layout = QHBoxLayout()
        btn_add = QPushButton('Добавить видео/GIF')
        btn_folder = QPushButton('Добавить папку')
        btn_clear = QPushButton('Очистить список')
        
        add_buttons_layout.addWidget(btn_add)
        add_buttons_layout.addWidget(btn_folder)
        add_buttons_layout.addWidget(btn_clear)
        self.left_panel.addLayout(add_buttons_layout)
        
        # Левый сплиттер для видео списка и YouTube блока
        left_splitter = QSplitter(Qt.Vertical)
        
        # Контейнер для списка видео
        top_left_container = QWidget()
        top_left_layout = QVBoxLayout(top_left_container)
        top_left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Список видео с drag&drop
        self.video_list_widget = DropListWidget(parent=self)
        self.video_list_widget.customContextMenuRequested.connect(self.on_list_menu)
        top_left_layout.addWidget(self.video_list_widget)
        
        # Подсказка для drag&drop
        dnd_label = QLabel('Перетащите файлы или папки сюда')
        dnd_label.setAlignment(Qt.AlignCenter)
        dnd_label.setStyleSheet('color: gray; font-style: italic;')
        top_left_layout.addWidget(dnd_label)
        
        left_splitter.addWidget(top_left_container)
        
        # YouTube группа
        yt_group = QGroupBox('Альтернативный источник')
        yt_layout = QVBoxLayout(yt_group)
        yt_layout.addWidget(QLabel('Ссылка на YouTube видео:'))
        
        self.yt_url_input = QLineEdit()
        self.yt_url_input.setPlaceholderText('https://www.youtube.com/watch?v=...')
        yt_layout.addWidget(self.yt_url_input)
        
        self.yt_add_button = QPushButton('Скачать и добавить в список')
        yt_layout.addWidget(self.yt_add_button)
        yt_layout.addStretch()
        
        left_splitter.addWidget(yt_group)
        left_splitter.setSizes([400, 150])
        
        self.left_panel.addWidget(left_splitter)
        
        # Вкладки настроек
        tab_widget = QTabWidget()
        self.right_panel.addWidget(tab_widget)
        
        # Создание вкладок
        main_tab = QWidget()
        transform_tab = QWidget()
        effects_tab = QWidget()
        audio_tab = QWidget()
        
        tab_widget.addTab(main_tab, 'Меню')
        tab_widget.addTab(transform_tab, 'Трансформация')
        tab_widget.addTab(effects_tab, 'Наложение')
        tab_widget.addTab(audio_tab, 'Аудио')
        
        # Layouts для вкладок
        main_tab_layout = QVBoxLayout(main_tab)
        transform_tab_layout = QVBoxLayout(transform_tab)
        effects_tab_layout = QVBoxLayout(effects_tab)
        audio_tab_layout = QVBoxLayout(audio_tab)
        
        # === ГЛАВНАЯ ВКЛАДКА ===
        
        # Группа формата вывода
        self.output_format_group = QGroupBox('Формат и кодирование')
        ofg_layout = QVBoxLayout(self.output_format_group)
        
        ofg_layout.addWidget(QLabel('Формат вывода:'))
        self.output_format_combo = QComboBox()
        self.output_format_combo.addItems(OUTPUT_FORMATS)
        self.output_format_combo.currentTextChanged.connect(self.on_output_format_changed)
        ofg_layout.addWidget(self.output_format_combo)
        
        self.blur_background_checkbox = QCheckBox('Размыть фон')
        self.blur_background_checkbox.setToolTip('Заполняет черные полосы размытой версией видео (только для Reels)')
        self.blur_background_checkbox.setEnabled(False)
        ofg_layout.addWidget(self.blur_background_checkbox)
        
        ofg_layout.addWidget(QLabel('Видеокодек:'))
        self.codec_combo = QComboBox()
        self.codec_combo.addItems(CODECS.keys())
        self.codec_combo.setToolTip('Аппаратные кодеки (NVIDIA, Intel, AMD) могут значительно ускорить обработку')
        ofg_layout.addWidget(self.codec_combo)
        
        main_tab_layout.addWidget(self.output_format_group)
        
        # Группа предпросмотра
        preview_group = QGroupBox('Предпросмотр')
        preview_layout = QVBoxLayout(preview_group)
        
        self.preview_label = QLabel("Выберите видео и нажмите 'Обновить'")
        self.preview_label.setObjectName('previewLabel')
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumHeight(220)
        preview_layout.addWidget(self.preview_label)
        
        self.preview_button = QPushButton('Обновить предпросмотр')
        preview_layout.addWidget(self.preview_button)
        
        main_tab_layout.addWidget(preview_group)
        main_tab_layout.addStretch()
        
        # === ВКЛАДКА ТРАНСФОРМАЦИИ ===
        
        # Группа обрезки
        self.crop_group = QGroupBox('Обрезка')
        crop_layout = QVBoxLayout(self.crop_group)
        
        self.auto_crop_checkbox = QCheckBox('Обрезать черные полосы (интеллектуально)')
        self.auto_crop_checkbox.setToolTip('Автоматически определяет и обрезает киношные черные полосы в видео')
        crop_layout.addWidget(self.auto_crop_checkbox)
        
        transform_tab_layout.addWidget(self.crop_group)
        
        # Группа фильтров
        self.filter_group = QGroupBox('Фильтры')
        f_lay = QVBoxLayout(self.filter_group)
        
        self.filter_list = QListWidget()
        self.filter_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        for fn in FILTERS:
            self.filter_list.addItem(fn)
        self.filter_list.setFixedHeight(150)
        f_lay.addWidget(self.filter_list)
        
        transform_tab_layout.addWidget(self.filter_group)
        
        # Группа Zoom
        self.zoom_group = QGroupBox('Zoom (приближение)')
        zg_lay = QVBoxLayout(self.zoom_group)
        
        # Радио кнопки для режима zoom
        z_mode = QHBoxLayout()
        self.zoom_static_radio = QRadioButton('Статическое (%):')
        self.zoom_dynamic_radio = QRadioButton('Диапазон (%):')
        self.zoom_static_radio.setChecked(True)
        
        self.zoom_button_group = QButtonGroup()
        self.zoom_button_group.addButton(self.zoom_static_radio)
        self.zoom_button_group.addButton(self.zoom_dynamic_radio)
        self.zoom_button_group.buttonClicked.connect(self.on_zoom_mode_changed)
        
        z_mode.addWidget(self.zoom_static_radio)
        z_mode.addWidget(self.zoom_dynamic_radio)
        zg_lay.addLayout(z_mode)
        
        # Статический zoom
        self.zoom_static_widget = QWidget()
        zsw_lay = QHBoxLayout(self.zoom_static_widget)
        zsw_lay.setContentsMargins(0, 0, 0, 0)
        
        self.zoom_static_spin = QSpinBox()
        self.zoom_static_spin.setRange(50, 300)
        self.zoom_static_spin.setValue(100)
        self.zoom_static_spin.setFixedWidth(80)
        zsw_lay.addWidget(self.zoom_static_spin)
        zsw_lay.addStretch()
        
        zg_lay.addWidget(self.zoom_static_widget)
        
        # Динамический zoom
        self.zoom_dynamic_widget = QWidget()
        zdd_lay = QHBoxLayout(self.zoom_dynamic_widget)
        zdd_lay.setContentsMargins(0, 0, 0, 0)
        
        self.zoom_min_spin = QSpinBox()
        self.zoom_min_spin.setRange(50, 300)
        self.zoom_min_spin.setValue(80)
        
        self.zoom_max_spin = QSpinBox()
        self.zoom_max_spin.setRange(50, 300)
        self.zoom_max_spin.setValue(120)
        
        zdd_lay.addWidget(QLabel('Мин:'))
        zdd_lay.addWidget(self.zoom_min_spin)
        zdd_lay.addWidget(QLabel('Макс:'))
        zdd_lay.addWidget(self.zoom_max_spin)
        zdd_lay.addStretch()
        
        zg_lay.addWidget(self.zoom_dynamic_widget)
        self.zoom_dynamic_widget.setVisible(False)
        
        transform_tab_layout.addWidget(self.zoom_group)
        
        # Группа скорости
        self.speed_group = QGroupBox('Скорость')
        sp_lay = QVBoxLayout(self.speed_group)
        
        # Радио кнопки для режима скорости
        sp_mode = QHBoxLayout()
        self.speed_static_radio = QRadioButton('Статическое (%):')
        self.speed_dynamic_radio = QRadioButton('Диапазон (%):')
        self.speed_static_radio.setChecked(True)
        
        self.speed_button_group = QButtonGroup()
        self.speed_button_group.addButton(self.speed_static_radio)
        self.speed_button_group.addButton(self.speed_dynamic_radio)
        self.speed_button_group.buttonClicked.connect(self.on_speed_mode_changed)
        
        sp_mode.addWidget(self.speed_static_radio)
        sp_mode.addWidget(self.speed_dynamic_radio)
        sp_lay.addLayout(sp_mode)
        
        # Статическая скорость
        self.speed_static_widget = QWidget()
        ssw2 = QHBoxLayout(self.speed_static_widget)
        ssw2.setContentsMargins(0, 0, 0, 0)
        
        self.speed_static_spin = QSpinBox()
        self.speed_static_spin.setRange(50, 200)
        self.speed_static_spin.setValue(100)
        self.speed_static_spin.setFixedWidth(80)
        ssw2.addWidget(self.speed_static_spin)
        ssw2.addStretch()
        
        sp_lay.addWidget(self.speed_static_widget)
        
        # Динамическая скорость
        self.speed_dynamic_widget = QWidget()
        sdy2 = QHBoxLayout(self.speed_dynamic_widget)
        sdy2.setContentsMargins(0, 0, 0, 0)
        
        self.speed_min_spin = QSpinBox()
        self.speed_min_spin.setRange(50, 200)
        self.speed_min_spin.setValue(90)
        
        self.speed_max_spin = QSpinBox()
        self.speed_max_spin.setRange(50, 200)
        self.speed_max_spin.setValue(110)
        
        sdy2.addWidget(QLabel('Мин:'))
        sdy2.addWidget(self.speed_min_spin)
        sdy2.addWidget(QLabel('Макс:'))
        sdy2.addWidget(self.speed_max_spin)
        sdy2.addStretch()
        
        sp_lay.addWidget(self.speed_dynamic_widget)
        self.speed_dynamic_widget.setVisible(False)
        
        transform_tab_layout.addWidget(self.speed_group)
        transform_tab_layout.addStretch()
        
        # === ВКЛАДКА НАЛОЖЕНИЙ ===
        
        # Группа наложения баннера
        self.overlay_group = QGroupBox('Наложение (баннер)')
        ov_lay = QVBoxLayout(self.overlay_group)
        
        # Строка с файлом
        row_ol = QHBoxLayout()
        self.overlay_path = QLineEdit()
        self.overlay_path.setPlaceholderText('Путь к файлу PNG, JPG, GIF...')
        
        btn_ol = QPushButton('Обзор...')
        btn_clear_ol = QPushButton('X')
        btn_clear_ol.setFixedWidth(30)
        btn_clear_ol.setToolTip('Очистить поле наложения')
        
        row_ol.addWidget(QLabel('Файл:'))
        row_ol.addWidget(self.overlay_path)
        row_ol.addWidget(btn_ol)
        row_ol.addWidget(btn_clear_ol)
        ov_lay.addLayout(row_ol)
        
        # Строка с позицией
        row_pos = QHBoxLayout()
        row_pos.addWidget(QLabel('Расположение:'))
        
        self.overlay_pos_combo = QComboBox()
        for pos in OVERLAY_POSITIONS:
            self.overlay_pos_combo.addItem(pos)
        self.overlay_pos_combo.setCurrentText('Середина-Центр')
        
        row_pos.addWidget(self.overlay_pos_combo)
        row_pos.addStretch()
        ov_lay.addLayout(row_pos)
        
        effects_tab_layout.addWidget(self.overlay_group)
        
        # Группа субтитров
        self.subs_group = QGroupBox('Субтитры')
        subs_main_layout = QVBoxLayout(self.subs_group)
        
        # Режим субтитров
        self.subs_mode_group = QButtonGroup()
        subs_mode_layout = QHBoxLayout()
        
        self.subs_off_radio = QRadioButton('Выключены')
        self.subs_from_file_radio = QRadioButton('Из файла SRT')
        self.subs_generate_radio = QRadioButton('Сгенерировать (Whisper)')
        self.subs_off_radio.setChecked(True)
        
        self.subs_mode_group.addButton(self.subs_off_radio)
        self.subs_mode_group.addButton(self.subs_from_file_radio)
        self.subs_mode_group.addButton(self.subs_generate_radio)
        
        subs_mode_layout.addWidget(self.subs_off_radio)
        subs_mode_layout.addWidget(self.subs_from_file_radio)
        subs_mode_layout.addWidget(self.subs_generate_radio)
        subs_main_layout.addLayout(subs_mode_layout)
        
        # Виджет для файла SRT
        self.subs_file_widget = QWidget()
        subs_file_layout = QHBoxLayout(self.subs_file_widget)
        subs_file_layout.setContentsMargins(0, 5, 0, 0)
        
        self.subs_srt_path = QLineEdit()
        self.subs_srt_path.setPlaceholderText('Путь к файлу .srt')
        btn_browse_srt = QPushButton('Обзор...')
        
        subs_file_layout.addWidget(QLabel('Файл:'))
        subs_file_layout.addWidget(self.subs_srt_path)
        subs_file_layout.addWidget(btn_browse_srt)
        
        subs_main_layout.addWidget(self.subs_file_widget)
        
        # Виджет для Whisper настроек
        self.subs_whisper_widget = QWidget()
        subs_whisper_layout = QVBoxLayout(self.subs_whisper_widget)
        subs_whisper_layout.setContentsMargins(0, 5, 0, 5)
        subs_whisper_layout.setSpacing(10)
        
        # Модель
        whisper_row1 = QHBoxLayout()
        whisper_row1.addWidget(QLabel('Модель:'))
        self.subs_model_combo = QComboBox()
        self.subs_model_combo.addItems(WHISPER_MODELS)
        self.subs_model_combo.setCurrentText('base')
        whisper_row1.addWidget(self.subs_model_combo)
        subs_whisper_layout.addLayout(whisper_row1)
        
        # Язык
        whisper_row2 = QHBoxLayout()
        whisper_row2.addWidget(QLabel('Язык:'))
        self.subs_lang_combo = QComboBox()
        self.subs_lang_combo.addItems(WHISPER_LANGUAGES)
        self.subs_lang_combo.setCurrentText('Russian')
        whisper_row2.addWidget(self.subs_lang_combo)
        subs_whisper_layout.addLayout(whisper_row2)
        
        # Слова в строке
        whisper_row3 = QHBoxLayout()
        whisper_row3.addWidget(QLabel('Слов в строке:'))
        self.subs_words_spin = QSpinBox()
        self.subs_words_spin.setRange(1, 10)
        self.subs_words_spin.setValue(4)
        whisper_row3.addWidget(self.subs_words_spin)
        whisper_row3.addStretch()
        subs_whisper_layout.addLayout(whisper_row3)
        
        subs_main_layout.addWidget(self.subs_whisper_widget)
        
        # Общие настройки стиля
        common_style_layout = QHBoxLayout()
        common_style_layout.addWidget(QLabel('Размер (pt):'))
        self.subs_size_spin = QSpinBox()
        self.subs_size_spin.setRange(10, 100)
        self.subs_size_spin.setValue(36)
        common_style_layout.addWidget(self.subs_size_spin)
        common_style_layout.addStretch(1)
        subs_main_layout.addLayout(common_style_layout)
        
        effects_tab_layout.addWidget(self.subs_group)
        effects_tab_layout.addStretch()
        
        # === ВКЛАДКА АУДИО ===
        
        # Группа управления звуком
        self.mute_group = QGroupBox('Управление звуком')
        mute_layout = QVBoxLayout(self.mute_group)
        
        self.mute_checkbox = QCheckBox('Удалить оригинальный звук из видео')
        mute_layout.addWidget(self.mute_checkbox)
        
        # Громкость оригинала
        orig_vol_layout = QHBoxLayout()
        self.orig_vol_slider = QSlider(Qt.Horizontal)
        self.orig_vol_slider.setRange(0, 150)
        self.orig_vol_slider.setValue(100)
        
        self.orig_vol_label = QLabel('Громкость оригинала: 100%')
        self.orig_vol_slider.valueChanged.connect(
            lambda v: self.orig_vol_label.setText(f'Громкость оригинала: {v}%')
        )
        self.mute_checkbox.toggled.connect(
            lambda c: self.orig_vol_slider.setDisabled(c)
        )
        
        orig_vol_layout.addWidget(self.orig_vol_label)
        orig_vol_layout.addWidget(self.orig_vol_slider)
        mute_layout.addLayout(orig_vol_layout)
        
        audio_tab_layout.addWidget(self.mute_group)
        
        # Группа наложения аудио
        self.overlay_audio_group = QGroupBox('Наложение аудио')
        overlay_audio_layout = QVBoxLayout(self.overlay_audio_group)
        
        # Путь к аудиофайлу
        ol_audio_path_layout = QHBoxLayout()
        self.overlay_audio_path_edit = QLineEdit()
        self.overlay_audio_path_edit.setPlaceholderText('Путь к аудиофайлу (MP3, WAV...)')
        
        browse_ol_audio_btn = QPushButton('Обзор...')
        clear_ol_audio_btn = QPushButton('X')
        clear_ol_audio_btn.setFixedWidth(30)
        
        ol_audio_path_layout.addWidget(QLabel('Файл:'))
        ol_audio_path_layout.addWidget(self.overlay_audio_path_edit)
        ol_audio_path_layout.addWidget(browse_ol_audio_btn)
        ol_audio_path_layout.addWidget(clear_ol_audio_btn)
        overlay_audio_layout.addLayout(ol_audio_path_layout)
        
        # Громкость наложения
        over_vol_layout = QHBoxLayout()
        self.over_vol_slider = QSlider(Qt.Horizontal)
        self.over_vol_slider.setRange(0, 150)
        self.over_vol_slider.setValue(100)
        
        self.over_vol_label = QLabel('Громкость наложения: 100%')
        self.over_vol_slider.valueChanged.connect(
            lambda v: self.over_vol_label.setText(f'Громкость наложения: {v}%')
        )
        
        over_vol_layout.addWidget(self.over_vol_label)
        over_vol_layout.addWidget(self.over_vol_slider)
        overlay_audio_layout.addLayout(over_vol_layout)
        
        # Управление активностью слайдера
        self.overlay_audio_path_edit.textChanged.connect(
            lambda t: self.over_vol_slider.setDisabled(not t)
        )
        self.over_vol_slider.setDisabled(True)
        
        audio_tab_layout.addWidget(self.overlay_audio_group)
        audio_tab_layout.addStretch()
        
        # === НИЖНИЕ ЭЛЕМЕНТЫ УПРАВЛЕНИЯ ===
        
        # Кнопка обработки
        self.process_button = QPushButton('🚀 Обработать')
        self.process_button.setObjectName('process_button')
        self.process_button.setFixedHeight(40)
        
        # Прогресс бар и лейблы
        self.progress_label = QLabel('')
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        
        self.status_label = QLabel('')
        self.status_label.setStyleSheet('color: gray;')
        
        # Layout для прогресса
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar, 1)
        
        # Watermark label
        self.watermark_label = QLabel()
        self.watermark_label.setText('Декомпиляцию последней версии программы выполнил llimonix.<br>Мой Telegram канал: '
        '<a href="https://t.me/findllimonix" style="color:#df4f44; text-decoration:none;">@findllimonix</a>')
        self.watermark_label.setTextFormat(Qt.RichText)
        self.watermark_label.setOpenExternalLinks(True)
        self.watermark_label.setAlignment(Qt.AlignCenter)
        
        # Нижний layout
        bottom_controls_layout = QVBoxLayout()
        bottom_controls_layout.addWidget(self.process_button)
        bottom_controls_layout.addLayout(progress_layout)
        bottom_controls_layout.addWidget(self.status_label)
        bottom_controls_layout.addWidget(self.watermark_label)
        
        self.right_panel.addLayout(bottom_controls_layout)
        
        # === ПОДКЛЮЧЕНИЕ СИГНАЛОВ ===
        
        # Кнопки
        btn_add.clicked.connect(self.on_add_files)
        btn_folder.clicked.connect(self.on_add_folder)
        btn_clear.clicked.connect(self.on_clear_list)
        btn_ol.clicked.connect(self.on_select_overlay)
        btn_clear_ol.clicked.connect(lambda: self.overlay_path.clear())
        self.yt_add_button.clicked.connect(self.on_add_from_youtube)
        self.preview_button.clicked.connect(self.on_update_preview)
        btn_browse_srt.clicked.connect(self.on_browse_srt)
        self.subs_mode_group.buttonClicked.connect(self.on_subs_mode_changed)
        browse_ol_audio_btn.clicked.connect(self.on_browse_overlay_audio)
        clear_ol_audio_btn.clicked.connect(self.overlay_audio_path_edit.clear)
        self.process_button.clicked.connect(self.start_processing)
        
        # Инициализация состояний
        self.on_subs_mode_changed()
        self.on_output_format_changed(self.output_format_combo.currentText())
        self.on_zoom_mode_changed()
        self.on_speed_mode_changed()
        
        # Drag & Drop
        self.video_list_widget.files_dropped.connect(self.refresh_video_list_display)
    
    def on_subs_mode_changed(self):
        is_from_file = self.subs_from_file_radio.isChecked()
        is_generate = self.subs_generate_radio.isChecked()
        
        self.subs_file_widget.setVisible(is_from_file)
        self.subs_whisper_widget.setVisible(is_generate)
    
    def on_browse_srt(self):
        fs, _ = QFileDialog.getOpenFileName(
            self, 'Выберите файл субтитров', '',
            'SRT Files (*.srt)'
        )
        if fs:
            self.subs_srt_path.setText(fs)
    
    def on_browse_overlay_audio(self):
        fs, _ = QFileDialog.getOpenFileName(
            self, 'Выберите аудиофайл', '',
            'Audio Files (*.mp3 *.wav *.m4a *.aac)'
        )
        if fs:
            self.overlay_audio_path_edit.setText(fs)
    
    def on_add_from_youtube(self):
        url = self.yt_url_input.text().strip()
        if not url:
            QMessageBox.warning(self, 'Нет ссылки', 'Пожалуйста, вставьте ссылку на YouTube видео.')
            return
        
        self.set_controls_enabled(False)
        self.status_label.setText(f'Скачивание видео: {url[:50]}...')
        
        self.downloader_thread = YoutubeDownloader(url, self.parent_window.temp_dir, False)
        self.downloader_thread.finished_signal.connect(self.on_youtube_download_finished)
        self.downloader_thread.error_signal.connect(self.on_youtube_download_error)
        self.downloader_thread.start()
    
    def on_youtube_download_finished(self, file_path, original_url):
        self.status_label.setText('Видео успешно скачано!')
        self.yt_url_input.clear()
        self.set_controls_enabled(True)
        
        if not self.video_list_widget.is_already_added(file_path):
            self.parent_window.temp_files.append(file_path)
            item_text = f'[YT] {os.path.basename(file_path)}'
            it = QListWidgetItem(item_text)
            it.setData(Qt.UserRole, file_path)
            self.video_list_widget.addItem(it)
            self.refresh_video_list_display()
    
    def on_youtube_download_error(self, error_msg):
        self.status_label.setText('Ошибка скачивания.')
        QMessageBox.critical(self, 'Ошибка скачивания', f'Не удалось скачать видео:\n\n{error_msg}')
        self.set_controls_enabled(True)
    
    def on_update_preview(self):
        selected_items = self.video_list_widget.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, 'Видео не выбрано', 'Пожалуйста, выберите видео из списка для предпросмотра.')
            return
        
        in_path = selected_items[0].data(Qt.UserRole)
        temp_preview_path = os.path.join(
            self.parent_window.temp_dir,
            f'preview_{uuid.uuid4()}.png'
        )
        
        crop_filter = None
        if self.auto_crop_checkbox.isChecked():
            self.preview_label.setText('Анализ кадра для обрезки...')
            QApplication.processEvents()
            try:
                crop_filter = detect_crop_dimensions(in_path)
            except Exception as e:
                self.on_preview_error(f'Не удалось определить размеры обрезки: {e}')
                return
        
        params = {
            'in_path': in_path,
            'out_path': temp_preview_path,
            'filters': [item.text() for item in self.filter_list.selectedItems()],
            'zoom_p': self.zoom_static_spin.value(),
            'overlay_file': self.overlay_path.text().strip() or None,
            'overlay_pos': self.overlay_pos_combo.currentText(),
            'output_format': self.output_format_combo.currentText(),
            'blur_background': self.blur_background_checkbox.isChecked(),
            'crop_filter': crop_filter
        }
        
        self.set_controls_enabled(False)
        self.preview_label.setText('Генерация предпросмотра...')
        
        self.parent_window.temp_files.append(temp_preview_path)
        self.preview_thread = PreviewWorker(params)
        self.preview_thread.finished_signal.connect(self.on_preview_finished)
        self.preview_thread.error_signal.connect(self.on_preview_error)
        self.preview_thread.start()
    
    def on_preview_finished(self, image_path):
        if os.path.exists(image_path):
            pixmap = QPixmap(image_path)
            self.preview_label.setPixmap(
                pixmap.scaled(
                    self.preview_label.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )
            )
        else:
            self.preview_label.setText('Ошибка: файл предпросмотра не найден')
        
        self.set_controls_enabled(True)
    
    def on_preview_error(self, error_msg):
        self.preview_label.setText('Ошибка генерации предпросмотра')
        QMessageBox.critical(self, 'Ошибка предпросмотра', f'Не удалось создать предпросмотр:\n\n{error_msg}')
        self.set_controls_enabled(True)
    
    def set_controls_enabled(self, enabled):
        self.process_button.setEnabled(enabled)
        self.yt_add_button.setEnabled(enabled)
        self.preview_button.setEnabled(enabled)
        self.video_list_widget.setEnabled(enabled)
    
    def on_output_format_changed(self, format_text):
        is_reels = format_text == REELS_FORMAT_NAME
        self.blur_background_checkbox.setEnabled(is_reels)
        if not is_reels:
            self.blur_background_checkbox.setChecked(False)
    
    def on_list_menu(self, pos: QPoint):
        menu = QMenu()
        act_del = menu.addAction('Удалить выделенное')
        act_clear = menu.addAction('Очистить список')
        
        chosen = menu.exec_(self.video_list_widget.viewport().mapToGlobal(pos))
        
        if chosen == act_del:
            selected_items = self.video_list_widget.selectedItems()
            if selected_items:
                for it in reversed(selected_items):
                    self.video_list_widget.takeItem(self.video_list_widget.row(it))
                self.refresh_video_list_display()
        elif chosen == act_clear:
            self.on_clear_list()
    
    def on_clear_list(self):
        self.video_list_widget.clear()
        self.refresh_video_list_display()
    
    def on_select_overlay(self):
        overlay_filter = 'Файлы наложения (*.png *.jpg *.jpeg *.bmp *.gif);;Все файлы (*)'
        fs, _ = QFileDialog.getOpenFileNames(
            self, 'Выберите файл для наложения (PNG, JPG, GIF)', '',
            overlay_filter
        )
        if fs:
            self.overlay_path.setText(fs[0])
    
    def on_add_files(self):
        file_filter = 'Видео и GIF (*.mp4 *.mov *.avi *.mkv *.flv *.wmv *.gif);;Все файлы (*)'
        fs, _ = QFileDialog.getOpenFileNames(
            self, 'Выберите видео или GIF', '', file_filter
        )
        if not fs:
            return
        
        added = False
        for f in fs:
            if (is_video_file(f) or f.lower().endswith('.gif')) and not self.video_list_widget.is_already_added(f):
                it = QListWidgetItem(f)
                it.setData(Qt.UserRole, f)
                self.video_list_widget.addItem(it)
                added = True
        
        if added:
            self.refresh_video_list_display()
    
    def on_add_folder(self):
        fol = QFileDialog.getExistingDirectory(self, 'Выберите папку', '')
        if not fol:
            return
        
        vs = find_videos_in_folder(fol, include_gifs=True)
        added = False
        for v in vs:
            if not self.video_list_widget.is_already_added(v):
                it = QListWidgetItem(v)
                it.setData(Qt.UserRole, v)
                self.video_list_widget.addItem(it)
                added = True
        
        if added:
            self.refresh_video_list_display()
    
    def refresh_video_list_display(self):
        for i in range(self.video_list_widget.count()):
            it = self.video_list_widget.item(i)
            if not it.text().startswith('[YT]'):
                f = it.data(Qt.UserRole)
                base_name = os.path.basename(f)
                it.setText(f'{i + 1}. {base_name}')
    
    def on_zoom_mode_changed(self):
        is_dynamic = self.zoom_dynamic_radio.isChecked()
        self.zoom_static_widget.setVisible(not is_dynamic)
        self.zoom_dynamic_widget.setVisible(is_dynamic)
    
    def on_speed_mode_changed(self):
        is_dynamic = self.speed_dynamic_radio.isChecked()
        self.speed_static_widget.setVisible(not is_dynamic)
        self.speed_dynamic_widget.setVisible(is_dynamic)
    
    def start_processing(self):
        video_files = [
            self.video_list_widget.item(i).data(Qt.UserRole)
            for i in range(self.video_list_widget.count())
        ]
        
        if not video_files:
            QMessageBox.warning(self, 'Нет файлов', 'Добавьте хотя бы один видео или GIF файл.')
            return
        
        out_dir = QFileDialog.getExistingDirectory(self, 'Выберите папку для сохранения результатов')
        if not out_dir:
            return
        
        # Настройки субтитров
        subtitle_settings = {'mode': 'none'}
        
        if self.subs_from_file_radio.isChecked():
            subtitle_settings['mode'] = 'srt_file'
            subtitle_settings['srt_path'] = self.subs_srt_path.text()
        elif self.subs_generate_radio.isChecked():
            subtitle_settings['mode'] = 'whisper'
            subtitle_settings['model'] = self.subs_model_combo.currentText()
            subtitle_settings['language'] = self.subs_lang_combo.currentText()
            subtitle_settings['words_per_line'] = self.subs_words_spin.value()
        
        subtitle_settings['style'] = {'font_size': self.subs_size_spin.value()}
        
        # Создание worker'а
        self.processing_thread = Worker(
            files=video_files,
            filters=[item.text() for item in self.filter_list.selectedItems()],
            zoom_mode='dynamic' if self.zoom_dynamic_radio.isChecked() else 'static',
            zoom_static=self.zoom_static_spin.value(),
            zoom_min=self.zoom_min_spin.value(),
            zoom_max=self.zoom_max_spin.value(),
            speed_mode='dynamic' if self.speed_dynamic_radio.isChecked() else 'static',
            speed_static=self.speed_static_spin.value(),
            speed_min=self.speed_min_spin.value(),
            speed_max=self.speed_max_spin.value(),
            overlay_file=self.overlay_path.text().strip() or None,
            overlay_pos=self.overlay_pos_combo.currentText(),
            out_dir=out_dir,
            mute_audio=self.mute_checkbox.isChecked(),
            output_format=self.output_format_combo.currentText(),
            blur_background=self.blur_background_checkbox.isChecked(),
            strip_metadata=self.parent_window.settings_widget.strip_meta_checkbox.isChecked(),
            codec=CODECS.get(self.codec_combo.currentText(), 'libx264'),
            subtitle_settings=subtitle_settings,
            auto_crop=self.auto_crop_checkbox.isChecked(),
            overlay_audio=self.overlay_audio_path_edit.text().strip() or None,
            original_volume=self.orig_vol_slider.value(),
            overlay_volume=self.over_vol_slider.value()
        )
        
        # Подключение сигналов
        self.processing_thread.progress.connect(self.on_prog)
        self.processing_thread.file_progress.connect(self.on_file_prog)
        self.processing_thread.finished.connect(self.on_done)
        self.processing_thread.error.connect(self.on_err)
        self.processing_thread.file_processing.connect(self.on_file_processing)
        self.processing_thread.status_update.connect(self.on_status_update)
        
        # Начальное состояние
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat('%p%')
        self.progress_label.setText(f'0 / {len(video_files)}')
        self.status_label.setText('Подготовка...')
        self.set_controls_enabled(False)
        
        self.processing_thread.start()
    
    def on_prog(self, done, total):
        self.progress_label.setText(f'{done} / {total}')
        self.progress_bar.setValue(100)
    
    def on_file_prog(self, percentage):
        self.progress_bar.setValue(percentage)
    
    def on_file_processing(self, fname):
        try:
            fm = QFontMetrics(self.status_label.font())
            elided_text = fm.elidedText(
                f'Обрабатываю: {fname}',
                Qt.ElideMiddle,
                self.status_label.width() - 20
            )
            self.status_label.setText(elided_text)
            self.progress_bar.setValue(0)
        except Exception:
            self.status_label.setText(f'Обрабатываю: ...{fname[-30:]}')
            self.progress_bar.setValue(0)
    
    def on_status_update(self, message: str):
        self.status_label.setText(message)
    
    def on_done(self):
        if self.processing_thread and not self.processing_thread.isRunning():
            output_paths = self.processing_thread.output_paths
            QMessageBox.information(self, 'Готово', 'Обработка успешно завершена!')
            
            if len(output_paths) == 1:
                self.video_processed.emit(output_paths[0])
        
        self.set_controls_enabled(True)
        self.status_label.setText('Готово')
        self.processing_thread = None
    
    def on_err(self, msg):
        QMessageBox.critical(self, 'Ошибка обработки', f'Произошла ошибка:\n\n{msg}')
        self.set_controls_enabled(True)
        self.status_label.setText('Ошибка')
        self.processing_thread = None


class SettingsWidget(QWidget):
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Основные настройки
        main_group = QGroupBox('Основные настройки')
        main_layout = QVBoxLayout(main_group)
        
        # FFmpeg путь
        ffmpeg_layout = QHBoxLayout()
        self.ffmpeg_path_edit = QLineEdit()
        self.ffmpeg_path_edit.setPlaceholderText('Укажите путь к ffmpeg.exe (необязательно)')
        browse_ffmpeg_btn = QPushButton('Выбрать')
        
        ffmpeg_layout.addWidget(QLabel('Путь к FFmpeg:'))
        ffmpeg_layout.addWidget(self.ffmpeg_path_edit)
        ffmpeg_layout.addWidget(browse_ffmpeg_btn)
        main_layout.addLayout(ffmpeg_layout)
        
        # Очистка метаданных
        self.strip_meta_checkbox = QCheckBox('Очистить метаданные при обработке')
        self.strip_meta_checkbox.setChecked(True)
        main_layout.addWidget(self.strip_meta_checkbox)
        
        layout.addWidget(main_group)
        
        # Внешний вид
        style_group = QGroupBox('Внешний вид')
        style_layout = QHBoxLayout(style_group)
        
        self.style_combo = QComboBox()
        self.style_combo.addItems(['Dark [mod by llimonix]', 'Light [mod by llimonix]', 'Dark [Original]', 'Light [Original]'])
        
        style_layout.addWidget(QLabel('Тема оформления:'))
        style_layout.addWidget(self.style_combo)
        style_layout.addStretch()
        
        layout.addWidget(style_group)
        layout.addStretch()
        
        # Подключение сигналов
        browse_ffmpeg_btn.clicked.connect(self.browse_ffmpeg)
    
    def browse_ffmpeg(self):
        path, _ = QFileDialog.getOpenFileName(
            self, 'Выберите ffmpeg.exe', '',
            'Executable Files (*.exe)'
        )
        if path:
            self.ffmpeg_path_edit.setText(path)


class VideoUnicApp(QMainWindow):
    
    def __init__(self):
        super().__init__()
        self.temp_dir = tempfile.mkdtemp(prefix='reels_maker_')
        self.temp_files = []
        self.init_ui()
    
    def init_ui(self):
        self.setWindowTitle(f'{APP_NAME} v{APP_VERSION}')
        self.setGeometry(100, 100, 1200, 850)
        
        # Иконка приложения
        icon_path = resource_path(os.path.join('resources', 'icon.png'))
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        # Центральный виджет
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        
        # Основной layout
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        # Левое меню
        self.left_menu = QFrame()
        self.left_menu.setObjectName('left_menu')
        self.left_menu.setFixedWidth(200)
        
        self.left_menu_layout = QVBoxLayout(self.left_menu)
        self.left_menu_layout.setContentsMargins(0, 0, 0, 0)
        self.left_menu_layout.setSpacing(0)
        
        # Группа кнопок меню
        self.button_group = QButtonGroup()
        self.button_group.setExclusive(True)
        
        # Кнопки меню
        self.processing_btn = QPushButton(qta.icon('fa5s.cogs', color='white', color_active='white'), ' Обработка')
        self.processing_btn.setObjectName('menu_button')
        self.processing_btn.setCheckable(True)
        self.button_group.addButton(self.processing_btn)
        
        self.upload_btn = QPushButton(qta.icon('fa5s.upload', color='white', color_active='white'), ' Загрузка на YouTube')
        self.upload_btn.setObjectName('menu_button')
        self.upload_btn.setCheckable(True)
        self.button_group.addButton(self.upload_btn)
        
        self.settings_btn = QPushButton(qta.icon('fa5s.sliders-h', color='white', color_active='white'), ' Настройки')
        self.settings_btn.setObjectName('menu_button')
        self.settings_btn.setCheckable(True)
        self.button_group.addButton(self.settings_btn)
        
        # Добавление кнопок в layout
        self.left_menu_layout.addWidget(self.processing_btn)
        self.left_menu_layout.addWidget(self.upload_btn)
        self.left_menu_layout.addWidget(self.settings_btn)
        self.left_menu_layout.addStretch()
        
        # Кнопка выхода
        self.exit_btn = QPushButton(qta.icon('fa5s.sign-out-alt', color='white', color_active='white'), ' Выход')
        self.exit_btn.setObjectName('menu_button')
        self.left_menu_layout.addWidget(self.exit_btn)
        
        # Основной контент
        self.main_content = QFrame()
        
        self.main_layout.addWidget(self.left_menu)
        self.main_layout.addWidget(self.main_content)
        
        self.main_content_layout = QVBoxLayout(self.main_content)
        
        # Создание виджетов содержимого
        self.processing_widget = ProcessingWidgetContent(self)
        self.settings_widget = SettingsWidget(self)
        self.uploader_widget = UploaderWidget(self)
        
        # Стек виджетов
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self.processing_widget)
        self.stacked_widget.addWidget(self.uploader_widget)
        self.stacked_widget.addWidget(self.settings_widget)
        
        self.main_content_layout.addWidget(self.stacked_widget)
        
        # Подключение сигналов
        self.processing_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(0))
        self.upload_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(1))
        self.settings_btn.clicked.connect(lambda: self.stacked_widget.setCurrentIndex(2))
        self.exit_btn.clicked.connect(self.close)
        
        # Настройки темы
        self.settings_widget.style_combo.currentTextChanged.connect(self.apply_stylesheet)
        
        # Установка начального состояния
        self.processing_btn.setChecked(True)
        self.apply_stylesheet('Dark [mod by llimonix]')
        
        # Подключение сигнала обработки видео
        self.processing_widget.video_processed.connect(self.prepare_for_upload)
    
    def apply_stylesheet(self, mode):
        mode = mode.lower()
        if mode == 'dark [mod by llimonix]':
            style_filename = 'styles_dark.qss'
        elif mode == 'light [mod by llimonix]':
            style_filename = 'styles_light.qss'
        elif mode == 'dark [original]':
            style_filename = 'original_dark.qss'
        elif mode == 'light [original]':
            style_filename = 'original_light.qss'
        else:
            style_filename = 'styles_dark.qss'

        path = resource_path(os.path.join('resources', style_filename))
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                style = f.read()
                self.setStyleSheet(style)
                if 'light' in style_filename:
                    icon_color = 'black'
                else:
                    icon_color = 'white'
                
                self.processing_btn.setIcon(qta.icon('fa5s.cogs', color=icon_color, color_active='white'))
                self.upload_btn.setIcon(qta.icon('fa5s.upload', color=icon_color, color_active='white'))
                self.settings_btn.setIcon(qta.icon('fa5s.sliders-h', color=icon_color, color_active='white'))
                self.exit_btn.setIcon(qta.icon('fa5s.sign-out-alt', color=icon_color, color_active='white'))
                self.uploader_widget.add_account_btn.setIcon(qta.icon('fa5s.user-plus', color=icon_color, color_active='white'))
                for i in range(self.uploader_widget.tabs.count()):
                    icon = qta.icon('fa5s.user-circle', color=icon_color, color_active='white')
                    self.uploader_widget.tabs.setTabIcon(i, icon)

        except FileNotFoundError:
            print(f'Stylesheet not found at {path}')
            self.setStyleSheet('')
    
    def prepare_for_upload(self, video_path):
        # Получение списка аккаунтов
        accounts = self.uploader_widget.get_account_names()
        if not accounts:
            QMessageBox.warning(self, 'Нет аккаунтов', "Сначала добавьте аккаунт в разделе 'Загрузка на YouTube'.")
            return
        
        # Подтверждение загрузки
        reply = QMessageBox.question(
            self, 'Загрузка видео',
            'Видео успешно обработано. Хотите отправить его на загрузку?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.No:
            return
        
        # Выбор аккаунта
        account_name, ok = QInputDialog.getItem(
            self, 'Выбор аккаунта',
            'Выберите аккаунт для загрузки:',
            accounts, 0, False
        )
        
        if ok and account_name:
            # Переключение на вкладку загрузки
            self.stacked_widget.setCurrentWidget(self.uploader_widget)
            self.upload_btn.setChecked(True)
            
            # Передача видео для загрузки
            self.uploader_widget.receive_video_for_upload(video_path, account_name)
    
    def _cleanup_temp_files(self):
        print('Cleaning up temporary files...')
        
        # Удаление временных файлов
        for f in self.temp_files:
            try:
                if os.path.exists(f):
                    os.remove(f)
            except OSError as e:
                print(f'Error removing temp file {f}: {e}')
        
        self.temp_files.clear()
        
        # Удаление временной директории
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except OSError as e:
            print(f'Error removing temp directory {self.temp_dir}: {e}')
    
    def closeEvent(self, event):
        # Проверка на работающие потоки
        proc_thread = self.processing_widget.processing_thread
        is_running = proc_thread and proc_thread.isRunning()
        
        reply = QMessageBox.Yes
        if is_running:
            reply = QMessageBox.question(
                self, 'Подтверждение',
                'Идет обработка видео. Вы уверены, что хотите выйти?',
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
        
        if reply == QMessageBox.Yes:
            if is_running:
                try:
                    proc_thread.stop()
                    proc_thread.wait(1000)
                except Exception as e:
                    print(f'Error stopping worker thread: {e}')
            
            self._cleanup_temp_files()
            event.accept()
        else:
            event.ignore()