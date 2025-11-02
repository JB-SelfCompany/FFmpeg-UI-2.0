from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QListWidget, QPushButton, QGroupBox, QListWidgetItem,
    QSizePolicy
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon


class BatchQueue(QWidget):
    """Виджет управления batch очередью"""
    
    clear_requested = Signal()
    
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._init_ui()
        
    def _init_ui(self):
        """Инициализация UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)
        
        # Группа batch очереди
        group = QGroupBox("📋 Batch Очередь")
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        group.setMaximumHeight(180)
        
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(5)
        group_layout.setContentsMargins(8, 8, 8, 8)
        
        # Список файлов
        self.queue_list = QListWidget()
        self.queue_list.setMaximumHeight(120)
        self.queue_list.setToolTip("Список файлов для batch конвертации")
        group_layout.addWidget(self.queue_list)
        
        # Кнопки управления
        buttons_layout = QHBoxLayout()
        
        self.clear_button = QPushButton("🗑 Очистить")
        self.clear_button.setToolTip("Очистить всю очередь")
        self.clear_button.clicked.connect(self.clear_requested.emit)
        buttons_layout.addWidget(self.clear_button)
        
        self.count_label = QLabel("Файлов: 0")
        buttons_layout.addWidget(self.count_label)
        buttons_layout.addStretch()
        
        group_layout.addLayout(buttons_layout)
        main_layout.addWidget(group)
        
    def add_file(self, filename: str):
        """Добавить файл в список"""
        item = QListWidgetItem(f"⏳ {filename}")
        self.queue_list.addItem(item)
        self._update_count()
        
    def update_file_status(self, index: int, status: str):
        """Обновить статус файла"""
        if index < self.queue_list.count():
            item = self.queue_list.item(index)
            filename = item.text().split(" ", 1)[1]
            
            if status == "processing":
                item.setText(f"⚙ {filename}")
            elif status == "completed":
                item.setText(f"✓ {filename}")
            elif status == "failed":
                item.setText(f"✗ {filename}")
                
    def clear_all(self):
        """Очистить весь список"""
        self.queue_list.clear()
        self._update_count()
        
    def _update_count(self):
        """Обновить счетчик файлов"""
        count = self.queue_list.count()
        self.count_label.setText(f"Файлов: {count}")
        
    def get_count(self) -> int:
        """Получить количество файлов"""
        return self.queue_list.count()