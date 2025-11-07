"""
Виджет для работы с главами (chapters) в видео
"""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QGroupBox, QTableWidget, QTableWidgetItem,
    QFileDialog, QHeaderView, QMessageBox, QTimeEdit, QMenu
)
from PySide6.QtCore import Qt, Signal, QTime
from PySide6.QtGui import QAction
from pathlib import Path
import logging

from core.chapters_manager import ChaptersManager, Chapter

logger = logging.getLogger(__name__)


class ChaptersWidget(QWidget):
    """Виджет для управления главами"""

    # Сигналы
    add_chapters_requested = Signal(list, str, str)  # chapters, input_file, output_file
    split_by_chapters_requested = Signal(list, str, str)  # chapters, input_file, output_folder

    def __init__(self):
        super().__init__()
        self.manager = ChaptersManager()
        self.current_video = ""
        self.video_duration = 0.0
        self._init_ui()

    def _init_ui(self):
        """Инициализация UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        # Группа: Входной файл
        input_group = QGroupBox("Видео файл")
        input_layout = QHBoxLayout(input_group)
        input_layout.setSpacing(5)

        self.video_file_edit = QLineEdit()
        self.video_file_edit.setPlaceholderText("Выберите видео файл")
        self.video_file_edit.textChanged.connect(self._on_video_changed)
        input_layout.addWidget(self.video_file_edit)

        browse_btn = QPushButton("Обзор...")
        browse_btn.clicked.connect(self._browse_video_file)
        input_layout.addWidget(browse_btn)

        load_chapters_btn = QPushButton("📖 Загрузить главы")
        load_chapters_btn.setToolTip("Извлечь существующие главы из видео")
        load_chapters_btn.clicked.connect(self._load_chapters_from_video)
        input_layout.addWidget(load_chapters_btn)

        layout.addWidget(input_group)

        # Информация о видео
        self.video_info_label = QLabel("")
        self.video_info_label.setStyleSheet("color: #2196F3; font-size: 9px;")
        self.video_info_label.setWordWrap(True)
        layout.addWidget(self.video_info_label)

        # Таблица глав
        chapters_group = QGroupBox("Главы")
        chapters_layout = QVBoxLayout(chapters_group)

        # Кнопки управления
        btn_layout = QHBoxLayout()

        add_chapter_btn = QPushButton("➕ Добавить")
        add_chapter_btn.clicked.connect(self._add_chapter)
        btn_layout.addWidget(add_chapter_btn)

        remove_chapter_btn = QPushButton("➖ Удалить")
        remove_chapter_btn.clicked.connect(self._remove_selected_chapter)
        btn_layout.addWidget(remove_chapter_btn)

        clear_btn = QPushButton("🗑️ Очистить")
        clear_btn.clicked.connect(self._clear_chapters)
        btn_layout.addWidget(clear_btn)

        btn_layout.addStretch()

        import_btn = QPushButton("📥 Импорт")
        import_btn.setToolTip("Импортировать главы из FFMETADATA файла")
        import_btn.clicked.connect(self._import_chapters)
        btn_layout.addWidget(import_btn)

        export_btn = QPushButton("📤 Экспорт")
        export_btn.setToolTip("Экспортировать главы в FFMETADATA файл")
        export_btn.clicked.connect(self._export_chapters)
        btn_layout.addWidget(export_btn)

        chapters_layout.addLayout(btn_layout)

        # Таблица
        self.chapters_table = QTableWidget()
        self.chapters_table.setColumnCount(4)
        self.chapters_table.setHorizontalHeaderLabels([
            "№", "Начало (мм:сс)", "Конец (мм:сс)", "Название"
        ])

        # Настройка таблицы
        header = self.chapters_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)

        self.chapters_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.chapters_table.setEditTriggers(QTableWidget.DoubleClicked)
        self.chapters_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.chapters_table.customContextMenuRequested.connect(self._show_context_menu)

        chapters_layout.addWidget(self.chapters_table)

        layout.addWidget(chapters_group)

        # Кнопки действий
        action_layout = QHBoxLayout()

        apply_chapters_btn = QPushButton("✅ Добавить главы к видео")
        apply_chapters_btn.setToolTip("Создать новый файл с главами (без перекодирования)")
        apply_chapters_btn.setMinimumHeight(35)
        apply_chapters_btn.clicked.connect(self._apply_chapters_to_video)
        action_layout.addWidget(apply_chapters_btn)

        split_btn = QPushButton("✂️ Разделить по главам")
        split_btn.setToolTip("Разделить видео на отдельные файлы по главам")
        split_btn.setMinimumHeight(35)
        split_btn.clicked.connect(self._split_video_by_chapters)
        action_layout.addWidget(split_btn)

        layout.addLayout(action_layout)

    def _browse_video_file(self):
        """Выбор видео файла"""
        file, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите видео файл",
            "",
            "Video Files (*.mp4 *.mkv *.avi *.mov *.webm *.flv);;All Files (*.*)"
        )
        if file:
            self.video_file_edit.setText(file)

    def _on_video_changed(self, video_path: str):
        """Обработка изменения видео файла"""
        if not video_path or not Path(video_path).exists():
            self.current_video = ""
            self.video_duration = 0.0
            self.video_info_label.setText("")
            return

        self.current_video = video_path

        # Получаем длительность
        self.video_duration = self.manager.get_video_duration(video_path)

        if self.video_duration > 0:
            minutes = int(self.video_duration // 60)
            seconds = int(self.video_duration % 60)
            self.video_info_label.setText(
                f"📊 Длительность: {minutes}:{seconds:02d} "
                f"({self.video_duration:.1f} сек)"
            )
        else:
            self.video_info_label.setText("⚠️ Не удалось определить длительность")

    def _load_chapters_from_video(self):
        """Загрузить главы из видео"""
        if not self.current_video:
            QMessageBox.warning(self, "Предупреждение", "Выберите видео файл")
            return

        chapters = self.manager.extract_chapters(self.current_video)

        if not chapters:
            QMessageBox.information(
                self,
                "Информация",
                "В видео не найдено глав или произошла ошибка при извлечении"
            )
            return

        # Очищаем текущую таблицу
        self._clear_chapters()

        # Добавляем главы
        for chapter in chapters:
            self._add_chapter_to_table(chapter)

        QMessageBox.information(
            self,
            "Успех",
            f"Загружено {len(chapters)} глав из видео"
        )
        logger.info(f"Loaded {len(chapters)} chapters from {self.current_video}")

    def _add_chapter(self):
        """Добавить новую главу"""
        row_count = self.chapters_table.rowCount()

        # Определяем время начала новой главы
        if row_count == 0:
            start_time = 0.0
        else:
            # Берем конец последней главы
            last_end_item = self.chapters_table.item(row_count - 1, 2)
            if last_end_item:
                last_end_text = last_end_item.text()
                start_time = self._time_string_to_seconds(last_end_text)
            else:
                start_time = 0.0

        # Конец главы - либо через 60 секунд, либо конец видео
        end_time = min(start_time + 60.0, self.video_duration)

        chapter = Chapter(
            start_time=start_time,
            end_time=end_time,
            title=f"Chapter {row_count + 1}"
        )

        self._add_chapter_to_table(chapter)

    def _add_chapter_to_table(self, chapter: Chapter):
        """Добавить главу в таблицу"""
        row = self.chapters_table.rowCount()
        self.chapters_table.insertRow(row)

        # Номер
        num_item = QTableWidgetItem(str(row + 1))
        num_item.setFlags(num_item.flags() & ~Qt.ItemIsEditable)
        self.chapters_table.setItem(row, 0, num_item)

        # Начало
        start_item = QTableWidgetItem(self._seconds_to_time_string(chapter.start_time))
        self.chapters_table.setItem(row, 1, start_item)

        # Конец
        end_item = QTableWidgetItem(self._seconds_to_time_string(chapter.end_time))
        self.chapters_table.setItem(row, 2, end_item)

        # Название
        title_item = QTableWidgetItem(chapter.title)
        self.chapters_table.setItem(row, 3, title_item)

    def _remove_selected_chapter(self):
        """Удалить выбранную главу"""
        current_row = self.chapters_table.currentRow()
        if current_row >= 0:
            self.chapters_table.removeRow(current_row)
            self._renumber_chapters()

    def _clear_chapters(self):
        """Очистить все главы"""
        self.chapters_table.setRowCount(0)

    def _renumber_chapters(self):
        """Перенумеровать главы после удаления"""
        for row in range(self.chapters_table.rowCount()):
            num_item = QTableWidgetItem(str(row + 1))
            num_item.setFlags(num_item.flags() & ~Qt.ItemIsEditable)
            self.chapters_table.setItem(row, 0, num_item)

    def _import_chapters(self):
        """Импортировать главы из FFMETADATA файла"""
        file, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите FFMETADATA файл",
            "",
            "Metadata Files (*.txt *.ffmetadata);;All Files (*.*)"
        )

        if not file:
            return

        metadata, chapters = self.manager.parse_ffmetadata_file(file)

        if not chapters:
            QMessageBox.warning(
                self,
                "Предупреждение",
                "Не удалось найти главы в файле метаданных"
            )
            return

        # Очищаем и добавляем главы
        self._clear_chapters()
        for chapter in chapters:
            self._add_chapter_to_table(chapter)

        QMessageBox.information(
            self,
            "Успех",
            f"Импортировано {len(chapters)} глав"
        )
        logger.info(f"Imported {len(chapters)} chapters from {file}")

    def _export_chapters(self):
        """Экспортировать главы в FFMETADATA файл"""
        chapters = self._get_chapters_from_table()

        if not chapters:
            QMessageBox.warning(self, "Предупреждение", "Нет глав для экспорта")
            return

        file, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить FFMETADATA файл",
            "metadata.txt",
            "Metadata Files (*.txt);;All Files (*.*)"
        )

        if not file:
            return

        # Создаем файл метаданных
        output = self.manager.create_ffmetadata_file(chapters, output_file=file)

        if output:
            QMessageBox.information(
                self,
                "Успех",
                f"Главы экспортированы в:\n{file}"
            )
            logger.info(f"Exported {len(chapters)} chapters to {file}")
        else:
            QMessageBox.critical(
                self,
                "Ошибка",
                "Не удалось экспортировать главы"
            )

    def _apply_chapters_to_video(self):
        """Добавить главы к видео"""
        if not self.current_video:
            QMessageBox.warning(self, "Предупреждение", "Выберите видео файл")
            return

        chapters = self._get_chapters_from_table()

        if not chapters:
            QMessageBox.warning(self, "Предупреждение", "Добавьте хотя бы одну главу")
            return

        # Выбираем выходной файл
        default_name = Path(self.current_video).stem + "_with_chapters" + Path(self.current_video).suffix
        output_file, _ = QFileDialog.getSaveFileName(
            self,
            "Сохранить видео с главами",
            default_name,
            "Video Files (*.mp4 *.mkv *.mov);;All Files (*.*)"
        )

        if not output_file:
            return

        # Emit signal
        self.add_chapters_requested.emit(chapters, self.current_video, output_file)
        logger.info(f"Requested add chapters: {len(chapters)} chapters to {output_file}")

    def _split_video_by_chapters(self):
        """Разделить видео по главам"""
        if not self.current_video:
            QMessageBox.warning(self, "Предупреждение", "Выберите видео файл")
            return

        chapters = self._get_chapters_from_table()

        if not chapters:
            QMessageBox.warning(self, "Предупреждение", "Добавьте хотя бы одну главу")
            return

        # Выбираем папку для сохранения
        output_folder = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для сохранения глав"
        )

        if not output_folder:
            return

        # Emit signal
        self.split_by_chapters_requested.emit(chapters, self.current_video, output_folder)
        logger.info(f"Requested split video: {len(chapters)} chapters to {output_folder}")

    def _get_chapters_from_table(self) -> list:
        """Получить список глав из таблицы"""
        chapters = []

        for row in range(self.chapters_table.rowCount()):
            start_item = self.chapters_table.item(row, 1)
            end_item = self.chapters_table.item(row, 2)
            title_item = self.chapters_table.item(row, 3)

            if not (start_item and end_item and title_item):
                continue

            start_time = self._time_string_to_seconds(start_item.text())
            end_time = self._time_string_to_seconds(end_item.text())
            title = title_item.text()

            chapter = Chapter(
                start_time=start_time,
                end_time=end_time,
                title=title
            )
            chapters.append(chapter)

        return chapters

    def _seconds_to_time_string(self, seconds: float) -> str:
        """Конвертация секунд в строку времени MM:SS"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def _time_string_to_seconds(self, time_str: str) -> float:
        """Конвертация строки времени в секунды"""
        try:
            parts = time_str.split(':')
            if len(parts) == 2:
                minutes, seconds = parts
                return int(minutes) * 60 + int(seconds)
            elif len(parts) == 3:
                hours, minutes, seconds = parts
                return int(hours) * 3600 + int(minutes) * 60 + int(seconds)
            else:
                return 0.0
        except ValueError:
            return 0.0

    def _show_context_menu(self, position):
        """Показать контекстное меню"""
        menu = QMenu(self)

        add_action = QAction("➕ Добавить главу", self)
        add_action.triggered.connect(self._add_chapter)
        menu.addAction(add_action)

        if self.chapters_table.currentRow() >= 0:
            remove_action = QAction("➖ Удалить главу", self)
            remove_action.triggered.connect(self._remove_selected_chapter)
            menu.addAction(remove_action)

        menu.addSeparator()

        clear_action = QAction("🗑️ Очистить все", self)
        clear_action.triggered.connect(self._clear_chapters)
        menu.addAction(clear_action)

        menu.exec(self.chapters_table.mapToGlobal(position))
