from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class FilterCategory(Enum):
    """Категории фильтров"""
    VIDEO_TRANSFORM = "video_transform"      # Трансформации (rotate, flip, crop)
    VIDEO_ADJUST = "video_adjust"            # Настройки (brightness, contrast, saturation)
    VIDEO_EFFECTS = "video_effects"          # Эффекты (blur, sharpen, denoise)
    VIDEO_OVERLAY = "video_overlay"          # Наложения (text, logo, watermark)
    VIDEO_TIME = "video_time"                # Временные (fade, speed)
    AUDIO_VOLUME = "audio_volume"            # Громкость
    AUDIO_EFFECTS = "audio_effects"          # Аудио эффекты
    AUDIO_FILTER = "audio_filter"            # Фильтры частот


class FilterParamType(Enum):
    """Типы параметров фильтра"""
    INT = "int"                  # Целое число
    FLOAT = "float"              # Дробное число
    STRING = "string"            # Строка
    BOOL = "bool"                # Булево значение
    CHOICE = "choice"            # Выбор из списка
    COLOR = "color"              # Цвет
    FILE = "file"                # Путь к файлу
    FONT = "font"                # Шрифт
    POSITION = "position"        # Позиция (x, y)
    SIZE = "size"                # Размер (width, height)


@dataclass
class FilterParameter:
    """Параметр фильтра"""
    name: str                           # Имя параметра для FFmpeg
    display_name: str                   # Отображаемое имя
    param_type: FilterParamType         # Тип параметра
    default_value: Any                  # Значение по умолчанию
    description: str                    # Описание

    # Ограничения
    min_value: Optional[float] = None   # Минимальное значение (для числовых)
    max_value: Optional[float] = None   # Максимальное значение (для числовых)
    choices: Optional[List[tuple]] = None  # Варианты выбора [(value, label), ...]

    # UI hints
    step: Optional[float] = None        # Шаг для числовых значений
    suffix: Optional[str] = None        # Суффикс (%, px, etc.)

    # Validation
    required: bool = False              # Обязательный параметр
    depends_on: Optional[str] = None    # Зависит от другого параметра


@dataclass
class FilterProfile:
    """Профиль фильтра"""
    id: str                             # Уникальный ID
    name: str                           # Название фильтра
    ffmpeg_name: str                    # Имя фильтра в FFmpeg
    category: FilterCategory            # Категория
    description: str                    # Описание

    # Параметры
    parameters: List[FilterParameter] = field(default_factory=list)

    # Метаданные
    icon: Optional[str] = None          # Иконка (emoji или путь)
    requires_gpu: bool = False          # Требует GPU
    processing_cost: int = 1            # Вычислительная стоимость (1-5)

    # Генерация команды
    command_template: Optional[str] = None  # Шаблон команды (если сложная логика)

    def build_filter_string(self, params: Dict[str, Any]) -> str:
        """
        Построить строку фильтра для FFmpeg

        Args:
            params: Словарь параметров {name: value}

        Returns:
            Строка фильтра, например: "crop=w=1280:h=720:x=0:y=0"
        """
        if self.command_template:
            # Используем кастомный шаблон
            return self.command_template.format(**params)

        # Стандартная генерация
        filter_parts = [self.ffmpeg_name]

        # Собираем параметры
        param_strings = []
        for param in self.parameters:
            value = params.get(param.name, param.default_value)

            # Пропускаем None и пустые значения
            if value is None or value == "":
                continue

            # Булевы значения
            if param.param_type == FilterParamType.BOOL:
                if value:
                    param_strings.append(f"{param.name}=1")
                continue

            # Остальные типы
            param_strings.append(f"{param.name}={value}")

        if param_strings:
            filter_parts.append("=".join([""] + [":".join(param_strings)]))
            return "".join(filter_parts)

        return self.ffmpeg_name

    def validate_params(self, params: Dict[str, Any]) -> tuple[bool, str]:
        """
        Валидация параметров

        Returns:
            (is_valid, error_message)
        """
        for param in self.parameters:
            if param.required and param.name not in params:
                return False, f"Параметр '{param.display_name}' обязателен"

            value = params.get(param.name)
            if value is None:
                continue

            # Проверка диапазона для числовых
            if param.param_type in [FilterParamType.INT, FilterParamType.FLOAT]:
                if param.min_value is not None and value < param.min_value:
                    return False, f"{param.display_name} не может быть меньше {param.min_value}"
                if param.max_value is not None and value > param.max_value:
                    return False, f"{param.display_name} не может быть больше {param.max_value}"

            # Проверка choices
            if param.param_type == FilterParamType.CHOICE and param.choices:
                valid_values = [choice[0] for choice in param.choices]
                if value not in valid_values:
                    return False, f"Недопустимое значение для {param.display_name}"

        return True, ""


