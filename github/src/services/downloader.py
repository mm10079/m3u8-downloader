import os
import sys
import time
import json
import aiohttp
import asyncio
import aiofiles
import logging
import requests
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from src.utils import default_info
from src.app_types import common_types

log = logging.getLogger(__name__)

def set_logger(new_log):
    current_module = sys.modules[__name__]  # 取得 `c` 模組的引用
    setattr(current_module, "log", new_log)

class ThreadPoolManager:
    def __init__(self, max_threads):
        log.debug(f"初始化執行緒池，最大執行緒數量: {max_threads}")
        self.executor = ThreadPoolExecutor(max_workers=max_threads)

    def join(self, threads):
        log.debug("等待執行緒完成")
        for thread in as_completed(threads):
            thread.result()

    def shutdown(self):
        log.debug("關閉執行緒池")
        self.executor.shutdown(wait=True)

def lock():
    return threading.Lock()

def download_json(filepath, content):
    log.debug(f'儲存json檔案：{filepath}')
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(json.dumps(content, indent=4, ensure_ascii=False))

def download_file_by_url(url: str, filepath: str, cookies: dict | None = None, headers: dict | None=None, stream=True, retry_times=6, chunk_size=262144, timeout=30, size_check = True):
    if not filepath:
        log.error("檔案路徑無效！")
        return False
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    session = requests.Session()
    for attempt in range(1, retry_times + 1):
        if cookies:
            session.cookies.update(cookies)
        try:
            response = session.get(url, headers=headers, stream=stream, timeout=timeout)
            if response.status_code != 200:
                log.warning(f"HTTP 狀態碼錯誤: {response.status_code}，URL: {url}，嘗試次數: {attempt}")
                time.sleep(3)
                continue

            file_size = int(response.headers.get('Content-Length', 0))
            if file_size == 0:
                log.warning(f"伺服器返回空檔案，URL: {url}，嘗試次數: {attempt}")
                time.sleep(3)
                continue

            if os.path.exists(filepath):
                local_size = os.path.getsize(filepath)
                if size_check:
                    # 確認檔案大小一致
                    if local_size != file_size:
                        log.warning(f"檔案異常！檔案路徑: {filepath}")
                        log.warning(f"檔案大小不匹配！伺服器大小: {file_size}，本地大小: {local_size}，嘗試次數: {attempt}")
                        os.remove(filepath)
                    else:
                        log.info(f"檔案已存在: {filepath}，大小: {local_size / 1024 / 1024:.2f} MB")
                        response.close()
                        return True
                else:
                    log.info(f"檔案已存在: {filepath}，跳過檔案大小檢查")
                    response.close()
                    return True

            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=chunk_size):
                    if chunk:  # 避免空內容
                        f.write(chunk)
            
            local_size = os.path.getsize(filepath)
            if size_check:
                # 確認檔案大小一致
                if local_size != file_size:
                    log.warning(f"檔案異常！檔案路徑: {filepath}")
                    log.warning(f"檔案大小不匹配！伺服器大小: {file_size}，本地大小: {local_size}，嘗試次數: {attempt}")
                    os.remove(filepath)
                    time.sleep(3)
                    continue

            log.info(f"下載成功: {filepath}，大小: {local_size / 1024 / 1024:.2f} MB")
            return True

        except Exception as e:
            log.warning(f"下載時發生其他錯誤: {e}，嘗試次數: {attempt}")
            time.sleep(3)

    log.error(f"下載失敗，URL: {url}")
    return False

