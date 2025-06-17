import os
import sys
from typing import List
from dataclasses import dataclass, field

USERAGENT = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36'

def get_resource_path():
    if os.name == "nt":
        if getattr(sys, 'frozen', False):
            # ✅ getattr 安全存取，避免靜態報錯
            base_path = getattr(sys, '_MEIPASS', os.getcwd())
        else:
            base_path = os.getcwd()
        return os.path.join(base_path, 'src', 'tools', 'ffmpeg.exe')
    else:
        return "ffmpeg"

@dataclass
class DefaultParams:
    url: str = field(
        default= '',
        metadata={
            "nargs": "?",
            "help": "下載網址\n可輸入m3u8網址或其他網址，留空則開啟google首頁",
            }
        )
    title: str = field(
        default= 'media',
        metadata={
            "help": "標題名稱\n如果網站有爬取到標題，則優先使用網站標題",
            }
        )
    quantity: int = field(
        default= 0,
        metadata={
            "help": "下載畫質\n僅用於自動化下載",
            }
        )
    output: str = field(
        default= 'downloads',
        metadata={
            "help": "輸出路徑",
            }
        )
    cookies: str = field(
        default= '',
        metadata={
            "help": "Cookies路徑\n僅用於直接下載m3u8時，若爬蟲網站則會自動生成，可輸入路徑或Cookies字串",
            }
        )
    tool: str = field(
        default_factory= get_resource_path,
        metadata={
            "help": "合併用工具路徑",
            }
        )
    decrypt: bool = field(
        default= False,
        metadata={
            "help": "邊下載中解密",
            }
        )
    #full_download: bool = field(
    #    default= True,
    #    metadata={
    #        "help": "完全下載\n於直播時嘗試回推存檔值",
    #        }
    #    )
    threads: int = field(
        default= 3,
        metadata={
            "help": "同步下載m3u8數量\n最少為1，最多不超過電腦多線程的 3/4",
            }
        )
    referer: str = field(
        default= "",
        metadata={
            "help": "referer，如果輸入m3u8網址則建議設定",
            }
        )
    user_agent: str = field(
        default= USERAGENT,
        metadata={
            "help": "user_agent，平常不用設定，如果無法下載可以手動添加",
            }
        )

@dataclass
class WebParams(DefaultParams):
    account: str = field(
        default="",
        metadata={
            "help": "登入帳號",
            }
        )
    password: str = field(
        default="",
        metadata={
            "help": "登入密碼",
            }
        )
    chrome_path: str = field(
        default="",
        metadata={
            "help": "chrome路徑\n平常不用設定，如果無法開啟瀏覽器請手動添加",
            }
        )
    headless: bool = field(
        default=False,
        metadata={
            "help": "無頭模式",
            }
        )
    media: bool = field(
        default=True,
        metadata={
            "help": "下載m3u8內容",
            }
        )
    attachment: bool = field(
        default=True,
        metadata={
            "help": "下載附件\n評論、貼圖、票券訊息等",
            }
        )
    skip_urls: List[str] = field(
        default_factory=list,
        metadata={
            "help": "跳過網址\n自動跳過特定的直播間或m3u8網址",
            }
        )