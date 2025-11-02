"""
Виджет видео-превью с поддержкой воспроизведения и live preview фильтров
"""
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Dict, List
import logging

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Signal, QThread, QObject
from PySide6.QtGui import QImage, QPixmap, QPainter, QPen
from PIL import Image

logger = logging.getLogger(__name__)


class VideoFrameLoader(QObject):
    """Загрузчик видео-фреймов в отдельном потоке"""

    frame_loaded = Signal(np.ndarray, dict)  # frame, metadata
    loading_finished = Signal()
    loading_error = Signal(str)

    def __init__(self):
        super().__init__()
        self.video_path = None
        self.frame_position = 0
        self._should_stop = False

    def load_frame(self, video_path: str, frame_position: int):
        """Загрузить конкретный фрейм"""
        self.video_path = video_path
        self.frame_position = frame_position
        self._load()

    def _load(self):
        """Загрузка фрейма из видео"""
        try:
            cap = cv2.VideoCapture(self.video_path)

            if not cap.isOpened():
                self.loading_error.emit(f"Не удалось открыть видео: {self.video_path}")
                return

            # Получаем метаданные
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = total_frames / fps if fps > 0 else 0

            metadata = {
                'fps': fps,
                'total_frames': total_frames,
                'width': width,
                'height': height,
                'duration': duration
            }

            # Переходим к нужному фрейму
            cap.set(cv2.CAP_PROP_POS_FRAMES, self.frame_position)

            ret, frame = cap.read()
            cap.release()

            if ret:
                # Конвертируем BGR в RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.frame_loaded.emit(frame_rgb, metadata)
            else:
                self.loading_error.emit(f"Не удалось прочитать фрейм {self.frame_position}")

            self.loading_finished.emit()

        except Exception as e:
            logger.error(f"Ошибка загрузки фрейма: {e}", exc_info=True)
            self.loading_error.emit(str(e))
            self.loading_finished.emit()


