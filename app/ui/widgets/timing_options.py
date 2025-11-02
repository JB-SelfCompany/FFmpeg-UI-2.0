"""
Виджет для настройки времени (обрезка видео)
Поддержка -ss, -t, -to, -copyts
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QTimeEdit, QCheckBox, QRadioButton, QButtonGroup
)
from PySide6.QtCore import Qt, QTime, Signal


class TimingOptionsWidget(QWidget):
    """Виджет для настройки временных параметров"""

    # Сигнал при изменении настроек
    options_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        """Инициализация UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Группа: Обрезка видео
        trim_group = QGroupBox("Обрезка видео")
        trim_layout = QVBoxLayout()

        # Начальное время (Start time)
        start_layout = QHBoxLayout()
        self.start_time_checkbox = QCheckBox("Начать с:")
        self.start_time_checkbox.stateChanged.connect(self._on_start_time_changed)
        self.start_time_checkbox.stateChanged.connect(self.options_changed.emit)

        self.start_time_edit = QTimeEdit()
        self.start_time_edit.setDisplayFormat("HH:mm:ss")
        self.start_time_edit.setTime(QTime(0, 0, 0))
        self.start_time_edit.setEnabled(False)
        self.start_time_edit.timeChanged.connect(self.options_changed.emit)

        start_help = QLabel("(-ss параметр)")
        start_help.setStyleSheet("color: gray; font-size: 10px;")

        start_layout.addWidget(self.start_time_checkbox)
        start_layout.addWidget(self.start_time_edit)
        start_layout.addWidget(start_help)
        start_layout.addStretch()
        trim_layout.addLayout(start_layout)

        # Режим окончания: Длительность или Конечное время
        end_mode_layout = QHBoxLayout()
        self.duration_radio = QRadioButton("Длительность:")
        self.end_time_radio = QRadioButton("Закончить в:")
        self.duration_radio.setChecked(True)

        self.end_mode_group = QButtonGroup()
        self.end_mode_group.addButton(self.duration_radio)
        self.end_mode_group.addButton(self.end_time_radio)
        self.end_mode_group.buttonClicked.connect(self._on_end_mode_changed)
        self.end_mode_group.buttonClicked.connect(self.options_changed.emit)

        end_mode_layout.addWidget(self.duration_radio)
        end_mode_layout.addWidget(self.end_time_radio)
        end_mode_layout.addStretch()
        trim_layout.addLayout(end_mode_layout)

        # Длительность (-t)
        duration_layout = QHBoxLayout()
        duration_label = QLabel("   ")
        self.duration_time_edit = QTimeEdit()
        self.duration_time_edit.setDisplayFormat("HH:mm:ss")
        self.duration_time_edit.setTime(QTime(0, 1, 0))  # По умолчанию 1 минута
        self.duration_time_edit.setEnabled(False)
        self.duration_time_edit.timeChanged.connect(self.options_changed.emit)

        duration_help = QLabel("(-t параметр)")
        duration_help.setStyleSheet("color: gray; font-size: 10px;")

        duration_layout.addWidget(duration_label)
        duration_layout.addWidget(self.duration_time_edit)
        duration_layout.addWidget(duration_help)
        duration_layout.addStretch()
        trim_layout.addLayout(duration_layout)

        # Конечное время (-to)
        end_time_layout = QHBoxLayout()
        end_time_label = QLabel("   ")
        self.end_time_edit = QTimeEdit()
        self.end_time_edit.setDisplayFormat("HH:mm:ss")
        self.end_time_edit.setTime(QTime(0, 1, 0))
        self.end_time_edit.setEnabled(False)
        self.end_time_edit.timeChanged.connect(self.options_changed.emit)

        end_time_help = QLabel("(-to параметр)")
        end_time_help.setStyleSheet("color: gray; font-size: 10px;")

        end_time_layout.addWidget(end_time_label)
        end_time_layout.addWidget(self.end_time_edit)
        end_time_layout.addWidget(end_time_help)
        end_time_layout.addStretch()
        trim_layout.addLayout(end_time_layout)

        # Включение обрезки
        self.enable_trim_checkbox = QCheckBox("Включить обрезку")
        self.enable_trim_checkbox.stateChanged.connect(self._on_trim_enabled_changed)
        self.enable_trim_checkbox.stateChanged.connect(self.options_changed.emit)
        trim_layout.addWidget(self.enable_trim_checkbox)

        trim_group.setLayout(trim_layout)
        layout.addWidget(trim_group)

        # Группа: Дополнительные опции
        advanced_group = QGroupBox("Дополнительные опции")
        advanced_layout = QVBoxLayout()

        # Copy timestamps
        self.copyts_checkbox = QCheckBox("Сохранить оригинальные timestamp (-copyts)")
        self.copyts_checkbox.setToolTip(
            "Не изменять временные метки, сохранить их как в оригинале"
        )
        self.copyts_checkbox.stateChanged.connect(self.options_changed.emit)
        advanced_layout.addWidget(self.copyts_checkbox)

        # Accurate seek
        self.accurate_seek_checkbox = QCheckBox("Точный поиск (-accurate_seek)")
        self.accurate_seek_checkbox.setChecked(True)
        self.accurate_seek_checkbox.setToolTip(
            "Точный поиск начальной позиции (медленнее, но точнее)"
        )
        self.accurate_seek_checkbox.stateChanged.connect(self.options_changed.emit)
        advanced_layout.addWidget(self.accurate_seek_checkbox)

        advanced_group.setLayout(advanced_layout)
        layout.addWidget(advanced_group)

        layout.addStretch()

        # Начальное состояние
        self._update_controls_state()

    def _on_start_time_changed(self, state):
        """Обработчик изменения начального времени"""
        enabled = state == Qt.CheckState.Checked.value
        self.start_time_edit.setEnabled(enabled)

    def _on_end_mode_changed(self):
        """Обработчик изменения режима окончания"""
        self._update_controls_state()

    def _on_trim_enabled_changed(self, state):
        """Обработчик включения/выключения обрезки"""
        self._update_controls_state()

    def _update_controls_state(self):
        """Обновить состояние контролов"""
        trim_enabled = self.enable_trim_checkbox.isChecked()

        # Включаем/выключаем все контролы обрезки
        self.start_time_checkbox.setEnabled(trim_enabled)
        self.duration_radio.setEnabled(trim_enabled)
        self.end_time_radio.setEnabled(trim_enabled)

        if trim_enabled:
            # Обновляем время начала
            self.start_time_edit.setEnabled(self.start_time_checkbox.isChecked())

            # Обновляем время окончания в зависимости от режима
            is_duration_mode = self.duration_radio.isChecked()
            self.duration_time_edit.setEnabled(is_duration_mode)
            self.end_time_edit.setEnabled(not is_duration_mode)
        else:
            self.start_time_edit.setEnabled(False)
            self.duration_time_edit.setEnabled(False)
            self.end_time_edit.setEnabled(False)

    def get_ffmpeg_options(self) -> list[str]:
        """
        Получить FFmpeg опции

        Returns:
            Список параметров командной строки
        """
        options = []

        if not self.enable_trim_checkbox.isChecked():
            # Обрезка выключена, но проверяем copyts
            if self.copyts_checkbox.isChecked():
                options.append("-copyts")
            return options

        # Начальное время (-ss)
        if self.start_time_checkbox.isChecked():
            start_seconds = self._time_to_seconds(self.start_time_edit.time())
            if start_seconds > 0:
                options.extend(["-ss", self._format_time(start_seconds)])

        # Длительность (-t) или Конечное время (-to)
        if self.duration_radio.isChecked():
            # Режим длительности
            duration_seconds = self._time_to_seconds(self.duration_time_edit.time())
            if duration_seconds > 0:
                options.extend(["-t", self._format_time(duration_seconds)])
        else:
            # Режим конечного времени
            end_seconds = self._time_to_seconds(self.end_time_edit.time())
            if end_seconds > 0:
                options.extend(["-to", self._format_time(end_seconds)])

        # Copy timestamps
        if self.copyts_checkbox.isChecked():
            options.append("-copyts")

        # Accurate seek (включен по умолчанию в ffmpeg, но можно выключить)
        if not self.accurate_seek_checkbox.isChecked():
            options.append("-noaccurate_seek")

        return options

    @staticmethod
    def _time_to_seconds(time: QTime) -> float:
        """
        Конвертировать QTime в секунды

        Args:
            time: QTime объект

        Returns:
            Количество секунд
        """
        return time.hour() * 3600 + time.minute() * 60 + time.second()

    @staticmethod
    def _format_time(seconds: float) -> str:
        """
        Форматировать секунды в строку HH:MM:SS

        Args:
            seconds: Количество секунд

        Returns:
            Форматированная строка
        """
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def is_trim_enabled(self) -> bool:
        """Проверить, включена ли обрезка"""
        return self.enable_trim_checkbox.isChecked()

    def get_start_time(self) -> float:
        """Получить начальное время в секундах"""
        if self.start_time_checkbox.isChecked():
            return self._time_to_seconds(self.start_time_edit.time())
        return 0.0

    def get_duration(self) -> float:
        """Получить длительность в секундах (если установлена)"""
        if self.duration_radio.isChecked():
            return self._time_to_seconds(self.duration_time_edit.time())
        return 0.0

    def reset(self):
        """Сбросить все настройки"""
        self.enable_trim_checkbox.setChecked(False)
        self.start_time_checkbox.setChecked(False)
        self.start_time_edit.setTime(QTime(0, 0, 0))
        self.duration_radio.setChecked(True)
        self.duration_time_edit.setTime(QTime(0, 1, 0))
        self.end_time_edit.setTime(QTime(0, 1, 0))
        self.copyts_checkbox.setChecked(False)
        self.accurate_seek_checkbox.setChecked(True)
