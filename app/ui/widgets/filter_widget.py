from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QComboBox,
    QSpinBox, QDoubleSpinBox, QLineEdit, QCheckBox, QColorDialog,
    QScrollArea, QFrame, QMessageBox, QFileDialog, QDialog,
    QDialogButtonBox, QTextEdit, QSplitter, QTabWidget
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
import logging
from pathlib import Path
from typing import Dict, Any, Optional

from core.filter_manager import FilterManager, AppliedFilter
from core.filter_profiles import (
    FilterDatabase, FilterProfile, FilterCategory,
    FilterParameter, FilterParamType
)

logger = logging.getLogger(__name__)


class FilterParameterWidget(QWidget):
    """Виджет для одного параметра фильтра"""

    value_changed = Signal(str, object)  # (param_name, value)

    def __init__(self, parameter: FilterParameter, parent=None):
        super().__init__(parent)
        self.parameter = parameter
        self._init_ui()

    def _init_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)

        # Label
        label = QLabel(f"{self.parameter.display_name}:")
        label.setMinimumWidth(120)
        label.setToolTip(self.parameter.description)
        layout.addWidget(label)

        # Input widget в зависимости от типа
        if self.parameter.param_type == FilterParamType.INT:
            self.input_widget = QSpinBox()
            self.input_widget.setMinimum(int(self.parameter.min_value or -999999))
            self.input_widget.setMaximum(int(self.parameter.max_value or 999999))
            self.input_widget.setValue(int(self.parameter.default_value))
            if self.parameter.suffix:
                self.input_widget.setSuffix(f" {self.parameter.suffix}")
            self.input_widget.valueChanged.connect(
                lambda v: self.value_changed.emit(self.parameter.name, v)
            )

        elif self.parameter.param_type == FilterParamType.FLOAT:
            self.input_widget = QDoubleSpinBox()
            self.input_widget.setMinimum(float(self.parameter.min_value or -999999))
            self.input_widget.setMaximum(float(self.parameter.max_value or 999999))
            self.input_widget.setValue(float(self.parameter.default_value))
            self.input_widget.setDecimals(2)
            if self.parameter.step:
                self.input_widget.setSingleStep(self.parameter.step)
            if self.parameter.suffix:
                self.input_widget.setSuffix(f" {self.parameter.suffix}")
            self.input_widget.valueChanged.connect(
                lambda v: self.value_changed.emit(self.parameter.name, v)
            )

        elif self.parameter.param_type == FilterParamType.STRING:
            self.input_widget = QLineEdit()
            self.input_widget.setText(str(self.parameter.default_value))
            self.input_widget.setPlaceholderText(self.parameter.description)
            self.input_widget.textChanged.connect(
                lambda v: self.value_changed.emit(self.parameter.name, v)
            )

        elif self.parameter.param_type == FilterParamType.BOOL:
            self.input_widget = QCheckBox()
            self.input_widget.setChecked(bool(self.parameter.default_value))
            self.input_widget.stateChanged.connect(
                lambda s: self.value_changed.emit(self.parameter.name, s == Qt.Checked)
            )

        elif self.parameter.param_type == FilterParamType.CHOICE:
            self.input_widget = QComboBox()
            for value, label in self.parameter.choices:
                self.input_widget.addItem(label, value)
            # Установить значение по умолчанию
            index = self.input_widget.findData(self.parameter.default_value)
            if index >= 0:
                self.input_widget.setCurrentIndex(index)
            self.input_widget.currentIndexChanged.connect(
                lambda: self.value_changed.emit(
                    self.parameter.name,
                    self.input_widget.currentData()
                )
            )

        elif self.parameter.param_type == FilterParamType.COLOR:
            self.input_widget = QPushButton()
            self.input_widget.setText(str(self.parameter.default_value))
            self.input_widget.clicked.connect(self._choose_color)

        else:
            self.input_widget = QLineEdit()
            self.input_widget.setText(str(self.parameter.default_value))

        layout.addWidget(self.input_widget, stretch=1)

    def _choose_color(self):
        """Выбор цвета"""
        color = QColorDialog.getColor(QColor(self.input_widget.text()), self)
        if color.isValid():
            color_name = color.name()
            self.input_widget.setText(color_name)
            self.value_changed.emit(self.parameter.name, color_name)

    def get_value(self) -> Any:
        """Получить текущее значение"""
        if self.parameter.param_type == FilterParamType.INT:
            return self.input_widget.value()
        elif self.parameter.param_type == FilterParamType.FLOAT:
            return self.input_widget.value()
        elif self.parameter.param_type == FilterParamType.STRING:
            return self.input_widget.text()
        elif self.parameter.param_type == FilterParamType.BOOL:
            return self.input_widget.isChecked()
        elif self.parameter.param_type == FilterParamType.CHOICE:
            return self.input_widget.currentData()
        elif self.parameter.param_type == FilterParamType.COLOR:
            return self.input_widget.text()
        return None

    def set_value(self, value: Any):
        """Установить значение"""
        if self.parameter.param_type == FilterParamType.INT:
            self.input_widget.setValue(int(value))
        elif self.parameter.param_type == FilterParamType.FLOAT:
            self.input_widget.setValue(float(value))
        elif self.parameter.param_type == FilterParamType.STRING:
            self.input_widget.setText(str(value))
        elif self.parameter.param_type == FilterParamType.BOOL:
            self.input_widget.setChecked(bool(value))
        elif self.parameter.param_type == FilterParamType.CHOICE:
            index = self.input_widget.findData(value)
            if index >= 0:
                self.input_widget.setCurrentIndex(index)
        elif self.parameter.param_type == FilterParamType.COLOR:
            self.input_widget.setText(str(value))


