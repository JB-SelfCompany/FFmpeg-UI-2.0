import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class CodecPurpose(Enum):
    """Цель использования кодека"""
    UNIVERSAL = "universal"  # Максимальная совместимость
    QUALITY = "quality"  # Максимальное качество
    SIZE = "size"  # Минимальный размер файла
    SPEED = "speed"  # Быстрое кодирование
    WEB = "web"  # Для веб-стриминга
    ARCHIVE = "archive"  # Для архивирования


@dataclass
class CodecProfile:
    """Профиль кодека с характеристиками"""
    name: str
    display_name: str
    ffmpeg_name: str
    
    # Характеристики (1-10 балльная система)
    compression_efficiency: int  # Эффективность сжатия
    encoding_speed: int  # Скорость кодирования
    quality_per_bitrate: int  # Качество на битрейт
    browser_support: int  # Поддержка браузерами
    hw_acceleration: int  # Доступность GPU ускорения
    
    # Совместимость
    compatible_containers: List[str]
    optimal_containers: List[str]
    
    # Рекомендации
    recommended_for: List[CodecPurpose]
    min_year: int  # Минимальный год для поддержки (устройства)
    
    # Ограничения
    max_resolution: str  # Например: "8K", "4K", "1080p"
    supports_hdr: bool
    supports_10bit: bool
    
    # Технические детали
    crf_range: Tuple[int, int]  # Рекомендуемый диапазон CRF
    optimal_crf: int  # Оптимальный CRF
    
    def __str__(self):
        return self.display_name


