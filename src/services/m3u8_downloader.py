import re
import os
import sys
import aiohttp
import asyncio
import logging
import threading
import subprocess
from selenium import webdriver

from src.app_types import common
from src.services import share, decrypt, downloader, m3u8_graber
from src.config import logger
from src.utils import set_cookies, default_info

log = logging.getLogger(name=__name__)

def set_logger(new_log):
    current_module = sys.modules[__name__]  # 取得 `c` 模組的引用
    setattr(current_module, "log", new_log)

def get_last_number(string: str) -> str|None:
    # 匹配所有數字組
    matches = re.findall(r'\d+', string)
    if matches:
        last_number = matches[-1]  # 找到最後一個數字組
        return last_number
    return None

def get_format_text(filepath: str, replacement: str) -> common.FormatText:
    """ return (fill, format_string) """
    # 獲取最後一個數字組並進行替換，需要避免抓取到mp4之類的檔名
    filepath_info = filepath.split('?')[0].split('/')
    filename = filepath_info[-1]
    ext = os.path.splitext(filename)[1]
    filename = filename[:filename.rfind(ext)]
    matches = get_last_number(filename)
    result = common.FormatText()
    if matches is not None:
        replaced_string = re.sub(rf'{re.escape(matches)}(?=\D*$)', replacement, filename, count=1)
        format_path = '/'.join(filepath_info[:-1]) + f'/{replaced_string}{ext}'
        if '0' == matches[0] and len(matches) > 1:
            result.fill = len(matches)
            result.text = format_path
        result.text = format_path
    return result


################################################################
class FindStartFile:
    def __init__(self, format_url:str, fill:int, session: aiohttp.ClientSession, split_times:int=10, space:int=10000):
        self.format_url = format_url
        self.fill = fill
        self.session = session
        self.split_times = split_times
        self.space = space
        self.lowest_value = None

    async def check_status(self, value:int):
        """檢查網址是否有效"""
        if value == self.lowest_value:
            return True
        url = self.format_url.format(num=str(value).zfill(self.fill))
        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    log.debug(f"檢查網址有效：{url}")
                    self.lowest_value = min(self.lowest_value, value) if self.lowest_value is not None else value
                    return True
                log.debug(f"檢查網址無效：{url} - {response.status}")
                return False
        except aiohttp.ClientError as e:
            log.warning(f"檢查網址無效：{url} - {str(e)}")
            return False
        except Exception as e:
            log.warning(f"檢查網址無效：{url} - {str(e)}")
            return False

    def create_tasks(self, value:int, space:int=10000):
        """創建檢查網址的任務列表，從value開始，向下每步進space，到limit次數，檢查網址是否有效"""
        tasks = []
        for num in range(max(0, value - space*self.split_times), value, space):
            tasks.append(self.check_status(num))
        return tasks

    async def part_search(self, value:int):
        """逐步減少檢查範圍，直到找到最小的有效值"""
        tasks = []
        now_space = self.space
        while True:
            tasks = self.create_tasks(value, now_space)
            await asyncio.gather(*tasks)
            if now_space == 1:
                break
            now_space //= 10
            if self.lowest_value is not None:
                value = min(self.lowest_value, value)
                log.info(f"此輪測試間距：{now_space}，當前最小值：{value}")
            if self.lowest_value == 0:
                break

    async def main(self, value: int) -> int:
        log.info(f"開始追朔已結束的碎片")
        await self.part_search(value)
        if self.lowest_value is not None:
            log.info(f"最終找到的最小有效值：{self.lowest_value}")
            return self.lowest_value
        raise ValueError("無法找到有效的檔案網址")

# 取得格式化連結
def get_format_file_url(base_url:str, first_file: str, second_file: str) -> common.FormatInfo:
    """
    base_url: 基本網址 配合前面m3u8的media_patch_url
    找出兩個檔案中參數不同的部分，替換成{num}
    """
    result = common.FormatInfo()
    # 分離副檔名，副檔名包含數字導致錯誤替換
    file_format_info = get_format_text(first_file, '{num}')
    if not file_format_info.text:
        log.error(f'無法解析的檔案名稱:{first_file}')
        return result

    second_file_name = get_format_text(second_file, '{num}').text
    if file_format_info.text != second_file_name:
        log.error(f'無法回朔檔案命名方式，名稱1：\"{file_format_info.text}\" | 名稱2：\"{second_file_name}\"')
        return result
    
    format_url = base_url + f'{file_format_info.text}'
    if '?' in first_file:
        format_url += '?'
        arg1 = first_file.split('?')[-1].split('&')
        arg2 = second_file.split('?')[-1].split('&')
        for n in range(len(arg1)):
            if arg1[n] != arg2[n]:
                # 檢測到參數不同，則替換數字組
                format_url += arg1[n].split('=')[0] + '=' + '{num}' + '&'
            elif arg1[n]:
                format_url += arg1[n] + '&'
        if format_url[-1] == '&':
            format_url = format_url[:-1]
    log.info(f'取得格式化連結：{format_url}')
    return common.FormatInfo(url=format_url, fill=file_format_info.fill)


