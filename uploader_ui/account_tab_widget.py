from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QLineEdit, QPushButton,
    QLabel, QFormLayout, QPlainTextEdit, QDateTimeEdit, QComboBox, QCheckBox,
    QTableWidget, QHeaderView, QAbstractItemView, QTableWidgetItem,
    QFileDialog, QMessageBox, QGroupBox
)
from PyQt5.QtCore import QDateTime, QThreadPool
import qtawesome as qta

from uploader_core.ai_worker import AIWorker
from uploader_core.youtube_worker import YouTubeWorker


class AccountTabWidget(QWidget):
    """Виджет для управления одним аккаунтом YouTube"""
    
    def __init__(self, account_name, config_manager, auth_manager, parent=None):
        super().__init__(parent)
        
        # Сохранение параметров
        self.account_name = account_name
        self.config_manager = config_manager
        self.auth_manager = auth_manager
        
        # Пул потоков для фоновых задач
        self.thread_pool = QThreadPool()
        
        # Основной layout
        self.main_layout = QVBoxLayout(self)
        
        # Создание вкладок
        self.sub_tabs = QTabWidget()
        self.sub_tabs.currentChanged.connect(self._tab_changed)
        
        # Создание виджетов для каждой вкладки
        self.manual_upload_widget = QWidget()
        self.scheduled_upload_widget = QWidget()
        self.history_widget = QWidget()
        
        # Инициализация содержимого вкладок
        self._create_manual_upload_tab()
        self._create_scheduled_upload_tab()
        self._create_history_tab()
        
        # Добавление вкладок
        self.sub_tabs.addTab(self.manual_upload_widget, 'Ручная загрузка')
        self.sub_tabs.addTab(self.scheduled_upload_widget, 'Запланированные')
        self.sub_tabs.addTab(self.history_widget, 'История')
        
        # Добавление в основной layout
        self.main_layout.addWidget(self.sub_tabs)
        self.setLayout(self.main_layout)
    
    def _tab_changed(self, index):
        """Обработчик смены вкладки"""
        # Обновляем историю при переключении на соответствующую вкладку
        if self.sub_tabs.widget(index) == self.history_widget:
            self._populate_history_table()
    
    def _create_manual_upload_tab(self):
        """Создание вкладки ручной загрузки"""
        layout = QVBoxLayout(self.manual_upload_widget)
        
        # Форма для ввода данных
        form_layout = QFormLayout()
        
        # Поле выбора видеофайла
        self.video_path_edit = QLineEdit()
        browse_btn = QPushButton('Выбрать файл')
        browse_btn.clicked.connect(self._browse_video)
        
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.video_path_edit)
        path_layout.addWidget(browse_btn)
        form_layout.addRow('Путь к видео:', path_layout)
        
        # Основные поля метаданных
        self.title_edit = QLineEdit()
        self.description_edit = QPlainTextEdit()
        self.tags_edit = QLineEdit()
        
        form_layout.addRow('Заголовок:', self.title_edit)
        form_layout.addRow('Описание:', self.description_edit)
        form_layout.addRow('Теги (через запятую):', self.tags_edit)
        
        # Настройки приватности
        self.privacy_combo = QComboBox()
        self.privacy_combo.addItems(['private', 'unlisted', 'public'])
        form_layout.addRow('Приватность:', self.privacy_combo)
        
        # Настройки планирования публикации
        self.publish_at_checkbox = QCheckBox('Опубликовать в определенное время')
        self.publish_at_datetime = QDateTimeEdit()
        self.publish_at_datetime.setDateTime(QDateTime.currentDateTime())
        self.publish_at_datetime.setCalendarPopup(True)
        self.publish_at_datetime.setVisible(False)
        
        # Связываем чекбокс с полем даты
        self.publish_at_checkbox.toggled.connect(self.publish_at_datetime.setVisible)
        
        form_layout.addRow(self.publish_at_checkbox)
        form_layout.addRow(self.publish_at_datetime)
        
        layout.addLayout(form_layout)
        
        # Группа AI генерации
        ai_group = QGroupBox('AI Генерация')
        ai_layout = QVBoxLayout(ai_group)
        
        # Кнопка генерации метаданных
        self.ai_generate_btn = QPushButton(
            qta.icon('fa5s.magic', color='white'),
            ' Сгенерировать метаданные'
        )
        self.ai_generate_btn.clicked.connect(self._run_ai_generation)
        
        # Статус AI генерации
        self.ai_status_label = QLabel('Статус: ожидание')
        self.ai_status_label.setStyleSheet('color: gray;')
        
        ai_layout.addWidget(self.ai_generate_btn)
        ai_layout.addWidget(self.ai_status_label)
        
        layout.addWidget(ai_group)
        
        # Кнопка загрузки
        self.upload_btn = QPushButton(
            qta.icon('fa5s.upload', color='white'),
            ' Загрузить видео'
        )
        self.upload_btn.clicked.connect(self._run_upload)
        
        layout.addWidget(self.upload_btn)
        layout.addStretch()
    
    def _create_scheduled_upload_tab(self):
        """Создание вкладки запланированных загрузок"""
        layout = QVBoxLayout(self.scheduled_upload_widget)
        
        # Таблица запланированных загрузок
        self.schedule_table = QTableWidget()
        self.schedule_table.setColumnCount(4)
        self.schedule_table.setHorizontalHeaderLabels([
            'Видео', 'Заголовок', 'Время публикации', 'Статус'
        ])
        
        # Настройка таблицы
        self.schedule_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.schedule_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        
        layout.addWidget(self.schedule_table)
    
    def _create_history_tab(self):
        """Создание вкладки истории загрузок"""
        layout = QVBoxLayout(self.history_widget)
        
        # Таблица истории
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels([
            'Дата', 'Видео', 'Заголовок', 'ID / Статус'
        ])
        
        # Настройка таблицы
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.history_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.history_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        layout.addWidget(self.history_table)
    
    def _populate_history_table(self):
        """Заполнение таблицы истории данными"""
        # Очищаем таблицу
        self.history_table.setRowCount(0)
        
        # Получаем данные истории
        history_entries = self.config_manager.get_history()
        
        # Фильтруем записи для текущего аккаунта
        account_history = [
            entry for entry in history_entries
            if entry.get('account') == self.account_name
        ]
        
        # Заполняем таблицу
        for entry in account_history:
            row_position = self.history_table.rowCount()
            self.history_table.insertRow(row_position)
            
            # Заполняем ячейки
            self.history_table.setItem(
                row_position, 0,
                QTableWidgetItem(entry.get('timestamp', ''))
            )
            self.history_table.setItem(
                row_position, 1,
                QTableWidgetItem(entry.get('path', ''))
            )
            self.history_table.setItem(
                row_position, 2,
                QTableWidgetItem(entry.get('title', ''))
            )
            self.history_table.setItem(
                row_position, 3,
                QTableWidgetItem(entry.get('video_id', 'N/A'))
            )
        
        # Подгоняем размеры колонок
        self.history_table.resizeColumnsToContents()
    
    def _browse_video(self):
        """Открытие диалога выбора видеофайла"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            'Выбрать видео',
            '',
            'Video Files (*.mp4 *.mov *.avi)'
        )
        
        if file_path:
            self.video_path_edit.setText(file_path)
    
    def _run_ai_generation(self):
        """Запуск AI генерации метаданных"""
        video_path = self.video_path_edit.text()
        
        if not video_path:
            QMessageBox.warning(self, 'Ошибка', 'Сначала выберите видеофайл.')
            return
        
        # Отключаем кнопку и обновляем статус
        self.ai_generate_btn.setEnabled(False)
        self.ai_status_label.setText('Статус: запуск...')
        
        # Создаем и запускаем worker
        worker = AIWorker(video_path)
        worker.signals.finished.connect(self._on_ai_finished)
        worker.signals.error.connect(self._on_ai_error)
        worker.signals.status_update.connect(self._on_ai_status_update)
        
        self.thread_pool.start(worker)
    
    def _on_ai_status_update(self, message):
        """Обновление статуса AI генерации"""
        self.ai_status_label.setText(f'Статус: {message}')
    
    def _on_ai_finished(self, metadata):
        """Обработчик завершения AI генерации"""
        # Заполняем поля сгенерированными данными
        self.title_edit.setText(metadata.get('title', ''))
        self.description_edit.setPlainText(metadata.get('description', ''))
        self.tags_edit.setText(metadata.get('tags', ''))
        
        # Восстанавливаем состояние UI
        self.ai_generate_btn.setEnabled(True)
        self.ai_status_label.setText('Статус: готово!')
        
        # Уведомляем пользователя
        QMessageBox.information(
            self, 'AI Генерация',
            'Метаданные успешно сгенерированы!'
        )
    
    def _on_ai_error(self, error_message):
        """Обработчик ошибки AI генерации"""
        self.ai_generate_btn.setEnabled(True)
        self.ai_status_label.setText('Статус: ошибка!')
        
        QMessageBox.critical(self, 'Ошибка AI', str(error_message))
    
    def _run_upload(self):
        """Запуск загрузки видео на YouTube"""
        # Получаем данные из формы
        video_path = self.video_path_edit.text()
        title = self.title_edit.text()
        description = self.description_edit.toPlainText()
        
        # Проверяем заполненность основных полей
        if not all([video_path, title, description]):
            QMessageBox.warning(
                self, 'Ошибка',
                'Заполните все поля: путь, заголовок и описание.'
            )
            return
        
        # Получаем учетные данные для аутентификации
        credentials = self.auth_manager.get_credentials(self.account_name)
        if not credentials:
            QMessageBox.critical(
                self, 'Ошибка',
                'Не удалось получить данные для аутентификации.'
            )
            return
        
        # Отключаем кнопку загрузки
        self.upload_btn.setEnabled(False)
        self.upload_btn.setText(' Загрузка...')
        
        # Подготавливаем параметры загрузки
        worker = YouTubeWorker(
            credentials=credentials,
            video_path=video_path,
            title=title,
            description=description,
            tags=self.tags_edit.text().split(','),
            privacy_status=self.privacy_combo.currentText(),
            publish_at=(
                self.publish_at_datetime.dateTime().toPyDateTime().isoformat() + 'Z'
                if self.publish_at_checkbox.isChecked()
                else None
            )
        )
        
        # Подключаем обработчики сигналов
        worker.signals.finished.connect(self._on_upload_finished)
        worker.signals.error.connect(self._on_upload_error)
        worker.signals.progress.connect(
            lambda p: self.upload_btn.setText(f' Загрузка... {p}%')
        )
        
        # Запускаем загрузку
        self.thread_pool.start(worker)
    
    def _on_upload_finished(self, video_id):
        """Обработчик успешной загрузки"""
        # Восстанавливаем состояние кнопки
        self.upload_btn.setEnabled(True)
        self.upload_btn.setText(' Загрузить видео')
        
        # Уведомляем пользователя
        QMessageBox.information(
            self, 'Успех',
            f'Видео успешно загружено! ID: {video_id}'
        )
        
        # Добавляем запись в историю
        self.config_manager.add_history_entry({
            'account': self.account_name,
            'video_id': video_id,
            'title': self.title_edit.text(),
            'path': self.video_path_edit.text(),
            'timestamp': QDateTime.currentDateTime().toString('yyyy-MM-dd HH:mm:ss')
        })
        
        # Очищаем форму и обновляем историю
        self._clear_manual_upload_form()
        self._populate_history_table()
    
    def _on_upload_error(self, error):
        """Обработчик ошибки загрузки"""
        # Восстанавливаем состояние кнопки
        self.upload_btn.setEnabled(True)
        self.upload_btn.setText(' Загрузить видео')
        
        # Показываем ошибку
        QMessageBox.critical(self, 'Ошибка загрузки', str(error))
    
    def _clear_manual_upload_form(self):
        """Очистка формы ручной загрузки"""
        self.video_path_edit.clear()
        self.title_edit.clear()
        self.description_edit.clear()
        self.tags_edit.clear()
        self.privacy_combo.setCurrentIndex(0)
        self.publish_at_checkbox.setChecked(False)