import threading
import time
import ctypes
from typing import Dict
import logging
from logger import app_logger

class TaskCleaner:
    def __init__(self, tasks: Dict, timeout: int = 300):  # 300 seconds = 5 minutes
        self.tasks = tasks
        self.timeout = timeout
        self.task_timestamps: Dict[str, float] = {}
        self.task_threads: Dict[str, threading.Thread] = {}  # Track task threads
        self.running = False
        self.cleaner_thread = None
        self.lock = threading.Lock()

    def start(self):
        """Start the cleaner thread."""
        self.running = True
        self.cleaner_thread = threading.Thread(target=self._clean_loop)
        self.cleaner_thread.daemon = True
        self.cleaner_thread.start()
        app_logger.info("Task cleaner started")

    def stop(self):
        """Stop the cleaner thread."""
        self.running = False
        if self.cleaner_thread:
            self.cleaner_thread.join()
        app_logger.info("Task cleaner stopped")

    def add_task(self, task_id: str, thread: threading.Thread):
        """Register a new task with current timestamp and its thread."""
        with self.lock:
            self.task_timestamps[task_id] = time.time()
            self.task_threads[task_id] = thread
        app_logger.info(f"Added task {task_id} to cleaner")

    def remove_task(self, task_id: str):
        """Remove a task from monitoring."""
        with self.lock:
            self.task_timestamps.pop(task_id, None)
            self.task_threads.pop(task_id, None)
        app_logger.info(f"Removed task {task_id} from cleaner")

    def _terminate_thread(self, thread: threading.Thread):
        """Forcefully terminate a thread."""
        if not thread.is_alive():
            return

        exc = ctypes.py_object(SystemExit)
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
            ctypes.c_long(thread.ident), exc)
        if res > 1:
            # If it fails, reset the state
            ctypes.pythonapi.PyThreadState_SetAsyncExc(
                ctypes.c_long(thread.ident), None)
            app_logger.error("Failed to terminate thread")

    def _clean_loop(self):
        """Main cleaning loop that checks for timed out tasks."""
        while self.running:
            current_time = time.time()
            to_remove = []

            with self.lock:
                for task_id, start_time in self.task_timestamps.items():
                    if current_time - start_time > self.timeout:
                        if task_id in self.tasks:
                            self.tasks[task_id]['status'] = 'error'
                            self.tasks[task_id]['value'] = 'timeout'
                            # Terminate the associated thread
                            if task_id in self.task_threads:
                                thread = self.task_threads[task_id]
                                self._terminate_thread(thread)
                                app_logger.warning(f"Terminated thread for task {task_id}")
                            app_logger.warning(f"Task {task_id} timed out after {self.timeout} seconds")
                        to_remove.append(task_id)

                for task_id in to_remove:
                    self.task_timestamps.pop(task_id, None)
                    self.task_threads.pop(task_id, None)

            time.sleep(1)  # Check every second
