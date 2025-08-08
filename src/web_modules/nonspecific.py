import logging
from selenium import webdriver

from src.services import gui
from src.app_types import common, params
from src.services import driver_tools
from src.utils import default_info, path

log = logging.getLogger(__name__)


def main(driver: webdriver.Chrome, config: params.AllParams, abandoned_m3u8s: set) -> common.Mission | None:
    # 沒有模塊則採用隨時檢測m3u8文件
    m3u8s = []
    for m3u8_url in driver_tools.get_m3u8_link(driver, abandoned_m3u8s):
        if m3u8_url in abandoned_m3u8s:
            continue
        log.info(f'找到m3u8文件：\"{m3u8_url}\"')
        if gui.ask_download(m3u8_url):
            title = path.sanitize_windows_path(config.title) if config.title else m3u8_url.split('.')[0].split('/')[-1]
            if len(m3u8s) > 1:
                title += f'_{len(m3u8s)}'

            m3u8_info = common.M3U8Info(
                url=m3u8_url,
                filename=title,
                folder=title,
                referer=driver.current_url,
                user_agent=config.user_agent,
                cookies=driver,
            )
            m3u8s.append(m3u8_info)
        else:
            log.info(f'已忽略m3u8文件：\"{m3u8_url}\"')
            abandoned_m3u8s.add(m3u8_url)
    return common.Mission(m3u8s, None) if m3u8s else None