class ModernTheme:
    """Современная тема с поддержкой светлого и темного режимов"""

    def __init__(self, mode: str = "light"):
        """
        Инициализация темы

        Args:
            mode: Режим темы - 'light' или 'dark'
        """
        self.mode = mode

    def get_stylesheet(self) -> str:
        """Получить таблицу стилей в зависимости от режима"""
        if self.mode == "dark":
            return self._get_dark_stylesheet()
        else:
            return self._get_light_stylesheet()

    def _get_light_stylesheet(self) -> str:
        """Получить светлую тему"""
        return """
        /* Основные цвета */
        QWidget {
            background-color: #FAFAFA;
            color: #212121;
            font-family: "Segoe UI", Arial, sans-serif;
        }
        
        /* Главное окно */
        QMainWindow {
            background-color: #FFFFFF;
        }
        
        /* Кнопки */
        QPushButton {
            background-color: #E0E0E0;
            border: none;
            border-radius: 5px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 500;
            min-height: 35px;
        }
        
        QPushButton:hover {
            background-color: #BDBDBD;
        }
        
        QPushButton:pressed {
            background-color: #9E9E9E;
        }
        
        QPushButton:disabled {
            background-color: #F5F5F5;
            color: #9E9E9E;
        }
        
        QPushButton#primaryButton {
            background-color: #2196F3;
            color: white;
        }
        
        QPushButton#primaryButton:hover {
            background-color: #1976D2;
        }
        
        QPushButton#primaryButton:pressed {
            background-color: #0D47A1;
        }
        
        QPushButton#secondaryButton {
            background-color: #E3F2FD;
            color: #1976D2;
        }
        
        QPushButton#secondaryButton:hover {
            background-color: #BBDEFB;
        }
        
        QPushButton#dangerButton {
            background-color: #F44336;
            color: white;
        }
        
        QPushButton#dangerButton:hover {
            background-color: #D32F2F;
        }
        
        /* Поля ввода */
        QLineEdit {
            border: 2px solid #E0E0E0;
            border-radius: 5px;
            padding: 8px;
            background-color: white;
            selection-background-color: #2196F3;
        }
        
        QLineEdit:focus {
            border-color: #2196F3;
        }
        
        /* ComboBox */
        QComboBox {
            border: 2px solid #E0E0E0;
            border-radius: 5px;
            padding: 6px;
            background-color: white;
            min-height: 30px;
        }
        
        QComboBox:hover {
            border-color: #BDBDBD;
        }
        
        QComboBox:focus {
            border-color: #2196F3;
        }
        
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border: none;
            background-color: transparent;
        }

        QComboBox::down-arrow {
            width: 0;
            height: 0;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid #616161;
        }

        QComboBox:hover::down-arrow {
            border-top-color: #212121;
        }

        QComboBox:disabled::down-arrow {
            border-top-color: #BDBDBD;
        }
        
        QComboBox QAbstractItemView {
            border: 2px solid #E0E0E0;
            border-radius: 5px;
            background-color: white;
            selection-background-color: #E3F2FD;
            selection-color: #1976D2;
        }
        
        /* Слайдеры */
        QSlider::groove:horizontal {
            border: none;
            height: 8px;
            background: #E0E0E0;
            border-radius: 4px;
        }
        
        QSlider::handle:horizontal {
            background: #2196F3;
            border: none;
            width: 20px;
            height: 20px;
            margin: -6px 0;
            border-radius: 10px;
        }
        
        QSlider::handle:horizontal:hover {
            background: #1976D2;
        }
        
        QSlider::sub-page:horizontal {
            background: #2196F3;
            border-radius: 4px;
        }
        
        /* SpinBox */
        QSpinBox, QDoubleSpinBox {
            border: 2px solid #E0E0E0;
            border-radius: 5px;
            padding: 6px;
            background-color: white;
        }

        QSpinBox:focus, QDoubleSpinBox:focus {
            border-color: #2196F3;
        }

        QSpinBox::up-button, QSpinBox::down-button,
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
            subcontrol-origin: border;
            background-color: transparent;
            border: none;
            width: 16px;
        }

        QSpinBox::up-button, QDoubleSpinBox::up-button {
            subcontrol-position: top right;
        }

        QSpinBox::down-button, QDoubleSpinBox::down-button {
            subcontrol-position: bottom right;
        }

        QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
            width: 0;
            height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-bottom: 5px solid #616161;
        }

        QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
            width: 0;
            height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid #616161;
        }

        QSpinBox:hover::up-arrow, QDoubleSpinBox:hover::up-arrow {
            border-bottom-color: #212121;
        }

        QSpinBox:hover::down-arrow, QDoubleSpinBox:hover::down-arrow {
            border-top-color: #212121;
        }

        QSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:disabled {
            border-bottom-color: #BDBDBD;
        }

        QSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:disabled {
            border-top-color: #BDBDBD;
        }

        /* TimeEdit и DateTimeEdit */
        QTimeEdit, QDateTimeEdit, QDateEdit {
            border: 2px solid #E0E0E0;
            border-radius: 5px;
            padding: 6px;
            background-color: white;
        }

        QTimeEdit:focus, QDateTimeEdit:focus, QDateEdit:focus {
            border-color: #2196F3;
        }

        QTimeEdit::up-button, QTimeEdit::down-button,
        QDateTimeEdit::up-button, QDateTimeEdit::down-button,
        QDateEdit::up-button, QDateEdit::down-button {
            subcontrol-origin: border;
            background-color: transparent;
            border: none;
            width: 16px;
        }

        QTimeEdit::up-button, QDateTimeEdit::up-button, QDateEdit::up-button {
            subcontrol-position: top right;
        }

        QTimeEdit::down-button, QDateTimeEdit::down-button, QDateEdit::down-button {
            subcontrol-position: bottom right;
        }

        QTimeEdit::up-arrow, QDateTimeEdit::up-arrow, QDateEdit::up-arrow {
            width: 0;
            height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-bottom: 5px solid #616161;
        }

        QTimeEdit::down-arrow, QDateTimeEdit::down-arrow, QDateEdit::down-arrow {
            width: 0;
            height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid #616161;
        }

        QTimeEdit:hover::up-arrow, QDateTimeEdit:hover::up-arrow, QDateEdit:hover::up-arrow {
            border-bottom-color: #212121;
        }

        QTimeEdit:hover::down-arrow, QDateTimeEdit:hover::down-arrow, QDateEdit:hover::down-arrow {
            border-top-color: #212121;
        }

        QTimeEdit::up-arrow:disabled, QDateTimeEdit::up-arrow:disabled, QDateEdit::up-arrow:disabled {
            border-bottom-color: #BDBDBD;
        }

        QTimeEdit::down-arrow:disabled, QDateTimeEdit::down-arrow:disabled, QDateEdit::down-arrow:disabled {
            border-top-color: #BDBDBD;
        }

        /* CheckBox */
        QCheckBox {
            spacing: 8px;
        }
        
        QCheckBox::indicator {
            width: 20px;
            height: 20px;
            border: 2px solid #9E9E9E;
            border-radius: 3px;
            background-color: white;
        }
        
        QCheckBox::indicator:checked {
            background-color: #2196F3;
            border-color: #2196F3;
            image: url(none);
        }
        
        QCheckBox::indicator:hover {
            border-color: #2196F3;
        }
        
        /* GroupBox */
        QGroupBox {
            border: 2px solid #E0E0E0;
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 12px;
            font-weight: bold;
        }
        
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
            color: #1976D2;
        }
        
        /* TabWidget */
        QTabWidget::pane {
            border: 2px solid #E0E0E0;
            border-radius: 5px;
            background-color: white;
        }
        
        QTabBar::tab {
            background-color: #F5F5F5;
            border: none;
            padding: 10px 20px;
            margin-right: 2px;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
        }
        
        QTabBar::tab:selected {
            background-color: white;
            color: #2196F3;
            font-weight: bold;
        }
        
        QTabBar::tab:hover:!selected {
            background-color: #E0E0E0;
        }
        
        /* ScrollBar */
        QScrollBar:vertical {
            border: none;
            background-color: #F5F5F5;
            width: 12px;
            border-radius: 6px;
        }
        
        QScrollBar::handle:vertical {
            background-color: #BDBDBD;
            border-radius: 6px;
            min-height: 30px;
        }
        
        QScrollBar::handle:vertical:hover {
            background-color: #9E9E9E;
        }
        
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            height: 0px;
        }
        
        /* StatusBar */
        QStatusBar {
            background-color: #F5F5F5;
            border-top: 1px solid #E0E0E0;
        }
        
        /* MenuBar */
        QMenuBar {
            background-color: white;
            border-bottom: 1px solid #E0E0E0;
        }
        
        QMenuBar::item {
            padding: 8px 12px;
        }
        
        QMenuBar::item:selected {
            background-color: #E3F2FD;
            color: #1976D2;
        }
        
        QMenu {
            background-color: white;
            border: 2px solid #E0E0E0;
            border-radius: 5px;
        }
        
        QMenu::item {
            padding: 8px 25px;
        }
        
        QMenu::item:selected {
            background-color: #E3F2FD;
            color: #1976D2;
        }

        /* DropZone */
        #DropZone {
            border: 2px dashed #999999;
            border-radius: 8px;
            background-color: #F5F5F5;
        }

        #DropZone[hover="true"] {
            background-color: #E8F5E9;
            border-color: #4CAF50;
        }

        /* FormatDescription */
        #FormatDescription {
            border: 1px solid #E0E0E0;
            border-radius: 5px;
            background-color: #FAFAFA;
            color: #212121;
            padding: 8px;
            font-size: 10px;
        }
        """

    def _get_dark_stylesheet(self) -> str:
        """Получить темную тему"""
        return """
        /* Основные цвета - темная тема */
        QWidget {
            background-color: #1E1E1E;
            color: #E0E0E0;
            font-family: "Segoe UI", Arial, sans-serif;
        }

        /* Главное окно */
        QMainWindow {
            background-color: #252526;
        }

        /* Кнопки */
        QPushButton {
            background-color: #3E3E42;
            border: none;
            border-radius: 5px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 500;
            min-height: 35px;
            color: #E0E0E0;
        }

        QPushButton:hover {
            background-color: #4E4E52;
        }

        QPushButton:pressed {
            background-color: #5E5E62;
        }

        QPushButton:disabled {
            background-color: #2D2D30;
            color: #656565;
        }

        QPushButton#primaryButton {
            background-color: #0E639C;
            color: white;
        }

        QPushButton#primaryButton:hover {
            background-color: #1177BB;
        }

        QPushButton#primaryButton:pressed {
            background-color: #1C88D4;
        }

        QPushButton#secondaryButton {
            background-color: #264F78;
            color: #3794FF;
        }

        QPushButton#secondaryButton:hover {
            background-color: #2A5C8C;
        }

        QPushButton#dangerButton {
            background-color: #C72E2E;
            color: white;
        }

        QPushButton#dangerButton:hover {
            background-color: #E04343;
        }

        /* Поля ввода */
        QLineEdit {
            border: 1px solid #3E3E42;
            border-radius: 5px;
            padding: 8px;
            background-color: #2D2D30;
            color: #E0E0E0;
            selection-background-color: #264F78;
        }

        QLineEdit:focus {
            border-color: #0E639C;
        }

        /* ComboBox */
        QComboBox {
            border: 1px solid #3E3E42;
            border-radius: 5px;
            padding: 6px;
            background-color: #2D2D30;
            color: #E0E0E0;
            min-height: 30px;
        }

        QComboBox:hover {
            border-color: #505050;
        }

        QComboBox:focus {
            border-color: #0E639C;
        }

        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 20px;
            border: none;
            background-color: transparent;
        }

        QComboBox::down-arrow {
            width: 0;
            height: 0;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid #AAAAAA;
        }

        QComboBox:hover::down-arrow {
            border-top-color: #FFFFFF;
        }

        QComboBox:disabled::down-arrow {
            border-top-color: #656565;
        }

        QComboBox QAbstractItemView {
            border: 1px solid #3E3E42;
            border-radius: 5px;
            background-color: #2D2D30;
            color: #E0E0E0;
            selection-background-color: #094771;
            selection-color: #FFFFFF;
        }

        /* Слайдеры */
        QSlider::groove:horizontal {
            border: none;
            height: 8px;
            background: #3E3E42;
            border-radius: 4px;
        }

        QSlider::handle:horizontal {
            background: #0E639C;
            border: none;
            width: 20px;
            height: 20px;
            margin: -6px 0;
            border-radius: 10px;
        }

        QSlider::handle:horizontal:hover {
            background: #1177BB;
        }

        QSlider::sub-page:horizontal {
            background: #0E639C;
            border-radius: 4px;
        }

        /* SpinBox */
        QSpinBox, QDoubleSpinBox {
            border: 1px solid #3E3E42;
            border-radius: 5px;
            padding: 6px;
            background-color: #2D2D30;
            color: #E0E0E0;
        }

        QSpinBox:focus, QDoubleSpinBox:focus {
            border-color: #0E639C;
        }

        QSpinBox::up-button, QSpinBox::down-button,
        QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
            subcontrol-origin: border;
            background-color: transparent;
            border: none;
            width: 16px;
        }

        QSpinBox::up-button, QDoubleSpinBox::up-button {
            subcontrol-position: top right;
        }

        QSpinBox::down-button, QDoubleSpinBox::down-button {
            subcontrol-position: bottom right;
        }

        QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
            width: 0;
            height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-bottom: 5px solid #AAAAAA;
        }

        QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
            width: 0;
            height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid #AAAAAA;
        }

        QSpinBox:hover::up-arrow, QDoubleSpinBox:hover::up-arrow {
            border-bottom-color: #FFFFFF;
        }

        QSpinBox:hover::down-arrow, QDoubleSpinBox:hover::down-arrow {
            border-top-color: #FFFFFF;
        }

        QSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:disabled {
            border-bottom-color: #656565;
        }

        QSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:disabled {
            border-top-color: #656565;
        }

        /* TimeEdit и DateTimeEdit */
        QTimeEdit, QDateTimeEdit, QDateEdit {
            border: 1px solid #3E3E42;
            border-radius: 5px;
            padding: 6px;
            background-color: #2D2D30;
            color: #E0E0E0;
        }

        QTimeEdit:focus, QDateTimeEdit:focus, QDateEdit:focus {
            border-color: #0E639C;
        }

        QTimeEdit::up-button, QTimeEdit::down-button,
        QDateTimeEdit::up-button, QDateTimeEdit::down-button,
        QDateEdit::up-button, QDateEdit::down-button {
            subcontrol-origin: border;
            background-color: transparent;
            border: none;
            width: 16px;
        }

        QTimeEdit::up-button, QDateTimeEdit::up-button, QDateEdit::up-button {
            subcontrol-position: top right;
        }

        QTimeEdit::down-button, QDateTimeEdit::down-button, QDateEdit::down-button {
            subcontrol-position: bottom right;
        }

        QTimeEdit::up-arrow, QDateTimeEdit::up-arrow, QDateEdit::up-arrow {
            width: 0;
            height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-bottom: 5px solid #AAAAAA;
        }

        QTimeEdit::down-arrow, QDateTimeEdit::down-arrow, QDateEdit::down-arrow {
            width: 0;
            height: 0;
            border-left: 4px solid transparent;
            border-right: 4px solid transparent;
            border-top: 5px solid #AAAAAA;
        }

        QTimeEdit:hover::up-arrow, QDateTimeEdit:hover::up-arrow, QDateEdit:hover::up-arrow {
            border-bottom-color: #FFFFFF;
        }

        QTimeEdit:hover::down-arrow, QDateTimeEdit:hover::down-arrow, QDateEdit:hover::down-arrow {
            border-top-color: #FFFFFF;
        }

        QTimeEdit::up-arrow:disabled, QDateTimeEdit::up-arrow:disabled, QDateEdit::up-arrow:disabled {
            border-bottom-color: #656565;
        }

        QTimeEdit::down-arrow:disabled, QDateTimeEdit::down-arrow:disabled, QDateEdit::down-arrow:disabled {
            border-top-color: #656565;
        }

        /* CheckBox */
        QCheckBox {
            spacing: 8px;
            color: #E0E0E0;
        }

        QCheckBox::indicator {
            width: 20px;
            height: 20px;
            border: 2px solid #656565;
            border-radius: 3px;
            background-color: #2D2D30;
        }

        QCheckBox::indicator:checked {
            background-color: #0E639C;
            border-color: #0E639C;
            image: url(none);
        }

        QCheckBox::indicator:hover {
            border-color: #0E639C;
        }

        /* GroupBox */
        QGroupBox {
            border: 2px solid #3E3E42;
            border-radius: 8px;
            margin-top: 12px;
            padding-top: 12px;
            font-weight: bold;
            color: #E0E0E0;
        }

        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px;
            color: #3794FF;
        }

        /* TabWidget */
        QTabWidget::pane {
            border: 2px solid #3E3E42;
            border-radius: 5px;
            background-color: #252526;
        }

        QTabBar::tab {
            background-color: #2D2D30;
            color: #969696;
            border: none;
            padding: 10px 20px;
            margin-right: 2px;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
        }

        QTabBar::tab:selected {
            background-color: #1E1E1E;
            color: #FFFFFF;
            font-weight: bold;
        }

        QTabBar::tab:hover:!selected {
            background-color: #3E3E42;
        }

        /* ScrollBar */
        QScrollBar:vertical {
            border: none;
            background-color: #1E1E1E;
            width: 12px;
            border-radius: 6px;
        }

        QScrollBar::handle:vertical {
            background-color: #424242;
            border-radius: 6px;
            min-height: 30px;
        }

        QScrollBar::handle:vertical:hover {
            background-color: #4E4E4E;
        }

        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {
            height: 0px;
        }

        /* StatusBar */
        QStatusBar {
            background-color: #007ACC;
            color: #FFFFFF;
            border-top: 1px solid #005A9E;
        }

        /* MenuBar */
        QMenuBar {
            background-color: #2D2D30;
            color: #E0E0E0;
            border-bottom: 1px solid #3E3E42;
        }

        QMenuBar::item {
            padding: 8px 12px;
            background-color: transparent;
        }

        QMenuBar::item:selected {
            background-color: #3E3E42;
            color: #FFFFFF;
        }

        QMenu {
            background-color: #252526;
            border: 1px solid #454545;
            border-radius: 5px;
            color: #E0E0E0;
        }

        QMenu::item {
            padding: 8px 25px;
        }

        QMenu::item:selected {
            background-color: #094771;
            color: #FFFFFF;
        }

        /* DropZone - темная тема */
        #DropZone {
            border: 2px dashed #555555;
            border-radius: 8px;
            background-color: #2D2D30;
        }

        #DropZone[hover="true"] {
            background-color: rgba(76, 175, 80, 0.2);
            border-color: #4CAF50;
        }

        /* FormatDescription - темная тема */
        #FormatDescription {
            border: 1px solid #3E3E42;
            border-radius: 5px;
            background-color: #1E1E1E;
            color: #E0E0E0;
            padding: 8px;
            font-size: 10px;
        }
        """