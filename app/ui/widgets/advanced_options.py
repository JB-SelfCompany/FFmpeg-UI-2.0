from PySide6.QtWidgets import (
    QGroupBox, QVBoxLayout, QHBoxLayout,
    QLabel, QComboBox, QLineEdit, QCheckBox, QPushButton
)
from PySide6.QtCore import Qt
import logging

logger = logging.getLogger(__name__)


class AdvancedOptions(QGroupBox):
    """Виджет продвинутых опций с GPU"""
    
    def __init__(self):
        super().__init__("⚙ Дополнительные настройки")
        self.gpu_list = []
        self._init_ui()
    
    def _init_ui(self):
        """Инициализация UI"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # GPU Acceleration
        gpu_layout = QHBoxLayout()
        gpu_label = QLabel("GPU ускорение:")
        gpu_label.setMinimumWidth(120)
        self.gpu_combo = QComboBox()
        self.gpu_combo.addItem("Авто (рекомендуется)", "auto")
        self.gpu_combo.addItem("CPU (без ускорения)", "none")
        self.gpu_combo.setToolTip("Выберите GPU для аппаратного ускорения кодирования и декодирования")
        self.gpu_combo.currentIndexChanged.connect(self._on_gpu_changed)
        gpu_layout.addWidget(gpu_label)
        gpu_layout.addWidget(self.gpu_combo, 1)
        layout.addLayout(gpu_layout)
        
        # Preset
        preset_layout = QHBoxLayout()
        preset_label = QLabel("Preset:")
        preset_label.setMinimumWidth(120)
        self.preset_combo = QComboBox()
        self.preset_combo.addItems([
            "ultrafast", "superfast", "veryfast", "faster",
            "fast", "medium", "slow", "slower", "veryslow"
        ])
        self.preset_combo.setCurrentText("medium")
        self.preset_combo.setToolTip(
            "Баланс скорости и качества кодирования:\n\n"
            "• CPU (x264/x265): используется напрямую\n"
            "• NVENC: маппится в p1-p7 (ultrafast→p1, veryslow→p7)\n"
            "• QSV: поддерживает veryfast-veryslow\n"
            "• AMF: маппится в speed/balanced/quality\n\n"
            "Медленнее = лучше качество при том же размере файла"
        )
        preset_layout.addWidget(preset_label)
        preset_layout.addWidget(self.preset_combo, 1)
        layout.addLayout(preset_layout)
        
        # CPU-used (для VP9)
        cpu_used_layout = QHBoxLayout()
        cpu_used_label = QLabel("CPU-used (VP9):")
        cpu_used_label.setMinimumWidth(120)
        self.cpu_used_combo = QComboBox()
        self.cpu_used_combo.addItems(["0", "1", "2", "3", "4", "5"])
        self.cpu_used_combo.setCurrentText("2")
        self.cpu_used_combo.setToolTip("Скорость для VP9 (0=медленнее/лучше, 5=быстрее)")
        cpu_used_layout.addWidget(cpu_used_label)
        cpu_used_layout.addWidget(self.cpu_used_combo, 1)
        layout.addLayout(cpu_used_layout)
        
        # Row-MT
        self.row_mt_check = QCheckBox("Row-MT (многопоточность для VP9)")
        self.row_mt_check.setChecked(True)
        layout.addWidget(self.row_mt_check)

        # Two-Pass Encoding
        self.two_pass_check = QCheckBox("Two-Pass Encoding (двухпроходное кодирование)")
        self.two_pass_check.setToolTip(
            "Двухпроходное кодирование для лучшего качества:\n\n"
            "• Проход 1: анализирует видео и собирает статистику\n"
            "• Проход 2: использует статистику для оптимального распределения битрейта\n\n"
            "Преимущества:\n"
            "• Лучшее качество при заданном размере файла\n"
            "• Более точный контроль битрейта\n"
            "• Особенно эффективно для CBR/ABR кодирования\n\n"
            "Недостатки:\n"
            "• Требует примерно вдвое больше времени\n"
            "• Не работает с CRF-режимом (CRF уже оптимален)"
        )
        self.two_pass_check.setChecked(False)
        layout.addWidget(self.two_pass_check)

        # Дополнительные параметры
        extra_layout = QVBoxLayout()
        extra_label = QLabel("Дополнительные параметры FFmpeg:")
        self.extra_params_input = QLineEdit()
        self.extra_params_input.setPlaceholderText("Например: -profile:v high -level 4.1")
        self.extra_params_input.setToolTip("Дополнительные аргументы командной строки FFmpeg")
        extra_layout.addWidget(extra_label)
        extra_layout.addWidget(self.extra_params_input)
        layout.addLayout(extra_layout)
        
        # Info кнопка
        info_btn = QPushButton("ℹ Информация о GPU")
        info_btn.clicked.connect(self._show_gpu_info)
        layout.addWidget(info_btn)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def set_gpu_list(self, gpu_list):
        """Установить список GPU"""
        self.gpu_list = gpu_list
        self.gpu_combo.clear()
        
        for gpu in gpu_list:
            self.gpu_combo.addItem(gpu['name'], gpu['id'])
        
        logger.info(f"Список GPU обновлен: {[g['name'] for g in gpu_list]}")
    
    def _on_gpu_changed(self, index):
        """Обработка смены GPU"""
        gpu_id = self.gpu_combo.itemData(index)
        gpu_name = self.gpu_combo.itemText(index)
        logger.info(f"Выбран GPU: {gpu_name} ({gpu_id})")
    
    def _show_gpu_info(self):
        """Показать информацию о GPU"""
        from PySide6.QtWidgets import QMessageBox
        
        info_text = "Обнаруженные GPU:\n\n"
        
        if self.gpu_list:
            for gpu in self.gpu_list:
                info_text += f"• {gpu['name']}\n"
        else:
            info_text += "GPU не обнаружены или FFmpeg не поддерживает GPU ускорение."
        
        info_text += "\n\nПоддерживаемые технологии:\n"
        info_text += "• NVIDIA: NVENC/NVDEC (CUDA)\n"
        info_text += "• Intel: Quick Sync (QSV)\n"
        info_text += "• AMD: AMF (Windows) / VA-API (Linux)"
        
        QMessageBox.information(self, "Информация о GPU", info_text)
    
    def get_preset(self) -> str:
        """Получить preset"""
        return self.preset_combo.currentText()
    
    def get_cpu_used(self) -> int:
        """Получить cpu-used"""
        return int(self.cpu_used_combo.currentText())
    
    def get_row_mt(self) -> bool:
        """Получить row-mt"""
        return self.row_mt_check.isChecked()

    def is_two_pass_enabled(self) -> bool:
        """Проверить, включено ли двухпроходное кодирование"""
        return self.two_pass_check.isChecked()

    def get_extra_params(self) -> str:
        """Получить дополнительные параметры"""
        return self.extra_params_input.text().strip()
    
    def get_selected_gpu(self) -> str:
        """Получить выбранный GPU"""
        return self.gpu_combo.currentData()