async def async_download(url: str, filepath: str, session: aiohttp.ClientSession, retry_times=3, chunk_size=262144, timeout=10, size_check = True, log_fullpath=False):
    if not filepath:
        log.error("檔案路徑無效！")
        return False
    timeout_context = aiohttp.ClientTimeout(total=timeout)
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    log_file = filepath if log_fullpath else filepath.split(os.path.sep)[-1]
    for attempt in range(1, retry_times + 1):
        try:
            async with session.get(url, timeout=timeout_context) as response:
                if response.status != 200:
                    log.warning(f"HTTP 狀態碼錯誤: {response.status}，URL: {url}，嘗試次數: {attempt}")
                    await asyncio.sleep(3)
                    continue

                file_size = int(response.headers.get('Content-Length', 0))
                if file_size == 0:
                    log.warning(f"伺服器返回空檔案，URL: {url}，嘗試次數: {attempt}")
                    await asyncio.sleep(3)
                    continue

                if os.path.exists(filepath):
                    local_size = os.path.getsize(filepath)
                    if size_check:
                        # 確認檔案大小一致
                        if local_size != file_size:
                            log.warning(f"檔案異常！移除檔案: {log_file}")
                            log.warning(f"檔案大小不匹配！伺服器大小: {file_size}，本地大小: {local_size}，嘗試次數: {attempt}")
                            os.remove(filepath)
                        else:
                            log.info(f"檔案已存在: {log_file}，符合大小: {local_size / 1024 / 1024:.2f} MB")
                            response.close()
                            return True
                    else:
                        log.info(f"檔案已存在: {filepath}，跳過檔案大小檢查")
                        response.close()
                        return True

                async with aiofiles.open(filepath, 'wb') as f:
                    async for chunk in response.content.iter_chunked(chunk_size):
                        if chunk:  # 避免空內容
                            await f.write(chunk)
                
                local_size = os.path.getsize(filepath)
                if size_check:
                    # 確認檔案大小一致
                    if local_size != file_size:
                        log.warning(f"檔案異常！移除檔案: {log_file}")
                        log.warning(f"檔案大小不匹配！伺服器大小: {file_size}，本地大小: {local_size}，嘗試次數: {attempt}")
                        await asyncio.sleep(3)
                        os.remove(filepath)
                        continue

            log.info(f"下載成功: {log_file}，大小: {local_size / 1024 / 1024:.2f} MB")
            return True
        except asyncio.TimeoutError:
            log.warning(f"下載超時，URL: {url}，嘗試次數: {attempt}")
        except Exception as e:
            log.warning(f"下載時發生其他錯誤: {e}，嘗試次數: {attempt}")
        await asyncio.sleep(1)
        if os.path.exists(filepath):
            os.remove(filepath)
        await asyncio.sleep(3)

    log.error(f"下載失敗，URL: {url}")
    return False


async def downlaod_attachment(attachments: common_types.AttachmentInfo, output_path: str, referer: str, cookies: dict[str, str] | None) -> None:
    task = []
    headers = {
        'User-Agent': default_info.DEFAULT_USER_AGENT,
        'Referer': referer
    }

    session = aiohttp.ClientSession(headers=headers, cookies=cookies)
    for name, info in attachments.files.items():
        if name == 'driver':
            continue
        folder = os.path.join(output_path, info.folder)
        os.makedirs(folder, exist_ok=True)

        if isinstance(info.file, list) or isinstance(info.file, dict):
            with open(os.path.join(folder, name), 'w', encoding='utf-8') as f:
                json.dump(info.file, f, indent=4, ensure_ascii=False)

        elif isinstance(info.file, str):
            if 'http' in info.file.split(':')[0]:
                task.append(async_download(info.file, os.path.join(folder, name), session, size_check=False, log_fullpath=True))
            
            else:
                with open(os.path.join(folder, name), 'w', encoding='utf-8') as f:
                    f.write(info.file)

        elif isinstance(info.file, bytes):
            with open(os.path.join(folder, name), 'wb') as f:
                f.write(info.file)

    await asyncio.gather(*task)
    await session.close()

if __name__ == '__main__':
    pass
    #import logger
    #log = logger.setup_logging()
    #m3u8_url = 'https://prod-fastly-ap-northeast-1.video.pscp.tv/Transcoding/v1/hls/nNboUoeqSj7r94pwe8NIuXBvgJ6IWy5eVTyUq61KqSY18bqIM-_992t1prDwHlOUy9PkFwO6qfrsIPfJimLfyw/non_transcode/ap-northeast-1/periscope-replay-direct-prod-ap-northeast-1-public/audio-space/master_playlist.m3u8'
    #DEFAULT_USER_AGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/'
    #headers = {
    #    'User-Agent': DEFAULT_USER_AGENT,
    #    'Referer': 'https://x.com',
    #}
    #cookies_path = os.path.join(os.getcwd(), 'cookies.txt')
    #grab_m3u8 = m3u8.get_media_m3u8(m3u8_url, 0, None, headers)
    #print(json.dumps(grab_m3u8.get_master_playlist(), indent=4, ensure_ascii=False))
    #media_playlist_info = grab_m3u8.update_media_playlist()
    #print(grab_m3u8.media_playlist_content)