class CodecSelector:
    """Интеллектуальный селектор кодеков"""
    
    def __init__(self):
        self.codecs = self._initialize_codec_database()
        
    def _initialize_codec_database(self) -> Dict[str, CodecProfile]:
        """Инициализация базы данных кодеков"""
        return {
            'h264': CodecProfile(
                name='h264',
                display_name='H.264 / AVC',
                ffmpeg_name='libx264',
                compression_efficiency=6,
                encoding_speed=9,
                quality_per_bitrate=7,
                browser_support=10,
                hw_acceleration=10,
                compatible_containers=['mp4', 'mkv', 'mov', 'avi', 'flv', 'ts', 'm4v'],
                optimal_containers=['mp4', 'mkv'],
                recommended_for=[
                    CodecPurpose.UNIVERSAL,
                    CodecPurpose.SPEED,
                    CodecPurpose.WEB
                ],
                min_year=2004,
                max_resolution='4K',
                supports_hdr=False,
                supports_10bit=True,
                crf_range=(18, 28),
                optimal_crf=23
            ),
            
            'h265': CodecProfile(
                name='h265',
                display_name='H.265 / HEVC',
                ffmpeg_name='libx265',
                compression_efficiency=9,
                encoding_speed=5,
                quality_per_bitrate=9,
                browser_support=6,
                hw_acceleration=9,
                compatible_containers=['mp4', 'mkv', 'mov', 'ts', 'm4v'],
                optimal_containers=['mp4', 'mkv'],
                recommended_for=[
                    CodecPurpose.QUALITY,
                    CodecPurpose.SIZE,
                    CodecPurpose.ARCHIVE
                ],
                min_year=2013,
                max_resolution='8K',
                supports_hdr=True,
                supports_10bit=True,
                crf_range=(20, 32),
                optimal_crf=28
            ),
            
            'vp8': CodecProfile(
                name='vp8',
                display_name='VP8',
                ffmpeg_name='libvpx',
                compression_efficiency=5,
                encoding_speed=7,
                quality_per_bitrate=6,
                browser_support=9,
                hw_acceleration=4,
                compatible_containers=['webm', 'mkv'],
                optimal_containers=['webm'],
                recommended_for=[
                    CodecPurpose.WEB
                ],
                min_year=2010,
                max_resolution='1080p',
                supports_hdr=False,
                supports_10bit=False,
                crf_range=(4, 63),
                optimal_crf=10
            ),
            
            'vp9': CodecProfile(
                name='vp9',
                display_name='VP9',
                ffmpeg_name='libvpx-vp9',
                compression_efficiency=8,
                encoding_speed=4,
                quality_per_bitrate=8,
                browser_support=9,
                hw_acceleration=7,
                compatible_containers=['webm', 'mkv'],
                optimal_containers=['webm'],
                recommended_for=[
                    CodecPurpose.WEB,
                    CodecPurpose.QUALITY,
                    CodecPurpose.SIZE
                ],
                min_year=2013,
                max_resolution='8K',
                supports_hdr=True,
                supports_10bit=True,
                crf_range=(15, 35),
                optimal_crf=31
            ),
            
            'av1': CodecProfile(
                name='av1',
                display_name='AV1',
                ffmpeg_name='libaom-av1',
                compression_efficiency=10,
                encoding_speed=2,
                quality_per_bitrate=10,
                browser_support=8,
                hw_acceleration=6,
                compatible_containers=['mp4', 'webm', 'mkv'],
                optimal_containers=['mp4', 'webm', 'mkv'],
                recommended_for=[
                    CodecPurpose.QUALITY,
                    CodecPurpose.SIZE,
                    CodecPurpose.WEB,
                    CodecPurpose.ARCHIVE
                ],
                min_year=2018,
                max_resolution='8K',
                supports_hdr=True,
                supports_10bit=True,
                crf_range=(20, 40),
                optimal_crf=30
            )
        }
    
    def get_codec_by_name(self, name: str) -> Optional[CodecProfile]:
        """Получить профиль кодека по имени"""
        return self.codecs.get(name.lower())
    
    def get_all_codecs(self) -> List[CodecProfile]:
        """Получить все кодеки"""
        return list(self.codecs.values())
    
    def get_best_codec_for_container(
        self,
        container: str,
        purpose: CodecPurpose = CodecPurpose.UNIVERSAL,
        has_gpu: bool = False,
        gpu_supported_codecs: Optional[List[str]] = None
    ) -> Tuple[CodecProfile, str]:
        """
        Выбрать лучший кодек для контейнера
        Возвращает: (CodecProfile, reason)
        """
        container = container.lower()
        gpu_supported_codecs = gpu_supported_codecs or []
        
        # Фильтруем совместимые кодеки
        compatible = [
            codec for codec in self.codecs.values()
            if container in codec.compatible_containers
        ]
        
        if not compatible:
            # Fallback на H.264
            reason = f"Нет совместимых кодеков для {container.upper()}, используется H.264"
            logger.warning(reason)
            return self.codecs['h264'], reason
        
        # Применяем эвристики в зависимости от цели
        if purpose == CodecPurpose.UNIVERSAL:
            # Приоритет: поддержка браузерами и GPU
            scores = [
                (codec, codec.browser_support * 2 + codec.hw_acceleration)
                for codec in compatible
            ]
        elif purpose == CodecPurpose.SPEED:
            # Приоритет: скорость кодирования
            scores = [
                (codec, codec.encoding_speed * 2 + (3 if has_gpu and codec.name in gpu_supported_codecs else 0))
                for codec in compatible
            ]
        elif purpose == CodecPurpose.QUALITY:
            # Приоритет: качество на битрейт
            scores = [
                (codec, codec.quality_per_bitrate * 2 + codec.compression_efficiency)
                for codec in compatible
            ]
        elif purpose == CodecPurpose.SIZE:
            # Приоритет: эффективность сжатия
            scores = [
                (codec, codec.compression_efficiency * 3)
                for codec in compatible
            ]
        elif purpose == CodecPurpose.WEB:
            # Приоритет: поддержка браузерами
            scores = [
                (codec, codec.browser_support * 3 + codec.compression_efficiency)
                for codec in compatible
            ]
        elif purpose == CodecPurpose.ARCHIVE:
            # Приоритет: качество и сжатие
            scores = [
                (codec, codec.quality_per_bitrate + codec.compression_efficiency * 2)
                for codec in compatible
            ]
        else:
            # По умолчанию
            scores = [(codec, codec.browser_support) for codec in compatible]
        
        # Бонус для GPU поддерживаемых кодеков
        if has_gpu and gpu_supported_codecs:
            scores = [
                (codec, score + 5 if codec.name in gpu_supported_codecs else score)
                for codec, score in scores
            ]
        
        # Сортируем по оценке
        scores.sort(key=lambda x: x[1], reverse=True)
        best_codec = scores[0][0]
        
        # Формируем причину
        reasons = []
        if purpose == CodecPurpose.UNIVERSAL:
            reasons.append("максимальная совместимость")
        elif purpose == CodecPurpose.SPEED:
            reasons.append("быстрое кодирование")
        elif purpose == CodecPurpose.QUALITY:
            reasons.append("высокое качество")
        elif purpose == CodecPurpose.SIZE:
            reasons.append("минимальный размер")
        elif purpose == CodecPurpose.WEB:
            reasons.append("оптимизация для веб")
        elif purpose == CodecPurpose.ARCHIVE:
            reasons.append("архивирование")
        
        if has_gpu and best_codec.name in gpu_supported_codecs:
            reasons.append("GPU ускорение")
        
        if container in best_codec.optimal_containers:
            reasons.append(f"оптимален для {container.upper()}")
        
        reason = f"{best_codec.display_name}: {', '.join(reasons)}"
        
        logger.info(f"Выбран кодек: {reason}")
        return best_codec, reason
    
    def get_codec_recommendations(
        self,
        container: str,
        has_gpu: bool = False,
        gpu_supported_codecs: Optional[List[str]] = None
    ) -> List[Tuple[CodecProfile, str, CodecPurpose]]:
        """
        Получить рекомендации кодеков для контейнера
        Возвращает: [(CodecProfile, reason, purpose), ...]
        """
        recommendations = []
        gpu_supported_codecs = gpu_supported_codecs or []
        
        purposes = [
            CodecPurpose.UNIVERSAL,
            CodecPurpose.QUALITY,
            CodecPurpose.SIZE,
            CodecPurpose.SPEED,
            CodecPurpose.WEB
        ]
        
        for purpose in purposes:
            codec, reason = self.get_best_codec_for_container(
                container, purpose, has_gpu, gpu_supported_codecs
            )
            # Избегаем дубликатов
            if not any(c.name == codec.name for c, _, _ in recommendations):
                recommendations.append((codec, reason, purpose))
        
        return recommendations
    
    def get_optimal_settings(self, codec_name: str) -> Dict[str, any]:
        """Получить оптимальные настройки для кодека"""
        codec = self.get_codec_by_name(codec_name)
        if not codec:
            return {}
        
        return {
            'crf': codec.optimal_crf,
            'crf_min': codec.crf_range[0],
            'crf_max': codec.crf_range[1],
            'supports_hdr': codec.supports_hdr,
            'supports_10bit': codec.supports_10bit,
            'max_resolution': codec.max_resolution
        }
    
    def validate_codec_container(self, codec_name: str, container: str) -> Tuple[bool, str]:
        """
        Проверить совместимость кодека и контейнера
        Возвращает: (is_valid, message)
        """
        codec = self.get_codec_by_name(codec_name)
        container = container.lower()
        
        if not codec:
            return False, f"Кодек {codec_name} не найден"
        
        if container not in codec.compatible_containers:
            return False, f"{codec.display_name} несовместим с {container.upper()}"
        
        if container in codec.optimal_containers:
            return True, f"{codec.display_name} оптимален для {container.upper()}"
        
        return True, f"{codec.display_name} совместим с {container.upper()}"