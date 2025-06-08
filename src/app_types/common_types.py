from typing import TypedDict, Union
from selenium import webdriver
from dataclasses import dataclass

@dataclass
class ZanLiveItem:
    driver: webdriver.Chrome
    ticket: dict  # 或更精確的類型

class PromotionalsPicture(TypedDict):
    banner: list[str]
    titlelogo: str

@dataclass
class M3U8Info:
    order: int = 0
    url: str = ""
    filename: str = ""
    folder: str = ""
    referer: str = ""
    user_agent: str | None = None
    cookies: str | webdriver.Chrome | dict | None = None
    full_download: bool = False

CookieType = Union[str, webdriver.Chrome, dict, None]

@dataclass
class File:
    folder: str
    file: str | dict | bytes | list

@dataclass
class AttachmentInfo:
    cookies: str | webdriver.Chrome | dict | None
    files: dict[str, File]

@dataclass
class Mission:
    m3u8s: list[M3U8Info]
    attachments: AttachmentInfo | None