"""
Модуль для работы с главами (chapters) в видео файлах
Поддержка:
- Экспорт глав из видео
- Импорт/редактирование глав
- Добавление глав к видео через FFMETADATA
- Разделение видео по главам
"""

import logging
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional, Tuple
from dataclasses import dataclass
import re

logger = logging.getLogger(__name__)


@dataclass
class Chapter:
    """Представление главы"""
    start_time: float  # В секундах
    end_time: float  # В секундах
    title: str

    @property
    def start_time_ms(self) -> int:
        """Время начала в миллисекундах"""
        return int(self.start_time * 1000)

    @property
    def end_time_ms(self) -> int:
        """Время конца в миллисекундах"""
        return int(self.end_time * 1000)

    @property
    def duration(self) -> float:
        """Длительность главы в секундах"""
        return self.end_time - self.start_time

    def to_ffmetadata_format(self, timebase: str = "1/1000") -> str:
        """Конвертация в формат FFMETADATA"""
        return (
            f"[CHAPTER]\n"
            f"TIMEBASE={timebase}\n"
            f"START={self.start_time_ms}\n"
            f"END={self.end_time_ms}\n"
            f"title={self.title}\n"
        )

    @staticmethod
    def from_ffprobe_chapter(chapter_dict: dict) -> 'Chapter':
        """Создание Chapter из словаря FFProbe"""
        start_time = float(chapter_dict.get('start_time', 0))
        end_time = float(chapter_dict.get('end_time', 0))

        # Получаем title из tags
        tags = chapter_dict.get('tags', {})
        title = tags.get('title', f"Chapter {chapter_dict.get('id', 0)}")

        return Chapter(
            start_time=start_time,
            end_time=end_time,
            title=title
        )

    @staticmethod
    def from_ffmetadata_text(text: str) -> Optional['Chapter']:
        """Парсинг главы из текста FFMETADATA"""
        lines = text.strip().split('\n')
        if not lines or lines[0] != '[CHAPTER]':
            return None

        data = {}
        for line in lines[1:]:
            if '=' in line:
                key, value = line.split('=', 1)
                data[key] = value

        try:
            # TIMEBASE обычно 1/1000 (миллисекунды)
            timebase = data.get('TIMEBASE', '1/1000')
            if timebase == '1/1000':
                divisor = 1000.0
            elif timebase == '1/1':
                divisor = 1.0
            else:
                # Парсим timebase вида "1/X"
                match = re.match(r'1/(\d+)', timebase)
                divisor = float(match.group(1)) if match else 1000.0

            start_time = float(data['START']) / divisor
            end_time = float(data['END']) / divisor
            title = data.get('title', 'Untitled Chapter')

            return Chapter(
                start_time=start_time,
                end_time=end_time,
                title=title
            )
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing chapter from FFMETADATA: {e}")
            return None


