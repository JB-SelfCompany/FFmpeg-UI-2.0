import os
import time
import logging
from pathlib import Path
from typing import List
from PySide6.QtCore import QObject, Signal

logger = logging.getLogger(__name__)


class BatchJob:
    """Задача для batch конвертации"""

    def __init__(self, input_file: str, output_file: str, command: List[str], pass2_command: List[str] = None, passlogfile: str = None):
        self.input_file = input_file
        self.output_file = output_file
        self.command = command
        self.pass2_command = pass2_command
        self.passlogfile = passlogfile
        self.status = "pending"  # pending, processing, completed, failed
        self.error = None


class BatchProcessor(QObject):
    """Процессор batch конвертации с правильной асинхронностью"""
    
    job_started = Signal(int, str)  # index, filename
    job_completed = Signal(int, str)  # index, filename
    job_failed = Signal(int, str, str)  # index, filename, error
    job_progress = Signal(int, dict)  # index, progress_data
    all_jobs_completed = Signal()
    progress_updated = Signal(int, int)  # current, total
    
    def __init__(self):
        super().__init__()
        self.jobs: List[BatchJob] = []
        self.current_job_index = -1
        self._should_stop = False
        
    def add_job(self, input_file: str, output_file: str, command: List[str], pass2_command: List[str] = None, passlogfile: str = None):
        """Добавить задачу в очередь"""
        job = BatchJob(input_file, output_file, command, pass2_command, passlogfile)
        self.jobs.append(job)
        
    def clear_jobs(self):
        """Очистить все задачи"""
        self.jobs.clear()
        self.current_job_index = -1
        
    def get_jobs_count(self) -> int:
        """Получить количество задач"""
        return len(self.jobs)
    
    def get_job(self, index: int) -> BatchJob:
        """Получить задачу по индексу"""
        if 0 <= index < len(self.jobs):
            return self.jobs[index]
        return None
        
    def process_all(self):
        """Обработать все задачи с правильной асинхронностью"""
        from core.conversion_engine import ConversionEngine
        from PySide6.QtCore import QEventLoop, QTimer
        
        self._should_stop = False
        total_jobs = len(self.jobs)
        
        for index, job in enumerate(self.jobs):
            if self._should_stop:
                break
                
            self.current_job_index = index
            job.status = "processing"
            
            # Сигнал о начале задачи
            filename = Path(job.input_file).name
            self.job_started.emit(index, filename)
            self.progress_updated.emit(index + 1, total_jobs)
            
            try:
                # Создаем новый движок конвертации для каждой задачи
                engine = ConversionEngine(job.command, job.pass2_command, job.passlogfile)
                
                # Флаг завершения
                conversion_finished = False
                conversion_error = None
                
                # Обработчики событий
                def on_finished():
                    nonlocal conversion_finished
                    conversion_finished = True
                    
                def on_error(error):
                    nonlocal conversion_finished, conversion_error
                    conversion_finished = True
                    conversion_error = error
                    
                def on_progress(progress_data):
                    # Передаем прогресс текущей задачи
                    self.job_progress.emit(index, progress_data)
                
                # Подключаем сигналы
                engine.conversion_finished.connect(on_finished)
                engine.conversion_error.connect(on_error)
                engine.progress_updated.connect(on_progress)
                
                # Запускаем конвертацию в отдельном потоке
                from PySide6.QtCore import QThread
                
                engine_thread = QThread()
                engine.moveToThread(engine_thread)
                engine_thread.started.connect(engine.start)
                engine_thread.start()
                
                # Ждем завершения с обработкой событий
                loop = QEventLoop()
                timer = QTimer()
                timer.timeout.connect(lambda: None)  # Просто обработка событий
                timer.start(100)  # Проверка каждые 100ms
                
                while not conversion_finished and not self._should_stop:
                    loop.processEvents()
                    time.sleep(0.05)  # Небольшая задержка для снижения CPU usage

                timer.stop()

                # Если остановлено пользователем, останавливаем engine
                if self._should_stop and engine:
                    engine.stop()

                # Корректно останавливаем поток
                if engine_thread.isRunning():
                    engine_thread.quit()
                    if not engine_thread.wait(5000):  # Ждем до 5 секунд
                        logger.warning(f"Поток batch job {index} не завершился, принудительное завершение")
                        engine_thread.terminate()
                        engine_thread.wait()

                if self._should_stop:
                    break
                
                # Проверка результата
                if conversion_error:
                    job.status = "failed"
                    job.error = conversion_error
                    self.job_failed.emit(index, filename, conversion_error)
                else:
                    job.status = "completed"
                    self.job_completed.emit(index, filename)
                    
            except Exception as e:
                job.status = "failed"
                job.error = str(e)
                self.job_failed.emit(index, filename, str(e))
        
        # Все задачи завершены
        if not self._should_stop:
            self.all_jobs_completed.emit()
            
    def stop(self):
        """Остановить обработку"""
        self._should_stop = True