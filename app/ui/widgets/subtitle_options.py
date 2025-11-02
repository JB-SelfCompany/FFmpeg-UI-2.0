"""
Виджет для работы с субтитрами
Поддержка выбора subtitle stream, burn-in субтитров
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QComboBox, QCheckBox, QPushButton,
    QRadioButton, QButtonGroup, QFileDialog, QMessageBox
)
from PySide6.QtCore import Signal
from typing import Optional, List
from pathlib import Path

from core.stream_info import StreamInfo, StreamType


class SubtitleOptionsWidget(QWidget):
    """Виджет для работы с субтитрами"""

    # Сигнал при изменении настроек
    options_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        self.subtitle_streams: List[StreamInfo] = []
        self.external_subtitle_file: Optional[str] = None

        self._init_ui()

    def _init_ui(self):
        """Инициализация UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Группа: Источник субтитров
        source_group = QGroupBox("Источник субтитров")
        source_layout = QVBoxLayout()

        # Режим: встроенные или внешние
        mode_layout = QHBoxLayout()
        self.embedded_radio = QRadioButton("Встроенные в видео")
        self.external_radio = QRadioButton("Внешний файл")
        self.embedded_radio.setChecked(True)

        self.mode_group = QButtonGroup()
        self.mode_group.addButton(self.embedded_radio)
        self.mode_group.addButton(self.external_radio)
        self.mode_group.buttonClicked.connect(self._on_mode_changed)

        mode_layout.addWidget(self.embedded_radio)
        mode_layout.addWidget(self.external_radio)
        mode_layout.addStretch()
        source_layout.addLayout(mode_layout)

        # Выбор встроенного subtitle stream
        embedded_layout = QHBoxLayout()
        embedded_label = QLabel("Дорожка:")
        self.subtitle_combo = QComboBox()
        self.subtitle_combo.addItem("(не выбрано)")
        self.subtitle_combo.currentIndexChanged.connect(self.options_changed.emit)

        embedded_layout.addWidget(embedded_label)
        embedded_layout.addWidget(self.subtitle_combo, 1)
        source_layout.addLayout(embedded_layout)

        # Выбор внешнего файла
        external_layout = QHBoxLayout()
        self.external_file_label = QLabel("Файл: не выбран")
        self.external_file_label.setEnabled(False)
        self.browse_button = QPushButton("📁 Обзор...")
        self.browse_button.clicked.connect(self._browse_subtitle_file)
        self.browse_button.setEnabled(False)

        external_layout.addWidget(self.external_file_label, 1)
        external_layout.addWidget(self.browse_button)
        source_layout.addLayout(external_layout)

        source_group.setLayout(source_layout)
        layout.addWidget(source_group)

        # Группа: Режим обработки
        processing_group = QGroupBox("Режим обработки")
        processing_layout = QVBoxLayout()

        # Burn-in (вжигание в видео)
        self.burnin_checkbox = QCheckBox("Вжечь субтитры в видео (burn-in)")
        self.burnin_checkbox.setToolTip(
            "Субтитры будут навсегда встроены в видео (нельзя будет отключить)"
        )
        self.burnin_checkbox.stateChanged.connect(self._on_burnin_changed)
        self.burnin_checkbox.stateChanged.connect(self.options_changed.emit)
        processing_layout.addWidget(self.burnin_checkbox)

        # Copy/Convert subtitle stream
        self.copy_stream_checkbox = QCheckBox("Копировать subtitle поток в выходной файл")
        self.copy_stream_checkbox.setToolTip(
            "Субтитры будут скопированы как отдельная дорожка (можно отключить при просмотре)"
        )
        self.copy_stream_checkbox.stateChanged.connect(self.options_changed.emit)
        processing_layout.addWidget(self.copy_stream_checkbox)

        # Предупреждение о burn-in
        self.burnin_warning = QLabel(
            "⚠️ Внимание: burn-in увеличит время кодирования и размер файла"
        )
        self.burnin_warning.setStyleSheet("color: orange; font-size: 10px;")
        self.burnin_warning.setWordWrap(True)
        self.burnin_warning.setVisible(False)
        processing_layout.addWidget(self.burnin_warning)

        processing_group.setLayout(processing_layout)
        layout.addWidget(processing_group)

        # Группа: Дополнительные опции
        advanced_group = QGroupBox("Дополнительные опции")
        advanced_layout = QVBoxLayout()

        # Fix subtitle duration
        self.fix_duration_checkbox = QCheckBox("Исправить длительность субтитров (-fix_sub_duration)")
        self.fix_duration_checkbox.setToolTip(
            "Автоматически корректирует длительность субтитров (полезно для DVB субтитров)"
        )
        self.fix_duration_checkbox.stateChanged.connect(self.options_changed.emit)
        advanced_layout.addWidget(self.fix_duration_checkbox)

        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)

        layout.addStretch()

        # Начальное состояние
        self._update_controls_state()

    def _on_mode_changed(self):
        """Обработчик изменения режима источника"""
        self._update_controls_state()
        self.options_changed.emit()

    def _on_burnin_changed(self, state):
        """Обработчик изменения burn-in"""
        from PySide6.QtCore import Qt
        is_checked = state == Qt.CheckState.Checked.value
        self.burnin_warning.setVisible(is_checked)

    def _update_controls_state(self):
        """Обновить состояние контролов"""
        is_embedded = self.embedded_radio.isChecked()

        # Встроенные субтитры
        self.subtitle_combo.setEnabled(is_embedded)

        # Внешний файл
        self.external_file_label.setEnabled(not is_embedded)
        self.browse_button.setEnabled(not is_embedded)

    def _browse_subtitle_file(self):
        """Открыть диалог выбора файла субтитров"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите файл субтитров",
            "",
            "Subtitle Files (*.srt *.ass *.ssa *.sub *.vtt);;All Files (*.*)"
        )

        if file_path:
            self.external_subtitle_file = file_path
            filename = Path(file_path).name
            self.external_file_label.setText(f"Файл: {filename}")
            self.options_changed.emit()

    def set_subtitle_streams(self, streams: List[StreamInfo]):
        """
        Установить список subtitle потоков

        Args:
            streams: Список StreamInfo объектов с субтитрами
        """
        self.subtitle_streams = [s for s in streams if s.stream_type == StreamType.SUBTITLE]

        # Обновляем комбобокс
        self.subtitle_combo.clear()
        self.subtitle_combo.addItem("(не выбрано)")

        for stream in self.subtitle_streams:
            self.subtitle_combo.addItem(stream.get_display_name(), stream)

        # Автоматически выбираем первый default subtitle
        for i, stream in enumerate(self.subtitle_streams):
            if stream.is_default:
                self.subtitle_combo.setCurrentIndex(i + 1)
                break

    def get_selected_stream(self) -> Optional[StreamInfo]:
        """
        Получить выбранный subtitle stream

        Returns:
            StreamInfo объект или None
        """
        if not self.embedded_radio.isChecked():
            return None

        index = self.subtitle_combo.currentIndex()
        if index <= 0:
            return None

        return self.subtitle_combo.itemData(index)

    def get_ffmpeg_options(self) -> list[str]:
        """
        Получить FFmpeg опции для субтитров

        Returns:
            Список параметров командной строки
        """
        options = []

        # Fix subtitle duration
        if self.fix_duration_checkbox.isChecked():
            options.append("-fix_sub_duration")

        # Копирование subtitle stream
        if self.copy_stream_checkbox.isChecked() and self.embedded_radio.isChecked():
            stream = self.get_selected_stream()
            if stream:
                # Копируем subtitle stream
                options.extend(["-c:s", "copy"])

        return options

    def get_filter_options(self) -> list[str]:
        """
        Получить опции фильтра для burn-in субтитров

        Returns:
            Список строк фильтров для -vf
        """
        if not self.burnin_checkbox.isChecked():
            return []

        filters = []

        if self.embedded_radio.isChecked():
            # Burn-in встроенных субтитров
            stream = self.get_selected_stream()
            if stream:
                # Используем subtitles filter
                filters.append(f"subtitles='{self._escape_filter_string(stream.index)}'")
        else:
            # Burn-in внешних субтитров
            if self.external_subtitle_file:
                # Экранируем путь для FFmpeg фильтра
                escaped_path = self._escape_filter_string(self.external_subtitle_file)
                filters.append(f"subtitles='{escaped_path}'")

        return filters

    @staticmethod
    def _escape_filter_string(text: str) -> str:
        """
        Экранировать строку для использования в FFmpeg фильтре

        Args:
            text: Исходная строка

        Returns:
            Экранированная строка
        """
        # Экранируем специальные символы для FFmpeg фильтров
        text = str(text)
        text = text.replace("\\", "\\\\")
        text = text.replace(":", "\\:")
        text = text.replace("'", "\\'")
        return text

    def is_burnin_enabled(self) -> bool:
        """Проверить, включен ли burn-in"""
        return self.burnin_checkbox.isChecked()

    def is_copy_enabled(self) -> bool:
        """Проверить, включено ли копирование subtitle потока"""
        return self.copy_stream_checkbox.isChecked()

    def reset(self):
        """Сбросить все настройки"""
        self.embedded_radio.setChecked(True)
        self.subtitle_combo.setCurrentIndex(0)
        self.external_subtitle_file = None
        self.external_file_label.setText("Файл: не выбран")
        self.burnin_checkbox.setChecked(False)
        self.copy_stream_checkbox.setChecked(False)
        self.fix_duration_checkbox.setChecked(False)
        self._update_controls_state()
