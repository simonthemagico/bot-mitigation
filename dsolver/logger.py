import os
import logging
from datetime import datetime
from config import current_dir

# Create logs directory if it doesn't exist
LOGS_DIR = os.path.join(current_dir, 'logs')
if not os.path.exists(LOGS_DIR):
    os.makedirs(LOGS_DIR)

# Configure general application logger
app_logger = logging.getLogger('dsolver')
app_logger.setLevel(logging.INFO)

# Create general log file handler
general_log_path = os.path.join(LOGS_DIR, 'dsolver.log')
general_handler = logging.FileHandler(general_log_path)
general_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
app_logger.addHandler(general_handler)

def get_task_logger(task_id: str) -> logging.Logger:
    """Create or get a logger for a specific task.

    If a logger with the given task_id already exists,
    return it instead of creating a new one.
    """
    logger_name = f'dsolver.task.{task_id}'
    logger = logging.getLogger(logger_name)
    if logger.handlers:
        return logger

    # Create task-specific directory with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Create task-specific stream handler
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s'
    ))
    logger.addHandler(handler)

    return logger