################################################################

def convert_m3u8_to_media(m3u8_url, output_path, tool):
    if '.ts' in output_path:
        log.info(f"重新封裝MPEG-TS至MP4容器：{output_path}")
        output_path = os.path.splitext(output_path)[0] + '.mp4'
    command = f'\"{tool}\" -hwaccel auto -analyzeduration 100M -probesize 50M -i \"{m3u8_url}\" -c copy \"{output_path}\"'
    log.debug(command)
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, shell=True) as process:
        if process.stdout is not None:
            for line in process.stdout:
                print(line.strip())
        else:
            log.error("ffmpeg無法獲取輸出")

################################################################
# 下載區塊
class m3u8_downloader:
    def __init__(self, stop_flag: threading.Event, m3u8_info: common.M3U8Info, merge_lock: threading.Lock, convert_tool="ffmpeg.exe", output_path="output", decrypt=False, full_download: bool= False):
        self.m3u8_info = m3u8_info
        self.merge_lock = merge_lock
        self.convert_tool = convert_tool
        self.output_path = output_path
        self.decrypt = decrypt
        self.full_download = full_download
        self.stop_flag = stop_flag
        
        self.key = None
        self.tasks: set[asyncio.Task] = set()
        self.semaphore = asyncio.Semaphore(10)
        self.files_status = {}

        self._original_loop = asyncio.get_event_loop()
        self.loop: asyncio.AbstractEventLoop = asyncio.new_event_loop()

    def prepare(self):
        asyncio.set_event_loop(self.loop)
        self.headers = {
            'User-Agent': (self.m3u8_info.user_agent or default_info.DEFAULT_USER_AGENT),
            'Referer': (self.m3u8_info.referer or '')
        }
        self.update_cookies()

        self.m3u8_graber = m3u8_graber.get_media_m3u8(
            self.m3u8_info.url,
            self.m3u8_info.order,
            self.m3u8_info.cookies,
            self.headers
            )
        self.m3u8_graber.update_master_playlist()
        if not self.m3u8_graber.update_media_playlist():
            raise Exception("初始化失敗，無法更新媒體播放清單")
        self.create_folder()

    def create_folder(self):
        '''初始化資料夾 含碎片與碎片解析'''
        os.makedirs(self.output_path, exist_ok=True)
        n = 1
        self.backup_folder = os.path.join(self.output_path, 'backup', self.m3u8_info.filename)
        #if os.path.exists(self.backup_folder):
        #    while True:
        #        self.backup_folder = os.path.join(self.output_path, 'backup', self.m3u8_info.filename + f'_{n}')
        #        if not os.path.exists(self.backup_folder):
        #            break
        #        n += 1
        os.makedirs(self.backup_folder, exist_ok=True)
        self.fragment_folder = os.path.join(self.backup_folder, 'fragments')
        log.info(f'碎片檔、KEY、完整M3U8將儲存於：\"{self.fragment_folder}\"')
        os.makedirs(self.fragment_folder, exist_ok=True)
        if self.decrypt and self.m3u8_graber.media_playlist_info.key_url:
            self.decrypted_folder = os.path.join(self.backup_folder, 'decrypt')
            os.makedirs(self.decrypted_folder, exist_ok=True)

    def update_cookies(self):
        '''更新 cookies'''
        log.info(f"更新Cookies")
        self.cookies = set_cookies.load_cookies_to_dict(self.m3u8_info.cookies)

    def write_source_m3u8(self):
        try:
            if self.m3u8_graber.master_playlist_url:
                master_playlist_content = self.m3u8_graber.get_master_playlist()
                if master_playlist_content:
                    filepath = os.path.join(self.backup_folder, self.m3u8_graber.master_playlist_url.split('?')[0].split('/')[-1])
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(master_playlist_content.replace('\n\n', '\n'))
            filepath = os.path.join(self.backup_folder, self.m3u8_graber.media_playlist_url.split('?')[0].split('/')[-1])
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(self.m3u8_graber.media_playlist_content.replace('\n\n', '\n'))
        except Exception as e:
            log.error(f'下載m3u8時發生錯誤\n{e}')

    async def download_map(self):
        '''下載MAP'''
        if 'http' in self.m3u8_graber.media_playlist_info.map_url:
            url = self.m3u8_graber.media_playlist_info.map_url
        else:
            url = self.m3u8_graber.media_patch_url + self.m3u8_graber.media_playlist_info.map_url
        filepath = os.path.join(self.fragment_folder, os.path.basename(url.split('?')[0]))
        await downloader.async_download(url, filepath, self.session, size_check=False)

    async def download_key(self):
        '''下載金鑰'''
        if 'http' in self.m3u8_graber.media_playlist_info.key_url:
            url = self.m3u8_graber.media_playlist_info.key_url
        else:
            url = self.m3u8_graber.media_patch_url + self.m3u8_graber.media_playlist_info.key_url
        filepath = os.path.join(self.fragment_folder, 'server.key')
        await downloader.async_download(url, filepath, self.session, size_check=False)
        with open(filepath, 'rb') as key_file:
            self.key = key_file.read()
            log.info(f"AES128解密HEX：\"{self.key.hex()}\"，儲存於：{filepath}")
        if self.m3u8_graber.media_playlist_info.iv:
            log.info(f"IV解密HEX：\"{self.m3u8_graber.media_playlist_info.iv}\"")

