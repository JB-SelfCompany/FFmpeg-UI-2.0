from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QComboBox, QSlider, QSpinBox, QCheckBox,
    QGroupBox, QGridLayout, QSizePolicy
)
from PySide6.QtCore import Qt


class AudioOptions(QWidget):
    """Виджет настроек аудио"""
    
    def __init__(self):
        super().__init__()
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._init_ui()
        
    def _init_ui(self):
        """Инициализация UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(5)
        
        # Группа аудио настроек
        group = QGroupBox("🔊 Аудио")
        group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        group_layout = QGridLayout(group)
        group_layout.setSpacing(5)
        group_layout.setContentsMargins(8, 8, 8, 8)
        
        # Удалить звук
        row = 0
        self.remove_audio_checkbox = QCheckBox("Удалить звук")
        self.remove_audio_checkbox.setToolTip(
            "Удалить все аудио дорожки из выходного файла (ffmpeg -an)"
        )
        self.remove_audio_checkbox.stateChanged.connect(self._on_remove_audio_changed)
        group_layout.addWidget(self.remove_audio_checkbox, row, 0, 1, 2)
        
        # Кодек
        row += 1
        group_layout.addWidget(QLabel("Кодек:"), row, 0)
        self.codec_combo = QComboBox()
        self.codec_combo.addItems([
            "aac",
            "libmp3lame (MP3)",
            "libvorbis (Vorbis)",
            "libopus (Opus)",
            "flac",
            "ac3 (Dolby Digital)",
            "eac3 (Dolby Digital Plus)",
            "dts",
            "amr_nb (AMR Narrowband)",
            "amr_wb (AMR Wideband)",
            "libtwolame (MP2)",
            "liblc3 (LC3 - Bluetooth LE)",
            "alac (Apple Lossless)",
            "copy"
        ])
        self.codec_combo.setToolTip(
            "Аудио кодек:\n"
            "• aac - современный, отличная совместимость\n"
            "• mp3 - универсальный, работает везде\n"
            "• opus - лучшее качество при низком битрейте\n"
            "• flac - без потерь (lossless), большой размер\n"
            "• ac3 - Dolby Digital, домашний кинотеатр (5.1)\n"
            "• eac3 - Dolby Digital Plus, улучшенная версия\n"
            "• dts - конкурент Dolby, домашний кинотеатр\n"
            "• amr_nb/wb - мобильная телефония, низкий битрейт\n"
            "• mp2 - MPEG Audio Layer II, DVD/Broadcast\n"
            "• lc3 - Bluetooth LE Audio, современный\n"
            "• alac - Apple Lossless, без потерь для iTunes\n"
            "• copy - копирование без перекодирования"
        )
        group_layout.addWidget(self.codec_combo, row, 1)
        
        # Битрейт
        row += 1
        self.bitrate_label = QLabel("Битрейт:")
        group_layout.addWidget(self.bitrate_label, row, 0)
        self.bitrate_combo = QComboBox()
        self.bitrate_combo.setEditable(True)
        self.bitrate_combo.addItems([
            "64k",
            "96k",
            "128k",
            "192k",
            "256k",
            "320k"
        ])
        self.bitrate_combo.setCurrentText("128k")
        self.bitrate_combo.setToolTip(
            "Битрейт аудио:\n"
            "• 64k - низкое качество, речь\n"
            "• 128k - стандартное качество\n"
            "• 192k - хорошее качество\n"
            "• 256k+ - высокое качество"
        )
        group_layout.addWidget(self.bitrate_combo, row, 1)
        
        # Качество (для vorbis/opus)
        row += 1
        self.quality_label = QLabel("Качество:")
        group_layout.addWidget(self.quality_label, row, 0)
        quality_layout = QHBoxLayout()
        self.quality_slider = QSlider(Qt.Horizontal)
        self.quality_slider.setMinimum(0)
        self.quality_slider.setMaximum(10)
        self.quality_slider.setValue(4)
        self.quality_slider.setToolTip("0=низкое качество, 10=максимальное качество (для vorbis/opus)")
        self.quality_spinbox = QSpinBox()
        self.quality_spinbox.setMinimum(0)
        self.quality_spinbox.setMaximum(10)
        self.quality_spinbox.setValue(4)
        self.quality_slider.valueChanged.connect(self.quality_spinbox.setValue)
        self.quality_spinbox.valueChanged.connect(self.quality_slider.setValue)
        quality_layout.addWidget(self.quality_slider)
        quality_layout.addWidget(self.quality_spinbox)
        group_layout.addLayout(quality_layout, row, 1)
        
        # Частота дискретизации
        row += 1
        self.sample_rate_label = QLabel("Частота:")
        group_layout.addWidget(self.sample_rate_label, row, 0)
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems([
            "Авто",
            "8000 Hz",
            "16000 Hz",
            "22050 Hz",
            "44100 Hz",
            "48000 Hz",
            "96000 Hz"
        ])
        self.sample_rate_combo.setCurrentText("Авто")
        self.sample_rate_combo.setToolTip(
            "Частота дискретизации:\n"
            "• 44100 Hz - CD качество\n"
            "• 48000 Hz - профессиональное аудио\n"
            "• Авто - сохранить оригинальную"
        )
        group_layout.addWidget(self.sample_rate_combo, row, 1)
        
        # Каналы
        row += 1
        self.channels_label = QLabel("Каналы:")
        group_layout.addWidget(self.channels_label, row, 0)
        self.channels_combo = QComboBox()
        self.channels_combo.addItems([
            "Авто",
            "1 (Mono)",
            "2 (Stereo)",
            "6 (5.1)"
        ])
        self.channels_combo.setCurrentText("Авто")
        self.channels_combo.setToolTip(
            "Количество аудио каналов:\n"
            "• Mono - один канал\n"
            "• Stereo - два канала\n"
            "• 5.1 - объемный звук"
        )
        group_layout.addWidget(self.channels_combo, row, 1)
        
        group_layout.setRowStretch(row + 1, 1)
        main_layout.addWidget(group)
        
    def _on_remove_audio_changed(self, state):
        """Обработка изменения опции удаления звука"""
        enabled = state != Qt.Checked
        self.codec_combo.setEnabled(enabled)
        self.bitrate_combo.setEnabled(enabled)
        self.bitrate_label.setEnabled(enabled)
        self.quality_slider.setEnabled(enabled)
        self.quality_spinbox.setEnabled(enabled)
        self.quality_label.setEnabled(enabled)
        self.sample_rate_combo.setEnabled(enabled)
        self.sample_rate_label.setEnabled(enabled)
        self.channels_combo.setEnabled(enabled)
        self.channels_label.setEnabled(enabled)
        
    def is_audio_removal_enabled(self) -> bool:
        """Проверка включена ли опция удаления звука"""
        return self.remove_audio_checkbox.isChecked()
        
    def get_audio_codec(self):
        """Получить аудио кодек"""
        if self.is_audio_removal_enabled():
            return None

        codec_map = {
            "aac": "aac",
            "libmp3lame (MP3)": "libmp3lame",
            "libvorbis (Vorbis)": "libvorbis",
            "libopus (Opus)": "libopus",
            "flac": "flac",
            "ac3 (Dolby Digital)": "ac3",
            "eac3 (Dolby Digital Plus)": "eac3",
            "dts": "dca",
            "amr_nb (AMR Narrowband)": "libopencore_amrnb",
            "amr_wb (AMR Wideband)": "libvo_amrwbenc",
            "libtwolame (MP2)": "libtwolame",
            "liblc3 (LC3 - Bluetooth LE)": "liblc3",
            "alac (Apple Lossless)": "alac",
            "copy": "copy"
        }
        return codec_map.get(self.codec_combo.currentText(), "aac")
        
    def get_audio_bitrate(self):
        """Получить битрейт аудио"""
        if self.is_audio_removal_enabled():
            return None
        bitrate = self.bitrate_combo.currentText()
        return bitrate if bitrate else "128k"
        
    def get_audio_quality(self):
        """Получить качество для vorbis/opus"""
        if self.is_audio_removal_enabled():
            return None
        return self.quality_spinbox.value()
        
    def get_sample_rate(self):
        """Получить частоту дискретизации"""
        if self.is_audio_removal_enabled():
            return None
        rate = self.sample_rate_combo.currentText()
        if "Авто" in rate:
            return None
        return rate.split()[0]
        
    def get_channels(self):
        """Получить количество каналов"""
        if self.is_audio_removal_enabled():
            return None
        channels = self.channels_combo.currentText()
        if "Авто" in channels:
            return None
        return channels.split()[0]