class FilterEditDialog(QDialog):
    """Диалог редактирования параметров фильтра"""

    def __init__(self, filter_profile: FilterProfile, current_params: Dict[str, Any] = None, parent=None):
        super().__init__(parent)
        self.filter_profile = filter_profile
        self.current_params = current_params or {}
        self.param_widgets: Dict[str, FilterParameterWidget] = {}
        self._init_ui()

    def _init_ui(self):
        self.setWindowTitle(f"Настройка: {self.filter_profile.name}")
        self.setMinimumWidth(500)

        layout = QVBoxLayout(self)

        # Описание фильтра
        desc_label = QLabel(f"{self.filter_profile.icon} {self.filter_profile.description}")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("font-style: italic; color: #666; padding: 10px;")
        layout.addWidget(desc_label)

        # Параметры
        if self.filter_profile.parameters:
            params_group = QGroupBox("Параметры")
            params_layout = QVBoxLayout()

            for param in self.filter_profile.parameters:
                widget = FilterParameterWidget(param)
                # Установить текущее значение если есть
                if param.name in self.current_params:
                    widget.set_value(self.current_params[param.name])
                self.param_widgets[param.name] = widget
                params_layout.addWidget(widget)

            params_group.setLayout(params_layout)
            layout.addWidget(params_group)
        else:
            no_params = QLabel("Этот фильтр не имеет настраиваемых параметров")
            no_params.setAlignment(Qt.AlignCenter)
            no_params.setStyleSheet("color: #999; padding: 20px;")
            layout.addWidget(no_params)

        # Кнопки
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_parameters(self) -> Dict[str, Any]:
        """Получить все параметры"""
        return {name: widget.get_value() for name, widget in self.param_widgets.items()}


