from pathlib import Path
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QFileDialog, QGroupBox, QSizePolicy, QCheckBox, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent


class DropZone(QFrame):
    """Зона для drag and drop"""
    
    files_dropped = Signal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setLineWidth(2)
        self.setMinimumHeight(80)
        self.setMaximumHeight(80)
        self.setObjectName("DropZone")

        self._update_style(False)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)

        self.icon_label = QLabel("📂")
        self.icon_label.setStyleSheet("font-size: 32px; border: none; background: transparent;")
        self.icon_label.setAlignment(Qt.AlignCenter)

        self.text_label = QLabel("Перетащите файлы сюда")
        self.text_label.setStyleSheet("font-size: 14px; border: none; background: transparent;")
        self.text_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)

    def _update_style(self, is_hover: bool = False):
        """Обновить стиль с учетом темы"""
        if is_hover:
            self.setProperty("hover", True)
        else:
            self.setProperty("hover", False)
        # Перерисовать стили
        self.style().unpolish(self)
        self.style().polish(self)
        
    def dragEnterEvent(self, event: QDragEnterEvent):
        """Обработка входа drag"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            self._update_style(True)

    def dragLeaveEvent(self, event):
        """Обработка выхода drag"""
        self._update_style(False)

    def dropEvent(self, event: QDropEvent):
        """Обработка drop"""
        urls = event.mimeData().urls()
        if urls:
            file_paths = [url.toLocalFile() for url in urls]
            self.files_dropped.emit(file_paths)

        self._update_style(False)


class FileSelector(QWidget):
    """Виджет выбора входного и выходного файла с batch поддержкой"""
    
    input_changed = Signal(str)
    output_changed = Signal(str)
    batch_files_selected = Signal(list)
    
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._init_ui()
        
    def _init_ui(self):
        """Инициализация UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)
        
        # Группа файлов
        group = QGroupBox("📁 Файлы")
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(8)
        group_layout.setContentsMargins(8, 8, 8, 8)
        
        # Batch режим
        batch_layout = QHBoxLayout()
        self.batch_mode_checkbox = QCheckBox("Batch режим (множественные файлы)")
        self.batch_mode_checkbox.setToolTip(
            "Включить режим batch конвертации для обработки нескольких файлов одновременно"
        )
        self.batch_mode_checkbox.stateChanged.connect(self._on_batch_mode_changed)
        batch_layout.addWidget(self.batch_mode_checkbox)
        batch_layout.addStretch()
        group_layout.addLayout(batch_layout)
        
        # Drag and drop зона
        self.drop_zone = DropZone()
        self.drop_zone.files_dropped.connect(self._on_files_dropped)
        group_layout.addWidget(self.drop_zone)
        
        # Входной файл
        input_layout = QHBoxLayout()
        input_layout.setSpacing(5)
        input_layout.addWidget(QLabel("Вход:"))
        
        self.input_line = QLineEdit()
        self.input_line.setPlaceholderText("Выберите входной файл...")
        self.input_line.setToolTip("Путь к входному видео/аудио файлу")
        self.input_line.textChanged.connect(self.input_changed.emit)
        input_layout.addWidget(self.input_line)
        
        self.browse_input_btn = QPushButton("📂 Обзор")
        self.browse_input_btn.setMinimumWidth(90)
        self.browse_input_btn.setMaximumWidth(100)
        self.browse_input_btn.setToolTip("Выбрать входной файл")
        self.browse_input_btn.clicked.connect(self.select_input_file)
        input_layout.addWidget(self.browse_input_btn)
        
        group_layout.addLayout(input_layout)
        
        # Выходной файл/папка
        output_layout = QHBoxLayout()
        output_layout.setSpacing(5)
        self.output_label = QLabel("Выход:")
        output_layout.addWidget(self.output_label)
        
        self.output_line = QLineEdit()
        self.output_line.setPlaceholderText("Путь к выходному файлу...")
        self.output_line.setToolTip("Путь к выходному файлу")
        self.output_line.textChanged.connect(self.output_changed.emit)
        output_layout.addWidget(self.output_line)
        
        self.browse_output_btn = QPushButton("💾 Сохр.")
        self.browse_output_btn.setMinimumWidth(90)
        self.browse_output_btn.setMaximumWidth(100)
        self.browse_output_btn.setToolTip("Выбрать выходной файл")
        self.browse_output_btn.clicked.connect(self.select_output_file)
        output_layout.addWidget(self.browse_output_btn)
        
        group_layout.addLayout(output_layout)
        
        main_layout.addWidget(group)
        
    def _on_batch_mode_changed(self, state):
        """Обработка изменения batch режима"""
        if state == Qt.Checked:
            self.output_label.setText("Папка:")
            self.output_line.setPlaceholderText("Выберите выходную папку...")
            self.output_line.setToolTip("Папка для сохранения конвертированных файлов")
            self.browse_output_btn.setToolTip("Выбрать выходную папку")
        else:
            self.output_label.setText("Выход:")
            self.output_line.setPlaceholderText("Путь к выходному файлу...")
            self.output_line.setToolTip("Путь к выходному файлу")
            self.browse_output_btn.setToolTip("Выбрать выходной файл")
            
    def _on_files_dropped(self, file_paths):
        """Обработка drag and drop файлов"""
        if self.is_batch_mode():
            # Множественные файлы
            self.input_line.setText(f"{len(file_paths)} файлов выбрано")
            self.batch_files_selected.emit(file_paths)
            if not self.output_line.text() and file_paths:
                # Предложить папку первого файла
                first_path = Path(file_paths[0])
                self.output_line.setText(str(first_path.parent))
        else:
            # Одиночный файл
            if file_paths:
                file_path = file_paths[0]
                self.input_line.setText(file_path)
                self._suggest_output_file(file_path)
            
    def is_batch_mode(self) -> bool:
        """Проверка batch режима"""
        return self.batch_mode_checkbox.isChecked()
        
    def select_input_file(self):
        """Выбор входного файла"""
        if self.is_batch_mode():
            # Множественный выбор
            file_paths, _ = QFileDialog.getOpenFileNames(
                self,
                "Выберите входные файлы",
                "",
                "Все файлы (*.*)"
            )
            if file_paths:
                self.input_line.setText(f"{len(file_paths)} файлов выбрано")
                self.batch_files_selected.emit(file_paths)
                if not self.output_line.text():
                    # Предложить папку первого файла
                    first_path = Path(file_paths[0])
                    self.output_line.setText(str(first_path.parent))
        else:
            # Одиночный выбор
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                "Выберите входной файл",
                "",
                "Все файлы (*.*)"
            )
            if file_path:
                self.input_line.setText(file_path)
                self._suggest_output_file(file_path)
                
    def select_output_file(self):
        """Выбор выходного файла или папки"""
        if self.is_batch_mode():
            # Выбор папки
            folder_path = QFileDialog.getExistingDirectory(
                self,
                "Выберите выходную папку"
            )
            if folder_path:
                self.output_line.setText(folder_path)
        else:
            # Выбор файла
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить как",
                "",
                "Все файлы (*.*)"
            )
            if file_path:
                self.output_line.setText(file_path)
                
    def _suggest_output_file(self, input_path: str):
        """Предложить имя выходного файла"""
        if not self.output_line.text():
            path = Path(input_path)
            output_path = path.parent / f"{path.stem}_converted{path.suffix}"
            self.output_line.setText(str(output_path))
            
    def has_input_file(self) -> bool:
        """Проверка наличия входного файла"""
        return bool(self.input_line.text())
        
    def has_output_file(self) -> bool:
        """Проверка наличия выходного файла"""
        return bool(self.output_line.text())
        
    def get_input_file(self) -> str:
        """Получить путь к входному файлу"""
        return self.input_line.text()
        
    def get_output_file(self) -> str:
        """Получить путь к выходному файлу"""
        return self.output_line.text()