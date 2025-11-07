# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for FFmpeg UI 2.0
Builds a complete Windows application bundle with all dependencies
"""
import os
import sys
from pathlib import Path

block_cipher = None

# Paths
app_path = os.path.abspath('app')
resources_path = os.path.join(app_path, 'resources')

# Collect OpenCV binaries (required for video preview)
def get_cv2_binaries():
    """Collect OpenCV DLL files"""
    import cv2
    cv2_path = Path(cv2.__file__).parent
    binaries = []

    # OpenCV DLLs on Windows
    for dll in cv2_path.glob('*.dll'):
        binaries.append((str(dll), '.'))

    # OpenCV Python extension
    for pyd in cv2_path.glob('*.pyd'):
        binaries.append((str(pyd), 'cv2'))

    return binaries

# Collect PySide6 plugins (required for proper Qt functioning)
def get_pyside6_plugins():
    """Collect PySide6 plugin directories"""
    try:
        from PySide6 import QtCore
        qt_path = Path(QtCore.__file__).parent
        plugins_path = qt_path / 'plugins'

        datas = []
        if plugins_path.exists():
            # Critical plugins
            for plugin_dir in ['platforms', 'styles', 'imageformats', 'iconengines']:
                plugin_full = plugins_path / plugin_dir
                if plugin_full.exists():
                    datas.append((str(plugin_full), f'PySide6/plugins/{plugin_dir}'))

        return datas
    except ImportError:
        return []

# Collect additional binaries
additional_binaries = []
try:
    additional_binaries.extend(get_cv2_binaries())
except ImportError:
    print("WARNING: OpenCV not found - video preview will not work")

a = Analysis(
    ['app/main.py'],
    pathex=[app_path],
    binaries=additional_binaries,
    datas=[
        # FFmpeg binaries
        ('app/resources/ffmpeg/ffmpeg.exe', 'resources/ffmpeg'),
        ('app/resources/ffmpeg/ffplay.exe', 'resources/ffmpeg'),
        ('app/resources/ffmpeg/ffprobe.exe', 'resources/ffmpeg'),
        # Icons
        ('app/resources/icons', 'resources/icons'),
        # PySide6 plugins
        *get_pyside6_plugins(),
    ],
    hiddenimports=[
        # PySide6 core modules
        'PySide6.QtCore',
        'PySide6.QtGui',
        'PySide6.QtWidgets',
        'PySide6.QtSvg',
        'PySide6.QtSvgWidgets',
        'shiboken6',

        # Application modules - core
        'app',
        'app.core',
        'app.core.ffmpeg_manager',
        'app.core.gpu_detector',
        'app.core.codec_selector',
        'app.core.conversion_engine',
        'app.core.batch_processor',
        'app.core.format_database',
        'app.core.filter_profiles',
        'app.core.filter_manager',
        'app.core.stream_info',
        'app.core.ffprobe_manager',
        'app.core.advanced_filters',
        'app.core.chapters_manager',
        'app.core.concatenation',
        'app.core.image_sequence',

        # Application modules - UI
        'app.ui',
        'app.ui.main_window',
        'app.ui.widgets',
        'app.ui.widgets.file_selector',
        'app.ui.widgets.format_selector',
        'app.ui.widgets.video_options',
        'app.ui.widgets.audio_options',
        'app.ui.widgets.advanced_options',
        'app.ui.widgets.progress_widget',
        'app.ui.widgets.batch_queue',
        'app.ui.widgets.logger_widget',
        'app.ui.widgets.settings_dialog',
        'app.ui.widgets.filter_widget',
        'app.ui.widgets.stream_selector',
        'app.ui.widgets.timing_options',
        'app.ui.widgets.metadata_editor',
        'app.ui.widgets.subtitle_options',
        'app.ui.widgets.video_preview',
        'app.ui.widgets.chapters_widget',
        'app.ui.widgets.concatenation_widget',
        'app.ui.widgets.image_sequence_widget',
        'app.ui.styles',
        'app.ui.styles.modern_theme',

        # Python stdlib dependencies
        'psutil',
        'logging',
        'logging.handlers',
        'subprocess',
        'pathlib',
        'json',
        'enum',
        'dataclasses',
        'typing',
        'datetime',
        'tempfile',
        'shutil',
        'platform',
        'winreg',

        # OpenCV and image processing
        'cv2',
        'cv2.data',
        'numpy',
        'numpy.core',
        'numpy.core._multiarray_umath',
        'PIL',
        'PIL.Image',
        'PIL.ImageQt',
        'PIL._imaging',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'pandas',
        'pytest',
        'scipy',
        'IPython',
        'notebook',
        'sphinx',
        'setuptools',
        'pip',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='FFmpegUI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app/resources/icons/app_icon.ico',
    version_file=None,
)