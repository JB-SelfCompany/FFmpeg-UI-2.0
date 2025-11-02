import subprocess
import platform
import logging
from typing import Dict, List, Optional, Tuple, Set
from pathlib import Path

logger = logging.getLogger(__name__)


class GPUInfo:
    """Информация о GPU с возможностями"""
    
    def __init__(self, vendor: str, name: str, index: int = 0):
        self.vendor = vendor  # 'nvidia', 'amd', 'intel', 'none'
        self.name = name
        self.index = index
        self.supported_codecs: Set[str] = set()
        
    def __str__(self):
        return f"{self.vendor.upper()}: {self.name}"


class GPUDetector:
    """Детектор GPU с валидацией возможностей"""
    
    def __init__(self, ffmpeg_path: str):
        self.ffmpeg_path = ffmpeg_path
        self.detected_gpus: List[GPUInfo] = []
        self.supported_encoders: List[str] = []
        self.supported_decoders: List[str] = []
        self.supported_hwaccels: List[str] = []
        
        self._detect_hardware()
        self._detect_gpu_capabilities()
        
    def _run_command(self, cmd: List[str]) -> str:
        """Безопасное выполнение команды"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0
            )
            return result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            logger.warning(f"Команда превысила тайм-аут: {' '.join(cmd)}")
            return ""
        except Exception as e:
            logger.error(f"Ошибка выполнения команды: {e}")
            return ""
    
    def _detect_hardware(self):
        """Обнаружение доступных GPU"""
        if not self.ffmpeg_path or not Path(self.ffmpeg_path).exists():
            logger.warning("FFmpeg не найден, GPU ускорение недоступно")
            return
            
        try:
            # Hwaccels
            hwaccels_output = self._run_command([self.ffmpeg_path, '-hwaccels'])
            self.supported_hwaccels = self._parse_hwaccels(hwaccels_output)
            logger.info(f"Доступные hwaccels: {self.supported_hwaccels}")
            
            # Энкодеры
            encoders_output = self._run_command([self.ffmpeg_path, '-encoders'])
            self.supported_encoders = self._parse_encoders(encoders_output)
            gpu_encoders = [e for e in self.supported_encoders if any(x in e for x in ['nvenc', 'qsv', 'amf', 'vaapi'])]
            logger.info(f"GPU энкодеры: {gpu_encoders}")
            
            # Декодеры
            decoders_output = self._run_command([self.ffmpeg_path, '-decoders'])
            self.supported_decoders = self._parse_decoders(decoders_output)
            
            # Идентификация GPU
            self._identify_gpus()
            
        except Exception as e:
            logger.error(f"Ошибка обнаружения GPU: {e}", exc_info=True)
    
    def _parse_hwaccels(self, output: str) -> List[str]:
        """Парсинг hwaccels"""
        hwaccels = []
        lines = output.split('\n')
        parsing = False
        
        for line in lines:
            line = line.strip()
            if 'Hardware acceleration methods:' in line:
                parsing = True
                continue
            if parsing and line and not line.startswith('-') and not line.startswith('libav'):
                hwaccels.append(line)
                
        return hwaccels
    
    def _parse_encoders(self, output: str) -> List[str]:
        """Парсинг энкодеров"""
        encoders = []
        for line in output.split('\n'):
            line = line.strip()
            if line and line.startswith('V'):
                parts = line.split()
                if len(parts) >= 2:
                    encoders.append(parts[1])
        return encoders
    
    def _parse_decoders(self, output: str) -> List[str]:
        """Парсинг декодеров"""
        decoders = []
        for line in output.split('\n'):
            line = line.strip()
            if line and line.startswith('V'):
                parts = line.split()
                if len(parts) >= 2:
                    decoders.append(parts[1])
        return decoders
    
    def _identify_gpus(self):
        """Идентификация GPU"""
        # NVIDIA
        if 'cuda' in self.supported_hwaccels or any('nvenc' in e for e in self.supported_encoders):
            gpu_name = self._get_nvidia_gpu_name()
            self.detected_gpus.append(GPUInfo('nvidia', gpu_name, 0))
            logger.info(f"Обнаружен NVIDIA GPU: {gpu_name}")
        
        # Intel
        if 'qsv' in self.supported_hwaccels or any('qsv' in e for e in self.supported_encoders):
            gpu_name = self._get_intel_gpu_name()
            self.detected_gpus.append(GPUInfo('intel', gpu_name, 0))
            logger.info(f"Обнаружен Intel GPU: {gpu_name}")
        
        # AMD
        if 'vaapi' in self.supported_hwaccels or any('amf' in e for e in self.supported_encoders):
            gpu_name = self._get_amd_gpu_name()
            self.detected_gpus.append(GPUInfo('amd', gpu_name, 0))
            logger.info(f"Обнаружен AMD GPU: {gpu_name}")
        
        if not self.detected_gpus:
            self.detected_gpus.append(GPUInfo('none', 'CPU (программное кодирование)', 0))
            logger.info("GPU не обнаружен")
    
    def _detect_gpu_capabilities(self):
        """Проверка реальных возможностей GPU тестовым кодированием"""
        for gpu in self.detected_gpus:
            if gpu.vendor == 'none':
                continue
            
            codecs_to_test = {
                'nvidia': ['h264_nvenc', 'hevc_nvenc', 'av1_nvenc'],
                'intel': ['h264_qsv', 'hevc_qsv', 'vp9_qsv', 'av1_qsv'],
                'amd': ['h264_amf', 'hevc_amf', 'av1_amf'] if platform.system() == 'Windows' else 
                       ['h264_vaapi', 'hevc_vaapi', 'vp9_vaapi', 'av1_vaapi']
            }
            
            encoders_to_test = codecs_to_test.get(gpu.vendor, [])
            
            for encoder in encoders_to_test:
                if encoder in self.supported_encoders:
                    if self._test_encoder(encoder):
                        # Извлекаем имя кодека (h264, hevc, av1)
                        codec_name = encoder.split('_')[0]
                        gpu.supported_codecs.add(codec_name)
                        logger.info(f"{gpu.vendor.upper()} GPU поддерживает {codec_name.upper()}")
                    else:
                        codec_name = encoder.split('_')[0]
                        logger.warning(f"{gpu.vendor.upper()} GPU НЕ поддерживает {codec_name.upper()}")
    
    def _test_encoder(self, encoder: str) -> bool:
        """Тестирование энкодера быстрым кодированием"""
        try:
            # Создаем тестовое видео 1 кадр
            test_cmd = [
                self.ffmpeg_path,
                '-f', 'lavfi',
                '-i', 'nullsrc=s=256x256:d=0.04',
                '-c:v', encoder,
                '-f', 'null',
                '-'
            ]
            
            result = subprocess.run(
                test_cmd,
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == 'Windows' else 0
            )
            
            # Проверяем на ошибки
            error_keywords = [
                'Codec not supported',
                'No capable devices',
                'does not support',
                'not supported',
                'Provided device doesn\'t support'
            ]
            
            stderr_lower = result.stderr.lower()
            for keyword in error_keywords:
                if keyword.lower() in stderr_lower:
                    logger.debug(f"Энкодер {encoder} не поддерживается: {keyword}")
                    return False
            
            return result.returncode == 0
            
        except Exception as e:
            logger.debug(f"Ошибка тестирования {encoder}: {e}")
            return False
    
    def _get_nvidia_gpu_name(self) -> str:
        """Получение имени NVIDIA GPU"""
        try:
            cmd = ['nvidia-smi', '--query-gpu=name', '--format=csv,noheader']
            if platform.system() == 'Windows':
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=3,
                                       creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
            
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip().split('\n')[0]
        except Exception as e:
            logger.debug(f"Не удалось получить имя NVIDIA GPU: {e}")
        return "NVIDIA GPU"
    
    def _get_intel_gpu_name(self) -> str:
        """Получение имени Intel GPU"""
        try:
            if platform.system() == 'Windows':
                result = subprocess.run(
                    ['wmic', 'path', 'win32_VideoController', 'get', 'name'],
                    capture_output=True, text=True, timeout=3,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                for line in result.stdout.split('\n'):
                    if 'Intel' in line:
                        return line.strip()
            else:
                result = subprocess.run(['lspci'], capture_output=True, text=True, timeout=3)
                for line in result.stdout.split('\n'):
                    if 'VGA' in line and 'Intel' in line:
                        return line.split(':')[-1].strip()
        except Exception as e:
            logger.debug(f"Не удалось получить имя Intel GPU: {e}")
        return "Intel GPU (Quick Sync)"
    
    def _get_amd_gpu_name(self) -> str:
        """Получение имени AMD GPU"""
        try:
            if platform.system() == 'Windows':
                result = subprocess.run(
                    ['wmic', 'path', 'win32_VideoController', 'get', 'name'],
                    capture_output=True, text=True, timeout=3,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                for line in result.stdout.split('\n'):
                    if 'AMD' in line or 'Radeon' in line:
                        return line.strip()
            else:
                result = subprocess.run(['lspci'], capture_output=True, text=True, timeout=3)
                for line in result.stdout.split('\n'):
                    if 'VGA' in line and ('AMD' in line or 'Radeon' in line):
                        return line.split(':')[-1].strip()
        except Exception as e:
            logger.debug(f"Не удалось получить имя AMD GPU: {e}")
        return "AMD GPU"
    
    def get_primary_gpu(self) -> Optional[GPUInfo]:
        """Получить основной GPU"""
        return self.detected_gpus[0] if self.detected_gpus else None
    
    def has_gpu_support(self) -> bool:
        """Проверка наличия GPU поддержки"""
        return len(self.detected_gpus) > 0 and self.detected_gpus[0].vendor != 'none'
    
    def is_codec_supported_by_gpu(self, codec: str, gpu_vendor: str) -> bool:
        """Проверка поддержки кодека конкретным GPU"""
        for gpu in self.detected_gpus:
            if gpu.vendor == gpu_vendor:
                return codec.lower() in gpu.supported_codecs
        return False
    
    def is_codec_container_compatible(self, codec: str, container: str) -> bool:
        """Проверка совместимости кодека и контейнера"""
        codec = codec.lower()
        container = container.lower()
        
        # WebM поддерживает только VP8, VP9, AV1
        if container in ['webm']:
            is_compatible = any(c in codec for c in ['vp8', 'vp9', 'av1'])
            if not is_compatible:
                logger.warning(f"Кодек {codec} несовместим с {container}")
            return is_compatible
        
        # MP4 не поддерживает VP8/VP9
        if container in ['mp4', 'mov', 'm4v']:
            is_compatible = not any(c in codec for c in ['vp8', 'vp9', 'theora'])
            if not is_compatible:
                logger.warning(f"Кодек {codec} несовместим с {container}")
            return is_compatible
        
        # MKV поддерживает всё
        return True
    
    def get_best_encoder(self, codec: str, preferred_gpu: str, container: str = 'mp4') -> Tuple[str, str]:
        """
        Получить лучший энкодер с валидацией
        Возвращает: (encoder_name, warning_message)
        """
        codec = codec.lower()
        container = container.lower()
        warning = ""
        
        # CPU режим
        if preferred_gpu == 'none' or not self.has_gpu_support():
            encoder = self._get_software_encoder(codec, container)
            logger.info(f"Используется CPU кодек: {encoder}")
            return encoder, ""
        
        # Автовыбор GPU
        if preferred_gpu == 'auto' and self.detected_gpus:
            preferred_gpu = self.detected_gpus[0].vendor
        
        # Проверка поддержки кодека GPU
        if not self.is_codec_supported_by_gpu(codec, preferred_gpu):
            logger.warning(f"GPU {preferred_gpu} не поддерживает {codec}")
            fallback = self._get_software_encoder(codec, container)
            gpu_name = self._get_gpu_name_by_vendor(preferred_gpu)
            warning = f"⚠ {gpu_name} не поддерживает {codec.upper()} кодирование. Используется CPU: {fallback}"
            return fallback, warning
        
        # NVIDIA
        if preferred_gpu == 'nvidia':
            encoder_map = {
                'h264': 'h264_nvenc',
                'hevc': 'hevc_nvenc',
                'h265': 'hevc_nvenc',
                'av1': 'av1_nvenc'
            }
            encoder = encoder_map.get(codec, '')
            
            if encoder and not self.is_codec_container_compatible(encoder, container):
                fallback = self._get_software_encoder(codec, container)
                warning = f"⚠ NVENC {codec.upper()} несовместим с {container.upper()}. Используется CPU: {fallback}"
                return fallback, warning
            
            if encoder in self.supported_encoders:
                logger.info(f"Используется NVIDIA энкодер: {encoder}")
                return encoder, ""
        
        # Intel QSV
        if preferred_gpu == 'intel':
            encoder_map = {
                'h264': 'h264_qsv',
                'hevc': 'hevc_qsv',
                'h265': 'hevc_qsv',
                'av1': 'av1_qsv',
                'mpeg2': 'mpeg2_qsv',
                'vp9': 'vp9_qsv'
            }
            encoder = encoder_map.get(codec, '')
            
            if encoder and not self.is_codec_container_compatible(encoder, container):
                fallback = self._get_software_encoder(codec, container)
                warning = f"⚠ QSV {codec.upper()} несовместим с {container.upper()}. Используется CPU: {fallback}"
                return fallback, warning
            
            if encoder in self.supported_encoders:
                logger.info(f"Используется Intel QSV энкодер: {encoder}")
                return encoder, ""
        
        # AMD
        if preferred_gpu == 'amd':
            if platform.system() == 'Windows':
                encoder_map = {
                    'h264': 'h264_amf',
                    'hevc': 'hevc_amf',
                    'h265': 'hevc_amf',
                    'av1': 'av1_amf'
                }
            else:
                encoder_map = {
                    'h264': 'h264_vaapi',
                    'hevc': 'hevc_vaapi',
                    'h265': 'hevc_vaapi',
                    'vp8': 'vp8_vaapi',
                    'vp9': 'vp9_vaapi',
                    'av1': 'av1_vaapi'
                }
            
            encoder = encoder_map.get(codec, '')
            
            if encoder and not self.is_codec_container_compatible(encoder, container):
                fallback = self._get_software_encoder(codec, container)
                warning = f"⚠ AMD {codec.upper()} несовместим с {container.upper()}. Используется CPU: {fallback}"
                return fallback, warning
            
            if encoder in self.supported_encoders:
                logger.info(f"Используется AMD энкодер: {encoder}")
                return encoder, ""
        
        # Fallback на CPU
        fallback = self._get_software_encoder(codec, container)
        warning = f"ℹ GPU энкодер недоступен. Используется CPU: {fallback}"
        return fallback, warning
    
    def _get_gpu_name_by_vendor(self, vendor: str) -> str:
        """Получить имя GPU по vendor"""
        for gpu in self.detected_gpus:
            if gpu.vendor == vendor:
                return str(gpu)
        return vendor.upper()
    
    def _get_software_encoder(self, codec: str, container: str = 'mp4') -> str:
        """CPU энкодер с учетом контейнера"""
        if container.lower() in ['webm']:
            if codec in ['h264', 'hevc', 'h265']:
                logger.info(f"Конвертация {codec} -> vp9 для WebM")
                return 'libvpx-vp9'
            return {
                'vp8': 'libvpx',
                'vp9': 'libvpx-vp9',
                'av1': 'libaom-av1'
            }.get(codec, 'libvpx-vp9')
        
        return {
            'h264': 'libx264',
            'hevc': 'libx265',
            'h265': 'libx265',
            'vp8': 'libvpx',
            'vp9': 'libvpx-vp9',
            'av1': 'libaom-av1'
        }.get(codec, 'libx264')
    
    def get_hwaccel_args(self, preferred_gpu: str = 'auto') -> List[str]:
        """Аргументы hwaccel для декодирования"""
        if preferred_gpu == 'none' or not self.has_gpu_support():
            return []
        
        if preferred_gpu == 'auto' and self.detected_gpus:
            preferred_gpu = self.detected_gpus[0].vendor
        
        # NVIDIA
        if preferred_gpu == 'nvidia' and 'cuda' in self.supported_hwaccels:
            logger.info("Используется CUDA hwaccel")
            return ['-hwaccel', 'cuda']
        
        # Intel
        if preferred_gpu == 'intel' and 'qsv' in self.supported_hwaccels:
            logger.info("Используется QSV hwaccel")
            return ['-hwaccel', 'qsv']
        
        # AMD VAAPI
        if preferred_gpu == 'amd' and 'vaapi' in self.supported_hwaccels:
            vaapi_device = '/dev/dri/renderD128' if platform.system() == 'Linux' else None
            if vaapi_device and Path(vaapi_device).exists():
                logger.info("Используется VAAPI hwaccel")
                return ['-hwaccel', 'vaapi', '-hwaccel_device', vaapi_device]
        
        return []
    
    def get_encoder_preset(self, encoder: str, user_preset: Optional[str] = None) -> Optional[str]:
        """
        Корректный preset для энкодера

        Args:
            encoder: название энкодера (nvenc, qsv, amf, vaapi или cpu)
            user_preset: preset выбранный пользователем (ultrafast..veryslow)

        Returns:
            preset для конкретного энкодера или None если не поддерживается
        """
        encoder_lower = encoder.lower()

        # NVENC: использует p1-p7 вместо традиционных preset'ов
        if 'nvenc' in encoder_lower:
            # Маппинг пользовательских preset'ов в NVENC p1-p7
            if user_preset:
                preset_map = {
                    'ultrafast': 'p1',
                    'superfast': 'p2',
                    'veryfast': 'p3',
                    'faster': 'p3',
                    'fast': 'p4',
                    'medium': 'p4',
                    'slow': 'p5',
                    'slower': 'p6',
                    'veryslow': 'p7'
                }
                return preset_map.get(user_preset, 'p4')
            return 'p4'  # default

        # QSV: поддерживает veryslow, slower, slow, medium, fast, faster, veryfast
        if 'qsv' in encoder_lower:
            if user_preset and user_preset in ['veryslow', 'slower', 'slow', 'medium', 'fast', 'faster', 'veryfast']:
                return user_preset
            return 'medium'

        # AMF: использует собственные preset'ы
        if 'amf' in encoder_lower:
            # Маппинг в AMF preset'ы (quality, balanced, speed)
            if user_preset:
                if user_preset in ['veryslow', 'slower', 'slow']:
                    return 'quality'
                elif user_preset in ['veryfast', 'faster', 'fast', 'ultrafast', 'superfast']:
                    return 'speed'
            return 'balanced'  # default

        # VA-API: не поддерживает preset'ы
        if 'vaapi' in encoder_lower:
            return None

        # CPU кодеки (libx264, libx265) - используют стандартные preset'ы
        return user_preset if user_preset else 'medium'
    
    def get_gpu_list(self) -> List[Dict[str, str]]:
        """Список GPU для UI"""
        result = [{'id': 'auto', 'name': 'Авто (рекомендуется)'}]
        
        for gpu in self.detected_gpus:
            if gpu.vendor != 'none':
                codecs_str = ', '.join(sorted(gpu.supported_codecs)) if gpu.supported_codecs else 'нет кодеков'
                result.append({
                    'id': gpu.vendor,
                    'name': f"{str(gpu)} [{codecs_str}]"
                })
        
        result.append({'id': 'none', 'name': 'CPU (без ускорения)'})
        return result