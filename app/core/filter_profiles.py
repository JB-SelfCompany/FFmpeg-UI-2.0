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
    VIDEO_STABILIZE = "video_stabilize"      # Стабилизация видео
    VIDEO_CREATIVE = "video_creative"        # Креативные эффекты (chromakey, reverse, zoom)
    VIDEO_OVERLAY = "video_overlay"          # Наложения (text, logo, watermark)
    VIDEO_TIME = "video_time"                # Временные (fade, speed)
    VIDEO_COLOR = "video_color"              # Цветокоррекция (расширенная)
    VIDEO_BLUR = "video_blur"                # Размытие
    VIDEO_DEINTERLACE = "video_deinterlace"  # Деинтерлейсинг
    VIDEO_ANALYSIS = "video_analysis"        # Анализ и визуализация
    AUDIO_VOLUME = "audio_volume"            # Громкость
    AUDIO_EFFECTS = "audio_effects"          # Аудио эффекты
    AUDIO_FILTER = "audio_filter"            # Фильтры частот
    AUDIO_DYNAMICS = "audio_dynamics"        # Динамическая обработка
    AUDIO_EQ = "audio_eq"                    # Эквализация
    AUDIO_SPATIAL = "audio_spatial"          # Пространственная обработка
    AUDIO_DENOISE = "audio_denoise"          # Шумоподавление


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
            name='Обрезка',
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
            name='Поворот',
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
            name='Быстрый поворот',
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
            name='Масштабирование',
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
            name='Цветовой тон',
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

        # Color Balance - баланс цветов
        self.filters['colorbalance'] = FilterProfile(
            id='colorbalance',
            name='Баланс цветов',
            ffmpeg_name='colorbalance',
            category=FilterCategory.VIDEO_ADJUST,
            description='Раздельная настройка цветового баланса для теней, средних тонов и светов',
            icon='🎨',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='rs', display_name='Красный (тени)', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-1.0, max_value=1.0, step=0.01,
                    description='Красный канал в тенях (-1.0=cyan, +1.0=red)'
                ),
                FilterParameter(
                    name='gs', display_name='Зелёный (тени)', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-1.0, max_value=1.0, step=0.01,
                    description='Зелёный канал в тенях (-1.0=magenta, +1.0=green)'
                ),
                FilterParameter(
                    name='bs', display_name='Синий (тени)', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-1.0, max_value=1.0, step=0.01,
                    description='Синий канал в тенях (-1.0=yellow, +1.0=blue)'
                ),
                FilterParameter(
                    name='rm', display_name='Красный (средние)', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-1.0, max_value=1.0, step=0.01,
                    description='Красный канал в средних тонах'
                ),
                FilterParameter(
                    name='gm', display_name='Зелёный (средние)', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-1.0, max_value=1.0, step=0.01,
                    description='Зелёный канал в средних тонах'
                ),
                FilterParameter(
                    name='bm', display_name='Синий (средние)', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-1.0, max_value=1.0, step=0.01,
                    description='Синий канал в средних тонах'
                ),
                FilterParameter(
                    name='rh', display_name='Красный (света)', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-1.0, max_value=1.0, step=0.01,
                    description='Красный канал в светах'
                ),
                FilterParameter(
                    name='gh', display_name='Зелёный (света)', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-1.0, max_value=1.0, step=0.01,
                    description='Зелёный канал в светах'
                ),
                FilterParameter(
                    name='bh', display_name='Синий (света)', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-1.0, max_value=1.0, step=0.01,
                    description='Синий канал в светах'
                ),
            ]
        )

        # Vibrance - живость цвета
        self.filters['vibrance'] = FilterProfile(
            id='vibrance',
            name='Живость цвета',
            ffmpeg_name='vibrance',
            category=FilterCategory.VIDEO_ADJUST,
            description='Умная насыщенность - усиливает приглушённые цвета, не перенасыщая яркие',
            icon='✨',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='intensity', display_name='Интенсивность', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-2.0, max_value=2.0, step=0.1,
                    description='Сила эффекта (отрицательные значения уменьшают живость)'
                ),
                FilterParameter(
                    name='rbal', display_name='Баланс красного', param_type=FilterParamType.FLOAT,
                    default_value=1.0, min_value=0.0, max_value=10.0, step=0.1,
                    description='Баланс красного канала'
                ),
                FilterParameter(
                    name='gbal', display_name='Баланс зелёного', param_type=FilterParamType.FLOAT,
                    default_value=1.0, min_value=0.0, max_value=10.0, step=0.1,
                    description='Баланс зелёного канала'
                ),
                FilterParameter(
                    name='bbal', display_name='Баланс синего', param_type=FilterParamType.FLOAT,
                    default_value=1.0, min_value=0.0, max_value=10.0, step=0.1,
                    description='Баланс синего канала'
                ),
            ]
        )

        # ============= VIDEO EFFECTS =============

        # Unsharp - резкость
        self.filters['unsharp'] = FilterProfile(
            id='unsharp',
            name='Резкость',
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
            name='Шумоподавление',
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

        # NLMeans - продвинутое шумоподавление
        self.filters['nlmeans'] = FilterProfile(
            id='nlmeans',
            name='Продвинутое шумоподавление',
            ffmpeg_name='nlmeans',
            category=FilterCategory.VIDEO_EFFECTS,
            description='Non-Local Means шумоподавление - сохраняет детали лучше чем hqdn3d',
            icon='🧹',
            processing_cost=5,
            parameters=[
                FilterParameter(
                    name='s', display_name='Сила', param_type=FilterParamType.FLOAT,
                    default_value=1.0, min_value=0.0, max_value=30.0, step=0.5,
                    description='Сила шумоподавления (выше=сильнее)'
                ),
                FilterParameter(
                    name='p', display_name='Размер патча', param_type=FilterParamType.INT,
                    default_value=7, min_value=0, max_value=99,
                    description='Размер патча для сравнения (0=автоматически)', suffix='px'
                ),
                FilterParameter(
                    name='r', display_name='Радиус поиска', param_type=FilterParamType.INT,
                    default_value=15, min_value=0, max_value=99,
                    description='Радиус области поиска (больше=медленнее, качественнее)', suffix='px'
                ),
            ]
        )

        # ============= VIDEO STABILIZE =============

        # Video Stabilization (deshake) - простая стабилизация
        self.filters['deshake'] = FilterProfile(
            id='deshake',
            name='Стабилизация',
            ffmpeg_name='deshake',
            category=FilterCategory.VIDEO_STABILIZE,
            description='Быстрое удаление дрожания камеры',
            icon='📷',
            processing_cost=3,
            parameters=[
                FilterParameter(
                    name='x', display_name='Размер окна X', param_type=FilterParamType.INT,
                    default_value=-1, min_value=-1, max_value=512,
                    description='Ширина области поиска (-1 = полная ширина)', suffix='px'
                ),
                FilterParameter(
                    name='y', display_name='Размер окна Y', param_type=FilterParamType.INT,
                    default_value=-1, min_value=-1, max_value=512,
                    description='Высота области поиска (-1 = полная высота)', suffix='px'
                ),
                FilterParameter(
                    name='rx', display_name='Макс. смещение X', param_type=FilterParamType.INT,
                    default_value=16, min_value=0, max_value=64,
                    description='Максимальное горизонтальное смещение', suffix='px'
                ),
                FilterParameter(
                    name='ry', display_name='Макс. смещение Y', param_type=FilterParamType.INT,
                    default_value=16, min_value=0, max_value=64,
                    description='Максимальное вертикальное смещение', suffix='px'
                ),
            ]
        )

        # Video Stabilization Detect (vidstabdetect) - анализ для 2-pass
        self.filters['vidstabdetect'] = FilterProfile(
            id='vidstabdetect',
            name='Анализ стабилизации (Проход 1)',
            ffmpeg_name='vidstabdetect',
            category=FilterCategory.VIDEO_STABILIZE,
            description='Первый проход: анализ движения камеры для vidstabtransform',
            icon='🔍',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='shakiness', display_name='Чувствительность', param_type=FilterParamType.INT,
                    default_value=5, min_value=1, max_value=10,
                    description='Уровень дрожания камеры (1=минимум, 10=максимум)'
                ),
                FilterParameter(
                    name='accuracy', display_name='Точность', param_type=FilterParamType.INT,
                    default_value=15, min_value=1, max_value=15,
                    description='Точность анализа (выше=медленнее, но точнее)'
                ),
                FilterParameter(
                    name='stepsize', display_name='Шаг анализа', param_type=FilterParamType.INT,
                    default_value=6, min_value=1, max_value=32,
                    description='Размер шага поиска (меньше=точнее, медленнее)'
                ),
                FilterParameter(
                    name='result', display_name='Файл результата', param_type=FilterParamType.STRING,
                    default_value='transforms.trf',
                    description='Путь к файлу с данными трансформации'
                ),
            ]
        )

        # Video Stabilization Transform (vidstabtransform) - применение для 2-pass
        self.filters['vidstabtransform'] = FilterProfile(
            id='vidstabtransform',
            name='Стабилизация (Проход 2)',
            ffmpeg_name='vidstabtransform',
            category=FilterCategory.VIDEO_STABILIZE,
            description='Второй проход: применение стабилизации на основе данных vidstabdetect',
            icon='✨',
            processing_cost=3,
            parameters=[
                FilterParameter(
                    name='input', display_name='Файл данных', param_type=FilterParamType.STRING,
                    default_value='transforms.trf',
                    description='Путь к файлу с данными трансформации от vidstabdetect'
                ),
                FilterParameter(
                    name='smoothing', display_name='Сглаживание', param_type=FilterParamType.INT,
                    default_value=10, min_value=0, max_value=100,
                    description='Величина сглаживания движения (0=без сглаживания)'
                ),
                FilterParameter(
                    name='zoom', display_name='Зум', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-20.0, max_value=20.0, step=0.5,
                    description='Дополнительный зум для скрытия границ (%)', suffix='%'
                ),
                FilterParameter(
                    name='optzoom', display_name='Авто-зум', param_type=FilterParamType.CHOICE,
                    default_value='1',
                    choices=[('0', 'Отключен'), ('1', 'Оптимальный'), ('2', 'Адаптивный')],
                    description='Автоматический зум для скрытия черных границ'
                ),
                FilterParameter(
                    name='interpol', display_name='Интерполяция', param_type=FilterParamType.CHOICE,
                    default_value='bilinear',
                    choices=[
                        ('no', 'Без интерполяции'),
                        ('linear', 'Линейная'),
                        ('bilinear', 'Билинейная'),
                        ('bicubic', 'Бикубическая')
                    ],
                    description='Метод интерполяции пикселей'
                ),
            ]
        )

        # Deinterlace - деинтерлейсинг
        self.filters['yadif'] = FilterProfile(
            id='yadif',
            name='Деинтерлейсинг',
            ffmpeg_name='yadif',
            category=FilterCategory.VIDEO_EFFECTS,
            description='Удаление чересстрочности',
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

        # ============= VIDEO CREATIVE =============

        # Chromakey - хромакей (зелёный/синий экран)
        self.filters['chromakey'] = FilterProfile(
            id='chromakey',
            name='Хромакей (Green/Blue)',
            ffmpeg_name='chromakey',
            category=FilterCategory.VIDEO_CREATIVE,
            description='Удаление зелёного или синего фона для композитинга',
            icon='🎬',
            processing_cost=3,
            parameters=[
                FilterParameter(
                    name='color', display_name='Цвет ключа', param_type=FilterParamType.COLOR,
                    default_value='0x00ff00',
                    description='Цвет для удаления (по умолчанию зелёный)'
                ),
                FilterParameter(
                    name='similarity', display_name='Схожесть', param_type=FilterParamType.FLOAT,
                    default_value=0.3, min_value=0.0, max_value=1.0, step=0.01,
                    description='Допуск схожести цвета (выше=больше оттенков удаляется)'
                ),
                FilterParameter(
                    name='blend', display_name='Смешивание', param_type=FilterParamType.FLOAT,
                    default_value=0.1, min_value=0.0, max_value=1.0, step=0.01,
                    description='Сглаживание краёв'
                ),
            ]
        )

        # Reverse - реверс видео
        self.filters['reverse'] = FilterProfile(
            id='reverse',
            name='Реверс видео',
            ffmpeg_name='reverse',
            category=FilterCategory.VIDEO_CREATIVE,
            description='Воспроизведение видео в обратном порядке',
            icon='⏪',
            processing_cost=4,
            parameters=[]  # Нет параметров
        )

        # Negate - негатив
        self.filters['negate'] = FilterProfile(
            id='negate',
            name='Негатив',
            ffmpeg_name='negate',
            category=FilterCategory.VIDEO_CREATIVE,
            description='Инвертирование цветов видео (негатив)',
            icon='🎞️',
            processing_cost=1,
            parameters=[
                FilterParameter(
                    name='negate_alpha', display_name='Инвертировать альфа', param_type=FilterParamType.BOOL,
                    default_value=False,
                    description='Инвертировать также альфа-канал'
                ),
            ]
        )

        # Vignette - виньетка
        self.filters['vignette'] = FilterProfile(
            id='vignette',
            name='Виньетка',
            ffmpeg_name='vignette',
            category=FilterCategory.VIDEO_CREATIVE,
            description='Затемнение краёв кадра (эффект виньетки)',
            icon='📷',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='angle', display_name='Угол', param_type=FilterParamType.FLOAT,
                    default_value=1.57, min_value=0.0, max_value=6.28, step=0.1,
                    description='Угол эллипса виньетки (радианы)', suffix='рад'
                ),
                FilterParameter(
                    name='x0', display_name='Центр X', param_type=FilterParamType.FLOAT,
                    default_value=0.5, min_value=0.0, max_value=1.0, step=0.01,
                    description='Горизонтальная позиция центра (доля ширины)'
                ),
                FilterParameter(
                    name='y0', display_name='Центр Y', param_type=FilterParamType.FLOAT,
                    default_value=0.5, min_value=0.0, max_value=1.0, step=0.01,
                    description='Вертикальная позиция центра (доля высоты)'
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
            name='Затухание',
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
            name='Громкость',
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
            name='Затухание аудио',
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

        # Dynamic Audio Normalizer - динамическая нормализация
        self.filters['dynaudnorm'] = FilterProfile(
            id='dynaudnorm',
            name='Динамическая нормализация',
            ffmpeg_name='dynaudnorm',
            category=FilterCategory.AUDIO_EFFECTS,
            description='Динамическая нормализация громкости с автоматической подстройкой усиления',
            icon='🎚️',
            processing_cost=3,
            parameters=[
                FilterParameter(
                    name='f', display_name='Размер кадра', param_type=FilterParamType.INT,
                    default_value=500, min_value=10, max_value=8000, step=10,
                    description='Размер кадра для анализа (больше=плавнее)', suffix='мс'
                ),
                FilterParameter(
                    name='g', display_name='Размер фильтра Гаусса', param_type=FilterParamType.INT,
                    default_value=31, min_value=3, max_value=301, step=2,
                    description='Размер окна сглаживания (должен быть нечетным)'
                ),
                FilterParameter(
                    name='p', display_name='Пиковое значение', param_type=FilterParamType.FLOAT,
                    default_value=0.95, min_value=0.0, max_value=1.0, step=0.05,
                    description='Целевое пиковое значение (0.0-1.0)'
                ),
                FilterParameter(
                    name='m', display_name='Макс. усиление', param_type=FilterParamType.FLOAT,
                    default_value=10.0, min_value=1.0, max_value=100.0, step=1.0,
                    description='Максимальное усиление', suffix='дБ'
                ),
                FilterParameter(
                    name='r', display_name='Целевой RMS', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=0.0, max_value=1.0, step=0.05,
                    description='Целевое RMS значение (0=автоматически)'
                ),
                FilterParameter(
                    name='c', display_name='Сжатие каналов', param_type=FilterParamType.BOOL,
                    default_value=False,
                    description='Включить coupling (одинаковое усиление для всех каналов)'
                ),
            ]
        )

        # ============= VIDEO BLUR =============

        # Boxblur - квадратное размытие
        self.filters['boxblur'] = FilterProfile(
            id='boxblur',
            name='Квадратное размытие',
            ffmpeg_name='boxblur',
            category=FilterCategory.VIDEO_BLUR,
            description='Размытие с использованием квадратного фильтра',
            icon='📦',
            processing_cost=3,
            parameters=[
                FilterParameter(
                    name='luma_radius', display_name='Радиус (яркость)', param_type=FilterParamType.INT,
                    default_value=2, min_value=0, max_value=20,
                    description='Радиус размытия для яркости'
                ),
                FilterParameter(
                    name='luma_power', display_name='Степень (яркость)', param_type=FilterParamType.INT,
                    default_value=2, min_value=0, max_value=10,
                    description='Количество проходов для яркости'
                ),
            ]
        )

        # Gblur - Gaussian blur
        self.filters['gblur'] = FilterProfile(
            id='gblur',
            name='Гауссово размытие',
            ffmpeg_name='gblur',
            category=FilterCategory.VIDEO_BLUR,
            description='Гауссово размытие (более качественное)',
            icon='🌫️',
            processing_cost=4,
            parameters=[
                FilterParameter(
                    name='sigma', display_name='Сигма', param_type=FilterParamType.FLOAT,
                    default_value=2.0, min_value=0.01, max_value=1024.0, step=0.1,
                    description='Стандартное отклонение Гаусса (сила размытия)'
                ),
            ]
        )

        # Avgblur - среднее размытие
        self.filters['avgblur'] = FilterProfile(
            id='avgblur',
            name='Среднее размытие',
            ffmpeg_name='avgblur',
            category=FilterCategory.VIDEO_BLUR,
            description='Размытие методом усреднения (быстрое)',
            icon='🔹',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='sizeX', display_name='Размер X', param_type=FilterParamType.INT,
                    default_value=5, min_value=1, max_value=1024,
                    description='Размер окна по горизонтали'
                ),
                FilterParameter(
                    name='sizeY', display_name='Размер Y', param_type=FilterParamType.INT,
                    default_value=5, min_value=1, max_value=1024,
                    description='Размер окна по вертикали'
                ),
            ]
        )

        # Median - медианный фильтр
        self.filters['median'] = FilterProfile(
            id='median',
            name='Медианный фильтр',
            ffmpeg_name='median',
            category=FilterCategory.VIDEO_BLUR,
            description='Медианный фильтр для удаления шума (сохраняет края)',
            icon='🎯',
            processing_cost=4,
            parameters=[
                FilterParameter(
                    name='radius', display_name='Радиус', param_type=FilterParamType.INT,
                    default_value=1, min_value=1, max_value=127,
                    description='Радиус медианного фильтра'
                ),
            ]
        )

        # Bilateral - двусторонний фильтр
        self.filters['bilateral'] = FilterProfile(
            id='bilateral',
            name='Двусторонний фильтр',
            ffmpeg_name='bilateral',
            category=FilterCategory.VIDEO_BLUR,
            description='Размытие с сохранением краев (размытие с сохранением краев)',
            icon='🎨',
            processing_cost=5,
            parameters=[
                FilterParameter(
                    name='sigmaS', display_name='Пространственная сигма', param_type=FilterParamType.FLOAT,
                    default_value=0.1, min_value=0.0, max_value=512.0, step=0.1,
                    description='Пространственная сигма (радиус)'
                ),
                FilterParameter(
                    name='sigmaR', display_name='Цветовая сигма', param_type=FilterParamType.FLOAT,
                    default_value=0.1, min_value=0.0, max_value=1.0, step=0.01,
                    description='Цветовая сигма (сохранение краев)'
                ),
            ]
        )

        # Smartblur - умное размытие
        self.filters['smartblur'] = FilterProfile(
            id='smartblur',
            name='Умное размытие',
            ffmpeg_name='smartblur',
            category=FilterCategory.VIDEO_BLUR,
            description='Умное размытие с адаптацией к краям',
            icon='🧠',
            processing_cost=4,
            parameters=[
                FilterParameter(
                    name='luma_radius', display_name='Радиус', param_type=FilterParamType.FLOAT,
                    default_value=1.0, min_value=0.1, max_value=5.0, step=0.1,
                    description='Радиус размытия'
                ),
                FilterParameter(
                    name='luma_strength', display_name='Сила', param_type=FilterParamType.FLOAT,
                    default_value=1.0, min_value=0.1, max_value=5.0, step=0.1,
                    description='Сила размытия'
                ),
                FilterParameter(
                    name='luma_threshold', display_name='Порог', param_type=FilterParamType.INT,
                    default_value=0, min_value=-30, max_value=30,
                    description='Порог определения краев'
                ),
            ]
        )

        # ============= VIDEO COLOR =============

        # Colorbalance - баланс цвета
        self.filters['colorbalance'] = FilterProfile(
            id='colorbalance',
            name='Цветовой баланс',
            ffmpeg_name='colorbalance',
            category=FilterCategory.VIDEO_COLOR,
            description='Регулировка цветового баланса (тени/средние тона/света)',
            icon='🎨',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='rs', display_name='Тени: Красный-Циан', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-1.0, max_value=1.0, step=0.01,
                    description='Красный-Циан для теней (-1=циан, +1=красный)'
                ),
                FilterParameter(
                    name='gs', display_name='Тени: Зеленый-Магента', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-1.0, max_value=1.0, step=0.01,
                    description='Зеленый-Магента для теней'
                ),
                FilterParameter(
                    name='bs', display_name='Тени: Синий-Желтый', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-1.0, max_value=1.0, step=0.01,
                    description='Синий-Желтый для теней'
                ),
                FilterParameter(
                    name='rm', display_name='Средние: Красный-Циан', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-1.0, max_value=1.0, step=0.01,
                    description='Красный-Циан для средних тонов'
                ),
                FilterParameter(
                    name='gm', display_name='Средние: Зеленый-Магента', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-1.0, max_value=1.0, step=0.01,
                    description='Зеленый-Магента для средних тонов'
                ),
                FilterParameter(
                    name='bm', display_name='Средние: Синий-Желтый', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-1.0, max_value=1.0, step=0.01,
                    description='Синий-Желтый для средних тонов'
                ),
                FilterParameter(
                    name='rh', display_name='Света: Красный-Циан', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-1.0, max_value=1.0, step=0.01,
                    description='Красный-Циан для светов'
                ),
                FilterParameter(
                    name='gh', display_name='Света: Зеленый-Магента', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-1.0, max_value=1.0, step=0.01,
                    description='Зеленый-Магента для светов'
                ),
                FilterParameter(
                    name='bh', display_name='Света: Синий-Желтый', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-1.0, max_value=1.0, step=0.01,
                    description='Синий-Желтый для светов'
                ),
            ]
        )

        # Curves - тональные кривые
        self.filters['curves'] = FilterProfile(
            id='curves',
            name='Тональные кривые',
            ffmpeg_name='curves',
            category=FilterCategory.VIDEO_COLOR,
            description='Корректировка тональных кривых',
            icon='📈',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='preset', display_name='Пресет', param_type=FilterParamType.CHOICE,
                    default_value='none',
                    choices=[
                        ('none', 'Без изменений'),
                        ('color_negative', 'Цветной негатив'),
                        ('cross_process', 'Кросс-процесс'),
                        ('darker', 'Темнее'),
                        ('increase_contrast', 'Увеличить контраст'),
                        ('lighter', 'Светлее'),
                        ('linear_contrast', 'Линейный контраст'),
                        ('medium_contrast', 'Средний контраст'),
                        ('negative', 'Негатив'),
                        ('strong_contrast', 'Сильный контраст'),
                        ('vintage', 'Винтаж'),
                    ],
                    description='Предустановленная кривая'
                ),
            ]
        )

        # Colortemperature - цветовая температура
        self.filters['colortemperature'] = FilterProfile(
            id='colortemperature',
            name='Цветовая температура',
            ffmpeg_name='colortemperature',
            category=FilterCategory.VIDEO_COLOR,
            description='Регулировка цветовой температуры (теплый/холодный)',
            icon='🌡️',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='temperature', display_name='Температура', param_type=FilterParamType.INT,
                    default_value=6500, min_value=1000, max_value=40000, step=100,
                    description='Цветовая температура в Кельвинах', suffix='K'
                ),
                FilterParameter(
                    name='mix', display_name='Смешивание', param_type=FilterParamType.FLOAT,
                    default_value=1.0, min_value=0.0, max_value=1.0, step=0.01,
                    description='Сила эффекта (0=нет, 1=полностью)'
                ),
            ]
        )

        # Colorlevels - уровни цвета
        self.filters['colorlevels'] = FilterProfile(
            id='colorlevels',
            name='Уровни цвета',
            ffmpeg_name='colorlevels',
            category=FilterCategory.VIDEO_COLOR,
            description='Регулировка входных и выходных уровней по каналам',
            icon='📊',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='rimin', display_name='Красный: вход min', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=0.0, max_value=1.0, step=0.01,
                    description='Минимальный входной уровень для красного канала'
                ),
                FilterParameter(
                    name='rimax', display_name='Красный: вход max', param_type=FilterParamType.FLOAT,
                    default_value=1.0, min_value=0.0, max_value=1.0, step=0.01,
                    description='Максимальный входной уровень для красного канала'
                ),
                FilterParameter(
                    name='romin', display_name='Красный: выход min', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=0.0, max_value=1.0, step=0.01,
                    description='Минимальный выходной уровень для красного канала'
                ),
                FilterParameter(
                    name='romax', display_name='Красный: выход max', param_type=FilterParamType.FLOAT,
                    default_value=1.0, min_value=0.0, max_value=1.0, step=0.01,
                    description='Максимальный выходной уровень для красного канала'
                ),
            ]
        )

        # Monochrome - монохром
        self.filters['monochrome'] = FilterProfile(
            id='monochrome',
            name='Монохром',
            ffmpeg_name='monochrome',
            category=FilterCategory.VIDEO_COLOR,
            description='Конвертация в монохромное изображение с оттенком',
            icon='⚫',
            processing_cost=1,
            parameters=[
                FilterParameter(
                    name='cb', display_name='Chroma Blue', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-1.0, max_value=1.0, step=0.01,
                    description='Синий оттенок'
                ),
                FilterParameter(
                    name='cr', display_name='Chroma Red', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-1.0, max_value=1.0, step=0.01,
                    description='Красный оттенок'
                ),
            ]
        )

        # Pseudocolor - ложные цвета
        self.filters['pseudocolor'] = FilterProfile(
            id='pseudocolor',
            name='Ложные цвета',
            ffmpeg_name='pseudocolor',
            category=FilterCategory.VIDEO_COLOR,
            description='Назначение цветов диапазонам яркости',
            icon='🌈',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='preset', display_name='Пресет', param_type=FilterParamType.CHOICE,
                    default_value='heat',
                    choices=[
                        ('heat', 'Тепловая карта'),
                        ('cool', 'Холодная'),
                        ('fire', 'Огонь'),
                        ('magma', 'Магма'),
                        ('rainbow', 'Радуга'),
                        ('viridis', 'Viridis'),
                    ],
                    description='Цветовая схема'
                ),
            ]
        )

        # Colorize - колоризация
        self.filters['colorize'] = FilterProfile(
            id='colorize',
            name='Колоризация',
            ffmpeg_name='colorize',
            category=FilterCategory.VIDEO_COLOR,
            description='Добавление цвета к черно-белому изображению',
            icon='🎨',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='hue', display_name='Оттенок', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=0.0, max_value=360.0, step=1.0,
                    description='Оттенок цвета (0-360°)', suffix='°'
                ),
                FilterParameter(
                    name='saturation', display_name='Насыщенность', param_type=FilterParamType.FLOAT,
                    default_value=0.5, min_value=0.0, max_value=1.0, step=0.01,
                    description='Насыщенность цвета'
                ),
                FilterParameter(
                    name='lightness', display_name='Яркость', param_type=FilterParamType.FLOAT,
                    default_value=0.5, min_value=0.0, max_value=1.0, step=0.01,
                    description='Яркость'
                ),
            ]
        )

        # ============= VIDEO DEINTERLACE =============

        # Bwdif - деинтерлейсинг
        self.filters['bwdif'] = FilterProfile(
            id='bwdif',
            name='Деинтерлейсинг Bwdif',
            ffmpeg_name='bwdif',
            category=FilterCategory.VIDEO_DEINTERLACE,
            description='Адаптивный к движению деинтерлейсинг (лучше чем yadif)',
            icon='🎬',
            processing_cost=3,
            parameters=[
                FilterParameter(
                    name='mode', display_name='Режим', param_type=FilterParamType.CHOICE,
                    default_value='send_frame',
                    choices=[
                        ('send_frame', 'Один кадр на поле'),
                        ('send_field', 'Один кадр на frame'),
                    ],
                    description='Режим вывода'
                ),
                FilterParameter(
                    name='parity', display_name='Чередование', param_type=FilterParamType.CHOICE,
                    default_value='auto',
                    choices=[
                        ('auto', 'Автоматически'),
                        ('tff', 'Top field first'),
                        ('bff', 'Bottom field first'),
                    ],
                    description='Порядок полей'
                ),
            ]
        )

        # Kerndeint - kernel deinterlace
        self.filters['kerndeint'] = FilterProfile(
            id='kerndeint',
            name='Деинтерлейсинг Kernel',
            ffmpeg_name='kerndeint',
            category=FilterCategory.VIDEO_DEINTERLACE,
            description='Основанный на ядре деинтерлейсинг',
            icon='🎞️',
            processing_cost=3,
            parameters=[
                FilterParameter(
                    name='thresh', display_name='Порог', param_type=FilterParamType.INT,
                    default_value=10, min_value=0, max_value=255,
                    description='Порог определения интерлейсинга'
                ),
                FilterParameter(
                    name='sharp', display_name='Резкость', param_type=FilterParamType.BOOL,
                    default_value=False,
                    description='Включить повышение резкости'
                ),
            ]
        )

        # ============= VIDEO ANALYSIS =============

        # Blackdetect - детекция черных кадров
        self.filters['blackdetect'] = FilterProfile(
            id='blackdetect',
            name='Детектор черных кадров',
            ffmpeg_name='blackdetect',
            category=FilterCategory.VIDEO_ANALYSIS,
            description='Обнаружение черных кадров и сегментов',
            icon='⬛',
            processing_cost=1,
            parameters=[
                FilterParameter(
                    name='d', display_name='Длительность', param_type=FilterParamType.FLOAT,
                    default_value=2.0, min_value=0.0, max_value=60.0, step=0.1,
                    description='Минимальная длительность черного сегмента', suffix='сек'
                ),
                FilterParameter(
                    name='pix_th', display_name='Порог пикселя', param_type=FilterParamType.FLOAT,
                    default_value=0.1, min_value=0.0, max_value=1.0, step=0.01,
                    description='Порог яркости пикселя (0-1)'
                ),
            ]
        )

        # Cropdetect - авто-детекция crop
        self.filters['cropdetect'] = FilterProfile(
            id='cropdetect',
            name='Детектор обрезки',
            ffmpeg_name='cropdetect',
            category=FilterCategory.VIDEO_ANALYSIS,
            description='Автоматическое определение области обрезки (черные края)',
            icon='🔍',
            processing_cost=1,
            parameters=[
                FilterParameter(
                    name='limit', display_name='Порог', param_type=FilterParamType.INT,
                    default_value=24, min_value=0, max_value=255,
                    description='Порог яркости для определения черных областей'
                ),
                FilterParameter(
                    name='round', display_name='Округление', param_type=FilterParamType.INT,
                    default_value=2, min_value=0, max_value=256, step=2,
                    description='Округление размеров (должно быть четным)'
                ),
            ]
        )

        # Histogram - гистограмма
        self.filters['histogram'] = FilterProfile(
            id='histogram',
            name='Гистограмма',
            ffmpeg_name='histogram',
            category=FilterCategory.VIDEO_ANALYSIS,
            description='Отображение гистограммы яркости и цвета',
            icon='📊',
            processing_cost=3,
            parameters=[
                FilterParameter(
                    name='mode', display_name='Режим', param_type=FilterParamType.CHOICE,
                    default_value='levels',
                    choices=[
                        ('levels', 'Уровни яркости'),
                        ('color', 'Цветовые компоненты'),
                        ('color2', 'Цвет (альтернативный)'),
                    ],
                    description='Тип гистограммы'
                ),
            ]
        )

        # Vectorscope - векторскоп
        self.filters['vectorscope'] = FilterProfile(
            id='vectorscope',
            name='Векторскоп',
            ffmpeg_name='vectorscope',
            category=FilterCategory.VIDEO_ANALYSIS,
            description='Векторскоп для анализа цвета и насыщенности',
            icon='🎯',
            processing_cost=3,
            parameters=[
                FilterParameter(
                    name='mode', display_name='Режим', param_type=FilterParamType.CHOICE,
                    default_value='color',
                    choices=[
                        ('gray', 'Серый'),
                        ('color', 'Цветной'),
                        ('color2', 'Цвет 2'),
                        ('color3', 'Цвет 3'),
                        ('color4', 'Цвет 4'),
                    ],
                    description='Режим отображения'
                ),
            ]
        )

        # Waveform - осциллограмма
        self.filters['waveform'] = FilterProfile(
            id='waveform',
            name='Осциллограмма',
            ffmpeg_name='waveform',
            category=FilterCategory.VIDEO_ANALYSIS,
            description='Волновой монитор для анализа яркости',
            icon='📉',
            processing_cost=3,
            parameters=[
                FilterParameter(
                    name='mode', display_name='Режим', param_type=FilterParamType.CHOICE,
                    default_value='column',
                    choices=[
                        ('row', 'Горизонтальный'),
                        ('column', 'Вертикальный'),
                    ],
                    description='Ориентация осциллограммы'
                ),
            ]
        )

        # ============= AUDIO DYNAMICS =============

        # Acompressor - аудио компрессор
        self.filters['acompressor'] = FilterProfile(
            id='acompressor',
            name='Аудио компрессор',
            ffmpeg_name='acompressor',
            category=FilterCategory.AUDIO_DYNAMICS,
            description='Динамический компрессор для сжатия динамического диапазона',
            icon='🔧',
            processing_cost=3,
            parameters=[
                FilterParameter(
                    name='threshold', display_name='Порог', param_type=FilterParamType.FLOAT,
                    default_value=-18.0, min_value=-100.0, max_value=0.0, step=1.0,
                    description='Порог срабатывания компрессии', suffix='dB'
                ),
                FilterParameter(
                    name='ratio', display_name='Отношение', param_type=FilterParamType.FLOAT,
                    default_value=2.0, min_value=1.0, max_value=20.0, step=0.1,
                    description='Степень компрессии (2:1, 4:1, и т.д.)'
                ),
                FilterParameter(
                    name='attack', display_name='Атака', param_type=FilterParamType.FLOAT,
                    default_value=20.0, min_value=0.01, max_value=2000.0, step=1.0,
                    description='Время атаки', suffix='мс'
                ),
                FilterParameter(
                    name='release', display_name='Восстановление', param_type=FilterParamType.FLOAT,
                    default_value=250.0, min_value=0.01, max_value=9000.0, step=1.0,
                    description='Время восстановления', suffix='мс'
                ),
                FilterParameter(
                    name='makeup', display_name='Усиление', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=0.0, max_value=64.0, step=0.5,
                    description='Компенсирующее усиление', suffix='dB'
                ),
            ]
        )

        # Alimiter - лимитер
        self.filters['alimiter'] = FilterProfile(
            id='alimiter',
            name='Аудио лимитер',
            ffmpeg_name='alimiter',
            category=FilterCategory.AUDIO_DYNAMICS,
            description='Лимитер для предотвращения клиппинга',
            icon='🚫',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='limit', display_name='Предел', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-99.0, max_value=0.0, step=0.1,
                    description='Максимальный уровень', suffix='dB'
                ),
                FilterParameter(
                    name='attack', display_name='Атака', param_type=FilterParamType.FLOAT,
                    default_value=5.0, min_value=0.1, max_value=80.0, step=0.1,
                    description='Время атаки', suffix='мс'
                ),
                FilterParameter(
                    name='release', display_name='Восстановление', param_type=FilterParamType.FLOAT,
                    default_value=50.0, min_value=1.0, max_value=8000.0, step=1.0,
                    description='Время восстановления', suffix='мс'
                ),
            ]
        )

        # Agate - noise gate
        self.filters['agate'] = FilterProfile(
            id='agate',
            name='Шумоподавитель',
            ffmpeg_name='agate',
            category=FilterCategory.AUDIO_DYNAMICS,
            description='Шумовые ворота для подавления фонового шума',
            icon='🚪',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='threshold', display_name='Порог', param_type=FilterParamType.FLOAT,
                    default_value=-40.0, min_value=-90.0, max_value=0.0, step=1.0,
                    description='Порог открытия гейта', suffix='dB'
                ),
                FilterParameter(
                    name='ratio', display_name='Отношение', param_type=FilterParamType.FLOAT,
                    default_value=2.0, min_value=1.0, max_value=9000.0, step=0.1,
                    description='Степень подавления'
                ),
                FilterParameter(
                    name='attack', display_name='Атака', param_type=FilterParamType.FLOAT,
                    default_value=20.0, min_value=0.01, max_value=9000.0, step=1.0,
                    description='Время открытия', suffix='мс'
                ),
                FilterParameter(
                    name='release', display_name='Восстановление', param_type=FilterParamType.FLOAT,
                    default_value=250.0, min_value=0.01, max_value=9000.0, step=1.0,
                    description='Время закрытия', suffix='мс'
                ),
            ]
        )

        # ============= AUDIO EQ =============

        # Anequalizer - параметрический EQ
        self.filters['anequalizer'] = FilterProfile(
            id='anequalizer',
            name='Параметрический эквалайзер',
            ffmpeg_name='anequalizer',
            category=FilterCategory.AUDIO_EQ,
            description='Многополосный параметрический эквалайзер',
            icon='🎚️',
            processing_cost=3,
            parameters=[
                FilterParameter(
                    name='curves', display_name='Настройки', param_type=FilterParamType.STRING,
                    default_value='',
                    description='Настройки эквалайзера (формат: f=100 w=200 g=-10|f=500...)'
                ),
            ]
        )

        # Bass - усиление басов
        self.filters['bass'] = FilterProfile(
            id='bass',
            name='Усиление басов',
            ffmpeg_name='bass',
            category=FilterCategory.AUDIO_EQ,
            description='Усиление или ослабление низких частот',
            icon='🔈',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='gain', display_name='Усиление', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-20.0, max_value=20.0, step=0.5,
                    description='Усиление басов', suffix='dB'
                ),
                FilterParameter(
                    name='frequency', display_name='Частота', param_type=FilterParamType.INT,
                    default_value=100, min_value=0, max_value=999,
                    description='Центральная частота', suffix='Hz'
                ),
                FilterParameter(
                    name='width_type', display_name='Тип ширины', param_type=FilterParamType.CHOICE,
                    default_value='q',
                    choices=[
                        ('h', 'Hz'),
                        ('q', 'Q-фактор'),
                        ('o', 'Октавы'),
                        ('s', 'Наклон'),
                    ],
                    description='Тип параметра ширины полосы'
                ),
            ]
        )

        # Treble - усиление высоких
        self.filters['treble'] = FilterProfile(
            id='treble',
            name='Усиление высоких',
            ffmpeg_name='treble',
            category=FilterCategory.AUDIO_EQ,
            description='Усиление или ослабление высоких частот',
            icon='🔊',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='gain', display_name='Усиление', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-20.0, max_value=20.0, step=0.5,
                    description='Усиление высоких', suffix='dB'
                ),
                FilterParameter(
                    name='frequency', display_name='Частота', param_type=FilterParamType.INT,
                    default_value=3000, min_value=0, max_value=999999,
                    description='Центральная частота', suffix='Hz'
                ),
            ]
        )

        # Equalizer - однополосный EQ
        self.filters['equalizer'] = FilterProfile(
            id='equalizer',
            name='Эквалайзер',
            ffmpeg_name='equalizer',
            category=FilterCategory.AUDIO_EQ,
            description='Однополосный параметрический эквалайзер',
            icon='📊',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='frequency', display_name='Частота', param_type=FilterParamType.INT,
                    default_value=1000, min_value=0, max_value=999999, step=10,
                    description='Центральная частота', suffix='Hz'
                ),
                FilterParameter(
                    name='width', display_name='Ширина полосы', param_type=FilterParamType.INT,
                    default_value=100, min_value=1, max_value=99999, step=10,
                    description='Ширина полосы', suffix='Hz'
                ),
                FilterParameter(
                    name='gain', display_name='Усиление', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-20.0, max_value=20.0, step=0.5,
                    description='Усиление/Ослабление', suffix='dB'
                ),
            ]
        )

        # ============= AUDIO SPATIAL =============

        # Stereotools - стерео обработка
        self.filters['stereotools'] = FilterProfile(
            id='stereotools',
            name='Стерео инструменты',
            ffmpeg_name='stereotools',
            category=FilterCategory.AUDIO_SPATIAL,
            description='Инструменты для обработки стерео поля',
            icon='🎧',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='mlev', display_name='Уровень Mid', param_type=FilterParamType.FLOAT,
                    default_value=1.0, min_value=0.0, max_value=10.0, step=0.1,
                    description='Уровень mid (центр)'
                ),
                FilterParameter(
                    name='slev', display_name='Уровень Side', param_type=FilterParamType.FLOAT,
                    default_value=1.0, min_value=0.0, max_value=10.0, step=0.1,
                    description='Уровень side (стороны)'
                ),
            ]
        )

        # Stereowiden - расширение стерео
        self.filters['stereowiden'] = FilterProfile(
            id='stereowiden',
            name='Расширение стерео',
            ffmpeg_name='stereowiden',
            category=FilterCategory.AUDIO_SPATIAL,
            description='Расширение стерео базы',
            icon='↔️',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='delay', display_name='Задержка', param_type=FilterParamType.FLOAT,
                    default_value=20.0, min_value=1.0, max_value=100.0, step=1.0,
                    description='Задержка для расширения', suffix='мс'
                ),
                FilterParameter(
                    name='feedback', display_name='Обратная связь', param_type=FilterParamType.FLOAT,
                    default_value=0.3, min_value=0.0, max_value=0.9, step=0.05,
                    description='Уровень обратной связи'
                ),
            ]
        )

        # Extrastereo - расширенное стерео
        self.filters['extrastereo'] = FilterProfile(
            id='extrastereo',
            name='Экстра стерео',
            ffmpeg_name='extrastereo',
            category=FilterCategory.AUDIO_SPATIAL,
            description='Усиление стерео эффекта (разность каналов)',
            icon='🎵',
            processing_cost=1,
            parameters=[
                FilterParameter(
                    name='m', display_name='Множитель', param_type=FilterParamType.FLOAT,
                    default_value=2.5, min_value=0.0, max_value=10.0, step=0.1,
                    description='Множитель стерео эффекта'
                ),
            ]
        )

        # ============= AUDIO DENOISE =============

        # Afftdn - FFT denoising
        self.filters['afftdn'] = FilterProfile(
            id='afftdn',
            name='FFT шумоподавитель',
            ffmpeg_name='afftdn',
            category=FilterCategory.AUDIO_DENOISE,
            description='FFT-based шумоподавление',
            icon='🔇',
            processing_cost=4,
            parameters=[
                FilterParameter(
                    name='nr', display_name='Подавление шума', param_type=FilterParamType.FLOAT,
                    default_value=12.0, min_value=0.01, max_value=97.0, step=1.0,
                    description='Степень подавления шума', suffix='dB'
                ),
                FilterParameter(
                    name='nf', display_name='Шумовой порог', param_type=FilterParamType.FLOAT,
                    default_value=-50.0, min_value=-80.0, max_value=-20.0, step=1.0,
                    description='Порог шума', suffix='dB'
                ),
            ]
        )

        # Adeclick - удаление кликов
        self.filters['adeclick'] = FilterProfile(
            id='adeclick',
            name='Удаление щелчков',
            ffmpeg_name='adeclick',
            category=FilterCategory.AUDIO_DENOISE,
            description='Удаление кликов и щелчков из аудио',
            icon='🔨',
            processing_cost=3,
            parameters=[
                FilterParameter(
                    name='w', display_name='Размер окна', param_type=FilterParamType.FLOAT,
                    default_value=55.0, min_value=10.0, max_value=100.0, step=5.0,
                    description='Размер окна анализа', suffix='мс'
                ),
                FilterParameter(
                    name='t', display_name='Порог', param_type=FilterParamType.FLOAT,
                    default_value=2.0, min_value=1.0, max_value=100.0, step=1.0,
                    description='Порог определения клика'
                ),
            ]
        )

        # Adeclip - удаление клиппинга
        self.filters['adeclip'] = FilterProfile(
            id='adeclip',
            name='Удаление клиппинга',
            ffmpeg_name='adeclip',
            category=FilterCategory.AUDIO_DENOISE,
            description='Восстановление клипированного аудио',
            icon='📍',
            processing_cost=4,
            parameters=[
                FilterParameter(
                    name='threshold', display_name='Порог', param_type=FilterParamType.FLOAT,
                    default_value=0.9, min_value=0.0, max_value=1.0, step=0.01,
                    description='Порог определения клиппинга'
                ),
            ]
        )

        # ============= AUDIO EFFECTS =============

        # Aecho - эхо
        self.filters['aecho'] = FilterProfile(
            id='aecho',
            name='Эхо',
            ffmpeg_name='aecho',
            category=FilterCategory.AUDIO_EFFECTS,
            description='Добавление эхо эффекта',
            icon='📢',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='in_gain', display_name='Вход', param_type=FilterParamType.FLOAT,
                    default_value=0.6, min_value=0.0, max_value=1.0, step=0.05,
                    description='Уровень входного сигнала'
                ),
                FilterParameter(
                    name='out_gain', display_name='Выход', param_type=FilterParamType.FLOAT,
                    default_value=0.3, min_value=0.0, max_value=1.0, step=0.05,
                    description='Уровень выходного сигнала'
                ),
                FilterParameter(
                    name='delays', display_name='Задержки', param_type=FilterParamType.STRING,
                    default_value='1000',
                    description='Задержки эхо в мс (разделенные |), например: 1000|1800'
                ),
                FilterParameter(
                    name='decays', display_name='Затухание', param_type=FilterParamType.STRING,
                    default_value='0.5',
                    description='Коэффициенты затухания (0-1), например: 0.5|0.3'
                ),
            ]
        )

        # Chorus - хорус
        self.filters['chorus'] = FilterProfile(
            id='chorus',
            name='Хорус',
            ffmpeg_name='chorus',
            category=FilterCategory.AUDIO_EFFECTS,
            description='Хорус эффект',
            icon='🎼',
            processing_cost=3,
            parameters=[
                FilterParameter(
                    name='in_gain', display_name='Вход', param_type=FilterParamType.FLOAT,
                    default_value=0.4, min_value=0.0, max_value=1.0, step=0.05,
                    description='Уровень входного сигнала'
                ),
                FilterParameter(
                    name='out_gain', display_name='Выход', param_type=FilterParamType.FLOAT,
                    default_value=0.4, min_value=0.0, max_value=1.0, step=0.05,
                    description='Уровень выходного сигнала'
                ),
                FilterParameter(
                    name='delays', display_name='Задержки', param_type=FilterParamType.STRING,
                    default_value='40|60|80',
                    description='Задержки в мс, разделенные |'
                ),
                FilterParameter(
                    name='decays', display_name='Затухание', param_type=FilterParamType.STRING,
                    default_value='0.4|0.32|0.25',
                    description='Коэффициенты затухания'
                ),
                FilterParameter(
                    name='speeds', display_name='Скорости', param_type=FilterParamType.STRING,
                    default_value='0.25|0.33|0.42',
                    description='Скорости модуляции'
                ),
                FilterParameter(
                    name='depths', display_name='Глубина', param_type=FilterParamType.STRING,
                    default_value='2|2.3|1.3',
                    description='Глубина модуляции'
                ),
            ]
        )

        # Aphaser - фазер
        self.filters['aphaser'] = FilterProfile(
            id='aphaser',
            name='Фейзер',
            ffmpeg_name='aphaser',
            category=FilterCategory.AUDIO_EFFECTS,
            description='Фейзер эффект',
            icon='🌀',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='in_gain', display_name='Вход', param_type=FilterParamType.FLOAT,
                    default_value=0.4, min_value=0.0, max_value=1.0, step=0.05,
                    description='Уровень входного сигнала'
                ),
                FilterParameter(
                    name='out_gain', display_name='Выход', param_type=FilterParamType.FLOAT,
                    default_value=0.74, min_value=0.0, max_value=1.0, step=0.05,
                    description='Уровень выходного сигнала'
                ),
                FilterParameter(
                    name='delay', display_name='Задержка', param_type=FilterParamType.FLOAT,
                    default_value=3.0, min_value=0.0, max_value=5.0, step=0.1,
                    description='Базовая задержка', suffix='мс'
                ),
                FilterParameter(
                    name='decay', display_name='Затухание', param_type=FilterParamType.FLOAT,
                    default_value=0.4, min_value=0.0, max_value=0.99, step=0.05,
                    description='Коэффициент затухания'
                ),
                FilterParameter(
                    name='speed', display_name='Скорость', param_type=FilterParamType.FLOAT,
                    default_value=0.5, min_value=0.1, max_value=2.0, step=0.05,
                    description='Скорость модуляции', suffix='Hz'
                ),
            ]
        )

        # Aflanger - флэнжер
        self.filters['aflanger'] = FilterProfile(
            id='aflanger',
            name='Фленжер',
            ffmpeg_name='aflanger',
            category=FilterCategory.AUDIO_EFFECTS,
            description='Фленжер эффект',
            icon='〰️',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='delay', display_name='Задержка', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=0.0, max_value=30.0, step=0.5,
                    description='Базовая задержка', suffix='мс'
                ),
                FilterParameter(
                    name='depth', display_name='Глубина', param_type=FilterParamType.FLOAT,
                    default_value=2.0, min_value=0.0, max_value=10.0, step=0.5,
                    description='Глубина модуляции', suffix='мс'
                ),
                FilterParameter(
                    name='speed', display_name='Скорость', param_type=FilterParamType.FLOAT,
                    default_value=0.5, min_value=0.1, max_value=10.0, step=0.1,
                    description='Скорость модуляции', suffix='Hz'
                ),
            ]
        )

        # Tremolo - тремоло
        self.filters['tremolo'] = FilterProfile(
            id='tremolo',
            name='Тремоло',
            ffmpeg_name='tremolo',
            category=FilterCategory.AUDIO_EFFECTS,
            description='Амплитудная модуляция (тремоло)',
            icon='🔉',
            processing_cost=1,
            parameters=[
                FilterParameter(
                    name='f', display_name='Частота', param_type=FilterParamType.FLOAT,
                    default_value=5.0, min_value=0.1, max_value=20000.0, step=0.1,
                    description='Частота модуляции', suffix='Hz'
                ),
                FilterParameter(
                    name='d', display_name='Глубина', param_type=FilterParamType.FLOAT,
                    default_value=0.5, min_value=0.0, max_value=1.0, step=0.05,
                    description='Глубина модуляции амплитуды'
                ),
            ]
        )

        # Vibrato - вибрато
        self.filters['vibrato'] = FilterProfile(
            id='vibrato',
            name='Вибрато',
            ffmpeg_name='vibrato',
            category=FilterCategory.AUDIO_EFFECTS,
            description='Частотная модуляция (вибрато)',
            icon='🎶',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='f', display_name='Частота', param_type=FilterParamType.FLOAT,
                    default_value=5.0, min_value=0.1, max_value=20000.0, step=0.1,
                    description='Частота модуляции', suffix='Hz'
                ),
                FilterParameter(
                    name='d', display_name='Глубина', param_type=FilterParamType.FLOAT,
                    default_value=0.5, min_value=0.0, max_value=1.0, step=0.05,
                    description='Глубина модуляции частоты'
                ),
            ]
        )

        # Atempo - изменение темпа
        self.filters['atempo'] = FilterProfile(
            id='atempo',
            name='Изменение темпа',
            ffmpeg_name='atempo',
            category=FilterCategory.AUDIO_EFFECTS,
            description='Изменение темпа без изменения pitch',
            icon='⏩',
            processing_cost=3,
            parameters=[
                FilterParameter(
                    name='tempo', display_name='Темп', param_type=FilterParamType.FLOAT,
                    default_value=1.0, min_value=0.5, max_value=2.0, step=0.05,
                    description='Множитель темпа (0.5=50%, 2.0=200%)'
                ),
            ]
        )

        # Bandpass - полосовой фильтр
        self.filters['bandpass'] = FilterProfile(
            id='bandpass',
            name='Полосовой фильтр',
            ffmpeg_name='bandpass',
            category=FilterCategory.AUDIO_FILTER,
            description='Пропускает частоты в заданном диапазоне',
            icon='📊',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='frequency', display_name='Центральная частота', param_type=FilterParamType.INT,
                    default_value=1000, min_value=10, max_value=20000, step=10,
                    description='Центральная частота полосы', suffix='Hz'
                ),
                FilterParameter(
                    name='width', display_name='Ширина полосы', param_type=FilterParamType.INT,
                    default_value=100, min_value=10, max_value=10000, step=10,
                    description='Ширина полосы пропускания', suffix='Hz'
                ),
            ]
        )

        # Bandreject - режекторный фильтр
        self.filters['bandreject'] = FilterProfile(
            id='bandreject',
            name='Режекторный фильтр',
            ffmpeg_name='bandreject',
            category=FilterCategory.AUDIO_FILTER,
            description='Подавляет частоты в заданном диапазоне',
            icon='🚫',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='frequency', display_name='Центральная частота', param_type=FilterParamType.INT,
                    default_value=1000, min_value=10, max_value=20000, step=10,
                    description='Центральная частота режекции', suffix='Hz'
                ),
                FilterParameter(
                    name='width', display_name='Ширина полосы', param_type=FilterParamType.INT,
                    default_value=100, min_value=10, max_value=10000, step=10,
                    description='Ширина полосы режекции', suffix='Hz'
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

        # ============= VIDEO TRANSFORM (ADVANCED) =============

        # Perspective - перспективная трансформация
        self.filters['perspective'] = FilterProfile(
            id='perspective',
            name='Перспективная трансформация',
            ffmpeg_name='perspective',
            category=FilterCategory.VIDEO_TRANSFORM,
            description='Коррекция перспективы (исправление угла съемки)',
            icon='🔷',
            processing_cost=3,
            parameters=[
                FilterParameter(
                    name='x0', display_name='Левый верх X', param_type=FilterParamType.STRING,
                    default_value='0',
                    description='X координата левого верхнего угла (или выражение)'
                ),
                FilterParameter(
                    name='y0', display_name='Левый верх Y', param_type=FilterParamType.STRING,
                    default_value='0',
                    description='Y координата левого верхнего угла'
                ),
                FilterParameter(
                    name='x1', display_name='Правый верх X', param_type=FilterParamType.STRING,
                    default_value='W',
                    description='X координата правого верхнего угла (W=ширина)'
                ),
                FilterParameter(
                    name='y1', display_name='Правый верх Y', param_type=FilterParamType.STRING,
                    default_value='0',
                    description='Y координата правого верхнего угла'
                ),
            ]
        )

        # Pad - добавление отступов
        self.filters['pad'] = FilterProfile(
            id='pad',
            name='Отступы',
            ffmpeg_name='pad',
            category=FilterCategory.VIDEO_TRANSFORM,
            description='Добавление рамки/отступов вокруг видео',
            icon='🖼️',
            processing_cost=1,
            parameters=[
                FilterParameter(
                    name='width', display_name='Ширина', param_type=FilterParamType.STRING,
                    default_value='iw',
                    description='Итоговая ширина (iw=input width, можно iw+100)'
                ),
                FilterParameter(
                    name='height', display_name='Высота', param_type=FilterParamType.STRING,
                    default_value='ih',
                    description='Итоговая высота (ih=input height)'
                ),
                FilterParameter(
                    name='x', display_name='Позиция X', param_type=FilterParamType.STRING,
                    default_value='0',
                    description='X позиция оригинала (можно (ow-iw)/2 для центра)'
                ),
                FilterParameter(
                    name='y', display_name='Позиция Y', param_type=FilterParamType.STRING,
                    default_value='0',
                    description='Y позиция оригинала'
                ),
                FilterParameter(
                    name='color', display_name='Цвет', param_type=FilterParamType.COLOR,
                    default_value='black',
                    description='Цвет padding'
                ),
            ]
        )

        # ============= VIDEO CREATIVE (ADVANCED) =============

        # Chromakey - хромакей
        self.filters['chromakey'] = FilterProfile(
            id='chromakey',
            name='Хромакей',
            ffmpeg_name='chromakey',
            category=FilterCategory.VIDEO_CREATIVE,
            description='Удаление цветного фона',
            icon='🟩',
            processing_cost=3,
            parameters=[
                FilterParameter(
                    name='color', display_name='Цвет', param_type=FilterParamType.COLOR,
                    default_value='green',
                    description='Цвет для удаления (green, blue, или hex)'
                ),
                FilterParameter(
                    name='similarity', display_name='Схожесть', param_type=FilterParamType.FLOAT,
                    default_value=0.3, min_value=0.0, max_value=1.0, step=0.01,
                    description='Допуск схожести цвета (0-1)'
                ),
                FilterParameter(
                    name='blend', display_name='Смешивание', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=0.0, max_value=1.0, step=0.01,
                    description='Мягкость краев (0-1)'
                ),
            ]
        )

        # Colorkey - альтернативный chromakey
        self.filters['colorkey'] = FilterProfile(
            id='colorkey',
            name='Цветовой ключ',
            ffmpeg_name='colorkey',
            category=FilterCategory.VIDEO_CREATIVE,
            description='Продвинутое удаление цветного фона',
            icon='🎬',
            processing_cost=3,
            parameters=[
                FilterParameter(
                    name='color', display_name='Цвет', param_type=FilterParamType.COLOR,
                    default_value='0x00FF00',
                    description='Цвет для удаления (hex формат: 0xRRGGBB)'
                ),
                FilterParameter(
                    name='similarity', display_name='Схожесть', param_type=FilterParamType.FLOAT,
                    default_value=0.01, min_value=0.0, max_value=1.0, step=0.001,
                    description='Допуск схожести (меньше=точнее)'
                ),
                FilterParameter(
                    name='blend', display_name='Смешивание', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=0.0, max_value=1.0, step=0.01,
                    description='Мягкость краев'
                ),
            ]
        )

        # Edgedetect - детекция краев
        self.filters['edgedetect'] = FilterProfile(
            id='edgedetect',
            name='Обнаружение границ',
            ffmpeg_name='edgedetect',
            category=FilterCategory.VIDEO_CREATIVE,
            description='Обнаружение контуров/краев в изображении',
            icon='🔲',
            processing_cost=3,
            parameters=[
                FilterParameter(
                    name='mode', display_name='Режим', param_type=FilterParamType.CHOICE,
                    default_value='wires',
                    choices=[
                        ('wires', 'Белые линии на черном'),
                        ('colormix', 'Цветные линии с оригиналом'),
                        ('canny', 'Canny edge detection'),
                    ],
                    description='Режим отображения'
                ),
                FilterParameter(
                    name='low', display_name='Нижний порог', param_type=FilterParamType.FLOAT,
                    default_value=20.0, min_value=0.0, max_value=1.0, step=0.01,
                    description='Нижний порог детекции (для Canny)'
                ),
                FilterParameter(
                    name='high', display_name='Верхний порог', param_type=FilterParamType.FLOAT,
                    default_value=50.0, min_value=0.0, max_value=1.0, step=0.01,
                    description='Верхний порог детекции (для Canny)'
                ),
            ]
        )

        # Loop - зацикливание
        self.filters['loop'] = FilterProfile(
            id='loop',
            name='Зацикливание видео',
            ffmpeg_name='loop',
            category=FilterCategory.VIDEO_TIME,
            description='Зацикливание видео (повтор)',
            icon='🔁',
            processing_cost=1,
            parameters=[
                FilterParameter(
                    name='loop', display_name='Количество циклов', param_type=FilterParamType.INT,
                    default_value=0, min_value=-1, max_value=10000,
                    description='Количество повторов (-1=бесконечно, 0=один раз)'
                ),
                FilterParameter(
                    name='size', display_name='Размер петли', param_type=FilterParamType.INT,
                    default_value=0, min_value=0, max_value=32767,
                    description='Количество кадров в петле (0=все кадры)'
                ),
            ]
        )

        # Reverse - реверс
        self.filters['reverse'] = FilterProfile(
            id='reverse',
            name='Реверс видео',
            ffmpeg_name='reverse',
            category=FilterCategory.VIDEO_TIME,
            description='Воспроизведение видео в обратном направлении',
            icon='⏪',
            processing_cost=2,
            parameters=[]  # Нет параметров
        )

        # Setpts - изменение скорости
        self.filters['setpts'] = FilterProfile(
            id='setpts',
            name='Изменение скорости',
            ffmpeg_name='setpts',
            category=FilterCategory.VIDEO_TIME,
            description='Изменение скорости воспроизведения видео',
            icon='⏩',
            processing_cost=1,
            parameters=[
                FilterParameter(
                    name='expr', display_name='Выражение', param_type=FilterParamType.CHOICE,
                    default_value='PTS-STARTPTS',
                    choices=[
                        ('PTS-STARTPTS', 'Нормальная скорость (1x)'),
                        ('0.5*(PTS-STARTPTS)', 'Ускорение 2x'),
                        ('0.25*(PTS-STARTPTS)', 'Ускорение 4x'),
                        ('2*(PTS-STARTPTS)', 'Замедление 0.5x'),
                        ('4*(PTS-STARTPTS)', 'Замедление 0.25x'),
                    ],
                    description='PTS выражение для скорости'
                ),
            ]
        )

        # Deflicker - удаление мерцания
        self.filters['deflicker'] = FilterProfile(
            id='deflicker',
            name='Устранение мерцания',
            ffmpeg_name='deflicker',
            category=FilterCategory.VIDEO_EFFECTS,
            description='Удаление мерцания яркости между кадрами',
            icon='💡',
            processing_cost=3,
            parameters=[
                FilterParameter(
                    name='size', display_name='Размер окна', param_type=FilterParamType.INT,
                    default_value=5, min_value=2, max_value=129,
                    description='Размер временного окна (кадры)'
                ),
                FilterParameter(
                    name='mode', display_name='Режим', param_type=FilterParamType.CHOICE,
                    default_value='am',
                    choices=[
                        ('am', 'Arithmetic mean'),
                        ('gm', 'Geometric mean'),
                        ('hm', 'Harmonic mean'),
                        ('qm', 'Quadratic mean'),
                        ('cm', 'Cubic mean'),
                        ('pm', 'Power mean'),
                        ('median', 'Median'),
                    ],
                    description='Метод усреднения'
                ),
            ]
        )

        # Delogo - удаление логотипа
        self.filters['delogo'] = FilterProfile(
            id='delogo',
            name='Удаление логотипа',
            ffmpeg_name='delogo',
            category=FilterCategory.VIDEO_EFFECTS,
            description='Удаление логотипа/водяного знака с видео',
            icon='🚫',
            processing_cost=3,
            parameters=[
                FilterParameter(
                    name='x', display_name='Позиция X', param_type=FilterParamType.INT,
                    default_value=0, min_value=0, max_value=7680,
                    description='X координата логотипа', suffix='px'
                ),
                FilterParameter(
                    name='y', display_name='Позиция Y', param_type=FilterParamType.INT,
                    default_value=0, min_value=0, max_value=4320,
                    description='Y координата логотипа', suffix='px'
                ),
                FilterParameter(
                    name='w', display_name='Ширина', param_type=FilterParamType.INT,
                    default_value=100, min_value=1, max_value=7680,
                    description='Ширина области логотипа', suffix='px'
                ),
                FilterParameter(
                    name='h', display_name='Высота', param_type=FilterParamType.INT,
                    default_value=100, min_value=1, max_value=4320,
                    description='Высота области логотипа', suffix='px'
                ),
            ]
        )

        # Deshake - стабилизация (простая)
        self.filters['deshake'] = FilterProfile(
            id='deshake',
            name='Стабилизация',
            ffmpeg_name='deshake',
            category=FilterCategory.VIDEO_STABILIZE,
            description='Простая стабилизация дрожащего видео',
            icon='📹',
            processing_cost=4,
            parameters=[
                FilterParameter(
                    name='rx', display_name='Радиус поиска X', param_type=FilterParamType.INT,
                    default_value=16, min_value=0, max_value=64,
                    description='Радиус поиска по горизонтали'
                ),
                FilterParameter(
                    name='ry', display_name='Радиус поиска Y', param_type=FilterParamType.INT,
                    default_value=16, min_value=0, max_value=64,
                    description='Радиус поиска по вертикали'
                ),
            ]
        )

        # Overlay (для двух входов) - базовый
        self.filters['overlay_basic'] = FilterProfile(
            id='overlay_basic',
            name='Наложение',
            ffmpeg_name='overlay',
            category=FilterCategory.VIDEO_OVERLAY,
            description='Наложение одного видео поверх другого',
            icon='🎞️',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='x', display_name='Позиция X', param_type=FilterParamType.STRING,
                    default_value='0',
                    description='X позиция overlay (можно: (W-w)/2 для центра)'
                ),
                FilterParameter(
                    name='y', display_name='Позиция Y', param_type=FilterParamType.STRING,
                    default_value='0',
                    description='Y позиция overlay (можно: (H-h)/2)'
                ),
            ]
        )

        # Drawbox - рисование прямоугольника
        self.filters['drawbox'] = FilterProfile(
            id='drawbox',
            name='Рисование рамки',
            ffmpeg_name='drawbox',
            category=FilterCategory.VIDEO_OVERLAY,
            description='Рисование прямоугольника/рамки на видео',
            icon='⬜',
            processing_cost=1,
            parameters=[
                FilterParameter(
                    name='x', display_name='Позиция X', param_type=FilterParamType.STRING,
                    default_value='0',
                    description='X координата'
                ),
                FilterParameter(
                    name='y', display_name='Позиция Y', param_type=FilterParamType.STRING,
                    default_value='0',
                    description='Y координата'
                ),
                FilterParameter(
                    name='w', display_name='Ширина', param_type=FilterParamType.STRING,
                    default_value='100',
                    description='Ширина прямоугольника'
                ),
                FilterParameter(
                    name='h', display_name='Высота', param_type=FilterParamType.STRING,
                    default_value='100',
                    description='Высота прямоугольника'
                ),
                FilterParameter(
                    name='color', display_name='Цвет', param_type=FilterParamType.COLOR,
                    default_value='black@0.5',
                    description='Цвет и прозрачность'
                ),
                FilterParameter(
                    name='thickness', display_name='Толщина', param_type=FilterParamType.INT,
                    default_value=3, min_value=1, max_value=100,
                    description='Толщина линии (fill для заливки)', suffix='px'
                ),
            ]
        )

        # Drawgrid - сетка
        self.filters['drawgrid'] = FilterProfile(
            id='drawgrid',
            name=' Рисование сетки',
            ffmpeg_name='drawgrid',
            category=FilterCategory.VIDEO_OVERLAY,
            description='Рисование сетки на видео',
            icon='#️⃣',
            processing_cost=1,
            parameters=[
                FilterParameter(
                    name='width', display_name='Ширина ячейки', param_type=FilterParamType.INT,
                    default_value=100, min_value=1, max_value=1000,
                    description='Ширина ячейки сетки', suffix='px'
                ),
                FilterParameter(
                    name='height', display_name='Высота ячейки', param_type=FilterParamType.INT,
                    default_value=100, min_value=1, max_value=1000,
                    description='Высота ячейки сетки', suffix='px'
                ),
                FilterParameter(
                    name='color', display_name='Цвет', param_type=FilterParamType.COLOR,
                    default_value='black@0.5',
                    description='Цвет линий сетки'
                ),
            ]
        )

        # Tile - создание плитки из кадров
        self.filters['tile'] = FilterProfile(
            id='tile',
            name='Раскладка плиткой',
            ffmpeg_name='tile',
            category=FilterCategory.VIDEO_OVERLAY,
            description='Создание плитки из нескольких кадров',
            icon='🔲',
            processing_cost=3,
            parameters=[
                FilterParameter(
                    name='layout', display_name='Раскладка', param_type=FilterParamType.STRING,
                    default_value='3x3',
                    description='Раскладка (колонки x строки), например: 4x3'
                ),
                FilterParameter(
                    name='margin', display_name='Отступ', param_type=FilterParamType.INT,
                    default_value=0, min_value=0, max_value=100,
                    description='Отступ между кадрами', suffix='px'
                ),
                FilterParameter(
                    name='padding', display_name='Padding', param_type=FilterParamType.INT,
                    default_value=0, min_value=0, max_value=100,
                    description='Внешний отступ', suffix='px'
                ),
            ]
        )

        # Zoompan - zoom и pan
        self.filters['zoompan'] = FilterProfile(
            id='zoompan',
            name='Зум и панорамирование',
            ffmpeg_name='zoompan',
            category=FilterCategory.VIDEO_CREATIVE,
            description='Масштабирование и панорамирование видео',
            icon='🔍',
            processing_cost=3,
            parameters=[
                FilterParameter(
                    name='zoom', display_name='Масштаб', param_type=FilterParamType.STRING,
                    default_value='1',
                    description='Коэффициент масштаба (можно выражение, например: 1+0.01*on)'
                ),
                FilterParameter(
                    name='x', display_name='Позиция X', param_type=FilterParamType.STRING,
                    default_value='0',
                    description='X позиция (можно выражение)'
                ),
                FilterParameter(
                    name='y', display_name='Позиция Y', param_type=FilterParamType.STRING,
                    default_value='0',
                    description='Y позиция (можно выражение)'
                ),
                FilterParameter(
                    name='d', display_name='Длительность', param_type=FilterParamType.INT,
                    default_value=90, min_value=1, max_value=10000,
                    description='Длительность эффекта в кадрах'
                ),
            ]
        )

        # Fps - изменение FPS
        self.filters['fps'] = FilterProfile(
            id='fps',
            name='Конвертер FPS',
            ffmpeg_name='fps',
            category=FilterCategory.VIDEO_TIME,
            description='Конвертация частоты кадров',
            icon='🎞️',
            processing_cost=2,
            parameters=[
                FilterParameter(
                    name='fps', display_name='Целевой FPS', param_type=FilterParamType.CHOICE,
                    default_value='30',
                    choices=[
                        ('24', '24 fps (кино)'),
                        ('25', '25 fps (PAL)'),
                        ('30', '30 fps (NTSC)'),
                        ('48', '48 fps'),
                        ('50', '50 fps (PAL HD)'),
                        ('60', '60 fps (плавное)'),
                        ('120', '120 fps (high frame rate)'),
                    ],
                    description='Целевая частота кадров'
                ),
            ]
        )

        # Mpdecimate - удаление дубликатов
        self.filters['mpdecimate'] = FilterProfile(
            id='mpdecimate',
            name='Удаление дубликатов кадров',
            ffmpeg_name='mpdecimate',
            category=FilterCategory.VIDEO_TIME,
            description='Удаление похожих/дублирующихся кадров',
            icon='🗑️',
            processing_cost=3,
            parameters=[
                FilterParameter(
                    name='max', display_name='Макс. дубликаты', param_type=FilterParamType.INT,
                    default_value=0, min_value=0, max_value=100,
                    description='Макс. дубликатов подряд (0=удалять все)'
                ),
                FilterParameter(
                    name='hi', display_name='Порог высокий', param_type=FilterParamType.INT,
                    default_value=64*12, min_value=0, max_value=100000,
                    description='Порог различия (выше=больше дубликатов)'
                ),
            ]
        )

        # Premultiply/Unpremultiply для альфа
        self.filters['premultiply'] = FilterProfile(
            id='premultiply',
            name='Премножение альфа',
            ffmpeg_name='premultiply',
            category=FilterCategory.VIDEO_OVERLAY,
            description='Премножение альфа канала (для правильного композитинга)',
            icon='🎭',
            processing_cost=1,
            parameters=[]
        )

        self.filters['unpremultiply'] = FilterProfile(
            id='unpremultiply',
            name='Отмена премножения альфа',
            ffmpeg_name='unpremultiply',
            category=FilterCategory.VIDEO_OVERLAY,
            description='Отмена премножения альфа канала',
            icon='🎪',
            processing_cost=1,
            parameters=[]
        )

        # Lenscorrection - коррекция линз
        self.filters['lenscorrection'] = FilterProfile(
            id='lenscorrection',
            name='Коррекция объектива',
            ffmpeg_name='lenscorrection',
            category=FilterCategory.VIDEO_TRANSFORM,
            description='Коррекция искажений объектива (бочка/подушка)',
            icon='📷',
            processing_cost=3,
            parameters=[
                FilterParameter(
                    name='k1', display_name='Коэффициент k1', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-1.0, max_value=1.0, step=0.01,
                    description='Радиальное искажение k1 (отрицательный=бочка)'
                ),
                FilterParameter(
                    name='k2', display_name='Коэффициент k2', param_type=FilterParamType.FLOAT,
                    default_value=0.0, min_value=-1.0, max_value=1.0, step=0.01,
                    description='Радиальное искажение k2'
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