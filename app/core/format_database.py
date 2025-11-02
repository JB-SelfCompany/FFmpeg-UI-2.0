from typing import List, Dict


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
                'description': 'Универсальный контейнер для видео. Поддерживается всеми устройствами и платформами. Идеален для веб и мобильных устройств.',
                'video_codecs': ['libx264', 'libx265', 'mpeg4', 'copy'],
                'audio_codecs': ['aac', 'libmp3lame', 'copy']
            },
            {
                'extension': 'mkv',
                'name': 'Matroska Video',
                'description': 'Открытый контейнер с поддержкой множества кодеков, субтитров и аудиодорожек. Отлично подходит для архивирования.',
                'video_codecs': ['libx264', 'libx265', 'libvpx-vp9', 'copy'],
                'audio_codecs': ['aac', 'libopus', 'flac', 'copy']
            },
            {
                'extension': 'avi',
                'name': 'Audio Video Interleave',
                'description': 'Старый формат Microsoft. Хорошая совместимость со старыми устройствами.',
                'video_codecs': ['mpeg4', 'libx264', 'copy'],
                'audio_codecs': ['libmp3lame', 'aac', 'copy']
            },
            {
                'extension': 'webm',
                'name': 'WebM',
                'description': 'Открытый формат для веб. Оптимизирован для потокового вещания в браузерах.',
                'video_codecs': ['libvpx-vp9', 'libvpx'],
                'audio_codecs': ['libopus', 'libvorbis']
            },
            {
                'extension': 'mov',
                'name': 'QuickTime Movie',
                'description': 'Формат Apple QuickTime. Отлично подходит для работы в macOS и iOS экосистеме.',
                'video_codecs': ['libx264', 'libx265', 'copy'],
                'audio_codecs': ['aac', 'libmp3lame', 'copy']
            },
            {
                'extension': 'flv',
                'name': 'Flash Video',
                'description': 'Устаревший формат Adobe Flash. Использовался для веб-видео.',
                'video_codecs': ['libx264', 'flv', 'copy'],
                'audio_codecs': ['libmp3lame', 'aac']
            },
            {
                'extension': 'mp3',
                'name': 'MPEG Audio Layer 3',
                'description': 'Популярный аудио формат с хорошим сжатием и совместимостью.',
                'video_codecs': [],
                'audio_codecs': ['libmp3lame']
            },
            {
                'extension': 'aac',
                'name': 'Advanced Audio Coding',
                'description': 'Современный аудио кодек с лучшим качеством чем MP3 при том же битрейте.',
                'video_codecs': [],
                'audio_codecs': ['aac']
            },
            {
                'extension': 'flac',
                'name': 'Free Lossless Audio Codec',
                'description': 'Lossless аудио кодек. Без потери качества, но большой размер.',
                'video_codecs': [],
                'audio_codecs': ['flac']
            },
            {
                'extension': 'wav',
                'name': 'Waveform Audio',
                'description': 'Несжатый аудио формат. Максимальное качество, максимальный размер.',
                'video_codecs': [],
                'audio_codecs': ['pcm_s16le']
            },
        ]
    
    def get_all_formats(self) -> List[Dict]:
        """Получить все форматы"""
        return self.formats
    
    def get_format_by_extension(self, ext: str) -> Dict:
        """Получить формат по расширению"""
        for fmt in self.formats:
            if fmt['extension'] == ext.lower():
                return fmt
        return {}