class FilterDatabase:
    """База данных фильтров"""

    def __init__(self):
        self.filters: Dict[str, FilterProfile] = {}
        self._initialize_filters()
        logger.info(f"Инициализирована база фильтров: {len(self.filters)} фильтров")

    def _initialize_filters(self):
        """Инициализация всех фильтров"""

        # ============= VIDEO TRANSFORM =============

        # Crop - обрезка
        self.filters['crop'] = FilterProfile(
            id='crop',
            name='Обрезка (Crop)',
            ffmpeg_name='crop',
            category=FilterCategory.VIDEO_TRANSFORM,
            description='Обрезка видео до заданного размера и позиции',
            icon='✂️',
            processing_cost=1,
            parameters=[
                FilterParameter(
                    name='w', display_name='Ширина', param_type=FilterParamType.INT,
                    default_value=1280, min_value=16, max_value=7680,
                    description='Ширина обрезанного видео', required=True, suffix='px'
                ),
                FilterParameter(
                    name='h', display_name='Высота', param_type=FilterParamType.INT,
                    default_value=720, min_value=16, max_value=4320,
                    description='Высота обрезанного видео', required=True, suffix='px'
                ),
                FilterParameter(
                    name='x', display_name='Позиция X', param_type=FilterParamType.INT,
                    default_value=0, min_value=0, max_value=7680,
                    description='Горизонтальная позиция начала обрезки', suffix='px'
                ),
                FilterParameter(
                    name='y', display_name='Позиция Y', param_type=FilterParamType.INT,
                    default_value=0, min_value=0, max_value=4320,
                    description='Вертикальная позиция начала обрезки', suffix='px'
                ),
            ]
        )

        # Rotate - поворот
        self.filters['rotate'] = FilterProfile(
            id='rotate',
            name='Поворот (Rotate)',
            ffmpeg_name='rotate',
            category=FilterCategory.VIDEO_TRANSFORM,
            description='Поворот видео на заданный угол',
            icon='🔄',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='angle', display_name='Угол', param_type=FilterParamType.CHOICE,
                    default_value='PI/2',
                    choices=[
                        ('0', '0° (без поворота)'),
                        ('PI/2', '90° по часовой'),
                        ('PI', '180°'),
                        ('-PI/2', '270° (или 90° против часовой)'),
                        ('PI/4', '45° по часовой'),
                        ('-PI/4', '45° против часовой'),
                    ],
                    description='Угол поворота', required=True
                ),
                FilterParameter(
                    name='fillcolor', display_name='Цвет фона', param_type=FilterParamType.COLOR,
                    default_value='black',
                    description='Цвет заполнения пустых областей'
                ),
            ]
        )

        # Transpose - быстрый поворот на 90°
        self.filters['transpose'] = FilterProfile(
            id='transpose',
            name='Быстрый поворот (Transpose)',
            ffmpeg_name='transpose',
            category=FilterCategory.VIDEO_TRANSFORM,
            description='Быстрый поворот на 90° без потери качества',
            icon='↻',
            processing_cost=1,
            parameters=[
                FilterParameter(
                    name='dir', display_name='Направление', param_type=FilterParamType.CHOICE,
                    default_value='1',
                    choices=[
                        ('0', '90° против часовой + вертикальное отражение'),
                        ('1', '90° по часовой'),
                        ('2', '90° против часовой'),
                        ('3', '90° по часовой + вертикальное отражение'),
                    ],
                    description='Направление поворота', required=True
                ),
            ]
        )

        # Flip - отражение
        self.filters['hflip'] = FilterProfile(
            id='hflip',
            name='Горизонтальное отражение',
            ffmpeg_name='hflip',
            category=FilterCategory.VIDEO_TRANSFORM,
            description='Отражение видео по горизонтали (зеркало)',
            icon='↔️',
            processing_cost=1,
            parameters=[]
        )

        self.filters['vflip'] = FilterProfile(
            id='vflip',
            name='Вертикальное отражение',
            ffmpeg_name='vflip',
            category=FilterCategory.VIDEO_TRANSFORM,
            description='Отражение видео по вертикали',
            icon='↕️',
            processing_cost=1,
            parameters=[]
        )

        # Scale - масштабирование (расширенное)
        self.filters['scale_advanced'] = FilterProfile(
            id='scale_advanced',
            name='Масштабирование (Scale)',
            ffmpeg_name='scale',
            category=FilterCategory.VIDEO_TRANSFORM,
            description='Изменение разрешения видео с сохранением пропорций',
            icon='🔍',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='w', display_name='Ширина', param_type=FilterParamType.INT,
                    default_value=1920, min_value=-1, max_value=7680,
                    description='Ширина (-1 для автоматического расчета)', suffix='px'
                ),
                FilterParameter(
                    name='h', display_name='Высота', param_type=FilterParamType.INT,
                    default_value=-1, min_value=-1, max_value=4320,
                    description='Высота (-1 для автоматического расчета)', suffix='px'
                ),
                FilterParameter(
                    name='flags', display_name='Алгоритм', param_type=FilterParamType.CHOICE,
                    default_value='lanczos',
                    choices=[
                        ('fast_bilinear', 'Быстрый билинейный'),
                        ('bilinear', 'Билинейный'),
                        ('bicubic', 'Бикубический'),
                        ('lanczos', 'Lanczos (лучшее качество)'),
                        ('spline', 'Spline'),
                    ],
                    description='Алгоритм масштабирования'
                ),
            ]
        )

        # ============= VIDEO ADJUST =============

        # Brightness/Contrast/Saturation
        self.filters['eq'] = FilterProfile(
            id='eq',
            name='Яркость/Контраст/Насыщенность',
            ffmpeg_name='eq',
            category=FilterCategory.VIDEO_ADJUST,
            description='Настройка яркости, контраста, насыщенности и гаммы',
            icon='🎨',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='brightness', display_name='Яркость', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-1.0, max_value=1.0, step=0.1,
                    description='Яркость (-1.0 = темнее, +1.0 = светлее)'
                ),
                FilterParameter(
                    name='contrast', display_name='Контраст', param_type=FilterParamType.FLOAT,
                    default_value=1.0, min_value=-1000.0, max_value=1000.0, step=0.1,
                    description='Контраст (1.0 = без изменений)'
                ),
                FilterParameter(
                    name='saturation', display_name='Насыщенность', param_type=FilterParamType.FLOAT,
                    default_value=1.0, min_value=0.0, max_value=3.0, step=0.1,
                    description='Насыщенность цвета (0 = ч/б, 1 = норма, >1 = насыщеннее)'
                ),
                FilterParameter(
                    name='gamma', display_name='Гамма', param_type=FilterParamType.FLOAT,
                    default_value=1.0, min_value=0.1, max_value=10.0, step=0.1,
                    description='Гамма коррекция (1.0 = без изменений)'
                ),
            ]
        )

        # Hue - цветовой тон
        self.filters['hue'] = FilterProfile(
            id='hue',
            name='Цветовой тон (Hue)',
            ffmpeg_name='hue',
            category=FilterCategory.VIDEO_ADJUST,
            description='Изменение цветового тона и насыщенности',
            icon='🌈',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='h', display_name='Тон', param_type=FilterParamType.FLOAT,
                    default_value=0, min_value=-180, max_value=180, step=1,
                    description='Сдвиг цветового тона', suffix='°'
                ),
                FilterParameter(
                    name='s', display_name='Насыщенность', param_type=FilterParamType.FLOAT,
                    default_value=1.0, min_value=-10.0, max_value=10.0, step=0.1,
                    description='Насыщенность (1.0 = без изменений)'
                ),
            ]
        )

        # ============= VIDEO EFFECTS =============

        # Unsharp - резкость
        self.filters['unsharp'] = FilterProfile(
            id='unsharp',
            name='Резкость (Unsharp)',
            ffmpeg_name='unsharp',
            category=FilterCategory.VIDEO_EFFECTS,
            description='Увеличение или уменьшение резкости',
            icon='🔪',
            processing_cost=3,
            parameters=[
                FilterParameter(
                    name='luma_msize_x', display_name='Размер матрицы X', param_type=FilterParamType.INT,
                    default_value=5, min_value=3, max_value=23, step=2,
                    description='Размер матрицы по горизонтали (нечетное число)'
                ),
                FilterParameter(
                    name='luma_msize_y', display_name='Размер матрицы Y', param_type=FilterParamType.INT,
                    default_value=5, min_value=3, max_value=23, step=2,
                    description='Размер матрицы по вертикали (нечетное число)'
                ),
                FilterParameter(
                    name='luma_amount', display_name='Сила эффекта', param_type=FilterParamType.FLOAT,
                    default_value=1.0, min_value=-2.0, max_value=5.0, step=0.1,
                    description='Сила эффекта резкости (отрицательное = размытие)'
                ),
            ]
        )

        # Denoise - шумоподавление
        self.filters['hqdn3d'] = FilterProfile(
            id='hqdn3d',
            name='Шумоподавление (Denoise)',
            ffmpeg_name='hqdn3d',
            category=FilterCategory.VIDEO_EFFECTS,
            description='Высококачественное шумоподавление',
            icon='🧹',
            processing_cost=4,
            parameters=[
                FilterParameter(
                    name='luma_spatial', display_name='Пространственное', param_type=FilterParamType.FLOAT,
                    default_value=4.0, min_value=0.0, max_value=10.0, step=0.5,
                    description='Пространственное шумоподавление'
                ),
                FilterParameter(
                    name='luma_tmp', display_name='Временное', param_type=FilterParamType.FLOAT,
                    default_value=3.0, min_value=0.0, max_value=10.0, step=0.5,
                    description='Временное шумоподавление'
                ),
            ]
        )

        # Deinterlace - деинтерлейсинг
        self.filters['yadif'] = FilterProfile(
            id='yadif',
            name='Деинтерлейсинг (Yadif)',
            ffmpeg_name='yadif',
            category=FilterCategory.VIDEO_EFFECTS,
            description='Удаление чересстрочности (interlacing)',
            icon='📺',
            processing_cost=3,
            parameters=[
                FilterParameter(
                    name='mode', display_name='Режим', param_type=FilterParamType.CHOICE,
                    default_value='0',
                    choices=[
                        ('0', 'Один кадр на поле'),
                        ('1', 'Один кадр на кадр'),
                    ],
                    description='Режим деинтерлейсинга'
                ),
                FilterParameter(
                    name='parity', display_name='Чередование', param_type=FilterParamType.CHOICE,
                    default_value='-1',
                    choices=[
                        ('-1', 'Автоматически'),
                        ('0', 'Top field first'),
                        ('1', 'Bottom field first'),
                    ],
                    description='Порядок полей'
                ),
            ]
        )

        # ============= VIDEO OVERLAY =============

        # Drawtext - текст/watermark
        self.filters['drawtext'] = FilterProfile(
            id='drawtext',
            name='Наложение текста',
            ffmpeg_name='drawtext',
            category=FilterCategory.VIDEO_OVERLAY,
            description='Добавление текста или водяного знака на видео',
            icon='📝',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='text', display_name='Текст', param_type=FilterParamType.STRING,
                    default_value='',
                    description='Текст для отображения', required=True
                ),
                FilterParameter(
                    name='fontsize', display_name='Размер шрифта', param_type=FilterParamType.INT,
                    default_value=24, min_value=8, max_value=200,
                    description='Размер шрифта', suffix='px'
                ),
                FilterParameter(
                    name='fontcolor', display_name='Цвет текста', param_type=FilterParamType.COLOR,
                    default_value='white',
                    description='Цвет текста'
                ),
                FilterParameter(
                    name='x', display_name='Позиция X', param_type=FilterParamType.STRING,
                    default_value='10',
                    description='Позиция X (число или выражение: (w-text_w)/2 для центра)'
                ),
                FilterParameter(
                    name='y', display_name='Позиция Y', param_type=FilterParamType.STRING,
                    default_value='10',
                    description='Позиция Y (число или выражение: (h-text_h)/2 для центра)'
                ),
                FilterParameter(
                    name='box', display_name='Фон', param_type=FilterParamType.BOOL,
                    default_value=False,
                    description='Добавить фон под текстом'
                ),
                FilterParameter(
                    name='boxcolor', display_name='Цвет фона', param_type=FilterParamType.COLOR,
                    default_value='black@0.5',
                    description='Цвет фона (с прозрачностью)', depends_on='box'
                ),
            ]
        )

        # ============= VIDEO TIME =============

        # Fade - затухание
        self.filters['fade'] = FilterProfile(
            id='fade',
            name='Затухание (Fade)',
            ffmpeg_name='fade',
            category=FilterCategory.VIDEO_TIME,
            description='Плавное появление или затухание видео',
            icon='🌅',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='type', display_name='Тип', param_type=FilterParamType.CHOICE,
                    default_value='in',
                    choices=[
                        ('in', 'Fade In (появление)'),
                        ('out', 'Fade Out (исчезновение)'),
                    ],
                    description='Тип затухания', required=True
                ),
                FilterParameter(
                    name='start_frame', display_name='Начальный кадр', param_type=FilterParamType.INT,
                    default_value=0, min_value=0, max_value=999999,
                    description='Номер кадра начала эффекта'
                ),
                FilterParameter(
                    name='nb_frames', display_name='Длительность', param_type=FilterParamType.INT,
                    default_value=25, min_value=1, max_value=1000,
                    description='Длительность эффекта в кадрах'
                ),
                FilterParameter(
                    name='color', display_name='Цвет', param_type=FilterParamType.COLOR,
                    default_value='black',
                    description='Цвет затухания'
                ),
            ]
        )

        # ============= AUDIO VOLUME =============

        # Volume - громкость
        self.filters['volume'] = FilterProfile(
            id='volume',
            name='Громкость (Volume)',
            ffmpeg_name='volume',
            category=FilterCategory.AUDIO_VOLUME,
            description='Изменение громкости аудио',
            icon='🔊',
            processing_cost=1,
            parameters=[
                FilterParameter(
                    name='volume', display_name='Громкость', param_type=FilterParamType.FLOAT,
                    default_value=1.0, min_value=0.0, max_value=10.0, step=0.1,
                    description='Множитель громкости (1.0 = без изменений, 2.0 = в 2 раза громче)'
                ),
            ]
        )

        # ============= AUDIO EFFECTS =============

        # Afade - затухание аудио
        self.filters['afade'] = FilterProfile(
            id='afade',
            name='Затухание аудио (Fade)',
            ffmpeg_name='afade',
            category=FilterCategory.AUDIO_EFFECTS,
            description='Плавное появление или затухание звука',
            icon='🔇',
            processing_cost=1,
            parameters=[
                FilterParameter(
                    name='type', display_name='Тип', param_type=FilterParamType.CHOICE,
                    default_value='in',
                    choices=[
                        ('in', 'Fade In (появление)'),
                        ('out', 'Fade Out (исчезновение)'),
                    ],
                    description='Тип затухания', required=True
                ),
                FilterParameter(
                    name='start_time', display_name='Начало', param_type=FilterParamType.FLOAT,
                    default_value=0, min_value=0, max_value=3600, step=0.1,
                    description='Время начала эффекта', suffix='сек'
                ),
                FilterParameter(
                    name='duration', display_name='Длительность', param_type=FilterParamType.FLOAT,
                    default_value=1.0, min_value=0.1, max_value=60, step=0.1,
                    description='Длительность эффекта', suffix='сек'
                ),
            ]
        )

        # Loudnorm - нормализация громкости
        self.filters['loudnorm'] = FilterProfile(
            id='loudnorm',
            name='Нормализация громкости',
            ffmpeg_name='loudnorm',
            category=FilterCategory.AUDIO_EFFECTS,
            description='EBU R128 нормализация громкости',
            icon='📊',
            processing_cost=3,
            parameters=[
                FilterParameter(
                    name='I', display_name='Целевая громкость', param_type=FilterParamType.FLOAT,
                    default_value=-16.0, min_value=-70.0, max_value=-5.0, step=1.0,
                    description='Целевая интегрированная громкость', suffix='LUFS'
                ),
                FilterParameter(
                    name='LRA', display_name='Диапазон', param_type=FilterParamType.FLOAT,
                    default_value=11.0, min_value=1.0, max_value=20.0, step=1.0,
                    description='Целевой диапазон громкости', suffix='LU'
                ),
            ]
        )

        # ============= AUDIO FILTER =============

        # Highpass - ВЧ фильтр
        self.filters['highpass'] = FilterProfile(
            id='highpass',
            name='Фильтр высоких частот',
            ffmpeg_name='highpass',
            category=FilterCategory.AUDIO_FILTER,
            description='Пропускает только высокие частоты (обрезает басы)',
            icon='📈',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='f', display_name='Частота среза', param_type=FilterParamType.INT,
                    default_value=200, min_value=10, max_value=20000, step=10,
                    description='Частота среза', suffix='Hz'
                ),
            ]
        )

        # Lowpass - НЧ фильтр
        self.filters['lowpass'] = FilterProfile(
            id='lowpass',
            name='Фильтр низких частот',
            ffmpeg_name='lowpass',
            category=FilterCategory.AUDIO_FILTER,
            description='Пропускает только низкие частоты (обрезает высокие)',
            icon='📉',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='f', display_name='Частота среза', param_type=FilterParamType.INT,
                    default_value=3000, min_value=10, max_value=20000, step=10,
                    description='Частота среза', suffix='Hz'
                ),
            ]
        )

    def get_filter(self, filter_id: str) -> Optional[FilterProfile]:
        """Получить фильтр по ID"""
        return self.filters.get(filter_id)

    def get_filters_by_category(self, category: FilterCategory) -> List[FilterProfile]:
        """Получить все фильтры категории"""
        return [f for f in self.filters.values() if f.category == category]

    def get_all_filters(self) -> List[FilterProfile]:
        """Получить все фильтры"""
        return list(self.filters.values())

    def search_filters(self, query: str) -> List[FilterProfile]:
        """Поиск фильтров по названию или описанию"""
        query_lower = query.lower()
        return [
            f for f in self.filters.values()
            if query_lower in f.name.lower() or query_lower in f.description.lower()
        ]