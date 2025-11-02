import subprocess
import re
import time
import logging
from pathlib import Path
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class ConversionEngine(QObject):
    """Движок конвертации с GPU поддержкой"""

    progress_updated = Signal(dict)
    conversion_finished = Signal()
    conversion_error = Signal(str)

    def __init__(self, command: list, pass2_command: list = None, passlogfile: str = None):
        super().__init__()
        self.command = command
        self.pass2_command = pass2_command
        self.passlogfile = passlogfile  # Путь к passlogfile для cleanup
        self.process = None
        self._should_stop = False
        self._start_time = None
        self.current_pass = 1
        self.total_passes = 2 if pass2_command else 1

        logger.info(f"Создан ConversionEngine с командой: {' '.join(command)}")
        if pass2_command:
            logger.info(f"Двухпроходное кодирование включено. Проход 2: {' '.join(pass2_command)}")
            if passlogfile:
                logger.info(f"Passlogfile для двухпроходного кодирования: {passlogfile}")
    
    def start(self):
        """Запуск конвертации"""
        try:
            self._start_time = time.time()
            logger.info("Начало конвертации")
            logger.debug(f"Полная команда: {' '.join(self.command)}")
            
            self.process = subprocess.Popen(
                self.command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )
            
            self._monitor_progress()
            
        except FileNotFoundError as e:
            error_msg = f"FFmpeg не найден: {e}"
            logger.error(error_msg)
            self.conversion_error.emit(error_msg)
        except PermissionError as e:
            error_msg = f"Нет прав доступа для выполнения FFmpeg: {e}"
            logger.error(error_msg)
            self.conversion_error.emit(error_msg)
        except Exception as e:
            error_msg = f"Ошибка запуска конвертации: {e}"
            logger.error(error_msg, exc_info=True)
            self.conversion_error.emit(error_msg)
    
    def _monitor_progress(self):
        """Мониторинг прогресса с GPU информацией"""
        duration_pattern = re.compile(r'Duration: (\d{2}):(\d{2}):(\d{2})')
        time_pattern = re.compile(r'time=(\d{2}):(\d{2}):(\d{2})')
        speed_pattern = re.compile(r'speed=\s*(\d+\.?\d*)x')

        total_seconds = None
        stderr_lines = []

        try:
            for line in self.process.stderr:
                if self._should_stop:
                    logger.info("Конвертация остановлена пользователем")
                    self._terminate_process()
                    # Очищаем passlogfile при остановке
                    self._cleanup_passlogfiles()
                    return
                
                stderr_lines.append(line)
                
                # Получаем общую длительность
                if total_seconds is None:
                    duration_match = duration_pattern.search(line)
                    if duration_match:
                        h, m, s = map(int, duration_match.groups())
                        total_seconds = h * 3600 + m * 60 + s
                        logger.info(f"Длительность видео: {self._format_time(total_seconds)}")
                
                # Получаем текущее время обработки
                time_match = time_pattern.search(line)
                if time_match and total_seconds:
                    h, m, s = map(int, time_match.groups())
                    current_seconds = h * 3600 + m * 60 + s

                    # Расчет прогресса с учетом двухпроходного кодирования
                    pass_progress = int((current_seconds / total_seconds) * 100)
                    pass_progress = min(pass_progress, 100)

                    # Общий прогресс (для двухпроходного кодирования)
                    if self.total_passes == 2:
                        # Проход 1: 0-50%, Проход 2: 50-100%
                        if self.current_pass == 1:
                            overall_progress = int(pass_progress * 0.5)
                        else:  # current_pass == 2
                            overall_progress = int(50 + pass_progress * 0.5)
                    else:
                        overall_progress = pass_progress

                    # Расчет ETA
                    elapsed_time = time.time() - self._start_time
                    if current_seconds > 0:
                        # Для двухпроходного кодирования умножаем время на количество оставшихся проходов
                        estimated_pass_time = (elapsed_time / current_seconds) * total_seconds
                        if self.total_passes == 2 and self.current_pass == 1:
                            # Добавляем время на второй проход
                            estimated_total_time = estimated_pass_time * 2
                        else:
                            estimated_total_time = estimated_pass_time

                        remaining_time = max(0, estimated_total_time - elapsed_time)
                        eta_formatted = self._format_time(remaining_time)
                    else:
                        eta_formatted = "Рассчитывается..."

                    # Скорость из FFmpeg
                    speed_match = speed_pattern.search(line)
                    speed_str = speed_match.group(1) + 'x' if speed_match else "N/A"

                    # Отправка обновления прогресса
                    self.progress_updated.emit({
                        'progress': overall_progress,
                        'current_time': self._format_time(current_seconds),
                        'total_time': self._format_time(total_seconds),
                        'eta': eta_formatted,
                        'speed': speed_str,
                        'current_pass': self.current_pass,
                        'total_passes': self.total_passes
                    })
            
            # Проверка завершения
            self.process.wait()

            if self.process.returncode == 0:
                # Проверяем, есть ли второй проход
                if self.current_pass == 1 and self.pass2_command:
                    logger.info("Проход 1 завершен успешно. Начинаем проход 2...")
                    self.current_pass = 2
                    self._start_pass2()
                else:
                    elapsed = time.time() - self._start_time
                    logger.info(f"Конвертация успешно завершена за {self._format_time(elapsed)}")
                    # Очищаем passlogfile если двухпроходное кодирование завершено
                    self._cleanup_passlogfiles()
                    self.conversion_finished.emit()
            else:
                # Собираем последние строки ошибок
                error_lines = stderr_lines[-20:] if len(stderr_lines) > 20 else stderr_lines
                error_output = ''.join(error_lines)

                # Улучшенная обработка ошибок
                user_friendly_error = self._parse_error(error_output)
                logger.error(f"Конвертация завершилась с ошибкой (код {self.process.returncode}): {user_friendly_error}")
                # Очищаем passlogfile в случае ошибки
                self._cleanup_passlogfiles()
                self.conversion_error.emit(user_friendly_error)
                
        except Exception as e:
            error_msg = f"Ошибка мониторинга прогресса: {e}"
            logger.error(error_msg, exc_info=True)
            self.conversion_error.emit(error_msg)

    def _start_pass2(self):
        """Запуск второго прохода кодирования"""
        try:
            logger.info("Начало второго прохода")
            logger.debug(f"Полная команда прохода 2: {' '.join(self.pass2_command)}")

            self.process = subprocess.Popen(
                self.pass2_command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
                creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
            )

            self._monitor_progress()

        except Exception as e:
            error_msg = f"Ошибка запуска второго прохода: {e}"
            logger.error(error_msg, exc_info=True)
            self.conversion_error.emit(error_msg)

    def _parse_error(self, error_output: str) -> str:
        """Парсинг ошибок FFmpeg для пользователя"""
        error_output_lower = error_output.lower()
        
        # GPU ошибки
        if 'cuda' in error_output_lower and ('failed' in error_output_lower or 'error' in error_output_lower):
            return "Ошибка NVIDIA GPU. Проверьте драйверы NVIDIA и доступность CUDA."
        
        if 'qsv' in error_output_lower and 'cannot load' in error_output_lower:
            return "Ошибка Intel Quick Sync. Убедитесь, что драйверы Intel установлены и GPU доступен."
        
        if 'amf' in error_output_lower and 'failed' in error_output_lower:
            return "Ошибка AMD AMF. Проверьте драйверы AMD."
        
        if 'vaapi' in error_output_lower and ('failed' in error_output_lower or 'error' in error_output_lower):
            return "Ошибка VA-API. Проверьте поддержку VAAPI в системе."
        
        # Общие ошибки
        if 'no such file or directory' in error_output_lower:
            return "Файл не найден. Проверьте путь к входному файлу."
        
        if 'permission denied' in error_output_lower:
            return "Нет прав доступа. Проверьте права на файлы."
        
        if 'invalid' in error_output_lower and 'codec' in error_output_lower:
            return "Неверный кодек. Попробуйте другой формат или кодек."
        
        if 'disk full' in error_output_lower or 'no space' in error_output_lower:
            return "Недостаточно места на диске."
        
        # Возвращаем последнюю значимую строку
        lines = [l.strip() for l in error_output.split('\n') if l.strip()]
        for line in reversed(lines):
            if 'error' in line.lower() or 'failed' in line.lower():
                return line[:200]  # Ограничиваем длину
        
        return "Ошибка конвертации. Проверьте лог для деталей."
    
    def _format_time(self, seconds) -> str:
        """Форматирование времени"""
        if seconds is None or seconds < 0:
            return "00:00:00"
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def _cleanup_passlogfiles(self):
        """Очистка временных passlogfile файлов после двухпроходного кодирования"""
        if not self.passlogfile:
            return

        try:
            passlog_path = Path(self.passlogfile)
            # Удаляем основной файл и все связанные (.log, .log.mbtree, .log.temp и т.д.)
            for suffix in ['', '-0.log', '-0.log.mbtree', '-0.log.temp', '.log', '.log.mbtree', '.log.temp']:
                file_to_delete = Path(str(passlog_path) + suffix)
                if file_to_delete.exists():
                    file_to_delete.unlink()
                    logger.info(f"Удален временный passlogfile: {file_to_delete}")
        except Exception as e:
            logger.warning(f"Не удалось очистить passlogfile: {e}")

    def _terminate_process(self):
        """Безопасное завершение процесса FFmpeg"""
        if not self.process:
            return

        try:
            # Сначала пытаемся мягко завершить
            self.process.terminate()
            try:
                self.process.wait(timeout=2)
                logger.info("Процесс FFmpeg успешно завершен")
            except subprocess.TimeoutExpired:
                # Если процесс не завершился за 2 секунды, принудительно убиваем
                logger.warning("Процесс не завершился, принудительное завершение")
                self.process.kill()
                try:
                    self.process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    logger.error("Не удалось завершить процесс даже после kill()")
        except Exception as e:
            logger.error(f"Ошибка при завершении процесса: {e}")
        finally:
            # Закрываем pipes чтобы разблокировать чтение
            try:
                if self.process.stdout:
                    self.process.stdout.close()
                if self.process.stderr:
                    self.process.stderr.close()
                if self.process.stdin:
                    self.process.stdin.close()
            except Exception as e:
                logger.debug(f"Ошибка при закрытии pipes: {e}")

    def stop(self):
        """Остановка конвертации"""
        logger.info("Запрошена остановка конвертации")
        self._should_stop = True
        self._terminate_process()
        self._cleanup_passlogfiles()