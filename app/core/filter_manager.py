from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field, asdict
import json
import logging
from pathlib import Path

from .filter_profiles import FilterDatabase, FilterProfile, FilterCategory

logger = logging.getLogger(__name__)


@dataclass
class AppliedFilter:
    """Примененный фильтр с параметрами"""
    filter_id: str                      # ID фильтра из базы
    enabled: bool = True                # Включен ли фильтр
    parameters: Dict[str, Any] = field(default_factory=dict)  # Значения параметров

    def to_dict(self) -> dict:
        """Сериализация в словарь"""
        return {
            'filter_id': self.filter_id,
            'enabled': self.enabled,
            'parameters': self.parameters
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'AppliedFilter':
        """Десериализация из словаря"""
        return cls(
            filter_id=data['filter_id'],
            enabled=data.get('enabled', True),
            parameters=data.get('parameters', {})
        )


class FilterChain:
    """Цепочка фильтров"""

    def __init__(self):
        self.video_filters: List[AppliedFilter] = []
        self.audio_filters: List[AppliedFilter] = []

    def add_video_filter(self, filter_id: str, parameters: Dict[str, Any] = None) -> AppliedFilter:
        """Добавить видео фильтр"""
        applied = AppliedFilter(
            filter_id=filter_id,
            parameters=parameters or {}
        )
        self.video_filters.append(applied)
        logger.info(f"Добавлен видео фильтр: {filter_id}")
        return applied

    def add_audio_filter(self, filter_id: str, parameters: Dict[str, Any] = None) -> AppliedFilter:
        """Добавить аудио фильтр"""
        applied = AppliedFilter(
            filter_id=filter_id,
            parameters=parameters or {}
        )
        self.audio_filters.append(applied)
        logger.info(f"Добавлен аудио фильтр: {filter_id}")
        return applied

    def remove_video_filter(self, index: int):
        """Удалить видео фильтр по индексу"""
        if 0 <= index < len(self.video_filters):
            removed = self.video_filters.pop(index)
            logger.info(f"Удален видео фильтр: {removed.filter_id}")

    def remove_audio_filter(self, index: int):
        """Удалить аудио фильтр по индексу"""
        if 0 <= index < len(self.audio_filters):
            removed = self.audio_filters.pop(index)
            logger.info(f"Удален аудио фильтр: {removed.filter_id}")

    def move_video_filter(self, from_index: int, to_index: int):
        """Переместить видео фильтр"""
        if 0 <= from_index < len(self.video_filters) and 0 <= to_index < len(self.video_filters):
            filter_item = self.video_filters.pop(from_index)
            self.video_filters.insert(to_index, filter_item)
            logger.info(f"Перемещен видео фильтр с {from_index} на {to_index}")

    def move_audio_filter(self, from_index: int, to_index: int):
        """Переместить аудио фильтр"""
        if 0 <= from_index < len(self.audio_filters) and 0 <= to_index < len(self.audio_filters):
            filter_item = self.audio_filters.pop(from_index)
            self.audio_filters.insert(to_index, filter_item)
            logger.info(f"Перемещен аудио фильтр с {from_index} на {to_index}")

    def clear_video_filters(self):
        """Очистить все видео фильтры"""
        self.video_filters.clear()
        logger.info("Очищены все видео фильтры")

    def clear_audio_filters(self):
        """Очистить все аудио фильтры"""
        self.audio_filters.clear()
        logger.info("Очищены все аудио фильтры")

    def clear_all(self):
        """Очистить все фильтры"""
        self.clear_video_filters()
        self.clear_audio_filters()

    def get_enabled_video_filters(self) -> List[AppliedFilter]:
        """Получить только включенные видео фильтры"""
        return [f for f in self.video_filters if f.enabled]

    def get_enabled_audio_filters(self) -> List[AppliedFilter]:
        """Получить только включенные аудио фильтры"""
        return [f for f in self.audio_filters if f.enabled]

    def to_dict(self) -> dict:
        """Сериализация в словарь"""
        return {
            'video_filters': [f.to_dict() for f in self.video_filters],
            'audio_filters': [f.to_dict() for f in self.audio_filters]
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'FilterChain':
        """Десериализация из словаря"""
        chain = cls()
        chain.video_filters = [
            AppliedFilter.from_dict(f) for f in data.get('video_filters', [])
        ]
        chain.audio_filters = [
            AppliedFilter.from_dict(f) for f in data.get('audio_filters', [])
        ]
        return chain


class FilterManager:
    """Менеджер фильтров"""

    def __init__(self):
        self.database = FilterDatabase()
        self.chain = FilterChain()
        self.presets_dir = Path.home() / '.ffmpeg_converter' / 'filter_presets'
        self.presets_dir.mkdir(parents=True, exist_ok=True)
        logger.info("Инициализирован FilterManager")

    def get_filter_database(self) -> FilterDatabase:
        """Получить базу данных фильтров"""
        return self.database

    def get_filter_chain(self) -> FilterChain:
        """Получить текущую цепочку фильтров"""
        return self.chain

    def build_video_filter_string(self) -> Optional[str]:
        """
        Построить строку видео фильтров для FFmpeg

        Returns:
            Строка фильтров, например: "crop=w=1280:h=720,scale=1920:-1,hflip"
            None если нет включенных фильтров
        """
        enabled_filters = self.chain.get_enabled_video_filters()

        if not enabled_filters:
            return None

        filter_strings = []

        for applied_filter in enabled_filters:
            profile = self.database.get_filter(applied_filter.filter_id)
            if not profile:
                logger.warning(f"Фильтр не найден: {applied_filter.filter_id}")
                continue

            # Валидация параметров
            is_valid, error_msg = profile.validate_params(applied_filter.parameters)
            if not is_valid:
                logger.error(f"Ошибка валидации фильтра {profile.name}: {error_msg}")
                continue

            # Построение строки фильтра
            filter_str = profile.build_filter_string(applied_filter.parameters)
            filter_strings.append(filter_str)
            logger.debug(f"Добавлен фильтр в цепочку: {filter_str}")

        if not filter_strings:
            return None

        result = ','.join(filter_strings)
        logger.info(f"Построена строка видео фильтров: {result}")
        return result

    def build_audio_filter_string(self) -> Optional[str]:
        """
        Построить строку аудио фильтров для FFmpeg

        Returns:
            Строка фильтров, например: "volume=2.0,afade=t=in:d=2"
            None если нет включенных фильтров
        """
        enabled_filters = self.chain.get_enabled_audio_filters()

        if not enabled_filters:
            return None

        filter_strings = []

        for applied_filter in enabled_filters:
            profile = self.database.get_filter(applied_filter.filter_id)
            if not profile:
                logger.warning(f"Фильтр не найден: {applied_filter.filter_id}")
                continue

            # Валидация параметров
            is_valid, error_msg = profile.validate_params(applied_filter.parameters)
            if not is_valid:
                logger.error(f"Ошибка валидации фильтра {profile.name}: {error_msg}")
                continue

            # Построение строки фильтра
            filter_str = profile.build_filter_string(applied_filter.parameters)
            filter_strings.append(filter_str)
            logger.debug(f"Добавлен фильтр в цепочку: {filter_str}")

        if not filter_strings:
            return None

        result = ','.join(filter_strings)
        logger.info(f"Построена строка аудио фильтров: {result}")
        return result

    def save_preset(self, name: str, description: str = "") -> bool:
        """
        Сохранить текущую цепочку фильтров как пресет

        Args:
            name: Имя пресета
            description: Описание пресета

        Returns:
            True если успешно сохранено
        """
        try:
            preset_data = {
                'name': name,
                'description': description,
                'chain': self.chain.to_dict()
            }

            # Создаем безопасное имя файла
            safe_name = "".join(c for c in name if c.isalnum() or c in (' ', '-', '_')).strip()
            preset_file = self.presets_dir / f"{safe_name}.json"

            with open(preset_file, 'w', encoding='utf-8') as f:
                json.dump(preset_data, f, ensure_ascii=False, indent=2)

            logger.info(f"Сохранен пресет: {name} в {preset_file}")
            return True

        except Exception as e:
            logger.error(f"Ошибка сохранения пресета: {e}", exc_info=True)
            return False

    def load_preset(self, preset_file: Path) -> bool:
        """
        Загрузить пресет из файла

        Args:
            preset_file: Путь к файлу пресета

        Returns:
            True если успешно загружено
        """
        try:
            with open(preset_file, 'r', encoding='utf-8') as f:
                preset_data = json.load(f)

            # Загружаем цепочку фильтров
            self.chain = FilterChain.from_dict(preset_data['chain'])

            logger.info(f"Загружен пресет: {preset_data.get('name', 'Unknown')}")
            return True

        except Exception as e:
            logger.error(f"Ошибка загрузки пресета: {e}", exc_info=True)
            return False

    def get_available_presets(self) -> List[Dict[str, Any]]:
        """
        Получить список доступных пресетов

        Returns:
            Список словарей с информацией о пресетах
        """
        presets = []

        try:
            for preset_file in self.presets_dir.glob('*.json'):
                try:
                    with open(preset_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)

                    presets.append({
                        'name': data.get('name', preset_file.stem),
                        'description': data.get('description', ''),
                        'file': preset_file,
                        'video_count': len(data.get('chain', {}).get('video_filters', [])),
                        'audio_count': len(data.get('chain', {}).get('audio_filters', []))
                    })
                except Exception as e:
                    logger.warning(f"Не удалось прочитать пресет {preset_file}: {e}")

        except Exception as e:
            logger.error(f"Ошибка получения списка пресетов: {e}", exc_info=True)

        return presets

    def delete_preset(self, preset_file: Path) -> bool:
        """
        Удалить пресет

        Args:
            preset_file: Путь к файлу пресета

        Returns:
            True если успешно удалено
        """
        try:
            preset_file.unlink()
            logger.info(f"Удален пресет: {preset_file}")
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления пресета: {e}", exc_info=True)
            return False

    def create_builtin_presets(self):
        """Создать встроенные пресеты при первом запуске"""

        # Проверяем, есть ли уже пресеты
        if list(self.presets_dir.glob('*.json')):
            return

        logger.info("Создание встроенных пресетов фильтров")

        # Пресет: Поворот 90° по часовой
        self.chain.clear_all()
        self.chain.add_video_filter('transpose', {'dir': '1'})
        self.save_preset(
            "Поворот 90° по часовой",
            "Быстрый поворот видео на 90 градусов по часовой стрелке"
        )

        # Пресет: Отражение по горизонтали
        self.chain.clear_all()
        self.chain.add_video_filter('hflip')
        self.save_preset(
            "Зеркальное отражение",
            "Горизонтальное отражение видео (зеркало)"
        )

        # Пресет: Улучшение качества
        self.chain.clear_all()
        self.chain.add_video_filter('unsharp', {'luma_msize_x': 5, 'luma_msize_y': 5, 'luma_amount': 1.5})
        self.chain.add_video_filter('eq', {'contrast': 1.1, 'saturation': 1.1})
        self.save_preset(
            "Улучшение качества",
            "Увеличение резкости и насыщенности для улучшения картинки"
        )

        # Пресет: Деинтерлейсинг
        self.chain.clear_all()
        self.chain.add_video_filter('yadif', {'mode': '0', 'parity': '-1'})
        self.save_preset(
            "Удаление чересстрочности",
            "Деинтерлейсинг для старых видео камер"
        )

        # Пресет: Водяной знак
        self.chain.clear_all()
        self.chain.add_video_filter('drawtext', {
            'text': '© Copyright 2024',
            'fontsize': 24,
            'fontcolor': 'white',
            'x': '(w-text_w)-10',
            'y': '(h-text_h)-10',
            'box': True,
            'boxcolor': 'black@0.5'
        })
        self.save_preset(
            "Водяной знак (нижний правый)",
            "Добавление copyright текста в правом нижнем углу"
        )

        # Пресет: Нормализация звука
        self.chain.clear_all()
        self.chain.add_audio_filter('loudnorm', {'I': -16.0, 'LRA': 11.0})
        self.save_preset(
            "Нормализация звука",
            "EBU R128 нормализация громкости для веб-платформ"
        )

        # Пресет: Fade In/Out
        self.chain.clear_all()
        self.chain.add_video_filter('fade', {'type': 'in', 'start_frame': 0, 'nb_frames': 30})
        self.chain.add_audio_filter('afade', {'type': 'in', 'start_time': 0, 'duration': 1.0})
        self.save_preset(
            "Плавное появление",
            "Fade in для видео и аудио в начале"
        )

        # Очищаем цепочку после создания пресетов
        self.chain.clear_all()

        logger.info("Встроенные пресеты созданы")

    def get_filter_summary(self) -> Dict[str, Any]:
        """
        Получить сводку о текущих фильтрах

        Returns:
            Словарь с информацией о фильтрах
        """
        return {
            'video_filters_count': len(self.chain.video_filters),
            'audio_filters_count': len(self.chain.audio_filters),
            'video_enabled_count': len(self.chain.get_enabled_video_filters()),
            'audio_enabled_count': len(self.chain.get_enabled_audio_filters()),
            'has_filters': len(self.chain.video_filters) > 0 or len(self.chain.audio_filters) > 0
        }