#######################################################################
    async def add_normal_download(self, url:str):
        dl_info = {"filename": os.path.basename(url.split('?')[0]), "url": url, "status": "Downloading"}
        last_number = get_last_number(dl_info["filename"][:dl_info["filename"].rfind('.')])
        if last_number is None:
            raise ValueError(f"無法從檔名中獲取序號：{dl_info['filename']}")
        num = int(last_number)
        if num in self.files_status.keys():
            return False
        filepath = os.path.join(self.fragment_folder, dl_info["filename"])
        self.files_status[num] = dl_info
        async with self.semaphore:
            for retries_time in range(3):
                status = await downloader.async_download(url, filepath, self.session, retry_times=3,size_check=True)
                if status:
                    break
                else:
                    await self.refresh_download_info()
        if status:
            dl_info["status"] = "Successful"
            if self.key and self.decrypt:
                decrypt_filepath = os.path.join(self.decrypted_folder, dl_info["filename"])
                decrypt.ts_with_key_file(filepath, decrypt_filepath, self.key, self.m3u8_graber.media_playlist_info.iv)
        else:
            log.critical(f"序號：{num},下載錯誤：{url}")
            dl_info["status"] = "Failed"

    async def normal_downloader(self):
        '''監控m3u8檔案更新直到直播間關閉或是下載完成'''
        retries, faided_times = 0, 0
        while retries < 10 or self.tasks:
            if not self.key:
                self.m3u8_graber.update_master_playlist()
            m3u8_status = self.m3u8_graber.update_media_playlist()
            if self.stop_flag.is_set() and retries < 10:
                log.warning(f"收到停止訊號，等待當前下載任務完成。")
                retries = 10
            elif not self.stop_flag.is_set():
                end_number = self.get_last_file_number()
                if end_number not in self.files_status.keys():
                    for file in self.m3u8_graber.media_playlist_info.files:
                        task = self.loop.create_task(self.add_normal_download(self.m3u8_graber.media_patch_url + file.path))
                        self.tasks.add(task)
                        task.add_done_callback(lambda t: self.tasks.discard(t))
                    retries, faided_times = 0, 0
                else:
                    retries += 1
                    #log.info(f"未監控到新的檔案")
            if not m3u8_status:
                faided_times += 1
                if faided_times > 10:
                    log.critical(f"直播間已關閉，停止所有下載任務。")
                    await self.stop_all_tasks()
                    break
            await asyncio.sleep(3)
