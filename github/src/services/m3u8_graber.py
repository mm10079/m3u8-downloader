import re
import sys
import logging
import requests
from selenium import webdriver
from collections import OrderedDict

from src.app_types import common_types
from src.utils import set_cookies

log = logging.getLogger(__name__)

def set_logger(new_log):
    current_module = sys.modules[__name__]  # 取得 `c` 模組的引用
    setattr(current_module, "log", new_log)

def is_digit(s):
    try:
        int(s)
        return True
    except ValueError:
        return False
    
# 取得與存檔案網址可組合的基本網址
def get_patch_url(m3u8_url: str, file_address: str) -> dict:
    scheme = m3u8_url.split('://')[0]
    m3u8_paths = m3u8_url.split('://')[1].split('?')[0].split('/')[:-1]
    file_paths = file_address.split('?')[0].split('/')
    base_url = scheme + '://'
    for path in m3u8_paths:
        if path in file_paths:
            break
        base_url += path + '/'
    if file_address[0] == '/':
        base_url = base_url[:-1]
    file_url = base_url + file_address
    return {'base_url': base_url, 'file_url': file_url}

def check_url_status(url, headers, session = requests.Session()) -> bool:
    # 檢查網址是否有效
    try:
        result = session.get(url, headers=headers)
        if result.status_code == 200:
            log.debug(f"檢驗網址，檢驗有效：{url}")
            return True
        log.debug(f"檢驗網址，檢驗無效：{url} - {result.status_code}")
        return False
    except requests.exceptions.RequestException as e:
        log.warning(f"檢驗網址，檢驗無效：{url} - {str(e)}")
        return False
    
# 解析區塊
# 將主播放列表解析為字典
def process_master_playlist(url: str, content: str):
    master_playlist_info = {
        "name": url.split('?')[0].split('/')[-1],
        "url": url,
        "EXT-X-VERSION": 0,
        "m3u8s": {},
    }

    lines = content.splitlines()
    index = 0  # 明確記錄插入順序
    for n in range(len(lines)):
        m3u8 = {
            'quality': '',
            'type': '',
            'uri': '',
            'line': lines[n],
            'order': index  # 新增順序欄位
        }
        if '#' in lines[n]:
            if 'EXT-X-MEDIA' in lines[n]:
                info = lines[n].replace('#EXT-X-MEDIA:', '').split(',')
                info = {i.split('=')[0]: i.split('=')[1].strip('"') for i in info}
                m3u8['quality'] = info.get('GROUP-ID', '')
                m3u8['type'] = info.get('TYPE', '')
                m3u8['uri'] = info.get('URI', '')
                master_playlist_info["m3u8s"][index] = m3u8
                index += 1
            elif 'EXT-X-STREAM-INF' in lines[n]:
                match = re.search(r'BANDWIDTH=(\d+)', lines[n])
                m3u8["quality"] = match.group(1) if match else '0'
                m3u8['type'] = 'STREAM'
                if n + 1 < len(lines):
                    m3u8['uri'] = lines[n + 1]
                master_playlist_info["m3u8s"][index] = m3u8
                index += 1
            elif 'EXT-X-VERSION' in lines[n]:
                master_playlist_info['EXT-X-VERSION'] = int(lines[n].split(':')[1])

    # 分類：數字 quality 要排序；字串則保持原順序
    entries = list(master_playlist_info["m3u8s"].values())
    numeric = [e for e in entries if is_digit(e['quality'])]
    non_numeric = [e for e in entries if not is_digit(e['quality'])]

    # 對數字部分排序（同類型，按 quality 數字從大到小）
    numeric_sorted = sorted(
        numeric,
        key=lambda x: (x['type'], int(x['quality'])),
        reverse=True
    )

    # 合併，維持非數字順序在原順序
    combined = numeric_sorted + non_numeric

    # 重建 m3u8s，並去掉 'order' 欄位
    master_playlist_info["m3u8s"] = OrderedDict()
    for i, m3u8 in enumerate(combined):
        m3u8.pop('order', None)
        master_playlist_info["m3u8s"][i] = m3u8

    return master_playlist_info