class ChaptersManager:
    """Менеджер для работы с главами в видео"""

    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path

    def extract_chapters(self, video_file: str) -> List[Chapter]:
        """
        Извлечь главы из видео файла с помощью FFProbe

        Returns:
            Список глав
        """
        try:
            cmd = [
                self.ffprobe_path,
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_chapters',
                video_file
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                logger.error(f"FFProbe failed: {result.stderr}")
                return []

            import json
            data = json.loads(result.stdout)

            chapters = []
            for chapter_dict in data.get('chapters', []):
                chapter = Chapter.from_ffprobe_chapter(chapter_dict)
                chapters.append(chapter)

            logger.info(f"Extracted {len(chapters)} chapters from {video_file}")
            return chapters

        except Exception as e:
            logger.error(f"Error extracting chapters: {e}")
            return []

    def export_ffmetadata(self, video_file: str, output_file: str) -> bool:
        """
        Экспорт метаданных (включая главы) в файл FFMETADATA

        ffmpeg -i input.mp4 -f ffmetadata metadata.txt
        """
        try:
            cmd = [
                self.ffmpeg_path,
                '-i', video_file,
                '-f', 'ffmetadata',
                '-y',  # Перезаписать если существует
                output_file
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                logger.error(f"Failed to export metadata: {result.stderr}")
                return False

            logger.info(f"Exported metadata to {output_file}")
            return True

        except Exception as e:
            logger.error(f"Error exporting metadata: {e}")
            return False

    def parse_ffmetadata_file(self, metadata_file: str) -> Tuple[dict, List[Chapter]]:
        """
        Парсинг файла FFMETADATA

        Returns:
            (metadata_dict, chapters_list)
        """
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Парсим metadata
            metadata = {}
            chapters = []

            # Разделяем на секции
            sections = re.split(r'\[CHAPTER\]', content)

            # Первая секция - общие метаданные
            if sections:
                for line in sections[0].split('\n'):
                    line = line.strip()
                    if line and '=' in line and not line.startswith(';'):
                        key, value = line.split('=', 1)
                        metadata[key] = value

            # Остальные секции - главы
            for section in sections[1:]:
                chapter_text = '[CHAPTER]\n' + section
                chapter = Chapter.from_ffmetadata_text(chapter_text)
                if chapter:
                    chapters.append(chapter)

            logger.info(f"Parsed {len(chapters)} chapters from {metadata_file}")
            return metadata, chapters

        except Exception as e:
            logger.error(f"Error parsing FFMETADATA file: {e}")
            return {}, []

    def create_ffmetadata_file(
        self,
        chapters: List[Chapter],
        metadata: Optional[dict] = None,
        output_file: Optional[str] = None
    ) -> str:
        """
        Создать файл FFMETADATA из списка глав

        Returns:
            Путь к созданному файлу
        """
        if output_file is None:
            # Создаем временный файл
            fd, output_file = tempfile.mkstemp(suffix='.txt', prefix='ffmetadata_')
            import os
            os.close(fd)

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                # Заголовок
                f.write(";FFMETADATA1\n")

                # Общие метаданные
                if metadata:
                    for key, value in metadata.items():
                        f.write(f"{key}={value}\n")

                # Главы
                for chapter in chapters:
                    f.write("\n")
                    f.write(chapter.to_ffmetadata_format())

            logger.info(f"Created FFMETADATA file: {output_file}")
            return output_file

        except Exception as e:
            logger.error(f"Error creating FFMETADATA file: {e}")
            return ""

    def add_chapters_to_video(
        self,
        input_file: str,
        chapters: List[Chapter],
        output_file: str,
        metadata: Optional[dict] = None
    ) -> List[str]:
        """
        Добавить главы к видео файлу

        ffmpeg -i input.mp4 -i metadata.txt -map_metadata 1 -codec copy output.mp4

        Returns:
            FFmpeg команда
        """
        # Создаем временный файл метаданных
        metadata_file = self.create_ffmetadata_file(chapters, metadata)

        if not metadata_file:
            logger.error("Failed to create metadata file")
            return []

        cmd = [
            self.ffmpeg_path,
            '-i', input_file,
            '-i', metadata_file,
            '-map_metadata', '1',  # Использовать метаданные из второго входа
            '-map', '0',  # Копировать все потоки из первого входа
            '-codec', 'copy',  # Без перекодирования
            '-y',  # Перезаписать если существует
            output_file
        ]

        logger.info(f"Add chapters command: {' '.join(cmd)}")
        return cmd

    def split_video_by_chapters(
        self,
        input_file: str,
        chapters: List[Chapter],
        output_folder: str,
        output_pattern: str = "chapter_{index}_{title}.mp4"
    ) -> List[List[str]]:
        """
        Разделить видео на файлы по главам

        Returns:
            Список FFmpeg команд для каждой главы
        """
        commands = []
        output_path = Path(output_folder)
        output_path.mkdir(parents=True, exist_ok=True)

        for i, chapter in enumerate(chapters, 1):
            # Формируем имя файла
            safe_title = self._sanitize_filename(chapter.title)
            filename = output_pattern.format(
                index=i,
                title=safe_title
            )
            output_file = str(output_path / filename)

            # Команда FFmpeg для извлечения главы
            cmd = [
                self.ffmpeg_path,
                '-i', input_file,
                '-ss', str(chapter.start_time),
                '-t', str(chapter.duration),
                '-codec', 'copy',  # Без перекодирования
                '-avoid_negative_ts', '1',  # Избежать отрицательных timestamps
                '-y',
                output_file
            ]

            commands.append(cmd)
            logger.info(f"Split chapter {i}: {chapter.title} ({chapter.duration:.1f}s)")

        return commands

    def create_chapters_from_timestamps(
        self,
        timestamps: List[Tuple[float, str]],
        video_duration: float
    ) -> List[Chapter]:
        """
        Создать главы из списка временных меток

        Args:
            timestamps: Список (время_в_секундах, название_главы)
            video_duration: Общая длительность видео

        Returns:
            Список глав
        """
        if not timestamps:
            return []

        # Сортируем по времени
        timestamps = sorted(timestamps, key=lambda x: x[0])

        chapters = []
        for i, (start_time, title) in enumerate(timestamps):
            # Конец главы - это начало следующей или конец видео
            if i < len(timestamps) - 1:
                end_time = timestamps[i + 1][0]
            else:
                end_time = video_duration

            chapter = Chapter(
                start_time=start_time,
                end_time=end_time,
                title=title
            )
            chapters.append(chapter)

        logger.info(f"Created {len(chapters)} chapters from timestamps")
        return chapters

    def _sanitize_filename(self, filename: str) -> str:
        """Очистка имени файла от недопустимых символов"""
        # Заменяем недопустимые символы на подчеркивание
        invalid_chars = r'[<>:"/\\|?*]'
        safe_name = re.sub(invalid_chars, '_', filename)

        # Ограничиваем длину
        max_length = 50
        if len(safe_name) > max_length:
            safe_name = safe_name[:max_length]

        return safe_name.strip()

    def get_video_duration(self, video_file: str) -> float:
        """
        Получить длительность видео

        Returns:
            Длительность в секундах
        """
        try:
            cmd = [
                self.ffprobe_path,
                '-v', 'error',
                '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1',
                video_file
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                duration = float(result.stdout.strip())
                return duration
            else:
                logger.error(f"Failed to get video duration: {result.stderr}")
                return 0.0

        except Exception as e:
            logger.error(f"Error getting video duration: {e}")
            return 0.0
