"""
Модуль для конкатенации (объединения) видео файлов
Поддержка:
- Простое объединение (concat demuxer)
- Объединение с переходами (xfade filter)
- Объединение файлов разных форматов/разрешений
- Автоматическое создание глав при объединении
"""

import logging
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ConcatMethod(Enum):
    """Методы конкатенации"""
    DEMUXER = "demuxer"  # Concat demuxer - быстро, без перекодирования, требует одинаковый формат
    PROTOCOL = "protocol"  # Concat protocol - для некоторых форматов (MPEG, TS)
    FILTER = "filter"  # Concat filter - с перекодированием, поддерживает разные форматы
    FILTER_WITH_TRANSITION = "filter_transition"  # С переходами между клипами


class TransitionEffect(Enum):
    """Эффекты переходов для xfade"""
    FADE = "fade"
    FADEBLACK = "fadeblack"
    FADEWHITE = "fadewhite"
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
    DISTANCE = "distance"
    FADEFAST = "fadefast"
    FADESLOW = "fadeslow"
    HLSLICE = "hlslice"
    HRSLICE = "hrslice"
    VUSLICE = "vuslice"
    VDSLICE = "vdslice"
    DISSOLVE = "dissolve"
    PIXELIZE = "pixelize"
    RADIAL = "radial"
    SMOOTHLEFT = "smoothleft"
    SMOOTHRIGHT = "smoothright"
    SMOOTHUP = "smoothup"
    SMOOTHDOWN = "smoothdown"


@dataclass
class VideoClip:
    """Представление видео клипа для конкатенации"""
    file_path: str
    title: Optional[str] = None  # Для названия главы
    start_time: Optional[float] = None  # Начало (для обрезки)
    end_time: Optional[float] = None  # Конец (для обрезки)
    duration: Optional[float] = None  # Длительность клипа

    def get_chapter_title(self, index: int) -> str:
        """Получить название главы"""
        if self.title:
            return self.title
        return f"Part {index + 1} - {Path(self.file_path).stem}"


@dataclass
class ConcatConfig:
    """Конфигурация конкатенации"""
    clips: List[VideoClip]
    output_file: str
    method: ConcatMethod = ConcatMethod.FILTER
    transition: Optional[TransitionEffect] = None
    transition_duration: float = 1.0  # Длительность перехода в секундах
    create_chapters: bool = True  # Создать главы для каждого клипа
    output_resolution: Optional[Tuple[int, int]] = None  # Выходное разрешение
    output_fps: Optional[int] = None  # Выходной FPS
    codec: str = "libx264"
    crf: int = 23
    audio_codec: str = "aac"
    audio_bitrate: str = "192k"