# 將媒體播放列表解析為字典
def process_media_playlist(url: str, content: str):
    media_playlist_info = {
        "name": url.split('?')[0].split('/')[-1],
        "url": url,
        "type": 'STREAM',
        "EXT-X-MAP": '',
        "EXT-X-TARGETDURATION": 0,
        "EXT-X-VERSION": 0,
        "EXT-X-MEDIA-SEQUENCE": 0,
        "KEY-URI": '',
        "IV": '',
        "files": [],
        "media_ext": '',
    }
    order_counter = 0
    lines = content.splitlines()
    
    for n in range(len(lines)):
        line = lines[n]
        if '#' in line:
            if 'EXTINF' in line:
                try:
                    duration = float(line.split(':')[1].split(',')[0])
                except (IndexError, ValueError):
                    duration = 0.0
                order_counter += 1
                file = {
                    'order': order_counter,
                    'EXTINF': duration,
                    'path': lines[n+1] if n+1 < len(lines) else '',
                    'EXT-X-PROGRAM-DATE-TIME': lines[n-1].replace('#EXT-X-PROGRAM-DATE-TIME:', '') if 'EXT-X-PROGRAM-DATE-TIME' in lines[n-1] else '',
                }
                media_playlist_info['files'].append(file)
            
            elif 'EXT-X-TARGETDURATION' in line:
                media_playlist_info['EXT-X-TARGETDURATION'] = int(line.split(':')[1])
            elif 'EXT-X-VERSION' in line:
                media_playlist_info['EXT-X-VERSION'] = int(line.split(':')[1])
            elif 'EXT-X-MEDIA-SEQUENCE' in line:
                media_playlist_info['EXT-X-MEDIA-SEQUENCE'] = int(line.split(':')[1])
            elif 'EXT-X-PLAYLIST-TYPE' in line:
                media_playlist_info['type'] = 'VOD'
            elif 'EXT-X-KEY' in line:
                if 'URI="' in line:
                    media_playlist_info['KEY-URI'] = line.split('URI="')[1].split('"')[0]
                if 'IV=0x' in line:
                    iv_split = line.split('IV=0x')
                    if len(iv_split) > 1:
                        media_playlist_info['IV'] = iv_split[1].split(',')[0]
            elif 'EXT-X-MAP' in line:
                media_playlist_info['EXT-X-MAP'] = line.split('URI="')[1].split('"')[0]
    media_playlist_info['media_ext'] = media_playlist_info['files'][-1]['path'].split('?')[0].split('.')[-1]
    return media_playlist_info


