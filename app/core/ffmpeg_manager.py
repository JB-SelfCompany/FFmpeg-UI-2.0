import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import Optional, List

from .gpu_detector import GPUDetector

logger = logging.getLogger(__name__)


class FFmpegManager:
    """Управление FFmpeg с GPU детектором"""
    
    def __init__(self):
        self.ffmpeg_path = self._find_ffmpeg()
        self.ffprobe_path = self._find_ffprobe()
        self.gpu_detector: Optional[GPUDetector] = None
        
        if self.is_available():
            try:
                self.gpu_detector = GPUDetector(self.ffmpeg_path)
                logger.info("GPU детектор инициализирован")
            except Exception as e:
                logger.error(f"Ошибка инициализации GPU детектора: {e}", exc_info=True)
    
    def _find_ffmpeg(self) -> str:
        """Поиск FFmpeg"""
        # Проверка в bundle (PyInstaller)
        if getattr(sys, 'frozen', False):
            base_path = Path(sys._MEIPASS)
            ffmpeg_name = 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg'
            ffmpeg_path = base_path / 'resources' / 'ffmpeg' / ffmpeg_name
            if ffmpeg_path.exists():
                logger.info(f"FFmpeg найден в bundle: {ffmpeg_path}")
                return str(ffmpeg_path)
        
        # Проверка в локальной директории
        local_path = Path(__file__).parent.parent / 'resources' / 'ffmpeg'
        ffmpeg_name = 'ffmpeg.exe' if os.name == 'nt' else 'ffmpeg'
        local_ffmpeg = local_path / ffmpeg_name
        if local_ffmpeg.exists():
            logger.info(f"FFmpeg найден локально: {local_ffmpeg}")
            return str(local_ffmpeg)
        
        # Проверка в системе
        try:
            cmd = 'where' if os.name == 'nt' else 'which'
            result = subprocess.run(
                [cmd, 'ffmpeg'],
                capture_output=True,
                text=True,
                timeout=3
            )
            if result.returncode == 0:
                system_path = result.stdout.strip().split('\n')[0]
                logger.info(f"FFmpeg найден в системе: {system_path}")
                return system_path
        except Exception as e:
            logger.warning(f"Ошибка поиска FFmpeg в системе: {e}")
        
        logger.warning("FFmpeg не найден")
        return ""
    
    def _find_ffprobe(self) -> str:
        """Поиск FFprobe"""
        if self.ffmpeg_path:
            ffprobe_name = 'ffprobe.exe' if os.name == 'nt' else 'ffprobe'
            ffprobe = Path(self.ffmpeg_path).parent / ffprobe_name
            if ffprobe.exists():
                return str(ffprobe)
        return ""
    
    def is_available(self) -> bool:
        """Проверка доступности FFmpeg"""
        available = bool(self.ffmpeg_path and Path(self.ffmpeg_path).exists())
        if available:
            logger.info("FFmpeg доступен")
        else:
            logger.error("FFmpeg недоступен")
        return available
    
    def get_version(self) -> str:
        """Получение версии FFmpeg"""
        if not self.is_available():
            return "Не найден"
        
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )
            first_line = result.stdout.split('\n')[0]
            version = first_line.split()[2]
            logger.info(f"FFmpeg версия: {version}")
            return version
        except Exception as e:
            logger.error(f"Ошибка получения версии FFmpeg: {e}")
            return "Неизвестна"
    
    def get_supported_formats(self) -> List[str]:
        """Получение поддерживаемых форматов"""
        if not self.is_available():
            return []
        
        try:
            result = subprocess.run(
                [self.ffmpeg_path, '-formats'],
                capture_output=True,
                text=True,
                timeout=5
            )
            lines = result.stdout.split('\n')
            formats = []
            for line in lines[4:]:
                if line.strip():
                    parts = line.split()
                    if len(parts) >= 2:
                        formats.append(parts[1])
            return formats
        except Exception as e:
            logger.error(f"Ошибка получения форматов: {e}")
            return []
    
    def get_gpu_detector(self) -> Optional[GPUDetector]:
        """Получить GPU детектор"""
        return self.gpu_detector