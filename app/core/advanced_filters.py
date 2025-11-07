"""
Расширенные фильтры FFmpeg
- Complex filtergraphs (Picture-in-Picture, chromakey, layouts)
- Stabilization
- LUTs and color grading
- Advanced effects
"""

from core.filter_profiles import (
    FilterProfile, FilterParameter, FilterParamType, FilterCategory
)


def get_advanced_video_filters():
    """Получить список расширенных видео фильтров"""
    filters = {}

    # === COMPLEX FILTERGRAPHS ===

    # Chromakey / Green Screen
    filters['chromakey'] = FilterProfile(
        id='chromakey',
        name='Хромакей (Зеленый экран)',
        ffmpeg_name='chromakey',
        category=FilterCategory.VIDEO_CREATIVE,
        description='Удаление цветного фона (зеленый/синий экран)',
        icon='🎬',
        processing_cost=3,
        parameters=[
            FilterParameter(
                name='color',
                display_name='Цвет',
                param_type=FilterParamType.COLOR,
                default_value='#00FF00',
                description='Цвет для удаления (обычно зеленый #00FF00)'
            ),
            FilterParameter(
                name='similarity',
                display_name='Похожесть',
                param_type=FilterParamType.FLOAT,
                default_value=0.3,
                min_value=0.0,
                max_value=1.0,
                step=0.01,
                description='Насколько похожие цвета удалять (0.01-1.0)'
            ),
            FilterParameter(
                name='blend',
                display_name='Смешивание',
                param_type=FilterParamType.FLOAT,
                default_value=0.1,
                min_value=0.0,
                max_value=1.0,
                step=0.01,
                description='Плавность краев (0.0-1.0)'
            )
        ]
    )

    # Colorkey (альтернатива chromakey)
    filters['colorkey'] = FilterProfile(
        id='colorkey',
        name='Цветовой ключ',
        ffmpeg_name='colorkey',
        category=FilterCategory.VIDEO_CREATIVE,
        description='Удаление цвета с расширенными настройками',
        icon='🎨',
        processing_cost=3,
        parameters=[
            FilterParameter(
                name='color',
                display_name='Цвет',
                param_type=FilterParamType.COLOR,
                default_value='#00FF00',
                description='Цвет для удаления'
            ),
            FilterParameter(
                name='similarity',
                display_name='Похожесть',
                param_type=FilterParamType.FLOAT,
                default_value=0.01,
                min_value=0.0,
                max_value=1.0,
                step=0.001,
                description='Диапазон цвета'
            ),
            FilterParameter(
                name='blend',
                display_name='Смешивание',
                param_type=FilterParamType.FLOAT,
                default_value=0.0,
                min_value=0.0,
                max_value=1.0,
                step=0.001,
                description='Плавность границы'
            )
        ]
    )

    # === STABILIZATION ===

    filters['vidstabdetect'] = FilterProfile(
        id='vidstabdetect',
        name='Стабилизация: Анализ (шаг 1)',
        ffmpeg_name='vidstabdetect',
        category=FilterCategory.VIDEO_STABILIZE,
        description='Анализ движения камеры (первый проход для стабилизации)',
        icon='📹',
        processing_cost=4,
        parameters=[
            FilterParameter(
                name='shakiness',
                display_name='Сила дрожания',
                param_type=FilterParamType.INT,
                default_value=5,
                min_value=1,
                max_value=10,
                description='Насколько сильное дрожание обнаружить (1=слабое, 10=сильное)'
            ),
            FilterParameter(
                name='accuracy',
                display_name='Точность',
                param_type=FilterParamType.INT,
                default_value=15,
                min_value=1,
                max_value=15,
                description='Точность анализа (больше = медленнее, но точнее)'
            ),
            FilterParameter(
                name='result',
                display_name='Файл результата',
                param_type=FilterParamType.STRING,
                default_value='transforms.trf',
                description='Путь к файлу с данными трансформаций'
            )
        ]
    )

    filters['vidstabtransform'] = FilterProfile(
        id='vidstabtransform',
        name='Стабилизация: Применение (шаг 2)',
        ffmpeg_name='vidstabtransform',
        category=FilterCategory.VIDEO_STABILIZE,
        description='Применение стабилизации на основе анализа',
        icon='🎯',
        processing_cost=4,
        parameters=[
            FilterParameter(
                name='input',
                display_name='Файл трансформаций',
                param_type=FilterParamType.STRING,
                default_value='transforms.trf',
                description='Файл из vidstabdetect'
            ),
            FilterParameter(
                name='smoothing',
                display_name='Сглаживание',
                param_type=FilterParamType.INT,
                default_value=10,
                min_value=0,
                max_value=100,
                description='Сила сглаживания движения (0=нет, 100=максимум)'
            ),
            FilterParameter(
                name='zoom',
                display_name='Зум',
                param_type=FilterParamType.INT,
                default_value=0,
                min_value=-100,
                max_value=100,
                description='Увеличение для обрезки краев (%)'
            ),
            FilterParameter(
                name='optzoom',
                display_name='Оптимальный зум',
                param_type=FilterParamType.BOOL,
                default_value=True,
                description='Автоматически подобрать зум'
            )
        ]
    )

    filters['deshake'] = FilterProfile(
        id='deshake',
        name='Простая стабилизация',
        ffmpeg_name='deshake',
        category=FilterCategory.VIDEO_STABILIZE,
        description='Простая стабилизация видео (одно проход)',
        icon='🛠️',
        processing_cost=3,
        parameters=[
            FilterParameter(
                name='edge',
                display_name='Края',
                param_type=FilterParamType.CHOICE,
                default_value='mirror',
                choices=[
                    ('blank', 'Пустые (черные)'),
                    ('original', 'Оригинал'),
                    ('clamp', 'Растянуть'),
                    ('mirror', 'Отразить')
                ],
                description='Как заполнить края'
            )
        ]
    )

    # === COLOR GRADING & LUTS ===

    filters['lut3d'] = FilterProfile(
        id='lut3d',
        name='3D LUT (Цветокоррекция)',
        ffmpeg_name='lut3d',
        category=FilterCategory.VIDEO_COLOR,
        description='Применение 3D LUT файла для цветокоррекции',
        icon='🎨',
        processing_cost=2,
        parameters=[
            FilterParameter(
                name='file',
                display_name='LUT файл',
                param_type=FilterParamType.FILE,
                default_value='',
                description='Путь к .cube или .3dl файлу',
                required=True
            ),
            FilterParameter(
                name='interp',
                display_name='Интерполяция',
                param_type=FilterParamType.CHOICE,
                default_value='tetrahedral',
                choices=[
                    ('nearest', 'Ближайшая'),
                    ('trilinear', 'Трилинейная'),
                    ('tetrahedral', 'Тетраэдрическая'),
                    ('pyramid', 'Пирамида')
                ],
                description='Метод интерполяции'
            )
        ]
    )

    filters['colorlevels'] = FilterProfile(
        id='colorlevels',
        name='Уровни цвета',
        ffmpeg_name='colorlevels',
        category=FilterCategory.VIDEO_COLOR,
        description='Настройка уровней цвета (аналог Levels в Photoshop)',
        icon='🌈',
        processing_cost=2,
        parameters=[
            FilterParameter(
                name='rimin',
                display_name='Красный Мин',
                param_type=FilterParamType.FLOAT,
                default_value=0.0,
                min_value=0.0,
                max_value=1.0,
                step=0.01,
                description='Минимальный уровень красного канала'
            ),
            FilterParameter(
                name='gimin',
                display_name='Зеленый Мин',
                param_type=FilterParamType.FLOAT,
                default_value=0.0,
                min_value=0.0,
                max_value=1.0,
                step=0.01,
                description='Минимальный уровень зеленого канала'
            ),
            FilterParameter(
                name='bimin',
                display_name='Синий Мин',
                param_type=FilterParamType.FLOAT,
                default_value=0.0,
                min_value=0.0,
                max_value=1.0,
                step=0.01,
                description='Минимальный уровень синего канала'
            ),
            FilterParameter(
                name='rimax',
                display_name='Красный Макс',
                param_type=FilterParamType.FLOAT,
                default_value=1.0,
                min_value=0.0,
                max_value=1.0,
                step=0.01,
                description='Максимальный уровень красного канала'
            ),
            FilterParameter(
                name='gimax',
                display_name='Зеленый Макс',
                param_type=FilterParamType.FLOAT,
                default_value=1.0,
                min_value=0.0,
                max_value=1.0,
                step=0.01,
                description='Максимальный уровень зеленого канала'
            ),
            FilterParameter(
                name='bimax',
                display_name='Синий Макс',
                param_type=FilterParamType.FLOAT,
                default_value=1.0,
                min_value=0.0,
                max_value=1.0,
                step=0.01,
                description='Максимальный уровень синего канала'
            )
        ]
    )

    filters['curves'] = FilterProfile(
        id='curves',
        name='Curves (Кривые)',
        ffmpeg_name='curves',
        category=FilterCategory.VIDEO_COLOR,
        description='Цветовые кривые для точной настройки тона',
        icon='📊',
        processing_cost=2,
        parameters=[
            FilterParameter(
                name='preset',
                display_name='Пресет',
                param_type=FilterParamType.CHOICE,
                default_value='none',
                choices=[
                    ('none', 'Нет'),
                    ('color_negative', 'Цветовой негатив'),
                    ('cross_process', 'Cross Process'),
                    ('darker', 'Темнее'),
                    ('increase_contrast', 'Контраст +'),
                    ('lighter', 'Светлее'),
                    ('linear_contrast', 'Линейный контраст'),
                    ('medium_contrast', 'Средний контраст'),
                    ('negative', 'Негатив'),
                    ('strong_contrast', 'Сильный контраст'),
                    ('vintage', 'Винтаж')
                ],
                description='Готовый пресет кривых'
            )
        ]
    )

    # === ADVANCED EFFECTS ===

    filters['perspective'] = FilterProfile(
        id='perspective',
        name='Перспектива',
        ffmpeg_name='perspective',
        category=FilterCategory.VIDEO_TRANSFORM,
        description='Коррекция перспективы и искажения',
        icon='🔲',
        processing_cost=3,
        parameters=[
            FilterParameter(
                name='sense',
                display_name='Режим',
                param_type=FilterParamType.CHOICE,
                default_value='source',
                choices=[
                    ('source', 'Исходная перспектива'),
                    ('destination', 'Целевая перспектива')
                ],
                description='Режим коррекции'
            ),
            FilterParameter(
                name='interp',
                display_name='Интерполяция',
                param_type=FilterParamType.CHOICE,
                default_value='linear',
                choices=[
                    ('linear', 'Линейная'),
                    ('cubic', 'Кубическая')
                ],
                description='Метод интерполяции'
            )
        ]
    )

    filters['lenscorrection'] = FilterProfile(
        id='lenscorrection',
        name='Коррекция линз',
        ffmpeg_name='lenscorrection',
        category=FilterCategory.VIDEO_TRANSFORM,
        description='Коррекция искажений объектива (бочка/подушка)',
        icon='🔍',
        processing_cost=3,
        parameters=[
            FilterParameter(
                name='k1',
                display_name='Радиальное искажение 1',
                param_type=FilterParamType.FLOAT,
                default_value=0.0,
                min_value=-1.0,
                max_value=1.0,
                step=0.01,
                description='Первый коэффициент радиального искажения'
            ),
            FilterParameter(
                name='k2',
                display_name='Радиальное искажение 2',
                param_type=FilterParamType.FLOAT,
                default_value=0.0,
                min_value=-1.0,
                max_value=1.0,
                step=0.01,
                description='Второй коэффициент радиального искажения'
            )
        ]
    )

    filters['minterpolate'] = FilterProfile(
        id='minterpolate',
        name='Интерполяция движения',
        ffmpeg_name='minterpolate',
        category=FilterCategory.VIDEO_TIME,
        description='Интерполяция кадров для smooth motion / slow motion',
        icon='🎞️',
        processing_cost=5,
        parameters=[
            FilterParameter(
                name='fps',
                display_name='Целевой FPS',
                param_type=FilterParamType.INT,
                default_value=60,
                min_value=1,
                max_value=240,
                description='Целевая частота кадров'
            ),
            FilterParameter(
                name='mi_mode',
                display_name='Режим интерполяции',
                param_type=FilterParamType.CHOICE,
                default_value='mci',
                choices=[
                    ('dup', 'Дублирование (быстро)'),
                    ('blend', 'Смешивание'),
                    ('mci', 'Motion Compensated (лучшее качество)')
                ],
                description='Алгоритм интерполяции'
            )
        ]
    )

    filters['zoompan'] = FilterProfile(
        id='zoompan',
        name='Зум/Панорама (Кен Бернс)',
        ffmpeg_name='zoompan',
        category=FilterCategory.VIDEO_CREATIVE,
        description='Эффект панорамирования и масштабирования (Ken Burns)',
        icon='🎥',
        processing_cost=3,
        parameters=[
            FilterParameter(
                name='zoom',
                display_name='Зум',
                param_type=FilterParamType.STRING,
                default_value='1',
                description='Выражение зума (1=без зума, 2=увеличение в 2x)'
            ),
            FilterParameter(
                name='x',
                display_name='Позиция X',
                param_type=FilterParamType.STRING,
                default_value='iw/2-(iw/zoom/2)',
                description='Выражение для X координаты'
            ),
            FilterParameter(
                name='y',
                display_name='Позиция Y',
                param_type=FilterParamType.STRING,
                default_value='ih/2-(ih/zoom/2)',
                description='Выражение для Y координаты'
            ),
            FilterParameter(
                name='d',
                display_name='Длительность',
                param_type=FilterParamType.INT,
                default_value=90,
                min_value=1,
                max_value=1000,
                description='Длительность эффекта в кадрах'
            )
        ]
    )

    filters['reverse'] = FilterProfile(
        id='reverse',
        name='Реверс',
        ffmpeg_name='reverse',
        category=FilterCategory.VIDEO_TIME,
        description='Воспроизведение видео в обратном порядке',
        icon='⏪',
        processing_cost=2,
        parameters=[]  # Нет параметров
    )

    filters['tblend'] = FilterProfile(
        id='tblend',
        name='Временное смешивание',
        ffmpeg_name='tblend',
        category=FilterCategory.VIDEO_EFFECTS,
        description='Смешивание соседних кадров во времени',
        icon='🌫️',
        processing_cost=2,
        parameters=[
            FilterParameter(
                name='all_mode',
                display_name='Режим смешивания',
                param_type=FilterParamType.CHOICE,
                default_value='average',
                choices=[
                    ('addition', 'Сложение'),
                    ('average', 'Среднее'),
                    ('subtract', 'Вычитание'),
                    ('multiply', 'Умножение'),
                    ('screen', 'Экран'),
                    ('overlay', 'Наложение'),
                    ('difference', 'Разница')
                ],
                description='Как смешивать кадры'
            )
        ]
    )

    # === AUDIO VISUALIZATION ===

    filters['showwaves'] = FilterProfile(
        id='showwaves',
        name='Аудио волна',
        ffmpeg_name='showwaves',
        category=FilterCategory.VIDEO_ANALYSIS,
        description='Визуализация аудио волны',
        icon='🌊',
        processing_cost=2,
        parameters=[
            FilterParameter(
                name='size',
                display_name='Размер',
                param_type=FilterParamType.STRING,
                default_value='1920x1080',
                description='Размер видео (ширина x высота)'
            ),
            FilterParameter(
                name='mode',
                display_name='Режим',
                param_type=FilterParamType.CHOICE,
                default_value='line',
                choices=[
                    ('point', 'Точки'),
                    ('line', 'Линия'),
                    ('p2p', 'Точка-точка'),
                    ('cline', 'Центральная линия')
                ],
                description='Режим визуализации'
            ),
            FilterParameter(
                name='rate',
                display_name='FPS',
                param_type=FilterParamType.INT,
                default_value=25,
                min_value=1,
                max_value=60,
                description='Частота кадров'
            )
        ]
    )

    filters['showspectrum'] = FilterProfile(
        id='showspectrum',
        name='Аудио спектр',
        ffmpeg_name='showspectrum',
        category=FilterCategory.VIDEO_ANALYSIS,
        description='Визуализация аудио спектра (частотный анализ)',
        icon='📊',
        processing_cost=3,
        parameters=[
            FilterParameter(
                name='size',
                display_name='Размер',
                param_type=FilterParamType.STRING,
                default_value='1920x1080',
                description='Размер видео'
            ),
            FilterParameter(
                name='scale',
                display_name='Шкала',
                param_type=FilterParamType.CHOICE,
                default_value='log',
                choices=[
                    ('lin', 'Линейная'),
                    ('log', 'Логарифмическая'),
                    ('sqrt', 'Квадратный корень'),
                    ('cbrt', 'Кубический корень')
                ],
                description='Шкала частот'
            ),
            FilterParameter(
                name='color',
                display_name='Цветовая схема',
                param_type=FilterParamType.CHOICE,
                default_value='intensity',
                choices=[
                    ('intensity', 'Интенсивность'),
                    ('rainbow', 'Радуга'),
                    ('moreland', 'Морленд'),
                    ('nebulae', 'Туманность'),
                    ('fire', 'Огонь'),
                    ('fiery', 'Пламя'),
                    ('fruit', 'Фрукты'),
                    ('cool', 'Холодный'),
                    ('magma', 'Магма'),
                    ('green', 'Зеленый')
                ],
                description='Цветовая схема'
            )
        ]
    )

    filters['showvolume'] = FilterProfile(
        id='showvolume',
        name='Громкость аудио',
        ffmpeg_name='showvolume',
        category=FilterCategory.VIDEO_ANALYSIS,
        description='Визуализация громкости аудио',
        icon='🔊',
        processing_cost=1,
        parameters=[
            FilterParameter(
                name='r',
                display_name='FPS',
                param_type=FilterParamType.INT,
                default_value=25,
                min_value=1,
                max_value=60,
                description='Частота обновления'
            ),
            FilterParameter(
                name='b',
                display_name='Граница',
                param_type=FilterParamType.INT,
                default_value=1,
                min_value=0,
                max_value=5,
                description='Толщина границы'
            ),
            FilterParameter(
                name='w',
                display_name='Ширина',
                param_type=FilterParamType.INT,
                default_value=400,
                min_value=10,
                max_value=2000,
                description='Ширина индикатора'
            ),
            FilterParameter(
                name='h',
                display_name='Высота',
                param_type=FilterParamType.INT,
                default_value=20,
                min_value=10,
                max_value=200,
                description='Высота индикатора'
            )
        ]
    )

    return filters


