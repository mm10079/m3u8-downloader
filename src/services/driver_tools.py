import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/97.0.4692.99 Safari/537.36"

def new(chrome_path: str | None = None, headless: bool = False) -> webdriver.Chrome:
    chrome_options = webdriver.ChromeOptions()
    prefs = {
        "credentials_enable_service": False,
        "profile.password_manager_enabled": False,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
        "safebrowsing.enabled": True
        }
    chrome_options.add_experimental_option('prefs', prefs) ##关掉密码弹窗
    chrome_options.add_argument("--log-level=3")#關閉瀏覽器日誌
    chrome_options.add_argument('–disable-gpu')#谷歌文档提到需要加上这个属性来规避bug
    chrome_options.add_argument('lang=zh_TW.UTF-8')#设置默认编码为utf-8
    chrome_options.add_argument(f"user-agent={USER_AGENT}")#設置用戶代理
    chrome_options.add_experimental_option('useAutomationExtension', False)#取消chrome受自动控制提示
    chrome_options.add_experimental_option('excludeSwitches', ['enable-automation']) # 取消chrome受自动控制提示
    if headless:
        chrome_options.add_argument("--headless")#启用无头模式
    caps = chrome_options.to_capabilities()
    caps['goog:loggingPrefs'] = {'performance': 'ALL'}
    return webdriver.Chrome(options= chrome_options) if not chrome_path else webdriver.Chrome(options= chrome_options, service= Service(chrome_path))

def get_m3u8_link(driver: webdriver.Chrome, skip_m3u8s: set) -> list:
    m3u8_urls = []
    for entry in driver.get_log('performance'):
        web_log = json.loads(entry['message'])  # 將日誌轉換為 JSON 格式
        message = web_log.get('message', {})
        if message.get('method') == 'Network.requestWillBeSent':  # 過濾網路請求事件
            request_url = message['params']['request']['url']
            if '.m3u8' in request_url and request_url not in skip_m3u8s:
                m3u8_urls.append(request_url)
    return m3u8_urls