class ConcatenationManager:
    """Менеджер для объединения видео"""

    def __init__(self, ffmpeg_path: str = "ffmpeg"):
        self.ffmpeg_path = ffmpeg_path

    def build_concat_command(self, config: ConcatConfig) -> List[str]:
        """
        Построение команды FFmpeg для конкатенации

        Returns:
            FFmpeg команда
        """
        if config.method == ConcatMethod.DEMUXER:
            return self._build_demuxer_concat(config)
        elif config.method == ConcatMethod.PROTOCOL:
            return self._build_protocol_concat(config)
        elif config.method == ConcatMethod.FILTER:
            return self._build_filter_concat(config)
        elif config.method == ConcatMethod.FILTER_WITH_TRANSITION:
            return self._build_filter_concat_with_transition(config)
        else:
            logger.error(f"Unknown concat method: {config.method}")
            return []

    def _build_demuxer_concat(self, config: ConcatConfig) -> List[str]:
        """
        Конкатенация через concat demuxer (без перекодирования)

        Требует создание файла списка:
        file 'video1.mp4'
        file 'video2.mp4'

        ffmpeg -f concat -safe 0 -i filelist.txt -c copy output.mp4
        """
        # Создаем временный файл со списком
        concat_file = self._create_concat_file(config.clips)

        cmd = [
            self.ffmpeg_path,
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_file,
            '-c', 'copy',  # Без перекодирования
            '-y',
            config.output_file
        ]

        logger.info(f"Demuxer concat command: {' '.join(cmd)}")
        return cmd

    def _build_protocol_concat(self, config: ConcatConfig) -> List[str]:
        """
        Конкатенация через concat protocol

        ffmpeg -i "concat:video1.ts|video2.ts" -c copy output.ts
        """
        # Объединяем пути через |
        concat_input = "concat:" + "|".join([clip.file_path for clip in config.clips])

        cmd = [
            self.ffmpeg_path,
            '-i', concat_input,
            '-c', 'copy',
            '-bsf:a', 'aac_adtstoasc',  # Для MPEG-TS
            '-y',
            config.output_file
        ]

        logger.info(f"Protocol concat command: {' '.join(cmd)}")
        return cmd

    def _build_filter_concat(self, config: ConcatConfig) -> List[str]:
        """
        Конкатенация через concat filter (с перекодированием)

        Поддерживает разные форматы/разрешения
        """
        cmd = [self.ffmpeg_path]

        # Добавляем все входные файлы
        for clip in config.clips:
            cmd.extend(['-i', clip.file_path])

        # Строим filter_complex
        filter_parts = []
        n = len(config.clips)

        # Масштабируем все входы до одного размера (если указано)
        if config.output_resolution:
            width, height = config.output_resolution
            scale_filter = ""
            for i in range(n):
                scale_filter += f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
                scale_filter += f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1[v{i}];"
            filter_parts.append(scale_filter)

            # Concat
            video_inputs = "".join([f"[v{i}]" for i in range(n)])
            audio_inputs = "".join([f"[{i}:a]" for i in range(n)])
            filter_parts.append(f"{video_inputs}{audio_inputs}concat=n={n}:v=1:a=1[outv][outa]")
        else:
            # Concat без масштабирования
            video_inputs = "".join([f"[{i}:v]" for i in range(n)])
            audio_inputs = "".join([f"[{i}:a]" for i in range(n)])
            filter_parts.append(f"{video_inputs}{audio_inputs}concat=n={n}:v=1:a=1[outv][outa]")

        filter_complex = "".join(filter_parts)

        cmd.extend(['-filter_complex', filter_complex])
        cmd.extend(['-map', '[outv]', '-map', '[outa]'])

        # Кодеки и настройки
        cmd.extend(['-c:v', config.codec])
        if config.codec not in ['copy']:
            cmd.extend(['-crf', str(config.crf)])

        if config.output_fps:
            cmd.extend(['-r', str(config.output_fps)])

        cmd.extend(['-c:a', config.audio_codec])
        cmd.extend(['-b:a', config.audio_bitrate])

        cmd.extend(['-y', config.output_file])

        logger.info(f"Filter concat command: {' '.join(cmd)}")
        return cmd

    def _build_filter_concat_with_transition(self, config: ConcatConfig) -> List[str]:
        """
        Конкатенация с переходами через xfade filter

        Создает плавные переходы между клипами
        """
        if not config.transition:
            logger.warning("No transition specified, using fade")
            config.transition = TransitionEffect.FADE

        cmd = [self.ffmpeg_path]

        # Добавляем все входные файлы
        for clip in config.clips:
            cmd.extend(['-i', clip.file_path])

        # Строим сложный filter_complex с xfade
        n = len(config.clips)

        if n < 2:
            logger.error("Need at least 2 clips for transition")
            return []

        # Масштабируем все входы
        filter_parts = []
        if config.output_resolution:
            width, height = config.output_resolution
        else:
            # Используем разрешение первого клипа
            width, height = 1920, 1080

        for i in range(n):
            scale_filter = (
                f"[{i}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
                f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={config.output_fps or 30}[v{i}]"
            )
            filter_parts.append(scale_filter)

        # Создаем цепочку xfade переходов
        current_label = "v0"
        offset = 0.0

        # TODO: Нужно знать длительность каждого клипа для правильного offset
        # Для упрощения используем фиксированную длительность
        clip_duration = 5.0  # Предполагаемая длительность каждого клипа

        for i in range(1, n):
            next_label = f"v{i}"
            output_label = f"v{i}x" if i < n - 1 else "outv"

            # Вычисляем offset для перехода
            offset = (i * clip_duration) - (i * config.transition_duration)

            xfade_filter = (
                f"[{current_label}][{next_label}]xfade="
                f"transition={config.transition.value}:"
                f"duration={config.transition_duration}:"
                f"offset={offset}[{output_label}]"
            )
            filter_parts.append(xfade_filter)
            current_label = output_label

        # Аудио concat
        audio_inputs = "".join([f"[{i}:a]" for i in range(n)])
        filter_parts.append(f"{audio_inputs}concat=n={n}:v=0:a=1[outa]")

        filter_complex = ";".join(filter_parts)

        cmd.extend(['-filter_complex', filter_complex])
        cmd.extend(['-map', '[outv]', '-map', '[outa]'])

        # Кодеки
        cmd.extend(['-c:v', config.codec])
        cmd.extend(['-crf', str(config.crf)])
        cmd.extend(['-c:a', config.audio_codec])
        cmd.extend(['-b:a', config.audio_bitrate])

        cmd.extend(['-y', config.output_file])

        logger.info(f"Filter concat with transition command: {' '.join(cmd)}")
        return cmd

    def _create_concat_file(self, clips: List[VideoClip]) -> str:
        """
        Создать временный файл списка для concat demuxer

        Returns:
            Путь к файлу
        """
        fd, concat_file = tempfile.mkstemp(suffix='.txt', prefix='concat_')

        try:
            import os
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                for clip in clips:
                    # Экранируем путь для FFmpeg
                    escaped_path = clip.file_path.replace('\\', '/').replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")

            logger.info(f"Created concat file: {concat_file}")
            return concat_file

        except Exception as e:
            logger.error(f"Error creating concat file: {e}")
            return ""

    def detect_best_concat_method(self, clips: List[VideoClip]) -> ConcatMethod:
        """
        Автоматически определить лучший метод конкатенации

        Returns:
            Рекомендуемый метод
        """
        if len(clips) < 2:
            return ConcatMethod.DEMUXER

        # Проверяем, все ли файлы одного формата
        # Для упрощения всегда используем filter (универсальный метод)
        return ConcatMethod.FILTER

    def create_chapters_for_concat(
        self,
        clips: List[VideoClip],
        clip_durations: List[float]
    ) -> List[Tuple[float, str]]:
        """
        Создать главы для объединенного видео

        Args:
            clips: Список клипов
            clip_durations: Длительности каждого клипа

        Returns:
            Список (время_начала, название_главы)
        """
        chapters = []
        current_time = 0.0

        for i, (clip, duration) in enumerate(zip(clips, clip_durations)):
            title = clip.get_chapter_title(i)
            chapters.append((current_time, title))
            current_time += duration

        logger.info(f"Created {len(chapters)} chapters for concatenation")
        return chapters

    def validate_clips(self, clips: List[VideoClip]) -> Tuple[bool, str]:
        """
        Валидация списка клипов

        Returns:
            (is_valid, message)
        """
        if not clips:
            return False, "Список клипов пуст"

        if len(clips) < 2:
            return False, "Требуется минимум 2 клипа для объединения"

        # Проверяем существование файлов
        for i, clip in enumerate(clips):
            if not Path(clip.file_path).exists():
                return False, f"Файл {i + 1} не найден: {clip.file_path}"

        return True, f"Готово {len(clips)} клипов к объединению"
