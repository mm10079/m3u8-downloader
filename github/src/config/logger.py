from datetime import datetime
import os
import sys
import time
import logging
import threading


def get_time():
    return datetime.now().strftime("%Y-%m-%d %H：%M：%S")

class ThreadLogFilter(logging.Filter):
    """
    This filter only show log entries for specified thread name
    """

    def __init__(self, thread_name, *args, **kwargs):
        logging.Filter.__init__(self, *args, **kwargs)
        self.thread_name = thread_name

    def filter(self, record):
        return record.threadName == self.thread_name


def start_thread_logging(log_file):
    """
    Add a log handler to separate file for current thread
    """
    thread_name = threading.Thread.getName(threading.current_thread())
    log_handler = logging.FileHandler(log_file)

    log_handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter(
        "%(asctime)-15s"
        " - %(module)-11s"
        " - %(levelname)-8s"
        " - %(message)s")
    log_handler.setFormatter(formatter)

    log_filter = ThreadLogFilter(thread_name)
    log_handler.addFilter(log_filter)

    logger = logging.getLogger()
    logger.addHandler(log_handler)

    return log_handler


def stop_thread_logging(log_handler):
    # Remove thread log handler from root logger
    logging.getLogger().removeHandler(log_handler)

    # Close the thread log handler so that the lock on log file can be released
    log_handler.close()

def setup_logging(name=__name__, log_file=None, level=logging.DEBUG):
    log = logging.getLogger(name)
    log.setLevel(level)  # 設定日誌層級
    
    # 清除現有處理器（防止重複添加）
    if log.hasHandlers():
        log.handlers.clear()
    
    # 添加文件日誌處理器
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
        log.addHandler(file_handler)  # 直接添加處理器
    
    return log

def set_log_config(name="Main", level=logging.DEBUG):
    
    # 設置基本配置
    logging.basicConfig(
        level=level,
        format='%(asctime)s | %(levelname)-8s | %(module)-11s.%(funcName)-22s:%(lineno)-4d | %(threadName)s | %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    
    # 設置第三方日誌層級
    logging.getLogger('requests').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('socketserver').setLevel(logging.WARNING)
    logging.getLogger('selenium').setLevel(logging.WARNING)
    logging.getLogger('socket').setLevel(logging.WARNING)
    logging.getLogger('http').setLevel(logging.WARNING)
    
    log = logging.getLogger(name)
    return log