#########################
    async def add_format_download(self, num:int):
        if num in self.files_status.keys():
            return False
        dl_info = {"filename": "", "url": "", "status": "Downloading"}
        self.files_status[num] = dl_info
        async with self.semaphore:
            for retries_time in range(3):
                assert self.format_info is not None, "格式化網址無法使用，請檢查網路連線、Cookies、Referer、User-Agent。"
                url:str = self.format_info.url.format(num=str(num).zfill(self.format_info.fill))
                dl_info["url"] = url
                if not dl_info["filename"]:
                    dl_info["filename"] = os.path.basename(url.split('?')[0])
                    filepath = os.path.join(self.fragment_folder, dl_info["filename"])
                status = await downloader.async_download(url, filepath, self.session, retry_times=5, size_check=True)
                if status:
                    break
                else:
                    await self.refresh_download_info()
        if status:
            dl_info["status"] = "Successful"
            if self.key and self.decrypt:
                decrypt_filepath = os.path.join(self.decrypted_folder, dl_info["filename"])
                decrypt.ts_with_key_file(filepath, decrypt_filepath, self.key, self.m3u8_graber.media_playlist_info.iv)
        else:
            log.critical(f"序號：{num},下載錯誤：{url}")
            dl_info["status"] = "Failed"

    async def format_downloader(self):
        """可用格式化下載方式下載"""
        last_num =  self.get_last_file_number()
        start_number = await FindStartFile(self.format_info.url, self.format_info.fill, session=self.session).main(last_num)
        retries, faided_times = 0, 0
        now_amount = 0
        while retries < 10 or self.tasks:
            #if not self.key:
            #    self.m3u8_graber.update_master_playlist()
            m3u8_status = self.m3u8_graber.update_media_playlist()
            if self.stop_flag.is_set() and retries < 10:
                log.warning(f"收到停止訊號，等待當前下載任務完成。")
                retries = 10
            elif not self.stop_flag.is_set():
                end_number = self.get_last_file_number()
                if end_number not in self.files_status.keys():
                    for num in range(start_number, end_number+1):
                        task = self.loop.create_task(self.add_format_download(num))
                        self.tasks.add(task)
                        task.add_done_callback(lambda t: self.tasks.discard(t))
                    log.info(f"添加下載範圍，序號：{start_number} - {end_number}，共 {end_number-now_amount+1}個檔案")
                    now_amount = end_number
                    retries, faided_times = 0, 0
                else:
                    retries += 1
                    log.info(f"未監控到新的檔案")
            if not m3u8_status:
                faided_times += 1
                if faided_times > 10:
                    log.critical(f"直播間已關閉，停止所有下載任務。")
                    await self.stop_all_tasks()
                    break
            start_number = end_number
            await asyncio.sleep(3)
        log.info(f"已結束的碎片下載完成")
