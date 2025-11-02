import logging
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QTextEdit,
    QPushButton, QHBoxLayout
)
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QTextCursor, QColor


class LogHandler(logging.Handler, QObject):
    """Кастомный обработчик логов для отправки в GUI"""
    log_signal = Signal(str, str)  # message, level

    def __init__(self):
        logging.Handler.__init__(self)
        QObject.__init__(self)

    def emit(self, record):
        """Отправка лог сообщения"""
        msg = self.format(record)
        level = record.levelname
        self.log_signal.emit(msg, level)


class LoggerWidget(QDialog):
    """Окно отображения логов в реальном времени"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Логирование")
        self.setMinimumSize(800, 600)

        self._init_ui()
        self._setup_logging()
        self._load_existing_logs()

    def _init_ui(self):
        """Инициализация UI"""
        layout = QVBoxLayout(self)

        # Текстовое поле для логов
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                font-family: 'Consolas', 'Courier New', monospace;
                font-size: 10pt;
                border: 1px solid #3E3E3E;
                border-radius: 5px;
                padding: 8px;
            }
        """)
        layout.addWidget(self.log_text)

        # Кнопки управления
        button_layout = QHBoxLayout()

        self.clear_button = QPushButton("Очистить")
        self.clear_button.clicked.connect(self._clear_logs)
        button_layout.addWidget(self.clear_button)

        button_layout.addStretch()

        self.close_button = QPushButton("Закрыть")
        self.close_button.clicked.connect(self.close)
        button_layout.addWidget(self.close_button)

        layout.addLayout(button_layout)

    def _setup_logging(self):
        """Настройка логирования"""
        # Создаем обработчик логов
        self.log_handler = LogHandler()
        self.log_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )

        # Подключаем сигнал
        self.log_handler.log_signal.connect(self._append_log)

        # Добавляем обработчик к root logger
        root_logger = logging.getLogger()
        root_logger.addHandler(self.log_handler)
        root_logger.setLevel(logging.DEBUG)

    def _append_log(self, message: str, level: str):
        """Добавление лог сообщения с цветовой разметкой"""
        # Цветовая схема для разных уровней логирования
        colors = {
            'DEBUG': '#808080',      # Серый
            'INFO': '#4EC9B0',       # Бирюзовый
            'WARNING': '#CE9178',    # Оранжевый
            'ERROR': '#F48771',      # Красный
            'CRITICAL': '#FF0000'    # Ярко-красный
        }

        color = colors.get(level, '#D4D4D4')

        # Форматируем сообщение с HTML
        html_message = f'<span style="color: {color};">{message}</span><br>'

        # Добавляем в текстовое поле
        cursor = self.log_text.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.log_text.setTextCursor(cursor)
        self.log_text.insertHtml(html_message)

        # Автопрокрутка вниз
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())

    def _clear_logs(self):
        """Очистка логов"""
        self.log_text.clear()

    def _load_existing_logs(self):
        """Загрузить существующие логи из файла"""
        try:
            # Получаем путь к текущему лог-файлу
            from pathlib import Path
            log_dir = Path.home() / '.ffmpeg_converter' / 'logs'

            if not log_dir.exists():
                return

            # Находим самый свежий лог-файл
            log_files = sorted(log_dir.glob('converter_*.log'), key=lambda x: x.stat().st_mtime, reverse=True)

            if not log_files:
                return

            current_log = log_files[0]

            # Читаем содержимое лог-файла
            with open(current_log, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Добавляем существующие логи в виджет
            for line in lines:
                line = line.strip()
                if not line:
                    continue

                # Определяем уровень логирования по содержимому строки
                level = 'INFO'
                if ' - DEBUG - ' in line:
                    level = 'DEBUG'
                elif ' - INFO - ' in line:
                    level = 'INFO'
                elif ' - WARNING - ' in line:
                    level = 'WARNING'
                elif ' - ERROR - ' in line:
                    level = 'ERROR'
                elif ' - CRITICAL - ' in line:
                    level = 'CRITICAL'

                self._append_log(line, level)

        except Exception as e:
            logging.error(f"Ошибка при загрузке существующих логов: {e}")

    def closeEvent(self, event):
        """Обработка закрытия окна"""
        # Удаляем обработчик логов
        root_logger = logging.getLogger()
        root_logger.removeHandler(self.log_handler)
        event.accept()
