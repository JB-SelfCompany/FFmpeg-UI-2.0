from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QSlider, QSpinBox, QCheckBox,
    QGroupBox, QGridLayout, QSizePolicy, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, Signal
import logging

logger = logging.getLogger(__name__)


class VideoOptions(QWidget):
    """Виджет настроек видео с автовыбором"""
    
    codec_auto_selected = Signal(str, str)  # codec_name, reason
    
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.auto_codec_mode = False
        self._init_ui()
        
    def _init_ui(self):
        """Инициализация UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)
        
        # Группа видео
        group = QGroupBox("🎥 Видео")
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        group_layout = QGridLayout(group)
        group_layout.setSpacing(5)
        group_layout.setContentsMargins(8, 8, 8, 8)
        
        # Кодек с кнопкой авто
        row = 0
        group_layout.addWidget(QLabel("Кодек:"), row, 0)
        
        codec_layout = QHBoxLayout()
        self.codec_combo = QComboBox()
        self.codec_combo.addItems([
            "Авто (рекомендуется)",
            "H.264 / AVC (libx264)",
            "H.265 / HEVC (libx265)",
            "H.266 / VVC (libvvenc)",
            "VP9 (libvpx-vp9)",
            "AV1 (libaom-av1)",
            "AV1 (SVT-AV1)",
            "MJPEG (Motion JPEG)",
            "Apple ProRes",
            "DNxHD / DNxHR",
            "JPEG 2000",
            "Theora",
            "MPEG-2",
            "Copy (без перекодирования)"
        ])
        self.codec_combo.setCurrentText("Авто (рекомендуется)")
        self.codec_combo.setToolTip(
            "Видео кодек:\n"
            "• Авто - автоматический выбор лучшего кодека\n"
            "• H.264 - универсальный, быстрый, максимальная совместимость\n"
            "• H.265 - лучшее сжатие на 30-50%, медленнее\n"
            "• H.266/VVC - следующее поколение, на 30% лучше H.265\n"
            "• VP9 - для WebM, открытый, хорошее сжатие\n"
            "• AV1 (libaom) - лучшее сжатие, очень медленный\n"
            "• AV1 (SVT-AV1) - быстрый AV1 энкодер от Intel/Netflix\n"
            "• MJPEG - покадровое сжатие, быстрое, для редактирования\n"
            "• ProRes - профессиональный кодек Apple, высокое качество\n"
            "• DNxHD/DNxHR - Avid кодек, для монтажа\n"
            "• JPEG 2000 - архивирование высокого качества\n"
            "• Theora - открытый кодек для OGG\n"
            "• MPEG-2 - DVD/Broadcast стандарт\n"
            "• Copy - копирование без перекодирования"
        )
        self.codec_combo.currentTextChanged.connect(self._on_codec_changed)
        codec_layout.addWidget(self.codec_combo, stretch=1)
        
        # Кнопка информации о выборе
        self.codec_info_btn = QPushButton("ℹ")
        self.codec_info_btn.setMaximumWidth(30)
        self.codec_info_btn.setToolTip("Информация об автоматическом выборе кодека")
        self.codec_info_btn.clicked.connect(self._show_codec_info)
        codec_layout.addWidget(self.codec_info_btn)
        
        group_layout.addLayout(codec_layout, row, 1)
        
        # Метка автовыбора
        row += 1
        self.auto_codec_label = QLabel("")
        self.auto_codec_label.setWordWrap(True)
        self.auto_codec_label.setStyleSheet("""
            QLabel {
                color: #2196F3;
                font-size: 9px;
                padding: 2px;
            }
        """)
        self.auto_codec_label.setVisible(False)
        group_layout.addWidget(self.auto_codec_label, row, 1)
        
        # CRF
        row += 1
        group_layout.addWidget(QLabel("CRF:"), row, 0)
        crf_layout = QHBoxLayout()
        self.crf_slider = QSlider(Qt.Horizontal)
        self.crf_slider.setMinimum(0)
        self.crf_slider.setMaximum(51)
        self.crf_slider.setValue(23)
        self.crf_slider.setToolTip(
            "Constant Rate Factor:\n"
            "• 0 = без потерь (огромный размер)\n"
            "• 18-23 = визуально без потерь\n"
            "• 23-28 = хорошее качество (рекомендуется)\n"
            "• 28+ = заметное снижение качества"
        )
        self.crf_spinbox = QSpinBox()
        self.crf_spinbox.setMinimum(0)
        self.crf_spinbox.setMaximum(51)
        self.crf_spinbox.setValue(23)
        self.crf_slider.valueChanged.connect(self.crf_spinbox.setValue)
        self.crf_spinbox.valueChanged.connect(self.crf_slider.setValue)
        crf_layout.addWidget(self.crf_slider)
        crf_layout.addWidget(self.crf_spinbox)
        group_layout.addLayout(crf_layout, row, 1)
        
        # FPS
        row += 1
        group_layout.addWidget(QLabel("FPS:"), row, 0)
        self.fps_spinbox = QSpinBox()
        self.fps_spinbox.setMinimum(0)
        self.fps_spinbox.setMaximum(240)
        self.fps_spinbox.setValue(0)
        self.fps_spinbox.setSpecialValueText("Авто")
        self.fps_spinbox.setToolTip(
            "Частота кадров:\n"
            "• Авто - сохранить оригинальную\n"
            "• 24 - кино\n"
            "• 30 - стандартное видео\n"
            "• 60 - плавное видео\n"
            "• 120+ - high framerate"
        )
        group_layout.addWidget(self.fps_spinbox, row, 1)
        
        # Разрешение
        row += 1
        group_layout.addWidget(QLabel("Разрешение:"), row, 0)
        self.resolution_combo = QComboBox()
        self.resolution_combo.addItems([
            "original",
            "3840x2160 (4K)",
            "2560x1440 (2K)",
            "1920x1080 (FHD)",
            "1280x720 (HD)",
            "854x480 (SD)"
        ])
        self.resolution_combo.setToolTip(
            "Разрешение видео:\n"
            "• original - без изменения\n"
            "• 4K - ультра высокое\n"
            "• 1080p - Full HD\n"
            "• 720p - HD\n"
            "• 480p - стандартное"
        )
        group_layout.addWidget(self.resolution_combo, row, 1)
        
        # Битрейт
        row += 1
        group_layout.addWidget(QLabel("Битрейт:"), row, 0)
        self.bitrate_combo = QComboBox()
        self.bitrate_combo.setEditable(True)
        self.bitrate_combo.addItems([
            "Авто (CRF)",
            "500k",
            "1M",
            "2M",
            "5M",
            "10M",
            "20M"
        ])
        self.bitrate_combo.setToolTip(
            "Битрейт видео:\n"
            "• Авто (CRF) - переменный битрейт, лучше\n"
            "• 1-2M - для 720p\n"
            "• 5-10M - для 1080p\n"
            "• 20M+ - для 4K"
        )
        group_layout.addWidget(self.bitrate_combo, row, 1)

        # === НОВЫЕ ОПЦИИ ===

        # Aspect Ratio
        row += 1
        self.aspect_checkbox = QCheckBox("Переопределить Aspect Ratio:")
        self.aspect_checkbox.setToolTip("Изменить соотношение сторон видео")
        self.aspect_checkbox.stateChanged.connect(self._on_aspect_changed)
        group_layout.addWidget(self.aspect_checkbox, row, 0)

        self.aspect_combo = QComboBox()
        self.aspect_combo.addItems([
            "16:9 (широкоэкранный)",
            "4:3 (стандартный)",
            "21:9 (ультраширокий)",
            "1:1 (квадратный)",
            "9:16 (вертикальный)"
        ])
        self.aspect_combo.setEnabled(False)
        self.aspect_combo.setToolTip(
            "Aspect Ratio (соотношение сторон):\n"
            "• 16:9 - стандарт для HD/Full HD\n"
            "• 4:3 - старый стандарт\n"
            "• 21:9 - кинематограф\n"
            "• 1:1 - Instagram квадрат\n"
            "• 9:16 - вертикальное видео (TikTok/Stories)"
        )
        group_layout.addWidget(self.aspect_combo, row, 1)

        # Pixel Format
        row += 1
        self.pix_fmt_checkbox = QCheckBox("Pixel Format:")
        self.pix_fmt_checkbox.setToolTip("Формат представления пикселей")
        self.pix_fmt_checkbox.stateChanged.connect(self._on_pixfmt_changed)
        group_layout.addWidget(self.pix_fmt_checkbox, row, 0)

        self.pix_fmt_combo = QComboBox()
        self.pix_fmt_combo.addItems([
            "yuv420p (стандарт)",
            "yuv422p (профессиональный)",
            "yuv444p (без потерь цвета)",
            "yuv420p10le (10-bit HDR)",
            "rgb24 (RGB без сжатия)"
        ])
        self.pix_fmt_combo.setEnabled(False)
        self.pix_fmt_combo.setToolTip(
            "Pixel Format:\n"
            "• yuv420p - стандарт, максимальная совместимость\n"
            "• yuv422p - для профессиональной работы\n"
            "• yuv444p - максимальное качество цвета\n"
            "• yuv420p10le - для 10-bit HDR видео\n"
            "• rgb24 - без сжатия (огромный размер)"
        )
        group_layout.addWidget(self.pix_fmt_combo, row, 1)

        # Force Keyframes
        row += 1
        self.keyframes_checkbox = QCheckBox("Принудительные ключевые кадры:")
        self.keyframes_checkbox.setToolTip(
            "Вставлять ключевые кадры через заданный интервал\n"
            "Полезно для потокового видео и точного seeking"
        )
        self.keyframes_checkbox.stateChanged.connect(self._on_keyframes_changed)
        group_layout.addWidget(self.keyframes_checkbox, row, 0)

        keyframes_layout = QHBoxLayout()
        self.keyframes_interval = QSpinBox()
        self.keyframes_interval.setMinimum(1)
        self.keyframes_interval.setMaximum(300)
        self.keyframes_interval.setValue(2)
        self.keyframes_interval.setSuffix(" сек")
        self.keyframes_interval.setEnabled(False)
        self.keyframes_interval.setToolTip("Интервал между ключевыми кадрами в секундах")
        keyframes_layout.addWidget(self.keyframes_interval)

        self.keyframes_chapters = QCheckBox("В начале глав")
        self.keyframes_chapters.setEnabled(False)
        self.keyframes_chapters.setToolTip("Вставлять ключевые кадры в начале каждой главы")
        keyframes_layout.addWidget(self.keyframes_chapters)
        keyframes_layout.addStretch()

        group_layout.addLayout(keyframes_layout, row, 1)

        group_layout.setRowStretch(row + 1, 1)
        main_layout.addWidget(group)
    
    def _on_codec_changed(self, text: str):
        """Обработка смены кодека"""
        if text == "Авто (рекомендуется)":
            self.auto_codec_mode = True
            self.auto_codec_label.setVisible(True)
            logger.info("Включен режим автовыбора кодека")
        else:
            self.auto_codec_mode = False
            self.auto_codec_label.setVisible(False)

    def _on_aspect_changed(self, state):
        """Обработчик изменения aspect ratio"""
        from PySide6.QtCore import Qt
        enabled = state == Qt.CheckState.Checked.value
        self.aspect_combo.setEnabled(enabled)

    def _on_pixfmt_changed(self, state):
        """Обработчик изменения pixel format"""
        from PySide6.QtCore import Qt
        enabled = state == Qt.CheckState.Checked.value
        self.pix_fmt_combo.setEnabled(enabled)

    def _on_keyframes_changed(self, state):
        """Обработчик изменения force keyframes"""
        from PySide6.QtCore import Qt
        enabled = state == Qt.CheckState.Checked.value
        self.keyframes_interval.setEnabled(enabled)
        self.keyframes_chapters.setEnabled(enabled)
    
    def set_auto_selected_codec(self, codec_name: str, reason: str):
        """Установить автоматически выбранный кодек"""
        if self.auto_codec_mode:
            self.auto_codec_label.setText(f"🤖 Выбран: {codec_name}\n💡 {reason}")
            self.auto_codec_label.setVisible(True)
            self.codec_auto_selected.emit(codec_name, reason)
            logger.info(f"Автовыбран кодек: {codec_name} - {reason}")
    
    def _show_codec_info(self):
        """Показать информацию о кодеках"""
        info = (
            "<h3>Информация о кодеках</h3>"
            "<table border='1' cellpadding='5' style='border-collapse: collapse;'>"
            "<tr><th>Кодек</th><th>Сжатие</th><th>Скорость</th><th>Совместимость</th><th>GPU</th></tr>"
            "<tr><td><b>H.264</b></td><td>★★★★☆</td><td>★★★★★</td><td>★★★★★</td><td>★★★★★</td></tr>"
            "<tr><td><b>H.265</b></td><td>★★★★★</td><td>★★★☆☆</td><td>★★★☆☆</td><td>★★★★☆</td></tr>"
            "<tr><td><b>VP9</b></td><td>★★★★☆</td><td>★★★☆☆</td><td>★★★★☆</td><td>★★★☆☆</td></tr>"
            "<tr><td><b>AV1 (libaom)</b></td><td>★★★★★</td><td>★★☆☆☆</td><td>★★★★☆</td><td>★★★☆☆</td></tr>"
            "<tr><td><b>AV1 (SVT-AV1)</b></td><td>★★★★★</td><td>★★★★☆</td><td>★★★★☆</td><td>★★★★☆</td></tr>"
            "</table>"
            "<br>"
            "<b>Рекомендации по выбору:</b><br>"
            "• <b>Универсальность</b>: H.264 - работает везде<br>"
            "• <b>Качество/Размер</b>: H.265 или AV1 - лучшее сжатие<br>"
            "• <b>Скорость</b>: H.264 или SVT-AV1 - быстрые энкодеры<br>"
            "• <b>Баланс</b>: SVT-AV1 - отличное сжатие + высокая скорость<br>"
            "• <b>WebM контейнер</b>: VP9 или AV1<br>"
            "• <b>Архивирование</b>: H.265 или AV1<br>"
            "<br>"
            "<b>Режим Авто:</b> автоматически выбирает оптимальный кодек<br>"
            "на основе контейнера, GPU возможностей и цели конвертации."
        )
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Информация о кодеках")
        msg.setTextFormat(Qt.RichText)
        msg.setText(info)
        msg.setIcon(QMessageBox.Information)
        msg.exec()
    
    def get_video_codec(self) -> str:
        """Получить видео кодек"""
        codec_text = self.codec_combo.currentText()

        if codec_text == "Авто (рекомендуется)":
            return "auto"

        codec_map = {
            "H.264 / AVC (libx264)": "libx264",
            "H.265 / HEVC (libx265)": "libx265",
            "H.266 / VVC (libvvenc)": "libvvenc",
            "VP9 (libvpx-vp9)": "libvpx-vp9",
            "AV1 (libaom-av1)": "libaom-av1",
            "AV1 (SVT-AV1)": "libsvtav1",
            "MJPEG (Motion JPEG)": "mjpeg",
            "Apple ProRes": "prores_ks",
            "DNxHD / DNxHR": "dnxhd",
            "JPEG 2000": "jpeg2000",
            "Theora": "libtheora",
            "MPEG-2": "mpeg2video",
            "Copy (без перекодирования)": "copy"
        }
        return codec_map.get(codec_text, "libx264")
    
    def is_auto_mode(self) -> bool:
        """Проверка режима авто"""
        return self.auto_codec_mode
    
    def get_crf(self) -> int:
        """Получить CRF"""
        return self.crf_spinbox.value()
    
    def set_crf(self, value: int):
        """Установить CRF"""
        self.crf_spinbox.setValue(value)
    
    def get_fps(self) -> Optional[int]:
        """Получить FPS"""
        fps = self.fps_spinbox.value()
        return fps if fps > 0 else None
    
    def get_resolution(self) -> Optional[str]:
        """Получить разрешение"""
        res = self.resolution_combo.currentText()
        if res == "original":
            return None
        return res.split()[0]
    
    def get_bitrate(self) -> Optional[str]:
        """Получить битрейт"""
        bitrate = self.bitrate_combo.currentText()
        if "Авто" in bitrate or not bitrate:
            return None
        return bitrate

    # === НОВЫЕ МЕТОДЫ ДЛЯ НОВЫХ ОПЦИЙ ===

    def get_aspect_ratio(self) -> Optional[str]:
        """
        Получить aspect ratio

        Returns:
            Строка вида "16:9" или None если не включено
        """
        if not self.aspect_checkbox.isChecked():
            return None

        aspect_text = self.aspect_combo.currentText()
        # Извлекаем только соотношение (до пробела)
        return aspect_text.split()[0]

    def get_pixel_format(self) -> Optional[str]:
        """
        Получить pixel format

        Returns:
            Строка вида "yuv420p" или None если не включено
        """
        if not self.pix_fmt_checkbox.isChecked():
            return None

        pix_fmt_text = self.pix_fmt_combo.currentText()
        # Извлекаем только формат (до пробела)
        return pix_fmt_text.split()[0]

    def get_force_keyframes(self) -> Optional[str]:
        """
        Получить строку для -force_key_frames параметра

        Returns:
            Строка для FFmpeg или None если не включено
        """
        if not self.keyframes_checkbox.isChecked():
            return None

        # Интервал в секундах
        interval = self.keyframes_interval.value()

        # Формируем expression для FFmpeg
        # expr:gte(t,n_forced*interval)
        keyframe_expr = f"expr:gte(t,n_forced*{interval})"

        # Если также выбраны главы
        if self.keyframes_chapters.isChecked():
            # Добавляем главы: "chapters-0.1,expr:..."
            keyframe_expr = f"chapters-0.1,{keyframe_expr}"

        return keyframe_expr