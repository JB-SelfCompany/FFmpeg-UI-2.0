"""
Модуль для работы с изображениями и последовательностями
Поддержка:
- Создание видео из последовательности изображений
- Извлечение кадров из видео
- Слайдшоу с переходами
- Time-lapse
"""

import logging
import os
import re
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class TransitionType(Enum):
    """Типы переходов для слайдшоу"""
    NONE = "none"
    FADE = "fade"
    WIPELEFT = "wipeleft"
    WIPERIGHT = "wiperight"
    WIPEUP = "wipeup"
    WIPEDOWN = "wipedown"
    SLIDELEFT = "slideleft"
    SLIDERIGHT = "slideright"
    SLIDEUP = "slideup"
    SLIDEDOWN = "slidedown"
    CIRCLECROP = "circlecrop"
    RECTCROP = "rectcrop"
    DISSOLVE = "dissolve"


class ImageFormat(Enum):
    """Поддерживаемые форматы изображений"""
    PNG = "png"
    JPG = "jpg"
    JPEG = "jpeg"
    BMP = "bmp"
    TIFF = "tiff"
    WEBP = "webp"


@dataclass
class ImageSequenceConfig:
    """Конфигурация для создания видео из изображений"""
    input_pattern: str  # Паттерн файлов (например, "image-%03d.png" или список файлов)
    output_file: str
    fps: int = 25
    resolution: Optional[Tuple[int, int]] = None  # (width, height)
    codec: str = "libx264"
    crf: int = 23
    start_number: int = 0  # Начальный номер для паттернов
    duration_per_image: float = 3.0  # Длительность каждого изображения в секундах (для слайдшоу)
    transition: TransitionType = TransitionType.FADE
    transition_duration: float = 1.0  # Длительность перехода в секундах
    loop: int = 0  # Количество повторений (0 = без повтора, -1 = бесконечный)


@dataclass
class FrameExtractionConfig:
    """Конфигурация для извлечения кадров из видео"""
    input_file: str
    output_pattern: str  # Например, "frame-%04d.png"
    fps: Optional[float] = None  # Если None, извлекаются все кадры
    start_time: Optional[float] = None  # Начальное время в секундах
    end_time: Optional[float] = None  # Конечное время в секундах
    image_format: ImageFormat = ImageFormat.PNG
    quality: int = 2  # Качество JPEG (2-31, меньше = лучше)
    scale: Optional[Tuple[int, int]] = None  # Масштабирование (width, height)


