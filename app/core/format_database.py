from typing import List, Dict
from enum import Enum


class FormatCategory(Enum):
    """Категории форматов"""
    VIDEO = "video"
    AUDIO = "audio"


class FormatDatabase:
    """База форматов"""

    def __init__(self):
        self.formats = self._load_formats()

    def _load_formats(self) -> List[Dict]:
        """Загрузка базы форматов"""
        return [
            {
                'extension': 'mp4',
                'name': 'MPEG-4 Part 14',
                'category': FormatCategory.VIDEO,
                'description': 'Универсальный контейнер для видео. Поддерживается всеми устройствами и платформами. Идеален для веб и мобильных устройств.',
                'video_codecs': ['libx264', 'libx265', 'mpeg4', 'copy'],
                'audio_codecs': ['aac', 'libmp3lame', 'copy']
            },
            {
                'extension': 'mkv',
                'name': 'Matroska Video',
                'category': FormatCategory.VIDEO,
                'description': 'Открытый контейнер с поддержкой множества кодеков, субтитров и аудиодорожек. Отлично подходит для архивирования.',
                'video_codecs': ['libx264', 'libx265', 'libvpx-vp9', 'copy'],
                'audio_codecs': ['aac', 'libopus', 'flac', 'copy']
            },
            {
                'extension': 'avi',
                'name': 'Audio Video Interleave',
                'category': FormatCategory.VIDEO,
                'description': 'Старый формат Microsoft. Хорошая совместимость со старыми устройствами.',
                'video_codecs': ['mpeg4', 'libx264', 'copy'],
                'audio_codecs': ['libmp3lame', 'aac', 'copy']
            },
            {
                'extension': 'webm',
                'name': 'WebM',
                'category': FormatCategory.VIDEO,
                'description': 'Открытый формат для веб. Оптимизирован для потокового вещания в браузерах.',
                'video_codecs': ['libvpx-vp9', 'libvpx'],
                'audio_codecs': ['libopus', 'libvorbis']
            },
            {
                'extension': 'mov',
                'name': 'QuickTime Movie',
                'category': FormatCategory.VIDEO,
                'description': 'Формат Apple QuickTime. Отлично подходит для работы в macOS и iOS экосистеме.',
                'video_codecs': ['libx264', 'libx265', 'copy'],
                'audio_codecs': ['aac', 'libmp3lame', 'copy']
            },
            {
                'extension': 'flv',
                'name': 'Flash Video',
                'category': FormatCategory.VIDEO,
                'description': 'Устаревший формат Adobe Flash. Использовался для веб-видео.',
                'video_codecs': ['libx264', 'flv', 'copy'],
                'audio_codecs': ['libmp3lame', 'aac']
            },
            {
                'extension': 'mp3',
                'name': 'MPEG Audio Layer 3',
                'category': FormatCategory.AUDIO,
                'description': 'Популярный аудио формат с хорошим сжатием и совместимостью.',
                'video_codecs': [],
                'audio_codecs': ['libmp3lame']
            },
            {
                'extension': 'aac',
                'name': 'Advanced Audio Coding',
                'category': FormatCategory.AUDIO,
                'description': 'Современный аудио кодек с лучшим качеством чем MP3 при том же битрейте.',
                'video_codecs': [],
                'audio_codecs': ['aac']
            },
            {
                'extension': 'flac',
                'name': 'Free Lossless Audio Codec',
                'category': FormatCategory.AUDIO,
                'description': 'Lossless аудио кодек. Без потери качества, но большой размер.',
                'video_codecs': [],
                'audio_codecs': ['flac']
            },
            {
                'extension': 'wav',
                'name': 'Waveform Audio',
                'category': FormatCategory.AUDIO,
                'description': 'Несжатый аудио формат. Максимальное качество, максимальный размер.',
                'video_codecs': [],
                'audio_codecs': ['pcm_s16le']
            },
            {
                'extension': 'ogg',
                'name': 'Ogg Container',
                'category': FormatCategory.VIDEO,
                'description': 'Открытый мультимедийный контейнер. Поддерживает Vorbis, Opus, Theora, VP8.',
                'video_codecs': ['libtheora', 'libvpx'],
                'audio_codecs': ['libvorbis', 'libopus', 'flac']
            },
            {
                'extension': 'ts',
                'name': 'MPEG Transport Stream',
                'category': FormatCategory.VIDEO,
                'description': 'Формат для цифрового вещания (DVB, IPTV). Поддерживает потоковую передачу.',
                'video_codecs': ['libx264', 'libx265', 'mpeg2video', 'copy'],
                'audio_codecs': ['aac', 'libmp3lame', 'ac3', 'copy']
            },
            {
                'extension': 'm2ts',
                'name': 'MPEG-2 Transport Stream (Blu-ray)',
                'category': FormatCategory.VIDEO,
                'description': 'Blu-ray disc формат. Высокое качество для домашнего видео.',
                'video_codecs': ['libx264', 'libx265', 'mpeg2video', 'copy'],
                'audio_codecs': ['ac3', 'dca', 'aac', 'copy']
            },
            {
                'extension': '3gp',
                'name': '3GPP Mobile',
                'category': FormatCategory.VIDEO,
                'description': 'Формат для мобильных устройств. Компактный размер.',
                'video_codecs': ['libx264', 'mpeg4', 'copy'],
                'audio_codecs': ['aac', 'libopencore_amrnb', 'libvo_amrwbenc']
            },
            {
                'extension': 'gif',
                'name': 'Graphics Interchange Format',
                'category': FormatCategory.VIDEO,
                'description': 'Анимированные GIF изображения. Для веб-анимаций и мемов.',
                'video_codecs': ['gif'],
                'audio_codecs': []
            },
            {
                'extension': 'apng',
                'name': 'Animated PNG',
                'category': FormatCategory.VIDEO,
                'description': 'Анимированный PNG. Лучшее качество чем GIF, прозрачность.',
                'video_codecs': ['apng'],
                'audio_codecs': []
            },
            {
                'extension': 'nut',
                'name': 'NUT Container',
                'category': FormatCategory.VIDEO,
                'description': 'Нативный FFmpeg контейнер. Универсальный, поддерживает все кодеки.',
                'video_codecs': ['libx264', 'libx265', 'libvpx-vp9', 'libaom-av1', 'copy'],
                'audio_codecs': ['aac', 'libmp3lame', 'libopus', 'flac', 'copy']
            },
            {
                'extension': 'mxf',
                'name': 'Material Exchange Format',
                'category': FormatCategory.VIDEO,
                'description': 'Профессиональный формат для видеопроизводства (broadcast, кино).',
                'video_codecs': ['mpeg2video', 'dnxhd', 'jpeg2000', 'copy'],
                'audio_codecs': ['pcm_s16le', 'pcm_s24le', 'aac', 'copy']
            },
            {
                'extension': 'mpg',
                'name': 'MPEG Program Stream',
                'category': FormatCategory.VIDEO,
                'description': 'Стандарт MPEG-1/MPEG-2. Для DVD и VCD дисков.',
                'video_codecs': ['mpeg1video', 'mpeg2video', 'copy'],
                'audio_codecs': ['libmp3lame', 'libtwolame', 'ac3', 'copy']
            },
            {
                'extension': 'vob',
                'name': 'DVD Video Object',
                'category': FormatCategory.VIDEO,
                'description': 'Формат DVD дисков. MPEG-2 видео с AC-3 аудио.',
                'video_codecs': ['mpeg2video', 'copy'],
                'audio_codecs': ['ac3', 'libtwolame', 'copy']
            },
        ]
    
    def get_all_formats(self) -> List[Dict]:
        """Получить все форматы"""
        return self.formats

    def get_video_formats(self) -> List[Dict]:
        """Получить только видео форматы"""
        return [fmt for fmt in self.formats if fmt['category'] == FormatCategory.VIDEO]

    def get_audio_formats(self) -> List[Dict]:
        """Получить только аудио форматы"""
        return [fmt for fmt in self.formats if fmt['category'] == FormatCategory.AUDIO]

    def get_format_by_extension(self, ext: str) -> Dict:
        """Получить формат по расширению"""
        for fmt in self.formats:
            if fmt['extension'] == ext.lower():
                return fmt
        return {}