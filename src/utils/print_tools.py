import logging
from datetime import datetime
import time

def print_remaining_time(target_time_str):
    """
    实时打印当前时间、目标时间和剩余时间在同一行。
    
    :param target_time_str: 预定时间字符串，格式为 "YYYY-MM-DD hh:mm:ss"
    """
    log = logging.getLogger(__name__)
    try:
        # 将预定时间字符串转换为 datetime 对象
        target_time = datetime.strptime(target_time_str, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        log.error("时间格式错误，请使用 'YYYY-MM-DD hh:mm:ss'")
        return
    
    log.info(f"啟用預定時間: {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    while True:
        # 获取当前时间
        now = datetime.now()
        # 计算剩余时间
        remaining_time = target_time - now
        # 格式化显示
        if remaining_time.total_seconds() > 0:
            print(
                f"\r當前時間: {now.strftime('%Y-%m-%d %H:%M:%S')} | 預定時間: {target_time.strftime('%Y-%m-%d %H:%M:%S')} | 剩餘時間: {str(remaining_time).split('.')[0]} ",
                end="",
                flush=True
            )
        else:
            print(
                f"\r當前時間: {now.strftime('%Y-%m-%d %H:%M:%S')} | 預定時間: {target_time.strftime('%Y-%m-%d %H:%M:%S')} | 剩餘時間: 已過期             ",
                end="",
                flush=True
            )
            break
        
        # 每秒更新一次
        time.sleep(1)
    log.info("時間已到，開始執行任務。")