class VideoPreviewWidget(QWidget):
    """Виджет видео-превью с плеером и live preview фильтров"""

    # Сигналы
    frame_changed = Signal(int)  # current_frame

    def __init__(self, parent=None):
        super().__init__(parent)

        # Состояние
        self.video_path: Optional[str] = None
        self.video_capture: Optional[cv2.VideoCapture] = None
        self.current_frame: Optional[np.ndarray] = None
        self.original_frame: Optional[np.ndarray] = None  # Оригинальный фрейм без фильтров

        # Метаданные видео
        self.fps = 30.0
        self.total_frames = 0
        self.video_width = 0
        self.video_height = 0
        self.duration = 0.0
        self.current_frame_pos = 0

        # Воспроизведение
        self.is_playing = False
        self.playback_timer = QTimer()
        self.playback_timer.timeout.connect(self._next_frame)

        # Фильтры для live preview
        self.active_filters: List[Dict] = []

        # Загрузчик фреймов
        self.frame_loader = VideoFrameLoader()
        self.loader_thread = QThread()
        self.frame_loader.moveToThread(self.loader_thread)
        self.frame_loader.frame_loaded.connect(self._on_frame_loaded)
        self.frame_loader.loading_error.connect(self._on_loading_error)
        self.loader_thread.start()

        self._init_ui()

    def _init_ui(self):
        """Инициализация UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(5, 5, 5, 5)

        # === Область превью ===
        preview_container = QWidget()
        preview_container.setMinimumHeight(300)
        preview_container.setMaximumHeight(600)
        preview_container.setStyleSheet("""
            QWidget {
                background-color: #1a1a1a;
                border: 2px solid #333;
                border-radius: 8px;
            }
        """)
        preview_layout = QVBoxLayout(preview_container)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        # Label для отображения видео
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("background-color: #000; border: none; color: #888; font-size: 14px;")
        self.video_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.video_label.setScaledContents(False)
        self.video_label.setMinimumHeight(280)
        self.video_label.setText("Загрузите видео для превью")
        preview_layout.addWidget(self.video_label)

        layout.addWidget(preview_container, 1)

        # === Временная шкала (Seekbar) ===
        timeline_layout = QHBoxLayout()

        self.time_label_current = QLabel("00:00")
        self.time_label_current.setStyleSheet("color: #fff; font-size: 11px; min-width: 45px;")
        timeline_layout.addWidget(self.time_label_current)

        self.timeline_slider = QSlider(Qt.Orientation.Horizontal)
        self.timeline_slider.setMinimum(0)
        self.timeline_slider.setMaximum(100)
        self.timeline_slider.setValue(0)
        self.timeline_slider.setEnabled(False)
        self.timeline_slider.sliderPressed.connect(self._on_timeline_pressed)
        self.timeline_slider.sliderReleased.connect(self._on_timeline_released)
        self.timeline_slider.valueChanged.connect(self._on_timeline_changed)
        self.timeline_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #555;
                height: 8px;
                background: #333;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #2196F3;
                border: 2px solid #1976D2;
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QSlider::sub-page:horizontal {
                background: #2196F3;
                border-radius: 4px;
            }
        """)
        timeline_layout.addWidget(self.timeline_slider, 1)

        self.time_label_total = QLabel("00:00")
        self.time_label_total.setStyleSheet("color: #fff; font-size: 11px; min-width: 45px;")
        timeline_layout.addWidget(self.time_label_total)

        layout.addLayout(timeline_layout)

        # === Информация о файле (перед контролами) ===
        info_layout = QHBoxLayout()
        info_layout.setSpacing(5)

        self.info_label = QLabel("Нет видео")
        self.info_label.setStyleSheet("color: #ddd; font-size: 10px; background: transparent;")
        self.info_label.setWordWrap(True)
        info_layout.addWidget(self.info_label, 1)

        layout.addLayout(info_layout)

        # === Контролы воспроизведения ===
        # Первая строка: основные контролы
        controls_row1 = QHBoxLayout()
        controls_row1.setSpacing(8)

        # Prev Frame
        self.prev_button = QPushButton("⏮ Предыдущий")
        self.prev_button.setEnabled(False)
        self.prev_button.setMinimumHeight(50)
        self.prev_button.setToolTip("Предыдущий кадр")
        self.prev_button.clicked.connect(self._prev_frame)
        self.prev_button.setStyleSheet("""
            QPushButton {
                background-color: #455A64;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #37474F;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        controls_row1.addWidget(self.prev_button, stretch=1)

        # Play/Pause
        self.play_button = QPushButton("▶ Воспроизвести")
        self.play_button.setEnabled(False)
        self.play_button.setMinimumHeight(50)
        self.play_button.setToolTip("Play/Pause")
        self.play_button.clicked.connect(self._toggle_playback)
        self.play_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 8px;
                font-weight: bold;
                font-size: 14px;
                padding: 8px 20px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        controls_row1.addWidget(self.play_button, stretch=1)

        # Next Frame
        self.next_button = QPushButton("Следующий ⏭")
        self.next_button.setEnabled(False)
        self.next_button.setMinimumHeight(50)
        self.next_button.setToolTip("Следующий кадр")
        self.next_button.clicked.connect(self._next_frame)
        self.next_button.setStyleSheet(self.prev_button.styleSheet())
        controls_row1.addWidget(self.next_button, stretch=1)

        layout.addLayout(controls_row1)

        # Стиль виджета
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border-radius: 8px;
            }
        """)

    def load_video(self, video_path: str):
        """Загрузить видео для превью"""
        if not video_path or not Path(video_path).exists():
            logger.warning(f"Видео не найдено: {video_path}")
            return

        # Останавливаем воспроизведение если активно
        if self.is_playing:
            self._toggle_playback()

        # Закрываем предыдущее видео
        if self.video_capture:
            self.video_capture.release()

        self.video_path = video_path

        try:
            # Открываем видео
            self.video_capture = cv2.VideoCapture(video_path)

            if not self.video_capture.isOpened():
                logger.error(f"Не удалось открыть видео: {video_path}")
                self.info_label.setText("Ошибка загрузки видео")
                return

            # Получаем метаданные
            self.fps = self.video_capture.get(cv2.CAP_PROP_FPS)
            self.total_frames = int(self.video_capture.get(cv2.CAP_PROP_FRAME_COUNT))
            self.video_width = int(self.video_capture.get(cv2.CAP_PROP_FRAME_WIDTH))
            self.video_height = int(self.video_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
            self.duration = self.total_frames / self.fps if self.fps > 0 else 0

            # Обновляем UI
            self.timeline_slider.setMaximum(self.total_frames - 1)
            self.timeline_slider.setEnabled(True)
            self.play_button.setEnabled(True)
            self.prev_button.setEnabled(True)
            self.next_button.setEnabled(True)

            self.time_label_total.setText(self._format_time(self.duration))

            # Компактный вывод информации
            filename = Path(video_path).name
            # Сокращаем имя если слишком длинное
            if len(filename) > 30:
                filename = filename[:27] + "..."
            self.info_label.setText(f"{self.video_width}x{self.video_height} • {self.fps:.0f}fps • {filename}")

            # Загружаем первый фрейм
            self.current_frame_pos = 0
            self._load_current_frame()

            logger.info(f"Видео загружено: {video_path} ({self.video_width}x{self.video_height}, {self.fps} FPS, {self.total_frames} frames)")

        except Exception as e:
            logger.error(f"Ошибка загрузки видео: {e}", exc_info=True)
            self.info_label.setText("Ошибка загрузки")

    def _load_current_frame(self):
        """Загрузить текущий фрейм"""
        if not self.video_capture:
            return

        try:
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, self.current_frame_pos)
            ret, frame = self.video_capture.read()

            if ret:
                # Конвертируем BGR в RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                self.original_frame = frame_rgb.copy()
                self.current_frame = frame_rgb

                # Применяем фильтры если есть
                if self.active_filters:
                    self.current_frame = self._apply_filters(self.current_frame)

                # Отображаем фрейм
                self._display_frame(self.current_frame)

                # Обновляем время
                current_time = self.current_frame_pos / self.fps if self.fps > 0 else 0
                self.time_label_current.setText(self._format_time(current_time))

                # Обновляем seekbar без триггера события
                self.timeline_slider.blockSignals(True)
                self.timeline_slider.setValue(self.current_frame_pos)
                self.timeline_slider.blockSignals(False)

                self.frame_changed.emit(self.current_frame_pos)

        except Exception as e:
            logger.error(f"Ошибка загрузки фрейма: {e}", exc_info=True)

    def _display_frame(self, frame: np.ndarray):
        """Отобразить фрейм на label"""
        try:
            height, width, channel = frame.shape
            bytes_per_line = 3 * width

            q_image = QImage(frame.data, width, height, bytes_per_line, QImage.Format.Format_RGB888)
            pixmap = QPixmap.fromImage(q_image)

            # Масштабируем под размер label с сохранением пропорций
            scaled_pixmap = pixmap.scaled(
                self.video_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )

            self.video_label.setPixmap(scaled_pixmap)

        except Exception as e:
            logger.error(f"Ошибка отображения фрейма: {e}", exc_info=True)

    def _apply_filters(self, frame: np.ndarray) -> np.ndarray:
        """Применить активные фильтры к фрейму"""
        if not self.active_filters:
            return frame

        result = frame.copy()

        try:
            for filter_config in self.active_filters:
                if not filter_config.get('enabled', True):
                    continue

                filter_id = filter_config.get('id')
                params = filter_config.get('params', {})

                # Применяем фильтры OpenCV
                result = self._apply_single_filter(result, filter_id, params)

        except Exception as e:
            logger.error(f"Ошибка применения фильтров: {e}", exc_info=True)
            return frame

        return result

    def _apply_single_filter(self, frame: np.ndarray, filter_id: str, params: Dict) -> np.ndarray:
        """Применить один фильтр"""
        try:
            # === Видео фильтры ===

            # Яркость/Контраст/Насыщенность (eq)
            if filter_id == 'eq':
                brightness = params.get('brightness', 0) / 100.0
                contrast = params.get('contrast', 1.0)
                saturation = params.get('saturation', 1.0)

                # Яркость
                if brightness != 0:
                    frame = cv2.convertScaleAbs(frame, alpha=1, beta=brightness * 255)

                # Контраст
                if contrast != 1.0:
                    frame = cv2.convertScaleAbs(frame, alpha=contrast, beta=0)

                # Насыщенность
                if saturation != 1.0:
                    hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV).astype(np.float32)
                    hsv[:, :, 1] = np.clip(hsv[:, :, 1] * saturation, 0, 255)
                    frame = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)

            # Резкость (unsharp)
            elif filter_id == 'unsharp':
                amount = params.get('amount', 1.0)
                if amount > 0:
                    gaussian = cv2.GaussianBlur(frame, (0, 0), 2.0)
                    frame = cv2.addWeighted(frame, 1.0 + amount, gaussian, -amount, 0)

            # Шумоподавление (hqdn3d)
            elif filter_id == 'hqdn3d':
                luma_spatial = params.get('luma_spatial', 4.0)
                frame = cv2.fastNlMeansDenoisingColored(frame, None, luma_spatial, luma_spatial, 7, 21)

            # Отзеркаливание по горизонтали
            elif filter_id == 'hflip':
                frame = cv2.flip(frame, 1)

            # Отзеркаливание по вертикали
            elif filter_id == 'vflip':
                frame = cv2.flip(frame, 0)

            # Поворот
            elif filter_id == 'rotate':
                angle = params.get('angle', 0)
                if angle != 0:
                    height, width = frame.shape[:2]
                    center = (width // 2, height // 2)
                    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
                    frame = cv2.warpAffine(frame, matrix, (width, height))

            # Масштабирование
            elif filter_id == 'scale' or filter_id == 'scale_advanced':
                width = params.get('width', frame.shape[1])
                height = params.get('height', frame.shape[0])
                if width != frame.shape[1] or height != frame.shape[0]:
                    frame = cv2.resize(frame, (width, height), interpolation=cv2.INTER_LANCZOS4)

            # Обрезка
            elif filter_id == 'crop':
                w = params.get('w', frame.shape[1])
                h = params.get('h', frame.shape[0])
                x = params.get('x', 0)
                y = params.get('y', 0)
                frame = frame[y:y+h, x:x+w]

            # Текст/Watermark (drawtext)
            elif filter_id == 'drawtext':
                text = params.get('text', 'Sample Text')
                x = params.get('x', 10)
                y = params.get('y', 30)
                fontsize = params.get('fontsize', 24)
                fontcolor = params.get('fontcolor', 'white')

                # Конвертируем цвет
                color_map = {
                    'white': (255, 255, 255),
                    'black': (0, 0, 0),
                    'red': (255, 0, 0),
                    'green': (0, 255, 0),
                    'blue': (0, 0, 255),
                    'yellow': (255, 255, 0)
                }
                color = color_map.get(fontcolor, (255, 255, 255))

                cv2.putText(frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX,
                           fontsize / 24, color, 2, cv2.LINE_AA)

        except Exception as e:
            logger.error(f"Ошибка применения фильтра {filter_id}: {e}", exc_info=True)

        return frame

    def set_filters(self, filters: List[Dict]):
        """Установить список фильтров для preview и автоматически применить их"""
        self.active_filters = filters
        logger.info(f"Установлено {len(filters)} фильтров для preview")
        # Автоматически обновляем превью
        self.refresh_preview()

    def refresh_preview(self):
        """Обновить превью с текущими фильтрами"""
        if self.original_frame is not None:
            self.current_frame = self.original_frame.copy()

            if self.active_filters:
                self.current_frame = self._apply_filters(self.current_frame)

            self._display_frame(self.current_frame)
            logger.info("Preview обновлен")

    def _toggle_playback(self):
        """Переключить воспроизведение"""
        if not self.video_capture:
            return

        self.is_playing = not self.is_playing

        if self.is_playing:
            self.play_button.setText("⏸ Пауза")
            self.play_button.setToolTip("Pause")
            interval = int(1000 / self.fps) if self.fps > 0 else 33
            self.playback_timer.start(interval)
        else:
            self.play_button.setText("▶ Воспроизвести")
            self.play_button.setToolTip("Play")
            self.playback_timer.stop()

    def _next_frame(self):
        """Следующий фрейм"""
        if not self.video_capture:
            return

        self.current_frame_pos += 1

        if self.current_frame_pos >= self.total_frames:
            self.current_frame_pos = 0  # Зацикливаем

        self._load_current_frame()

    def _prev_frame(self):
        """Предыдущий фрейм"""
        if not self.video_capture:
            return

        self.current_frame_pos -= 1

        if self.current_frame_pos < 0:
            self.current_frame_pos = 0

        self._load_current_frame()

    def _on_timeline_pressed(self):
        """Обработка нажатия на seekbar"""
        if self.is_playing:
            self._toggle_playback()

    def _on_timeline_released(self):
        """Обработка отпускания seekbar"""
        pass

    def _on_timeline_changed(self, value: int):
        """Обработка изменения позиции на seekbar"""
        if not self.video_capture:
            return

        # Проверяем, было ли изменение от пользователя
        if self.timeline_slider.isSliderDown():
            self.current_frame_pos = value
            self._load_current_frame()

    def _on_frame_loaded(self, frame: np.ndarray, metadata: dict):
        """Обработка загруженного фрейма из потока"""
        self.current_frame = frame
        self._display_frame(frame)

    def _on_loading_error(self, error: str):
        """Обработка ошибки загрузки"""
        logger.error(f"Ошибка загрузки: {error}")
        self.info_label.setText(f"Ошибка: {error}")

    def _format_time(self, seconds: float) -> str:
        """Форматировать время в MM:SS"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def clear(self):
        """Очистить превью"""
        if self.is_playing:
            self._toggle_playback()

        if self.video_capture:
            self.video_capture.release()
            self.video_capture = None

        self.video_path = None
        self.current_frame = None
        self.original_frame = None
        self.current_frame_pos = 0

        self.video_label.clear()
        self.video_label.setText("Загрузите видео для превью")

        self.timeline_slider.setValue(0)
        self.timeline_slider.setEnabled(False)
        self.play_button.setEnabled(False)
        self.prev_button.setEnabled(False)
        self.next_button.setEnabled(False)

        self.time_label_current.setText("00:00")
        self.time_label_total.setText("00:00")
        self.info_label.setText("Нет видео")

        logger.info("Preview очищен")

    def resizeEvent(self, event):
        """Обработка изменения размера виджета"""
        super().resizeEvent(event)
        # Перерисовываем текущий фрейм с новыми размерами для сохранения aspect ratio
        if self.current_frame is not None:
            self._display_frame(self.current_frame)

    def closeEvent(self, event):
        """Обработка закрытия виджета"""
        if self.video_capture:
            self.video_capture.release()

        self.loader_thread.quit()
        self.loader_thread.wait()

        event.accept()
