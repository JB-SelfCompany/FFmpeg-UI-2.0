"""
Виджет для редактирования метаданных медиа-файлов
Поддержка -metadata параметра FFmpeg
"""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QLineEdit, QPushButton, QTableWidget,
    QTableWidgetItem, QHeaderView, QMessageBox, QCheckBox
)
from PySide6.QtCore import Signal
from typing import Dict


class MetadataEditorWidget(QWidget):
    """Виджет для редактирования метаданных"""

    # Сигнал при изменении метаданных
    metadata_changed = Signal()

    # Стандартные теги метаданных
    COMMON_TAGS = {
        "title": "Название",
        "artist": "Исполнитель",
        "album": "Альбом",
        "album_artist": "Исполнитель альбома",
        "date": "Дата",
        "year": "Год",
        "genre": "Жанр",
        "comment": "Комментарий",
        "description": "Описание",
        "composer": "Композитор",
        "track": "Трек",
        "copyright": "Авторские права",
        "language": "Язык"
    }

    def __init__(self, parent=None):
        super().__init__(parent)

        # Хранилище метаданных
        self.metadata: Dict[str, str] = {}

        self._init_ui()

    def _init_ui(self):
        """Инициализация UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Опция включения редактирования метаданных
        self.enable_metadata_checkbox = QCheckBox("Редактировать метаданные")
        self.enable_metadata_checkbox.stateChanged.connect(self._on_enable_changed)
        layout.addWidget(self.enable_metadata_checkbox)

        # Группа: Стандартные теги
        common_group = QGroupBox("Основные теги")
        common_layout = QVBoxLayout()

        self.common_inputs = {}
        for tag_key, tag_label in self.COMMON_TAGS.items():
            row_layout = QHBoxLayout()
            label = QLabel(f"{tag_label}:")
            label.setMinimumWidth(150)

            line_edit = QLineEdit()
            line_edit.setPlaceholderText(f"Введите {tag_label.lower()}")
            line_edit.textChanged.connect(self._on_common_tag_changed)
            line_edit.setEnabled(False)

            row_layout.addWidget(label)
            row_layout.addWidget(line_edit)

            common_layout.addLayout(row_layout)
            self.common_inputs[tag_key] = line_edit

        common_group.setLayout(common_layout)

        # Делаем группу прокручиваемой
        from PySide6.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidget(common_group)
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(250)
        layout.addWidget(scroll)

        # Группа: Кастомные теги
        custom_group = QGroupBox("Дополнительные теги")
        custom_layout = QVBoxLayout()

        # Таблица кастомных тегов
        self.custom_table = QTableWidget(0, 2)
        self.custom_table.setHorizontalHeaderLabels(["Ключ", "Значение"])
        self.custom_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
        self.custom_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.custom_table.setColumnWidth(0, 150)
        self.custom_table.setMaximumHeight(150)
        self.custom_table.itemChanged.connect(self._on_custom_tag_changed)
        self.custom_table.setEnabled(False)
        custom_layout.addWidget(self.custom_table)

        # Кнопки управления кастомными тегами
        custom_btn_layout = QHBoxLayout()
        self.add_custom_btn = QPushButton("➕ Добавить тег")
        self.add_custom_btn.clicked.connect(self._add_custom_tag)
        self.add_custom_btn.setEnabled(False)

        self.remove_custom_btn = QPushButton("➖ Удалить тег")
        self.remove_custom_btn.clicked.connect(self._remove_custom_tag)
        self.remove_custom_btn.setEnabled(False)

        custom_btn_layout.addWidget(self.add_custom_btn)
        custom_btn_layout.addWidget(self.remove_custom_btn)
        custom_btn_layout.addStretch()
        custom_layout.addLayout(custom_btn_layout)

        custom_group.setLayout(custom_layout)
        layout.addWidget(custom_group)

        # Кнопки общего управления
        action_btn_layout = QHBoxLayout()
        self.clear_all_btn = QPushButton("Очистить все")
        self.clear_all_btn.clicked.connect(self._clear_all_metadata)
        self.clear_all_btn.setEnabled(False)

        action_btn_layout.addWidget(self.clear_all_btn)
        action_btn_layout.addStretch()
        layout.addLayout(action_btn_layout)

        layout.addStretch()

    def _on_enable_changed(self, state):
        """Обработчик включения/выключения редактирования"""
        from PySide6.QtCore import Qt
        enabled = state == Qt.CheckState.Checked.value

        # Включаем/выключаем все контролы
        for line_edit in self.common_inputs.values():
            line_edit.setEnabled(enabled)

        self.custom_table.setEnabled(enabled)
        self.add_custom_btn.setEnabled(enabled)
        self.remove_custom_btn.setEnabled(enabled)
        self.clear_all_btn.setEnabled(enabled)

        self.metadata_changed.emit()

    def _on_common_tag_changed(self):
        """Обработчик изменения стандартного тега"""
        self.metadata_changed.emit()

    def _on_custom_tag_changed(self):
        """Обработчик изменения кастомного тега"""
        self.metadata_changed.emit()

    def _add_custom_tag(self):
        """Добавить пустую строку для кастомного тега"""
        row = self.custom_table.rowCount()
        self.custom_table.insertRow(row)
        self.custom_table.setItem(row, 0, QTableWidgetItem(""))
        self.custom_table.setItem(row, 1, QTableWidgetItem(""))

    def _remove_custom_tag(self):
        """Удалить выбранный кастомный тег"""
        current_row = self.custom_table.currentRow()
        if current_row >= 0:
            self.custom_table.removeRow(current_row)
            self.metadata_changed.emit()

    def _clear_all_metadata(self):
        """Очистить все метаданные"""
        reply = QMessageBox.question(
            self,
            "Подтверждение",
            "Очистить все метаданные?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            # Очищаем стандартные теги
            for line_edit in self.common_inputs.values():
                line_edit.clear()

            # Очищаем кастомные теги
            self.custom_table.setRowCount(0)

            self.metadata_changed.emit()

    def get_metadata(self) -> Dict[str, str]:
        """
        Получить все метаданные

        Returns:
            Словарь с метаданными
        """
        if not self.enable_metadata_checkbox.isChecked():
            return {}

        metadata = {}

        # Собираем стандартные теги
        for tag_key, line_edit in self.common_inputs.items():
            value = line_edit.text().strip()
            if value:
                metadata[tag_key] = value

        # Собираем кастомные теги
        for row in range(self.custom_table.rowCount()):
            key_item = self.custom_table.item(row, 0)
            value_item = self.custom_table.item(row, 1)

            if key_item and value_item:
                key = key_item.text().strip()
                value = value_item.text().strip()

                if key and value:
                    metadata[key] = value

        return metadata

    def set_metadata(self, metadata: Dict[str, str]):
        """
        Установить метаданные

        Args:
            metadata: Словарь с метаданными
        """
        # Очищаем текущие
        for line_edit in self.common_inputs.values():
            line_edit.clear()
        self.custom_table.setRowCount(0)

        if not metadata:
            return

        # Заполняем стандартные теги
        for tag_key, line_edit in self.common_inputs.items():
            if tag_key in metadata:
                line_edit.setText(metadata[tag_key])

        # Заполняем кастомные теги
        for key, value in metadata.items():
            if key not in self.COMMON_TAGS:
                row = self.custom_table.rowCount()
                self.custom_table.insertRow(row)
                self.custom_table.setItem(row, 0, QTableWidgetItem(key))
                self.custom_table.setItem(row, 1, QTableWidgetItem(value))

    def get_ffmpeg_options(self) -> list[str]:
        """
        Получить FFmpeg опции для метаданных

        Returns:
            Список параметров командной строки
        """
        if not self.enable_metadata_checkbox.isChecked():
            return []

        options = []
        metadata = self.get_metadata()

        for key, value in metadata.items():
            # Экранируем специальные символы
            escaped_value = value.replace("\\", "\\\\").replace("\"", "\\\"")
            options.extend(["-metadata", f'{key}={escaped_value}'])

        return options

    def is_enabled(self) -> bool:
        """Проверить, включено ли редактирование метаданных"""
        return self.enable_metadata_checkbox.isChecked()

    def reset(self):
        """Сбросить все настройки"""
        self.enable_metadata_checkbox.setChecked(False)
        self._clear_all_metadata()
