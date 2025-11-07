from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QComboBox,
    QLabel, QGroupBox, QSizePolicy
)
from PySide6.QtCore import Signal
from core.format_database import FormatDatabase


class FormatSelector(QWidget):
    """Виджет выбора формата вывода"""
    
    format_changed = Signal(dict)
    
    def __init__(self):
        super().__init__()
        self.format_db = FormatDatabase()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._init_ui()
    
    def _init_ui(self):
        """Инициализация UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)
        
        # Группа формата
        group = QGroupBox("🎯 Формат")
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(5)
        group_layout.setContentsMargins(8, 8, 8, 8)
        
        # Выбор формата
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Формат:"))
        self.format_combo = QComboBox()
        self.format_combo.setMinimumHeight(30)
        self._populate_formats()
        self.format_combo.currentTextChanged.connect(self._on_format_changed)
        format_layout.addWidget(self.format_combo, stretch=1)
        group_layout.addLayout(format_layout)
        
        # Описание формата
        self.description_label = QLabel()
        self.description_label.setWordWrap(True)
        self.description_label.setObjectName("FormatDescription")
        # Стили применяются из глобальной темы через objectName
        group_layout.addWidget(self.description_label, stretch=1)
        
        main_layout.addWidget(group)
        
        # Инициализация описания
        self._on_format_changed(self.format_combo.currentText())
    
    def _populate_formats(self):
        """Заполнение списка форматов"""
        # Добавляем видео форматы
        video_formats = self.format_db.get_video_formats()
        if video_formats:
            self.format_combo.addItem("─── 📹 ВИДЕО ФОРМАТЫ ───", None)
            for fmt in video_formats:
                self.format_combo.addItem(
                    f"  {fmt['extension'].upper()} - {fmt['name']}",
                    fmt
                )

        # Добавляем разделитель
        self.format_combo.addItem("", None)

        # Добавляем аудио форматы
        audio_formats = self.format_db.get_audio_formats()
        if audio_formats:
            self.format_combo.addItem("─── 🎵 АУДИО ФОРМАТЫ ───", None)
            for fmt in audio_formats:
                self.format_combo.addItem(
                    f"  {fmt['extension'].upper()} - {fmt['name']}",
                    fmt
                )
    
    def _on_format_changed(self, text: str):
        """Обработка смены формата"""
        format_data = self.format_combo.currentData()
        if format_data:
            self.description_label.setText(format_data['description'])
            self.format_changed.emit(format_data)
        else:
            # Это разделитель или заголовок - переключаемся на следующий элемент
            current_index = self.format_combo.currentIndex()
            if current_index < self.format_combo.count() - 1:
                self.format_combo.setCurrentIndex(current_index + 1)
    
    def get_selected_format(self) -> dict:
        """Получить выбранный формат"""
        return self.format_combo.currentData()