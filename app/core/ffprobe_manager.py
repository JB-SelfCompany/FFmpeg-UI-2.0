"""
Модуль для работы с ffprobe и анализа медиа-файлов
"""
import json
import subprocess
import logging
from pathlib import Path
from typing import Optional

from .stream_info import StreamInfo, FileInfo, StreamType

logger = logging.getLogger(__name__)


class FFProbeManager:
    """Менеджер для работы с ffprobe"""

    def __init__(self, ffprobe_path: str = "ffprobe"):
        """
        Инициализация менеджера

        Args:
            ffprobe_path: Путь к исполняемому файлу ffprobe
        """
        self.ffprobe_path = ffprobe_path

    def probe_file(self, filepath: str) -> Optional[FileInfo]:
        """
        Анализировать медиа-файл и получить полную информацию

        Args:
            filepath: Путь к файлу

        Returns:
            FileInfo объект с информацией о файле или None при ошибке
        """
        try:
            # Строим команду ffprobe
            cmd = [
                self.ffprobe_path,
                "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                "-show_chapters",
                filepath
            ]

            logger.debug(f"Запуск ffprobe: {' '.join(cmd)}")

            # Выполняем команду
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )

            if result.returncode != 0:
                logger.error(f"ffprobe вернул ошибку: {result.stderr}")
                return None

            # Парсим JSON
            data = json.loads(result.stdout)

            # Создаем FileInfo объект
            file_info = self._parse_file_info(filepath, data)

            logger.info(f"Проанализирован файл: {file_info.get_summary()}")

            return file_info

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout при анализе файла: {filepath}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON от ffprobe: {e}")
            return None
        except Exception as e:
            logger.error(f"Ошибка при анализе файла {filepath}: {e}")
            return None

    def _parse_file_info(self, filepath: str, data: dict) -> FileInfo:
        """
        Парсинг JSON данных от ffprobe в FileInfo объект

        Args:
            filepath: Путь к файлу
            data: JSON данные от ffprobe

        Returns:
            FileInfo объект
        """
        format_data = data.get("format", {})
        streams_data = data.get("streams", [])
        chapters_data = data.get("chapters", [])

        # Парсим общую информацию о файле
        file_info = FileInfo(
            filepath=filepath,
            format_name=format_data.get("format_name", "unknown"),
            format_long_name=format_data.get("format_long_name", ""),
            duration=self._parse_float(format_data.get("duration")),
            size=self._parse_int(format_data.get("size")),
            bitrate=self._parse_int(format_data.get("bit_rate")),
            metadata=format_data.get("tags", {})
        )

        # Парсим потоки
        for idx, stream_data in enumerate(streams_data):
            stream = self._parse_stream_info(idx, stream_data)
            if stream:
                file_info.streams.append(stream)

        # Парсим главы
        file_info.chapters = chapters_data

        return file_info

    def _parse_stream_info(self, index: int, data: dict) -> Optional[StreamInfo]:
        """
        Парсинг данных одного потока

        Args:
            index: Индекс потока
            data: JSON данные потока

        Returns:
            StreamInfo объект или None
        """
        try:
            # Определяем тип потока
            codec_type = data.get("codec_type", "unknown")
            stream_type = self._map_stream_type(codec_type)

            # Базовая информация
            stream = StreamInfo(
                index=index,
                stream_type=stream_type,
                codec_name=data.get("codec_name", "unknown"),
                codec_long_name=data.get("codec_long_name", ""),
                duration=self._parse_float(data.get("duration")),
                bitrate=self._parse_int(data.get("bit_rate")),
                metadata=data.get("tags", {})
            )

            # Язык и название из метаданных
            stream.language = stream.metadata.get("language")
            stream.title = stream.metadata.get("title")

            # Видео-специфичные поля
            if stream_type == StreamType.VIDEO:
                stream.width = data.get("width")
                stream.height = data.get("height")
                stream.pix_fmt = data.get("pix_fmt")

                # Парсим FPS
                fps_str = data.get("r_frame_rate", "0/0")
                stream.fps = self._parse_frame_rate(fps_str)

                # Aspect ratio
                dar = data.get("display_aspect_ratio")
                if dar and dar != "0:1":
                    stream.aspect_ratio = dar

            # Аудио-специфичные поля
            elif stream_type == StreamType.AUDIO:
                stream.sample_rate = self._parse_int(data.get("sample_rate"))
                stream.channels = data.get("channels")
                stream.channel_layout = data.get("channel_layout")

            # Субтитры
            elif stream_type == StreamType.SUBTITLE:
                stream.subtitle_codec = stream.codec_name

            # Disposition флаги
            disposition = data.get("disposition", {})
            stream.is_default = disposition.get("default", 0) == 1
            stream.is_forced = disposition.get("forced", 0) == 1
            stream.is_hearing_impaired = disposition.get("hearing_impaired", 0) == 1
            stream.is_visual_impaired = disposition.get("visual_impaired", 0) == 1

            return stream

        except Exception as e:
            logger.error(f"Ошибка при парсинге потока {index}: {e}")
            return None

    @staticmethod
    def _map_stream_type(codec_type: str) -> StreamType:
        """
        Преобразование типа кодека в StreamType

        Args:
            codec_type: Тип кодека из ffprobe

        Returns:
            StreamType enum
        """
        type_map = {
            "video": StreamType.VIDEO,
            "audio": StreamType.AUDIO,
            "subtitle": StreamType.SUBTITLE,
            "data": StreamType.DATA,
            "attachment": StreamType.ATTACHMENT
        }
        return type_map.get(codec_type.lower(), StreamType.UNKNOWN)

    @staticmethod
    def _parse_float(value) -> Optional[float]:
        """Безопасное преобразование в float"""
        try:
            return float(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_int(value) -> Optional[int]:
        """Безопасное преобразование в int"""
        try:
            return int(value) if value is not None else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _parse_frame_rate(fps_str: str) -> Optional[float]:
        """
        Парсинг frame rate из строки вида "30000/1001"

        Args:
            fps_str: Строка с дробью

        Returns:
            FPS как float или None
        """
        try:
            if "/" in fps_str:
                num, den = fps_str.split("/")
                num, den = int(num), int(den)
                if den > 0:
                    return num / den
            else:
                return float(fps_str)
        except (ValueError, ZeroDivisionError):
            pass
        return None

    def get_stream_codec_info(self, filepath: str, stream_index: int) -> Optional[dict]:
        """
        Получить детальную информацию о кодеке конкретного потока

        Args:
            filepath: Путь к файлу
            stream_index: Индекс потока

        Returns:
            Словарь с информацией о кодеке или None
        """
        file_info = self.probe_file(filepath)
        if not file_info or stream_index >= len(file_info.streams):
            return None

        stream = file_info.streams[stream_index]
        return {
            "codec_name": stream.codec_name,
            "codec_long_name": stream.codec_long_name,
            "type": stream.stream_type.value
        }

    def check_ffprobe_available(self) -> bool:
        """
        Проверить доступность ffprobe

        Returns:
            True если ffprobe доступен
        """
        try:
            result = subprocess.run(
                [self.ffprobe_path, "-version"],
                capture_output=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            return result.returncode == 0
        except Exception:
            return False