class ImageSequenceManager:
    """Менеджер для работы с последовательностями изображений"""

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path

    def detect_image_sequence(self, folder: str) -> Optional[Tuple[str, int, int, str]]:
        """
        Автоматическое определение последовательности изображений в папке

        Returns:
            Tuple[pattern, start_number, end_number, extension] или None
        """
        folder_path = Path(folder)
        if not folder_path.exists() or not folder_path.is_dir():
            return None

        # Ищем паттерны вида image_001.png, frame_0001.jpg и т.д.
        sequences = {}

        for file in folder_path.iterdir():
            if not file.is_file():
                continue

            # Проверяем расширение
            ext = file.suffix.lower()
            if ext not in ['.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp']:
                continue

            # Ищем числа в имени файла
            match = re.match(r'(.+?)(\d+)(\.\w+)$', file.name)
            if match:
                prefix, number, extension = match.groups()
                number = int(number)

                key = (prefix, extension)
                if key not in sequences:
                    sequences[key] = []
                sequences[key].append(number)

        # Находим самую длинную последовательность
        best_sequence = None
        max_length = 0

        for (prefix, extension), numbers in sequences.items():
            numbers.sort()
            if len(numbers) > max_length:
                # Проверяем, что это действительно последовательность
                if self._is_valid_sequence(numbers):
                    max_length = len(numbers)
                    # Определяем количество цифр
                    digit_count = len(str(numbers[-1]))
                    pattern = f"{prefix}%0{digit_count}d{extension}"
                    best_sequence = (pattern, numbers[0], numbers[-1], extension)

        return best_sequence

    def _is_valid_sequence(self, numbers: List[int]) -> bool:
        """Проверка, что список чисел образует последовательность"""
        if len(numbers) < 2:
            return False

        # Проверяем, что разрыв между номерами не больше 10
        for i in range(len(numbers) - 1):
            if numbers[i + 1] - numbers[i] > 10:
                return False

        return True

    def build_image_to_video_command(self, config: ImageSequenceConfig) -> List[str]:
        """
        Построение команды FFmpeg для создания видео из изображений

        Для простой последовательности:
        ffmpeg -framerate 25 -start_number 0 -i image-%03d.png -c:v libx264 -crf 23 output.mp4

        Для слайдшоу с переходами - используем concat с xfade
        """
        cmd = [self.ffmpeg_path]

        # Если это слайдшоу с переходами и у нас список файлов
        if config.transition != TransitionType.NONE and isinstance(config.input_pattern, list):
            return self._build_slideshow_command(config)

        # Простая последовательность
        # Framerate для входных изображений
        if config.duration_per_image:
            # Для слайдшоу: fps = 1/duration
            input_fps = 1.0 / config.duration_per_image
            cmd.extend(['-framerate', str(input_fps)])
        else:
            cmd.extend(['-framerate', str(config.fps)])

        # Начальный номер
        if config.start_number > 0:
            cmd.extend(['-start_number', str(config.start_number)])

        # Входной паттерн
        cmd.extend(['-i', config.input_pattern])

        # Loop (для GIF/APNG)
        if config.loop != 0:
            cmd.extend(['-loop', str(config.loop)])

        # Видео кодек
        cmd.extend(['-c:v', config.codec])

        # CRF
        if config.codec not in ['copy', 'gif', 'apng']:
            cmd.extend(['-crf', str(config.crf)])

        # FPS на выходе
        cmd.extend(['-r', str(config.fps)])

        # Разрешение
        if config.resolution:
            width, height = config.resolution
            cmd.extend(['-s', f'{width}x{height}'])

        # Pixel format для совместимости
        if config.codec in ['libx264', 'libx265']:
            cmd.extend(['-pix_fmt', 'yuv420p'])

        # Выходной файл
        cmd.append(config.output_file)

        logger.info(f"Image to video command: {' '.join(cmd)}")
        return cmd

    def _build_slideshow_command(self, config: ImageSequenceConfig) -> List[str]:
        """
        Построение команды для слайдшоу с переходами
        Использует xfade filter для создания переходов между изображениями
        """
        cmd = [self.ffmpeg_path]

        if not isinstance(config.input_pattern, list):
            logger.error("Slideshow requires list of image files")
            return []

        images = config.input_pattern
        if len(images) < 2:
            logger.error("Slideshow requires at least 2 images")
            return []

        # Добавляем каждое изображение как input
        for img in images:
            # Каждое изображение показывается duration_per_image секунд
            cmd.extend([
                '-loop', '1',
                '-t', str(config.duration_per_image),
                '-i', img
            ])

        # Строим filter_complex для xfade переходов
        filter_parts = []

        # Масштабируем все входы до одного размера
        scale_filter = ""
        if config.resolution:
            width, height = config.resolution
            for i in range(len(images)):
                scale_filter += f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={config.fps},format=yuv420p[v{i}];"
        else:
            for i in range(len(images)):
                scale_filter += f"[{i}:v]fps={config.fps},format=yuv420p[v{i}];"

        filter_parts.append(scale_filter)

        # Создаем xfade переходы
        transition_offset = config.duration_per_image - config.transition_duration

        # Первое изображение
        current_label = "v0"

        for i in range(1, len(images)):
            next_label = f"v{i}"
            output_label = f"v{i}out" if i < len(images) - 1 else "out"

            # xfade переход
            offset_time = i * config.duration_per_image - (i * config.transition_duration)
            xfade_filter = (
                f"[{current_label}][{next_label}]xfade="
                f"transition={config.transition.value}:"
                f"duration={config.transition_duration}:"
                f"offset={offset_time}[{output_label}]"
            )
            filter_parts.append(xfade_filter)
            current_label = output_label

        filter_complex = ";".join(filter_parts)

        cmd.extend(['-filter_complex', filter_complex])
        cmd.extend(['-map', '[out]'])

        # Видео кодек
        cmd.extend(['-c:v', config.codec])
        if config.codec not in ['copy', 'gif', 'apng']:
            cmd.extend(['-crf', str(config.crf)])

        cmd.extend(['-movflags', '+faststart'])  # Для веб-оптимизации

        # Выходной файл
        cmd.append(config.output_file)

        logger.info(f"Slideshow command: {' '.join(cmd)}")
        return cmd

    def build_frame_extraction_command(self, config: FrameExtractionConfig) -> List[str]:
        """
        Построение команды для извлечения кадров из видео

        ffmpeg -i input.mp4 -vf fps=1 frame-%04d.png
        """
        cmd = [self.ffmpeg_path]

        # Входной файл
        cmd.extend(['-i', config.input_file])

        # Временные границы
        if config.start_time is not None:
            cmd.extend(['-ss', str(config.start_time)])
        if config.end_time is not None:
            cmd.extend(['-to', str(config.end_time)])

        # Фильтры
        filters = []

        # FPS для извлечения
        if config.fps:
            filters.append(f'fps={config.fps}')

        # Масштабирование
        if config.scale:
            width, height = config.scale
            filters.append(f'scale={width}:{height}')

        if filters:
            cmd.extend(['-vf', ','.join(filters)])

        # Качество для JPEG
        if config.image_format in [ImageFormat.JPG, ImageFormat.JPEG]:
            cmd.extend(['-q:v', str(config.quality)])

        # Выходной паттерн
        cmd.append(config.output_pattern)

        logger.info(f"Frame extraction command: {' '.join(cmd)}")
        return cmd

    def validate_image_sequence(self, pattern: str, folder: str) -> Tuple[bool, str, int]:
        """
        Валидация последовательности изображений

        Returns:
            (is_valid, message, image_count)
        """
        folder_path = Path(folder)
        if not folder_path.exists():
            return False, "Папка не существует", 0

        # Пытаемся найти файлы по паттерну
        if '%' in pattern:
            # Это printf-style паттерн
            base_name = re.sub(r'%\d*d', '*', pattern)
            files = list(folder_path.glob(base_name))
        else:
            # Это конкретный файл или список
            files = [folder_path / pattern] if (folder_path / pattern).exists() else []

        if not files:
            return False, "Не найдено изображений по указанному паттерну", 0

        return True, f"Найдено {len(files)} изображений", len(files)

    def estimate_video_duration(
        self,
        image_count: int,
        duration_per_image: float,
        transition_duration: float = 0.0
    ) -> float:
        """
        Оценка длительности видео из изображений
        """
        if image_count <= 1:
            return duration_per_image

        # Общая длительность = (кол-во изображений * длительность) - (кол-во переходов * длительность перехода)
        total_duration = (image_count * duration_per_image) - ((image_count - 1) * transition_duration)
        return max(total_duration, duration_per_image)
