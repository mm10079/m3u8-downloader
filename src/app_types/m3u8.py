from dataclasses import dataclass, field
from selenium import webdriver

@dataclass
class MediaPlaylistFileInfo:
    index: int = 0
    quality: str = ""
    media_type: str = ""
    line: str = ""
    filepath: str = ""
    
@dataclass
class MasterPlaylistInfo:
    name: str = ""
    url: str = ""
    session_key: str = ""
    m3u8s: dict[int, MediaPlaylistFileInfo] = field(default_factory=dict)

@dataclass
class MediaFile:
    order: int = 0
    extinf: float = 0
    path: str = ""
    time: str = ""

@dataclass
class MediaPlaylistInfo:
    name: str = ""
    url: str = ""
    play_type: str = ""
    encode_type: str = ""
    iv: str = ""
    key_url: str = ""
    map_url: str = ""
    img_url: str = ""
    media_ext: str = ""
    target_duration: int = 0
    version: int = 0
    media_sequence: int = 0
    files: list[MediaFile] = field(default_factory=list)

@dataclass
class M3U8Info:
    order: int = 0
    url: str = ""
    filename: str = ""
    folder: str = ""
    referer: str = ""
    user_agent: str | None = None
    cookies: str | webdriver.Chrome | dict | None = None

@dataclass
class PatchInfo:
    base: str = ""
    file: str = ""