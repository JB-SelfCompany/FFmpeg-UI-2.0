import sys
import os
import logging
from pathlib import Path
from datetime import datetime

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QLocale
from PySide6.QtGui import QIcon, QFont

from ui.main_window import MainWindow


def setup_logging():
    """Настройка логирования"""
    log_dir = Path.home() / '.ffmpeg_converter' / 'logs'
    log_dir.mkdir(parents=True, exist_ok=True)
    
    log_file = log_dir / f'converter_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    
    # Форматирование
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # File handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    logging.info(f"Логирование настроено, файл: {log_file}")


def setup_app_metadata():
    """Настройка метаданных приложения"""
    QApplication.setApplicationName("FFmpeg UI 2.0")
    QApplication.setApplicationVersion("1.0.0")
    QApplication.setOrganizationName("MediaTools")
    QApplication.setOrganizationDomain("mediatools.local")


def setup_high_dpi():
    """Настройка High DPI поддержки для Qt6"""
    try:
        QApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
    except AttributeError:
        pass


def get_resource_path(relative_path: str) -> Path:
    """Получить путь к ресурсу"""
    if getattr(sys, 'frozen', False):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent
    return base_path / relative_path


def main():
    """Главная функция запуска"""
    # Настройка логирования
    setup_logging()
    logging.info("=" * 80)
    logging.info("FFmpeg UI 2.0 запущен")
    logging.info("=" * 80)
    
    # Настройка High DPI
    setup_high_dpi()
    
    # Создание приложения
    app = QApplication(sys.argv)
    
    # Настройка метаданных
    setup_app_metadata()
    
    # Установка локали
    QLocale.setDefault(QLocale(QLocale.Russian, QLocale.Russia))

    # Установка шрифта
    font = QFont("Segoe UI", 10)
    app.setFont(font)
    
    # Установка иконки
    icon_path = get_resource_path("resources/icons/app_icon.png")
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    
    # Создание главного окна
    try:
        main_window = MainWindow()
        main_window.show()
        logging.info("Главное окно создано и отображено")
    except Exception as e:
        logging.error(f"Критическая ошибка при создании главного окна: {e}", exc_info=True)
        return 1
    
    # Запуск event loop
    result = app.exec()
    logging.info(f"Приложение завершено с кодом: {result}")
    return result


if __name__ == "__main__":
    sys.exit(main())