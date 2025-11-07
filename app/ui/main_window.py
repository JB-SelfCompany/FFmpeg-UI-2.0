from pathlib import Path
from typing import Optional, Tuple, List
import logging

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QMessageBox, QScrollArea, QMenuBar, QTabWidget
)
from PySide6.QtCore import Qt, QThread, QSettings
from PySide6.QtGui import QScreen, QAction

from .widgets.file_selector import FileSelector
from .widgets.format_selector import FormatSelector
from .widgets.video_options import VideoOptions
from .widgets.audio_options import AudioOptions
from .widgets.advanced_options import AdvancedOptions
from .widgets.progress_widget import ProgressWidget
from .widgets.batch_queue import BatchQueue
from .widgets.logger_widget import LoggerWidget
from .widgets.settings_dialog import SettingsDialog
from .widgets.filter_widget import FilterWidget
from .widgets.stream_selector import StreamSelectorWidget
from .widgets.timing_options import TimingOptionsWidget
from .widgets.metadata_editor import MetadataEditorWidget
from .widgets.subtitle_options import SubtitleOptionsWidget
from .widgets.image_sequence_widget import ImageSequenceWidget
from .widgets.chapters_widget import ChaptersWidget
from .widgets.concatenation_widget import ConcatenationWidget

from core.ffmpeg_manager import FFmpegManager
from core.conversion_engine import ConversionEngine
from core.batch_processor import BatchProcessor
from core.codec_selector import CodecSelector, CodecPurpose
from core.filter_manager import FilterManager
from core.ffprobe_manager import FFProbeManager
from core.image_sequence import ImageSequenceManager, ImageSequenceConfig, FrameExtractionConfig
from core.chapters_manager import ChaptersManager
from core.concatenation import ConcatenationManager, ConcatConfig
from core.advanced_filters import get_advanced_video_filters, get_advanced_audio_filters

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    """Главное окно с GPU поддержкой"""
    
    def __init__(self):
        super().__init__()

        self.ffmpeg_manager = FFmpegManager()
        self.codec_selector = CodecSelector()
        self.filter_manager = FilterManager()

        # Инициализируем FFProbeManager с путем из FFmpegManager
        ffprobe_path = self.ffmpeg_manager.ffprobe_path or "ffprobe"
        self.ffprobe_manager = FFProbeManager(ffprobe_path)
        logger.info(f"FFProbeManager инициализирован с путем: {ffprobe_path}")
        self.conversion_engine = None
        self.conversion_thread = None
        self.batch_processor = None
        self.batch_thread = None
        self.batch_files = []

        # Настройки приложения
        self.settings = QSettings("FFmpegConverter", "Settings")
        self.current_theme = self.settings.value("theme", "auto")

        # Окна
        self.logger_widget = None

        self._setup_window_geometry()
        self._init_menu()
        self._init_ui()
        self._setup_connections()
        self._check_ffmpeg()
        self._setup_gpu()
        self._load_advanced_filters()
        self._apply_theme()
        self._restore_advanced_mode()

    def _restore_advanced_mode(self):
        """Восстановить сохраненное состояние расширенного режима"""
        is_advanced = self.settings.value("advanced_mode", True, type=bool)
        self.advanced_mode_action.setChecked(is_advanced)
        self._toggle_advanced_mode()

    def _setup_window_geometry(self):
        """Настройка геометрии окна"""
        self.setWindowTitle("FFmpeg UI 2.0")
        self.setMinimumSize(900, 600)
        
        screen = QScreen.availableGeometry(self.screen())
        width = min(1100, int(screen.width() * 0.75))
        height = min(800, int(screen.height() * 0.85))
        self.resize(width, height)
        
        x = (screen.width() - width) // 2
        y = (screen.height() - height) // 2
        self.move(x, y)

    def _init_menu(self):
        """Инициализация меню"""
        menubar = self.menuBar()

        # === Меню "Инструменты" (теперь первое) ===
        tools_menu = menubar.addMenu("🛠 Инструменты")

        # Логирование
        logging_action = QAction("📋 Просмотр логов", self)
        logging_action.setShortcut("Ctrl+L")
        logging_action.triggered.connect(self._open_logger)
        tools_menu.addAction(logging_action)

        # Настройки
        settings_action = QAction("⚙️ Настройки", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self._open_settings)
        tools_menu.addAction(settings_action)

        tools_menu.addSeparator()

        # Выход
        exit_action = QAction("❌ Выход", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        tools_menu.addAction(exit_action)

        # === Меню "Вид" ===
        view_menu = menubar.addMenu("👁 Вид")

        # Чекбокс расширенного режима (единственный пункт в меню)
        self.advanced_mode_action = QAction("🔧 Расширенный режим", self)
        self.advanced_mode_action.setCheckable(True)
        self.advanced_mode_action.setChecked(True)  # По умолчанию включен
        self.advanced_mode_action.triggered.connect(self._toggle_advanced_mode)
        view_menu.addAction(self.advanced_mode_action)

        # Список для отслеживания расширенных действий (пустой, но нужен для совместимости)
        self.advanced_menu_actions = []

        # === Меню "Помощь" ===
        help_menu = menubar.addMenu("❓ Помощь")

        # О программе
        about_action = QAction("О программе", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)

        # Горячие клавиши
        shortcuts_action = QAction("Горячие клавиши", self)
        shortcuts_action.setShortcut("F1")
        shortcuts_action.triggered.connect(self._show_shortcuts)
        help_menu.addAction(shortcuts_action)

    def _init_ui(self):
        """Инициализация UI"""
        # Создаем центральный виджет
        central = QWidget()
        self.setCentralWidget(central)
        central_layout = QVBoxLayout(central)
        central_layout.setContentsMargins(5, 5, 5, 5)
        central_layout.setSpacing(5)

        # Создаем вкладки для основного функционала
        self.tabs = QTabWidget()

        # Вкладка 1: Файлы и формат
        files_tab = self._create_files_tab()
        self.tabs.addTab(files_tab, "📁 Файлы")

        # Вкладка 2: Превью видео (сразу после файлов)
        preview_tab = self._create_preview_tab()
        self.tabs.addTab(preview_tab, "🎞 Превью")

        # Вкладка 3: Видео опции
        video_tab = self._create_video_tab()
        self.tabs.addTab(video_tab, "🎬 Видео")

        # Вкладка 4: Аудио опции
        audio_tab = self._create_audio_tab()
        self.tabs.addTab(audio_tab, "🔊 Аудио")

        # Вкладка 5: Продвинутые настройки
        advanced_tab = self._create_advanced_tab()
        self.tabs.addTab(advanced_tab, "⚙️ Дополнительно")

        # Вкладка 6: Выбор потоков
        streams_tab = self._create_streams_tab()
        self.tabs.addTab(streams_tab, "📺 Потоки")

        # Вкладка 7: Обрезка
        timing_tab = self._create_timing_tab()
        self.tabs.addTab(timing_tab, "✂️ Обрезка")

        # Вкладка 8: Метаданные
        metadata_tab = self._create_metadata_tab()
        self.tabs.addTab(metadata_tab, "📝 Метаданные")

        # Вкладка 9: Субтитры
        subtitles_tab = self._create_subtitles_tab()
        self.tabs.addTab(subtitles_tab, "💬 Субтитры")

        # Вкладка 10: Последовательности изображений
        image_seq_tab = self._create_image_sequence_tab()
        self.tabs.addTab(image_seq_tab, "📸 Изображения")

        # Вкладка 11: Главы
        chapters_tab = self._create_chapters_tab()
        self.tabs.addTab(chapters_tab, "📖 Главы")

        # Вкладка 12: Объединение видео
        concat_tab = self._create_concatenation_tab()
        self.tabs.addTab(concat_tab, "🔗 Объединение")

        # Добавляем вкладки в layout (теперь без горизонтального split)
        central_layout.addWidget(self.tabs, stretch=1)

        # Прогресс (всегда видимый внизу)
        self.progress_widget = ProgressWidget()
        central_layout.addWidget(self.progress_widget, stretch=0)

        # Кнопки управления (всегда видимые внизу)
        buttons_row = QHBoxLayout()
        buttons_row.setSpacing(10)
        buttons_row.setContentsMargins(10, 5, 10, 10)

        self.start_button = QPushButton("▶ Начать конвертацию")
        self.start_button.setMinimumHeight(45)
        self.start_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4CAF50, stop:1 #45a049);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #66BB6A, stop:1 #4CAF50);
            }
            QPushButton:disabled {
                background: #BDBDBD;
                color: #757575;
            }
        """)

        self.stop_button = QPushButton("⏹ Остановить")
        self.stop_button.setMinimumHeight(45)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #F44336, stop:1 #D32F2F);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #E57373, stop:1 #F44336);
            }
            QPushButton:disabled {
                background: #BDBDBD;
                color: #757575;
            }
        """)

        self.quick_apply_button = QPushButton("⚡ Применить без конвертации")
        self.quick_apply_button.setMinimumHeight(45)
        self.quick_apply_button.setToolTip("Применить фильтры к видео без полной конвертации (минимальное перекодирование)")
        self.quick_apply_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #9C27B0, stop:1 #7B1FA2);
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #AB47BC, stop:1 #9C27B0);
            }
            QPushButton:disabled {
                background: #BDBDBD;
                color: #757575;
            }
        """)
        self.quick_apply_button.clicked.connect(self._quick_apply_filters)

        buttons_row.addWidget(self.start_button, stretch=1)
        buttons_row.addWidget(self.stop_button, stretch=1)
        buttons_row.addWidget(self.quick_apply_button, stretch=1)
        central_layout.addLayout(buttons_row)

        self.statusBar().showMessage("✓ Готов к работе")

    def _create_files_tab(self) -> QWidget:
        """Создать вкладку выбора файлов и формата"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # Файлы и формат
        top_layout = QHBoxLayout()
        top_layout.setSpacing(10)

        self.file_selector = FileSelector()
        top_layout.addWidget(self.file_selector, stretch=2)

        self.format_selector = FormatSelector()
        top_layout.addWidget(self.format_selector, stretch=1)

        layout.addLayout(top_layout)

        # Batch очередь
        self.batch_queue = BatchQueue()
        self.batch_queue.setVisible(False)
        layout.addWidget(self.batch_queue, stretch=1)

        layout.addStretch()

        return tab

    def _create_video_tab(self) -> QWidget:
        """Создать вкладку видео опций"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        self.video_options = VideoOptions()
        layout.addWidget(self.video_options)

        layout.addStretch()

        return tab

    def _create_audio_tab(self) -> QWidget:
        """Создать вкладку аудио опций"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        self.audio_options = AudioOptions()
        layout.addWidget(self.audio_options)

        layout.addStretch()

        return tab

    def _create_advanced_tab(self) -> QWidget:
        """Создать вкладку продвинутых настроек"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        self.advanced_options = AdvancedOptions()
        layout.addWidget(self.advanced_options)

        layout.addStretch()

        return tab

    def _create_streams_tab(self) -> QWidget:
        """Создать вкладку выбора потоков"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # Добавляем ScrollArea для прокрутки
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.stream_selector = StreamSelectorWidget(self.ffprobe_manager)
        scroll.setWidget(self.stream_selector)

        layout.addWidget(scroll)

        return tab

    def _create_timing_tab(self) -> QWidget:
        """Создать вкладку настроек времени"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # Добавляем ScrollArea для прокрутки
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.timing_options = TimingOptionsWidget()
        scroll.setWidget(self.timing_options)

        layout.addWidget(scroll)

        return tab

    def _create_metadata_tab(self) -> QWidget:
        """Создать вкладку редактирования метаданных"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # Добавляем ScrollArea для прокрутки
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.metadata_editor = MetadataEditorWidget()
        scroll.setWidget(self.metadata_editor)

        layout.addWidget(scroll)

        return tab

    def _create_subtitles_tab(self) -> QWidget:
        """Создать вкладку работы с субтитрами"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        # Добавляем ScrollArea для прокрутки
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.subtitle_options = SubtitleOptionsWidget()
        scroll.setWidget(self.subtitle_options)

        layout.addWidget(scroll)

        return tab

    def _create_preview_tab(self) -> QWidget:
        """Создать вкладку превью видео с фильтрами"""
        from PySide6.QtWidgets import QSplitter

        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Создаем splitter для разделения превью и фильтров
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Левая часть: Видео-превью
        from ui.widgets.video_preview import VideoPreviewWidget
        self.video_preview = VideoPreviewWidget()
        splitter.addWidget(self.video_preview)

        # Правая часть: Фильтры
        self.filter_widget = FilterWidget(self.filter_manager)
        splitter.addWidget(self.filter_widget)

        # Устанавливаем пропорции: превью 60%, фильтры 40%
        splitter.setStretchFactor(0, 6)
        splitter.setStretchFactor(1, 4)

        layout.addWidget(splitter, stretch=1)

        return tab

    def _create_image_sequence_tab(self) -> QWidget:
        """Создать вкладку для работы с изображениями"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.image_sequence_widget = ImageSequenceWidget()
        scroll.setWidget(self.image_sequence_widget)

        layout.addWidget(scroll)
        return tab

    def _create_chapters_tab(self) -> QWidget:
        """Создать вкладку для управления главами"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.chapters_widget = ChaptersWidget()
        scroll.setWidget(self.chapters_widget)

        layout.addWidget(scroll)
        return tab

    def _create_concatenation_tab(self) -> QWidget:
        """Создать вкладку для объединения видео"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(10, 10, 10, 10)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self.concatenation_widget = ConcatenationWidget()
        scroll.setWidget(self.concatenation_widget)

        layout.addWidget(scroll)
        return tab

    def _setup_connections(self):
        """Настройка сигналов"""
        self.start_button.clicked.connect(self._start_conversion)
        self.stop_button.clicked.connect(self._stop_conversion)
        self.file_selector.batch_files_selected.connect(self._on_batch_files_selected)
        self.batch_queue.clear_requested.connect(self._clear_batch_queue)

        # Связываем file_selector с stream_selector
        self.file_selector.input_line.textChanged.connect(self._on_input_file_changed)

        # Связываем изменения фильтров с video preview
        self.filter_widget.filters_changed.connect(self._on_filters_changed)

        # Image Sequences
        self.image_sequence_widget.create_video_requested.connect(self._handle_create_video_from_images)
        self.image_sequence_widget.extract_frames_requested.connect(self._handle_extract_frames)

        # Chapters
        self.chapters_widget.add_chapters_requested.connect(self._handle_add_chapters)
        self.chapters_widget.split_by_chapters_requested.connect(self._handle_split_by_chapters)

        # Concatenation
        self.concatenation_widget.concat_requested.connect(self._handle_concatenation)
    
    def _on_batch_files_selected(self, files):
        """Обработка выбора batch файлов"""
        self.batch_files = files
        self.batch_queue.setVisible(True)
        self.batch_queue.clear_all()
        
        for file_path in files:
            filename = Path(file_path).name
            self.batch_queue.add_file(filename)
        
        logger.info(f"Выбрано {len(files)} файлов для batch обработки")
    
    def _clear_batch_queue(self):
        """Очистить batch очередь"""
        self.batch_files.clear()
        self.batch_queue.clear_all()
        self.batch_queue.setVisible(False)
        logger.info("Batch очередь очищена")

    def _on_input_file_changed(self, filepath: str):
        """Обработчик изменения входного файла"""
        if filepath and Path(filepath).exists():
            # Устанавливаем файл для stream selector
            self.stream_selector.set_input_file(filepath)

            # Загружаем видео в превью (только если не batch режим)
            if not self.file_selector.is_batch_mode():
                # Проверяем, что это видео файл
                video_extensions = ['.mp4', '.avi', '.mkv', '.mov', '.webm', '.flv', '.wmv', '.m4v', '.mpg', '.mpeg']
                if Path(filepath).suffix.lower() in video_extensions:
                    self.video_preview.load_video(filepath)
                    logger.info(f"Видео загружено в превью: {filepath}")

                    # Обновляем фильтры для preview
                    self._update_preview_filters()
                else:
                    self.video_preview.clear()
            else:
                # В batch режиме очищаем превью
                self.video_preview.clear()

    def _on_filters_changed(self):
        """Обработчик изменения фильтров"""
        self._update_preview_filters()

    def _update_preview_filters(self):
        """Обновить фильтры в video preview"""
        if self.video_preview.video_path:
            filters = self.filter_widget.get_filters_for_preview()
            self.video_preview.set_filters(filters)
            logger.info(f"Фильтры обновлены в preview: {len(filters)} фильтров")

    def _check_ffmpeg(self):
        """Проверка FFmpeg"""
        if not self.ffmpeg_manager.is_available():
            QMessageBox.warning(
                self,
                "FFmpeg не найден",
                "FFmpeg не обнаружен в системе.\n"
                "Пожалуйста, установите FFmpeg для работы приложения."
            )
            self.start_button.setEnabled(False)
            logger.error("FFmpeg недоступен")
    
    def _setup_gpu(self):
        """Настройка GPU"""
        gpu_detector = self.ffmpeg_manager.get_gpu_detector()

        if gpu_detector:
            gpu_list = gpu_detector.get_gpu_list()
            self.advanced_options.set_gpu_list(gpu_list)

            primary_gpu = gpu_detector.get_primary_gpu()
            if primary_gpu and primary_gpu.vendor != 'none':
                self.statusBar().showMessage(f"✓ GPU обнаружен: {primary_gpu}", 5000)
                logger.info(f"Основной GPU: {primary_gpu}")
            else:
                self.statusBar().showMessage("ℹ GPU не обнаружен, доступно CPU кодирование", 5000)
                logger.info("GPU не обнаружен")
        else:
            logger.warning("GPU детектор недоступен")

        # Загружаем расширенные фильтры
        self._load_advanced_filters()

    def _load_advanced_filters(self):
        """Загрузить расширенные фильтры"""
        try:
            # Получаем новые фильтры
            video_filters = get_advanced_video_filters()
            audio_filters = get_advanced_audio_filters()

            # Добавляем в filter_manager
            for filter_id, filter_profile in video_filters.items():
                if not hasattr(self.filter_manager, 'filters'):
                    self.filter_manager.filters = {}
                self.filter_manager.filters[filter_id] = filter_profile

            for filter_id, filter_profile in audio_filters.items():
                if not hasattr(self.filter_manager, 'filters'):
                    self.filter_manager.filters = {}
                self.filter_manager.filters[filter_id] = filter_profile

            # Обновляем UI фильтров
            if hasattr(self, 'filter_widget') and hasattr(self.filter_widget, 'refresh_filter_library'):
                self.filter_widget.refresh_filter_library()

            logger.info(f"Загружено {len(video_filters)} видео и {len(audio_filters)} аудио расширенных фильтров")
        except Exception as e:
            logger.error(f"Ошибка загрузки расширенных фильтров: {e}", exc_info=True)

    def _handle_create_video_from_images(self, config: ImageSequenceConfig):
        """Обработка создания видео из изображений"""
        try:
            manager = ImageSequenceManager(self.ffmpeg_manager.ffmpeg_path)
            cmd = manager.build_image_to_video_command(config)

            if not cmd:
                QMessageBox.warning(self, "Ошибка", "Не удалось построить команду")
                return

            # Запускаем конвертацию
            self._start_conversion_with_command(cmd, config.output_file)
            logger.info(f"Запущено создание видео из изображений: {config.output_file}")
        except Exception as e:
            logger.error(f"Ошибка создания видео из изображений: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка создания видео:\n{str(e)}")

    def _handle_extract_frames(self, config: FrameExtractionConfig):
        """Обработка извлечения кадров из видео"""
        try:
            manager = ImageSequenceManager(self.ffmpeg_manager.ffmpeg_path)
            cmd = manager.build_frame_extraction_command(config)

            if not cmd:
                QMessageBox.warning(self, "Ошибка", "Не удалось построить команду")
                return

            self._start_conversion_with_command(cmd, config.output_pattern)
            logger.info(f"Запущено извлечение кадров: {config.output_pattern}")
        except Exception as e:
            logger.error(f"Ошибка извлечения кадров: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка извлечения кадров:\n{str(e)}")

    def _handle_add_chapters(self, chapters: list, input_file: str, output_file: str):
        """Обработка добавления глав к видео"""
        try:
            manager = ChaptersManager(
                self.ffmpeg_manager.ffmpeg_path,
                self.ffmpeg_manager.ffprobe_path
            )
            cmd = manager.add_chapters_to_video(input_file, chapters, output_file)

            if not cmd:
                QMessageBox.warning(self, "Ошибка", "Не удалось построить команду")
                return

            self._start_conversion_with_command(cmd, output_file)
            logger.info(f"Запущено добавление глав: {len(chapters)} глав в {output_file}")
        except Exception as e:
            logger.error(f"Ошибка добавления глав: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка добавления глав:\n{str(e)}")

    def _handle_split_by_chapters(self, chapters: list, input_file: str, output_folder: str):
        """Обработка разделения видео по главам"""
        try:
            manager = ChaptersManager(
                self.ffmpeg_manager.ffmpeg_path,
                self.ffmpeg_manager.ffprobe_path
            )
            commands = manager.split_video_by_chapters(input_file, chapters, output_folder)

            if not commands:
                QMessageBox.warning(self, "Ошибка", "Не удалось построить команды")
                return

            # Для множественных команд создаем batch задачи
            from core.batch_processor import BatchJob
            batch_jobs = []
            for i, cmd in enumerate(commands):
                output_path = Path(output_folder) / f"chapter_{i+1:02d}.mp4"
                job = BatchJob(
                    input_file=input_file,
                    output_file=str(output_path),
                    format_name="mp4",
                    ffmpeg_command=cmd
                )
                batch_jobs.append(job)

            # Запускаем batch обработку
            self._start_batch_with_jobs(batch_jobs)
            logger.info(f"Запущено разделение по главам: {len(chapters)} частей")
        except Exception as e:
            logger.error(f"Ошибка разделения по главам: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка разделения по главам:\n{str(e)}")

    def _handle_concatenation(self, config: ConcatConfig):
        """Обработка объединения видео"""
        try:
            manager = ConcatenationManager(self.ffmpeg_manager.ffmpeg_path)
            cmd = manager.build_concat_command(config)

            if not cmd:
                QMessageBox.warning(self, "Ошибка", "Не удалось построить команду")
                return

            self._start_conversion_with_command(cmd, config.output_file)
            logger.info(f"Запущено объединение: {len(config.clips)} клипов в {config.output_file}")
        except Exception as e:
            logger.error(f"Ошибка объединения видео: {e}", exc_info=True)
            QMessageBox.critical(self, "Ошибка", f"Ошибка объединения видео:\n{str(e)}")

    def _start_conversion_with_command(self, cmd: list, output_file: str):
        """Запуск конвертации с готовой командой"""
        # Останавливаем предыдущие процессы
        if self.conversion_engine:
            self.conversion_engine.stop()
            if self.conversion_thread:
                self.conversion_thread.quit()
                self.conversion_thread.wait()

        # Создаем новый engine
        self.conversion_engine = ConversionEngine(cmd)
        self.conversion_thread = QThread()
        self.conversion_engine.moveToThread(self.conversion_thread)

        # Подключаем сигналы
        self.conversion_thread.started.connect(self.conversion_engine.start)
        self.conversion_engine.progress_updated.connect(self.progress_widget.update_progress)
        self.conversion_engine.conversion_finished.connect(self._on_conversion_finished)
        self.conversion_engine.conversion_error.connect(self._on_conversion_error)

        # Обновляем UI
        self.progress_widget.show_progress()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        # Запускаем
        self.conversion_thread.start()
        logger.info(f"Конвертация запущена: {output_file}")
        logger.info(f"Команда FFmpeg: {' '.join(cmd)}")

    def _start_batch_with_jobs(self, jobs: list):
        """Запуск batch обработки с готовыми задачами"""
        if not jobs:
            return

        # Останавливаем предыдущие процессы
        if self.batch_processor:
            self.batch_processor.stop()
            if self.batch_thread:
                self.batch_thread.quit()
                self.batch_thread.wait()

        # Создаем batch processor
        from core.batch_processor import BatchProcessor
        self.batch_processor = BatchProcessor(jobs, self.ffmpeg_manager.ffmpeg_path)
        self.batch_thread = QThread()
        self.batch_processor.moveToThread(self.batch_thread)

        # Подключаем сигналы
        self.batch_thread.started.connect(self.batch_processor.start)
        self.batch_processor.job_started.connect(self._on_batch_job_started)
        self.batch_processor.job_finished.connect(self._on_batch_job_finished)
        self.batch_processor.job_error.connect(self._on_batch_job_error)
        self.batch_processor.all_finished.connect(self._on_batch_all_finished)
        self.batch_processor.progress_updated.connect(self.progress_widget.update_progress)

        # Обновляем UI
        self.progress_widget.show_progress()
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        # Запускаем
        self.batch_thread.start()
        logger.info(f"Batch обработка запущена: {len(jobs)} задач")

    def _start_conversion(self):
        """Запуск конвертации"""
        if self.file_selector.is_batch_mode() and self.batch_files:
            self._start_batch_conversion()
        else:
            self._start_single_conversion()
    
    def _start_single_conversion(self):
        """Одиночная конвертация с валидацией GPU"""
        input_file = self.file_selector.get_input_file()
        if not input_file or not Path(input_file).exists():
            QMessageBox.warning(self, "Ошибка", "Выберите корректный входной файл")
            return
        
        output_file = self.file_selector.get_output_file()
        if not output_file:
            QMessageBox.warning(self, "Ошибка", "Укажите выходной файл")
            return
        
        format_data = self.format_selector.get_selected_format()
        if not format_data:
            QMessageBox.warning(self, "Ошибка", "Выберите выходной формат")
            return
        
        output_format = format_data.get('extension', 'mp4')
        
        # Обновление расширения
        output_path = Path(output_file)
        if output_path.suffix.lower() != f'.{output_format.lower()}':
            output_file = str(output_path.with_suffix(f'.{output_format}'))
            self.file_selector.output_line.setText(output_file)
        
        # Валидация GPU и кодека
        selected_gpu = self.advanced_options.get_selected_gpu()
        gpu_detector = self.ffmpeg_manager.get_gpu_detector()
        
        if gpu_detector and selected_gpu not in ['none', 'auto']:
            video_codec = self.video_options.get_video_codec()
            if video_codec and video_codec != 'copy':
                codec_name = self._get_codec_name(video_codec)
                
                # Проверка поддержки кодека GPU
                if not gpu_detector.is_codec_supported_by_gpu(codec_name, selected_gpu):
                    gpu_name = gpu_detector._get_gpu_name_by_vendor(selected_gpu)
                    reply = QMessageBox.warning(
                        self,
                        "Кодек не поддерживается GPU",
                        f"⚠ {gpu_name} не поддерживает {codec_name.upper()} кодирование.\n\n"
                        f"Поддерживаемые кодеки для этого GPU:\n"
                        f"{', '.join(sorted([c.upper() for c in gpu_detector.detected_gpus[0].supported_codecs])) if gpu_detector.detected_gpus else 'нет'}\n\n"
                        f"Варианты:\n"
                        f"• Выбрать другой кодек (H.264 вместо AV1)\n"
                        f"• Переключиться на CPU кодирование\n"
                        f"• Продолжить с автоматическим fallback на CPU\n\n"
                        f"Продолжить с CPU кодированием?",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply == QMessageBox.No:
                        return
                
                # Проверка совместимости с контейнером
                if not gpu_detector.is_codec_container_compatible(codec_name, output_format):
                    reply = QMessageBox.question(
                        self,
                        "Несовместимость кодека и контейнера",
                        f"⚠ Кодек {codec_name.upper()} несовместим с контейнером {output_format.upper()}.\n\n"
                        f"Рекомендации:\n"
                        f"• Для WebM: VP8, VP9 или AV1\n"
                        f"• Для MP4: H.264, H.265 или AV1\n"
                        f"• Для универсальности: MKV\n\n"
                        f"Продолжить с автоматическим подбором кодека?",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply == QMessageBox.No:
                        return
        
        try:
            actual_format = self._get_output_format_from_file(output_file)
            command, pass2_command, passlogfile = self._build_ffmpeg_command(input_file, output_file, actual_format)
            logger.info(f"Начало конвертации: {input_file} -> {output_file}")

            self.conversion_engine = ConversionEngine(command, pass2_command, passlogfile)
            self.conversion_thread = QThread()
            self.conversion_engine.moveToThread(self.conversion_thread)
            
            self.conversion_engine.progress_updated.connect(self.progress_widget.update_progress)
            self.conversion_engine.conversion_finished.connect(self._on_conversion_finished)
            self.conversion_engine.conversion_error.connect(self._on_conversion_error)
            self.conversion_thread.started.connect(self.conversion_engine.start)
            
            self.progress_widget.show_progress()
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.statusBar().showMessage("⚙ Конвертация...")
            
            self.conversion_thread.start()
            
        except Exception as e:
            error_msg = f"Ошибка запуска конвертации: {e}"
            logger.error(error_msg, exc_info=True)
            QMessageBox.critical(self, "Ошибка", error_msg)
            self._reset_ui()
    
    def _start_batch_conversion(self):
        """Batch конвертация"""
        output_folder = self.file_selector.get_output_file()
        if not output_folder:
            QMessageBox.warning(self, "Ошибка", "Укажите выходную папку")
            return
        
        output_path = Path(output_folder)
        if not output_path.exists():
            output_path.mkdir(parents=True, exist_ok=True)
        
        format_data = self.format_selector.get_selected_format()
        if not format_data:
            QMessageBox.warning(self, "Ошибка", "Выберите выходной формат")
            return
        
        output_format = format_data.get('extension', 'mp4')
        
        try:
            self.batch_processor = BatchProcessor()

            for input_file in self.batch_files:
                input_path = Path(input_file)
                output_file = str(output_path / f"{input_path.stem}_converted.{output_format}")
                command, pass2_command, passlogfile = self._build_ffmpeg_command(input_file, output_file, output_format)
                self.batch_processor.add_job(input_file, output_file, command, pass2_command, passlogfile)
            
            logger.info(f"Начало batch конвертации: {len(self.batch_files)} файлов")
            
            self.batch_thread = QThread()
            self.batch_processor.moveToThread(self.batch_thread)
            
            self.batch_processor.job_started.connect(self._on_batch_job_started)
            self.batch_processor.job_completed.connect(self._on_batch_job_completed)
            self.batch_processor.job_failed.connect(self._on_batch_job_failed)
            self.batch_processor.job_progress.connect(self._on_batch_job_progress)
            self.batch_processor.all_jobs_completed.connect(self._on_batch_all_completed)
            self.batch_thread.started.connect(self.batch_processor.process_all)
            
            self.progress_widget.show_progress()
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.statusBar().showMessage("⚙ Batch конвертация...")
            
            self.batch_thread.start()
            
        except Exception as e:
            error_msg = f"Ошибка запуска batch конвертации: {e}"
            logger.error(error_msg, exc_info=True)
            QMessageBox.critical(self, "Ошибка", error_msg)
            self._reset_ui()
    
    def _auto_select_codec(self, container: str, gpu_vendor: str = 'none') -> Tuple[str, str]:
        """
        Автоматический выбор кодека
        Возвращает: (ffmpeg_codec_name, reason)
        """
        gpu_detector = self.ffmpeg_manager.get_gpu_detector()
        
        has_gpu = gpu_detector and gpu_vendor not in ['none', 'auto']
        gpu_supported_codecs = []
        
        if has_gpu and gpu_detector:
            for gpu in gpu_detector.detected_gpus:
                if gpu.vendor == gpu_vendor:
                    gpu_supported_codecs = list(gpu.supported_codecs)
                    break
        
        # Определяем цель
        purpose = CodecPurpose.UNIVERSAL
        
        codec_profile, reason = self.codec_selector.get_best_codec_for_container(
            container,
            purpose,
            has_gpu,
            gpu_supported_codecs
        )
        
        # Обновляем UI - ТОЛЬКО информация о выборе кодека
        self.video_options.set_auto_selected_codec(codec_profile.display_name, reason)
        
        return codec_profile.ffmpeg_name, reason
    
    def _build_ffmpeg_command(self, input_file: str, output_file: str, output_format: str):
        """Построение команды FFmpeg с GPU и проверкой совместимости"""
        cmd = [self.ffmpeg_manager.ffmpeg_path]

        # GPU hwaccel для декодирования
        gpu_detector = self.ffmpeg_manager.get_gpu_detector()
        selected_gpu = self.advanced_options.get_selected_gpu()

        # Добавляем hwaccel ТОЛЬКО для декодирования
        if gpu_detector and selected_gpu != 'none':
            hwaccel_args = gpu_detector.get_hwaccel_args(selected_gpu)
            if hwaccel_args:
                cmd.extend(hwaccel_args)
                logger.info(f"Добавлены hwaccel аргументы: {hwaccel_args}")

        # Timing options (ДО -i для input seeking)
        timing_opts = self.timing_options.get_ffmpeg_options()
        # Добавляем только -ss (start time) перед -i, остальное после
        timing_before_input = []
        timing_after_input = []

        i = 0
        while i < len(timing_opts):
            if timing_opts[i] == "-ss":
                timing_before_input.extend([timing_opts[i], timing_opts[i+1]])
                i += 2
            elif timing_opts[i] in ["-t", "-to", "-copyts", "-noaccurate_seek"]:
                timing_after_input.append(timing_opts[i])
                if i + 1 < len(timing_opts) and not timing_opts[i+1].startswith("-"):
                    timing_after_input.append(timing_opts[i+1])
                    i += 2
                else:
                    i += 1
            else:
                i += 1

        if timing_before_input:
            cmd.extend(timing_before_input)
            logger.info(f"Timing options (перед -i): {timing_before_input}")

        cmd.extend(["-i", input_file, "-y"])

        # Timing options (ПОСЛЕ -i)
        if timing_after_input:
            cmd.extend(timing_after_input)
            logger.info(f"Timing options (после -i): {timing_after_input}")

        # Stream selection (-map опции)
        map_opts = self.stream_selector.get_map_options()
        if map_opts:
            cmd.extend(map_opts)
            logger.info(f"Stream mapping: {map_opts}")
        
        # Удаление звука
        if self.audio_options.is_audio_removal_enabled():
            cmd.extend(["-an"])
            logger.info("Звук будет удален")
        
        video_codec = self.video_options.get_video_codec()
        encoder_warning = ""
        
        if video_codec == "auto":
            # Автоматический выбор кодека
            selected_gpu = self.advanced_options.get_selected_gpu()
            auto_codec, auto_reason = self._auto_select_codec(output_format, selected_gpu)
            video_codec = auto_codec
            logger.info(f"Автовыбран кодек: {auto_codec} - {auto_reason}")
        
        if video_codec and video_codec != "copy":
            # Определяем GPU энкодер с учетом контейнера
            if gpu_detector and selected_gpu != 'none':
                codec_name = self._get_codec_name(video_codec)
                gpu_encoder, encoder_warning = gpu_detector.get_best_encoder(codec_name, selected_gpu, output_format)
                cmd.extend(["-c:v", gpu_encoder])
                logger.info(f"Видео кодек: {gpu_encoder}")
                
                # Показываем предупреждение пользователю если есть
                if encoder_warning:
                    self.statusBar().showMessage(encoder_warning, 8000)
                
                # Получаем корректный preset для энкодера с учетом выбора пользователя
                user_preset = self.advanced_options.get_preset()
                preset = gpu_detector.get_encoder_preset(gpu_encoder, user_preset)
                if preset:
                    cmd.extend(["-preset", preset])
                    logger.info(f"Preset: {preset} (из пользовательского: {user_preset})")
            else:
                # CPU кодек
                cpu_encoder = gpu_detector._get_software_encoder(self._get_codec_name(video_codec), output_format) if gpu_detector else video_codec
                cmd.extend(["-c:v", cpu_encoder])
                logger.info(f"Видео кодек (CPU): {cpu_encoder}")
                
                # Preset для CPU кодеков
                if cpu_encoder in ["libx264", "libx265"]:
                    preset = self.advanced_options.get_preset()
                    cmd.extend(["-preset", preset])
            
            # VP9 специфика
            if 'vp9' in cmd[-1].lower() or video_codec == "libvpx-vp9":
                crf = self.video_options.get_crf()
                cmd.extend(["-crf", str(crf), "-b:v", "0"])
                
                cpu_used = self.advanced_options.get_cpu_used()
                cmd.extend(["-cpu-used", str(cpu_used)])
                
                if self.advanced_options.get_row_mt():
                    cmd.extend(["-row-mt", "1"])
            else:
                # CRF для остальных
                crf = self.video_options.get_crf()
                if crf is not None:
                    cmd.extend(["-crf", str(crf)])
                
                bitrate = self.video_options.get_bitrate()
                if bitrate:
                    cmd.extend(["-b:v", bitrate])
            
            # FPS
            fps = self.video_options.get_fps()
            if fps:
                cmd.extend(["-r", str(fps)])

            # === НОВЫЕ ADVANCED VIDEO OPTIONS ===

            # Pixel Format
            pix_fmt = self.video_options.get_pixel_format()
            if pix_fmt:
                cmd.extend(["-pix_fmt", pix_fmt])
                logger.info(f"Pixel format: {pix_fmt}")

            # Aspect Ratio
            aspect = self.video_options.get_aspect_ratio()
            if aspect:
                cmd.extend(["-aspect", aspect])
                logger.info(f"Aspect ratio: {aspect}")

            # Force Keyframes
            keyframes = self.video_options.get_force_keyframes()
            if keyframes:
                cmd.extend(["-force_key_frames", keyframes])
                logger.info(f"Force keyframes: {keyframes}")

            # Видео фильтры (интегрированная система)
            filter_parts = []

            # Разрешение из video_options
            resolution = self.video_options.get_resolution()
            if resolution and resolution != "original":
                filter_parts.append(f"scale={resolution}")
                logger.info(f"Масштабирование: {resolution}")

            # Фильтры из FilterWidget
            filter_string = self.filter_widget.get_video_filter_string()
            if filter_string:
                filter_parts.append(filter_string)
                logger.info(f"Применены видео фильтры: {filter_string}")

            # Subtitle burn-in фильтры
            subtitle_filters = self.subtitle_options.get_filter_options()
            if subtitle_filters:
                filter_parts.extend(subtitle_filters)
                logger.info(f"Применены subtitle фильтры: {subtitle_filters}")

            # Объединяем все фильтры
            if filter_parts:
                combined_filters = ','.join(filter_parts)
                cmd.extend(["-vf", combined_filters])
                logger.info(f"Итоговая цепочка видео фильтров: {combined_filters}")
        else:
            cmd.extend(["-c:v", "copy"])
        
        # Аудио параметры
        if not self.audio_options.is_audio_removal_enabled():
            audio_codec = self.audio_options.get_audio_codec()

            # WebM only supports Opus, Vorbis, or no audio
            webm_compatible_codecs = ["libopus", "libvorbis", "opus", "vorbis"]
            is_webm = output_format.lower() == "webm"

            if audio_codec and audio_codec != "copy":
                # User specified a codec
                if is_webm and audio_codec not in webm_compatible_codecs:
                    logger.warning(f"Audio codec {audio_codec} not compatible with WebM. Switching to libopus.")
                    audio_codec = "libopus"

                cmd.extend(["-c:a", audio_codec])

                if audio_codec in ["libvorbis", "libopus"]:
                    audio_quality = self.audio_options.get_audio_quality()
                    if audio_quality is not None:
                        cmd.extend(["-q:a", str(audio_quality)])
                else:
                    audio_bitrate = self.audio_options.get_audio_bitrate()
                    if audio_bitrate:
                        cmd.extend(["-b:a", audio_bitrate])

                sample_rate = self.audio_options.get_sample_rate()
                if sample_rate:
                    cmd.extend(["-ar", str(sample_rate)])

                channels = self.audio_options.get_channels()
                if channels:
                    cmd.extend(["-ac", str(channels)])
            else:
                # User selected "copy" or no codec
                if is_webm:
                    # WebM doesn't support copying arbitrary codecs
                    # Auto-select Opus with reasonable defaults
                    logger.info("WebM format detected with 'copy' audio codec. Auto-selecting libopus for compatibility.")
                    cmd.extend(["-c:a", "libopus"])
                    # Use default bitrate if not specified
                    audio_bitrate = self.audio_options.get_audio_bitrate()
                    if audio_bitrate:
                        cmd.extend(["-b:a", audio_bitrate])
                    else:
                        cmd.extend(["-b:a", "128k"])  # Reasonable default for Opus
                else:
                    cmd.extend(["-c:a", "copy"])

            # Аудио фильтры из FilterWidget
            audio_filter_string = self.filter_widget.get_audio_filter_string()
            if audio_filter_string:
                cmd.extend(["-af", audio_filter_string])
                logger.info(f"Применены аудио фильтры: {audio_filter_string}")
        else:
            # Удаление аудио
            cmd.append("-an")
            logger.info("Audio removal enabled, adding -an parameter")
        
        # Subtitle options (не burn-in, а копирование потока)
        subtitle_opts = self.subtitle_options.get_ffmpeg_options()
        if subtitle_opts:
            cmd.extend(subtitle_opts)
            logger.info(f"Subtitle опции: {subtitle_opts}")

        # Метаданные
        metadata_opts = self.metadata_editor.get_ffmpeg_options()
        if metadata_opts:
            cmd.extend(metadata_opts)
            logger.info(f"Метаданные: {len(metadata_opts)//2} тегов")

        # Дополнительные параметры
        extra_params = self.advanced_options.get_extra_params()
        if extra_params:
            cmd.extend(extra_params.split())
            logger.info(f"Дополнительные параметры: {extra_params}")

        cmd.append(output_file)

        logger.info(f"Команда FFmpeg: {' '.join(cmd)}")

        # Проверяем, включено ли двухпроходное кодирование
        if self.advanced_options.is_two_pass_enabled():
            logger.info("Two-pass encoding enabled, building pass 1 and pass 2 commands")
            pass1_cmd, pass2_cmd, passlogfile = self._build_two_pass_commands(input_file, output_file, output_format)
            return pass1_cmd, pass2_cmd, passlogfile

        return cmd, None, None

    def _build_two_pass_commands(self, input_file: str, output_file: str, output_format: str):
        """
        Построение команд для двухпроходного кодирования

        Returns:
            Tuple[List[str], List[str], str]: (pass1_cmd, pass2_cmd, passlogfile_path)
        """
        import platform
        import tempfile

        # Определяем null device в зависимости от ОС
        null_device = "NUL" if platform.system() == "Windows" else "/dev/null"

        # Временная директория для passlogfile с уникальным именем на основе выходного файла
        temp_dir = tempfile.gettempdir()
        # Добавляем timestamp для уникальности при параллельных конвертациях
        import time
        timestamp = int(time.time() * 1000)  # миллисекунды
        output_basename = Path(output_file).stem
        passlogfile = Path(temp_dir) / f"ffmpeg2pass_{output_basename}_{timestamp}"

        # Строим базовую команду FFmpeg
        cmd = [self.ffmpeg_manager.ffmpeg_path]

        # GPU hwaccel для декодирования
        gpu_detector = self.ffmpeg_manager.get_gpu_detector()
        selected_gpu = self.advanced_options.get_selected_gpu()

        if gpu_detector and selected_gpu != 'none':
            hwaccel_args = gpu_detector.get_hwaccel_args(selected_gpu)
            if hwaccel_args:
                cmd.extend(hwaccel_args)

        # Timing options (ДО -i для input seeking)
        timing_opts = self.timing_options.get_ffmpeg_options()
        ss_before_input = []
        opts_after_input = []
        if timing_opts:
            i = 0
            while i < len(timing_opts):
                if timing_opts[i] == "-ss" and i + 1 < len(timing_opts):
                    ss_before_input.extend([timing_opts[i], timing_opts[i+1]])
                    i += 2
                else:
                    opts_after_input.extend([timing_opts[i]])
                    if i + 1 < len(timing_opts) and not timing_opts[i+1].startswith('-'):
                        opts_after_input.append(timing_opts[i+1])
                        i += 2
                    else:
                        i += 1

        cmd.extend(ss_before_input)
        cmd.extend(["-i", input_file, "-y"])
        cmd.extend(opts_after_input)

        # Stream selection
        map_opts = self.stream_selector.get_map_options()
        if map_opts:
            cmd.extend(map_opts)

        # Video codec
        video_codec = self.video_options.get_video_codec()
        if video_codec == "copy":
            logger.warning("Two-pass encoding не работает с video codec copy. Используйте другой кодек.")
            # Fallback to single pass
            cmd, _, _ = self._build_ffmpeg_command(input_file, output_file, output_format)
            return cmd, None, None

        # Получаем encoder
        if video_codec and video_codec != "auto":
            encoder, warning = gpu_detector.get_best_encoder(video_codec, selected_gpu) if gpu_detector else (video_codec, None)
        else:
            # Auto codec
            encoder, reason = self._auto_select_codec(output_format, selected_gpu)

        cmd.extend(["-c:v", encoder])

        # Video encoder options (CRF, preset, etc.)
        preset = self.advanced_options.get_preset()
        if encoder.startswith("h264_nvenc") or encoder.startswith("hevc_nvenc"):
            preset_map = {
                "ultrafast": "p1", "superfast": "p2", "veryfast": "p3",
                "faster": "p4", "fast": "p4", "medium": "p4",
                "slow": "p5", "slower": "p6", "veryslow": "p7"
            }
            nvenc_preset = preset_map.get(preset, "p4")
            cmd.extend(["-preset", nvenc_preset])
        elif "qsv" in encoder:
            cmd.extend(["-preset", preset])
        elif encoder in ["libx264", "libx265", "libaom-av1", "libsvtav1"]:
            cmd.extend(["-preset", preset])

        # CRF и Bitrate
        # VP9 и некоторые другие кодеки поддерживают CRF с двухпроходным кодированием
        crf = self.video_options.get_crf()
        bitrate = self.video_options.get_bitrate()

        if 'vp9' in encoder.lower():
            # VP9 использует CRF + constrained quality mode
            if crf is not None:
                cmd.extend(["-crf", str(crf)])
            if bitrate:
                cmd.extend(["-b:v", bitrate])
            else:
                # Для VP9 можно использовать CRF без битрейта в двухпроходном режиме
                cmd.extend(["-b:v", "0"])

            # VP9 специфичные параметры
            cpu_used = self.advanced_options.get_cpu_used()
            cmd.extend(["-cpu-used", str(cpu_used)])

            if self.advanced_options.get_row_mt():
                cmd.extend(["-row-mt", "1"])
        else:
            # Для других кодеков в two-pass режиме нужен битрейт
            if bitrate:
                cmd.extend(["-b:v", bitrate])
            else:
                # Если битрейт не указан, используем значение по умолчанию
                logger.warning("Two-pass encoding требует указания битрейта. Используется значение по умолчанию: 2M")
                cmd.extend(["-b:v", "2M"])

            # CRF для некоторых кодеков тоже можно добавить
            if crf is not None and encoder in ["libx264", "libx265"]:
                cmd.extend(["-crf", str(crf)])

        # FPS
        fps = self.video_options.get_fps()
        if fps:
            cmd.extend(["-r", str(fps)])

        # Advanced video options
        pix_fmt = self.video_options.get_pixel_format()
        if pix_fmt:
            cmd.extend(["-pix_fmt", pix_fmt])

        aspect = self.video_options.get_aspect_ratio()
        if aspect:
            cmd.extend(["-aspect", aspect])

        keyframes = self.video_options.get_force_keyframes()
        if keyframes:
            cmd.extend(["-force_key_frames", keyframes])

        # Video filters
        filter_parts = []
        resolution = self.video_options.get_resolution()
        if resolution and resolution != "original":
            filter_parts.append(f"scale={resolution}")

        video_filter_string = self.filter_widget.get_video_filter_string()
        if video_filter_string:
            filter_parts.append(video_filter_string)

        subtitle_filters = self.subtitle_options.get_filter_options()
        if subtitle_filters:
            filter_parts.extend(subtitle_filters)

        if filter_parts:
            cmd.extend(["-vf", ",".join(filter_parts)])

        # === PASS 1 COMMAND (без аудио и метаданных для оптимизации) ===
        pass1_cmd = cmd.copy()
        pass1_cmd.extend(["-an"])  # Отключаем аудио в Pass 1
        logger.info("Pass 1: аудио отключено (-an) для ускорения анализа")

        # Extra params для обоих проходов
        extra_params = self.advanced_options.get_extra_params()
        if extra_params:
            pass1_cmd.extend(extra_params.split())

        pass1_cmd.extend(["-pass", "1", "-passlogfile", str(passlogfile), "-f", "null", null_device])

        # === PASS 2 COMMAND (с аудио и метаданными) ===
        pass2_cmd = cmd.copy()

        # Audio codec - WebM container requires special handling
        audio_codec = self.audio_options.get_audio_codec()

        # WebM only supports Opus, Vorbis, or no audio
        webm_compatible_codecs = ["libopus", "libvorbis", "opus", "vorbis"]
        is_webm = output_format.lower() == "webm"

        if audio_codec and audio_codec != "copy":
            # User specified a codec
            if is_webm and audio_codec not in webm_compatible_codecs:
                logger.warning(f"Audio codec {audio_codec} not compatible with WebM. Switching to libopus.")
                audio_codec = "libopus"

            pass2_cmd.extend(["-c:a", audio_codec])
            audio_bitrate = self.audio_options.get_audio_bitrate()
            if audio_bitrate:
                pass2_cmd.extend(["-b:a", audio_bitrate])
            sample_rate = self.audio_options.get_sample_rate()
            if sample_rate:
                pass2_cmd.extend(["-ar", str(sample_rate)])
            channels = self.audio_options.get_channels()
            if channels:
                pass2_cmd.extend(["-ac", str(channels)])
        else:
            # User selected "copy" or no codec
            if is_webm:
                # WebM doesn't support copying arbitrary codecs
                # Auto-select Opus with reasonable defaults
                logger.info("WebM format detected with 'copy' audio codec. Auto-selecting libopus for compatibility.")
                pass2_cmd.extend(["-c:a", "libopus"])
                # Use default bitrate if not specified
                audio_bitrate = self.audio_options.get_audio_bitrate()
                if audio_bitrate:
                    pass2_cmd.extend(["-b:a", audio_bitrate])
                else:
                    pass2_cmd.extend(["-b:a", "128k"])  # Reasonable default for Opus
            else:
                pass2_cmd.extend(["-c:a", "copy"])

        # Audio filters
        audio_filter_string = self.filter_widget.get_audio_filter_string()
        if audio_filter_string:
            pass2_cmd.extend(["-af", audio_filter_string])

        # Metadata
        metadata_opts = self.metadata_editor.get_ffmpeg_options()
        if metadata_opts:
            pass2_cmd.extend(metadata_opts)

        # Extra params
        if extra_params:
            pass2_cmd.extend(extra_params.split())

        pass2_cmd.extend(["-pass", "2", "-passlogfile", str(passlogfile)])

        # Subtitle options для pass 2
        subtitle_opts = self.subtitle_options.get_ffmpeg_options()
        if subtitle_opts:
            pass2_cmd.extend(subtitle_opts)

        pass2_cmd.append(output_file)

        logger.info(f"Pass 1 command: {' '.join(pass1_cmd)}")
        logger.info(f"Pass 2 command: {' '.join(pass2_cmd)}")
        logger.info(f"Passlogfile: {passlogfile}")

        return pass1_cmd, pass2_cmd, str(passlogfile)

    def _get_output_format_from_file(self, output_file: str) -> str:
        """Определить формат контейнера из расширения файла"""
        ext = Path(output_file).suffix.lower().lstrip('.')
        return ext if ext else 'mp4'

    def _get_codec_name(self, ffmpeg_codec: str) -> str:
        """Преобразование имени кодека FFmpeg в базовое имя"""
        codec_map = {
            'libx264': 'h264',
            'libx265': 'hevc',
            'libvpx': 'vp8',
            'libvpx-vp9': 'vp9',
            'libaom-av1': 'av1',
            'libsvtav1': 'svt-av1'
        }
        return codec_map.get(ffmpeg_codec, 'h264')
    
    def _on_batch_job_started(self, index, filename):
        """Обработка начала batch задачи"""
        self.batch_queue.update_file_status(index, "processing")
        self.statusBar().showMessage(f"⚙ Обработка ({index+1}/{self.batch_processor.get_jobs_count()}): {filename}")
    
    def _on_batch_job_completed(self, index, filename):
        """Обработка завершения batch задачи"""
        self.batch_queue.update_file_status(index, "completed")
        logger.info(f"Batch задача {index+1} завершена: {filename}")
    
    def _on_batch_job_failed(self, index, filename, error):
        """Обработка ошибки batch задачи"""
        self.batch_queue.update_file_status(index, "failed")
        logger.error(f"Batch задача {index+1} провалена: {filename} - {error}")
    
    def _on_batch_job_progress(self, index, progress_data):
        """Обработка прогресса batch задачи"""
        self.progress_widget.update_progress(progress_data)
    
    def _on_batch_all_completed(self):
        """Обработка завершения всех batch задач с проверкой ошибок"""
        if not self.batch_processor:
            return
        
        # Проверяем статистику
        total = self.batch_processor.get_jobs_count()
        completed = sum(1 for job in self.batch_processor.jobs if job.status == 'completed')
        failed = sum(1 for job in self.batch_processor.jobs if job.status == 'failed')
        
        self._reset_ui()
        
        # Формируем сообщение в зависимости от результатов
        if failed == 0:
            # Все успешно
            self.statusBar().showMessage(f"✓ Все файлы ({total}) успешно конвертированы!", 5000)
            QMessageBox.information(
                self,
                "Успех",
                f"✓ Все файлы ({total}) успешно конвертированы!"
            )
            logger.info(f"Batch конвертация завершена успешно: {completed}/{total}")
        elif completed == 0:
            # Все провалены
            self.statusBar().showMessage(f"✗ Все файлы ({total}) провалены", 8000)
            
            # Собираем причины ошибок
            error_summary = "\n\n".join([
                f"• {Path(job.input_file).name}: {job.error}"
                for job in self.batch_processor.jobs if job.status == 'failed'
            ])
            
            QMessageBox.critical(
                self,
                "Ошибка конвертации",
                f"✗ Конвертация не удалась для всех {total} файлов:\n\n{error_summary}\n\n"
                f"Рекомендации:\n"
                f"• Проверьте совместимость GPU и выбранного кодека\n"
                f"• Попробуйте другой кодек (H.264 вместо AV1)\n"
                f"• Используйте CPU кодирование"
            )
            logger.error(f"Batch конвертация провалена: 0/{total} успешно")
        else:
            # Частичный успех
            self.statusBar().showMessage(f"⚠ Завершено с ошибками: {completed}/{total} успешно", 8000)
            
            failed_files = [Path(job.input_file).name for job in self.batch_processor.jobs if job.status == 'failed']
            
            QMessageBox.warning(
                self,
                "Частичный успех",
                f"⚠ Конвертация завершена частично:\n\n"
                f"✓ Успешно: {completed}\n"
                f"✗ Провалено: {failed}\n\n"
                f"Проваленные файлы:\n" + "\n".join(f"• {f}" for f in failed_files)
            )
            logger.warning(f"Batch конвертация завершена частично: {completed}/{total} успешно")
    
    def _stop_conversion(self):
        """Остановка конвертации"""
        # Останавливаем engine
        if self.conversion_engine:
            self.conversion_engine.stop()

        if self.batch_processor:
            self.batch_processor.stop()

        # Корректно завершаем потоки
        if self.conversion_thread and self.conversion_thread.isRunning():
            logger.info("Завершаем поток конвертации...")
            self.conversion_thread.quit()
            if not self.conversion_thread.wait(5000):  # Ждем 5 секунд
                logger.warning("Поток конвертации не завершился, принудительное завершение")
                self.conversion_thread.terminate()
                self.conversion_thread.wait()
            self.conversion_thread = None
            self.conversion_engine = None

        if self.batch_thread and self.batch_thread.isRunning():
            logger.info("Завершаем поток batch обработки...")
            self.batch_thread.quit()
            if not self.batch_thread.wait(5000):  # Ждем 5 секунд
                logger.warning("Поток batch не завершился, принудительное завершение")
                self.batch_thread.terminate()
                self.batch_thread.wait()
            self.batch_thread = None
            self.batch_processor = None

        self._reset_ui()
        self.statusBar().showMessage("⏹ Остановлено", 3000)
        logger.info("Конвертация остановлена пользователем")

    def _quick_apply_filters(self):
        """Быстрое применение фильтров без полной конвертации"""
        from PySide6.QtWidgets import QFileDialog

        # Проверка входного файла
        input_file = self.file_selector.get_input_file()
        if not input_file or not Path(input_file).exists():
            QMessageBox.warning(self, "Ошибка", "Выберите корректный входной файл")
            return

        # Проверка наличия фильтров
        video_filter_string = self.filter_widget.get_video_filter_string()
        audio_filter_string = self.filter_widget.get_audio_filter_string()

        if not video_filter_string and not audio_filter_string:
            QMessageBox.information(
                self,
                "Нет фильтров",
                "Добавьте хотя бы один видео или аудио фильтр для применения"
            )
            return

        # Диалог выбора выходного файла
        input_path = Path(input_file)
        default_output = str(input_path.parent / f"{input_path.stem}_filtered{input_path.suffix}")

        output_file, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить отфильтрованное видео",
            default_output,
            f"Видео файлы (*{input_path.suffix});;Все файлы (*.*)"
        )

        if not output_file:
            return  # Пользователь отменил

        try:
            # Строим команду для быстрого применения фильтров
            cmd = self._build_quick_filter_command(input_file, output_file, video_filter_string, audio_filter_string)

            logger.info(f"Быстрое применение фильтров: {input_file} -> {output_file}")
            logger.info(f"Команда FFmpeg: {' '.join(cmd)}")

            # Запускаем конвертацию
            self.conversion_engine = ConversionEngine(cmd, None)
            self.conversion_thread = QThread()
            self.conversion_engine.moveToThread(self.conversion_thread)

            self.conversion_engine.progress_updated.connect(self.progress_widget.update_progress)
            self.conversion_engine.conversion_finished.connect(self._on_quick_filter_finished)
            self.conversion_engine.conversion_error.connect(self._on_conversion_error)
            self.conversion_thread.started.connect(self.conversion_engine.start)

            self.progress_widget.show_progress()
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.quick_apply_button.setEnabled(False)
            self.statusBar().showMessage("⚡ Применение фильтров...")

            self.conversion_thread.start()

        except Exception as e:
            error_msg = f"Ошибка применения фильтров: {e}"
            logger.error(error_msg, exc_info=True)
            QMessageBox.critical(self, "Ошибка", error_msg)

    def _build_quick_filter_command(self, input_file: str, output_file: str,
                                   video_filter_string: Optional[str],
                                   audio_filter_string: Optional[str]) -> List[str]:
        """
        Построить команду FFmpeg для быстрого применения фильтров
        Использует stream copy где возможно для минимизации перекодирования
        """
        cmd = [self.ffmpeg_manager.ffmpeg_path]

        # Перезапись выходного файла без запроса
        cmd.append("-y")

        # Нормализуем пути для Windows (используем обратные слэши)
        input_file_normalized = str(Path(input_file).resolve())
        output_file_normalized = str(Path(output_file).resolve())

        # Входной файл
        cmd.extend(["-i", input_file_normalized])

        # Видео кодек
        if video_filter_string:
            # Если есть видео фильтры - нужно перекодировать видео
            # Используем быстрые настройки для минимизации времени
            input_path = Path(input_file)
            output_format = input_path.suffix.lstrip('.')

            # Определяем оптимальный кодек для формата
            if output_format.lower() in ['mp4', 'm4v']:
                video_codec = 'libx264'
                cmd.extend(["-c:v", video_codec, "-preset", "fast", "-crf", "18"])
            elif output_format.lower() == 'webm':
                video_codec = 'libvpx-vp9'
                cmd.extend(["-c:v", video_codec, "-crf", "18", "-b:v", "0", "-cpu-used", "4"])
            elif output_format.lower() in ['mkv', 'avi', 'mov']:
                video_codec = 'libx264'
                cmd.extend(["-c:v", video_codec, "-preset", "fast", "-crf", "18"])
            else:
                # Универсальный вариант
                cmd.extend(["-c:v", "libx264", "-preset", "fast", "-crf", "18"])

            # Применяем видео фильтры
            cmd.extend(["-vf", video_filter_string])
            logger.info(f"Quick filter: применение видео фильтров: {video_filter_string}")
        else:
            # Нет видео фильтров - копируем поток
            cmd.extend(["-c:v", "copy"])
            logger.info("Quick filter: копирование видео потока без изменений")

        # Аудио кодек
        if audio_filter_string:
            # Если есть аудио фильтры - нужно перекодировать аудио
            cmd.extend(["-c:a", "aac", "-b:a", "192k"])
            cmd.extend(["-af", audio_filter_string])
            logger.info(f"Quick filter: применение аудио фильтров: {audio_filter_string}")
        else:
            # Нет аудио фильтров - копируем поток
            cmd.extend(["-c:a", "copy"])
            logger.info("Quick filter: копирование аудио потока без изменений")

        # Копируем метаданные
        cmd.extend(["-map_metadata", "0"])

        # Выходной файл (используем нормализованный путь)
        cmd.append(output_file_normalized)

        return cmd

    def _on_quick_filter_finished(self):
        """Обработка завершения быстрого применения фильтров"""
        self._reset_ui()
        self.quick_apply_button.setEnabled(True)
        self.statusBar().showMessage("✓ Фильтры применены успешно!", 5000)
        QMessageBox.information(self, "Успех", "Фильтры применены успешно!")
        logger.info("Быстрое применение фильтров завершено")

    def _on_conversion_finished(self):
        """Обработка завершения конвертации"""
        # Корректно завершаем поток
        if self.conversion_thread and self.conversion_thread.isRunning():
            self.conversion_thread.quit()
            self.conversion_thread.wait()
        self.conversion_thread = None
        self.conversion_engine = None

        self._reset_ui()
        self.statusBar().showMessage("✓ Конвертация завершена!", 5000)
        QMessageBox.information(self, "Успех", "Конвертация завершена успешно!")

    def _on_conversion_error(self, error):
        """Обработка ошибки конвертации"""
        # Корректно завершаем поток
        if self.conversion_thread and self.conversion_thread.isRunning():
            self.conversion_thread.quit()
            self.conversion_thread.wait()
        self.conversion_thread = None
        self.conversion_engine = None

        self._reset_ui()
        self.statusBar().showMessage(f"✗ Ошибка: {error}", 10000)
        QMessageBox.critical(self, "Ошибка", f"Ошибка конвертации:\n{error}")
    
    def _reset_ui(self):
        """Сброс UI"""
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.quick_apply_button.setEnabled(True)
        self.progress_widget.hide_progress()

        # Потоки должны быть уже завершены в _stop_conversion
        # Но на всякий случай проверяем
        if self.conversion_thread and self.conversion_thread.isRunning():
            logger.warning("Поток конвертации все еще работает в _reset_ui")
            self.conversion_thread.quit()
            self.conversion_thread.wait(3000)

        if self.batch_thread and self.batch_thread.isRunning():
            logger.warning("Поток batch все еще работает в _reset_ui")
            self.batch_thread.quit()
            self.batch_thread.wait(3000)
    
    def _apply_theme(self):
        """Применить тему при запуске"""
        from .styles.modern_theme import ModernTheme

        if self.current_theme == "auto":
            # Определяем системную тему
            theme_mode = self._detect_system_theme()
            logger.info(f"Автоопределение темы: {theme_mode}")
        else:
            theme_mode = self.current_theme

        theme_obj = ModernTheme(theme_mode)
        self.setStyleSheet(theme_obj.get_stylesheet())
        logger.info(f"Применена тема: {theme_mode}")

    def _detect_system_theme(self) -> str:
        """Определить системную тему"""
        import sys
        import platform

        # Windows
        if sys.platform == "win32":
            try:
                import winreg
                registry = winreg.ConnectRegistry(None, winreg.HKEY_CURRENT_USER)
                key = winreg.OpenKey(
                    registry,
                    r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
                )
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
                winreg.CloseKey(key)
                return "light" if value == 1 else "dark"
            except Exception as e:
                logger.warning(f"Не удалось определить тему Windows: {e}")

        # macOS
        elif sys.platform == "darwin":
            try:
                import subprocess
                result = subprocess.run(
                    ["defaults", "read", "-g", "AppleInterfaceStyle"],
                    capture_output=True,
                    text=True
                )
                return "dark" if result.returncode == 0 else "light"
            except Exception as e:
                logger.warning(f"Не удалось определить тему macOS: {e}")

        # Linux / Fallback
        from PySide6.QtGui import QPalette
        palette = self.palette()
        is_dark = palette.color(QPalette.Window).lightness() < 128
        return "dark" if is_dark else "light"

    def _open_settings(self):
        """Открыть окно настроек"""
        dialog = SettingsDialog(self.current_theme, self)
        dialog.theme_changed.connect(self._on_theme_changed)

        if dialog.exec():
            logger.info("Настройки сохранены")

    def _open_logger(self):
        """Открыть окно логирования"""
        if self.logger_widget is None or not self.logger_widget.isVisible():
            self.logger_widget = LoggerWidget(self)
            self.logger_widget.show()
        else:
            self.logger_widget.raise_()
            self.logger_widget.activateWindow()

    def _show_about(self):
        """Показать окно О программе"""
        from PySide6.QtWidgets import QMessageBox

        about_text = """
        <h2>FFmpeg UI 2.0</h2>
        <p><b>Мощное и удобное десктопное приложение, предоставляющее современный графический интерфейс для конвертации видео через FFmpeg.</b></p>
        <p>Версия: 1.1</p>

        <p><b>Возможности:</b></p>
        <ul>
        <li>🎬 Поддержка всех популярных форматов видео</li>
        <li>🚀 GPU ускорение (NVIDIA, Intel QSV, AMD AMF)</li>
        <li>🎨 Расширенные фильтры и эффекты</li>
        <li>📊 Превью видео с live-фильтрами</li>
        <li>⚡ Пакетная конвертация</li>
        <li>✂️ Обрезка и склейка видео</li>
        <li>📝 Редактор метаданных</li>
        <li>💬 Работа с субтитрами</li>
        </ul>

        <p><b>Технологии:</b> Python, PySide6, FFmpeg</p>
        <p><b>Лицензия:</b> GPLv3</p>
        """

        QMessageBox.about(self, "О программе", about_text)

    def _show_shortcuts(self):
        """Показать окно с горячими клавишами"""
        from PySide6.QtWidgets import QMessageBox

        shortcuts_text = """
        <h2>Горячие клавиши</h2>

        <p><b>🛠 Инструменты:</b></p>
        <ul>
        <li><b>Ctrl+L</b> - Просмотр логов</li>
        <li><b>Ctrl+,</b> - Настройки</li>
        <li><b>Ctrl+Q</b> - Выход из программы</li>
        </ul>

        <p><b>👁 Основные вкладки:</b></p>
        <ul>
        <li><b>Ctrl+1</b> - Файлы</li>
        <li><b>Ctrl+2</b> - Превью</li>
        <li><b>Ctrl+3</b> - Видео</li>
        <li><b>Ctrl+4</b> - Аудио</li>
        <li><b>Ctrl+5</b> - Дополнительно</li>
        </ul>

        <p><b>👁 Расширенные вкладки:</b></p>
        <ul>
        <li><b>Ctrl+6</b> - Потоки</li>
        <li><b>Ctrl+7</b> - Обрезка</li>
        <li><b>Ctrl+8</b> - Метаданные</li>
        <li><b>Ctrl+9</b> - Субтитры</li>
        <li><b>Ctrl+0</b> - Изображения</li>
        <li><b>Alt+1</b> - Главы</li>
        <li><b>Alt+2</b> - Объединение</li>
        </ul>

        <p><b>❓ Помощь:</b></p>
        <ul>
        <li><b>F1</b> - Показать горячие клавиши</li>
        </ul>
        """

        QMessageBox.information(self, "Горячие клавиши", shortcuts_text)

    def _toggle_advanced_mode(self):
        """Переключение расширенного режима (скрыть/показать дополнительные вкладки)"""
        is_advanced = self.advanced_mode_action.isChecked()

        # Индексы расширенных вкладок (с 5 по 11)
        # 0-4: Основные (Файлы, Превью, Видео, Аудио, Дополнительно)
        # 5-11: Расширенные (Потоки, Обрезка, Метаданные, Субтитры, Изображения, Главы, Объединение)
        advanced_tab_indices = [5, 6, 7, 8, 9, 10, 11]

        if is_advanced:
            # Показать все расширенные вкладки
            for i in advanced_tab_indices:
                self.tabs.setTabVisible(i, True)
        else:
            # Скрыть расширенные вкладки
            current_index = self.tabs.currentIndex()
            for i in advanced_tab_indices:
                self.tabs.setTabVisible(i, False)

            # Если текущая вкладка была расширенной, переключиться на основную
            if current_index in advanced_tab_indices:
                self.tabs.setCurrentIndex(0)  # Переключиться на "Файлы"

        # Сохранить настройку
        self.settings.setValue("advanced_mode", is_advanced)
        logger.info(f"Расширенный режим: {'включен' if is_advanced else 'выключен'}")

    def _on_theme_changed(self, theme: str):
        """Обработка изменения темы"""
        self.current_theme = theme
        self.settings.setValue("theme", theme)

        # Применяем тему
        from .styles.modern_theme import ModernTheme

        if theme == "auto":
            # Определяем системную тему
            theme_mode = self._detect_system_theme()
        else:
            theme_mode = theme

        theme_obj = ModernTheme(theme_mode)
        self.setStyleSheet(theme_obj.get_stylesheet())

        logger.info(f"Тема изменена на: {theme}")

        # Информируем пользователя
        QMessageBox.information(
            self,
            "Тема изменена",
            f"Тема успешно изменена на '{theme}'."
        )

    def closeEvent(self, event):
        """Обработка закрытия окна"""
        # Останавливаем конвертацию перед закрытием
        if self.conversion_engine:
            self.conversion_engine.stop()

        if self.batch_processor:
            self.batch_processor.stop()

        # Корректно завершаем потоки
        if self.conversion_thread and self.conversion_thread.isRunning():
            logger.info("Завершаем поток конвертации при закрытии...")
            self.conversion_thread.quit()
            if not self.conversion_thread.wait(5000):
                logger.warning("Поток конвертации не завершился, принудительное завершение")
                self.conversion_thread.terminate()
                self.conversion_thread.wait()

        if self.batch_thread and self.batch_thread.isRunning():
            logger.info("Завершаем поток batch при закрытии...")
            self.batch_thread.quit()
            if not self.batch_thread.wait(5000):
                logger.warning("Поток batch не завершился, принудительное завершение")
                self.batch_thread.terminate()
                self.batch_thread.wait()

        # Закрываем окно логирования
        if self.logger_widget:
            self.logger_widget.close()

        event.accept()
        logger.info("Приложение закрыто")