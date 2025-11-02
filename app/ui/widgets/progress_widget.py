from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QProgressBar, QFrame
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont


class ProgressWidget(QWidget):
    """Виджет прогресса"""
    
    def __init__(self):
        super().__init__()
        self._init_ui()
        self.hide()
    
    def _init_ui(self):
        """Инициализация UI"""
        self.setObjectName("progressWidget")
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Заголовок
        self.title_label = QLabel("⚙️ Процесс конвертации")
        self.title_label.setStyleSheet("font-size: 15px; font-weight: bold; color: #333;")
        layout.addWidget(self.title_label)

        # Метка прохода (для двухпроходного кодирования)
        self.pass_label = QLabel("")
        self.pass_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #1976D2;")
        self.pass_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pass_label.hide()
        layout.addWidget(self.pass_label)
        
        # Прогресс-бар
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFixedHeight(28)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #2196F3;
                border-radius: 8px;
                text-align: center;
                background-color: #E3F2FD;
                color: #1976D2;
                font-weight: bold;
                font-size: 13px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #64B5F6, stop:1 #2196F3);
                border-radius: 6px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Информация о времени
        time_layout = QHBoxLayout()
        time_layout.setSpacing(15)
        
        self.current_time_label = QLabel("⏱ Обработано: 00:00:00")
        self.current_time_label.setStyleSheet("font-size: 12px; color: #555;")
        time_layout.addWidget(self.current_time_label)
        
        self.eta_label = QLabel("⏰ Осталось: 00:00:00")
        self.eta_label.setStyleSheet("font-size: 12px; color: #555; font-weight: bold;")
        time_layout.addWidget(self.eta_label)
        
        self.speed_label = QLabel("⚡ Скорость: 0.00x")
        self.speed_label.setStyleSheet("font-size: 12px; color: #555;")
        time_layout.addWidget(self.speed_label)
        
        time_layout.addStretch()
        layout.addLayout(time_layout)
        
        # Стиль виджета
        self.setStyleSheet("""
            #progressWidget {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #F5F5F5, stop:1 #E0E0E0);
                border: 2px solid #BDBDBD;
                border-radius: 10px;
            }
        """)
    
    def update_progress(self, data: dict):
        """Обновление прогресса"""
        progress = data.get('progress', 0)
        current_time = data.get('current_time', '00:00:00')
        eta = data.get('eta', '00:00:00')
        speed = data.get('speed', '0.00x')
        current_pass = data.get('current_pass', 1)
        total_passes = data.get('total_passes', 1)

        # Отображение информации о проходе
        if total_passes > 1:
            self.pass_label.setText(f"🔄 Проход {current_pass} из {total_passes}")
            self.pass_label.show()
        else:
            self.pass_label.hide()

        self.progress_bar.setValue(progress)
        self.current_time_label.setText(f"⏱ Обработано: {current_time}")
        self.eta_label.setText(f"⏰ Осталось: {eta}")
        self.speed_label.setText(f"⚡ Скорость: {speed}")
    
    def show_progress(self):
        """Показать виджет прогресса"""
        self.progress_bar.setValue(0)
        self.current_time_label.setText("⏱ Обработано: 00:00:00")
        self.eta_label.setText("⏰ Осталось: Рассчитывается...")
        self.speed_label.setText("⚡ Скорость: 0.00x")
        self.pass_label.hide()
        self.show()
    
    def hide_progress(self):
        """Скрыть виджет прогресса"""
        self.hide()