# -*- coding: utf-8 -*-
import os
import time
import asyncio
import logging
import threading
import importlib
import pkgutil

from src.utils import set_cookies, default_info
from src.config import logger, setting
from src.services import downloader, driver_tools, m3u8_downloader
from src.app_types import common_types
import src.web_modules

log = logging.getLogger(__name__)


def web_graber(config: dict) -> common_types.Mission:
    # 初始化網頁解析器
    log.info(f'初始網址：\"{config["url"]}\"')

    if '.m3u8' in config["url"]:
        if config["referer"]:
            referer = config["referer"]
        else:
            for keyword in default_info.Common_Referers.keys():
                if keyword in config["url"]:
                    referer = default_info.Common_Referers[keyword]
                    break
        m3u8_info = common_types.M3U8Info(
            url=config["url"],
            filename=config["title"],
            folder=config["title"],
            referer=referer,
            user_agent=(config["user_agent"] or default_info.DEFAULT_USER_AGENT),
            cookies=config["cookies_path"],
            full_download=config["full_download"],
        )
        download_info = common_types.Mission([m3u8_info], None)
    else:
        # 如果網址不為m3u8文件，則進行網頁解析
        if config["url"]:
            # 如果有提供網址，則直接進入網址
            base_driver = driver_tools.new(config["chrome_path"], config["headless"])
            base_driver.get(config["url"])
        else:
            base_driver = driver_tools.new(config["chrome_path"])
            log.info('未提供網址，請手動進入帶有m3u8文件的網址')
        # 下載資訊檢測區塊
        log.info('開始尋找m3u8文件，如果你已到播放間或Space空間但沒檢測到m3u8文件，請手動刷新幾次網頁')
        download_info = None # type: ignore
        abandoned_m3u8s = set()
        models = []
        for _, module_name, _ in pkgutil.iter_modules(src.web_modules.__path__):
            if module_name != "nonspecific" and module_name != "__init__":
                models.append(f"src.web_modules.{module_name}")
        models.append("src.web_modules.nonspecific")
        while download_info is None:
            # 檢測網址是否為特定模塊，如有則執行對應模塊
            for model in models:
                module = importlib.import_module(model)
                download_info: common_types.Mission = module.main(base_driver, config, abandoned_m3u8s)
                if download_info is not None:
                    break
            if download_info is None:
                time.sleep(0.8)
    return download_info

def download(config: dict, mission: common_types.Mission) -> None:
    # 下載m3u8文件
    if config["media"]:
        ThreadPoolManager = downloader.ThreadPoolManager(config['threads_limit'])
        lock = threading.Lock()
        futures = []
        name_length = max(len(m3u8_info.filename) for m3u8_info in mission.m3u8s)
        for m3u8_info in mission.m3u8s:
            m3u8_info.order = config["quantity"]
            output_path = os.path.join(config['output_path'], m3u8_info.folder)
            dl_mission = m3u8_downloader.m3u8_downloader(
                m3u8_info= m3u8_info,
                merge_lock= lock,
                convert_tool= config["tool_path"],
                output_path= output_path,
                decrypt= config["decrypt"]
            )
            thread = ThreadPoolManager.executor.submit(dl_mission.main, name_length)
            log.info(f'開始下載m3u8文件：\"{m3u8_info.url}\"')
            futures.append(thread)

        ThreadPoolManager.join(futures)
        ThreadPoolManager.shutdown()
    if config["attachment"] and mission.attachments:
        source_cookies = mission.attachments.cookies
        cookies = set_cookies.load_cookies_to_dict(source_cookies)
        task = downloader.downlaod_attachment(
            mission.attachments,
            config["output_path"],
            source_cookies.current_url if isinstance(source_cookies, driver_tools.webdriver.Chrome) else config["url"],
            cookies
            )
        asyncio.run(task)

if __name__ == '__main__':
    config = setting.get_config('web')
    log = logger.set_log_config()

    log.info(config['opening_message'])
    download_info = web_graber(config)
    download(config, download_info)
    log.info('下載完成')