class FilterWidget(QWidget):
    """Главный виджет управления фильтрами"""

    filters_changed = Signal()  # Сигнал при изменении фильтров

    def __init__(self, filter_manager: FilterManager, parent=None):
        super().__init__(parent)
        self.filter_manager = filter_manager
        self.database = filter_manager.get_filter_database()
        self._init_ui()
        self._load_builtin_presets()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Создаем вкладки
        self.tabs = QTabWidget()

        # Вкладка 1: Библиотека фильтров
        library_tab = self._create_library_tab()
        self.tabs.addTab(library_tab, "📚 Библиотека")

        # Вкладка 2: Применённые фильтры
        applied_tab = self._create_applied_tab()
        self.tabs.addTab(applied_tab, "✅ Применённые")

        # Вкладка 3: Пресеты
        presets_tab = self._create_presets_tab()
        self.tabs.addTab(presets_tab, "💾 Пресеты")

        layout.addWidget(self.tabs)

        self._refresh_presets()

    def _create_library_tab(self) -> QWidget:
        """Создать вкладку библиотеки фильтров"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Категории
        category_layout = QHBoxLayout()
        category_layout.addWidget(QLabel("Категория:"))
        self.category_combo = QComboBox()
        self.category_combo.addItem("📚 Все фильтры", None)

        # Разделитель
        self.category_combo.addItem("", None)

        # Добавляем видео категории
        self.category_combo.addItem("─── 🎬 ВИДЕО ФИЛЬТРЫ ───", "separator_video")
        for category in FilterCategory:
            if category.value.startswith('video_'):
                self.category_combo.addItem(self._get_category_label(category), category)
        
        # Разделитель
        self.category_combo.addItem("", None)

        # Добавляем аудио категории
        self.category_combo.addItem("─── 🔊 АУДИО ФИЛЬТРЫ ───", "separator_audio")
        for category in FilterCategory:
            if category.value.startswith('audio_'):
                self.category_combo.addItem(self._get_category_label(category), category)

        self.category_combo.currentIndexChanged.connect(self._refresh_filter_list)
        category_layout.addWidget(self.category_combo, stretch=1)
        layout.addLayout(category_layout)

        # Список фильтров
        self.filter_list = QListWidget()
        self.filter_list.itemDoubleClicked.connect(self._add_filter_from_library)
        layout.addWidget(self.filter_list)

        # Кнопка добавить
        add_btn = QPushButton("➕ Добавить фильтр")
        add_btn.clicked.connect(self._add_filter_from_library)
        layout.addWidget(add_btn)

        self._refresh_filter_list()
        return tab

    def _create_applied_tab(self) -> QWidget:
        """Создать вкладку применённых фильтров"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Видео фильтры
        video_group = QGroupBox("🎬 Видео фильтры")
        video_layout = QVBoxLayout()

        self.video_filters_list = QListWidget()
        self.video_filters_list.setSelectionMode(QListWidget.SingleSelection)
        self.video_filters_list.itemDoubleClicked.connect(lambda: self._edit_filter(True))
        video_layout.addWidget(self.video_filters_list)

        video_buttons = QHBoxLayout()
        edit_video_btn = QPushButton("✏️ Изменить")
        edit_video_btn.clicked.connect(lambda: self._edit_filter(True))
        remove_video_btn = QPushButton("❌ Удалить")
        remove_video_btn.clicked.connect(lambda: self._remove_filter(True))
        up_video_btn = QPushButton("⬆️")
        up_video_btn.clicked.connect(lambda: self._move_filter(True, -1))
        down_video_btn = QPushButton("⬇️")
        down_video_btn.clicked.connect(lambda: self._move_filter(True, 1))

        video_buttons.addWidget(edit_video_btn)
        video_buttons.addWidget(remove_video_btn)
        video_buttons.addWidget(up_video_btn)
        video_buttons.addWidget(down_video_btn)
        video_layout.addLayout(video_buttons)
        video_group.setLayout(video_layout)

        # Аудио фильтры
        audio_group = QGroupBox("🔊 Аудио фильтры")
        audio_layout = QVBoxLayout()

        self.audio_filters_list = QListWidget()
        self.audio_filters_list.setSelectionMode(QListWidget.SingleSelection)
        self.audio_filters_list.itemDoubleClicked.connect(lambda: self._edit_filter(False))
        audio_layout.addWidget(self.audio_filters_list)

        audio_buttons = QHBoxLayout()
        edit_audio_btn = QPushButton("✏️ Изменить")
        edit_audio_btn.clicked.connect(lambda: self._edit_filter(False))
        remove_audio_btn = QPushButton("❌ Удалить")
        remove_audio_btn.clicked.connect(lambda: self._remove_filter(False))
        up_audio_btn = QPushButton("⬆️")
        up_audio_btn.clicked.connect(lambda: self._move_filter(False, -1))
        down_audio_btn = QPushButton("⬇️")
        down_audio_btn.clicked.connect(lambda: self._move_filter(False, 1))

        audio_buttons.addWidget(edit_audio_btn)
        audio_buttons.addWidget(remove_audio_btn)
        audio_buttons.addWidget(up_audio_btn)
        audio_buttons.addWidget(down_audio_btn)
        audio_layout.addLayout(audio_buttons)
        audio_group.setLayout(audio_layout)

        layout.addWidget(video_group)
        layout.addWidget(audio_group)

        # Кнопки управления внизу
        buttons_layout = QHBoxLayout()

        self.preview_btn = QPushButton("👁 Предпросмотр команды")
        self.preview_btn.clicked.connect(self._preview_command)
        buttons_layout.addWidget(self.preview_btn)

        self.clear_btn = QPushButton("🗑 Очистить всё")
        self.clear_btn.clicked.connect(self._clear_all_filters)
        buttons_layout.addWidget(self.clear_btn)

        layout.addLayout(buttons_layout)

        return tab

    def _create_presets_tab(self) -> QWidget:
        """Создать вкладку пресетов"""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Описание
        info_label = QLabel("Пресеты позволяют сохранять и загружать наборы фильтров для повторного использования.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; padding: 10px; font-style: italic;")
        layout.addWidget(info_label)

        # Список пресетов
        presets_group = QGroupBox("Доступные пресеты")
        presets_layout = QVBoxLayout()

        self.preset_combo = QComboBox()
        self.preset_combo.addItem("-- Выберите пресет --", None)
        presets_layout.addWidget(self.preset_combo)

        presets_group.setLayout(presets_layout)
        layout.addWidget(presets_group)

        # Кнопки управления пресетами
        buttons_layout = QHBoxLayout()

        load_preset_btn = QPushButton("📥 Загрузить пресет")
        load_preset_btn.clicked.connect(self._load_preset)
        buttons_layout.addWidget(load_preset_btn)

        save_preset_btn = QPushButton("💾 Сохранить пресет")
        save_preset_btn.clicked.connect(self._save_preset)
        buttons_layout.addWidget(save_preset_btn)

        layout.addLayout(buttons_layout)

        layout.addStretch()

        return tab

    def _get_category_label(self, category: FilterCategory) -> str:
        """Получить читаемое название категории"""
        labels = {
            # Видео категории
            FilterCategory.VIDEO_TRANSFORM: "🔄 Трансформации видео",
            FilterCategory.VIDEO_ADJUST: "🎨 Настройки цвета",
            FilterCategory.VIDEO_EFFECTS: "✨ Видео эффекты",
            FilterCategory.VIDEO_STABILIZE: "📹 Стабилизация видео",
            FilterCategory.VIDEO_CREATIVE: "🎬 Креативные эффекты",
            FilterCategory.VIDEO_OVERLAY: "📝 Наложения",
            FilterCategory.VIDEO_TIME: "⏱️ Временные эффекты",
            FilterCategory.VIDEO_COLOR: "🌈 Цветокоррекция",
            FilterCategory.VIDEO_BLUR: "🌫️ Размытие",
            FilterCategory.VIDEO_DEINTERLACE: "🎞️ Деинтерлейсинг",
            FilterCategory.VIDEO_ANALYSIS: "📊 Анализ видео",
            # Аудио категории
            FilterCategory.AUDIO_VOLUME: "🔊 Громкость",
            FilterCategory.AUDIO_EFFECTS: "🎵 Аудио эффекты",
            FilterCategory.AUDIO_FILTER: "📊 Частотные фильтры",
            FilterCategory.AUDIO_DYNAMICS: "🔧 Динамическая обработка",
            FilterCategory.AUDIO_EQ: "🎚️ Эквализация",
            FilterCategory.AUDIO_SPATIAL: "🎧 Пространственная обработка",
            FilterCategory.AUDIO_DENOISE: "🔇 Шумоподавление",
        }
        return labels.get(category, category.value)

    def _refresh_filter_list(self):
        """Обновить список фильтров в библиотеке"""
        self.filter_list.clear()

        category = self.category_combo.currentData()

        # Игнорируем разделители
        if isinstance(category, str) and category.startswith("separator_"):
            # Если выбран разделитель, переключаемся на "Все фильтры"
            self.category_combo.setCurrentIndex(0)
            return

        if category:
            filters = self.database.get_filters_by_category(category)
        else:
            filters = self.database.get_all_filters()

        for filter_profile in filters:
            item = QListWidgetItem(f"{filter_profile.icon} {filter_profile.name}")
            item.setData(Qt.UserRole, filter_profile.id)
            item.setToolTip(filter_profile.description)
            self.filter_list.addItem(item)

    def _add_filter_from_library(self):
        """Добавить фильтр из библиотеки"""
        current_item = self.filter_list.currentItem()
        if not current_item:
            return

        filter_id = current_item.data(Qt.UserRole)
        filter_profile = self.database.get_filter(filter_id)

        if not filter_profile:
            return

        # Открыть диалог настройки
        dialog = FilterEditDialog(filter_profile, parent=self)
        if dialog.exec():
            params = dialog.get_parameters()

            # Определить видео или аудио
            is_video = filter_profile.category in [
                FilterCategory.VIDEO_TRANSFORM,
                FilterCategory.VIDEO_ADJUST,
                FilterCategory.VIDEO_EFFECTS,
                FilterCategory.VIDEO_OVERLAY,
                FilterCategory.VIDEO_TIME
            ]

            if is_video:
                self.filter_manager.chain.add_video_filter(filter_id, params)
            else:
                self.filter_manager.chain.add_audio_filter(filter_id, params)

            self._refresh_applied_filters()
            self.filters_changed.emit()

    def _refresh_applied_filters(self):
        """Обновить списки применённых фильтров"""
        # Видео фильтры
        self.video_filters_list.clear()
        for applied_filter in self.filter_manager.chain.video_filters:
            profile = self.database.get_filter(applied_filter.filter_id)
            if profile:
                enabled_mark = "✓" if applied_filter.enabled else "✗"
                item = QListWidgetItem(f"{enabled_mark} {profile.icon} {profile.name}")
                item.setData(Qt.UserRole, applied_filter)
                self.video_filters_list.addItem(item)

        # Аудио фильтры
        self.audio_filters_list.clear()
        for applied_filter in self.filter_manager.chain.audio_filters:
            profile = self.database.get_filter(applied_filter.filter_id)
            if profile:
                enabled_mark = "✓" if applied_filter.enabled else "✗"
                item = QListWidgetItem(f"{enabled_mark} {profile.icon} {profile.name}")
                item.setData(Qt.UserRole, applied_filter)
                self.audio_filters_list.addItem(item)

    def _edit_filter(self, is_video: bool):
        """Редактировать фильтр"""
        list_widget = self.video_filters_list if is_video else self.audio_filters_list
        current_item = list_widget.currentItem()

        if not current_item:
            return

        applied_filter: AppliedFilter = current_item.data(Qt.UserRole)
        profile = self.database.get_filter(applied_filter.filter_id)

        if not profile:
            return

        dialog = FilterEditDialog(profile, applied_filter.parameters, parent=self)
        if dialog.exec():
            applied_filter.parameters = dialog.get_parameters()
            self._refresh_applied_filters()
            self.filters_changed.emit()

    def _remove_filter(self, is_video: bool):
        """Удалить фильтр"""
        list_widget = self.video_filters_list if is_video else self.audio_filters_list
        current_row = list_widget.currentRow()

        if current_row < 0:
            return

        if is_video:
            self.filter_manager.chain.remove_video_filter(current_row)
        else:
            self.filter_manager.chain.remove_audio_filter(current_row)

        self._refresh_applied_filters()
        self.filters_changed.emit()

    def _move_filter(self, is_video: bool, direction: int):
        """Переместить фильтр вверх/вниз"""
        list_widget = self.video_filters_list if is_video else self.audio_filters_list
        current_row = list_widget.currentRow()

        if current_row < 0:
            return

        new_row = current_row + direction

        if is_video:
            if 0 <= new_row < len(self.filter_manager.chain.video_filters):
                self.filter_manager.chain.move_video_filter(current_row, new_row)
        else:
            if 0 <= new_row < len(self.filter_manager.chain.audio_filters):
                self.filter_manager.chain.move_audio_filter(current_row, new_row)

        self._refresh_applied_filters()
        list_widget.setCurrentRow(new_row)
        self.filters_changed.emit()

    def _clear_all_filters(self):
        """Очистить все фильтры"""
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Удалить все применённые фильтры?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.filter_manager.chain.clear_all()
            self._refresh_applied_filters()
            self.filters_changed.emit()

    def _preview_command(self):
        """Предпросмотр FFmpeg команды"""
        video_filter_str = self.filter_manager.build_video_filter_string()
        audio_filter_str = self.filter_manager.build_audio_filter_string()

        preview_text = "FFmpeg фильтры:\n\n"

        if video_filter_str:
            preview_text += f"Видео фильтры:\n-vf \"{video_filter_str}\"\n\n"
        else:
            preview_text += "Видео фильтры: нет\n\n"

        if audio_filter_str:
            preview_text += f"Аудио фильтры:\n-af \"{audio_filter_str}\"\n"
        else:
            preview_text += "Аудио фильтры: нет\n"

        dialog = QDialog(self)
        dialog.setWindowTitle("Предпросмотр команды")
        dialog.setMinimumSize(600, 300)

        layout = QVBoxLayout(dialog)
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setPlainText(preview_text)
        layout.addWidget(text_edit)

        close_btn = QPushButton("Закрыть")
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)

        dialog.exec()

    def _load_builtin_presets(self):
        """Загрузить встроенные пресеты"""
        self.filter_manager.create_builtin_presets()

    def _refresh_presets(self):
        """Обновить список пресетов"""
        self.preset_combo.clear()
        self.preset_combo.addItem("-- Выберите пресет --", None)

        presets = self.filter_manager.get_available_presets()
        for preset in presets:
            label = f"{preset['name']} (V:{preset['video_count']}, A:{preset['audio_count']})"
            self.preset_combo.addItem(label, preset['file'])

    def _load_preset(self):
        """Загрузить пресет"""
        preset_file = self.preset_combo.currentData()
        if not preset_file:
            return

        if self.filter_manager.load_preset(preset_file):
            self._refresh_applied_filters()
            self.filters_changed.emit()
            QMessageBox.information(self, "Успех", "Пресет загружен")
        else:
            QMessageBox.warning(self, "Ошибка", "Не удалось загрузить пресет")

    def _save_preset(self):
        """Сохранить пресет"""
        from PySide6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(
            self, "Сохранить пресет",
            "Введите название пресета:"
        )

        if ok and name:
            description, ok = QInputDialog.getText(
                self, "Описание",
                "Описание пресета (опционально):"
            )

            if self.filter_manager.save_preset(name, description or ""):
                self._refresh_presets()
                QMessageBox.information(self, "Успех", "Пресет сохранён")
            else:
                QMessageBox.warning(self, "Ошибка", "Не удалось сохранить пресет")

    def get_video_filter_string(self) -> Optional[str]:
        """Получить строку видео фильтров для FFmpeg"""
        return self.filter_manager.build_video_filter_string()

    def get_audio_filter_string(self) -> Optional[str]:
        """Получить строку аудио фильтров для FFmpeg"""
        return self.filter_manager.build_audio_filter_string()

    def get_filters_for_preview(self) -> list:
        """Получить список фильтров для video preview"""
        filters_list = []

        # Получаем только видео фильтры из chain
        for applied_filter in self.filter_manager.chain.video_filters:
            if not applied_filter.enabled:
                continue

            # Получаем профиль фильтра
            profile = self.filter_manager.database.get_filter(applied_filter.filter_id)
            if profile:
                filters_list.append({
                    'id': profile.id,
                    'name': profile.name,
                    'enabled': applied_filter.enabled,
                    'params': applied_filter.parameters.copy()
                })

        logger.debug(f"Получено {len(filters_list)} фильтров для preview")
        return filters_list