def get_advanced_audio_filters():
    """Получить список расширенных аудио фильтров"""
    filters = {}

    # Compressor
    filters['acompressor'] = FilterProfile(
        id='acompressor',
        name='Компрессор',
        ffmpeg_name='acompressor',
        category=FilterCategory.AUDIO_DYNAMICS,
        description='Динамическая компрессия аудио',
        icon='🎚️',
        processing_cost=2,
        parameters=[
            FilterParameter(
                name='threshold',
                display_name='Порог',
                param_type=FilterParamType.FLOAT,
                default_value=0.125,
                min_value=0.0,
                max_value=1.0,
                step=0.001,
                description='Порог компрессии'
            ),
            FilterParameter(
                name='ratio',
                display_name='Соотношение',
                param_type=FilterParamType.FLOAT,
                default_value=2.0,
                min_value=1.0,
                max_value=20.0,
                step=0.1,
                description='Соотношение компрессии (2=2:1, 4=4:1)'
            ),
            FilterParameter(
                name='attack',
                display_name='Атака',
                param_type=FilterParamType.FLOAT,
                default_value=20.0,
                min_value=0.01,
                max_value=2000.0,
                suffix=' мс',
                description='Время атаки в миллисекундах'
            ),
            FilterParameter(
                name='release',
                display_name='Спад',
                param_type=FilterParamType.FLOAT,
                default_value=250.0,
                min_value=0.01,
                max_value=9000.0,
                suffix=' мс',
                description='Время спада в миллисекундах'
            )
        ]
    )

    # Gate
    filters['agate'] = FilterProfile(
        id='agate',
        name='Гейт',
        ffmpeg_name='agate',
        category=FilterCategory.AUDIO_DYNAMICS,
        description='Noise gate для подавления тихих звуков',
        icon='🚪',
        processing_cost=2,
        parameters=[
            FilterParameter(
                name='threshold',
                display_name='Порог',
                param_type=FilterParamType.FLOAT,
                default_value=0.125,
                min_value=0.0,
                max_value=1.0,
                step=0.001,
                description='Порог открытия гейта'
            ),
            FilterParameter(
                name='ratio',
                display_name='Соотношение',
                param_type=FilterParamType.FLOAT,
                default_value=2.0,
                min_value=1.0,
                max_value=9000.0,
                step=0.1,
                description='Соотношение подавления'
            ),
            FilterParameter(
                name='attack',
                display_name='Атака',
                param_type=FilterParamType.FLOAT,
                default_value=20.0,
                min_value=0.01,
                max_value=9000.0,
                suffix=' мс',
                description='Время атаки'
            ),
            FilterParameter(
                name='release',
                display_name='Спад',
                param_type=FilterParamType.FLOAT,
                default_value=250.0,
                min_value=0.01,
                max_value=9000.0,
                suffix=' мс',
                description='Время спада'
            )
        ]
    )

    # Equalizer
    filters['equalizer'] = FilterProfile(
        id='equalizer',
        name='Эквалайзер',
        ffmpeg_name='equalizer',
        category=FilterCategory.AUDIO_EQ,
        description='Параметрический эквалайзер',
        icon='🎛️',
        processing_cost=2,
        parameters=[
            FilterParameter(
                name='frequency',
                display_name='Частота',
                param_type=FilterParamType.INT,
                default_value=1000,
                min_value=1,
                max_value=20000,
                suffix=' Гц',
                description='Центральная частота'
            ),
            FilterParameter(
                name='width_type',
                display_name='Тип ширины',
                param_type=FilterParamType.CHOICE,
                default_value='q',
                choices=[
                    ('h', 'Гц'),
                    ('q', 'Q-фактор'),
                    ('o', 'Октавы')
                ],
                description='Единицы измерения ширины'
            ),
            FilterParameter(
                name='width',
                display_name='Ширина',
                param_type=FilterParamType.FLOAT,
                default_value=1.0,
                min_value=0.0,
                max_value=10.0,
                step=0.1,
                description='Ширина полосы'
            ),
            FilterParameter(
                name='gain',
                display_name='Усиление',
                param_type=FilterParamType.FLOAT,
                default_value=0.0,
                min_value=-20.0,
                max_value=20.0,
                step=0.1,
                suffix=' дБ',
                description='Усиление/ослабление'
            )
        ]
    )

    # Reverb
    filters['afreqshift'] = FilterProfile(
        id='afreqshift',
        name='Сдвиг частоты',
        ffmpeg_name='afreqshift',
        category=FilterCategory.AUDIO_EFFECTS,
        description='Сдвиг частоты (эффект Доплера, роботизация)',
        icon='🤖',
        processing_cost=2,
        parameters=[
            FilterParameter(
                name='shift',
                display_name='Сдвиг',
                param_type=FilterParamType.FLOAT,
                default_value=0.0,
                min_value=-10000.0,
                max_value=10000.0,
                step=1.0,
                suffix=' Гц',
                description='Сдвиг частоты в Гц'
            )
        ]
    )

    # Chorus
    filters['chorus'] = FilterProfile(
        id='chorus',
        name='Хорус',
        ffmpeg_name='chorus',
        category=FilterCategory.AUDIO_EFFECTS,
        description='Эффект хоруса (объемное звучание)',
        icon='🎤',
        processing_cost=3,
        parameters=[
            FilterParameter(
                name='delays',
                display_name='Задержки',
                param_type=FilterParamType.STRING,
                default_value='40|50',
                description='Задержки в мс (через |)'
            ),
            FilterParameter(
                name='decays',
                display_name='Затухания',
                param_type=FilterParamType.STRING,
                default_value='0.4|0.5',
                description='Затухания (через |)'
            ),
            FilterParameter(
                name='speeds',
                display_name='Скорости',
                param_type=FilterParamType.STRING,
                default_value='0.25|0.4',
                description='Скорости модуляции (через |)'
            ),
            FilterParameter(
                name='depths',
                display_name='Глубины',
                param_type=FilterParamType.STRING,
                default_value='2|2',
                description='Глубины модуляции (через |)'
            )
        ]
    )

    # Stereo widener
    filters['stereotools'] = FilterProfile(
        id='stereotools',
        name='Стерео инструменты',
        ffmpeg_name='stereotools',
        category=FilterCategory.AUDIO_SPATIAL,
        description='Расширение/сужение стерео базы',
        icon='🎧',
        processing_cost=2,
        parameters=[
            FilterParameter(
                name='mlev',
                display_name='Моно уровень',
                param_type=FilterParamType.FLOAT,
                default_value=1.0,
                min_value=0.0,
                max_value=2.0,
                step=0.01,
                description='Уровень моно сигнала'
            ),
            FilterParameter(
                name='slev',
                display_name='Стерео уровень',
                param_type=FilterParamType.FLOAT,
                default_value=1.0,
                min_value=0.0,
                max_value=2.0,
                step=0.01,
                description='Уровень стерео сигнала'
            ),
            FilterParameter(
                name='balance',
                display_name='Баланс',
                param_type=FilterParamType.FLOAT,
                default_value=0.0,
                min_value=-1.0,
                max_value=1.0,
                step=0.01,
                description='Баланс L/R (-1=левый, 1=правый)'
            )
        ]
    )

    return filters
