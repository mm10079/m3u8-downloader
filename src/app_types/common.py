from typing import TypedDict, Union
from selenium import webdriver
from dataclasses import dataclass
from enum import Enum

from src.app_types.m3u8 import M3U8Info

class Deltas(Enum):
    IG = [2000, 2001, 1999, 1967, 1968, 1966, 2564]
    REALITY = [8000, 8001, 7999, 7967, 7968, 7966, 8564]
    
@dataclass
class ZanLiveItem:
    driver: webdriver.Chrome
    ticket: dict  # 或更精確的類型

class PromotionalsPicture(TypedDict):
    banner: list[str]
    titlelogo: str


CookieType = Union[str, webdriver.Chrome, dict, None]

@dataclass
class FileInfo:
    number: int
    format_path: str
    fill: int

@dataclass
class FormatInfo:
    url: str = ""
    fill: int = 0
    space: int = 1

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