class get_media_m3u8:
    ''' 
    使用方式：
        先透過get_master_playlist取得主播放清單資訊，透過self.m3u8_order來控制要被更新的媒體播放清單
        接著只要執行update_media_playlist即可取得更新後的媒體播放清單
    '''
   
    def __init__(self, url: str, m3u8_order:int = 0, cookies: webdriver.Chrome|dict|str|None = None, headers:dict = {}):
        self.m3u8_order = m3u8_order
        self.cookies = cookies
        self.headers = headers
        self.determine_m3u8_type(url)

        self.print_check = False

    def determine_m3u8_type(self, url):
        # 初始化m3u8相關參數，並且判定是主播放清單還是媒體播放清單
        # 之後可以直接透過self.media_patch_url來組合正式的檔案網址
        self.master_playlist_content = ''
        self.master_playlist_url = ''
        self.master_patch_url = ''
        self.master_playlist_info = {}
        self.media_playlist_content = ''
        self.old_media_playlist_url = ''
        self.media_playlist_url = ''
        self.media_patch_url = ''
        self.media_playlist_info = {}
        self.session = set_cookies.update_session(self.cookies)
        top_m3u8_content = self.session.get(url, headers=self.headers).text
        if '.m3u8' in top_m3u8_content:
            self.master_playlist_url = url
        elif '#EXTINF' in top_m3u8_content:
            self.media_playlist_url = url
        else:
            raise Exception()

    def print_info(self):
        if not self.print_check:
            if self.master_playlist_url:
                log.info(f"取得主播放清單網址：{self.master_playlist_url}")
                log.info(f"選擇的媒體播放清單品質：{self.master_playlist_info['m3u8s'][self.m3u8_order]['line']}")
            log.info(f"媒體播放清單網址：{self.media_playlist_url}")
            self.print_check = True


    def get_master_playlist(self) -> str:
        '''取得並回傳Master Playlist內容，過程中解析Master Playlist內容並取得Media Playlist網址'''
        try:
            self.master_playlist_content = self.session.get(self.master_playlist_url, headers=self.headers).text
            self.master_playlist_info = process_master_playlist(self.master_playlist_url, self.master_playlist_content)
            if self.m3u8_order >= len(self.master_playlist_info["m3u8s"]) or self.m3u8_order < 0:
                self.m3u8_order = -1
            media_m3u8_file_url = self.master_playlist_info["m3u8s"][self.m3u8_order]["uri"]
            if not self.master_patch_url:
                patch = get_patch_url(self.master_playlist_url, media_m3u8_file_url)
                self.master_patch_url = patch["base_url"]
            self.media_playlist_url = self.master_patch_url + media_m3u8_file_url
            return self.master_playlist_content
        except:
            self.media_playlist_url = ''
            log.warning(f"獲取主播放清單失敗: {self.master_playlist_url}")
            return ""

    def get_media_playlist(self) -> str:
        '''取得並回傳Media Playlist內容，過程中解析Media Playlist內容
        如有Master Playlist網址則從Master Playlist取得Media Playlist網址，再取得內容
        如無Master Playlist網址則直接從Media Playlist網址取得Media Playlist內容
        '''
        try:
            self.media_playlist_content = self.session.get(self.media_playlist_url, headers=self.headers).text
            media_playlist_info = process_media_playlist(self.media_playlist_url, self.media_playlist_content)
            if not self.media_patch_url:
                self.get_media_patch_url(media_playlist_info)
            else:
                if not check_url_status(self.media_patch_url + media_playlist_info["files"][0]["path"], headers=self.headers, session = self.session):
                    self.get_media_patch_url(media_playlist_info)
            self.media_playlist_info =  media_playlist_info
            return self.media_playlist_content
        except:
            self.media_patch_url = ''
            log.warning(f"MEDIA M3U8 URL: {self.media_playlist_url}")
            log.warning("獲取媒體播放清單失敗")
            return ""

    def get_media_patch_url(self, media_playlist_info) -> str | None:
        '''對Master Playlist與Media Playlist的網址進行拆解測試，從中取得可以與檔案組合成正確網址的Patch網址'''
        file_url = media_playlist_info["files"][0]["path"]
        patch = get_patch_url(self.media_playlist_url, file_url)
        if not check_url_status(patch["file_url"], headers=self.headers, session = self.session):
            if self.master_playlist_url:
                patch = get_patch_url(self.master_playlist_url, file_url)
                if not check_url_status(patch["file_url"], headers=self.headers, session = self.session):
                    log.error(f"媒體播放清單網址與主播放清單網址皆無法用於檔案網址，請檢查網路連線、Cookies、Referer、User-Agent。")
                    log.error(f"主播放清單基底網址：{patch['base_url']}")
                    log.error(f"檔案網址：{patch['file_url']}")
                    return None
            else:
                log.error(f"媒體播放清單網址無法用於檔案網址，並且缺失主播放清單網址。")
                log.error(f"媒體播放清單基底網址：{patch['base_url']}")
                log.error(f"檔案網址：{patch['file_url']}")
                return None
        self.media_patch_url = patch["base_url"]
        return patch["base_url"]

    def update_master_playlist(self) -> None:
        if self.master_playlist_url:
            self.session = set_cookies.update_session(self.cookies, self.session)
            log.info(f"更新主播放清單: {self.master_playlist_url}")
            self.get_master_playlist()

    def update_media_playlist(self) -> bool:
        # 更新媒體播放清單，可以透過self.m3u8_order來控制更新媒體播放清單
        self.print_info()
        if self.media_playlist_url:
            self.session = set_cookies.update_session(self.cookies, self.session)
            log.info("更新媒體播放清單")
            self.get_media_playlist()
            if self.old_media_playlist_url != self.media_playlist_url:
                self.old_media_playlist_url = self.media_playlist_url
                log.info(f"媒體播放清單網址更新為：{self.media_playlist_url}")
            return True
        else:
            log.warning("獲取媒體播放清單失敗")
            return False