# -*- coding: utf-8 -*-
import os
import time
import signal
import asyncio
import logging
import pkgutil
import threading
import importlib
from concurrent.futures import ThreadPoolExecutor

from src.app_types import params
from src.utils import set_cookies, default_info
from src.config import logger, setting
from src.services import downloader, driver_tools, m3u8_downloader
from src.app_types import common
import src.web_modules
from src import __description__

log = logging.getLogger(__name__)

stop_flag = threading.Event()

def signal_handler(sig, frame):
    log.warning("📴 收到 Ctrl+C 中斷訊號")
    stop_flag.set()

signal.signal(signal.SIGINT, signal_handler)

def web_graber(config: params.WebParams) -> common.Mission:
    # 初始化網頁解析器
    log.info(f'初始網址：\"{config.url}\"')

    if '.m3u8' in config.url:
        if config.referer:
            referer = config.referer
        else:
            for keyword in default_info.Common_Referers.keys():
                if keyword in config.url:
                    referer = default_info.Common_Referers[keyword]
                    break
        m3u8_info = common.M3U8Info(
            url=config.url,
            filename=config.title,
            folder=config.title,
            referer=referer,
            user_agent=config.user_agent,
            cookies=config.cookies,
            full_download=config.full_download,
        )
        download_info = common.Mission([m3u8_info], None)
    else:
        # 如果網址不為m3u8文件，則進行網頁解析
        if config.url:
            # 如果有提供網址，則直接進入網址
            base_driver = driver_tools.new(config.chrome_path, config.headless)
            base_driver.get(config.url)
        else:
            base_driver = driver_tools.new(config.chrome_path)
            log.info('未提供網址，請手動進入帶有m3u8文件的網址')
        # 下載資訊檢測區塊
        log.info('開始尋找m3u8文件，如果你已到播放間或Space空間但沒檢測到m3u8文件，請手動刷新幾次網頁')
        download_info = None # type: ignore
        skip_urls = set(config.skip_urls)
        models = []
        for _, module_name, _ in pkgutil.iter_modules(src.web_modules.__path__):
            if module_name != "nonspecific" and module_name != "__init__":
                models.append(f"src.web_modules.{module_name}")
        models.append("src.web_modules.nonspecific")
        while download_info is None:
            # 檢測網址是否為特定模塊，如有則執行對應模塊
            for model in models:
                module = importlib.import_module(model)
                download_info: common.Mission = module.main(base_driver, config, skip_urls)
                if download_info is not None:
                    break
            if download_info is None:
                time.sleep(0.8)
    return download_info

def download(config: params.WebParams, mission: common.Mission) -> None:
    # 下載m3u8文件
    if config.media:
        with ThreadPoolExecutor(max_workers=config.threads_limit) as executor:
            threadPool = []
            lock = threading.Lock()
            name_length = max(len(m3u8_info.filename) for m3u8_info in mission.m3u8s)
            for m3u8_info in mission.m3u8s:
                m3u8_info.order = config.quantity
                output_path = os.path.join(config.output_path, m3u8_info.folder)
                dl_mission = m3u8_downloader.m3u8_downloader(
                    m3u8_info= m3u8_info,
                    merge_lock= lock,
                    convert_tool= config.tool_path,
                    output_path= output_path,
                    decrypt= config.decrypt,
                    full_download=config.full_download,
                    stop_flag=stop_flag
                )
                thread = executor.submit(dl_mission.main, name_length)
                log.info(f'開始下載m3u8文件：\"{m3u8_info.url}\"')
                threadPool.append(thread)
            try:
                while any(not t.done() for t in threadPool):
                    time.sleep(1)
            except KeyboardInterrupt:
                log.warning('🛑 捕捉到 Ctrl+C，設定 stop_flag，等待任務自行停止...')
                # 不要立即取 result()，讓任務能優雅完成
                stop_flag.set()
                while any(not t.done() for t in threadPool):
                    time.sleep(1)
            finally:
                # 確保所有 future 拋出的 exception 被處理掉，避免程式 hang 在這裡
                for future in threadPool:
                    try:
                        future.result(timeout=1)
                    except Exception as e:
                        log.error(f'任務異常終止：{e}')
    if config.attachment and mission.attachments:
        source_cookies = mission.attachments.cookies
        cookies = set_cookies.load_cookies_to_dict(source_cookies)
        task = downloader.downlaod_attachment(
            mission.attachments,
            config.output_path,
            source_cookies.current_url if isinstance(source_cookies, driver_tools.webdriver.Chrome) else config.url,
            cookies
            )
        asyncio.run(task)

if __name__ == '__main__':
    config = setting.get_config()
    log = logger.set_log_config()

    log.info(__description__)
    download_info = web_graber(config)
    download(config, download_info)
    log.info('下載完成')