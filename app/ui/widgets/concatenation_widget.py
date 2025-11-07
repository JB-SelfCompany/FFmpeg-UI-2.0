"""
Виджет для объединения (конкатенации) видео файлов
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QListWidget, QFileDialog,
    QComboBox, QSpinBox, QCheckBox, QDoubleSpinBox,
    QMessageBox, QListWidgetItem, QMenu
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent
from pathlib import Path
import logging

from core.concatenation import (
    ConcatenationManager, ConcatConfig, ConcatMethod,
    TransitionEffect, VideoClip
)

logger = logging.getLogger(__name__)


class ConcatenationWidget(QWidget):
    """Виджет для объединения видео"""

    # Сигналы
    concat_requested = Signal(object)  # ConcatConfig

    def __init__(self):
        super().__init__()
        self.manager = ConcatenationManager()
        self.clips = []  # Список VideoClip
        self._init_ui()

    def _init_ui(self):
        """Инициализация UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Группа: Список файлов
        files_group = QGroupBox("Видео файлы для объединения")
        files_layout = QVBoxLayout(files_group)

        # Кнопки управления списком
        btn_layout = QHBoxLayout()

        add_files_btn = QPushButton("➕ Добавить файлы")
        add_files_btn.clicked.connect(self._add_files)
        btn_layout.addWidget(add_files_btn)

        remove_btn = QPushButton("➖ Удалить")
        remove_btn.clicked.connect(self._remove_selected)
        btn_layout.addWidget(remove_btn)

        move_up_btn = QPushButton("⬆️ Вверх")
        move_up_btn.clicked.connect(self._move_up)
        btn_layout.addWidget(move_up_btn)

        move_down_btn = QPushButton("⬇️ Вниз")
        move_down_btn.clicked.connect(self._move_down)
        btn_layout.addWidget(move_down_btn)

        clear_btn = QPushButton("🗑️ Очистить")
        clear_btn.clicked.connect(self._clear_list)
        btn_layout.addWidget(clear_btn)

        btn_layout.addStretch()
        files_layout.addLayout(btn_layout)

        # Список файлов
        self.files_list = QListWidget()
        self.files_list.setDragDropMode(QListWidget.InternalMove)
        self.files_list.setSelectionMode(QListWidget.ExtendedSelection)
        self.files_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.files_list.customContextMenuRequested.connect(self._show_context_menu)
        self.files_list.setMinimumHeight(200)
        self.files_list.setToolTip(
            "Порядок файлов определяет порядок объединения.\n"
            "Перетаскивайте файлы для изменения порядка."
        )
        files_layout.addWidget(self.files_list)

        # Информация
        self.files_info_label = QLabel("")
        self.files_info_label.setStyleSheet("color: #2196F3; font-size: 9px;")
        self.files_info_label.setWordWrap(True)
        files_layout.addWidget(self.files_info_label)

        layout.addWidget(files_group)

        # Группа: Настройки объединения
        settings_group = QGroupBox("Настройки объединения")
        settings_layout = QVBoxLayout(settings_group)

        # Метод объединения
        method_layout = QHBoxLayout()
        method_layout.addWidget(QLabel("Метод:"))

        self.method_combo = QComboBox()
        self.method_combo.addItems([
            "Concat Demuxer (быстро, без перекодирования)",
            "Concat Filter (универсальный, с перекодированием)",
            "С переходами (xfade)"
        ])
        self.method_combo.setCurrentIndex(1)  # Filter по умолчанию
        self.method_combo.setToolTip(
            "• Demuxer - быстрый, но требует одинаковый формат всех файлов\n"
            "• Filter - универсальный, работает с любыми форматами\n"
            "• С переходами - добавляет визуальные эффекты между клипами"
        )
        self.method_combo.currentIndexChanged.connect(self._on_method_changed)
        method_layout.addWidget(self.method_combo, stretch=1)

        settings_layout.addLayout(method_layout)

        # Опции для переходов (скрыты по умолчанию)
        self.transition_widget = QWidget()
        transition_layout = QHBoxLayout(self.transition_widget)
        transition_layout.setContentsMargins(0, 0, 0, 0)

        transition_layout.addWidget(QLabel("Переход:"))
        self.transition_combo = QComboBox()
        self.transition_combo.addItems([
            "Fade (затухание)",
            "Fade Black (через черный)",
            "Fade White (через белый)",
            "Wipe Left (шторка влево)",
            "Wipe Right (шторка вправо)",
            "Slide Left (сдвиг влево)",
            "Slide Right (сдвиг вправо)",
            "Dissolve (растворение)",
            "Pixelize (пикселизация)",
            "Radial (радиальный)"
        ])
        transition_layout.addWidget(self.transition_combo)

        transition_layout.addWidget(QLabel("Длительность:"))
        self.transition_duration = QDoubleSpinBox()
        self.transition_duration.setMinimum(0.1)
        self.transition_duration.setMaximum(5.0)
        self.transition_duration.setValue(1.0)
        self.transition_duration.setSuffix(" сек")
        self.transition_duration.setDecimals(1)
        transition_layout.addWidget(self.transition_duration)

        transition_layout.addStretch()

        self.transition_widget.setVisible(False)
        settings_layout.addWidget(self.transition_widget)

        # Разрешение выхода
        resolution_layout = QHBoxLayout()
        resolution_layout.addWidget(QLabel("Разрешение:"))

        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            "Как у первого файла",
            "3840x2160 (4K)",
            "2560x1440 (2K)",
            "1920x1080 (FHD)",
            "1280x720 (HD)"
        ])
        self.resolution_combo.setToolTip("Разрешение выходного видео")
        resolution_layout.addWidget(self.resolution_combo)

        resolution_layout.addWidget(QLabel("FPS:"))
        self.fps_spinbox = QSpinBox()
        self.fps_spinbox.setMinimum(0)
        self.fps_spinbox.setMaximum(120)
        self.fps_spinbox.setValue(0)
        self.fps_spinbox.setSpecialValueText("Авто")
        self.fps_spinbox.setToolTip("Частота кадров (0 = как у первого файла)")
        resolution_layout.addWidget(self.fps_spinbox)

        resolution_layout.addStretch()
        settings_layout.addLayout(resolution_layout)

        # Кодеки
        codec_layout = QHBoxLayout()
        codec_layout.addWidget(QLabel("Видео кодек:"))

        self.video_codec = QComboBox()
        self.video_codec.addItems([
            "libx264 (H.264)",
            "libx265 (H.265)",
            "libvpx-vp9 (VP9)"
        ])
        codec_layout.addWidget(self.video_codec)

        codec_layout.addWidget(QLabel("CRF:"))
        self.crf_spinbox = QSpinBox()
        self.crf_spinbox.setMinimum(0)
        self.crf_spinbox.setMaximum(51)
        self.crf_spinbox.setValue(23)
        self.crf_spinbox.setToolTip("Качество (меньше = лучше)")
        codec_layout.addWidget(self.crf_spinbox)

        codec_layout.addWidget(QLabel("Аудио:"))
        self.audio_codec = QComboBox()
        self.audio_codec.addItems(["aac", "libmp3lame", "libopus"])
        codec_layout.addWidget(self.audio_codec)

        codec_layout.addWidget(QLabel("Битрейт:"))
        self.audio_bitrate = QComboBox()
        self.audio_bitrate.addItems(["128k", "192k", "256k", "320k"])
        self.audio_bitrate.setCurrentText("192k")
        codec_layout.addWidget(self.audio_bitrate)

        codec_layout.addStretch()
        settings_layout.addLayout(codec_layout)

        # Опции
        options_layout = QHBoxLayout()
        self.create_chapters_checkbox = QCheckBox("Создать главы для каждого файла")
        self.create_chapters_checkbox.setChecked(True)
        self.create_chapters_checkbox.setToolTip(
            "Автоматически создать главы в выходном файле,\n"
            "по одной на каждый объединенный клип"
        )
        options_layout.addWidget(self.create_chapters_checkbox)
        options_layout.addStretch()

        settings_layout.addLayout(options_layout)

        layout.addWidget(settings_group)

        # Выходной файл
        output_group = QGroupBox("Выходной файл")
        output_layout = QHBoxLayout(output_group)

        self.output_edit = QLineEdit()
        self.output_edit.setPlaceholderText("merged_video.mp4")
        output_layout.addWidget(self.output_edit)

        output_btn = QPushButton("Сохранить как...")
        output_btn.clicked.connect(self._browse_output_file)
        output_layout.addWidget(output_btn)

        layout.addWidget(output_group)

        # Кнопка объединения
        concat_btn = QPushButton("▶ Объединить видео")
        concat_btn.setMinimumHeight(40)
        concat_btn.clicked.connect(self._concat_videos)
        layout.addWidget(concat_btn)

    def _add_files(self):
        """Добавить файлы"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите видео файлы",
            "",
            "Video Files (*.mp4 *.mkv *.avi *.mov *.webm *.flv *.ts *.m2ts);;All Files (*.*)"
        )

        if files:
            for file in files:
                clip = VideoClip(file_path=file)
                self.clips.append(clip)

                item = QListWidgetItem(f"{len(self.clips)}. {Path(file).name}")
                item.setToolTip(file)
                self.files_list.addItem(item)

            self._update_info()
            logger.info(f"Added {len(files)} files to concat list")

    def _remove_selected(self):
        """Удалить выбранные файлы"""
        selected_rows = sorted([item.row() for item in self.files_list.selectedItems()], reverse=True)

        for row in selected_rows:
            self.files_list.takeItem(row)
            del self.clips[row]

        self._renumber_items()
        self._update_info()

    def _move_up(self):
        """Переместить файл вверх"""
        current_row = self.files_list.currentRow()
        if current_row > 0:
            # Меняем в списке
            self.clips[current_row], self.clips[current_row - 1] = \
                self.clips[current_row - 1], self.clips[current_row]

            # Меняем в UI
            item = self.files_list.takeItem(current_row)
            self.files_list.insertItem(current_row - 1, item)
            self.files_list.setCurrentRow(current_row - 1)

            self._renumber_items()

    def _move_down(self):
        """Переместить файл вниз"""
        current_row = self.files_list.currentRow()
        if current_row < self.files_list.count() - 1:
            # Меняем в списке
            self.clips[current_row], self.clips[current_row + 1] = \
                self.clips[current_row + 1], self.clips[current_row]

            # Меняем в UI
            item = self.files_list.takeItem(current_row)
            self.files_list.insertItem(current_row + 1, item)
            self.files_list.setCurrentRow(current_row + 1)

            self._renumber_items()

    def _clear_list(self):
        """Очистить список"""
        self.files_list.clear()
        self.clips.clear()
        self._update_info()

    def _renumber_items(self):
        """Перенумеровать элементы списка"""
        for i in range(self.files_list.count()):
            item = self.files_list.item(i)
            file_path = self.clips[i].file_path
            item.setText(f"{i + 1}. {Path(file_path).name}")

    def _update_info(self):
        """Обновить информационную метку"""
        count = len(self.clips)
        if count == 0:
            self.files_info_label.setText("")
        elif count == 1:
            self.files_info_label.setText("⚠️ Требуется минимум 2 файла для объединения")
        else:
            self.files_info_label.setText(f"✅ Готово {count} файлов к объединению")

    def _on_method_changed(self, index):
        """Обработка изменения метода объединения"""
        # Показываем опции переходов только для метода "С переходами"
        self.transition_widget.setVisible(index == 2)

        # Для Demuxer отключаем опции кодеков (они не используются)
        is_demuxer = (index == 0)
        self.video_codec.setEnabled(not is_demuxer)
        self.crf_spinbox.setEnabled(not is_demuxer)
        self.audio_codec.setEnabled(not is_demuxer)
        self.audio_bitrate.setEnabled(not is_demuxer)
        self.resolution_combo.setEnabled(not is_demuxer)
        self.fps_spinbox.setEnabled(not is_demuxer)

    def _browse_output_file(self):
        """Выбор выходного файла"""
        file, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить объединенное видео",
            "merged_video.mp4",
            "Video Files (*.mp4 *.mkv *.webm);;All Files (*.*)"
        )
        if file:
            self.output_edit.setText(file)

    def _concat_videos(self):
        """Объединить видео"""
        if len(self.clips) < 2:
            QMessageBox.warning(
                self,
                "Предупреждение",
                "Добавьте минимум 2 файла для объединения"
            )
            return

        output_file = self.output_edit.text()
        if not output_file:
            QMessageBox.warning(
                self,
                "Предупреждение",
                "Укажите выходной файл"
            )
            return

        # Определяем метод
        method_index = self.method_combo.currentIndex()
        if method_index == 0:
            method = ConcatMethod.DEMUXER
        elif method_index == 1:
            method = ConcatMethod.FILTER
        else:
            method = ConcatMethod.FILTER_WITH_TRANSITION

        # Переход
        transition = None
        if method == ConcatMethod.FILTER_WITH_TRANSITION:
            transition_map = {
                "Fade (затухание)": TransitionEffect.FADE,
                "Fade Black (через черный)": TransitionEffect.FADEBLACK,
                "Fade White (через белый)": TransitionEffect.FADEWHITE,
                "Wipe Left (шторка влево)": TransitionEffect.WIPELEFT,
                "Wipe Right (шторка вправо)": TransitionEffect.WIPERIGHT,
                "Slide Left (сдвиг влево)": TransitionEffect.SLIDELEFT,
                "Slide Right (сдвиг вправо)": TransitionEffect.SLIDERIGHT,
                "Dissolve (растворение)": TransitionEffect.DISSOLVE,
                "Pixelize (пикселизация)": TransitionEffect.PIXELIZE,
                "Radial (радиальный)": TransitionEffect.RADIAL
            }
            transition = transition_map.get(
                self.transition_combo.currentText(),
                TransitionEffect.FADE
            )

        # Разрешение
        resolution = None
        res_text = self.resolution_combo.currentText()
        if res_text != "Как у первого файла":
            width, height = res_text.split()[0].split('x')
            resolution = (int(width), int(height))

        # FPS
        fps = self.fps_spinbox.value() if self.fps_spinbox.value() > 0 else None

        # Кодеки
        codec_map = {
            "libx264 (H.264)": "libx264",
            "libx265 (H.265)": "libx265",
            "libvpx-vp9 (VP9)": "libvpx-vp9"
        }
        video_codec = codec_map.get(self.video_codec.currentText(), "libx264")
        audio_codec = self.audio_codec.currentText()

        # Создаем конфиг
        config = ConcatConfig(
            clips=self.clips,
            output_file=output_file,
            method=method,
            transition=transition,
            transition_duration=self.transition_duration.value(),
            create_chapters=self.create_chapters_checkbox.isChecked(),
            output_resolution=resolution,
            output_fps=fps,
            codec=video_codec,
            crf=self.crf_spinbox.value(),
            audio_codec=audio_codec,
            audio_bitrate=self.audio_bitrate.currentText()
        )

        # Валидация
        is_valid, message = self.manager.validate_clips(self.clips)
        if not is_valid:
            QMessageBox.warning(self, "Ошибка", message)
            return

        # Emit signal
        self.concat_requested.emit(config)
        logger.info(f"Requested concatenation: {len(self.clips)} clips -> {output_file}")

    def _show_context_menu(self, position):
        """Показать контекстное меню"""
        menu = QMenu(self)

        add_action = QAction("➕ Добавить файлы", self)
        add_action.triggered.connect(self._add_files)
        menu.addAction(add_action)

        if self.files_list.currentRow() >= 0:
            menu.addSeparator()

            remove_action = QAction("➖ Удалить", self)
            remove_action.triggered.connect(self._remove_selected)
            menu.addAction(remove_action)

            menu.addSeparator()

            move_up_action = QAction("⬆️ Переместить вверх", self)
            move_up_action.triggered.connect(self._move_up)
            menu.addAction(move_up_action)

            move_down_action = QAction("⬇️ Переместить вниз", self)
            move_down_action.triggered.connect(self._move_down)
            menu.addAction(move_down_action)

        menu.addSeparator()

        clear_action = QAction("🗑️ Очистить все", self)
        clear_action.triggered.connect(self._clear_list)
        menu.addAction(clear_action)

        menu.exec(self.files_list.mapToGlobal(position))