#######################################################################

    def get_last_file_number(self) -> int:
        """獲取最後一個檔案的序號"""
        last_file: str = self.m3u8_graber.media_playlist_info.files[-1].path.split('?')[0]
        last_file_name = os.path.basename(last_file)
        last_number = get_last_number(last_file_name[:last_file_name.rfind('.')])
        if last_number is None:
            raise ValueError(f"無法從檔名中獲取序號：{last_file}")
        return int(last_number)

    async def refresh_download_info(self):
        """更新下載所需的資訊"""
        #更新cookies
        if isinstance(self.m3u8_info.cookies, webdriver.Chrome):
            self.update_cookies()
            if isinstance(self.cookies, dict):
                self.session.cookie_jar.update_cookies(self.cookies)
            else:
                log.warning("Cookies已失效")
        #更新格式化網址
        #if self.format_info is not None:
        #    self.m3u8_graber.update_media_playlist()
        #    self.format_info = get_format_file_url(self.m3u8_graber.media_patch_url, self.m3u8_graber.media_playlist_info.files[0].path, self.m3u8_graber.media_playlist_info.files[1].path)
        #    if self.format_info is not None:
        #        log.info(f"格式化網址更新為：{self.format_info['format_url']}")
        #    else:
        #        log.warning("格式化網址已失效")

    async def stop_all_tasks(self):
        """ 取消所有異步任務 """
        for task in self.tasks:
            task.cancel()
        try:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        finally:
            self.tasks.clear()
            log.info(f"所有下載已取消")

    def create_m3u8_file(self, filepath, without_key = False):
        header_text = ''
        for line in self.m3u8_graber.media_playlist_content.splitlines():
            if "#EXTINF:" in line or "#EXT-X-PROGRAM-DATE-TIME:" in line:
                break
            elif "#EXT-X-MAP:" in line:
                header_text += line.replace(self.m3u8_graber.media_playlist_info.map_url, os.path.basename(self.m3u8_graber.media_playlist_info.map_url)) + '\n'
            elif "#EXT-X-KEY:" in line and not without_key:
                header_text += line.replace(self.m3u8_graber.media_playlist_info.key_url, "server.key") + '\n'
            else:
                header_text += line + '\n'
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(header_text)
            for num in sorted(self.files_status.keys()):
                f.write(f"#EXTINF:{self.m3u8_graber.media_playlist_info.target_duration},\n")
                f.write(self.files_status[num]["filename"] + "\n")
            f.write("#EXT-X-ENDLIST")
    
    def merge_media(self):
        '''合併碎片檔案至MP4'''
        log.info(f"開始合併媒體檔案")
        share_url = share.main(set_port=8000, directory=self.fragment_folder) 
        final_file = os.path.join(self.output_path, f'{self.m3u8_info.filename}.{self.m3u8_graber.media_playlist_info.media_ext}')
        if os.path.exists(final_file):
            log.info(f"最終檔案已存在，不進行合併。")
            return
        convert_m3u8_to_media(os.path.join(share_url, 'media.m3u8'), final_file, self.convert_tool)
        log.info(f"合併媒體檔案完成。")
        share.stop()

    def log_status(self):
        error = 0
        success = 0
        for name, info in self.files_status.items():
            if info["status"] == "Downloading" or info["status"] == "Failed":
                error += 1
            else:
                success += 1
        log.info(f"成功下載{success}個檔案，失敗{error}個檔案")
        return True if not error else False

    def log_thread_info(self):
        log.debug(f"Thread ID：{threading.get_ident()}")
        log.debug(f"Loop ID：{threading.get_ident()}")
        log.debug(f"Session ID：{id(self.session)}")

    async def mission(self):
        log.info(f"開始下載m3u8內容，網址：{self.m3u8_graber.media_playlist_url}")
        self.session = aiohttp.ClientSession(headers=self.headers, cookies=self.cookies)
        self.log_thread_info()
        self.write_source_m3u8()

        if self.m3u8_graber.media_playlist_info.map_url:
            await self.download_map()

        # 如果有解密金鑰，則下載
        if self.m3u8_graber.media_playlist_info.key_url:
            await self.download_key()

        # 監控m3u8檔案更新直到直播間關閉或是下載完成
        log.info(f"開始下載媒體檔案")
        self.format_info = get_format_file_url(
            self.m3u8_graber.media_patch_url,
            self.m3u8_graber.media_playlist_info.files[0].path,
            self.m3u8_graber.media_playlist_info.files[1].path
            )
        if self.format_info.url and self.full_download:
            log.info(f"存在關聯性檔案連結，使用格式化下載方式下載")
            await self.format_downloader()
        else:
            log.info(f"不存在關聯性檔案連結，使用串流下載方式下載")
            await self.normal_downloader()

        self.create_m3u8_file(os.path.join(self.fragment_folder, "media.m3u8"))
        if self.log_status():
            with self.merge_lock:
                self.merge_media()
        else:
            log.critical(f'存在下載失敗的檔案，請手動進行合成或是重新下載失敗的檔案')
            for name, info in self.files_status.items():
                if info["status"] != 'Successful':
                    log.error(f"序號：{name},下載錯誤：{info['url']}")
        await self.session.close()
        return True

    def set_model_logger(self, log: logging.Logger):
        """設定模組日誌"""
        set_logger(log)
        downloader.set_logger(log)
        decrypt.set_logger(log)
        m3u8_graber.set_logger(log)
        log.info(f"模組日誌已設定為：{log.name}")

    def main(self, name_length: int = 0):
        threading.current_thread().name = self.m3u8_info.filename if name_length == 0 else self.m3u8_info.filename.ljust(name_length)
        self.prepare()
        log_path = os.path.join(self.backup_folder, self.m3u8_info.filename+'.log')
        log_handler = logger.start_thread_logging(log_path)
        log = logging.getLogger(self.m3u8_info.filename)
        self.set_model_logger(log)
        self.loop.run_until_complete(self.mission())
        self.loop.close()
        asyncio.set_event_loop(self._original_loop)
        logging.getLogger().removeHandler(log_handler)
        log_handler.close()


################################################################

if __name__ == '__main__':
    pass