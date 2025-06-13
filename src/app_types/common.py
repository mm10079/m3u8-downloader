from typing import TypedDict, Union
from selenium import webdriver
from dataclasses import dataclass

from src.app_types.m3u8 import M3U8Info

@dataclass
class ZanLiveItem:
    driver: webdriver.Chrome
    ticket: dict  # 或更精確的類型

class PromotionalsPicture(TypedDict):
    banner: list[str]
    titlelogo: str


CookieType = Union[str, webdriver.Chrome, dict, None]

@dataclass
class FormatText:
    fill: int = 0
    text: str = ""

@dataclass
class FormatInfo:
    url: str = ""
    fill: int = 0

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