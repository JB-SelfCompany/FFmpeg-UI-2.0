"""
Виджет для работы с изображениями и последовательностями
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QComboBox, QSpinBox, QGroupBox, QGridLayout,
    QFileDialog, QRadioButton, QButtonGroup, QDoubleSpinBox,
    QTextEdit, QCheckBox, QTabWidget
)
from PySide6.QtCore import Qt, Signal
from pathlib import Path
import logging

from core.image_sequence import (
    TransitionType, ImageFormat, ImageSequenceManager,
    ImageSequenceConfig, FrameExtractionConfig
)

logger = logging.getLogger(__name__)


class ImageSequenceWidget(QWidget):
    """Виджет для работы с последовательностями изображений"""

    # Сигналы
    create_video_requested = Signal(object)  # ImageSequenceConfig
    extract_frames_requested = Signal(object)  # FrameExtractionConfig

    def __init__(self):
        super().__init__()
        self.manager = ImageSequenceManager()
        self._init_ui()

    def _init_ui(self):
        """Инициализация UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Tabs для разных режимов
        tabs = QTabWidget()
        tabs.addTab(self._create_images_to_video_tab(), "📸→🎬 Изображения → Видео")
        tabs.addTab(self._create_video_to_images_tab(), "🎬→📸 Видео → Изображения")
        tabs.addTab(self._create_slideshow_tab(), "🖼️ Слайдшоу")

        layout.addWidget(tabs)

    def _create_images_to_video_tab(self) -> QWidget:
        """Вкладка: создание видео из последовательности изображений"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(5)

        # Группа: Входные данные
        input_group = QGroupBox("Входные изображения")
        input_layout = QGridLayout(input_group)
        input_layout.setSpacing(5)

        row = 0
        input_layout.addWidget(QLabel("Папка:"), row, 0)
        self.seq_folder_edit = QLineEdit()
        self.seq_folder_edit.setPlaceholderText("Выберите папку с изображениями")
        input_layout.addWidget(self.seq_folder_edit, row, 1)

        seq_browse_btn = QPushButton("Обзор...")
        seq_browse_btn.clicked.connect(self._browse_sequence_folder)
        input_layout.addWidget(seq_browse_btn, row, 2)

        seq_detect_btn = QPushButton("🔍 Авто")
        seq_detect_btn.setToolTip("Автоматически определить последовательность")
        seq_detect_btn.clicked.connect(self._auto_detect_sequence)
        input_layout.addWidget(seq_detect_btn, row, 3)

        row += 1
        input_layout.addWidget(QLabel("Паттерн:"), row, 0)
        self.seq_pattern_edit = QLineEdit()
        self.seq_pattern_edit.setPlaceholderText("image-%03d.png")
        self.seq_pattern_edit.setToolTip(
            "Паттерн имени файлов:\n"
            "• %03d = трехзначное число (001, 002, ...)\n"
            "• %04d = четырехзначное число (0001, 0002, ...)\n"
            "Пример: frame-%04d.jpg"
        )
        input_layout.addWidget(self.seq_pattern_edit, row, 1, 1, 3)

        row += 1
        input_layout.addWidget(QLabel("Начальный номер:"), row, 0)
        self.seq_start_number = QSpinBox()
        self.seq_start_number.setMinimum(0)
        self.seq_start_number.setMaximum(999999)
        self.seq_start_number.setValue(0)
        self.seq_start_number.setToolTip("Первый номер в последовательности")
        input_layout.addWidget(self.seq_start_number, row, 1)

        # Информация о найденных файлах
        row += 1
        self.seq_info_label = QLabel("")
        self.seq_info_label.setStyleSheet("color: #2196F3; font-size: 9px;")
        self.seq_info_label.setWordWrap(True)
        input_layout.addWidget(self.seq_info_label, row, 0, 1, 4)

        layout.addWidget(input_group)

        # Группа: Настройки видео
        video_group = QGroupBox("Настройки видео")
        video_layout = QGridLayout(video_group)
        video_layout.setSpacing(5)

        row = 0
        video_layout.addWidget(QLabel("FPS:"), row, 0)
        self.seq_fps = QSpinBox()
        self.seq_fps.setMinimum(1)
        self.seq_fps.setMaximum(240)
        self.seq_fps.setValue(25)
        self.seq_fps.setToolTip("Частота кадров выходного видео")
        video_layout.addWidget(self.seq_fps, row, 1)

        video_layout.addWidget(QLabel("Кодек:"), row, 2)
        self.seq_codec = QComboBox()
        self.seq_codec.addItems([
            "libx264 (H.264)",
            "libx265 (H.265)",
            "libvpx-vp9 (VP9)",
            "libaom-av1 (AV1)",
            "gif (GIF)",
            "apng (Animated PNG)"
        ])
        video_layout.addWidget(self.seq_codec, row, 3)

        row += 1
        video_layout.addWidget(QLabel("Разрешение:"), row, 0)
        self.seq_resolution = QComboBox()
        self.seq_resolution.addItems([
            "Исходное",
            "3840x2160 (4K)",
            "2560x1440 (2K)",
            "1920x1080 (FHD)",
            "1280x720 (HD)",
            "854x480 (SD)"
        ])
        video_layout.addWidget(self.seq_resolution, row, 1)

        video_layout.addWidget(QLabel("CRF:"), row, 2)
        self.seq_crf = QSpinBox()
        self.seq_crf.setMinimum(0)
        self.seq_crf.setMaximum(51)
        self.seq_crf.setValue(23)
        self.seq_crf.setToolTip("Качество (меньше = лучше)")
        video_layout.addWidget(self.seq_crf, row, 3)

        layout.addWidget(video_group)

        # Группа: Выходной файл
        output_group = QGroupBox("Выходной файл")
        output_layout = QHBoxLayout(output_group)
        output_layout.setSpacing(5)

        self.seq_output_edit = QLineEdit()
        self.seq_output_edit.setPlaceholderText("output.mp4")
        output_layout.addWidget(self.seq_output_edit)

        seq_output_btn = QPushButton("Сохранить как...")
        seq_output_btn.clicked.connect(lambda: self._browse_output_file(self.seq_output_edit))
        output_layout.addWidget(seq_output_btn)

        layout.addWidget(output_group)

        # Кнопка создания
        create_btn = QPushButton("▶ Создать видео")
        create_btn.setMinimumHeight(40)
        create_btn.clicked.connect(self._create_video_from_images)
        layout.addWidget(create_btn)

        layout.addStretch()
        return widget

    def _create_video_to_images_tab(self) -> QWidget:
        """Вкладка: извлечение кадров из видео"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(5)

        # Группа: Входной файл
        input_group = QGroupBox("Входное видео")
        input_layout = QHBoxLayout(input_group)
        input_layout.setSpacing(5)

        self.extract_input_edit = QLineEdit()
        self.extract_input_edit.setPlaceholderText("Выберите видео файл")
        input_layout.addWidget(self.extract_input_edit)

        extract_browse_btn = QPushButton("Обзор...")
        extract_browse_btn.clicked.connect(self._browse_video_file)
        input_layout.addWidget(extract_browse_btn)

        layout.addWidget(input_group)

        # Группа: Настройки извлечения
        settings_group = QGroupBox("Настройки извлечения")
        settings_layout = QGridLayout(settings_group)
        settings_layout.setSpacing(5)

        row = 0
        settings_layout.addWidget(QLabel("Формат:"), row, 0)
        self.extract_format = QComboBox()
        self.extract_format.addItems(["PNG", "JPEG", "BMP", "TIFF", "WEBP"])
        settings_layout.addWidget(self.extract_format, row, 1)

        settings_layout.addWidget(QLabel("Качество (JPEG):"), row, 2)
        self.extract_quality = QSpinBox()
        self.extract_quality.setMinimum(2)
        self.extract_quality.setMaximum(31)
        self.extract_quality.setValue(2)
        self.extract_quality.setToolTip("Только для JPEG (меньше = лучше)")
        settings_layout.addWidget(self.extract_quality, row, 3)

        row += 1
        self.extract_fps_checkbox = QCheckBox("Извлечь с FPS:")
        settings_layout.addWidget(self.extract_fps_checkbox, row, 0)
        self.extract_fps = QDoubleSpinBox()
        self.extract_fps.setMinimum(0.01)
        self.extract_fps.setMaximum(240)
        self.extract_fps.setValue(1.0)
        self.extract_fps.setDecimals(2)
        self.extract_fps.setSuffix(" fps")
        self.extract_fps.setToolTip("1 fps = 1 кадр в секунду")
        self.extract_fps.setEnabled(False)
        self.extract_fps_checkbox.toggled.connect(self.extract_fps.setEnabled)
        settings_layout.addWidget(self.extract_fps, row, 1)

        settings_layout.addWidget(QLabel("Масштаб:"), row, 2)
        self.extract_scale = QComboBox()
        self.extract_scale.addItems([
            "Исходный",
            "1920x1080",
            "1280x720",
            "854x480"
        ])
        settings_layout.addWidget(self.extract_scale, row, 3)

        row += 1
        self.extract_time_checkbox = QCheckBox("Временной диапазон:")
        settings_layout.addWidget(self.extract_time_checkbox, row, 0)

        time_layout = QHBoxLayout()
        time_layout.addWidget(QLabel("от"))
        self.extract_start = QDoubleSpinBox()
        self.extract_start.setMinimum(0)
        self.extract_start.setMaximum(999999)
        self.extract_start.setSuffix(" сек")
        self.extract_start.setEnabled(False)
        time_layout.addWidget(self.extract_start)

        time_layout.addWidget(QLabel("до"))
        self.extract_end = QDoubleSpinBox()
        self.extract_end.setMinimum(0)
        self.extract_end.setMaximum(999999)
        self.extract_end.setSuffix(" сек")
        self.extract_end.setEnabled(False)
        time_layout.addWidget(self.extract_end)

        self.extract_time_checkbox.toggled.connect(self.extract_start.setEnabled)
        self.extract_time_checkbox.toggled.connect(self.extract_end.setEnabled)

        settings_layout.addLayout(time_layout, row, 1, 1, 3)

        layout.addWidget(settings_group)

        # Группа: Выходные файлы
        output_group = QGroupBox("Выходные файлы")
        output_layout = QGridLayout(output_group)
        output_layout.setSpacing(5)

        row = 0
        output_layout.addWidget(QLabel("Папка:"), row, 0)
        self.extract_output_folder = QLineEdit()
        self.extract_output_folder.setPlaceholderText("Выберите папку для сохранения кадров")
        output_layout.addWidget(self.extract_output_folder, row, 1)

        extract_folder_btn = QPushButton("Обзор...")
        extract_folder_btn.clicked.connect(self._browse_output_folder)
        output_layout.addWidget(extract_folder_btn, row, 2)

        row += 1
        output_layout.addWidget(QLabel("Паттерн имени:"), row, 0)
        self.extract_pattern = QLineEdit()
        self.extract_pattern.setText("frame-%04d.png")
        self.extract_pattern.setToolTip("Паттерн имени файлов (например, frame-%04d.png)")
        output_layout.addWidget(self.extract_pattern, row, 1, 1, 2)

        layout.addWidget(output_group)

        # Кнопка извлечения
        extract_btn = QPushButton("▶ Извлечь кадры")
        extract_btn.setMinimumHeight(40)
        extract_btn.clicked.connect(self._extract_frames_from_video)
        layout.addWidget(extract_btn)

        layout.addStretch()
        return widget

    def _create_slideshow_tab(self) -> QWidget:
        """Вкладка: создание слайдшоу с переходами"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(5)

        # Группа: Файлы изображений
        files_group = QGroupBox("Изображения для слайдшоу")
        files_layout = QVBoxLayout(files_group)

        btn_layout = QHBoxLayout()
        add_files_btn = QPushButton("➕ Добавить файлы")
        add_files_btn.clicked.connect(self._add_slideshow_images)
        btn_layout.addWidget(add_files_btn)

        add_folder_btn = QPushButton("📁 Добавить папку")
        add_folder_btn.clicked.connect(self._add_slideshow_folder)
        btn_layout.addWidget(add_folder_btn)

        clear_btn = QPushButton("🗑️ Очистить")
        clear_btn.clicked.connect(self._clear_slideshow_images)
        btn_layout.addWidget(clear_btn)

        btn_layout.addStretch()
        files_layout.addLayout(btn_layout)

        self.slideshow_files_list = QTextEdit()
        self.slideshow_files_list.setMaximumHeight(150)
        self.slideshow_files_list.setReadOnly(True)
        self.slideshow_files_list.setPlaceholderText("Список изображений будет отображаться здесь")
        files_layout.addWidget(self.slideshow_files_list)

        self.slideshow_files = []  # Хранилище путей

        layout.addWidget(files_group)

        # Группа: Настройки слайдшоу
        settings_group = QGroupBox("Настройки слайдшоу")
        settings_layout = QGridLayout(settings_group)
        settings_layout.setSpacing(5)

        row = 0
        settings_layout.addWidget(QLabel("Длительность кадра:"), row, 0)
        self.slideshow_duration = QDoubleSpinBox()
        self.slideshow_duration.setMinimum(0.1)
        self.slideshow_duration.setMaximum(60.0)
        self.slideshow_duration.setValue(3.0)
        self.slideshow_duration.setSuffix(" сек")
        self.slideshow_duration.setDecimals(1)
        settings_layout.addWidget(self.slideshow_duration, row, 1)

        settings_layout.addWidget(QLabel("Переход:"), row, 2)
        self.slideshow_transition = QComboBox()
        self.slideshow_transition.addItems([
            "Fade (затухание)",
            "Wipe Left (шторка влево)",
            "Wipe Right (шторка вправо)",
            "Wipe Up (шторка вверх)",
            "Wipe Down (шторка вниз)",
            "Slide Left (сдвиг влево)",
            "Slide Right (сдвиг вправо)",
            "Circle Crop (круг)",
            "Dissolve (растворение)"
        ])
        settings_layout.addWidget(self.slideshow_transition, row, 3)

        row += 1
        settings_layout.addWidget(QLabel("Длительность перехода:"), row, 0)
        self.slideshow_transition_duration = QDoubleSpinBox()
        self.slideshow_transition_duration.setMinimum(0.1)
        self.slideshow_transition_duration.setMaximum(5.0)
        self.slideshow_transition_duration.setValue(1.0)
        self.slideshow_transition_duration.setSuffix(" сек")
        self.slideshow_transition_duration.setDecimals(1)
        settings_layout.addWidget(self.slideshow_transition_duration, row, 1)

        settings_layout.addWidget(QLabel("Разрешение:"), row, 2)
        self.slideshow_resolution = QComboBox()
        self.slideshow_resolution.addItems([
            "1920x1080 (FHD)",
            "1280x720 (HD)",
            "3840x2160 (4K)",
            "2560x1440 (2K)"
        ])
        settings_layout.addWidget(self.slideshow_resolution, row, 3)

        row += 1
        settings_layout.addWidget(QLabel("FPS:"), row, 0)
        self.slideshow_fps = QSpinBox()
        self.slideshow_fps.setMinimum(15)
        self.slideshow_fps.setMaximum(60)
        self.slideshow_fps.setValue(30)
        settings_layout.addWidget(self.slideshow_fps, row, 1)

        settings_layout.addWidget(QLabel("Кодек:"), row, 2)
        self.slideshow_codec = QComboBox()
        self.slideshow_codec.addItems([
            "libx264 (H.264)",
            "libx265 (H.265)",
            "libvpx-vp9 (VP9)"
        ])
        settings_layout.addWidget(self.slideshow_codec, row, 3)

        layout.addWidget(settings_group)

        # Выходной файл
        output_group = QGroupBox("Выходной файл")
        output_layout = QHBoxLayout(output_group)

        self.slideshow_output = QLineEdit()
        self.slideshow_output.setPlaceholderText("slideshow.mp4")
        output_layout.addWidget(self.slideshow_output)

        slideshow_output_btn = QPushButton("Сохранить как...")
        slideshow_output_btn.clicked.connect(lambda: self._browse_output_file(self.slideshow_output))
        output_layout.addWidget(slideshow_output_btn)

        layout.addWidget(output_group)

        # Информация
        self.slideshow_info = QLabel("")
        self.slideshow_info.setStyleSheet("color: #2196F3; font-size: 9px;")
        self.slideshow_info.setWordWrap(True)
        layout.addWidget(self.slideshow_info)

        # Кнопка создания
        create_btn = QPushButton("▶ Создать слайдшоу")
        create_btn.setMinimumHeight(40)
        create_btn.clicked.connect(self._create_slideshow)
        layout.addWidget(create_btn)

        layout.addStretch()
        return widget

    # === Слоты и обработчики ===

    def _browse_sequence_folder(self):
        """Выбор папки с последовательностью изображений"""
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку с изображениями")
        if folder:
            self.seq_folder_edit.setText(folder)

    def _auto_detect_sequence(self):
        """Автоматическое определение последовательности"""
        folder = self.seq_folder_edit.text()
        if not folder:
            self.seq_info_label.setText("❌ Выберите папку")
            return

        result = self.manager.detect_image_sequence(folder)
        if result:
            pattern, start, end, ext = result
            self.seq_pattern_edit.setText(pattern)
            self.seq_start_number.setValue(start)
            count = end - start + 1
            self.seq_info_label.setText(
                f"✅ Найдено {count} изображений ({start}-{end})\n"
                f"Паттерн: {pattern}"
            )
            logger.info(f"Auto-detected sequence: {pattern}, {start}-{end}")
        else:
            self.seq_info_label.setText("❌ Последовательность не обнаружена")

    def _browse_video_file(self):
        """Выбор видео файла для извлечения кадров"""
        file, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите видео файл",
            "",
            "Video Files (*.mp4 *.mkv *.avi *.mov *.webm *.flv);;All Files (*.*)"
        )
        if file:
            self.extract_input_edit.setText(file)

    def _browse_output_folder(self):
        """Выбор папки для сохранения кадров"""
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для сохранения кадров")
        if folder:
            self.extract_output_folder.setText(folder)

    def _browse_output_file(self, line_edit: QLineEdit):
        """Выбор выходного файла"""
        file, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить как",
            "",
            "Video Files (*.mp4 *.mkv *.webm *.avi);;All Files (*.*)"
        )
        if file:
            line_edit.setText(file)

    def _add_slideshow_images(self):
        """Добавить файлы изображений в слайдшоу"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите изображения",
            "",
            "Image Files (*.png *.jpg *.jpeg *.bmp *.tiff *.webp);;All Files (*.*)"
        )
        if files:
            self.slideshow_files.extend(files)
            self._update_slideshow_list()

    def _add_slideshow_folder(self):
        """Добавить все изображения из папки"""
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку с изображениями")
        if folder:
            folder_path = Path(folder)
            for ext in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp']:
                self.slideshow_files.extend([str(f) for f in folder_path.glob(f'*{ext}')])
            self._update_slideshow_list()

    def _clear_slideshow_images(self):
        """Очистить список изображений"""
        self.slideshow_files.clear()
        self._update_slideshow_list()

    def _update_slideshow_list(self):
        """Обновить отображение списка изображений"""
        self.slideshow_files_list.clear()
        for i, file in enumerate(self.slideshow_files, 1):
            self.slideshow_files_list.append(f"{i}. {Path(file).name}")

        # Обновить информацию
        if self.slideshow_files:
            duration = self.manager.estimate_video_duration(
                len(self.slideshow_files),
                self.slideshow_duration.value(),
                self.slideshow_transition_duration.value()
            )
            self.slideshow_info.setText(
                f"📊 Изображений: {len(self.slideshow_files)} | "
                f"Примерная длительность: {duration:.1f} сек"
            )
        else:
            self.slideshow_info.setText("")

    def _create_video_from_images(self):
        """Создать видео из последовательности изображений"""
        folder = self.seq_folder_edit.text()
        pattern = self.seq_pattern_edit.text()
        output = self.seq_output_edit.text()

        if not folder or not pattern or not output:
            logger.warning("Missing input parameters for image sequence")
            return

        # Полный путь к паттерну
        full_pattern = str(Path(folder) / pattern)

        # Получаем codec
        codec_map = {
            "libx264 (H.264)": "libx264",
            "libx265 (H.265)": "libx265",
            "libvpx-vp9 (VP9)": "libvpx-vp9",
            "libaom-av1 (AV1)": "libaom-av1",
            "gif (GIF)": "gif",
            "apng (Animated PNG)": "apng"
        }
        codec = codec_map.get(self.seq_codec.currentText(), "libx264")

        # Разрешение
        resolution = None
        res_text = self.seq_resolution.currentText()
        if res_text != "Исходное":
            width, height = res_text.split()[0].split('x')
            resolution = (int(width), int(height))

        # Создаем конфиг
        config = ImageSequenceConfig(
            input_pattern=full_pattern,
            output_file=output,
            fps=self.seq_fps.value(),
            resolution=resolution,
            codec=codec,
            crf=self.seq_crf.value(),
            start_number=self.seq_start_number.value()
        )

        # Emit signal
        self.create_video_requested.emit(config)
        logger.info(f"Requested video creation from images: {full_pattern} -> {output}")

    def _extract_frames_from_video(self):
        """Извлечь кадры из видео"""
        input_file = self.extract_input_edit.text()
        output_folder = self.extract_output_folder.text()
        pattern = self.extract_pattern.text()

        if not input_file or not output_folder or not pattern:
            logger.warning("Missing input parameters for frame extraction")
            return

        # Полный путь к выходному паттерну
        output_pattern = str(Path(output_folder) / pattern)

        # FPS
        fps = self.extract_fps.value() if self.extract_fps_checkbox.isChecked() else None

        # Временной диапазон
        start_time = self.extract_start.value() if self.extract_time_checkbox.isChecked() else None
        end_time = self.extract_end.value() if self.extract_time_checkbox.isChecked() else None

        # Формат
        format_map = {
            "PNG": ImageFormat.PNG,
            "JPEG": ImageFormat.JPEG,
            "BMP": ImageFormat.BMP,
            "TIFF": ImageFormat.TIFF,
            "WEBP": ImageFormat.WEBP
        }
        image_format = format_map.get(self.extract_format.currentText(), ImageFormat.PNG)

        # Масштаб
        scale = None
        scale_text = self.extract_scale.currentText()
        if scale_text != "Исходный":
            width, height = scale_text.split('x')
            scale = (int(width), int(height))

        # Создаем конфиг
        config = FrameExtractionConfig(
            input_file=input_file,
            output_pattern=output_pattern,
            fps=fps,
            start_time=start_time,
            end_time=end_time,
            image_format=image_format,
            quality=self.extract_quality.value(),
            scale=scale
        )

        # Emit signal
        self.extract_frames_requested.emit(config)
        logger.info(f"Requested frame extraction: {input_file} -> {output_pattern}")

    def _create_slideshow(self):
        """Создать слайдшоу с переходами"""
        if not self.slideshow_files:
            logger.warning("No images selected for slideshow")
            return

        output = self.slideshow_output.text()
        if not output:
            logger.warning("No output file specified for slideshow")
            return

        # Получаем codec
        codec_map = {
            "libx264 (H.264)": "libx264",
            "libx265 (H.265)": "libx265",
            "libvpx-vp9 (VP9)": "libvpx-vp9"
        }
        codec = codec_map.get(self.slideshow_codec.currentText(), "libx264")

        # Разрешение
        res_text = self.slideshow_resolution.currentText()
        width, height = res_text.split()[0].split('x')
        resolution = (int(width), int(height))

        # Переход
        transition_map = {
            "Fade (затухание)": TransitionType.FADE,
            "Wipe Left (шторка влево)": TransitionType.WIPELEFT,
            "Wipe Right (шторка вправо)": TransitionType.WIPERIGHT,
            "Wipe Up (шторка вверх)": TransitionType.WIPEUP,
            "Wipe Down (шторка вниз)": TransitionType.WIPEDOWN,
            "Slide Left (сдвиг влево)": TransitionType.SLIDELEFT,
            "Slide Right (сдвиг вправо)": TransitionType.SLIDERIGHT,
            "Circle Crop (круг)": TransitionType.CIRCLECROP,
            "Dissolve (растворение)": TransitionType.DISSOLVE
        }
        transition = transition_map.get(
            self.slideshow_transition.currentText(),
            TransitionType.FADE
        )

        # Создаем конфиг
        config = ImageSequenceConfig(
            input_pattern=self.slideshow_files,  # Передаем список файлов
            output_file=output,
            fps=self.slideshow_fps.value(),
            resolution=resolution,
            codec=codec,
            crf=23,
            duration_per_image=self.slideshow_duration.value(),
            transition=transition,
            transition_duration=self.slideshow_transition_duration.value()
        )

        # Emit signal
        self.create_video_requested.emit(config)
        logger.info(f"Requested slideshow creation: {len(self.slideshow_files)} images -> {output}")
