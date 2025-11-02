"""
Виджет для выбора медиа-потоков (Stream Selection)
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QListWidget, QListWidgetItem, QPushButton, QLabel,
    QMessageBox, QCheckBox
)
from PySide6.QtCore import Qt, Signal
from typing import Optional, List

from core.stream_info import StreamInfo, FileInfo, StreamType
from core.ffprobe_manager import FFProbeManager


class StreamSelectorWidget(QWidget):
    """Виджет для выбора потоков из медиа-файла"""

    # Сигнал при изменении выбора потоков
    streams_changed = Signal()

    def __init__(self, ffprobe_manager: Optional[FFProbeManager] = None, parent=None):
        super().__init__(parent)

        self.file_info: Optional[FileInfo] = None
        self.ffprobe_manager = ffprobe_manager if ffprobe_manager else FFProbeManager()

        self._init_ui()

    def _init_ui(self):
        """Инициализация UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Группа: Информация о файле
        info_group = QGroupBox("Информация о файле")
        info_layout = QVBoxLayout()
        self.file_info_label = QLabel("Файл не загружен")
        self.file_info_label.setWordWrap(True)
        info_layout.addWidget(self.file_info_label)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        # Кнопка анализа
        analyze_btn_layout = QHBoxLayout()
        self.analyze_button = QPushButton("🔍 Анализировать файл")
        self.analyze_button.clicked.connect(self.analyze_current_file)
        self.analyze_button.setEnabled(False)
        analyze_btn_layout.addWidget(self.analyze_button)
        analyze_btn_layout.addStretch()
        layout.addLayout(analyze_btn_layout)

        # Опция: автоматический выбор
        self.auto_select_checkbox = QCheckBox("Автоматический выбор потоков (по умолчанию)")
        self.auto_select_checkbox.setChecked(True)
        self.auto_select_checkbox.stateChanged.connect(self._on_auto_select_changed)
        layout.addWidget(self.auto_select_checkbox)

        # Группа: Списки потоков
        streams_group = QGroupBox("Доступные потоки")
        streams_layout = QVBoxLayout()

        # Видео потоки
        video_label = QLabel("Видео потоки:")
        streams_layout.addWidget(video_label)
        self.video_list = QListWidget()
        self.video_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.video_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.video_list.setMaximumHeight(100)
        streams_layout.addWidget(self.video_list)

        # Аудио потоки
        audio_label = QLabel("Аудио потоки:")
        streams_layout.addWidget(audio_label)
        self.audio_list = QListWidget()
        self.audio_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.audio_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.audio_list.setMaximumHeight(100)
        streams_layout.addWidget(self.audio_list)

        # Субтитры
        subtitle_label = QLabel("Субтитры:")
        streams_layout.addWidget(subtitle_label)
        self.subtitle_list = QListWidget()
        self.subtitle_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.subtitle_list.itemSelectionChanged.connect(self._on_selection_changed)
        self.subtitle_list.setMaximumHeight(80)
        streams_layout.addWidget(self.subtitle_list)

        streams_group.setLayout(streams_layout)
        layout.addWidget(streams_group)

        # Кнопки управления
        btn_layout = QHBoxLayout()
        select_all_btn = QPushButton("Выбрать все")
        select_all_btn.clicked.connect(self._select_all_streams)
        clear_btn = QPushButton("Сбросить выбор")
        clear_btn.clicked.connect(self._clear_selection)

        btn_layout.addWidget(select_all_btn)
        btn_layout.addWidget(clear_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()

        # Начальное состояние
        self._set_manual_selection_enabled(False)

    def set_input_file(self, filepath: str):
        """
        Установить входной файл для анализа

        Args:
            filepath: Путь к файлу
        """
        self.current_file = filepath
        self.analyze_button.setEnabled(bool(filepath))
        self.file_info = None
        self._clear_lists()
        self.file_info_label.setText(f"Файл: {filepath}\nНажмите 'Анализировать' для получения информации о потоках")

    def analyze_current_file(self):
        """Анализировать текущий файл"""
        if not hasattr(self, 'current_file') or not self.current_file:
            QMessageBox.warning(self, "Ошибка", "Файл не выбран")
            return

        # Проверяем наличие ffprobe
        if not self.ffprobe_manager.check_ffprobe_available():
            QMessageBox.critical(
                self,
                "Ошибка",
                "ffprobe не найден. Убедитесь, что FFmpeg установлен и доступен."
            )
            return

        # Анализируем файл
        self.analyze_button.setEnabled(False)
        self.analyze_button.setText("Анализ...")

        try:
            self.file_info = self.ffprobe_manager.probe_file(self.current_file)

            if self.file_info:
                self._populate_stream_lists()
                self.file_info_label.setText(self.file_info.get_summary())
            else:
                QMessageBox.warning(
                    self,
                    "Ошибка",
                    "Не удалось проанализировать файл. Проверьте формат файла."
                )
                self.file_info_label.setText("Ошибка анализа файла")

        finally:
            self.analyze_button.setEnabled(True)
            self.analyze_button.setText("🔍 Анализировать файл")

    def _populate_stream_lists(self):
        """Заполнить списки потоками"""
        if not self.file_info:
            return

        self._clear_lists()

        # Видео потоки
        for stream in self.file_info.get_video_streams():
            item = QListWidgetItem(stream.get_display_name())
            item.setData(Qt.ItemDataRole.UserRole, stream)
            self.video_list.addItem(item)
            # Автовыбор первого видео потока
            if stream.index == 0 or stream.is_default:
                item.setSelected(True)

        # Аудио потоки
        for stream in self.file_info.get_audio_streams():
            item = QListWidgetItem(stream.get_display_name())
            item.setData(Qt.ItemDataRole.UserRole, stream)
            self.audio_list.addItem(item)
            # Автовыбор первого или default аудио потока
            if stream.is_default or (
                self.audio_list.count() == 1 and not any(
                    self.audio_list.item(i).isSelected()
                    for i in range(self.audio_list.count())
                )
            ):
                item.setSelected(True)

        # Субтитры
        for stream in self.file_info.get_subtitle_streams():
            item = QListWidgetItem(stream.get_display_name())
            item.setData(Qt.ItemDataRole.UserRole, stream)
            self.subtitle_list.addItem(item)
            # Субтитры не выбираем автоматически

    def _clear_lists(self):
        """Очистить все списки"""
        self.video_list.clear()
        self.audio_list.clear()
        self.subtitle_list.clear()

    def _on_auto_select_changed(self, state):
        """Обработчик изменения автовыбора"""
        is_manual = state == Qt.CheckState.Unchecked.value
        self._set_manual_selection_enabled(is_manual)
        self.streams_changed.emit()

    def _set_manual_selection_enabled(self, enabled: bool):
        """Включить/выключить ручной выбор потоков"""
        self.video_list.setEnabled(enabled)
        self.audio_list.setEnabled(enabled)
        self.subtitle_list.setEnabled(enabled)

    def _on_selection_changed(self):
        """Обработчик изменения выбора"""
        if not self.auto_select_checkbox.isChecked():
            self.streams_changed.emit()

    def _select_all_streams(self):
        """Выбрать все потоки"""
        self.video_list.selectAll()
        self.audio_list.selectAll()
        self.subtitle_list.selectAll()

    def _clear_selection(self):
        """Сбросить выбор"""
        self.video_list.clearSelection()
        self.audio_list.clearSelection()
        self.subtitle_list.clearSelection()

    def get_selected_streams(self) -> List[StreamInfo]:
        """
        Получить список выбранных потоков

        Returns:
            Список StreamInfo объектов
        """
        if self.auto_select_checkbox.isChecked():
            # Автоматический режим - возвращаем пустой список (ffmpeg сам выберет)
            return []

        selected = []

        # Видео
        for i in range(self.video_list.count()):
            item = self.video_list.item(i)
            if item.isSelected():
                stream = item.data(Qt.ItemDataRole.UserRole)
                selected.append(stream)

        # Аудио
        for i in range(self.audio_list.count()):
            item = self.audio_list.item(i)
            if item.isSelected():
                stream = item.data(Qt.ItemDataRole.UserRole)
                selected.append(stream)

        # Субтитры
        for i in range(self.subtitle_list.count()):
            item = self.subtitle_list.item(i)
            if item.isSelected():
                stream = item.data(Qt.ItemDataRole.UserRole)
                selected.append(stream)

        return selected

    def is_auto_select(self) -> bool:
        """Проверить, включен ли автовыбор"""
        return self.auto_select_checkbox.isChecked()

    def get_map_options(self) -> List[str]:
        """
        Получить список -map опций для FFmpeg

        Returns:
            Список строк для командной строки FFmpeg
        """
        if self.is_auto_select():
            return []

        map_options = []
        for stream in self.get_selected_streams():
            map_options.extend(["-map", f"0:{stream.index}"])

        return map_options
