import argparse
import json
import os
import sys

type_map = {
    "str": str,
    "int": int,
    "bool": lambda x: bool(int(x)) if isinstance(x, str) else bool(x),
    "list": lambda x: x.split(",")
}

def get_resource_path():
    if os.name == "nt":
        if getattr(sys, 'frozen', False):
            # ✅ getattr 安全存取，避免靜態報錯
            base_path = getattr(sys, '_MEIPASS', os.getcwd())
        else:
            base_path = os.getcwd()
        return os.path.join(base_path, 'tools', 'ffmpeg.exe')
    else:
        return "ffmpeg"

class CustomHelpFormatter(argparse.ArgumentDefaultsHelpFormatter):
    def add_argument(self, action):
        if action.type and action.metavar is None:
            action.metavar = getattr(action.type, '__name__', str(action.type))
        super().add_argument(action)

class Params:
    def default(self):
        value = {
            "url": {
                "type": "str",
                "nargs": "?",
                "help": "下載網址\n可輸入m3u8網址或其他網址，留空則開啟google首頁",
                "default": ''
            },
            "title": {
                "type": "str",
                "nargs": None,
                "help": "標題名稱\n如果網站有爬取到標題，則優先使用網站標題",
                "default": "media"
            },
            "quantity": {
                "type": "int",
                "nargs": None,
                "help": "下載畫質\n僅用於自動化下載",
                "default": 0
            },
            "output_path": {
                "type": "str",
                "nargs": None,
                "help": "輸出路徑",
                "default": os.path.join(os.getcwd(), 'downloads')
            },
            "cookies_path": {
                "type": "str",
                "nargs": None,
                "help": "Cookies路徑\n僅用於直接下載m3u8時，若爬蟲網站則會自動生成",
                "default": os.path.join(os.getcwd(), 'cookies.txt')
            },
            "tool_path": {
                "type": "str",
                "nargs": None,
                "help": "合併用工具路徑",
                "default": get_resource_path()
            },
            "decrypt": {
                "type": "bool",
                "nargs": None,
                "help": "邊下載中解密",
                "default": False
            },
            "full_download": {
                "type": "bool",
                "nargs": None,
                "help": "完全下載\n於直播時嘗試回推存檔值",
                "default": True
            },
            "threads_limit": {
                "type": "int",
                "nargs": None,
                "help": "多線程數量\n最少為3，最多不超過電腦多線程的 3/4",
                "default": 10
            },
            "referer": {
                "type": "str",
                "nargs": None,
                "help": "referer，如果輸入m3u8網址則建議設定",
                "default": ""
            },
            "user_agent":{
                "type": "str",
                "nargs": None,
                "help": "user_agent，平常不用設定，如果無法下載可以手動添加",
                "default": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
            }
        }
        return value

    def web(self):
        value= {
            "account": {
                "type": "str",
                "nargs": None,
                "help": "登入帳號",
                "default": ""
            },
            "password": {
                "type": "str",
                "nargs": None,
                "help": "登入密碼",
                "default": ""
            },
            "chrome_path": {
                "type": "str",
                "nargs": None,
                "help": "chrome路徑\n平常不用設定，如果無法開啟瀏覽器請手動添加",
                "default": ""
            },
            "headless": {
                "type": "bool",
                "nargs": None,
                "help": "無頭模式",
                "default": False
            },
            "media": {
                "type": "bool",
                "nargs": None,
                "help": "下載m3u8內容",
                "default": True
            },
            "attachment": {
                "type": "bool",
                "nargs": None,
                "help": "下載附件\n評論、貼圖、票券訊息等",
                "default": True
            },
            "twitter_keywords": {
                "type": "list",
                "nargs": None,
                "help": "推特關鍵字\n要下載的推特m3u8名稱的關鍵字，可以輸入多個關鍵字 e.g. '推特1,推特2'",
                "default": "playlist"
            },
            "skip_urls": {
                "type": "list",
                "nargs": None,
                "help": "跳過網址\n自動跳過特定的直播間或m3u8網址",
                "default": ""
            }
        }
        value.update(self.default())
        return value

def set_parser(params: dict, description=""):
    parser = argparse.ArgumentParser(
        description=description,
        formatter_class=CustomHelpFormatter
    )
    for env, param  in params.items():
        param_type = type_map.get(param["type"], str)

        if env == "media":
            parser.add_argument(
                f'--skip-media',
                action='store_true',
                help="跳過m3u8內容",
            )
            continue

        env = env.replace('_', '-')
        if param["type"] == "bool":
            parser.add_argument(
                f'--{env}',
                action='store_true',
                help=param["help"],
            )
        else:
            parser.add_argument(
                env if param["nargs"] == '?' else f'--{env}',
                type=param_type,
                nargs=param["nargs"],
                help=param["help"],
                default=param["default"]
            )
    return parser


def get_config(config_type="default") -> dict:
    '''取得設定'''
    params = Params().default() if config_type == "default" else Params().web()
    config = get_base_config()
    description=f"m3u8下載器，可輸入m3u8網址或其他網址，下載器將會自動解析m3u8文件，並下載m3u8內容。目前版本：{config['version']}\n"
    parser = set_parser(params ,description)
    args, unknown_args  = parser.parse_known_args()
    for env, param in params.items():
        if env == "media":
            config[env] = True if not getattr(args, "skip_media") else False
        else:
            config[env] = getattr(args, env)
    config = get_test_config(config)
    return config

def get_base_config(config = {}) -> dict:
    '''取得基本設定'''
    config["version"] = 'v2025.06.08-2.0.0.0'
    config["opening_message"] = f'開始執行m3u8下載器(版本：{config["version"]})\n歡迎使用m3u8下載器，本下載器提供者為 馬邦德，有任何問題請到 https://github.com/mm10079/m3u8-downloader 聯繫。\n本下載器僅供學術研究使用，請勿用於任何商業用途，如有侵權請告知，將立即刪除。\n'
    return config

def get_test_config(config = {}) -> dict:
    '''手動輸入測試設定'''
    return config

if __name__ == '__main__':
    config = get_config("web")
    print(json.dumps(config, indent=4, ensure_ascii=False)) # 輸出設定參數
    pass