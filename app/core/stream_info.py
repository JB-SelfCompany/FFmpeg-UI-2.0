"""
Модуль для работы с информацией о медиа-потоках
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class StreamType(Enum):
    """Типы потоков"""
    VIDEO = "video"
    AUDIO = "audio"
    SUBTITLE = "subtitle"
    DATA = "data"
    ATTACHMENT = "attachment"
    UNKNOWN = "unknown"


@dataclass
class StreamInfo:
    """Информация о медиа-потоке"""

    # Базовая информация
    index: int  # Индекс потока в файле
    stream_type: StreamType  # Тип потока
    codec_name: str  # Название кодека
    codec_long_name: str = ""  # Полное название кодека

    # Общие свойства
    duration: Optional[float] = None  # Длительность в секундах
    bitrate: Optional[int] = None  # Битрейт в бит/с
    language: Optional[str] = None  # Язык потока (eng, rus и т.д.)
    title: Optional[str] = None  # Название потока

    # Видео-специфичные свойства
    width: Optional[int] = None
    height: Optional[int] = None
    fps: Optional[float] = None  # Кадров в секунду
    pix_fmt: Optional[str] = None  # Pixel format
    aspect_ratio: Optional[str] = None  # Display aspect ratio

    # Аудио-специфичные свойства
    sample_rate: Optional[int] = None  # Частота дискретизации
    channels: Optional[int] = None  # Количество каналов
    channel_layout: Optional[str] = None  # Раскладка каналов (stereo, 5.1 и т.д.)

    # Субтитры-специфичные свойства
    subtitle_codec: Optional[str] = None

    # Disposition флаги
    is_default: bool = False
    is_forced: bool = False
    is_hearing_impaired: bool = False
    is_visual_impaired: bool = False

    # Дополнительные метаданные
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        """Инициализация после создания"""
        if self.metadata is None:
            self.metadata = {}

    def get_display_name(self) -> str:
        """
        Получить читаемое имя потока для UI

        Returns:
            Форматированная строка с описанием потока
        """
        parts = [f"Stream {self.index}"]

        # Добавляем тип
        parts.append(f"[{self.stream_type.value.upper()}]")

        # Добавляем кодек
        if self.codec_long_name:
            parts.append(self.codec_long_name)
        else:
            parts.append(self.codec_name)

        # Добавляем специфичную информацию
        if self.stream_type == StreamType.VIDEO:
            if self.width and self.height:
                parts.append(f"{self.width}x{self.height}")
            if self.fps:
                parts.append(f"{self.fps:.2f}fps")

        elif self.stream_type == StreamType.AUDIO:
            if self.channels:
                parts.append(f"{self.channels}ch")
            if self.sample_rate:
                parts.append(f"{self.sample_rate}Hz")

        # Добавляем язык
        if self.language:
            parts.append(f"({self.language})")

        # Добавляем название
        if self.title:
            parts.append(f'"{self.title}"')

        # Добавляем битрейт
        if self.bitrate:
            bitrate_kb = self.bitrate // 1000
            parts.append(f"{bitrate_kb}kb/s")

        return " ".join(parts)

    def get_short_name(self) -> str:
        """
        Получить короткое имя потока

        Returns:
            Краткая строка для компактного отображения
        """
        type_char = {
            StreamType.VIDEO: "V",
            StreamType.AUDIO: "A",
            StreamType.SUBTITLE: "S",
            StreamType.DATA: "D",
            StreamType.ATTACHMENT: "T"
        }.get(self.stream_type, "?")

        name = f"{type_char}:{self.index}"

        if self.stream_type == StreamType.VIDEO and self.width and self.height:
            name += f" {self.height}p"
        elif self.stream_type == StreamType.AUDIO and self.language:
            name += f" {self.language}"
        elif self.stream_type == StreamType.SUBTITLE and self.language:
            name += f" {self.language}"

        return name

    def to_map_string(self) -> str:
        """
        Получить строку для использования в -map параметре FFmpeg

        Returns:
            Строка вида "0:v:0" или "0:a:1" и т.д.
        """
        type_specifier = {
            StreamType.VIDEO: "v",
            StreamType.AUDIO: "a",
            StreamType.SUBTITLE: "s",
            StreamType.DATA: "d",
            StreamType.ATTACHMENT: "t"
        }.get(self.stream_type, "")

        if type_specifier:
            return f"0:{type_specifier}:{self.index}"
        else:
            return f"0:{self.index}"


@dataclass
class FileInfo:
    """Информация о медиа-файле"""

    filepath: str
    format_name: str  # Формат контейнера
    format_long_name: str = ""
    duration: Optional[float] = None  # Общая длительность
    size: Optional[int] = None  # Размер файла в байтах
    bitrate: Optional[int] = None  # Общий битрейт

    # Потоки
    streams: list[StreamInfo] = None

    # Метаданные файла
    metadata: Dict[str, Any] = None

    # Информация о главах
    chapters: list[Dict[str, Any]] = None

    def __post_init__(self):
        """Инициализация после создания"""
        if self.streams is None:
            self.streams = []
        if self.metadata is None:
            self.metadata = {}
        if self.chapters is None:
            self.chapters = []

    def get_streams_by_type(self, stream_type: StreamType) -> list[StreamInfo]:
        """
        Получить все потоки заданного типа

        Args:
            stream_type: Тип потока

        Returns:
            Список потоков указанного типа
        """
        return [s for s in self.streams if s.stream_type == stream_type]

    def get_video_streams(self) -> list[StreamInfo]:
        """Получить все видео-потоки"""
        return self.get_streams_by_type(StreamType.VIDEO)

    def get_audio_streams(self) -> list[StreamInfo]:
        """Получить все аудио-потоки"""
        return self.get_streams_by_type(StreamType.AUDIO)

    def get_subtitle_streams(self) -> list[StreamInfo]:
        """Получить все субтитры"""
        return self.get_streams_by_type(StreamType.SUBTITLE)

    def has_video(self) -> bool:
        """Проверить наличие видео-потоков"""
        return len(self.get_video_streams()) > 0

    def has_audio(self) -> bool:
        """Проверить наличие аудио-потоков"""
        return len(self.get_audio_streams()) > 0

    def has_subtitles(self) -> bool:
        """Проверить наличие субтитров"""
        return len(self.get_subtitle_streams()) > 0

    def get_summary(self) -> str:
        """
        Получить краткую сводку о файле

        Returns:
            Форматированная строка с информацией
        """
        parts = []

        video_count = len(self.get_video_streams())
        audio_count = len(self.get_audio_streams())
        subtitle_count = len(self.get_subtitle_streams())

        if video_count > 0:
            parts.append(f"{video_count} video")
        if audio_count > 0:
            parts.append(f"{audio_count} audio")
        if subtitle_count > 0:
            parts.append(f"{subtitle_count} subtitle")

        summary = f"{self.format_name}: {', '.join(parts)}"

        if self.duration:
            minutes = int(self.duration // 60)
            seconds = int(self.duration % 60)
            summary += f" | {minutes}:{seconds:02d}"

        if self.size:
            size_mb = self.size / (1024 * 1024)
            summary += f" | {size_mb:.1f} MB"

        return summary
