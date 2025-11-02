from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QPushButton, QGroupBox
)
from PySide6.QtCore import Signal


class SettingsDialog(QDialog):
    """Диалог настроек"""

    theme_changed = Signal(str)  # Сигнал при изменении темы

    def __init__(self, current_theme="auto", parent=None):
        super().__init__(parent)
        self.current_theme = current_theme

        self.setWindowTitle("Настройки")
        self.setMinimumSize(400, 200)
        self.setModal(True)

        self._init_ui()

    def _init_ui(self):
        """Инициализация UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)

        # Группа "Внешний вид"
        appearance_group = QGroupBox("Внешний вид")
        appearance_layout = QVBoxLayout()

        # Выбор темы
        theme_layout = QHBoxLayout()
        theme_label = QLabel("Тема:")
        theme_label.setMinimumWidth(100)

        self.theme_combo = QComboBox()
        self.theme_combo.addItem("Авто (системная)", "auto")
        self.theme_combo.addItem("Светлая", "light")
        self.theme_combo.addItem("Темная", "dark")

        # Устанавливаем текущую тему
        index = self.theme_combo.findData(self.current_theme)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)

        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_combo, stretch=1)

        appearance_layout.addLayout(theme_layout)

        # Описание
        description = QLabel(
            "Авто - автоматическое определение темы на основе системных настроек.\n"
            "Светлая - светлая тема для дневного использования.\n"
            "Темная - темная тема для ночного использования."
        )
        description.setWordWrap(True)
        description.setStyleSheet("color: #757575; font-size: 11px;")
        appearance_layout.addWidget(description)

        appearance_group.setLayout(appearance_layout)
        layout.addWidget(appearance_group)

        layout.addStretch()

        # Кнопки
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.save_button = QPushButton("Сохранить")
        self.save_button.setObjectName("primaryButton")
        self.save_button.clicked.connect(self._save_settings)
        button_layout.addWidget(self.save_button)

        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

    def _save_settings(self):
        """Сохранение настроек"""
        selected_theme = self.theme_combo.currentData()

        if selected_theme != self.current_theme:
            self.theme_changed.emit(selected_theme)

        self.accept()

    def get_selected_theme(self) -> str:
        """Получить выбранную тему"""
        return self.theme_combo.currentData()
